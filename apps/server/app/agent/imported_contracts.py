"""Bounded ICA-B1 wire contracts. Model observations are not verified real-world facts."""

from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

ShortText = Annotated[str, Field(min_length=1, max_length=320)]
Kind = Literal["emotional_mismatch", "recurring_conflict", "temporal_change"]
Speaker = Literal["self", "person", "system"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)


class ImportedEvidenceRef(StrictModel):
    evidence_id: str = Field(pattern=r"^w[01]-m\d{5}$")
    speaker: Speaker
    start: int = Field(ge=0)
    end: int = Field(gt=0)
    quote: str = Field(min_length=1, max_length=160)


class ObservedFact(StrictModel):
    statement: ShortText
    evidence: list[ImportedEvidenceRef] = Field(min_length=1, max_length=8)


class RepairAction(StrictModel):
    action: ShortText
    observe: ShortText
    stop_when: ShortText


class RoleRisk(StrictModel):
    actor: Literal["self", "person", "unknown"]
    user_role: Literal["at_risk", "causing_harm", "unclear"]
    temporality: Literal["current", "historical", "quoted_or_denied", "unknown"]
    category: Literal[
        "self_harm", "violence", "coercion", "stalking", "refusal", "fraud", "uncertain"
    ]
    source: Literal["question", "chat"]
    evidence: list[ImportedEvidenceRef] = Field(max_length=4)

    @model_validator(mode="after")
    def source_requires_evidence(self):
        if (self.source == "chat") != bool(self.evidence):
            raise ValueError("risk source/evidence mismatch")
        return self


class ChunkSafety(StrictModel):
    decision: Literal["normal", "boundary", "danger", "uncertain"]
    risks: list[RoleRisk] = Field(max_length=8)

    @model_validator(mode="after")
    def consistent_decision(self):
        if (self.decision == "normal") == bool(self.risks):
            raise ValueError("risk decision mismatch")
        return self


class InteractionCandidate(StrictModel):
    kind: Kind
    facts: list[ObservedFact] = Field(min_length=1, max_length=4)
    hypothesis: ShortText
    unknowns: list[ShortText] = Field(min_length=1, max_length=3)
    alternative_explanations: list[ShortText] = Field(min_length=1, max_length=3)
    repair: RepairAction


class ChunkInteractions(StrictModel):
    candidates: list[InteractionCandidate] = Field(max_length=3)


class CounterItem(StrictModel):
    candidate_id: str = Field(min_length=1, max_length=80)
    decision: Literal["no_evidence", "qualifies", "refutes", "repair"]
    facts: list[ObservedFact] = Field(max_length=2)

    @model_validator(mode="after")
    def consistent_counter(self):
        if (self.decision == "no_evidence") == bool(self.facts):
            raise ValueError("counterevidence decision mismatch")
        return self


class ChunkCounterevidence(StrictModel):
    checks: list[CounterItem] = Field(max_length=96)


class Finding(InteractionCandidate):
    candidate_ids: list[str] = Field(min_length=1, max_length=8)
    counterevidence: list[ObservedFact] = Field(max_length=8)


class ReportDraft(StrictModel):
    findings: list[Finding] = Field(max_length=3)


class ContentReview(StrictModel):
    approved: bool
    grounded: bool
    respects_boundaries: bool
    preserves_counterevidence: bool
    reason_codes: list[
        Literal["unsupported", "unsafe", "misattributed", "counterevidence_omitted", "uncertain"]
    ] = Field(max_length=5)


class WindowCoverage(StrictModel):
    window_index: int = Field(ge=0, le=1)
    start_utc: str
    end_utc: str
    timezone: str
    scope_digest: str
    snapshot_digest: str
    message_count: int = Field(ge=0)
    text_count: int = Field(ge=0)
    body_bytes: int = Field(ge=0)
    core_count: int = Field(ge=0)
    self_count: int = Field(ge=0)
    person_count: int = Field(ge=0)
    active_local_days: int = Field(ge=0)


class SourceBinding(StrictModel):
    evidence_id: str
    message_id: UUID
    dataset_id: UUID
    speaker: Speaker
    timestamp: str
    scope_digest: str


class AnalysisReport(StrictModel):
    version: Literal["ica-report-v1"] = "ica-report-v1"
    outcome: Literal["findings", "insufficient_evidence", "safety_blocked"]
    findings: list[Finding] = Field(max_length=3)
    coverage: list[WindowCoverage] = Field(min_length=1, max_length=2)
    safety_roles: list[RoleRisk] = Field(max_length=256)
    limitations: list[ShortText] = Field(min_length=1, max_length=6)
    sources: list[SourceBinding] = Field(max_length=512)
    knowledge_refs: list[str] = Field(min_length=1, max_length=3)

    @model_validator(mode="after")
    def outcome_matches_findings(self):
        if (self.outcome == "findings") != bool(self.findings):
            raise ValueError("report outcome mismatch")
        if self.outcome == "safety_blocked" and not self.safety_roles:
            raise ValueError("safety report requires risk roles")
        return self


class AnalysisStageReceipt(StrictModel):
    chunk_id: str | None
    stage: Literal["safety", "interaction", "counterevidence", "synthesis", "content_review"]
    status: Literal["completed", "not_applicable"]


class ImportedAnalysisResult(StrictModel):
    report: AnalysisReport
    receipts: list[AnalysisStageReceipt]
    provider_calls: int = Field(ge=0)
