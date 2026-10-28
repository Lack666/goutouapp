"""Source-limited boundary classification and user-facing safety assembly."""

import re

from app.agent.contact_scope import HIGH_RISK_CATEGORIES
from app.agent.contracts import SafetyResult
from app.agent.errors import AgentStructuredOutputError
from app.agent.state import AgentState
from app.observability import emit


def verified_safety(result: SafetyResult, state: AgentState) -> SafetyResult:
    if not result.safety_route_required and HIGH_RISK_CATEGORIES.intersection(
        result.risk_categories
    ):
        # Contradictory live classifications cannot silently choose ordinary advice.
        raise AgentStructuredOutputError() from None
    if result.safety_route_required:
        note = protective_safety_answer(result, state["current_message"])
        if result.user_facing_note != note:
            emit("safety_presentation", decision="candidate_replaced", policy="protective_v1")
        return result.model_copy(update={"user_facing_note": note})
    return result


def protective_safety_answer(result: SafetyResult, message: str) -> str:
    """High-risk presentation is controlled protection, not generated relationship advice.

    Categories select policy text, never interpolate model/user text. Conditions distinguish
    a person facing harm from one proposing harm; support contacts are not pursuit contacts.
    """
    if not result.safety_route_required:
        raise AgentStructuredOutputError() from None
    chinese = bool(re.search(r"[\u3400-\u9fff]", message))
    categories = set(result.risk_categories)
    if chinese:
        parts = ["请先以你和他人的安全为重，现在不做关系推进或挽回。"]
        if "self_harm" in categories:
            parts.append(
                "如果你可能伤害自己，请先远离可能伤人的物品，尽量不要独处，"
                "联系能陪在你身边的可信赖的人。"
            )
        if categories & {"violence", "coercion", "stalking", "non_consensual"}:
            parts.append(
                "如果你正打算伤害、威胁、跟踪他人或进行未经同意的接触，请立即停止，"
                "放下可能伤人的物品并离开接触现场，不换渠道继续接触。"
                "若你正遭受这些行为，不必与对方单独对质、解释或修复关系。"
            )
        if categories & {"fraud", "privacy_legal"}:
            parts.append(
                "先停止有风险的转账、账号共享、定位或私密内容传递，"
                "不必为维持关系而配合；只在安全前提下保留你有权保存的记录。"
            )
        if "manipulation" in categories:
            parts.append("不能用欺骗、羞辱或制造依赖来维系关系，也不绕过拒绝。")
        parts.append(
            "若有眼前危险，尽可能前往安全地点、保持安全距离，"
            "并联系可信赖的人或当地紧急服务。你不必独自应对。你目前是否在安全的地方？"
        )
        return "".join(parts)
    parts = [
        "Your safety and others' safety come first. Pause relationship pursuit or reconciliation."
    ]
    if "self_harm" in categories:
        parts.append(
            "If you might hurt yourself, move away from objects you could use to do so, "
            "avoid being alone if possible, and ask a trusted person to stay with you."
        )
    if categories & {"violence", "coercion", "stalking", "non_consensual"}:
        parts.append(
            "If you are planning harm, threats, stalking or non-consensual contact, stop, "
            "put down objects that could hurt someone and leave the contact situation. "
            "Do not switch channels to continue contact. If someone is doing this to you, "
            "you do not need to confront them alone or repair the relationship."
        )
    if categories & {"fraud", "privacy_legal"}:
        parts.append(
            "Stop risky transfers, account sharing, location tracking or private-content sharing. "
            "You do not owe these to maintain a relationship. Preserve only records you may "
            "lawfully keep and only when safe."
        )
    if "manipulation" in categories:
        parts.append("Do not use deception, humiliation or dependency, or bypass a refusal.")
    parts.append(
        "If there is immediate danger, seek a safe place, keep a safe distance, and contact "
        "someone you trust or local emergency services. Are you in a safe place now?"
    )
    return " ".join(parts)


def validate_safety_answer(answer: str, state: AgentState) -> None:
    """Publication requires the same controlled policy in both public answer fields."""
    result = state["safety"]
    if result is None:
        raise AgentStructuredOutputError() from None
    expected = protective_safety_answer(result, state["current_message"])
    if answer != expected or result.user_facing_note != expected:
        emit("safety_presentation", decision="publication_rejected", policy="protective_v1")
        raise AgentStructuredOutputError() from None


def safety_answer(state: AgentState) -> str:
    result = state["safety"]
    if result is None:
        raise AgentStructuredOutputError() from None
    answer = protective_safety_answer(result, state["current_message"])
    validate_safety_answer(answer, state)
    return answer
