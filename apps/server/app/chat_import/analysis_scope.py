"""ICA v3 deterministic preparation. No provider, memory or execution authority."""

import hashlib
import json
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

VERSION = "ica-long-range-v3"


def utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("aware timestamp required")
    return value.astimezone(UTC)


@dataclass(frozen=True)
class AnalysisScope:
    owner_id: UUID
    person_id: UUID
    dataset_id: UUID
    timezone: str
    start: datetime
    end: datetime
    version: str = VERSION

    def __post_init__(self):
        ZoneInfo(self.timezone)
        if utc(self.start) >= utc(self.end) or self.version != VERSION:
            raise ValueError("invalid scope")

    @property
    def digest(self) -> str:
        return hashlib.sha256(
            json.dumps(
                [
                    str(self.owner_id),
                    str(self.person_id),
                    str(self.dataset_id),
                    self.timezone,
                    utc(self.start).isoformat(),
                    utc(self.end).isoformat(),
                    self.version,
                ]
            ).encode()
        ).hexdigest()


def calendar_window(
    timezone: str,
    now: datetime,
    *,
    days: int | None = None,
    first: date | None = None,
    last: date | None = None,
) -> tuple[datetime, datetime]:
    zone = ZoneInfo(timezone)
    now = utc(now)
    today = now.astimezone(zone).date()
    if days is not None:
        if days not in (3, 7) or first is not None or last is not None:
            raise ValueError("select 3/7 days or custom dates")
        first, last = today - timedelta(days=days - 1), today
    if first is None or last is None or first > last or first > today:
        raise ValueError("invalid dates")

    def midnight(day: date) -> datetime:
        local = datetime.combine(day, time.min)
        possibilities = {
            local.replace(tzinfo=zone, fold=fold).astimezone(UTC)
            for fold in (0, 1)
            if local.replace(tzinfo=zone, fold=fold)
            .astimezone(UTC)
            .astimezone(zone)
            .replace(tzinfo=None)
            == local
        }
        if len(possibilities) != 1:
            raise ValueError("ambiguous or nonexistent midnight")
        return possibilities.pop()

    return midnight(first), min(now, midnight(last + timedelta(days=1)))


@dataclass(frozen=True)
class ScopeMessage:
    id: UUID
    owner_id: UUID
    person_id: UUID
    dataset_id: UUID
    timestamp: datetime
    speaker: str
    content: str
    content_type: str = "text"

    @property
    def size(self) -> int:
        return len(self.content.encode("utf-8"))


@dataclass(frozen=True)
class ChunkManifest:
    id: str
    scope_digest: str
    core: tuple[UUID, ...]
    halo_before: tuple[UUID, ...]
    halo_after: tuple[UUID, ...]
    continuation: bool


@dataclass(frozen=True)
class StageReceipt:
    chunk_id: str
    stage: str
    status: str = "pending"

    def __post_init__(self):
        if self.stage not in {"safety", "interaction", "counterevidence"}:
            raise ValueError("unknown stage")
        if self.status != "pending":
            raise ValueError("ICA-A cannot complete model stages")


@dataclass(frozen=True)
class ImportedChatContext:
    scope: AnalysisScope
    snapshot_digest: str
    chunks: tuple[ChunkManifest, ...]
    messages: tuple[ScopeMessage, ...]


def prepare_context(scope: AnalysisScope, messages: list[ScopeMessage]) -> ImportedChatContext:
    ordered = sorted(messages, key=lambda m: (utc(m.timestamp), m.id))
    ids = [m.id for m in ordered]
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate canonical UUID")
    for m in ordered:
        if (m.owner_id, m.person_id, m.dataset_id) != (
            scope.owner_id,
            scope.person_id,
            scope.dataset_id,
        ) or not utc(scope.start) <= utc(m.timestamp) < utc(scope.end):
            raise ValueError("message outside authorized scope")
        if m.size > 48 * 1024:
            raise ValueError("single message exceeds core budget")
    if len(ordered) > 10000 or sum(m.size for m in ordered) > 2 * 1024 * 1024:
        raise ValueError("selection exceeds source budget")
    snapshot = hashlib.sha256(
        json.dumps(
            [
                [str(m.id), utc(m.timestamp).isoformat(), m.speaker, m.content, m.content_type]
                for m in ordered
            ],
            ensure_ascii=False,
        ).encode()
    ).hexdigest()
    boundaries = []
    start = 0
    while start < len(ordered):
        end, size = start, 0
        while end < len(ordered) and end - start < 200:
            if size + ordered[end].size > 48 * 1024:
                break
            size += ordered[end].size
            end += 1
        # Prefer the last session boundary, then a turn boundary within this core.
        if end < len(ordered):
            sessions = [
                i
                for i in range(start + 1, end + 1)
                if utc(ordered[i].timestamp) - utc(ordered[i - 1].timestamp) > timedelta(minutes=30)
            ]
            turns = [
                i for i in range(start + 1, end + 1) if ordered[i].speaker != ordered[i - 1].speaker
            ]
            end = (sessions or turns or [end])[-1]
        boundaries.append((start, end))
        start = end
    if len(boundaries) > 32:
        raise ValueError("selection exceeds chunk budget; no partial coverage")

    def halo(indices):
        selected, size = [], 0
        for i in indices:
            if len(selected) == 20 or size + ordered[i].size > 4096:
                break
            selected.append(ordered[i].id)
            size += ordered[i].size
        return tuple(selected)

    chunks = []
    for start, end in boundaries:
        core = tuple(ids[start:end])
        chunk_id = hashlib.sha256(f"{scope.digest}:{snapshot}:{start}:{end}".encode()).hexdigest()
        chunks.append(
            ChunkManifest(
                chunk_id,
                scope.digest,
                core,
                tuple(reversed(halo(range(start - 1, -1, -1)))),
                halo(range(end, len(ordered))),
                start > 0
                and utc(ordered[start].timestamp) - utc(ordered[start - 1].timestamp)
                <= timedelta(minutes=30),
            )
        )
    context = ImportedChatContext(scope, snapshot, tuple(chunks), tuple(ordered))
    validate_coverage(context)
    return context


def validate_coverage(context: ImportedChatContext) -> None:
    core = [i for c in context.chunks for i in c.core]
    authorized = {m.id for m in context.messages}
    if len(core) != len(set(core)) or set(core) != authorized:
        raise ValueError("core does not partition snapshot")
    for chunk in context.chunks:
        if (
            chunk.scope_digest != context.scope.digest
            or not set(chunk.halo_before + chunk.halo_after) <= authorized
        ):
            raise ValueError("halo or scope mismatch")


def validate_evidence(
    context: ImportedChatContext,
    message_id: UUID,
    start: int,
    end: int,
    quote: str,
) -> ScopeMessage:
    message = next((m for m in context.messages if m.id == message_id), None)
    if message is None or type(start) is not int or type(end) is not int:
        raise ValueError("unauthorized evidence")
    if not 0 <= start < end <= len(message.content) or message.content[start:end] != quote:
        raise ValueError("invalid Unicode code point span")
    return message


def preview(context: ImportedChatContext) -> dict:
    messages = context.messages
    return {
        "version": VERSION,
        "scope_digest": context.scope.digest,
        "snapshot_digest": context.snapshot_digest,
        "messages": len(messages),
        "body_bytes": sum(m.size for m in messages),
        "speakers": dict(Counter(m.speaker for m in messages)),
        "local_days": dict(
            Counter(
                utc(m.timestamp).astimezone(ZoneInfo(context.scope.timezone)).date().isoformat()
                for m in messages
            )
        ),
        "first": utc(messages[0].timestamp).isoformat() if messages else None,
        "last": utc(messages[-1].timestamp).isoformat() if messages else None,
        "nontext": sum(m.content_type != "text" for m in messages),
        "chunks": len(context.chunks),
        "planned_requests": 3 * len(context.chunks) + 8,
        "core_coverage_complete": True,
        "export_completeness": "unknown",
        "model_stages": "pending",
        "provider_calls": 0,
    }


def budget_plan(
    context: ImportedChatContext,
    *,
    prompt_reserve_bytes: int,
    max_output_tokens: int,
    price_per_million: int,
) -> dict:
    """Integer microcurrency ceiling; one token per UTF-8 byte is a conservative plan.

    Caller must provide a frozen model tariff and prompt/output caps before granting.
    This deterministic estimate is not a tokenizer measurement or actual invoice.
    """
    if any(
        type(v) is not int or v < 0
        for v in (prompt_reserve_bytes, max_output_tokens, price_per_million)
    ):
        raise ValueError("invalid budget inputs")
    lookup = {m.id: m for m in context.messages}
    payload_bytes = 0
    for chunk in context.chunks:
        payload = [
            {
                "id": str(i),
                "time": utc(lookup[i].timestamp).isoformat(),
                "speaker": lookup[i].speaker,
                "content": lookup[i].content,
            }
            for i in chunk.halo_before + chunk.core + chunk.halo_after
        ]
        payload_bytes += len(json.dumps(payload, ensure_ascii=True).encode())
    requests = 3 * len(context.chunks) + 8
    # Global synthesis calls reserve the entire serialized transcript each time.
    token_cap = 11 * payload_bytes + requests * (prompt_reserve_bytes + max_output_tokens)
    return {
        "requests": requests,
        "serialized_payload_bytes": payload_bytes,
        "token_cap": token_cap,
        "cost_cap_microcurrency": (token_cap * price_per_million + 999999) // 1000000,
        "actual_provider_calls": 0,
        "estimate_only": True,
    }
