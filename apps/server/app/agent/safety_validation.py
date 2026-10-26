"""Source-limited boundary classification and user-facing safety assembly."""

import re

from app.agent.action_validation import INTERNAL_CUES
from app.agent.contracts import SafetyResult
from app.agent.state import AgentState
from app.observability import emit

# A closed scheduling-only utterance cannot establish withdrawal of contact consent.
# Anything additional, previous context, or any other risk retains the model's gate.
SCHEDULE_ONLY = re.compile(
    r"(?:她|他|对方|TA)说(?:周[一二三四五六日天]|星期[一二三四五六日天]|今天|明天|今晚)"
    r"(?:没空|不方便|没时间)[，,。；; ]*(?:怎么|如何)(?:低压力|礼貌地?|合适地?)?"
    r"(?:约另一天|改约|改期)[？?]?"
)


def verified_safety(result: SafetyResult, state: AgentState) -> SafetyResult:
    if (
        not result.safety_route_required
        and result.risk_categories == ["explicit_refusal"]
        and not state["messages"]
        and SCHEDULE_ONLY.fullmatch(state["current_message"])
    ):
        emit("safety_semantics", decision="schedule_only", removed_category="explicit_refusal")
        return result.model_copy(update={"risk_categories": []})
    return result


def safety_answer(state: AgentState) -> str:
    chinese = bool(re.search(r"[\u3400-\u9fff]", state["current_message"]))
    note = (state["safety"].user_facing_note or "").strip()
    unsafe_instruction = re.search(
        r"(?:你可以|建议你|按以下步骤|you can|you should).{0,20}"
        r"(?:下药|强迫|跟踪|编造|绕过|威胁|drug|stalk)",
        note,
        re.I,
    )
    if (
        note
        and len(note) <= 1000
        and (not chinese or re.search(r"[\u3400-\u9fff]", note))
        and not any(p.search(note) for p in INTERNAL_CUES)
        and not unsafe_instruction
    ):
        return note
    emit("safety_presentation", decision="localized_fallback")
    if chinese:
        return (
            "请先以你和他人的安全为重。若有眼前危险，尽可能前往安全地点、保持安全距离，"
            "并联系可信赖的人或当地紧急服务。你不必独自应对。"
        )
    return (
        "Your safety and others' safety come first. If there is immediate danger, seek a safe "
        "place, keep a safe distance, and contact someone you trust or local emergency services."
    )
