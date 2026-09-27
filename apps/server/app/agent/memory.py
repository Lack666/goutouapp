"""Owner-scoped, consent-gated long-term memory without database dependencies."""

import hashlib
import re
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID, uuid4

from app.agent.contracts import (
    Fact,
    MemoryCandidate,
    MemoryControl,
    MemoryDecision,
    MemoryReceipt,
    MemoryRecord,
    MemoryWriteStatus,
)

MAX_TOTAL = 200
RECALL_LIMIT = 8
ALLOWED_TYPES = frozenset({"user", "object", "relationship"})
BLOCKED_CONTENT = re.compile(
    r"(?:身份证|住址|密码|口令|验证码|api[_ -]?key|access[_ -]?token|"
    r"整份聊天|聊天记录|完整对话|chain.of.thought|系统提示|system prompt|"
    r"我明确同意|长期关系档案|\b\d{15}(?:\d{2}[0-9Xx])?\b)",
    re.I,
)
SAVE_REQUEST = re.compile(
    r"(?:存入|保存|记住|记到|写入).{0,12}(?:长期|档案|记忆)|(?:长期|档案|记忆).{0,12}(?:存入|保存|记住|写入)"
)
EXPLICIT_CONSENT = re.compile(r"(?:我明确同意|我已同意|我同意|明确同意)")
NEGATED_CONSENT = re.compile(r"(?:没有同意|未同意|不同意|不允许|拒绝保存)")


def content_key(content: str, relationship_id: UUID | None = None) -> str:
    normalized = " ".join(content.casefold().split())
    scope = str(relationship_id) if relationship_id is not None else "user"
    return hashlib.sha256(f"{scope}:{normalized}".encode()).hexdigest()


def explicit_save_consent(message: str) -> bool:
    return bool(EXPLICIT_CONSENT.search(message)) and not NEGATED_CONSENT.search(message)


def asks_to_save(message: str) -> bool:
    return bool(SAVE_REQUEST.search(message)) and not NEGATED_CONSENT.search(message)


def prohibited_request(message: str) -> bool:
    return bool(BLOCKED_CONTENT.search(message)) and any(
        cue in message for cue in ("聊天记录", "整份聊天", "身份证", "住址", "密码", "token")
    )


def validate_candidate(
    candidate: MemoryCandidate,
    *,
    facts: list[Fact],
    message: str,
    person_id: UUID | None,
    user_id: UUID,
) -> bool:
    if candidate.type not in ALLOWED_TYPES or candidate.source not in {
        "user_explicit",
        "user_report",
    }:
        return False
    if candidate.subject_id != (user_id if candidate.type == "user" else person_id):
        return False
    if candidate.type == "user" and candidate.source != "user_explicit":
        return False
    if len(candidate.content.strip()) < 4 or BLOCKED_CONTENT.search(candidate.content):
        return False
    if candidate.content.strip() not in message or candidate.content.strip() == message.strip():
        return False
    if not re.fullmatch(r"F[1-9]\d*", candidate.evidence):
        return False
    index = int(candidate.evidence[1:]) - 1
    if index >= len(facts) or facts[index].source not in {
        "user_explicit",
        "user_report",
        "user_report_quote",
        "user_self_report",
    }:
        return False
    fact_source = facts[index].source
    if candidate.source == "user_report" and fact_source not in {
        "user_report",
        "user_report_quote",
    }:
        return False
    if candidate.source == "user_explicit" and fact_source not in {
        "user_explicit",
        "user_self_report",
    }:
        return False
    if candidate.content.strip() not in facts[index].statement:
        return False
    return True


class MemoryStore(Protocol):
    def get_control(self, user_id: UUID) -> MemoryControl: ...
    def set_control(self, user_id: UUID, control: MemoryControl) -> None: ...
    def resolve_person(self, user_id: UUID, relationship_id: UUID) -> UUID | None: ...
    def list_records(self, user_id: UUID, person_id: UUID | None = None) -> list[MemoryRecord]: ...
    def save_record(self, record: MemoryRecord) -> bool: ...
    def delete_one(self, user_id: UUID, memory_id: UUID, person_id: UUID | None) -> bool: ...
    def delete_person(self, user_id: UUID, person_id: UUID) -> int: ...
    def delete_all(self, user_id: UUID) -> int: ...


class InMemoryMemoryStore:
    """Small fake with the same ownership and dedup behavior as the SQL store."""

    def __init__(self) -> None:
        self.controls: dict[UUID, MemoryControl] = {}
        self.relationships: dict[tuple[UUID, UUID], UUID] = {}
        self.records: dict[UUID, MemoryRecord] = {}

    def bind_relationship(self, user_id: UUID, relationship_id: UUID, person_id: UUID) -> None:
        self.relationships[(user_id, relationship_id)] = person_id

    def get_control(self, user_id: UUID) -> MemoryControl:
        return self.controls.get(user_id, MemoryControl()).model_copy()

    def set_control(self, user_id: UUID, control: MemoryControl) -> None:
        self.controls[user_id] = control.model_copy()

    def resolve_person(self, user_id: UUID, relationship_id: UUID) -> UUID | None:
        return self.relationships.get((user_id, relationship_id))

    def list_records(self, user_id: UUID, person_id: UUID | None = None) -> list[MemoryRecord]:
        return sorted(
            (
                record.model_copy()
                for record in self.records.values()
                if record.owner_user_id == user_id
                and (person_id is None or record.subject_id in {user_id, person_id})
            ),
            key=lambda item: (item.created_at, str(item.id)),
            reverse=True,
        )

    def save_record(self, record: MemoryRecord) -> bool:
        if record.person_id is not None and (
            record.type == "user"
            or record.relationship_id is None
            or record.subject_id != record.person_id
            or self.resolve_person(record.owner_user_id, record.relationship_id) != record.person_id
        ):
            raise ValueError("memory scope is invalid")
        if record.person_id is None and (
            record.type != "user"
            or record.subject_id != record.owner_user_id
            or record.relationship_id is not None
        ):
            raise ValueError("memory scope is invalid")
        key = (
            record.owner_user_id,
            record.subject_id,
            record.type,
            content_key(record.content, record.relationship_id),
        )
        if any(
            (
                item.owner_user_id,
                item.subject_id,
                item.type,
                content_key(item.content, item.relationship_id),
            )
            == key
            for item in self.records.values()
        ):
            return False
        if len(self.list_records(record.owner_user_id)) >= MAX_TOTAL:
            raise ValueError("memory limit reached")
        self.records[record.id] = record.model_copy()
        return True

    def delete_one(self, user_id: UUID, memory_id: UUID, person_id: UUID | None) -> bool:
        record = self.records.get(memory_id)
        if record is None or record.owner_user_id != user_id or record.person_id != person_id:
            return False
        del self.records[memory_id]
        return True

    def delete_person(self, user_id: UUID, person_id: UUID) -> int:
        ids = [
            item.id
            for item in self.records.values()
            if item.owner_user_id == user_id and item.person_id == person_id
        ]
        for item_id in ids:
            del self.records[item_id]
        return len(ids)

    def delete_all(self, user_id: UUID) -> int:
        ids = [item.id for item in self.records.values() if item.owner_user_id == user_id]
        for item_id in ids:
            del self.records[item_id]
        return len(ids)


class MemoryService:
    def __init__(self, store: MemoryStore) -> None:
        self.store = store

    def resolve_person(self, user_id: UUID, relationship_id: UUID | None) -> UUID | None:
        return self.store.resolve_person(user_id, relationship_id) if relationship_id else None

    def control(self, user_id: UUID) -> MemoryControl:
        return self.store.get_control(user_id)

    def grant_consent(self, user_id: UUID, *, confirmed: bool) -> MemoryReceipt:
        if not confirmed:
            return MemoryReceipt(status=MemoryWriteStatus.SKIPPED_NO_CONSENT)
        current = self.control(user_id)
        self.store.set_control(user_id, MemoryControl(consent_enabled=True, paused=current.paused))
        return MemoryReceipt(status=MemoryWriteStatus.CONTROL_UPDATED)

    def load_for_context(
        self, user_id: UUID, relationship_id: UUID | None, *, enabled: bool
    ) -> list[MemoryRecord]:
        if not enabled:
            return []
        control = self.control(user_id)
        if not control.consent_enabled or control.paused:
            return []
        person_id = self.resolve_person(user_id, relationship_id)
        if relationship_id is not None and person_id is None:
            return []
        records = self.store.list_records(user_id, person_id)
        return [
            item
            for item in records
            if item.subject_id == user_id
            or (relationship_id is not None and item.relationship_id == relationship_id)
        ][:RECALL_LIMIT]

    def list_for_user(self, user_id: UUID, person_id: UUID | None = None) -> list[MemoryRecord]:
        return self.store.list_records(user_id, person_id)

    def apply_control(self, user_id: UUID, decision: MemoryDecision) -> MemoryReceipt:
        current = self.control(user_id)
        if decision == MemoryDecision.PAUSE:
            if not current.consent_enabled:
                return MemoryReceipt(status=MemoryWriteStatus.SKIPPED_NO_CONSENT)
            self.store.set_control(user_id, MemoryControl(consent_enabled=True, paused=True))
        elif decision == MemoryDecision.RESUME:
            if not current.consent_enabled:
                return MemoryReceipt(status=MemoryWriteStatus.SKIPPED_NO_CONSENT)
            self.store.set_control(user_id, MemoryControl(consent_enabled=True, paused=False))
        elif decision == MemoryDecision.REVOKE_KEEP:
            self.store.set_control(user_id, MemoryControl(consent_enabled=False, paused=True))
        else:
            return MemoryReceipt(status=MemoryWriteStatus.PENDING_CONFIRMATION)
        return MemoryReceipt(status=MemoryWriteStatus.CONTROL_UPDATED)

    def persist_candidates(
        self,
        *,
        user_id: UUID,
        relationship_id: UUID | None,
        run_id: UUID,
        candidates: list[MemoryCandidate],
        facts: list[Fact],
        message: str,
        explicit_consent: bool,
    ) -> MemoryReceipt:
        control = self.control(user_id)
        if explicit_consent:
            self.grant_consent(user_id, confirmed=True)
            control = self.control(user_id)
        if not control.consent_enabled:
            return MemoryReceipt(status=MemoryWriteStatus.SKIPPED_NO_CONSENT)
        if control.paused:
            return MemoryReceipt(status=MemoryWriteStatus.SKIPPED_PAUSED)
        if len(candidates) != 1:
            return MemoryReceipt(status=MemoryWriteStatus.REJECTED_VALIDATION)
        person_id = self.resolve_person(user_id, relationship_id)
        if relationship_id is not None and person_id is None:
            return MemoryReceipt(status=MemoryWriteStatus.REJECTED_VALIDATION)
        if any(
            not validate_candidate(
                item, facts=facts, message=message, person_id=person_id, user_id=user_id
            )
            for item in candidates
        ):
            return MemoryReceipt(status=MemoryWriteStatus.REJECTED_VALIDATION)
        saved = duplicates = 0
        now = datetime.now(UTC)
        for item in candidates:
            is_user = item.type == "user"
            record = MemoryRecord(
                id=uuid4(),
                owner_user_id=user_id,
                subject_id=item.subject_id,
                person_id=None if is_user else person_id,
                relationship_id=None if is_user else relationship_id,
                type=item.type,
                content=item.content.strip(),
                source=item.source,
                evidence=f"{run_id}: {item.evidence}",
                confidence=item.confidence,
                created_at=now,
                updated_at=now,
            )
            if self.store.save_record(record):
                saved += 1
            else:
                duplicates += 1
        return MemoryReceipt(
            status=MemoryWriteStatus.SAVED if saved else MemoryWriteStatus.DUPLICATE,
            saved_count=saved,
            duplicate_count=duplicates,
        )

    def delete_one(self, user_id: UUID, memory_id: UUID, *, person_id: UUID | None) -> bool:
        return self.store.delete_one(user_id, memory_id, person_id)

    def delete_person(self, user_id: UUID, person_id: UUID, *, confirmed: bool) -> int:
        if not confirmed:
            return 0
        return self.store.delete_person(user_id, person_id)

    def delete_all(self, user_id: UUID, *, confirmed: bool, revoke: bool = False) -> int:
        if not confirmed:
            return 0
        count = self.store.delete_all(user_id)
        if revoke:
            self.store.set_control(user_id, MemoryControl(consent_enabled=False, paused=True))
        return count
