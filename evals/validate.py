"""Validate synthetic Golden annotations without running or grading an Agent."""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "evals/golden_cases.jsonl"
REFERENCE_MAP = ROOT / "evals/reference_map.json"
CONTRACT = ROOT / "docs/SKILL_CONTRACT.md"
BEHAVIOR_CATALOG = ROOT / "evals/behavior_catalog.json"
SCENARIOS = {
    "reply", "invitation", "flirt", "relationship", "imbalance", "conflict",
    "breakup", "long_term", "household", "online", "chat_import",
    "personality", "social_system", "pua", "consent", "diversity",
    "social_other", "safety", "memory",
}
CATEGORIES = {
    "reply", "flirt", "invitation", "conflict", "imbalance", "breakup",
    "reconciliation", "betrayal", "online", "chat_import", "mbti", "pua",
    "memory", "family", "violence", "coercion", "stalking", "fraud",
    "self_harm", "threat", "privacy", "relationship", "long_term",
    "diversity", "social_other", "social_system", "consent",
}
MEMORY_DECISIONS = {
    "no_write", "allow_candidate", "pause", "resume", "revoke_keep",
    "delete_item", "delete_person", "delete_all", "revoke_and_delete_all",
}
EVIDENCE_SOURCES = {
    "user_report", "user_report_quote", "user_self_report", "chat_message",
    "screenshot", "tool_result", "user_explicit",
}
PAIR_CONTRAST = {
    "A": "expected.route", "B": "expected.evidence.facts",
    "C": "expected.evidence.facts", "D": "expected.memory_writes",
    "E": "expected.route", "F": "expected.knowledge.required_any",
}
REQUIRED_ASSERTIONS = {
    "first_copyable", "facts_inferences_split", "no_mbti_mindreading",
    "stop_pursuit", "consent_required", "person_isolation",
    "no_inference_as_fact", "safety_first", "no_harm_instructions",
    "no_raw_chat_memory", "ask_speaker_mapping", "no_claim_export",
}
REQUIRED_FORBIDDEN = {
    "mind_reading", "inference_as_fact", "mbti_determinism",
    "gender_stereotype", "refusal_bypass", "manipulation_steps",
    "one_event_diagnosis", "unwarranted_certainty", "theory_only",
    "ignore_reciprocity", "ignore_user_behavior", "overload_references",
    "ordinary_strategy_first", "speaker_reversal", "raw_chat_memory",
    "cross_person_memory", "consent_from_silence",
}


def contract_rule_ids(text: str) -> set[str]:
    ids = set(re.findall(r"(?m)^## (\d+)\. ", text))
    ids.update(re.findall(r"(?m)^### (\d+\.\d+) ", text))
    section = None
    for line in text.splitlines():
        heading = re.match(r"^## (\d+)\. ", line)
        if heading:
            section = heading.group(1)
        item = re.match(r"^(\d+)\. ", line)
        if item and section in {"4", "7", "10"}:
            ids.add(f"{section}.{item.group(1)}")
    return ids


def load_cases(path: Path = DATA) -> list[dict]:
    cases = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            case = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"line {number}: invalid JSON: {exc.msg}") from exc
        if not isinstance(case, dict):
            raise ValueError(f"line {number}: case must be an object")
        cases.append(case)
    return cases


def get_path(value: dict, dotted: str):
    for part in dotted.split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    return value


def nonempty_strings(value) -> bool:
    return isinstance(value, list) and bool(value) and all(isinstance(x, str) and bool(x.strip()) for x in value)


def validate_cases(cases: list[dict], references: dict[str, str], rule_ids: set[str]) -> list[str]:
    errors: list[str] = []
    catalog = json.loads(BEHAVIOR_CATALOG.read_text(encoding="utf-8"))
    known_required = catalog["required"]
    known_forbidden = catalog["forbidden"]
    ids: set[str] = set()
    scenario_counts: Counter[str] = Counter()
    rules_seen: set[str] = set()
    assertions_seen: set[str] = set()
    forbidden_seen: set[str] = set()
    pairs: dict[str, list[dict]] = defaultdict(list)
    high_count = memory_count = 0
    if len(cases) < 40:
        errors.append(f"at least 40 cases required, got {len(cases)}")

    for index, case in enumerate(cases, 1):
        if not isinstance(case, dict):
            errors.append(f"case {index}: must be an object")
            continue
        case_id = case.get("id")
        if not isinstance(case_id, str) or not re.fullmatch(r"[a-z][a-z0-9_]*", case_id):
            errors.append(f"case {index}: invalid or missing id")
            case_id = f"<case {index}>"
        if case_id in ids:
            errors.append(f"duplicate id: {case_id}")
        ids.add(case_id)
        category = case.get("category")
        if not isinstance(category, str) or category not in CATEGORIES:
            errors.append(f"{case_id}: invalid category {category!r}")
        if not isinstance(case.get("input"), str) or len(case["input"].strip()) < 8:
            errors.append(f"{case_id}: missing or too short input")
        rules = case.get("contract_rules")
        if not nonempty_strings(rules):
            errors.append(f"{case_id}: contract_rules required")
        else:
            for rule in rules:
                if rule not in rule_ids:
                    errors.append(f"{case_id}: unknown contract rule {rule}")
            rules_seen.update(rules)
        tags = case.get("tags")
        if not nonempty_strings(tags):
            errors.append(f"{case_id}: at least one tag required")
            tags = []
        exp = case.get("expected")
        if not isinstance(exp, dict):
            errors.append(f"{case_id}: expected must be an object")
            continue
        if "expected_response" in case or "expected_response" in exp:
            errors.append(f"{case_id}: exact expected_response is forbidden")
        scenario = exp.get("scenario")
        if not isinstance(scenario, str) or scenario not in SCENARIOS:
            errors.append(f"{case_id}: invalid scenario {scenario!r}")
        else:
            scenario_counts[scenario] += 1
        acts = exp.get("assertions")
        if not nonempty_strings(acts) or len(acts) != len(set(acts)):
            errors.append(f"{case_id}: assertions must be unique behavior IDs")
            acts = []
        assertions_seen.update(acts)
        for behavior in acts:
            if behavior not in known_required:
                errors.append(f"{case_id}: unknown required behavior {behavior}")
        forbidden = exp.get("forbidden_behaviors")
        if not isinstance(forbidden, list) or any(not isinstance(x, str) or not x.strip() for x in forbidden) or len(forbidden) != len(set(forbidden)):
            errors.append(f"{case_id}: forbidden_behaviors must be unique behavior IDs")
            forbidden = []
        forbidden_seen.update(forbidden)
        for behavior in forbidden:
            if behavior not in known_forbidden:
                errors.append(f"{case_id}: unknown forbidden behavior {behavior}")

        knowledge = exp.get("knowledge")
        if not isinstance(knowledge, dict):
            errors.append(f"{case_id}: knowledge expectation required")
            knowledge = {}
        required_any = knowledge.get("required_any")
        allowed = knowledge.get("allowed")
        blocked = knowledge.get("forbidden")
        maximum = knowledge.get("max_count")
        if not nonempty_strings(required_any) or not nonempty_strings(allowed) or not isinstance(blocked, list) or any(not isinstance(x, str) or not x.strip() for x in blocked):
            errors.append(f"{case_id}: knowledge needs required_any, allowed and forbidden aliases")
            required_any, allowed, blocked = [], [], []
        aliases = [*required_any, *allowed, *blocked]
        if not isinstance(maximum, int) or isinstance(maximum, bool) or not 1 <= maximum <= 3:
            errors.append(f"{case_id}: knowledge max_count must be 1–3")
        if len(set(allowed)) != len(allowed) or len(set(blocked)) != len(blocked):
            errors.append(f"{case_id}: duplicate knowledge alias")
        if not set(required_any).issubset(allowed) or set(blocked) & set(allowed):
            errors.append(f"{case_id}: required/forbidden aliases conflict with allowed")
        if isinstance(maximum, int) and len(allowed) > maximum:
            errors.append(f"{case_id}: allowed references exceed max_count")
        for alias in aliases:
            path = references.get(alias)
            if not isinstance(path, str) or not path.startswith("references/") or not (ROOT / "knowledge/goutoujunshi" / path).is_file():
                errors.append(f"{case_id}: unknown or missing reference {alias}")

        safety = exp.get("safety")
        route = exp.get("route")
        writes = exp.get("memory_writes")
        if writes not in (0, 1) or isinstance(writes, bool):
            errors.append(f"{case_id}: memory_writes must be 0 or 1")
        if safety == "high":
            high_count += 1
            if route != "safety" or scenario != "safety" or "safety_first" not in acts or "safety" not in required_any:
                errors.append(f"{case_id}: high-risk case must take safety path and require safety reference")
            if writes != 0 or "ordinary_strategy_first" not in forbidden:
                errors.append(f"{case_id}: high-risk case must forbid ordinary-first handling and memory writes")
        elif safety == "normal":
            if route not in {"ordinary", "boundary"}:
                errors.append(f"{case_id}: invalid normal-risk route")
            if scenario == "safety":
                errors.append(f"{case_id}: safety scenario cannot have normal risk")
            if route == "boundary" and not ({"stop_pursuit", "boundary_respected"} & set(acts)):
                errors.append(f"{case_id}: boundary route needs a stopping or boundary assertion")
        else:
            errors.append(f"{case_id}: safety must be normal or high")

        memory = exp.get("memory")
        if scenario == "memory":
            memory_count += 1
            if not isinstance(memory, dict) or memory.get("decision") not in MEMORY_DECISIONS:
                errors.append(f"{case_id}: memory case needs a valid decision")
            else:
                decision = memory["decision"]
                if (writes == 1) != (decision == "allow_candidate"):
                    errors.append(f"{case_id}: memory decision conflicts with write expectation")
                if decision == "allow_candidate" and ("consent_recorded" not in acts or memory.get("source") not in {"user_explicit", "user_report"}):
                    errors.append(f"{case_id}: candidate needs explicit consent and valid source")
                if decision in {"delete_person", "delete_all", "revoke_and_delete_all"} and memory.get("requires_confirmation") is not True:
                    errors.append(f"{case_id}: destructive memory operation needs confirmation")
                if decision == "delete_person" and not memory.get("person_id"):
                    errors.append(f"{case_id}: person deletion needs target person_id")
                if decision == "delete_item" and (not memory.get("person_id") or not memory.get("item_id")):
                    errors.append(f"{case_id}: item deletion needs person_id and item_id")
        elif memory is not None:
            errors.append(f"{case_id}: memory decision belongs to memory scenario")
        if writes == 1 and scenario != "memory":
            errors.append(f"{case_id}: only memory scenario can allow a write candidate")

        ev = exp.get("evidence")
        if ev is not None:
            if not isinstance(ev, dict) or not isinstance(ev.get("facts"), list) or not isinstance(ev.get("inferences"), list) or not isinstance(ev.get("unknowns"), list):
                errors.append(f"{case_id}: evidence needs facts/inferences/unknowns lists")
            else:
                if not ev["facts"] or not ev["unknowns"]:
                    errors.append(f"{case_id}: evidence needs at least one fact and unknown")
                for fact in ev["facts"]:
                    if not isinstance(fact, dict) or not isinstance(fact.get("claim"), str) or not fact["claim"].strip() or fact.get("source") not in EVIDENCE_SOURCES:
                        errors.append(f"{case_id}: fact needs claim and valid source")
                for inference in ev["inferences"]:
                    if not isinstance(inference, dict) or not isinstance(inference.get("claim"), str) or not inference["claim"].strip() or not isinstance(inference.get("alternative"), str) or not inference["alternative"].strip():
                        errors.append(f"{case_id}: inference needs claim and alternative")
                if any(not isinstance(x, str) or not x.strip() for x in ev["unknowns"]):
                    errors.append(f"{case_id}: unknowns need nonempty descriptions")
                if "facts_inferences_split" not in acts and "no_inference_as_fact" not in acts and "speaker_mapping_preserved" not in acts:
                    errors.append(f"{case_id}: evidence needs an evidence behavior assertion")
        if "fiu" in tags and ev is None:
            errors.append(f"{case_id}: fiu-tagged case needs evidence expectations")

        pair = case.get("minimal_pair")
        if pair is not None:
            if not isinstance(pair, dict) or not isinstance(pair.get("group"), str) or pair.get("group") not in PAIR_CONTRAST:
                errors.append(f"{case_id}: invalid minimal pair group")
            else:
                pairs[pair["group"]].append(case)
                if pair.get("contrast_field") != PAIR_CONTRAST[pair["group"]]:
                    errors.append(f"{case_id}: wrong minimal pair contrast_field")

    for group, path in PAIR_CONTRAST.items():
        members = pairs[group]
        if len(members) != 2:
            errors.append(f"pair {group}: exactly two cases required")
            continue
        variants = {case["minimal_pair"].get("variant") for case in members}
        if variants != {f"{group}1", f"{group}2"}:
            errors.append(f"pair {group}: variants must be {group}1 and {group}2")
        if members[0].get("input") == members[1].get("input") or get_path(members[0], path) == get_path(members[1], path):
            errors.append(f"pair {group}: input and contrast expectation must differ")
    if missing := (SCENARIOS - {"memory"}) - scenario_counts.keys():
        errors.append(f"missing taxonomy scenarios: {sorted(missing)}")
    tracked_rules = {rule for rule in rule_ids if rule.startswith(("4.", "7.", "10."))}
    tracked_rules.update({"3", "5.1", "6", "8", "9"})
    if missing := tracked_rules - rules_seen:
        errors.append(f"missing contract rule coverage: {sorted(missing)}")
    if memory_count < 10 or high_count < 8:
        errors.append(f"insufficient memory/high-risk coverage: {memory_count}/{high_count}")
    if missing := REQUIRED_ASSERTIONS - assertions_seen:
        errors.append(f"missing required assertions: {sorted(missing)}")
    if missing := REQUIRED_FORBIDDEN - forbidden_seen:
        errors.append(f"missing anti-patterns: {sorted(missing)}")
    return errors


def validate() -> dict[str, int]:
    cases = load_cases()
    references = json.loads(REFERENCE_MAP.read_text(encoding="utf-8"))
    if not isinstance(references, dict):
        raise ValueError("reference_map must be an object")
    for alias, path in references.items():
        if not isinstance(alias, str) or not isinstance(path, str) or not path.startswith("references/") or not (ROOT / "knowledge/goutoujunshi" / path).is_file():
            raise ValueError(f"invalid reference_map entry: {alias!r}")
    errors = validate_cases(cases, references, contract_rule_ids(CONTRACT.read_text(encoding="utf-8")))
    if errors:
        raise ValueError("\n".join(errors))
    return {
        "cases": len(cases),
        "categories": len({case["category"] for case in cases}),
        "scenarios": len({case["expected"]["scenario"] for case in cases}),
        "high_risk": sum(case["expected"]["safety"] == "high" for case in cases),
        "minimal_pairs": len(PAIR_CONTRAST),
    }


if __name__ == "__main__":
    print("Golden annotation validation passed:", validate())
