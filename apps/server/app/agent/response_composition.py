"""Compose an approved step without trusting a model to transcribe it exactly."""

from pydantic import ValidationError

from app.agent.contracts import ResponseResult, Scenario
from app.agent.errors import AgentStructuredOutputError
from app.agent.state import AgentState
from app.observability import emit


def compose_response(candidate: ResponseResult, state: AgentState) -> ResponseResult:
    plan = state["action_plan"]
    if plan is None or candidate.contact_policy != plan.contact_policy:
        raise AgentStructuredOutputError() from None
    required = plan.message_suggestion or plan.recommended_action
    answer = candidate.final_answer
    reply = bool(state["scenario"] and state["scenario"].primary == Scenario.REPLY)
    changed = required not in answer or (reply and not answer.strip().startswith(required))
    emit("response_composition", changed=changed, retries=0)
    if changed:
        # Keep the entire candidate for subsequent guards; never discard a bad clause.
        try:
            candidate = ResponseResult(
                final_answer=f"{required}\n\n{answer}", contact_policy=candidate.contact_policy
            )
        except ValidationError:
            # Preserve the formal length limit without leaking private exception inputs.
            raise AgentStructuredOutputError() from None
    return candidate
