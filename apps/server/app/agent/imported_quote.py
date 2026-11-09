"""Quote-only model inputs; canonical evidence retains server-computed Unicode spans."""

from collections.abc import Callable

from pydantic import BaseModel, Field, ValidationError

from app.agent.imported_contracts import (
    ChunkCounterevidence,
    ChunkInteractions,
    ChunkSafety,
    ContentReview,
    CounterItem,
    Finding,
    ImportedEvidenceRef,
    InteractionCandidate,
    ObservedFact,
    ReportDraft,
    RoleRisk,
    Speaker,
    StrictModel,
)

QUOTE_PROTOCOL = "quote-v2"
SPAN_PROTOCOL = "span-v1"


class QuotedEvidenceRef(StrictModel):
    evidence_id: str = Field(pattern=r"^w[01]-m\d{5}$")
    speaker: Speaker
    quote: str = Field(min_length=1, max_length=160)


class QuotedFact(ObservedFact):
    evidence: list[QuotedEvidenceRef] = Field(min_length=1, max_length=8)


class QuotedRoleRisk(RoleRisk):
    evidence: list[QuotedEvidenceRef] = Field(max_length=4)


class QuotedChunkSafety(ChunkSafety):
    risks: list[QuotedRoleRisk] = Field(max_length=8)


class QuotedInteractionCandidate(InteractionCandidate):
    facts: list[QuotedFact] = Field(min_length=1, max_length=4)


class QuotedChunkInteractions(ChunkInteractions):
    candidates: list[QuotedInteractionCandidate] = Field(max_length=3)


class QuotedCounterItem(CounterItem):
    facts: list[QuotedFact] = Field(max_length=2)


class QuotedChunkCounterevidence(ChunkCounterevidence):
    checks: list[QuotedCounterItem] = Field(max_length=96)


class QuotedFinding(Finding):
    facts: list[QuotedFact] = Field(min_length=1, max_length=4)
    counterevidence: list[QuotedFact] = Field(max_length=8)


class QuotedReportDraft(ReportDraft):
    findings: list[QuotedFinding] = Field(max_length=3)


STAGE_SCHEMAS = {
    "safety": QuotedChunkSafety,
    "interaction": QuotedChunkInteractions,
    "counterevidence": QuotedChunkCounterevidence,
    "synthesis": QuotedReportDraft,
    "content_review": ContentReview,
}
CANONICAL_SCHEMAS = {
    "safety": ChunkSafety,
    "interaction": ChunkInteractions,
    "counterevidence": ChunkCounterevidence,
    "synthesis": ReportDraft,
    "content_review": ContentReview,
}


def exact_span(text: str, quote: str) -> tuple[int, int]:
    """Locate one exact occurrence, including overlaps; never normalize or trim text."""
    if not isinstance(text, str) or not isinstance(quote, str) or not 1 <= len(quote) <= 160:
        raise ValueError("invalid_quote")
    start = text.find(quote)
    if start < 0:
        raise ValueError("quote_not_found")
    if text.find(quote, start + 1) >= 0:
        raise ValueError("quote_ambiguous")
    return start, start + len(quote)


def resolve_output(
    stage: str,
    output: BaseModel,
    resolver: Callable[[QuotedEvidenceRef], ImportedEvidenceRef],
) -> BaseModel:
    """Resolve every quote through the caller's current authorized message context."""
    if stage not in STAGE_SCHEMAS:
        raise ValueError("invalid_quote_stage")
    # Revalidation also rejects model_construct bypasses and legacy numeric spans.
    wire = STAGE_SCHEMAS[stage].model_validate(output.model_dump(mode="python"))

    def canonical(value):
        if isinstance(value, QuotedEvidenceRef):
            resolved = resolver(value)
            if not isinstance(resolved, ImportedEvidenceRef):
                raise ValueError("invalid_quote_resolution")
            resolved = ImportedEvidenceRef.model_validate(resolved.model_dump(mode="python"))
            if (resolved.evidence_id, resolved.speaker, resolved.quote) != (
                value.evidence_id,
                value.speaker,
                value.quote,
            ):
                raise ValueError("quote_resolution_mismatch")
            return resolved.model_dump(mode="python")
        if isinstance(value, BaseModel):
            return {name: canonical(getattr(value, name)) for name in type(value).model_fields}
        if isinstance(value, list):
            return [canonical(item) for item in value]
        return value

    return CANONICAL_SCHEMAS[stage].model_validate(canonical(wire))


def quote_payload(value):
    """Serialize previously validated canonical inputs for quote-only model stages.

    This is not a resolver and must never repair unvalidated legacy model output.
    """
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json")
    if isinstance(value, dict):
        if set(value) == {"evidence_id", "speaker", "start", "end", "quote"}:
            try:
                ImportedEvidenceRef.model_validate(value)
            except ValidationError:
                pass
            else:
                return {key: value[key] for key in ("evidence_id", "speaker", "quote")}
        return {key: quote_payload(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [quote_payload(item) for item in value]
    return value
