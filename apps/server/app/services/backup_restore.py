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
    ChatImportSpeaker,
    Conversation,
    ErasureConfirmation,
    ErasureReceipt,
    LifecycleConfirmation,
    LifecycleReceipt,
    MemoryConfirmationRow,
    MemoryControlRow,
    MemoryMutationRow,
    MemoryOperationRow,
    MemoryRecordRow,
    Message,
    Person,
    Relationship,
    RelationshipMessage,
    RunRecoveryReceipt,
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
                # A frozen SQL snapshot cannot stop a live executor or Provider.
                # Unacknowledged writers require the separate OS-proof recovery path.
                if current.scalar(
                    select(AgentRun.id)
                    .where(
                        AgentRun.user_id.in_(owners),
                        AgentRun.writer_token.is_not(None),
                        AgentRun.writer_released.is_(False),
                        AgentRun.recovered_at.is_(None),
                    )
                    .limit(1)
                ):
                    raise RecoveryError()
                # A bare recovered_at flag cannot substitute for a writer proof.
                recovered = current.execute(
                    select(
                        AgentRun.id,
                        AgentRun.user_id,
                        AgentRun.conversation_id,
                        AgentRun.writer_token,
                        AgentRun.writer_scope,
                        AgentRun.recovered_at,
                        AgentRun.status,
                        AgentRun.failure_code,
                    ).where(AgentRun.user_id.in_(owners), AgentRun.recovered_at.is_not(None))
                )
                for run in recovered:
                    if (
                        run.status != "failed"
                        or run.failure_code != "writer_stopped"
                        or not current.scalar(
                            select(RunRecoveryReceipt.id).where(
                                RunRecoveryReceipt.run_id == run.id,
                                RunRecoveryReceipt.owner_user_id == run.user_id,
                                RunRecoveryReceipt.conversation_id == run.conversation_id,
                                RunRecoveryReceipt.writer_token == run.writer_token,
                                RunRecoveryReceipt.writer_scope == run.writer_scope,
                                RunRecoveryReceipt.performed_at == run.recovered_at,
                            )
                        )
                    ):
                        raise RecoveryError()
                erased_owners, erased_relationships = set(), set()
                for model, owner_column, identity_columns in (
                    (User, User.id, ()),
                    (Person, Person.user_id, ()),
                    (Relationship, Relationship.user_id, (Relationship.person_id,)),
                ):
                    columns = (model.id, owner_column, *identity_columns, model.deleted_at)
                    authoritative_profiles = {
                        row[0]: tuple(row)
                        for row in current.execute(select(*columns).where(owner_column.in_(owners)))
                    }
                    restored_profiles = {
                        row[0]: tuple(row)
                        for row in db.execute(select(*columns).where(owner_column.in_(owners)))
                    }
                    for target_id, old in restored_profiles.items():
                        live = authoritative_profiles.get(target_id)
                        if live is None or old[:-1] != live[:-1]:
                            raise RecoveryError()
                        if old[-1] is not None and old[-1] != live[-1]:
                            raise RecoveryError()
                    for target_id, live in authoritative_profiles.items():
                        if live[-1] is None:
                            continue
                        if target_id not in restored_profiles:
                            raise RecoveryError()
                        values = {"deleted_at": live[-1], "updated_at": live[-1]}
                        if model is Person:
                            values["display_name"] = ""
                        elif model is Relationship:
                            values.update(relationship_type="erased", status="erased")
                            erased_relationships.add(target_id)
                        else:
                            erased_owners.add(target_id)
                        db.execute(update(model).where(model.id == target_id).values(**values))
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
                # Exact immutable resource IDs from the frozen primary; no replay
                # of a broad historical scope. Missing post-backup tombstone fences
                # cannot safely be reconstructed and keep this restore quarantined.
                erased_counts = {"dataset_messages_removed": 0, "agent_messages_removed": 0}
                for model, owner_column, scope_columns in (
                    (Conversation, Conversation.user_id, (Conversation.relationship_id,)),
                    (
                        ChatImportJob,
                        ChatImportJob.owner_user_id,
                        (ChatImportJob.bound_relationship_id, ChatImportJob.transcript_fingerprint),
                    ),
                ):
                    columns = (model.id, owner_column, *scope_columns, model.deleted_at)
                    authoritative_targets = {
                        row[0]: tuple(row)
                        for row in current.execute(select(*columns).where(owner_column.in_(owners)))
                    }
                    restored_targets = {
                        row[0]: tuple(row)
                        for row in db.execute(select(*columns).where(owner_column.in_(owners)))
                    }
                    for target_id, row in restored_targets.items():
                        now_row = authoritative_targets.get(target_id)
                        if now_row is None or row[:-1] != now_row[:-1]:
                            raise RecoveryError()
                        if row[-1] is not None and row[-1] != now_row[-1]:
                            raise RecoveryError()
                    for target_id, row in authoritative_targets.items():
                        if row[-1] is None:
                            continue
                        if target_id not in restored_targets:
                            raise RecoveryError()
                        parent_erased = model is ChatImportJob and (
                            row[1] in erased_owners or row[2] in erased_relationships
                        )
                        if (
                            model is ChatImportJob
                            and not parent_erased
                            and (
                                db.get(ChatImportJob, target_id).status != "imported"
                                or current.scalar(
                                    select(ChatImportJob.status).where(
                                        ChatImportJob.id == target_id
                                    )
                                )
                                != "imported"
                            )
                        ):
                            # deleted_at alone is insufficient: the partial unique
                            # index/replay fence exists only on canonical imported
                            # Jobs. A ready pre-import backup cannot be released.
                            raise RecoveryError()
                        if model is Conversation:
                            erased_counts["agent_messages_removed"] += db.execute(
                                delete(Message).where(Message.conversation_id == target_id)
                            ).rowcount
                            db.execute(
                                update(AgentRun)
                                .where(AgentRun.conversation_id == target_id)
                                .values(memory_status=None, result_warnings=None)
                            )
                        else:
                            erased_counts["dataset_messages_removed"] += db.execute(
                                delete(RelationshipMessage).where(
                                    RelationshipMessage.import_job_id == target_id,
                                    RelationshipMessage.owner_user_id == row[1],
                                    RelationshipMessage.relationship_id == row[2],
                                )
                            ).rowcount
                            db.execute(
                                delete(ChatImportSpeaker).where(
                                    ChatImportSpeaker.job_id == target_id,
                                    ChatImportSpeaker.owner_user_id == row[1],
                                )
                            )
                        db.execute(
                            update(model)
                            .where(model.id == target_id)
                            .values(deleted_at=row[-1], updated_at=row[-1])
                        )
                erasure_receipts = list(
                    current.execute(select(ErasureReceipt.__table__)).mappings()
                )
                authoritative_receipts = {row["id"]: dict(row) for row in erasure_receipts}
                for row in db.execute(select(ErasureReceipt.__table__)).mappings():
                    if authoritative_receipts.get(row["id"]) != dict(row):
                        raise RecoveryError()
                db.execute(delete(ErasureReceipt))
                copied = [dict(row) for row in erasure_receipts if row["owner_user_id"] in owners]
                if copied:
                    db.execute(ErasureReceipt.__table__.insert(), copied)
                db.execute(delete(ErasureConfirmation))
                for model in (LifecycleReceipt, RunRecoveryReceipt):
                    authoritative_rows = {
                        row["id"]: dict(row)
                        for row in current.execute(select(model.__table__)).mappings()
                    }
                    for row in db.execute(select(model.__table__)).mappings():
                        if authoritative_rows.get(row["id"]) != dict(row):
                            raise RecoveryError()
                    db.execute(delete(model))
                    rows = [r for r in authoritative_rows.values() if r["owner_user_id"] in owners]
                    if rows:
                        db.execute(model.__table__.insert(), rows)
                db.execute(delete(LifecycleConfirmation))
                for receipt in current.execute(select(RunRecoveryReceipt.__table__)).mappings():
                    if receipt["owner_user_id"] not in owners:
                        continue
                    live = (
                        current.execute(
                            select(AgentRun.__table__).where(AgentRun.id == receipt["run_id"])
                        )
                        .mappings()
                        .one_or_none()
                    )
                    restored = db.get(AgentRun, receipt["run_id"])
                    if (
                        live is None
                        or restored is None
                        or live["status"] != "failed"
                        or live["failure_code"] != "writer_stopped"
                        or live["recovered_at"] != receipt["performed_at"]
                        or restored.conversation_id != receipt["conversation_id"]
                        or restored.user_id != receipt["owner_user_id"]
                    ):
                        raise RecoveryError()
                    # Never invent post-backup answers or inferred Memory success.
                    for field in ("user_message_id", "assistant_message_id"):
                        if getattr(restored, field) != live[field]:
                            raise RecoveryError()
                    db.execute(
                        update(AgentRun)
                        .where(AgentRun.id == restored.id)
                        .values(
                            status="failed",
                            failure_code="writer_stopped",
                            recovered_at=live["recovered_at"],
                            completed_at=live["completed_at"],
                            writer_token=live["writer_token"],
                            writer_scope=live["writer_scope"],
                            writer_released=live["writer_released"],
                        )
                    )
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
                    **erased_counts,
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
