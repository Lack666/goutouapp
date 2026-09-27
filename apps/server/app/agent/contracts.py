"""JSON-safe public values for a future standalone Agent runtime."""

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


class AnalysisResult(ContractModel):
    core_issue: str = Field(min_length=1)
    observations: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)


class ActionPlan(ContractModel):
    recommended_action: str = Field(min_length=1)
    message_suggestion: str | None = None
    observation_window: str | None = None
    stop_conditions: list[str] = Field(default_factory=list)


class MemoryCandidate(ContractModel):
    subject_id: UUID
    type: str = Field(min_length=1)
    content: str = Field(min_length=1)
    source: str = Field(min_length=1)
    evidence: str = Field(min_length=1)
    confidence: float | None = Field(default=None, ge=0, le=1)
    requires_consent: Literal[True] = True


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
        if self.memory_candidates and (
            self.memory_intent.person_id is None
            or any(
                candidate.subject_id != self.memory_intent.person_id
                for candidate in self.memory_candidates
            )
        ):
            raise ValueError("memory candidates must match the intended person")
        return self
