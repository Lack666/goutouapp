"""Phase 5C transcript promotion, provenance, atomicity and Agent isolation."""

import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from test_agent_service import queue_safety, service_with_mock

from app.chat_import import ChatImportSource, ImportOptions, WeChatMarkdownParser
from app.db.models import (
    ChatImportJob,
    ChatImportSpeaker,
    Conversation,
    Message,
    RelationshipMessage,
)
from app.db.repositories import records
from app.services.agent_service import actor_from_verified_identity
from app.services.import_jobs import (
    ImportJobError,
    ImportJobErrorCode,
    ImportJobService,
    SpeakerBinding,
)
from app.services.import_merge import (
    ImportMergeError,
    ImportMergeErrorCode,
    ImportMergeService,
    ImportMergeStatus,
    list_relationship_messages,
)


def source(value):
    return ChatImportSource([value])


def parse(value):
    return WeChatMarkdownParser().parse(
        source(value), ImportOptions(source_timezone="Asia/Shanghai", include_messages=False)
    )


def transcript(*entries):
    return "".join(
        f"## 2023-11-09 07:51:{second:02} {label}\n\n{body}\n" for second, label, body in entries
    )


def factory(engine):
    return sessionmaker(bind=engine, expire_on_commit=False)


def ready_job(
    make_session, value, *, actor=None, person_id=None, relationship_id=None, extras=None
):
    with make_session() as db, db.begin():
        if actor is None:
            user = records.create_user(db)
            actor = actor_from_verified_identity(user.id)
        if person_id is None:
            person = records.create_person(db, actor.user_id, "A")
            person_id = person.id
        if relationship_id is None:
            relationship = records.create_relationship(
                db, actor.user_id, person_id, "dating", "active"
            )
            relationship_id = relationship.id
        service = ImportJobService(db)
        job = service.create(actor, parse(value))
        service.set_speaker_binding(actor, job.id, "我", SpeakerBinding.SELF)
        service.set_speaker_binding(actor, job.id, "A", SpeakerBinding.PERSON, person_id)
        for label, binding in (extras or {}).items():
            service.set_speaker_binding(actor, job.id, label, binding)
        service.set_relationship_binding(actor, job.id, relationship_id)
        view = service.mark_ready(actor, job.id)
        return actor, job.id, relationship_id, person_id, view.binding_revision


def merge(make_session, actor, job_id, revision, value):
    return ImportMergeService(make_session).merge(
        actor=actor, job_id=job_id, expected_revision=revision, source=source(value)
    )


def assert_error(code, call):
    with pytest.raises(ImportMergeError) as caught:
        call()
    assert caught.value.code == code


def job_rows(make_session, job_id):
    with make_session() as db:
        job = db.get(ChatImportJob, job_id)
        count = db.scalar(
            select(func.count())
            .select_from(RelationshipMessage)
            .where(RelationshipMessage.import_job_id == job_id)
        )
        return job.status, count


def test_occurrence_sender_policy_receipt_and_replay(database_engine) -> None:
    make_session = factory(database_engine)
    value = transcript(
        (23, "我", "same"),
        (23, "我", "same"),
        (23, "我", "same"),
        (24, "A", "hello"),
        (25, "系统", "notice"),
        (26, "跳过", "irrelevant"),
    )
    actor, job_id, relationship_id, person_id, revision = ready_job(
        make_session, value, extras={"系统": SpeakerBinding.SYSTEM, "跳过": SpeakerBinding.IGNORE}
    )
    receipt = merge(make_session, actor, job_id, revision, value)
    assert receipt.status == ImportMergeStatus.IMPORTED
    assert (
        receipt.imported_message_count,
        receipt.ignored_message_count,
        receipt.system_message_count,
        receipt.new_message_count,
    ) == (5, 1, 1, 5)
    assert receipt.first_timestamp_utc == datetime(2023, 11, 8, 23, 51, 23, tzinfo=UTC)
    with make_session() as db:
        rows = list_relationship_messages(db, actor, relationship_id)
        assert [r.source_index for r in rows] == [1, 2, 3, 4, 5]
        assert [r.sender_kind for r in rows] == ["self", "self", "self", "person", "system"]
        assert all(r.person_id is None for r in rows[:3])
        assert rows[3].person_id == person_id and rows[4].person_id is None
        assert len({r.id for r in rows[:3]}) == 3
        assert len({r.message_fingerprint for r in rows[:3]}) == 1
        assert all(r.timestamp_utc.year == 2023 for r in rows)
        assert (
            db.scalar(
                select(func.count())
                .select_from(Message)
                .join(Conversation)
                .where(Conversation.user_id == actor.user_id)
            )
            == 0
        )
        job = db.get(ChatImportJob, job_id)
        assert job.imported_message_count == 5 and job.ignored_message_count == 1
        with pytest.raises(ImportJobError) as caught:
            ImportJobService(db).set_speaker_binding(actor, job_id, "我", SpeakerBinding.IGNORE)
        assert caught.value.code == ImportJobErrorCode.JOB_IMPORTED
    replay = merge(make_session, actor, job_id, revision, value)
    assert replay.status == ImportMergeStatus.ALREADY_IMPORTED
    assert replay.new_message_count == 0 and replay.imported_at == receipt.imported_at
    assert_error(
        ImportMergeErrorCode.TRANSCRIPT_MISMATCH,
        lambda: merge(
            make_session, actor, job_id, revision, value.replace("irrelevant", "changed")
        ),
    )
    assert job_rows(make_session, job_id) == ("imported", 5)


def test_exact_dataset_dedup_is_scoped_to_relationship(database_engine) -> None:
    make_session = factory(database_engine)
    value = transcript((23, "我", "x"), (24, "A", "y"))
    actor, first, relationship_id, person_id, revision = ready_job(make_session, value)
    merge(make_session, actor, first, revision, value)
    _, duplicate, _, _, duplicate_revision = ready_job(
        make_session, value, actor=actor, person_id=person_id, relationship_id=relationship_id
    )
    duplicate_result = merge(make_session, actor, duplicate, duplicate_revision, value)
    assert duplicate_result.status == ImportMergeStatus.ALREADY_IMPORTED
    assert duplicate_result.dataset_job_id == first and duplicate_result.new_message_count == 0
    assert job_rows(make_session, duplicate) == ("ready", 0)
    with make_session() as db, db.begin():
        other_person = records.create_person(db, actor.user_id, "B")
        other_relationship = records.create_relationship(
            db, actor.user_id, other_person.id, "dating", "active"
        )
        other_id = other_relationship.id
        other_person_id = other_person.id
    _, independent, _, _, independent_revision = ready_job(
        make_session, value, actor=actor, person_id=other_person_id, relationship_id=other_id
    )
    assert (
        merge(make_session, actor, independent, independent_revision, value).new_message_count == 2
    )
    with make_session() as db:
        assert len(list_relationship_messages(db, actor, relationship_id)) == 2
        assert len(list_relationship_messages(db, actor, other_id)) == 2


def test_source_and_parser_metadata_integrity_are_strict(database_engine) -> None:
    make_session = factory(database_engine)
    value = transcript((23, "我", "x"), (24, "A", "y"))
    actor, job_id, _, _, revision = ready_job(make_session, value)
    # Canonical messages remain equal after line-ending normalization, but
    # source bytes no longer match the recorded Job fingerprint.
    assert (
        parse(value).transcript_fingerprint
        == parse(value.replace("\n", "\r\n")).transcript_fingerprint
    )
    assert_error(
        ImportMergeErrorCode.TRANSCRIPT_MISMATCH,
        lambda: merge(make_session, actor, job_id, revision, value.replace("\n", "\r\n")),
    )
    with make_session() as db, db.begin():
        job = db.get(ChatImportJob, job_id)
        job.parser_version = "tampered"
    assert_error(
        ImportMergeErrorCode.TRANSCRIPT_MISMATCH,
        lambda: merge(make_session, actor, job_id, revision, value),
    )
    assert job_rows(make_session, job_id) == ("ready", 0)


def test_mismatch_stale_cancelled_cross_owner_and_tampering(database_engine) -> None:
    make_session = factory(database_engine)
    value = transcript((23, "我", "x"), (24, "A", "y"))
    actor, job_id, relationship_id, person_id, revision = ready_job(make_session, value)
    with make_session() as db, db.begin():
        waiting = ImportJobService(db).create(actor, parse(value))
        waiting_id = waiting.id
    assert_error(
        ImportMergeErrorCode.JOB_NOT_READY,
        lambda: merge(make_session, actor, waiting_id, 0, value),
    )
    assert_error(
        ImportMergeErrorCode.TRANSCRIPT_MISMATCH,
        lambda: merge(
            make_session, actor, job_id, revision, transcript((23, "我", "changed"), (24, "A", "y"))
        ),
    )
    with make_session() as db, db.begin():
        outsider = actor_from_verified_identity(records.create_user(db).id)
    assert_error(
        ImportMergeErrorCode.JOB_NOT_FOUND,
        lambda: merge(make_session, outsider, job_id, revision, value),
    )
    with make_session() as db, db.begin():
        service = ImportJobService(db)
        service.set_speaker_binding(actor, job_id, "我", SpeakerBinding.SELF)
        new_revision = service.mark_ready(actor, job_id).binding_revision
    assert new_revision == revision + 1
    assert_error(
        ImportMergeErrorCode.REVISION_CONFLICT,
        lambda: merge(make_session, actor, job_id, revision, value),
    )
    with make_session() as db, db.begin():
        wrong_person = records.create_person(db, actor.user_id, "wrong")
        wrong_relationship = records.create_relationship(
            db, actor.user_id, wrong_person.id, "dating", "active"
        )
        row = db.get(ChatImportJob, job_id)
        row.bound_relationship_id = wrong_relationship.id
    assert_error(
        ImportMergeErrorCode.BINDING_INVALID,
        lambda: merge(make_session, actor, job_id, new_revision, value),
    )
    with make_session() as db, db.begin():
        row = db.get(ChatImportJob, job_id)
        row.bound_relationship_id = relationship_id
        service = ImportJobService(db)
        service.cancel(actor, job_id)
    assert_error(
        ImportMergeErrorCode.JOB_NOT_READY,
        lambda: merge(make_session, actor, job_id, new_revision, value),
    )
    assert job_rows(make_session, job_id) == ("cancelled", 0)
    with make_session() as db, db.begin():
        speaker = db.scalar(
            select(ChatImportSpeaker).where(
                ChatImportSpeaker.job_id == job_id,
                ChatImportSpeaker.raw_speaker_label == "A",
            )
        )
        assert speaker.person_id == person_id


def test_database_owner_constraint_and_query_scope(database_engine) -> None:
    make_session = factory(database_engine)
    value = transcript((23, "我", "x"), (24, "A", "y"))
    actor, job_id, relationship_id, _, revision = ready_job(make_session, value)
    merge(make_session, actor, job_id, revision, value)
    with make_session() as db, db.begin():
        outsider = actor_from_verified_identity(records.create_user(db).id)
    with make_session() as db:
        assert_error(
            ImportMergeErrorCode.JOB_NOT_FOUND,
            lambda: list_relationship_messages(db, outsider, relationship_id),
        )
        with pytest.raises(IntegrityError), db.begin_nested():
            row = db.scalar(
                select(RelationshipMessage).where(RelationshipMessage.import_job_id == job_id)
            )
            row.owner_user_id = outsider.user_id
            db.flush()


def test_failure_rolls_back_all_rows_and_status(database_engine) -> None:
    make_session = factory(database_engine)
    value = transcript((23, "我", "1"), (24, "A", "2"), (25, "我", "3"))
    actor, job_id, _, _, revision = ready_job(make_session, value)
    with database_engine.begin() as connection:
        connection.execute(
            text(
                "CREATE FUNCTION phase5c_reject_third() RETURNS trigger LANGUAGE plpgsql AS $$ "
                "BEGIN IF NEW.source_index = 3 THEN RAISE EXCEPTION 'synthetic failure'; "
                "END IF; RETURN NEW; END $$"
            )
        )
        connection.execute(
            text(
                "CREATE TRIGGER phase5c_reject_third BEFORE INSERT ON relationship_messages "
                "FOR EACH ROW EXECUTE FUNCTION phase5c_reject_third()"
            )
        )
    try:
        assert_error(
            ImportMergeErrorCode.PERSISTENCE_FAILED,
            lambda: merge(make_session, actor, job_id, revision, value),
        )
        assert job_rows(make_session, job_id) == ("ready", 0)
    finally:
        with database_engine.begin() as connection:
            connection.execute(text("DROP TRIGGER phase5c_reject_third ON relationship_messages"))
            connection.execute(text("DROP FUNCTION phase5c_reject_third()"))


def test_agent_service_history_stays_isolated(database_engine) -> None:
    make_session = factory(database_engine)
    value = transcript((23, "我", "external one"), (24, "A", "external two"))
    actor, job_id, relationship_id, _, revision = ready_job(make_session, value)
    with make_session() as db, db.begin():
        conversation = records.create_conversation(db, actor.user_id, relationship_id)
        conversation_id = conversation.id
    merge(make_session, actor, job_id, revision, value)
    service, provider, spy = service_with_mock(database_engine)
    queue_safety(provider)
    asyncio.run(
        service.execute(actor=actor, conversation_id=conversation_id, message="有人正在伤害我")
    )
    assert spy.requests[0].recent_messages == []
    with make_session() as db:
        assert (
            db.scalar(
                select(func.count())
                .select_from(Message)
                .where(Message.conversation_id == conversation_id)
            )
            == 2
        )
        assert len(list_relationship_messages(db, actor, relationship_id)) == 2


def test_ten_thousand_message_postgres_import(database_engine) -> None:
    make_session = factory(database_engine)
    start = datetime(2023, 11, 9, 7, 51, 23)

    def lines():
        for index in range(10_000):
            stamp = (start + timedelta(seconds=index)).strftime("%Y-%m-%d %H:%M:%S")
            label = "我" if index % 2 == 0 else "A"
            yield f"## {stamp} {label}\n\nsynthetic {index}\n"

    with make_session() as db, db.begin():
        user = records.create_user(db)
        actor = actor_from_verified_identity(user.id)
        person = records.create_person(db, user.id, "A")
        relationship = records.create_relationship(db, user.id, person.id, "dating", "active")
        service = ImportJobService(db)
        result = WeChatMarkdownParser().parse(
            ChatImportSource(lines()),
            ImportOptions(source_timezone="Asia/Shanghai", include_messages=False),
        )
        job = service.create(actor, result)
        service.set_speaker_binding(actor, job.id, "我", SpeakerBinding.SELF)
        service.set_speaker_binding(actor, job.id, "A", SpeakerBinding.PERSON, person.id)
        service.set_relationship_binding(actor, job.id, relationship.id)
        revision = service.mark_ready(actor, job.id).binding_revision
        job_id, relationship_id = job.id, relationship.id
    receipt = ImportMergeService(make_session).merge(
        actor=actor,
        job_id=job_id,
        expected_revision=revision,
        source=ChatImportSource(lines()),
    )
    assert receipt.imported_message_count == receipt.new_message_count == 10_000
    with make_session() as db:
        rows = db.scalars(
            select(RelationshipMessage)
            .where(
                RelationshipMessage.owner_user_id == actor.user_id,
                RelationshipMessage.relationship_id == relationship_id,
            )
            .order_by(RelationshipMessage.source_index)
        )
        first = next(rows)
        assert first.source_index == 1
        assert first.timestamp_utc == datetime(2023, 11, 8, 23, 51, 23, tzinfo=UTC)
        tail = list_relationship_messages(db, actor, relationship_id, limit=3, offset=9997)
        assert [row.source_index for row in tail] == [9998, 9999, 10000]
        assert tail[-1].timestamp_utc == (start + timedelta(seconds=9999, hours=-8)).replace(
            tzinfo=UTC
        )
        assert (
            db.scalar(
                select(func.count())
                .select_from(RelationshipMessage)
                .where(RelationshipMessage.import_job_id == job_id)
            )
            == 10_000
        )
        assert (
            db.scalar(
                select(func.count(func.distinct(RelationshipMessage.source_index))).where(
                    RelationshipMessage.import_job_id == job_id
                )
            )
            == 10_000
        )
        assert (
            db.scalar(
                select(func.max(RelationshipMessage.source_index)).where(
                    RelationshipMessage.import_job_id == job_id
                )
            )
            == 10_000
        )
    replay = ImportMergeService(make_session).merge(
        actor=actor,
        job_id=job_id,
        expected_revision=revision,
        source=ChatImportSource(lines()),
    )
    assert replay.new_message_count == 0
