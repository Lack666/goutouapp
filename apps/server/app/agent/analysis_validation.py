"""Structural provenance and scope checks for model-produced analysis."""

import re

from app.agent.content_safety import ContentApproval, require_review
from app.agent.contracts import AnalysisPoint, AnalysisResult, Route
from app.agent.errors import AgentStructuredOutputError
from app.agent.state import AgentState

ACTION_CUES = (
    re.compile(r"(?:你|您)(?:现在|接下来)?(?:应该|需要)"),
    re.compile(r"(?:^|[。.!?\n])\s*(?:请立刻|马上联系|下一步|第一步|回复模板)"),
    re.compile(r"\b(?:send|text|call|message) (?:her|him|them)\b", re.IGNORECASE),
)
UNSUPPORTED_CERTAINTY_CUES = (
    re.compile(r"(?:他|她|TA|对方).{0,10}(?:肯定|一定|必然).{0,8}(?:不爱|爱你|故意|出轨|想分手)"),
    re.compile(r"(?:MBTI|INTJ|INTP|INFJ|ENFJ|回避型|焦虑型).{0,12}(?:一定|必然|注定|证明)"),
)
BOUNDARY_BYPASS_CUES = (
    re.compile(r"(?:突破|破解|绕过).{0,8}(?:拒绝|边界|拉黑)"),
    re.compile(r"(?:换平台|找朋友).{0,8}(?:联系|传话)"),
)


def has_unsupported_certainty(statement: str) -> bool:
    """Lexical review trigger only; quoted/negated assertions are not exempted."""
    return any(pattern.search(statement) for pattern in UNSUPPORTED_CERTAINTY_CUES)


def evidence_ids(state: AgentState) -> set[str]:
    return {
        *(f"F{index}" for index, _ in enumerate(state["facts"], 1)),
        *(f"I{index}" for index, _ in enumerate(state["inferences"], 1)),
        *(f"U{index}" for index, _ in enumerate(state["unknowns"], 1)),
    }


def all_points(result: AnalysisResult) -> list[AnalysisPoint]:
    return [
        *result.observations,
        *result.relationship_dynamics,
        *result.risks,
        *result.constraints,
        *result.uncertainties,
    ]


def validate_analysis(
    result: AnalysisResult, state: AgentState, *, approval: ContentApproval | None = None
) -> None:
    """Validate IDs and roles; semantic entailment remains a separate eval."""
    valid_evidence = evidence_ids(state)
    valid_references = {reference.alias for reference in state["retrieved_context"]}
    points = all_points(result)
    if not points or not valid_references:
        raise AgentStructuredOutputError() from None
    if not result.insufficient_evidence and not (
        result.core_evidence_ids or result.core_reference_ids
    ):
        raise AgentStructuredOutputError() from None
    if (
        not set(result.core_evidence_ids) <= valid_evidence
        or not set(result.core_reference_ids) <= valid_references
    ):
        raise AgentStructuredOutputError() from None
    if not (set(result.core_reference_ids) | set().union(*(set(p.reference_ids) for p in points))):
        raise AgentStructuredOutputError() from None
    if valid_evidence and not any(point.evidence_ids for point in points):
        raise AgentStructuredOutputError() from None
    for point in points:
        if (
            not set(point.evidence_ids) <= valid_evidence
            or not set(point.reference_ids) <= valid_references
        ):
            raise AgentStructuredOutputError() from None
    if state["route"] == Route.BOUNDARY and not any(
        point.dimension == "boundary" for point in points
    ):
        raise AgentStructuredOutputError() from None
    # Lexical cues select review, not a semantic verdict or a quotation whitelist.
    patterns = (*ACTION_CUES, *UNSUPPORTED_CERTAINTY_CUES, *BOUNDARY_BYPASS_CUES)
    if any(
        pattern.search(statement)
        for statement in (result.core_issue, *(point.statement for point in points))
        for pattern in patterns
    ):
        require_review(result, state, approval)
