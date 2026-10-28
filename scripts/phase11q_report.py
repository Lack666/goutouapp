"""Read-only Phase11Q live evidence audit and keyless full-graph response replay."""

import argparse
import asyncio
import copy
import hashlib
import json
import zipfile
from collections import deque
from uuid import UUID, uuid4

from pydantic import ValidationError

from app.agent import contracts
from app.agent.action_validation import CONTACT_CUES
from app.agent.contracts import AgentInput, AgentResult, Route
from app.agent.dependencies import RuntimeDependencies
from app.agent.memory import MemoryService
from app.agent.response_composition import compose_response
from app.agent.runtime import AgentRuntime
from app.agent.safety_validation import validate_safety_answer
from app.agent.state import initial_state
from app.llm.mock import MockLLMProvider
from app.observability import TRACES
from evals.agent.content_safety_integration import scoped_memory
from evals.agent.harness import summarize
from evals.agent.independent import ROOT, call_metrics, sha, write_new
from evals.agent.remediation_q import OUTPUT, PLAN, RESULTS, cases, check_frozen

BASELINE = RESULTS / "q11-protected-baseline-v2.json"
SUMMARY = RESULTS / "q11-remediation-summary-v2.json"
LOCAL_V1 = RESULTS / "q11-protected-baseline-v1.json"
PREFLIGHT = ROOT / ".cache/phase11q-preflight.json"


def protected_baseline():
    if BASELINE.exists():
        result = json.loads(BASELINE.read_text("utf-8"))
        assert result["version"] == "phase11q-preflight-preservation-v2"
        return result
    captured = LOCAL_V1 if LOCAL_V1.exists() else PREFLIGHT
    preflight = json.loads(captured.read_text("utf-8"))
    local = set(preflight["unrelated_user_work"])
    old_hashes = preflight["protected_raw_sha256"]
    assert local == {
        "evals/agent/results/human-review-15.json",
        "evals/agent/results/human-review-summary.md",
    }
    assert local <= set(old_hashes)
    return {
        "version": "phase11q-preflight-preservation-v2",
        "base_commit": preflight["base_commit"],
        "original_preflight_sha256": preflight.get("original_preflight_sha256", sha(captured)),
        "local_v1_sha256": sha(LOCAL_V1) if LOCAL_V1.exists() else None,
        "source": "Pre-remediation capture; tracked evidence and unrelated local work separated",
        "original_capture_count": len(old_hashes),
        "protected_raw_sha256": {p: value for p, value in old_hashes.items() if p not in local},
        "local_user_work_hashes": {p: old_hashes[p] for p in sorted(local)},
        "local_user_work_policy": (
            "Captured metadata only for unrelated, deliberately uncommitted user work. "
            "Not required for portable replay; use --check-local-user-work on original workspace."
        ),
    }


def verify_protected(baseline, *, include_local=False):
    required = baseline["protected_raw_sha256"]
    local = baseline["local_user_work_hashes"]
    assert not set(required) & set(local)
    for path, value in required.items():
        assert sha(ROOT / path) == value, f"Protected historical evidence changed: {path}"
    if include_local:
        for path, value in local.items():
            assert sha(ROOT / path) == value, f"Original local user work changed: {path}"


def without_run_id(value):
    result = copy.deepcopy(value)
    result.pop("run_id")
    return result


class RecordedProvider(MockLLMProvider):
    """Consume actual operation/schema order and visible responses; never invokes a network."""

    def __init__(self, row):
        super().__init__()
        calls = [r for r in row["traces"] if r["kind"] == "provider"]
        self.recorded = deque(zip(calls, row["raw_visible_outputs"], strict=True))
        self.consumed = []

    def take(self, operation, schema=None):
        observed, response = self.recorded.popleft()
        assert observed["operation"] == operation
        assert observed.get("schema") == schema
        self.consumed.append((operation, schema))
        return response

    async def structured_output(self, messages, schema, **kwargs):
        response = self.take("structured_output", schema.__name__)
        self.queue_structured(response["content"])
        return await super().structured_output(messages, schema, **kwargs)

    async def chat(self, messages, **kwargs):
        response = self.take("chat")
        self.queue_chat(response["content"], finish_reason=response["finish_reason"])
        return await super().chat(messages, **kwargs)


async def replay_case(row):
    request = AgentInput(
        run_id=uuid4(),
        user_id=uuid4(),
        conversation_id=uuid4(),
        relationship_id=uuid4(),
        message=row["input"],
        memory_enabled=True,
    )
    store, person = scoped_memory(request, consented=False)
    recorded_person = row["result"].get("memory_intent", {}).get("person_id")
    if recorded_person:
        # Recreate the recorded synthetic Person mapping, never alter the expected output.
        old_person, person = person, UUID(recorded_person)
        store.bind_relationship(request.user_id, request.relationship_id, person)
        for key, record in store.records.items():
            if record.owner_user_id == request.user_id and record.subject_id == old_person:
                store.records[key] = record.model_copy(
                    update={"person_id": person, "subject_id": person}
                )
    before = store.snapshot()
    provider = RecordedProvider(row)
    runtime = AgentRuntime(
        dependencies=RuntimeDependencies(
            llm_provider=provider,
            memory_service=MemoryService(store),
        )
    )
    result = await runtime.run(request)
    assert without_run_id(result.model_dump(mode="json")) == without_run_id(row["result"])
    assert not provider.recorded and not provider._structured and not provider._chats
    assert store.snapshot() == before and store.writes == 0
    assert all(pair == (request.user_id, person) for pair in store.reads)
    trace = [r for r in TRACES.snapshot() if r["run_id"] == str(request.run_id)]
    old_nodes = [r["node"] for r in row["traces"] if r["kind"] == "node_start"]
    assert [r["node"] for r in trace if r["kind"] == "node_start"] == old_nodes
    if isinstance(result, AgentResult) and result.route == Route.SAFETY:
        state = initial_state(request)
        state["safety"], state["route"] = result.safety, result.route
        validate_safety_answer(result.final_answer, state)
        assert not set(old_nodes) & {
            "relationship_analysis",
            "action_planner",
            "response_generator",
            "memory_intent_resolver",
            "memory_candidate_extractor",
            "memory_persist",
        }
    return {
        "id": row["id"],
        "status": row["status"],
        "exact_result_without_run_id": True,
        "provider_responses_consumed": len(provider.consumed),
        "node_order_equal": True,
        "memory_writes": store.writes,
        "owner_reads_scoped": True,
    }


def failure_evidence(row):
    calls = [r for r in row["traces"] if r["kind"] == "provider"]
    parsed, schema_errors = {}, []
    for call, raw in zip(calls, row["raw_visible_outputs"], strict=True):
        if call["operation"] != "structured_output":
            continue
        schema = getattr(contracts, call["schema"])
        try:
            parsed[call["schema"]] = schema.model_validate_json(raw["content"])
            assert call["status"] == "completed"
        except ValidationError as exc:
            assert call["status"] == "failed"
            schema_errors.extend({"type": e["type"], "loc": list(e["loc"])} for e in exc.errors())
    result = {
        "id": row["id"],
        "status": row["status"],
        "diagnostic": row["diagnostic"],
        "checks": row["checks"],
        "schema_errors": schema_errors,
        "failed_node": next(
            (
                r["node"]
                for r in reversed(row["traces"])
                if r["kind"] == "node_end" and r["status"] == "failed"
            ),
            None,
        ),
    }
    if row["diagnostic"] == "formal_guard_rejection":
        plan, response = parsed["ActionPlan"], parsed["ResponseResult"]
        state = initial_state(
            AgentInput(user_id=uuid4(), conversation_id=uuid4(), message=row["input"])
        )
        state["action_plan"] = plan
        state["scenario"] = parsed["ScenarioResult"]
        candidate = compose_response(response, state)
        result["contact_guard"] = {
            "contact_policy": plan.contact_policy,
            "candidate_preserved": response.final_answer in candidate.final_answer,
            "required_plan_present": (plan.message_suggestion or plan.recommended_action)
            in candidate.final_answer,
            "matched_patterns": [
                p.pattern for p in CONTACT_CUES if p.search(candidate.final_answer)
            ],
        }
    return result


async def build():
    plan = check_frozen()
    live = json.loads(OUTPUT.read_text("utf-8"))
    selected = cases()
    rows = live["cases"]
    assert [r["id"] for r in rows] == [c["id"] for c in selected] == plan["case_ids"]
    assert live["plan_sha256"] == sha(PLAN)
    assert live["dataset_sha256"] == plan["dataset_sha256"]
    assert live["source_files"] == plan["files"] and live["source_stable"]
    digest = hashlib.sha256(json.dumps(plan["files"], sort_keys=True).encode()).hexdigest()
    assert live["source_fingerprint_start"] == live["source_fingerprint"] == digest
    with zipfile.ZipFile(RESULTS / "q11-source-v1.zip") as archive:
        for path, value in plan["files"].items():
            assert hashlib.sha256(archive.read(path)).hexdigest() == value
    baseline = protected_baseline()
    verify_protected(baseline)
    calls = [r for r in live["traces"] if r["kind"] == "provider"]
    journals = [
        json.loads(p.read_text("utf-8")) for p in sorted(RESULTS.glob("q11-call-*-v1.json"))
    ]
    raw_outputs = [raw for row in rows for raw in row["raw_visible_outputs"]]
    assert len(journals) == live["budget"]["requests"] == len(calls) == len(raw_outputs) == 71
    for serial, (journal, call, raw) in enumerate(
        zip(journals, calls, raw_outputs, strict=True), 1
    ):
        assert journal["serial"] == serial and journal["request_reserved"]
        assert journal["status"] == "response" and journal["visible_response"] == raw
        assert raw["usage"] == call["usage"] and journal["duration_ms"] >= 0
    assert [r["case_id"] for r in journals] == [
        row["id"] for row in rows for _ in row["raw_visible_outputs"]
    ]
    for row in rows:
        assert json.loads((RESULTS / f"q11-case-{row['id']}-v1.json").read_text("utf-8")) == row
        assert row["memory_write_attempts"] == 0 and row["memory_unchanged"]
        assert row["checks"]["memory_reads_scoped"]
        observed = [r for r in row["traces"] if r["kind"] == "provider"]
        assert row["provider"] == call_metrics(observed)
    recomputed = summarize(rows, calls) | call_metrics(calls)
    assert all(live["metrics"][k] == v for k, v in recomputed.items())
    replay = [await replay_case(row) for row in rows]
    assert sum(row["group"] == "safety" and row["route"] == "safety" for row in rows) == 5
    reviews = [r for r in live["traces"] if r["kind"] == "content_safety_review"]
    review_calls = [r for r in calls if r["operation"] == "chat"]
    failures = [failure_evidence(row) for row in rows if not row["passed"]]
    packet = json.loads((RESULTS / "q11-human-review-v1.json").read_text("utf-8"))
    assert [i["case_id"] for i in packet["items"]] == plan["review_ids"]
    assert all(
        i["reviewer"] is None and all(v is None for v in i["scores"].values())
        for i in packet["items"]
    )
    metrics = {k: v for k, v in live["metrics"].items() if k != "token_distribution"}
    return {
        "version": "phase11q-remediation-summary-v2",
        "status": "PARTIAL FIX / REMAINING BLOCKERS",
        "phase11_quality": "QUALITY FAIL",
        "human_review": "PENDING / 0 of 15; no scores inferred",
        "live_source_sha256": sha(OUTPUT),
        "plan_sha256": sha(PLAN),
        "source_fingerprint": digest,
        "protected_baseline_sha256": sha(BASELINE) if BASELINE.exists() else None,
        "protected_old_files": len(baseline["protected_raw_sha256"]),
        "local_user_work_original_hashes": baseline["local_user_work_hashes"],
        "local_user_work_verification": "Metadata only; excluded from required portable replay",
        "provider_journals_verified": len(journals),
        "metrics": metrics,
        "review": {
            "calls": len(review_calls),
            "allow": sum(r["decision"] == "allow" for r in reviews),
            "block": sum(r["decision"] == "block" for r in reviews),
            "fault": len(review_calls) - len(reviews),
            "accounting": call_metrics(review_calls),
        },
        "recorded_output_graph_replay": replay,
        "retained_machine_failures": failures,
        "safety": {
            "controlled_policy_valid": 5,
            "controlled_policy_violations": 0,
            "semantic_population_false_negative_rate": None,
            "limit": (
                "Policy equality and five synthetic cases, "
                "not independent human safety certification"
            ),
        },
        "memory_owner": {
            "writes": 0,
            "runtime_canary_reads_scoped": True,
            "limit": "Runtime fixture only; signed API Owner isolation is tested separately",
        },
        "full_regression": "DEFERRED TO FINAL CLOSEOUT",
        "official_marker": json.loads((ROOT / "project-phase.json").read_text("utf-8")),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--check-local-user-work", action="store_true")
    args = parser.parse_args()
    if not args.check and not BASELINE.exists():
        write_new(BASELINE, protected_baseline())
    result = asyncio.run(build())
    if args.check_local_user_work:
        verify_protected(protected_baseline(), include_local=True)
    if args.check:
        assert json.loads(SUMMARY.read_text("utf-8")) == result
    else:
        write_new(SUMMARY, result)
    print(
        json.dumps(
            {
                "status": result["status"],
                "replayed": len(result["recorded_output_graph_replay"]),
                "requests": result["provider_journals_verified"],
                "retained_failures": len(result["retained_machine_failures"]),
            }
        )
    )


if __name__ == "__main__":
    main()
