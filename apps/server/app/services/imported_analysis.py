"""ICA-A authority. Owner lock precedes Dataset lock, matching deletion services."""

import hashlib
import hmac
import json
import secrets
from contextlib import contextmanager
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import select, update

from app.chat_import.analysis_scope import (
    AnalysisScope,
    budget_plan,
    calendar_window,
    prepare_context,
    preview,
    validate_evidence,
)
from app.db.models import ChatImportJob, ImportedAnalysisGrant, RelationshipMessage, User
from app.db.repositories import records
from app.schemas.imported_analysis import AnalysisGrantView, AnalysisPreparation, EvidenceView
from app.services.agent_service import AuthenticatedActor
from app.services.imported_scope import read_scope


class AnalysisError(Exception):
    def __init__(self, code="scope_unavailable"):
        self.code = code
        super().__init__(code)


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, default=str, ensure_ascii=True).encode()
    ).hexdigest()


def invalidate_datasets(db, dataset_ids, *, status="deleted"):
    db.execute(
        update(ImportedAnalysisGrant)
        .where(ImportedAnalysisGrant.dataset_id.in_(dataset_ids))
        .values(status=status, payload={}, token_hash="")
    )


class ImportedAnalysisService:
    def __init__(self, sessions, *, clock=lambda: datetime.now(UTC)):
        self.sessions, self.clock = sessions, clock

    @contextmanager
    def transaction(self, actor):
        if not isinstance(actor, AuthenticatedActor):
            raise AnalysisError()
        with self.sessions() as db, db.begin():
            owner = db.scalar(
                select(User)
                .where(User.id == actor.user_id, User.deleted_at.is_(None))
                .with_for_update(key_share=True)
            )
            if owner is None:
                raise AnalysisError()
            yield db

    def materialize(self, db, actor, body, prepared_at):
        job = db.scalar(
            select(ChatImportJob)
            .where(
                ChatImportJob.id == body.dataset_id,
                ChatImportJob.owner_user_id == actor.user_id,
                ChatImportJob.status == "imported",
                ChatImportJob.deleted_at.is_(None),
            )
            .with_for_update()
        )
        relationship = records.get_relationship(db, actor.user_id, body.relationship_id)
        if (
            job is None
            or relationship is None
            or job.bound_relationship_id != relationship.id
            or relationship.person_id != body.person_id
            or records.get_person(db, actor.user_id, body.person_id) is None
        ):
            raise AnalysisError()
        try:
            windows = [
                calendar_window(body.timezone, prepared_at, **w.model_dump()) for w in body.windows
            ]
            windows.sort()
            if any(end - start > timedelta(days=367) for start, end in windows):
                raise AnalysisError("scope_or_budget_rejected")
            if len(windows) == 2 and windows[0][1] > windows[1][0]:
                raise AnalysisError("overlapping_windows")
            contexts = []
            for start, end in windows:
                scope = AnalysisScope(
                    actor.user_id, body.person_id, body.dataset_id, body.timezone, start, end
                )
                contexts.append(prepare_context(scope, list(read_scope(db, actor, scope))))
        except (ValueError, KeyError) as exc:
            raise AnalysisError("scope_or_budget_rejected") from exc
        total = sum(len(c.messages) for c in contexts)
        total_bytes = sum(sum(m.size for m in c.messages) for c in contexts)
        k = sum(len(c.chunks) for c in contexts)
        if total > 10000 or total_bytes > 2 * 1024 * 1024 or k > 32:
            raise AnalysisError("scope_or_budget_rejected")
        plans = [
            budget_plan(
                c,
                prompt_reserve_bytes=16384 + len(json.dumps(body.question).encode()),
                max_output_tokens=8192,
                price_per_million=0,
            )
            for c in contexts
        ]
        token_cap = sum(p["token_cap"] for p in plans)
        requests = 3 * k + 8
        if token_cap > body.max_tokens or requests > body.max_requests:
            raise AnalysisError("scope_or_budget_rejected")
        summaries, manifests, aliases = [], [], {}
        selected_ids = [m.id for c in contexts for m in c.messages]
        sources = {}
        for offset in range(0, len(selected_ids), 500):
            sources.update(
                {
                    r.id: r
                    for r in db.scalars(
                        select(RelationshipMessage).where(
                            RelationshipMessage.owner_user_id == actor.user_id,
                            RelationshipMessage.import_job_id == body.dataset_id,
                            RelationshipMessage.id.in_(selected_ids[offset : offset + 500]),
                        )
                    )
                }
            )
        for window_index, context in enumerate(contexts):
            summary = preview(context)
            start, end = windows[window_index]
            zone = ZoneInfo(body.timezone)
            first_day, last_day = start.astimezone(zone).date(), end.astimezone(zone).date()
            day = first_day
            daily = {}
            while day <= last_day:
                daily[day.isoformat()] = {"self": 0, "person": 0, "system": 0}
                day += timedelta(days=1)
            for message in context.messages:
                key = message.timestamp.astimezone(zone).date().isoformat()
                daily[key][message.speaker] += 1
            summary.update(
                start=start.isoformat(),
                end=end.isoformat(),
                daily=daily,
                analyzable_text=sum(
                    m.content_type == "text" and m.speaker != "system" for m in context.messages
                ),
                system=sum(m.speaker == "system" for m in context.messages),
                media=sum(
                    m.content_type != "text" and m.speaker != "system" for m in context.messages
                ),
                export_gaps="unknown; unexported messages cannot be inferred absent",
                parser_warnings=job.warning_count,
                parser_errors=job.error_count,
                ignored_source_messages=job.ignored_message_count,
                skipped_source_items="not reconstructible from canonical import; see parser issues",
            )
            summaries.append(summary)
            for chunk in context.chunks:
                manifests.append(
                    json.loads(
                        json.dumps(
                            {
                                **asdict(chunk),
                                "window": window_index,
                                "stages": {
                                    s: "pending"
                                    for s in ("safety", "interaction", "counterevidence")
                                },
                            },
                            default=str,
                        )
                    )
                )
            for message in context.messages:
                alias = f"w{window_index}-m{len(aliases) + 1:05d}"
                row = sources[message.id]
                aliases[alias] = {
                    "id": str(message.id),
                    "window": window_index,
                    "source_hash": digest(
                        [
                            row.message_fingerprint,
                            row.source_index,
                            row.raw_speaker_label,
                            row.person_id,
                            row.source_line_start,
                            row.source_line_end,
                            row.external_message_id,
                            row.external_reply_id,
                            row.external_message_type,
                            row.content,
                            row.timestamp_utc,
                            row.sender_kind,
                            row.content_type,
                        ]
                    ),
                }
        payload = {
            "request": body.model_dump(mode="json"),
            "prepared_at": prepared_at.isoformat(),
            "source": digest(
                [
                    job.source_fingerprint,
                    job.transcript_fingerprint,
                    job.binding_revision,
                    job.updated_at,
                    job.parser_version,
                    job.source_timezone,
                ]
            ),
            "preview": {
                "windows": summaries,
                "messages": total,
                "body_bytes": total_bytes,
                "chunks": k,
                "planned_requests": requests,
                "token_cap": token_cap,
                "cost_cap": None,
                "price_status": "unquoted; execution prohibited until priced",
                "provider_calls": 0,
                "memory_access": False,
            },
            "manifests": manifests,
            "aliases": aliases,
        }
        return payload, contexts

    def prepare(self, actor, body):
        with self.transaction(actor) as db:
            payload, _ = self.materialize(db, actor, body, self.clock())
            token = secrets.token_urlsafe(32)
            row = ImportedAnalysisGrant(
                owner_user_id=actor.user_id,
                dataset_id=body.dataset_id,
                relationship_id=body.relationship_id,
                person_id=body.person_id,
                status="prepared",
                token_hash=digest(token),
                binding_hash=digest(payload),
                expires_at=self.clock() + timedelta(minutes=5),
                payload=payload,
            )
            db.add(row)
            db.flush()
            return AnalysisPreparation(
                preparation_id=row.id,
                challenge=token,
                binding_hash=row.binding_hash,
                expires_at=row.expires_at,
                preview=payload["preview"],
            )

    def owned(self, db, actor, grant_id):
        row = db.scalar(
            select(ImportedAnalysisGrant).where(
                ImportedAnalysisGrant.id == grant_id,
                ImportedAnalysisGrant.owner_user_id == actor.user_id,
            )
        )
        if row is None:
            raise AnalysisError()
        return row

    def current(self, db, actor, row, *, prepared=False):
        from app.schemas.imported_analysis import AnalysisPrepare

        if (
            row.status != ("prepared" if prepared else "confirmed")
            or row.expires_at <= self.clock()
        ):
            raise AnalysisError("grant_inactive")
        payload, contexts = self.materialize(
            db,
            actor,
            AnalysisPrepare.model_validate(row.payload["request"]),
            datetime.fromisoformat(row.payload["prepared_at"]),
        )
        if not hmac.compare_digest(digest(payload), row.binding_hash):
            raise AnalysisError("source_changed")
        return contexts

    @staticmethod
    def view(row):
        return AnalysisGrantView(
            grant_id=row.id,
            status=row.status,
            expires_at=row.expires_at,
            binding_hash=row.binding_hash,
            preview=row.payload.get("preview", {}),
            manifests=row.payload.get("manifests", []),
            evidence_aliases={
                k: {"message_id": v["id"], "window": v["window"]}
                for k, v in row.payload.get("aliases", {}).items()
            },
        )

    def confirm(self, actor, body):
        with self.transaction(actor) as db:
            prior = db.scalar(
                select(ImportedAnalysisGrant).where(
                    ImportedAnalysisGrant.owner_user_id == actor.user_id,
                    ImportedAnalysisGrant.operation_key == body.operation_key,
                )
            )
            fingerprint = digest(body.model_dump(mode="json"))
            if prior:
                if prior.confirmation_hash != fingerprint:
                    raise AnalysisError("idempotency_conflict")
                self.current(db, actor, prior)
                return self.view(prior)
            row = self.owned(db, actor, body.preparation_id)
            if not hmac.compare_digest(
                row.token_hash, digest(body.challenge)
            ) or not hmac.compare_digest(row.binding_hash, body.binding_hash):
                raise AnalysisError("challenge_mismatch")
            self.current(db, actor, row, prepared=True)
            row.status, row.confirmed_at = "confirmed", self.clock()
            row.expires_at = self.clock() + timedelta(hours=24)
            row.operation_key, row.confirmation_hash = body.operation_key, fingerprint
            return self.view(row)

    def inspect(self, actor, grant_id):
        with self.transaction(actor) as db:
            row = self.owned(db, actor, grant_id)
            self.current(db, actor, row)
            return self.view(row)

    def revoke(self, actor, grant_id):
        with self.transaction(actor) as db:
            row = self.owned(db, actor, grant_id)
            row.status, row.payload, row.token_hash = "revoked", {}, ""
            return self.view(row)

    def evidence(self, actor, grant_id, alias, start, end, quote):
        with self.transaction(actor) as db:
            row = self.owned(db, actor, grant_id)
            contexts = self.current(db, actor, row)
            ref = row.payload["aliases"].get(alias)
            if ref is None:
                raise AnalysisError("evidence_unavailable")
            try:
                message = validate_evidence(
                    contexts[ref["window"]], UUID(ref["id"]), start, end, quote
                )
            except ValueError as exc:
                raise AnalysisError("evidence_unavailable") from exc
            source = db.get(RelationshipMessage, message.id)
            return EvidenceView(
                alias=alias,
                message_id=message.id,
                dataset_id=row.dataset_id,
                source_index=source.source_index,
                speaker=message.speaker,
                timestamp=message.timestamp,
                content=message.content,
                quote=quote,
                line_start=source.source_line_start,
                line_end=source.source_line_end,
                external_message_id=source.external_message_id,
                external_reply_id=source.external_reply_id,
            )

    def cleanup(self):
        # Owner serialization also protects confirm/revoke/deletion against TTL cleanup.
        with self.sessions() as db:
            owners = list(
                db.scalars(
                    select(ImportedAnalysisGrant.owner_user_id)
                    .where(
                        ImportedAnalysisGrant.expires_at <= self.clock(),
                        ImportedAnalysisGrant.status.in_(["prepared", "confirmed"]),
                    )
                    .distinct()
                    .limit(100)
                )
            )
        for owner in owners:
            with self.sessions() as db, db.begin():
                db.scalar(select(User).where(User.id == owner).with_for_update(key_share=True))
                db.execute(
                    update(ImportedAnalysisGrant)
                    .where(
                        ImportedAnalysisGrant.owner_user_id == owner,
                        ImportedAnalysisGrant.expires_at <= self.clock(),
                        ImportedAnalysisGrant.status.in_(["prepared", "confirmed"]),
                    )
                    .values(status="expired", payload={}, token_hash="")
                )
