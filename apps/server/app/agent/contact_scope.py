"""Semantic contact policy v1; existing SafetyResult category vocabulary only.

See docs/PHASE_11R_CONTRACT.md. Legacy/unresolved boundaries fail closed.
These categories never override a high-risk route or authorize an outbound message.
"""

from app.agent.contracts import SafetyResult

POLICY_VERSION = "phase11r-contact-v1"
HIGH_RISK_CATEGORIES = frozenset(
    {
        "self_harm",
        "violence",
        "coercion",
        "stalking",
        "non_consensual",
        "manipulation",
        "fraud",
        "privacy_legal",
    }
)
NORMAL_CATEGORIES = frozenset(
    {
        "explicit_refusal",
        "consent_withdrawal",
        "refusal_dating",
        "refusal_private",
        "refusal_all",
        "refusal_unknown",
        "user_exit",
        "schedule_only",
        "necessary_classroom",
        "necessary_work",
    }
)
REFUSAL_CATEGORIES = frozenset(
    {
        "explicit_refusal",
        "consent_withdrawal",
        "refusal_dating",
        "refusal_private",
        "refusal_all",
        "refusal_unknown",
    }
)


def scope_from_safety(safety: SafetyResult | None) -> str:
    if safety is None:
        return "unknown"
    categories = set(safety.risk_categories)
    if categories - NORMAL_CATEGORIES:
        return "unknown"
    if "consent_withdrawal" in categories or "refusal_unknown" in categories:
        return "unknown"
    if "refusal_all" in categories:
        return "all"
    if "refusal_private" in categories:
        return "private"
    if "refusal_dating" in categories:
        return "dating"
    if "explicit_refusal" in categories:
        return "unknown"
    if "user_exit" in categories:
        return "user_exit"
    if "schedule_only" in categories:
        return "schedule"
    return "none"
