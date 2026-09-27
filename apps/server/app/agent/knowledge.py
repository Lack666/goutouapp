"""Deterministic knowledge routing and bounded reads from the frozen snapshot."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from app.agent.contracts import (
    KnowledgeRouteResult,
    LoadedReference,
    Route,
    SafetyResult,
    Scenario,
    ScenarioResult,
)
from app.agent.errors import AgentKnowledgeError

PROJECT_ROOT = Path(__file__).resolve().parents[4]
KNOWLEDGE_ROOT = PROJECT_ROOT / "knowledge/goutoujunshi"
REFERENCE_MAP = PROJECT_ROOT / "evals/reference_map.json"
UPSTREAM_MANIFEST = PROJECT_ROOT / "knowledge/upstream-manifest.json"

SCENARIO_ALIASES: dict[Scenario, str] = {
    Scenario.REPLY: "reply",
    Scenario.FLIRT: "flirt",
    Scenario.RELATIONSHIP: "relationship",
    Scenario.IMBALANCE: "imbalance",
    Scenario.CONFLICT: "conflict",
    Scenario.BREAKUP: "breakup",
    Scenario.LONG_TERM: "family",
    Scenario.HOUSEHOLD: "money",
    Scenario.ONLINE: "online",
    Scenario.CHAT_IMPORT: "chat_import",
    Scenario.PERSONALITY: "mbti",
    Scenario.SOCIAL_SYSTEM: "social_system",
    Scenario.PUA: "pua",
    Scenario.CONSENT: "consent",
    Scenario.DIVERSITY: "diversity",
    Scenario.SOCIAL_OTHER: "social_intro",
    Scenario.MEMORY: "memory",
    Scenario.SAFETY: "safety",
    Scenario.INVITATION: "first_date",
}


@dataclass(frozen=True)
class ReferenceEntry:
    alias: str
    source_id: str
    title: str
    category: str
    source_type: str
    sha256: str


@dataclass(frozen=True)
class ContextBudget:
    max_references: int = 3
    max_document_chars: int = 4000
    max_total_chars: int = 9000

    def __post_init__(self) -> None:
        if (
            not 1 <= self.max_references <= 3
            or min(self.max_document_chars, self.max_total_chars) < 1
        ):
            raise AgentKnowledgeError("Invalid knowledge context budget")


class ReferenceRegistry:
    """Only app-owned aliases backed by the frozen manifest can be resolved."""

    def __init__(
        self,
        *,
        root: Path = KNOWLEDGE_ROOT,
        mapping_path: Path = REFERENCE_MAP,
        manifest_path: Path = UPSTREAM_MANIFEST,
    ) -> None:
        try:
            self.root = root.resolve(strict=True)
            mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
            hashes = json.loads(manifest_path.read_text(encoding="utf-8"))["files"]
            if not isinstance(mapping, dict) or not mapping:
                raise ValueError("invalid reference map")
            entries: dict[str, ReferenceEntry] = {}
            seen_paths: set[str] = set()
            for alias, source_id in mapping.items():
                if not isinstance(alias, str) or not alias.isidentifier():
                    raise ValueError("invalid reference alias")
                path = self._safe_path(source_id)
                if source_id in seen_paths or source_id not in hashes:
                    raise ValueError("reference is duplicated or absent from frozen manifest")
                seen_paths.add(source_id)
                family = PurePosixPath(source_id).parts[1]
                entries[alias] = ReferenceEntry(
                    alias=alias,
                    source_id=source_id,
                    title=path.stem,
                    category=alias,
                    source_type=family,
                    sha256=hashes[source_id],
                )
            self.entries = entries
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise AgentKnowledgeError("Reference registry is invalid") from exc

    def _safe_path(self, source_id: str) -> Path:
        if not isinstance(source_id, str) or "\\" in source_id or ":" in source_id:
            raise ValueError("invalid source identifier")
        relative = PurePosixPath(source_id)
        if (
            relative.is_absolute()
            or relative.as_posix() != source_id
            or len(relative.parts) != 3
            or relative.parts[0] != "references"
            or relative.parts[1] not in {"knowledge", "practical"}
            or relative.suffix != ".md"
            or any(part in {".", ".."} for part in source_id.split("/"))
        ):
            raise ValueError("source outside reference tree")
        path = (self.root / Path(*relative.parts)).resolve(strict=True)
        if not path.is_relative_to(self.root) or not path.is_file():
            raise ValueError("source outside frozen knowledge tree")
        return path

    def get(self, alias: str) -> ReferenceEntry:
        if not isinstance(alias, str) or alias not in self.entries:
            raise AgentKnowledgeError("Unknown reference alias")
        entry = self.entries[alias]
        try:
            self._safe_path(entry.source_id)
        except (OSError, ValueError) as exc:
            raise AgentKnowledgeError("Reference source is unavailable") from exc
        return entry

    def read(self, alias: str) -> tuple[ReferenceEntry, str]:
        entry = self.get(alias)
        try:
            raw = self._safe_path(entry.source_id).read_bytes()
            if hashlib.sha256(raw).hexdigest() != entry.sha256:
                raise ValueError("frozen reference hash mismatch")
            content = raw.decode("utf-8")
            if not content:
                raise ValueError("empty frozen reference")
            return entry, content
        except (OSError, UnicodeError, ValueError) as exc:
            raise AgentKnowledgeError("Reference content is unavailable") from exc

    def validate_integrity(self) -> None:
        for alias in self.entries:
            self.read(alias)


def route_knowledge(
    *,
    safety: SafetyResult,
    route: Route,
    scenario: ScenarioResult | None,
    current_message: str,
    max_references: int = 3,
) -> KnowledgeRouteResult:
    """Choose one primary alias; limited topic cues refine broad scenario labels."""
    if route == Route.SAFETY or safety.safety_route_required:
        alias, reason = "safety", "High risk requires the safety reference first"
    else:
        if scenario is None or scenario.primary == Scenario.SAFETY:
            raise AgentKnowledgeError("Scenario is unavailable for ordinary routing")
        primary = scenario.primary
        alias = SCENARIO_ALIASES[primary]
        reason = f"Primary scenario: {primary.value}"
        if route == Route.BOUNDARY and primary not in {Scenario.BREAKUP, Scenario.CONSENT}:
            alias, reason = "consent", "Boundary route takes consent priority"
        elif primary == Scenario.INVITATION and "想具体约" in current_message:
            alias, reason = "reply", "Invitation phrasing is the current task"
        elif (
            primary == Scenario.PERSONALITY
            and any(cue in current_message for cue in ("依恋", "回避型", "焦虑型"))
            and not any(cue in current_message.upper() for cue in ("MBTI", "INTJ", "INTP"))
        ):
            alias, reason = "attachment", "Attachment is the explicit topic"
        elif primary == Scenario.RELATIONSHIP and any(
            cue in current_message for cue in ("文章", "论文", "研究")
        ):
            alias, reason = "evidence", "Research evidence is the explicit topic"
    return KnowledgeRouteResult(
        selected_references=[alias],
        primary_reference=alias,
        reason_summary=reason,
        max_references=max_references,
    )


def load_references(
    aliases: list[str],
    registry: ReferenceRegistry,
    budget: ContextBudget | None = None,
) -> list[LoadedReference]:
    budget = budget or ContextBudget()
    if not aliases or len(aliases) > budget.max_references or len(set(aliases)) != len(aliases):
        raise AgentKnowledgeError("Reference count is invalid")
    remaining = budget.max_total_chars
    loaded: list[LoadedReference] = []
    for alias in aliases:
        entry, content = registry.read(alias)
        if remaining < 1:
            raise AgentKnowledgeError("Knowledge context budget is exhausted")
        limit = min(budget.max_document_chars, remaining)
        excerpt = content[:limit]
        loaded.append(
            LoadedReference(
                alias=alias,
                source_id=entry.source_id,
                title=entry.title,
                category=entry.category,
                content=excerpt,
                truncated=len(excerpt) < len(content),
                content_length=len(content),
            )
        )
        remaining -= len(excerpt)
    return loaded
