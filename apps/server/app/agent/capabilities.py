"""Runtime-owned policies for contact refusal and unconnected imported content."""

import re

from app.agent.contracts import ActionPlan, Route
from app.agent.state import AgentState


def imported_chat_reply(message: str) -> str:
    if re.search(r"[\u3400-\u9fff]", message):
        return (
            "当前 Agent 未接入导入聊天或上传文件，不能访问已导入会话，也不能引用其中的消息。"
            "如果愿意，你可以在当前对话直接提供少量经授权、去标识化的相关原文，"
            "并明确说话人身份和消息范围。"
            "缺少直接提供的原文时，不猜测具体条目或聊天趋势。"
        )
    return (
        "This Agent has no connection to imported chats or uploaded files and cannot access or "
        "cite their messages. You may paste a small, authorized, anonymized excerpt directly "
        "here, identifying speakers and scope. Without that text, do not infer entries or trends."
    )


def imported_chat_plan(state: AgentState) -> ActionPlan:
    text = imported_chat_reply(state["current_message"])
    boundary = state["route"] == Route.BOUNDARY
    action = (
        "尊重拒绝，停止继续接触。" if "当前 Agent" in text else "Respect refusal. Stop pursuit. "
    )
    return ActionPlan(
        contact_policy="stop_contact" if boundary else "observe",
        recommended_action=action + text if boundary else text,
        supporting_analysis_ids=["A1"],
        message_suggestion=None,
        observation_window=(
            "在当前对话提供授权原文并明确说话人和范围之前暂停。"
            if "当前 Agent" in text
            else "Pause until authorized text, speakers and scope are supplied directly here."
        ),
        stop_conditions=[
            "缺少当前对话直接提供的授权原文时，停止引用或趋势推断。"
            if "当前 Agent" in text
            else "Without authorized text supplied directly here, stop citation or trend inference."
        ],
    )


def boundary_plan(state: AgentState) -> ActionPlan:
    chinese = bool(re.search(r"[\u3400-\u9fff]", state["current_message"]))
    return ActionPlan(
        contact_policy="stop_contact",
        recommended_action=(
            "尊重明确拒绝或撤回同意，停止联系。请优先照顾自己的情绪与日常生活，"
            "寻求可靠支持。未经明确主动改变意愿，保持这一边界。"
            if chinese
            else "Respect refusal or withdrawn consent. Stop pursuit and focus on your own life. "
            "Keep this boundary without a free, explicit change of wishes; "
            "seek trusted support if this is difficult."
        ),
        supporting_analysis_ids=["A1"],
        stop_conditions=[
            "对方没有主动明确改变意愿时，保持停止接触。"
            if chinese
            else "Keep the no-pursuit boundary without a freely and explicitly changed wish."
        ],
    )
