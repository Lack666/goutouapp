"""Synthetic-only logical recovery. No target is returned before reconciliation."""

import os
import re
import shutil
import subprocess
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from sqlalchemy import Engine, create_engine, delete, select, text, update
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.models import (
    AdmissionState,
    AgentRun,
    ChatImportArtifact,
    ChatImportJob,
    MemoryConfirmationRow,
    MemoryControlRow,
    MemoryMutationRow,
    MemoryOperationRow,
    MemoryRecordRow,
    UploadReservation,
    User,
)


class RecoveryError(Exception):
    def __init__(self):
        super().__init__("synthetic_recovery_failed")


def _synthetic(url):
    if (
        url.drivername != "postgresql+psycopg"
        or url.host not in {"127.0.0.1", "localhost", "::1"}
        or not re.fullmatch(r"[a-zA-Z0-9_]+_test_[0-9a-f]{12}", url.database or "")
    ):
        raise RecoveryError()


def _pg_environment(url):
    env = os.environ.copy()
    for key in list(env):
        if key.startswith("PG"):
            del env[key]
    env.update(
        PGHOST=url.host,
        PGPORT=str(url.port or 5432),
        PGUSER=url.username or "postgres",
        PGDATABASE=url.database,
        PGPASSWORD=url.password or "",
        PGCONNECT_TIMEOUT="3",
        PGCLIENTENCODING="UTF8",
    )
    return env


def _native(binary, arguments, url):
    try:
        result = subprocess.run(
            [str(binary), *arguments],
            env=_pg_environment(url),
            capture_output=True,
            timeout=60,
            check=False,
        )
        if result.returncode:
            raise RecoveryError()
    except Exception:
        # TimeoutExpired and CalledProcessError may include private argv/output.
        raise RecoveryError() from None


def pg_binary(name: str) -> Path:
    directory = os.getenv("PG_BIN_DIR")
    suffix = ".exe" if os.name == "nt" else ""
    candidate = Path(directory) / (name + suffix) if directory else None
    if candidate and candidate.is_file():
        return candidate
    found = shutil.which(name)
    if found:
        return Path(found)
    # Existing repository-local PostgreSQL16 test installation; not a download.
    local = Path(__file__).resolve().parents[4] / ".cache/pg16/pgsql/bin" / (name + suffix)
    if local.is_file():
        return local
    raise RecoveryError()


def dump_synthetic(source: Engine, archive: Path, *, snapshot: str | None = None):
    _synthetic(source.url)
    if archive.exists() or archive.is_symlink() or not archive.parent.is_dir():
        raise RecoveryError()
    arguments = ["--format=custom", "--no-owner", "--no-privileges", "--file", str(archive)]
    if snapshot is not None:
        if not re.fullmatch(r"[0-9A-Fa-f]+-[0-9A-Fa-f]+-[0-9]+", snapshot):
            raise RecoveryError()
        arguments += ["--snapshot", snapshot]
    try:
        _native(pg_binary("pg_dump"), arguments, source.url)
        archive.chmod(0o600)
    except Exception:
        archive.unlink(missing_ok=True)
        raise RecoveryError() from None


def _table_lock(connection, mode):
    # Names come exclusively from registered repository metadata, not user data.
    names = ", ".join('"' + table.name + '"' for table in Base.metadata.sorted_tables)
    connection.execute(text("SET LOCAL lock_timeout = '3000ms'"))
    connection.execute(text("SET LOCAL statement_timeout = '10000ms'"))
    connection.execute(text(f"LOCK TABLE {names} IN {mode} MODE"))


class QuarantinedRestore:
    def __init__(self, source: Engine, target: Engine, artifact_root: Path):
        _synthetic(source.url)
        _synthetic(target.url)
        if source.url == target.url or not artifact_root.is_dir() or any(artifact_root.iterdir()):
            raise RecoveryError()
        self._source = source
        self._target = target
        self._root = artifact_root
        self.released = False
        self.counts = {}

    def reconcile(self) -> Engine:
        self.released = False
        try:
            # Freeze current authoritative primary, including legacy Undo/retention.
            # Locks wait for prior writers; current READ COMMITTED reads then see commits.
            with self._source.begin() as current, Session(self._target) as db, db.begin():
                _table_lock(current, "SHARE")
                _table_lock(db, "SHARE ROW EXCLUSIVE")
                if any(self._root.iterdir()):
                    raise RecoveryError()
                owners = set(db.scalars(select(User.id)))
                if not owners <= set(current.scalars(select(User.id))):
                    raise RecoveryError()
                # Agent fences live on AgentRun, not Memory receipts. A missing
                # post-backup key could re-execute an old consent/save request.
                # Recovering its run/messages beyond the backup is outside scope.
                run_columns = (
                    AgentRun.user_id,
                    AgentRun.conversation_id,
                    AgentRun.operation_key,
                    AgentRun.id,
                    AgentRun.request_fingerprint,
                )
                keyed = select(*run_columns).where(
                    AgentRun.user_id.in_(owners), AgentRun.operation_key.is_not(None)
                )
                if not set(current.execute(keyed)) <= set(db.execute(keyed)):
                    raise RecoveryError()
                columns = (
                    "owner_user_id",
                    "id",
                    "subject_id",
                    "person_id",
                    "relationship_id",
                    "type",
                    "content_hash",
                    "expires_at",
                )
                authoritative = {
                    (row.owner_user_id, row.id): tuple(row)
                    for row in current.execute(
                        select(*(getattr(MemoryRecordRow, k) for k in columns))
                    )
                }
                removed = 0
                retained = set()
                for row in db.execute(select(*(getattr(MemoryRecordRow, k) for k in columns))):
                    key = (row.owner_user_id, row.id)
                    if key not in authoritative:
                        removed += db.execute(
                            delete(MemoryRecordRow).where(
                                MemoryRecordRow.id == row.id,
                                MemoryRecordRow.owner_user_id == row.owner_user_id,
                            )
                        ).rowcount
                    elif tuple(row) != authoritative[key]:
                        raise RecoveryError()
                    else:
                        retained.add(row.id)
                # Protect key fencing: an older target receipt must still exist unchanged
                # in the complete authoritative source. Missing history cannot be inferred.
                receipts = list(current.execute(select(MemoryMutationRow.__table__)).mappings())
                by_id = {row["id"]: dict(row) for row in receipts}
                for row in db.execute(select(MemoryMutationRow.__table__)).mappings():
                    if by_id.get(row["id"]) != dict(row):
                        raise RecoveryError()
                for model, predicate in (
                    (MemoryMutationRow, lambda row: row["owner_user_id"] in owners),
                    (MemoryControlRow, lambda row: row["user_id"] in owners),
                    (
                        MemoryOperationRow,
                        lambda row: row["owner_user_id"] in owners and row["record_id"] in retained,
                    ),
                ):
                    rows = [
                        dict(row)
                        for row in current.execute(select(model.__table__)).mappings()
                        if predicate(row)
                    ]
                    db.execute(delete(model))
                    if rows:
                        db.execute(model.__table__.insert(), rows)
                db.execute(delete(MemoryConfirmationRow))
                cancelled = db.execute(
                    update(ChatImportJob)
                    .where(ChatImportJob.status != "imported")
                    .values(status="cancelled", updated_at=datetime.now(UTC))
                ).rowcount
                db.execute(
                    update(ChatImportArtifact).values(state="deleted", updated_at=datetime.now(UTC))
                )
                db.execute(delete(UploadReservation))
                db.execute(delete(AdmissionState))
                db.execute(
                    update(AgentRun)
                    .where(AgentRun.status.in_(["pending", "running"]))
                    .values(
                        status="failed",
                        failure_code="restore_interrupted",
                        completed_at=datetime.now(UTC),
                    )
                )
                counts = {
                    "memory_removed": removed,
                    "memory_retained": len(retained),
                    "pending_imports_cancelled": cancelled,
                    "current_receipts": sum(row["owner_user_id"] in owners for row in receipts),
                }
            # Publish only after commit. This object never creates an API listener.
            self.counts = counts
            self.released = True
            return self._target
        except Exception:
            raise RecoveryError() from None


@contextmanager
def restore_synthetic(source: Engine, archive: Path, artifact_root: Path):
    _synthetic(source.url)
    if not archive.is_file() or archive.is_symlink():
        raise RecoveryError()
    name = "goutou_restore_test_" + uuid4().hex[:12]
    url = source.url.set(database=name)
    admin = create_engine(
        source.url.set(database="postgres"),
        isolation_level="AUTOCOMMIT",
        hide_parameters=True,
        connect_args={"connect_timeout": 3},
    )
    target = None
    created = False
    try:
        with admin.connect() as connection:
            connection.execute(text(f'CREATE DATABASE "{name}"'))
            created = True
        _native(
            pg_binary("pg_restore"),
            [
                "--exit-on-error",
                "--single-transaction",
                "--no-owner",
                "--no-privileges",
                "--dbname",
                name,
                str(archive),
            ],
            url,
        )
        target = create_engine(url, hide_parameters=True, connect_args={"connect_timeout": 3})
        yield QuarantinedRestore(source, target, artifact_root)
    except Exception:
        raise RecoveryError() from None
    finally:
        if target is not None:
            target.dispose()
        if created:
            with admin.connect() as connection:
                connection.execute(
                    text(
                        "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                        "WHERE datname=:name AND pid <> pg_backend_pid()"
                    ),
                    {"name": name},
                )
                connection.execute(text(f'DROP DATABASE "{name}"'))
        admin.dispose()
