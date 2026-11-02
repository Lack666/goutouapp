"""Bounded canonical Dataset reads. Does not issue an analysis grant."""

from sqlalchemy import select, tuple_
from sqlalchemy.orm import Session

from app.chat_import.analysis_scope import AnalysisScope, ScopeMessage, utc
from app.db.models import ChatImportJob, RelationshipMessage
from app.db.repositories import records
from app.services.agent_service import AuthenticatedActor


def read_scope(db: Session, actor: AuthenticatedActor, scope: AnalysisScope):
    if not isinstance(actor, AuthenticatedActor) or actor.user_id != scope.owner_id:
        raise ValueError("scope unavailable")
    job = db.scalar(
        select(ChatImportJob)
        .where(
            ChatImportJob.id == scope.dataset_id,
            ChatImportJob.owner_user_id == actor.user_id,
            ChatImportJob.status == "imported",
            ChatImportJob.deleted_at.is_(None),
        )
        .with_for_update()
    )
    if job is None or job.bound_relationship_id is None:
        raise ValueError("scope unavailable")
    relationship = records.get_relationship(db, actor.user_id, job.bound_relationship_id)
    if relationship is None or relationship.person_id != scope.person_id:
        raise ValueError("scope unavailable")
    cursor = None
    total = 0
    body_bytes = 0
    while True:
        query = (
            select(RelationshipMessage)
            .where(
                RelationshipMessage.owner_user_id == actor.user_id,
                RelationshipMessage.import_job_id == scope.dataset_id,
                RelationshipMessage.relationship_id == relationship.id,
                RelationshipMessage.timestamp_utc >= utc(scope.start),
                RelationshipMessage.timestamp_utc < utc(scope.end),
            )
            .order_by(RelationshipMessage.timestamp_utc, RelationshipMessage.id)
            .limit(500)
        )
        if cursor:
            query = query.where(
                tuple_(RelationshipMessage.timestamp_utc, RelationshipMessage.id) > cursor
            )
        rows = list(db.scalars(query))
        if not rows:
            return
        for row in rows:
            total += 1
            body_bytes += len(row.content.encode("utf-8"))
            if total > 10000:
                raise ValueError("source exceeds message limit; no partial scope")
            if body_bytes > 2 * 1024 * 1024:
                raise ValueError("source exceeds byte limit; no partial scope")
            yield ScopeMessage(
                row.id,
                actor.user_id,
                scope.person_id,
                scope.dataset_id,
                row.timestamp_utc,
                row.sender_kind,
                row.content,
                row.content_type,
            )
        cursor = (rows[-1].timestamp_utc, rows[-1].id)
        if len(rows) < 500:
            return
