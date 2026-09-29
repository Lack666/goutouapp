"""Memory graph nodes; no direct SQLAlchemy access or response edits."""

import re
from typing import TypedDict

from app.agent.contracts import (
    MemoryCandidate,
    MemoryCandidateBatch,
    MemoryControl,
    MemoryDecision,
    MemoryIntent,
    MemoryReceipt,
    MemoryRecord,
    MemoryWriteStatus,
)
from app.agent.dependencies import RuntimeDependencies
from app.agent.memory import (
    asks_to_save,
    explicit_save_consent,
    prohibited_request,
    validate_candidate,
)
from app.agent.prompts import memory
from app.agent.state import AgentState
from app.llm.models import LLMMessage


class LoadMemoryUpdate(TypedDict):
    loaded_memories: list[MemoryRecord]
    memory_control: MemoryControl
    warnings: list[str]


class MemoryIntentUpdate(TypedDict):
    memory_intent: MemoryIntent
    warnings: list[str]


class CandidateUpdate(TypedDict):
    memory_candidates: list[MemoryCandidate]
    memory_receipt: MemoryReceipt
    warnings: list[str]


class PersistUpdate(TypedDict):
    memory_receipt: MemoryReceipt
    warnings: list[str]


def load_memory(state: AgentState, dependencies: RuntimeDependencies) -> LoadMemoryUpdate:
    service = dependencies.memory_service
    if service is None or not state["memory_enabled"]:
        return {
            "loaded_memories": [],
            "memory_control": MemoryControl(),
            "warnings": state["warnings"],
        }
    try:
        return {
            "loaded_memories": service.load_for_context(
                state["user_id"], state["relationship_id"], enabled=True
            ),
            "memory_control": service.control(state["user_id"]),
            "warnings": state["warnings"],
        }
    except Exception:
        return {
            "loaded_memories": [],
            "memory_control": MemoryControl(),
            "warnings": [*state["warnings"], "Long-term memory was unavailable"],
        }


def resolve_memory_intent(
    state: AgentState, dependencies: RuntimeDependencies
) -> MemoryIntentUpdate:
    service = dependencies.memory_service
    warnings = state["warnings"]
    if service is None or not state["memory_enabled"] or state["route"].value == "safety":
        return {"memory_intent": MemoryIntent(), "warnings": warnings}
    message = state["current_message"]
    try:
        person_id = service.resolve_person(state["user_id"], state["relationship_id"])
    except Exception:
        return {
            "memory_intent": MemoryIntent(),
            "warnings": [*warnings, "Long-term memory was unavailable"],
        }
    if "撤回" in message and ("删除全部" in message or "全部长期" in message):
        intent = MemoryIntent(
            decision=MemoryDecision.REVOKE_AND_DELETE_ALL, requires_confirmation=True
        )
    elif "撤回" in message and "同意" in message:
        intent = MemoryIntent(decision=MemoryDecision.REVOKE_KEEP)
    elif "撤销" in message and "记忆" in message:
        intent = MemoryIntent(
            decision=MemoryDecision.UNDO,
            requires_confirmation=state["guarded_undo_required"],
        )
    elif "恢复" in message and "记忆" in message:
        intent = MemoryIntent(decision=MemoryDecision.RESUME)
    elif "暂停" in message and "记忆" in message:
        intent = MemoryIntent(decision=MemoryDecision.PAUSE)
    elif ("删除" in message or "清空" in message) and (
        "全部" in message or "所有" in message or "清空" in message
    ):
        intent = MemoryIntent(decision=MemoryDecision.DELETE_ALL, requires_confirmation=True)
    elif "删除" in message and "编号" in message:
        match = re.search(r"编号\s*([\w-]+)", message)
        intent = MemoryIntent(
            decision=MemoryDecision.DELETE_ITEM,
            person_id=person_id,
            item_id=match.group(1) if match else None,
        )
    elif "删除" in message and "对象" in message:
        intent = MemoryIntent(
            decision=MemoryDecision.DELETE_PERSON, person_id=person_id, requires_confirmation=True
        )
    elif "查看" in message and ("记忆" in message or "档案" in message):
        intent = MemoryIntent(decision=MemoryDecision.INSPECT)
    elif (
        not prohibited_request(message)
        and asks_to_save(message)
        and (explicit_save_consent(message) or state["memory_control"].consent_enabled)
    ):
        intent = MemoryIntent(decision=MemoryDecision.ALLOW_CANDIDATE, person_id=person_id)
    else:
        intent = MemoryIntent(person_id=person_id)
    return {"memory_intent": intent, "warnings": warnings}


async def memory_candidate_extractor(
    state: AgentState, dependencies: RuntimeDependencies
) -> CandidateUpdate:
    intent = state["memory_intent"]
    service = dependencies.memory_service
    if service is None or intent.decision != MemoryDecision.ALLOW_CANDIDATE:
        return {
            "memory_candidates": [],
            "memory_receipt": MemoryReceipt(),
            "warnings": state["warnings"],
        }
    if state["memory_control"].paused:
        return {
            "memory_candidates": [],
            "memory_receipt": MemoryReceipt(status=MemoryWriteStatus.SKIPPED_PAUSED),
            "warnings": state["warnings"],
        }
    try:
        result = await dependencies.llm_provider.structured_output(
            [
                LLMMessage(role="system", content=memory.SYSTEM),
                LLMMessage(role="user", content=memory.input_payload(state)),
            ],
            MemoryCandidateBatch,
        )
        if not isinstance(result, MemoryCandidateBatch):
            raise ValueError("invalid candidate batch")
        if any(
            not validate_candidate(
                item,
                facts=state["facts"],
                message=state["current_message"],
                person_id=intent.person_id,
                user_id=state["user_id"],
            )
            for item in result.candidates
        ):
            return {
                "memory_candidates": [],
                "memory_receipt": MemoryReceipt(status=MemoryWriteStatus.REJECTED_VALIDATION),
                "warnings": [*state["warnings"], "Long-term memory was not saved"],
            }
        return {
            "memory_candidates": result.candidates,
            "memory_receipt": MemoryReceipt(),
            "warnings": state["warnings"],
        }
    except Exception:
        return {
            "memory_candidates": [],
            "memory_receipt": MemoryReceipt(status=MemoryWriteStatus.FAILED),
            "warnings": [*state["warnings"], "Long-term memory was not saved"],
        }


def persist_memory(state: AgentState, dependencies: RuntimeDependencies) -> PersistUpdate:
    service = dependencies.memory_service
    receipt = state["memory_receipt"]
    intent = state["memory_intent"]
    warnings = state["warnings"]
    if service is None:
        return {"memory_receipt": receipt, "warnings": warnings}
    try:
        if (
            state["memory_enabled"]
            and asks_to_save(state["current_message"])
            and not prohibited_request(state["current_message"])
            and explicit_save_consent(state["current_message"])
        ):
            service.grant_consent(state["user_id"], confirmed=True)
        if receipt.status != MemoryWriteStatus.NONE:
            return {"memory_receipt": receipt, "warnings": warnings}
        if intent.decision == MemoryDecision.ALLOW_CANDIDATE:
            receipt = service.persist_candidates(
                user_id=state["user_id"],
                relationship_id=state["relationship_id"],
                run_id=state["run_id"],
                candidates=state["memory_candidates"],
                facts=state["facts"],
                message=state["current_message"],
                explicit_consent=explicit_save_consent(state["current_message"]),
            )
        elif intent.decision in {
            MemoryDecision.PAUSE,
            MemoryDecision.RESUME,
            MemoryDecision.REVOKE_KEEP,
        }:
            receipt = service.apply_control(state["user_id"], intent.decision)
        elif intent.decision == MemoryDecision.UNDO:
            receipt = (
                MemoryReceipt(status=MemoryWriteStatus.PENDING_CONFIRMATION)
                if intent.requires_confirmation
                else service.undo_last(state["user_id"])
            )
        elif intent.decision in {
            MemoryDecision.DELETE_ITEM,
            MemoryDecision.DELETE_PERSON,
            MemoryDecision.DELETE_ALL,
            MemoryDecision.REVOKE_AND_DELETE_ALL,
        }:
            receipt = MemoryReceipt(status=MemoryWriteStatus.PENDING_CONFIRMATION)
    except Exception:
        return {
            "memory_receipt": MemoryReceipt(status=MemoryWriteStatus.FAILED),
            "warnings": [*warnings, "Long-term memory was not saved"],
        }
    if receipt.status in {
        MemoryWriteStatus.REJECTED_VALIDATION,
        MemoryWriteStatus.SKIPPED_NO_CONSENT,
    }:
        warnings = [*warnings, "Long-term memory was not saved"]
    return {"memory_receipt": receipt, "warnings": warnings}
