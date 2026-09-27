"""Explicit, serializable business state for future LangGraph nodes."""

from typing import TypedDict
from uuid import UUID, uuid4

from app.agent.contracts import (
    ActionPlan,
    AgentInput,
    AgentRunStatus,
    AnalysisResult,
    ConversationMessage,
    Fact,
    Inference,
    KnowledgeRouteResult,
    LoadedReference,
    MemoryCandidate,
    MemoryControl,
    MemoryIntent,
    MemoryReceipt,
    MemoryRecord,
    Route,
    RuntimeMetadata,
    SafetyResult,
    ScenarioResult,
    Unknown,
)


class UserProfile(TypedDict):
    display_name: str | None
    stated_goals: list[str]


class RelationshipProfile(TypedDict):
    relationship_id: UUID
    person_id: UUID
    relationship_type: str
    status: str


class AgentState(TypedDict):
    run_id: UUID
    run_status: AgentRunStatus
    user_id: UUID
    conversation_id: UUID
    relationship_id: UUID | None
    current_message: str
    messages: list[ConversationMessage]
    locale: str | None
    timezone: str | None
    memory_enabled: bool
    input_metadata: dict[str, str]
    scenario: ScenarioResult | None
    safety: SafetyResult | None
    route: Route | None
    facts: list[Fact]
    inferences: list[Inference]
    unknowns: list[Unknown]
    selected_references: list[str]
    retrieved_context: list[LoadedReference]
    knowledge_route: KnowledgeRouteResult | None
    user_profile: UserProfile | None
    relationship_profile: RelationshipProfile | None
    analysis_result: AnalysisResult | None
    action_plan: ActionPlan | None
    memory_intent: MemoryIntent
    memory_candidates: list[MemoryCandidate]
    memory_control: MemoryControl
    loaded_memories: list[MemoryRecord]
    memory_receipt: MemoryReceipt
    final_answer: str | None
    warnings: list[str]
    runtime_metadata: RuntimeMetadata


def initial_state(request: AgentInput) -> AgentState:
    """Create a fresh state; no dependency or model response object enters it."""
    return AgentState(
        run_id=uuid4(),
        run_status=AgentRunStatus.PENDING,
        user_id=request.user_id,
        conversation_id=request.conversation_id,
        relationship_id=request.relationship_id,
        current_message=request.message,
        messages=list(request.recent_messages),
        locale=request.locale,
        timezone=request.timezone,
        memory_enabled=request.memory_enabled,
        input_metadata=dict(request.metadata),
        scenario=None,
        safety=None,
        route=None,
        facts=[],
        inferences=[],
        unknowns=[],
        selected_references=[],
        retrieved_context=[],
        knowledge_route=None,
        user_profile=None,
        relationship_profile=None,
        analysis_result=None,
        action_plan=None,
        memory_intent=MemoryIntent(),
        memory_candidates=[],
        memory_control=MemoryControl(),
        loaded_memories=[],
        memory_receipt=MemoryReceipt(),
        final_answer=None,
        warnings=[],
        runtime_metadata=RuntimeMetadata(),
    )
