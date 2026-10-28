"""Conservative, high-precision guards for generated actions and answers."""

import re

from app.agent.analysis_validation import UNSUPPORTED_CERTAINTY_CUES, all_points
from app.agent.capabilities import imported_chat_reply
from app.agent.contact_scope import scope_from_safety
from app.agent.content_safety import (
    CONTACT_CUES as CONTACT_CUES,
)
from app.agent.content_safety import (
    ContentApproval,
    candidate_fields,
    is_controlled_candidate,
    require_review,
    requires_contact_review,
)
from app.agent.contracts import ActionPlan, ResponseResult, Route, Scenario
from app.agent.errors import AgentStructuredOutputError
from app.agent.state import AgentState

HARMFUL_CUES = (
    re.compile(r"(?:绕过|突破|破解|试探).{0,12}(?:拒绝|拉黑|边界|同意)"),
    re.compile(r"(?:换(?:个)?(?:平台|号码)|找朋友|借号).{0,12}(?:联系|传话|私信)"),
    re.compile(r"(?:假装|编造|捏造|谎称|冒充|装作).{0,14}(?:经历|生病|忙|家人|身份|没事)?"),
    re.compile(r"(?:冷暴力|欲擒故纵|制造嫉妒|操控|继续施压|威胁|跟踪|查手机|监控)"),
    re.compile(r"\b(?:bypass (?:refusal|block)|impersonate|stalk|manipulate)\b", re.I),
    re.compile(
        r"(?:欺骗|说谎|下药|强迫|胁迫|偷拍|勒索|曝光|诈骗|服从测试|煤气灯|孤立|"
        r"制造依赖|报复|自伤|自杀|伤害|醉酒|无意识|账号|账户|定位|跟随|尾随)"
    ),
    re.compile(
        r"\b(?:deceiv\w*|lie|lying|excuse|coerc\w*|blackmail|surveill\w*|gaslight\w*|"
        r"fraud|threat\w*|drug\w*)\b",
        re.I,
    ),
)
INTERNAL_CUES = (
    re.compile(r"\b(?:run_id|chain.of.thought|system prompt|analysis_point_ids)\b", re.I),
    re.compile(r"(?<![A-Za-z0-9])(?:F|I|U)\d+\b"),
    re.compile(r"(?<![A-Za-z0-9])(?:A)\d+\b"),
    re.compile(r"\bK\d{2}\b"),
    re.compile(r"(?:API_KEY|Bearer\s+[A-Za-z0-9._-]+)"),
    re.compile(r"(?:references/|knowledge/goutoujunshi/|\.env\b)", re.I),
)
UNVERIFIED_CUES = (
    re.compile(r"(?:我已|已经)(?:核实|查证|导出|保存|查询)(?:了)?(?:对方|聊天|资料|法律|记忆)"),
    re.compile(r"(?:研究|论文|专家)(?:明确)?(?:证明|表明).{0,25}(?:爱|喜欢|分手|关系)"),
)
UNKNOWN_MOTIVE_CUES = (
    re.compile(r"(?:他|她|TA|对方).{0,6}(?:已经失去兴趣|已经不爱|一定喜欢|肯定喜欢|故意冷落)"),
)
PERSONAL_EXPERIENCE_CUES = (
    re.compile(
        r"(?:我|你|您|我们|咱们|你们|双方).{0,6}(?:之前|以前|过去|上次|曾经|平时|经常|总是)"
    ),
    re.compile(
        r"\b(?:I|you|we|both of you)\b.{0,24}"
        r"\b(?:used to|usually|often|always|last time|previously)\b",
        re.I,
    ),
)


def _validate_text_encoding(texts: list[str]) -> None:
    if any(
        char == "\ufffd" or (ord(char) < 32 and char not in "\n\r\t")
        for text in texts
        for char in text
    ):
        raise AgentStructuredOutputError() from None


def has_safety_cues(text: str) -> bool:
    # A review trigger, never a semantic verdict; no sentence/negation exemptions.
    return any(
        pattern.search(text)
        for pattern in (
            *HARMFUL_CUES,
            *PERSONAL_EXPERIENCE_CUES,
            *UNSUPPORTED_CERTAINTY_CUES,
            *UNKNOWN_MOTIVE_CUES,
            *UNVERIFIED_CUES,
        )
    )


def analysis_ids(state: AgentState) -> set[str]:
    analysis = state["analysis_result"]
    return {f"A{index}" for index, _ in enumerate(all_points(analysis), 1)} if analysis else set()


def _reject_if_cued(texts: list[str], patterns: tuple[re.Pattern[str], ...]) -> None:
    if any(pattern.search(value) for value in texts for pattern in patterns):
        raise AgentStructuredOutputError() from None


def validate_action(
    plan: ActionPlan, state: AgentState, *, approval: ContentApproval | None = None
) -> None:
    _validate_text_encoding(list(candidate_fields(plan).values()))
    if state["route"] not in {Route.ORDINARY, Route.BOUNDARY} or not state["analysis_result"]:
        raise AgentStructuredOutputError() from None
    if state["safety"] and state["safety"].safety_route_required:
        raise AgentStructuredOutputError() from None
    if (
        scope_from_safety(state["safety"]) in {"dating", "private", "all", "unknown"}
        and state["route"] != Route.BOUNDARY
    ):
        raise AgentStructuredOutputError() from None
    if scope_from_safety(state["safety"]) == "user_exit" and plan.contact_policy in {
        "reply",
        "invite",
    }:
        raise AgentStructuredOutputError() from None
    if not set(plan.supporting_analysis_ids) <= analysis_ids(state) or len(
        set(plan.supporting_analysis_ids)
    ) != len(plan.supporting_analysis_ids):
        raise AgentStructuredOutputError() from None
    _reject_if_cued(
        [plan.recommended_action, plan.message_suggestion or ""],
        INTERNAL_CUES,
    )
    _reject_if_cued([plan.observation_window or "", *plan.stop_conditions], INTERNAL_CUES)
    if state["route"] == Route.BOUNDARY:
        if plan.contact_policy != "stop_contact" or plan.message_suggestion is not None:
            raise AgentStructuredOutputError() from None
        if not is_controlled_candidate(plan, state):
            raise AgentStructuredOutputError() from None
    elif (
        plan.contact_policy == "stop_contact" and scope_from_safety(state["safety"]) != "user_exit"
    ):
        # Voluntary exit is not permission to invent a refusal by the other person.
        raise AgentStructuredOutputError() from None
    if plan.contact_policy in {"observe", "pause", "stop_contact"} and plan.message_suggestion:
        raise AgentStructuredOutputError() from None
    if plan.contact_policy in {"reply", "invite"} and not plan.message_suggestion:
        raise AgentStructuredOutputError() from None
    if (
        state["scenario"]
        and state["scenario"].primary == Scenario.REPLY
        and state["route"] != Route.BOUNDARY
        and scope_from_safety(state["safety"]) != "user_exit"
        and plan.contact_policy != "reply"
    ):
        raise AgentStructuredOutputError() from None
    if plan.contact_policy == "observe" and not plan.observation_window:
        raise AgentStructuredOutputError() from None
    if plan.contact_policy in {"observe", "pause", "stop_contact"} and not plan.stop_conditions:
        raise AgentStructuredOutputError() from None
    if state["scenario"] and state["scenario"].primary == Scenario.CHAT_IMPORT:
        if not plan.stop_conditions or not all(s.strip() for s in plan.stop_conditions):
            raise AgentStructuredOutputError() from None
        if imported_chat_reply(state["current_message"]) not in (
            plan.message_suggestion or plan.recommended_action
        ):
            raise AgentStructuredOutputError() from None
    if not is_controlled_candidate(plan, state) and (
        requires_contact_review(plan, state)
        or any(has_safety_cues(v) for v in candidate_fields(plan).values())
    ):
        require_review(plan, state, approval)


def validate_response(
    response: ResponseResult, state: AgentState, *, approval: ContentApproval | None = None
) -> None:
    _validate_text_encoding([response.final_answer])
    plan = state["action_plan"]
    if plan is None or response.contact_policy != plan.contact_policy:
        raise AgentStructuredOutputError() from None
    if state["route"] not in {Route.ORDINARY, Route.BOUNDARY} or (
        state["safety"] and state["safety"].safety_route_required
    ):
        raise AgentStructuredOutputError() from None
    if state["route"] == Route.BOUNDARY and not is_controlled_candidate(response, state):
        raise AgentStructuredOutputError() from None
    if scope_from_safety(state["safety"]) == "user_exit" and plan.contact_policy in {
        "reply",
        "invite",
    }:
        raise AgentStructuredOutputError() from None
    answer = response.final_answer.strip()
    _reject_if_cued([answer], INTERNAL_CUES)
    if state["scenario"] and state["scenario"].primary == Scenario.CHAT_IMPORT:
        if answer != (plan.message_suggestion or plan.recommended_action):
            raise AgentStructuredOutputError() from None
    if plan.message_suggestion and plan.message_suggestion not in answer:
        raise AgentStructuredOutputError() from None
    if not plan.message_suggestion and plan.recommended_action not in answer:
        raise AgentStructuredOutputError() from None
    if (
        state["scenario"]
        and state["scenario"].primary == Scenario.REPLY
        and plan.message_suggestion
        and not answer.startswith(plan.message_suggestion)
    ):
        raise AgentStructuredOutputError() from None
    if plan.contact_policy == "stop_contact":
        if state["route"] == Route.BOUNDARY and not is_controlled_candidate(response, state):
            raise AgentStructuredOutputError() from None
    if not is_controlled_candidate(response, state) and (
        requires_contact_review(response, state) or has_safety_cues(answer)
    ):
        require_review(response, state, approval)
