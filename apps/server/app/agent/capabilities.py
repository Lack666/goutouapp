"""Runtime-owned policies for contact refusal and unconnected imported content."""

import re

from app.agent.contact_scope import scope_from_safety
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
    scope = scope_from_safety(state["safety"])
    categories = set(state["safety"].risk_categories) if state["safety"] else set()
    practical = scope in {"dating", "private"} and bool(
        categories & {"necessary_classroom", "necessary_work"}
    )
    if practical:
        text = (
            "尊重对方的拒绝，停止约会邀约、私人追求和额外示好，不另发确认消息。"
            "同班上课或工作中不可避免的互动，只围绕确有必要的课程、作业或工作事务，"
            "简短、礼貌，在公共或正式场合按正常流程处理即可；不制造单独相处机会，"
            "不借事务重启追求。若对方回避或不适，停止非必要互动，保持适当距离。"
            if chinese
            else "Respect the refusal. Stop dating invitations, private pursuit "
            "and extra attention; "
            "do not send an additional acknowledgement. In unavoidable shared classes or work, "
            "keep interactions brief, polite and limited to necessary coursework or work in "
            "public or official settings. Do not create private meetings or use practical "
            "matters to restart pursuit. Respect avoidance or discomfort and stop "
            "optional interaction."
        )
        return ActionPlan(
            contact_policy="stop_contact",
            recommended_action=text,
            supporting_analysis_ids=["A1"],
            stop_conditions=[
                "出现回避或不适时停止非必要互动。"
                if chinese
                else "Stop optional interaction at avoidance or discomfort."
            ],
        )
    return ActionPlan(
        contact_policy="stop_contact",
        recommended_action=(
            "尊重明确拒绝或撤回同意，停止联系。今天先把想说的话写在私密草稿里，"
            "不要发送；离开聊天界面，安排吃饭、休息或散步。情绪难受时找可信的人陪伴，"
            "先照顾自己，不用今天就决定以后。对方没有主动明确改变意愿时，保持停止接触。"
            if chinese
            else "Respect refusal or withdrawn consent. Stop pursuit and all proactive target "
            "contact, including messages through other people or channels. Today, "
            "write your feelings "
            "in a private draft without sending it, close the chat, and make time for a meal, "
            "rest or a walk. Ask someone you trust for company if this feels difficult. "
            "Maintain this no-contact boundary without a free, explicit change of wishes."
        ),
        supporting_analysis_ids=["A1"],
        stop_conditions=[
            "对方没有主动明确改变意愿时，保持停止接触。"
            if chinese
            else "Keep the no-pursuit boundary without a freely and explicitly changed wish."
        ],
    )
