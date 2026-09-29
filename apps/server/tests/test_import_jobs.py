"""Phase 5B durable workflow, explicit identity, and owner-scope regression."""

from dataclasses import replace
from datetime import timedelta

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.chat_import import ChatImportSource, ImportOptions, WeChatMarkdownParser
from app.db.models import ChatImportJob, ChatImportSpeaker, Conversation, Message
from app.db.repositories import records
from app.services.agent_service import actor_from_verified_identity
from app.services.import_jobs import (
    ImportJobError,
    ImportJobErrorCode,
    ImportJobService,
    ImportJobStatus,
    SpeakerBinding,
)


def parsed(*labels: str):
    text = "".join(
        f"## 2023-11-09 07:51:{index:02} {label}\n\nsynthetic {index}\n"
        for index, label in enumerate(labels)
    )
    return WeChatMarkdownParser().parse(
        ChatImportSource([text]),
        ImportOptions(source_timezone="Asia/Shanghai", include_messages=False),
    )


def owner(db: Session):
    user = records.create_user(db)
    return actor_from_verified_identity(user.id)


def assert_error(code: ImportJobErrorCode, call) -> None:
    with pytest.raises(ImportJobError) as caught:
        call()
    assert caught.value.code == code


def owner_message_count(db: Session, user_id) -> int:
    return (
        db.scalar(
            select(func.count())
            .select_from(Message)
            .join(Conversation)
            .where(Conversation.user_id == user_id)
        )
        or 0
    )


def test_explicit_binding_readiness_and_no_message_write(db_session: Session) -> None:
    actor = owner(db_session)
    other = owner(db_session)
    person = records.create_person(db_session, actor.user_id, "怡宝🥰")
    relationship = records.create_relationship(
        db_session, actor.user_id, person.id, "dating", "active"
    )
    service = ImportJobService(db_session)
    initial = service.create(actor, parsed("我", "怡宝🥰"))
    assert initial.status == ImportJobStatus.AWAITING_BINDING
    assert [(s.raw_speaker_label, s.message_count, s.binding_kind) for s in initial.speakers] == [
        ("我", 1, SpeakerBinding.UNBOUND),
        ("怡宝🥰", 1, SpeakerBinding.UNBOUND),
    ]
    assert "exactly_one_self_required" in initial.readiness_issues
    assert "exactly_one_primary_person_required" in initial.readiness_issues
    assert_error(ImportJobErrorCode.NOT_READY, lambda: service.mark_ready(actor, initial.id))
    assert_error(ImportJobErrorCode.JOB_NOT_FOUND, lambda: service.inspect(other, initial.id))
    assert_error(ImportJobErrorCode.JOB_NOT_FOUND, lambda: service.cancel(other, initial.id))
    assert_error(
        ImportJobErrorCode.SPEAKER_NOT_FOUND,
        lambda: service.set_speaker_binding(actor, initial.id, "invented", SpeakerBinding.SELF),
    )
    service.set_speaker_binding(actor, initial.id, "我", SpeakerBinding.SELF, expected_revision=0)
    assert_error(
        ImportJobErrorCode.REVISION_CONFLICT,
        lambda: service.set_speaker_binding(
            actor, initial.id, "怡宝🥰", SpeakerBinding.PERSON, person.id, expected_revision=0
        ),
    )
    service.set_speaker_binding(actor, initial.id, "怡宝🥰", SpeakerBinding.PERSON, person.id)
    service.set_relationship_binding(actor, initial.id, relationship.id)
    ready = service.mark_ready(actor, initial.id)
    assert ready.status == ImportJobStatus.READY
    assert ready.readiness_issues == ()
    assert ready.binding_revision == 3
    assert owner_message_count(db_session, actor.user_id) == 0
    changed = service.set_speaker_binding(actor, initial.id, "我", SpeakerBinding.SELF)
    assert changed.status == ImportJobStatus.AWAITING_BINDING
    assert changed.updated_at >= ready.updated_at
    assert service.mark_ready(actor, initial.id).status == ImportJobStatus.READY
    cancelled = service.cancel(actor, initial.id)
    assert cancelled.status == ImportJobStatus.CANCELLED
    assert_error(ImportJobErrorCode.JOB_CANCELLED, lambda: service.mark_ready(actor, initial.id))
    assert owner_message_count(db_session, actor.user_id) == 0


def test_group_policy_system_ignore_and_relationship_mismatch(db_session: Session) -> None:
    actor = owner(db_session)
    a = records.create_person(db_session, actor.user_id, "A")
    b = records.create_person(db_session, actor.user_id, "B")
    relationship_a = records.create_relationship(
        db_session, actor.user_id, a.id, "dating", "active"
    )
    relationship_b = records.create_relationship(
        db_session, actor.user_id, b.id, "dating", "active"
    )
    service = ImportJobService(db_session)
    job = service.create(actor, parsed("我", "A", "B"))
    service.set_speaker_binding(actor, job.id, "我", SpeakerBinding.SELF)
    service.set_speaker_binding(actor, job.id, "A", SpeakerBinding.PERSON, a.id)
    service.set_relationship_binding(actor, job.id, relationship_b.id)
    assert "unbound_speakers" in service.validate_readiness(actor, job.id)
    service.set_speaker_binding(actor, job.id, "B", SpeakerBinding.PERSON, b.id)
    assert "unsupported_group_binding" in service.validate_readiness(actor, job.id)
    service.set_speaker_binding(actor, job.id, "B", SpeakerBinding.SYSTEM)
    assert "relationship_person_mismatch" in service.validate_readiness(actor, job.id)
    service.set_relationship_binding(actor, job.id, relationship_a.id)
    assert service.mark_ready(actor, job.id).status == ImportJobStatus.READY
    service.set_speaker_binding(actor, job.id, "B", SpeakerBinding.IGNORE)
    assert service.mark_ready(actor, job.id).status == ImportJobStatus.READY


def test_fatal_duplicate_and_bounded_issue_metadata(db_session: Session) -> None:
    actor = owner(db_session)
    service = ImportJobService(db_session)
    result = parsed("我", "A")
    assert_error(
        ImportJobErrorCode.FATAL_PARSE_RESULT,
        lambda: service.create(actor, replace(result, fatal_count=1)),
    )
    first = service.create(actor, result)
    second = service.create(actor, result)
    assert first.id != second.id
    assert second.possible_duplicate_job_id == first.id
    assert second.issue_code_samples == ()
    assert (
        db_session.scalar(
            select(func.count())
            .select_from(ChatImportJob)
            .where(ChatImportJob.owner_user_id == actor.user_id)
        )
        == 2
    )


def test_warning_flood_has_bounded_parser_and_job_metadata(db_session: Session) -> None:
    actor = owner(db_session)
    transcript = ("## 2023-11-09 07:51:23 我\n\nsynthetic\n" for _ in range(2000))
    result = WeChatMarkdownParser().parse(
        ChatImportSource(transcript),
        ImportOptions(source_timezone="Asia/Shanghai", include_messages=False, max_issue_records=7),
    )
    assert result.warning_count == 1999
    assert len(result.issues) == 7
    assert result.issues_truncated == 1992
    job = ImportJobService(db_session).create(actor, result)
    assert job.warning_count == 1999
    assert job.issues_truncated == 1992
    assert job.issue_code_samples == ("duplicate_timestamp",)


def test_owner_scoped_fk_constraints(db_session: Session) -> None:
    actor_a = owner(db_session)
    actor_b = owner(db_session)
    person_b = records.create_person(db_session, actor_b.user_id, "B")
    relationship_b = records.create_relationship(
        db_session, actor_b.user_id, person_b.id, "dating", "active"
    )
    service = ImportJobService(db_session)
    job = service.create(actor_a, parsed("我", "A"))
    assert_error(
        ImportJobErrorCode.PERSON_NOT_FOUND,
        lambda: service.set_speaker_binding(
            actor_a, job.id, "A", SpeakerBinding.PERSON, person_b.id
        ),
    )
    assert_error(
        ImportJobErrorCode.RELATIONSHIP_NOT_FOUND,
        lambda: service.set_relationship_binding(actor_a, job.id, relationship_b.id),
    )
    speaker = db_session.scalar(select(ChatImportSpeaker).where(ChatImportSpeaker.job_id == job.id))
    assert speaker is not None
    with pytest.raises(IntegrityError), db_session.begin_nested():
        speaker.binding_kind = SpeakerBinding.PERSON.value
        speaker.person_id = person_b.id
        db_session.flush()
    db_session.expire(speaker)
    with pytest.raises(IntegrityError), db_session.begin_nested():
        job_row = db_session.get(ChatImportJob, job.id)
        assert job_row is not None
        job_row.bound_relationship_id = relationship_b.id
        db_session.flush()
    with pytest.raises(IntegrityError), db_session.begin_nested():
        db_session.add(
            ChatImportSpeaker(
                owner_user_id=actor_b.user_id,
                job_id=job.id,
                raw_speaker_label="forged",
                source_order=2,
                message_count=1,
                binding_kind="unbound",
            )
        )
        db_session.flush()


def test_persists_across_sessions(database_engine) -> None:
    with Session(database_engine) as db:
        actor = owner(db)
        person = records.create_person(db, actor.user_id, "A")
        relationship = records.create_relationship(db, actor.user_id, person.id, "dating", "active")
        service = ImportJobService(db)
        job = service.create(actor, parsed("我", "A"))
        service.set_speaker_binding(actor, job.id, "我", SpeakerBinding.SELF)
        service.set_speaker_binding(actor, job.id, "A", SpeakerBinding.PERSON, person.id)
        service.set_relationship_binding(actor, job.id, relationship.id)
        service.mark_ready(actor, job.id)
        db.commit()
    with Session(database_engine) as db:
        persisted = ImportJobService(db).inspect(actor, job.id)
        assert persisted.status == ImportJobStatus.READY
        assert [s.binding_kind for s in persisted.speakers] == [
            SpeakerBinding.SELF,
            SpeakerBinding.PERSON,
        ]
        assert persisted.created_at.utcoffset() == timedelta(0)
        assert owner_message_count(db, actor.user_id) == 0
