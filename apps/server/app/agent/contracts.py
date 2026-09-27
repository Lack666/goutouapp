"""JSON-safe public values for a future standalone Agent runtime."""

from datetime import datetime
from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ContractModel(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")


class Scenario(StrEnum):
    REPLY = "reply"
    INVITATION = "invitation"
    FLIRT = "flirt"
    RELATIONSHIP = "relationship"
    IMBALANCE = "imbalance"
    CONFLICT = "conflict"
    BREAKUP = "breakup"
    LONG_TERM = "long_term"
    HOUSEHOLD = "household"
    ONLINE = "online"
    CHAT_IMPORT = "chat_import"
    PERSONALITY = "personality"
    SOCIAL_SYSTEM = "social_system"
    PUA = "pua"
    CONSENT = "consent"
    DIVERSITY = "diversity"
    SOCIAL_OTHER = "social_other"
    SAFETY = "safety"
    MEMORY = "memory"


class RiskLevel(StrEnum):
    NORMAL = "normal"
    HIGH = "high"


class Route(StrEnum):
    ORDINARY = "ordinary"
    BOUNDARY = "boundary"
    SAFETY = "safety"


class AgentRunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class MemoryDecision(StrEnum):
    NO_WRITE = "no_write"
    ALLOW_CANDIDATE = "allow_candidate"
    PAUSE = "pause"
    RESUME = "resume"
    REVOKE_KEEP = "revoke_keep"
    DELETE_ITEM = "delete_item"
    DELETE_PERSON = "delete_person"
    DELETE_ALL = "delete_all"
    REVOKE_AND_DELETE_ALL = "revoke_and_delete_all"
    INSPECT = "inspect"
    UNDO = "undo"


class MemoryWriteStatus(StrEnum):
    NONE = "none"
    SAVED = "saved"
    DUPLICATE = "duplicate"
    SKIPPED_NO_CONSENT = "skipped_no_consent"
    SKIPPED_PAUSED = "skipped_paused"
    REJECTED_VALIDATION = "rejected_validation"
    PENDING_CONFIRMATION = "pending_confirmation"
    CONTROL_UPDATED = "control_updated"
    FAILED = "failed"
    UNDONE = "undone"
    NOTHING_TO_UNDO = "nothing_to_undo"


class ConversationMessage(ContractModel):
    role: Literal["user", "assistant", "tool"]
    content: str = Field(min_length=1)
    speaker: str | None = None


class AgentInput(ContractModel):
    user_id: UUID
    conversation_id: UUID
    relationship_id: UUID | None = None
    message: str = Field(min_length=1)
    recent_messages: list[ConversationMessage] = Field(default_factory=list)
    locale: str | None = None
    timezone: str | None = None
    memory_enabled: bool = False
    metadata: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def nonblank_message(self) -> "AgentInput":
        if not self.message.strip():
            raise ValueError("message must not be blank")
        return self


class ScenarioResult(ContractModel):
    primary: Scenario
    secondary: Scenario | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    reason_summary: str = Field(min_length=1)


class SafetyResult(ContractModel):
    risk_level: RiskLevel
    risk_categories: list[str] = Field(default_factory=list)
    safety_route_required: bool
    user_facing_note: str | None = None

    @model_validator(mode="after")
    def consistent_risk(self) -> "SafetyResult":
        if self.safety_route_required != (self.risk_level == RiskLevel.HIGH):
            raise ValueError("high risk requires safety route; normal risk does not")
        return self


class Fact(ContractModel):
    type: Literal["fact"] = "fact"
    statement: str = Field(min_length=1)
    source: str = Field(min_length=1)
    confidence: float | None = Field(default=None, ge=0, le=1)


class Inference(ContractModel):
    type: Literal["inference"] = "inference"
    statement: str = Field(min_length=1)
    source: str = Field(min_length=1)
    alternative: str = Field(min_length=1)
    confidence: float | None = Field(default=None, ge=0, le=1)


class Unknown(ContractModel):
    type: Literal["unknown"] = "unknown"
    statement: str = Field(min_length=1)
    source: str | None = None


EvidenceItem = Fact | Inference | Unknown


class FactExtractionResult(ContractModel):
    facts: list[Fact] = Field(default_factory=list)
    inferences: list[Inference] = Field(default_factory=list)
    unknowns: list[Unknown] = Field(default_factory=list)


class KnowledgeRouteResult(ContractModel):
    selected_references: list[str] = Field(min_length=1, max_length=3)
    primary_reference: str | None = None
    reason_summary: str = Field(min_length=1)
    max_references: int = Field(default=3, ge=1, le=3)

    @model_validator(mode="after")
    def within_limit(self) -> "KnowledgeRouteResult":
        if len(self.selected_references) > self.max_references:
            raise ValueError("selected references exceed max_references")
        if any(not alias.strip() for alias in self.selected_references):
            raise ValueError("selected references must be nonblank")
        if len(set(self.selected_references)) != len(self.selected_references):
            raise ValueError("selected references must be unique")
        if (
            self.primary_reference is not None
            and self.primary_reference != self.selected_references[0]
        ):
            raise ValueError("primary reference must be selected first")
        return self


class LoadedReference(ContractModel):
    alias: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    category: str = Field(min_length=1)
    content: str = Field(min_length=1)
    truncated: bool
    content_length: int = Field(ge=1)


class AnalysisPoint(ContractModel):
    statement: str = Field(min_length=1, max_length=500)
    kind: Literal["observed", "tentative", "framework", "uncertainty"]
    dimension: Literal[
        "reciprocity",
        "boundary",
        "communication",
        "consistency",
        "reality_constraint",
        "opportunity_cost",
        "evidence_quality",
        "personality_caution",
        "general",
    ]
    evidence_ids: list[str] = Field(default_factory=list, max_length=8)
    reference_ids: list[str] = Field(default_factory=list, max_length=3)

    @model_validator(mode="after")
    def source_shape(self) -> "AnalysisPoint":
        if not self.evidence_ids and not self.reference_ids:
            raise ValueError("analysis point requires a source")
        if len(set(self.evidence_ids)) != len(self.evidence_ids) or len(
            set(self.reference_ids)
        ) != len(self.reference_ids):
            raise ValueError("analysis provenance IDs must be unique")
        if self.kind == "observed" and (
            not self.evidence_ids
            or any(not evidence_id.startswith("F") for evidence_id in self.evidence_ids)
            or self.reference_ids
        ):
            raise ValueError("observed claim requires only fact evidence")
        if self.kind == "tentative" and not any(
            evidence_id.startswith(("F", "I")) for evidence_id in self.evidence_ids
        ):
            raise ValueError("tentative interpretation requires case evidence")
        if self.kind == "framework" and not self.reference_ids:
            raise ValueError("knowledge lens requires a reference")
        if self.kind == "uncertainty" and not any(
            evidence_id.startswith("U") for evidence_id in self.evidence_ids
        ):
            raise ValueError("uncertainty requires an unknown")
        return self


class AnalysisResult(ContractModel):
    core_issue: str = Field(min_length=1, max_length=500)
    core_evidence_ids: list[str] = Field(default_factory=list, max_length=8)
    core_reference_ids: list[str] = Field(default_factory=list, max_length=3)
    insufficient_evidence: bool = False
    observations: list[AnalysisPoint] = Field(default_factory=list, max_length=6)
    relationship_dynamics: list[AnalysisPoint] = Field(default_factory=list, max_length=6)
    risks: list[AnalysisPoint] = Field(default_factory=list, max_length=6)
    constraints: list[AnalysisPoint] = Field(default_factory=list, max_length=6)
    uncertainties: list[AnalysisPoint] = Field(default_factory=list, max_length=6)


class ActionPlan(ContractModel):
    contact_policy: Literal["reply", "invite", "observe", "pause", "stop_contact"]
    recommended_action: str = Field(min_length=1, max_length=500)
    supporting_analysis_ids: list[str] = Field(min_length=1, max_length=5)
    message_suggestion: str | None = Field(default=None, min_length=1, max_length=300)
    observation_window: str | None = Field(default=None, min_length=1, max_length=150)
    stop_conditions: list[str] = Field(default_factory=list, max_length=4)


class ResponseResult(ContractModel):
    final_answer: str = Field(min_length=1, max_length=3000)
    contact_policy: Literal["reply", "invite", "observe", "pause", "stop_contact"]


class MemoryCandidate(ContractModel):
    subject_id: UUID
    type: str = Field(min_length=1)
    content: str = Field(min_length=1, max_length=200)
    source: str = Field(min_length=1)
    evidence: str = Field(min_length=1)
    confidence: float | None = Field(default=None, ge=0, le=1)
    requires_consent: Literal[True] = True


class MemoryCandidateBatch(ContractModel):
    candidates: list[MemoryCandidate] = Field(default_factory=list, max_length=1)


class MemoryControl(ContractModel):
    consent_enabled: bool = False
    paused: bool = False


class MemoryRecord(ContractModel):
    id: UUID
    owner_user_id: UUID
    subject_id: UUID
    person_id: UUID | None = None
    relationship_id: UUID | None = None
    type: str
    content: str
    source: str
    evidence: str
    confidence: float | None = None
    created_at: datetime
    updated_at: datetime


class MemoryReceipt(ContractModel):
    status: MemoryWriteStatus = MemoryWriteStatus.NONE
    saved_count: int = Field(default=0, ge=0)
    duplicate_count: int = Field(default=0, ge=0)
    undone_count: int = Field(default=0, ge=0)


class MemoryIntent(ContractModel):
    decision: MemoryDecision = MemoryDecision.NO_WRITE
    person_id: UUID | None = None
    item_id: str | None = None
    requires_confirmation: bool = False


class RuntimeMetadata(ContractModel):
    warnings: list[str] = Field(default_factory=list)
    provider_name: str | None = None


class AgentResult(ContractModel):
    schema_version: Literal["1"] = "1"
    run_id: UUID
    status: AgentRunStatus
    scenario: ScenarioResult
    safety: SafetyResult
    route: Route
    evidence: FactExtractionResult
    knowledge: KnowledgeRouteResult | None = None
    analysis: AnalysisResult | None = None
    action: ActionPlan | None = None
    memory_intent: MemoryIntent = Field(default_factory=MemoryIntent)
    memory_candidates: list[MemoryCandidate] = Field(default_factory=list)
    memory_receipt: MemoryReceipt = Field(default_factory=MemoryReceipt)
    final_answer: str = Field(min_length=1)
    warnings: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def completed_output(self) -> "AgentResult":
        if self.status != AgentRunStatus.COMPLETED:
            raise ValueError("AgentResult represents a completed run")
        if self.safety.safety_route_required and self.route != Route.SAFETY:
            raise ValueError("high risk must use the safety route")
        if self.memory_candidates and self.memory_intent.decision != MemoryDecision.ALLOW_CANDIDATE:
            raise ValueError("memory candidates require an allow_candidate intent")
        if self.memory_candidates and any(
            candidate.type != "user" and candidate.subject_id != self.memory_intent.person_id
            for candidate in self.memory_candidates
        ):
            raise ValueError("memory candidates must match the intended person")
        return self
