"""PostgreSQL-serialized admission with OS-owned worker liveness fences.

Only trusted deployment configuration and verified identities enter this layer.
Physical files remain charged after failed deletion or worker death.
"""

import math
import secrets
import shutil
import tempfile
from collections import Counter
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from threading import Lock
from uuid import UUID, uuid4

from sqlalchemy import Connection, select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.models import AdmissionState, ChatImportArtifact, ChatImportJob, UploadReservation, User
from app.db.session import Database, DatabaseUnavailable
from app.services.admission_fence import WorkerFence, is_live


class AdmissionRejected(Exception):
    def __init__(self, status=503, code="artifact_unavailable", retry_after=1):
        super().__init__(code)
        self.status = status
        self.code = code
        self.retry_after = retry_after


@dataclass
class AdmissionLease:
    connection: Connection
    id: UUID
    lock_key: int
    artifact_key: str | None
    fence: WorkerFence


class ResourceAdmission:
    def __init__(self, database: Database, settings: Settings):
        self.database = database
        self.settings = settings
        self.root = settings.chat_import_artifact_root.resolve()
        self.scope_key = sha256(str(self.root).encode()).hexdigest()
        self.fence_root = self.root.parent / (".admission-fences-" + self.scope_key[:16])
        self.guard_key = int(self.scope_key[:15], 16)
        policy = {k: v for k, v in settings.model_dump().items() if k.startswith("admission_")}
        policy["max_chat_import_bytes"] = settings.max_chat_import_bytes
        policy["max_chat_import_speakers"] = settings.max_chat_import_speakers
        self.policy_hash = sha256(repr(sorted(policy.items())).encode()).hexdigest()
        # One file spool, one artifact, form framing and conservative file overhead.
        self.upload_reservation_bytes = 2 * settings.max_chat_import_bytes + 1024**2 + 16384
        self._metrics = Counter()
        self._metrics_lock = Lock()

    def record(self, event):
        if event not in {
            "capacity_rejected",
            "rate_rejected",
            "body_timeout",
            "reclaim_candidates",
            "cleanup_failure",
        }:
            raise ValueError("Unknown resource event")
        with self._metrics_lock:
            self._metrics[event] += 1

    def _state(self, db):
        db.execute(text("SET LOCAL lock_timeout = '250ms'"))
        db.execute(text("SET LOCAL statement_timeout = '2000ms'"))
        db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": self.guard_key})
        db.execute(
            insert(AdmissionState)
            .values(scope_key=self.scope_key, policy_hash=self.policy_hash, counters={})
            .on_conflict_do_nothing(index_elements=[AdmissionState.scope_key])
        )
        state = db.get(AdmissionState, self.scope_key)
        if state.policy_hash != self.policy_hash:
            # A different worker policy must not silently enlarge the quota.
            raise AdmissionRejected()
        return state

    def rate(self, owner: UUID | None, *, upload=False):
        """Shared one-minute windows, including anonymous early upload attempts."""
        try:
            with self.database.session() as db, db.begin():
                state = self._state(db)
                if owner and db.get(User, owner) is None:
                    owner = None
                now = float(db.scalar(text("SELECT extract(epoch FROM clock_timestamp())")))
                window = int(now // 60)
                counters = dict(state.counters)
                if counters.get("window") != window:
                    counters = {"window": window, "requests": 0, "uploads": 0, "owners": {}}
                owners = dict(counters["owners"])
                owned = dict(owners.get(str(owner), {"requests": 0, "uploads": 0}))
                checks = [(counters, "requests", self.settings.admission_requests_per_minute)]
                if upload:
                    checks.append((counters, "uploads", self.settings.admission_uploads_per_minute))
                if owner:
                    if (
                        str(owner) not in owners
                        and len(owners) >= self.settings.admission_inventory_limit
                    ):
                        raise AdmissionRejected()
                    checks.append(
                        (owned, "requests", self.settings.admission_owner_requests_per_minute)
                    )
                    if upload:
                        checks.append(
                            (owned, "uploads", self.settings.admission_owner_uploads_per_minute)
                        )
                rejected = any(values[name] >= limit for values, name, limit in checks)
                # Owner-rejected attempts still debit global windows. Raising
                # inside this transaction would silently roll those debits back.
                for values, name, limit in checks:
                    if values is counters or not rejected:
                        values[name] = min(limit, values[name] + 1)
                if owner:
                    owners[str(owner)] = owned
                counters["owners"] = owners
                state.counters = counters
            if rejected:
                raise AdmissionRejected(429, "http_error", max(1, math.ceil(60 - now % 60)))
        except (SQLAlchemyError, DatabaseUnavailable, OSError):
            raise AdmissionRejected() from None

    def _inventory(self, db, *, allow_unattributed=False):
        rows = list(
            db.scalars(
                select(UploadReservation).where(UploadReservation.scope_key == self.scope_key)
            )
        )
        if len(rows) > self.settings.admission_inventory_limit:
            raise AdmissionRejected()
        # A disconnected DB backend does not prove a worker stopped writing.
        # Only a released OS fence permits reclamation; no elapsed-time lease.
        for row in rows:
            if row.active and not is_live(self.fence_root / f"{row.id.hex}.lock"):
                row.active = False
                self.record("reclaim_candidates")
                (self.fence_root / f"{row.id.hex}.lock").unlink(missing_ok=True)
        active = [row for row in rows if row.active]
        ownership = {row.artifact_key: row.owner_user_id for row in rows if row.artifact_key}
        # Include pre-9C artifacts and deleted/expired metadata: disk is authority.
        files = []
        for path in self.root.iterdir():
            if (
                len(files) >= self.settings.admission_inventory_limit
                or path.is_symlink()
                or not path.is_file()
            ):
                raise AdmissionRejected()
            stat = path.stat()
            files.append(
                (path.stem, max(stat.st_size, math.ceil(stat.st_size / 4096) * 4096) + 4096)
            )
        keys = {key for key, _ in files}
        if keys:
            ownership.update(
                db.execute(
                    select(ChatImportArtifact.storage_key, ChatImportArtifact.owner_user_id).where(
                        ChatImportArtifact.storage_key.in_(keys)
                    )
                ).all()
            )
        if not allow_unattributed and any(key not in ownership for key in keys):
            # An orphan with unknown provenance cannot bypass an Owner quota.
            raise AdmissionRejected()
        active_keys = {row.artifact_key for row in active}
        totals: dict[UUID, int] = {}
        for key, size in files:
            if key not in active_keys:
                owner = ownership.get(key)
                totals[owner] = totals.get(owner, 0) + size
        for row in active:
            totals[row.owner_user_id] = totals.get(row.owner_user_id, 0) + row.reserved_bytes
        # Keep attribution for crash files; remove inactive records only after
        # actual disappearance, never on Job status alone.
        for row in rows:
            if not row.active and row.artifact_key not in keys:
                db.delete(row)
        db.flush()
        # Crash between OS fence creation and reservation commit leaves no row.
        # Serialized admissions can remove only those orphan fences whose OS
        # lock is free. Neither age nor a dead DB backend authorizes removal.
        if self.fence_root.exists():
            known = {f"{row.id.hex}.lock" for row in rows}
            for count, path in enumerate(self.fence_root.iterdir()):
                if count >= self.settings.admission_inventory_limit or path.is_symlink():
                    raise AdmissionRejected()
                if path.name not in known and not is_live(path):
                    path.unlink(missing_ok=True)
        return active, totals, keys

    def acquire(self, owner: UUID, kind="upload") -> AdmissionLease:
        connection = None
        fence = None
        lock_key = secrets.randbits(62) + 1
        try:
            connection = self.database.engine().connect()
            with connection.begin(), Session(bind=connection) as db:
                self._state(db)
                if db.get(User, owner) is None:
                    raise AdmissionRejected(401, "invalid_credential")
                active, totals, keys = self._inventory(db)
                global_limit = getattr(
                    self.settings,
                    f"admission_{'uploads' if kind == 'upload' else 'processing'}_global",
                )
                owner_limit = getattr(
                    self.settings,
                    f"admission_{'uploads' if kind == 'upload' else 'processing'}_owner",
                )
                current = [row for row in active if row.kind == kind]
                if (
                    len(current) >= global_limit
                    or sum(row.owner_user_id == owner for row in current) >= owner_limit
                ):
                    raise AdmissionRejected()
                reserved = self.upload_reservation_bytes if kind == "upload" else 0
                if reserved:
                    if (
                        sum(totals.values()) + reserved
                        > self.settings.admission_storage_global_bytes
                        or totals.get(owner, 0) + reserved
                        > self.settings.admission_storage_owner_bytes
                    ):
                        raise AdmissionRejected()
                    for volume in (self.root, Path(tempfile.gettempdir())):
                        if (
                            shutil.disk_usage(volume).free
                            < self.settings.admission_min_free_bytes
                            + sum(row.reserved_bytes for row in active)
                            + reserved
                        ):
                            raise AdmissionRejected()
                    pending = list(
                        db.execute(
                            select(ChatImportJob.owner_user_id)
                            .join(
                                ChatImportArtifact,
                                ChatImportJob.artifact_id == ChatImportArtifact.id,
                            )
                            .where(
                                ChatImportArtifact.storage_key.in_(keys),
                                ChatImportJob.status.in_(
                                    ["awaiting_binding", "ready", "importing"]
                                ),
                            )
                        ).scalars()
                    )
                    uploads = [row for row in active if row.kind == "upload"]
                    if (
                        len(pending) + len(uploads) >= self.settings.admission_pending_global
                        or pending.count(owner) + sum(row.owner_user_id == owner for row in uploads)
                        >= self.settings.admission_pending_owner
                    ):
                        raise AdmissionRejected()
                if len(active) + len(keys) >= self.settings.admission_inventory_limit:
                    raise AdmissionRejected()
                reservation_id = uuid4()
                self.fence_root.mkdir(parents=True, exist_ok=True)
                if self.fence_root.is_symlink():
                    raise AdmissionRejected()
                fence = WorkerFence(self.fence_root / f"{reservation_id.hex}.lock")
                lease = AdmissionLease(
                    connection,
                    reservation_id,
                    lock_key,
                    uuid4().hex if kind == "upload" else None,
                    fence,
                )
                db.execute(text("SELECT pg_advisory_lock(:key)"), {"key": lock_key})
                db.add(
                    UploadReservation(
                        id=lease.id,
                        scope_key=self.scope_key,
                        owner_user_id=owner,
                        lock_key=lock_key,
                        kind=kind,
                        artifact_key=lease.artifact_key,
                        reserved_bytes=reserved,
                        active=True,
                    )
                )
                db.flush()
            return lease
        except BaseException as exc:
            if fence is not None:
                fence.close()
            if connection is not None:
                # Closing a pooled connection does not release session locks.
                # Invalidate the physical connection on every unsuccessful exit.
                connection.invalidate()
                connection.close()
            if isinstance(exc, (SQLAlchemyError, DatabaseUnavailable, OSError)):
                raise AdmissionRejected() from None
            raise

    def release(self, lease):
        if lease.connection.closed:
            try:
                lease.fence.close()
            except OSError:
                pass
            return
        try:
            with lease.connection.begin(), Session(bind=lease.connection) as db:
                self._state(db)
                row = db.get(UploadReservation, lease.id)
                if row:
                    row.active = False
                    if row.artifact_key is None or not any(
                        (self.root / f"{row.artifact_key}.{suffix}").exists()
                        for suffix in ("bin", "part")
                    ):
                        db.delete(row)
                    db.flush()
                db.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": lease.lock_key})
        except (SQLAlchemyError, DatabaseUnavailable, OSError, AdmissionRejected):
            # A later admission reconciles the durable row against the dead lock.
            lease.connection.invalidate()
        finally:
            lease.connection.close()
            try:
                lease.fence.close()
            except OSError:
                pass  # Unlocked fence can be reconciled without releasing a live worker.

    def snapshot(self):
        """Operator-only aggregate counts; never expose identifiers as labels."""
        with self.database.session() as db, db.begin():
            self._state(db)
            active, totals, _ = self._inventory(db, allow_unattributed=True)
            result = {
                "active_uploads": sum(row.kind == "upload" for row in active),
                "active_processing": sum(row.kind == "processing" for row in active),
                "charged_storage_bytes": sum(totals.values()),
                "unattributed_storage_bytes": totals.get(None, 0),
                "reserved_storage_bytes": sum(row.reserved_bytes for row in active),
            }
            with self._metrics_lock:
                result["worker_events"] = dict(self._metrics)
            return result
