"""Frozen synthetic ICA graph runs; no DB, Memory, live-key lookup or quality grading."""

import hashlib
import json
from datetime import datetime
from pathlib import Path
from time import perf_counter
from uuid import UUID

from app.agent.imported_analysis import (
    ImportedAnalysisError,
    ImportedAnalysisRuntime,
    serialized_request_bytes,
)
from app.chat_import.analysis_scope import AnalysisScope, ScopeMessage, prepare_context
from app.llm.errors import LLMError
from app.llm.models import LLMMessage
from app.llm.provider import LLMProvider

ROOT = Path(__file__).resolve().parents[2]
DATASET = Path(__file__).with_name("v1") / "cases.jsonl"
MANIFEST = DATASET.with_name("manifest.json")
BASELINE_VERSION = "ica-local-summary-prompt-v1"
BASELINE_INSTRUCTION = (
    "Frozen local-summary comparison: summarize the observable exchange within each supplied "
    "chunk into the requested candidate fields; do not build an additional event index or "
    "invent cross-chunk episodes. At synthesis, combine these local summary candidates into "
    "the requested findings. All existing evidence, safety, counterevidence, recurrence, "
    "uncertainty and output-schema requirements still apply."
)
ARM_DESCRIPTORS = {
    "event": "Existing structured candidate / full-core counterevidence ICA graph.",
    "baseline": (
        "Prompt-only local-summary comparison using the identical graph and validators; "
        "not an independent hierarchical-summary or event-index architecture benchmark."
    ),
}
RUNTIME_ERROR_CODES = frozenset(
    {
        "input_budget_exceeded",
        "invalid_input",
        "invalid_context",
        "invalid_speaker",
        "invalid_evidence",
        "invalid_attribution",
        "nontext_finding",
        "model_statistics",
        "halo_only_candidate",
        "incomplete_counterevidence",
        "duplicate_finding_kind",
        "unverified_candidate",
        "unverified_fact",
        "refuted_finding",
        "counterevidence_omitted",
        "one_sided_finding",
        "incomparable_windows",
        "insufficient_episodes",
        "content_review_rejected",
        "call_budget_exceeded",
        "invalid_model_output",
        "evaluation_admission_rejected",
        "evaluation_callback_error",
    }
)


def source_fingerprint(*, case_set="v1") -> str:
    """Bind actual executable/knowledge/case bytes, not only a Git HEAD label."""
    dataset, manifest_path = case_paths(case_set)
    paths = {
        ROOT / "apps/server/app/agent/imported_analysis.py",
        ROOT / "apps/server/app/agent/imported_contracts.py",
        ROOT / "apps/server/app/agent/imported_quote.py",
        ROOT / "apps/server/app/chat_import/analysis_scope.py",
        ROOT / "knowledge/upstream-manifest.json",
        ROOT / "knowledge/goutoujunshi/SKILL.md",
        ROOT / "evals/reference_map.json",
        ROOT / "uv.lock",
        dataset,
        manifest_path,
        *Path(__file__).parent.glob("*.py"),
        *(ROOT / "knowledge/goutoujunshi/references").rglob("*.md"),
    }
    digest = hashlib.sha256()
    for path in sorted(paths):
        digest.update(path.relative_to(ROOT).as_posix().encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def case_paths(case_set):
    if case_set not in {"v1", "v2"}:
        raise ValueError("Unsupported case set")
    directory = Path(__file__).with_name(case_set)
    return directory / "cases.jsonl", directory / "manifest.json"


def load_cases(split: str, *, case_set="v1") -> list[dict]:
    """Read the existing byte-frozen inventory without regenerating or changing it."""
    if split not in {"development", "holdout"}:
        raise ValueError("Select development or holdout")
    dataset, manifest_path = case_paths(case_set)
    raw = dataset.read_bytes()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if hashlib.sha256(raw).hexdigest() != manifest["cases_sha256"]:
        raise ValueError("Frozen case file changed")
    rows = [json.loads(line) for line in raw.decode("utf-8").splitlines()]
    if len(rows) != 48 or len({row["case_id"] for row in rows}) != 48:
        raise ValueError("Frozen case inventory mismatch")
    expected_hashes = {row["case_id"]: row["sha256"] for row in manifest["cases"]}
    for row in rows:
        encoded = json.dumps(row, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        if hashlib.sha256(encoded.encode()).hexdigest() != expected_hashes[row["case_id"]]:
            raise ValueError("Frozen case changed")
    selected = [row for row in rows if row["split"] == split]
    if {row["case_id"] for row in selected} != set(manifest[split]):
        raise ValueError("Frozen split mismatch")
    return selected


def case_to_contexts(case: dict) -> tuple:
    """Only the selected source/window/message fields become model-visible context."""
    if case["schema_version"] != "ica-case-v1":
        raise ValueError("Unsupported case schema")
    source = case["source"]
    owner, person, dataset = (UUID(source[key]) for key in ("owner_id", "person_id", "dataset_id"))
    windows = case["windows"]
    if not 1 <= len(windows) <= 2:
        raise ValueError("Invalid window count")
    ids = [window["window_id"] for window in windows]
    if len(set(ids)) != len(ids):
        raise ValueError("Duplicate window ID")
    messages = case["messages"]
    message_ids = [UUID(message["message_id"]) for message in messages]
    if len(set(message_ids)) != len(message_ids):
        raise ValueError("Duplicate message ID")
    if any(message["window_id"] not in ids for message in messages):
        raise ValueError("Message outside selected window")
    contexts = []
    for window in windows:
        scope = AnalysisScope(
            owner,
            person,
            dataset,
            case["timezone"],
            datetime.fromisoformat(window["start_utc"]),
            datetime.fromisoformat(window["end_utc"]),
        )
        scoped = [
            ScopeMessage(
                UUID(message["message_id"]),
                owner,
                person,
                dataset,
                datetime.fromisoformat(message["timestamp_utc"]),
                message["sender_role"],
                message["content"],
                message["content_type"],
            )
            for message in messages
            if message["window_id"] == window["window_id"]
        ]
        contexts.append(prepare_context(scope, scoped))
    return tuple(contexts)


def arm_messages(arm: str, messages: tuple[LLMMessage, ...]) -> tuple[LLMMessage, ...]:
    if arm != "baseline":
        return messages
    payload = json.loads(messages[1].content)
    if payload["stage"] not in {"interaction", "synthesis"}:
        return messages
    return (
        LLMMessage(role="system", content=messages[0].content + "\n" + BASELINE_INSTRUCTION),
        *messages[1:],
    )


class _ArmProvider:
    """Use the public Provider seam; do not patch Runtime internals or bypass validation."""

    def __init__(self, provider: LLMProvider, arm: str):
        self.provider, self.arm = provider, arm

    async def structured_output(self, messages, schema, *, model=None, temperature=None):
        return await self.provider.structured_output(
            arm_messages(self.arm, tuple(messages)),
            schema,
            model=model,
            temperature=temperature,
        )


async def evaluate_case(
    case: dict,
    provider: LLMProvider,
    model: str,
    arm: str = "event",
    before_call=None,
    after_call=None,
    *,
    evidence_protocol="span-v1",
    case_set="v1",
) -> dict:
    """One attempt; preserve failures and call metadata, never infer semantic quality."""
    fingerprint = source_fingerprint(case_set=case_set)
    calls, started = [], {}
    row = {
        "case_id": case["case_id"],
        "evidence_protocol": evidence_protocol,
        "case_set": case_set,
        "arm": arm,
        "arm_descriptor": ARM_DESCRIPTORS.get(arm),
        "baseline_definition": BASELINE_VERSION if arm == "baseline" else None,
        "status": "failed",
        "result": None,
        "error_code": None,
        "calls": calls,
        "source_fingerprint": fingerprint,
        "authority_faults_exercised": False,
        "required_authority_faults": [],
    }
    attack = case.get("adversarial_input") or {}
    if attack.get("kind") in {
        "foreign_owner_reference",
        "foreign_person_dataset_reference",
        "revoked_snapshot_restore",
    }:
        row["required_authority_faults"] = attack.get("required_faults") or [attack["kind"]]

    async def before(stage, chunk_id, messages, schema):
        actual_messages = arm_messages(arm, messages)
        entry = {
            "call_id": None,
            "stage": stage,
            "chunk_id": chunk_id,
            "schema": schema.__name__,
            "input_bytes": serialized_request_bytes(actual_messages, schema, model),
            "status": "not_admitted",
            "error_code": None,
        }
        calls.append(entry)
        try:
            call_id = (
                await before_call(stage, chunk_id, actual_messages, schema)
                if before_call
                else str(len(calls))
            )
        except Exception:
            entry["error_code"] = "evaluation_admission_rejected"
            raise ImportedAnalysisError("evaluation_admission_rejected") from None
        if any(prior["call_id"] == call_id for prior in calls[:-1]):
            entry["error_code"] = "evaluation_admission_rejected"
            raise ImportedAnalysisError("evaluation_admission_rejected")
        entry["call_id"], entry["status"] = call_id, "admitted"
        started[call_id] = perf_counter()
        return call_id

    async def after(call_id, output, error):
        entry = next(item for item in calls if item["call_id"] == call_id)
        entry["elapsed_ms"] = round((perf_counter() - started[call_id]) * 1000, 3)
        entry["status"] = "failed" if error else "succeeded"
        entry["error_code"] = error if error in RUNTIME_ERROR_CODES else None
        if after_call:
            try:
                await after_call(call_id, output, error)
            except Exception:
                entry["status"], entry["error_code"] = "failed", "evaluation_callback_error"
                raise ImportedAnalysisError("evaluation_callback_error") from None

    try:
        if arm not in ARM_DESCRIPTORS:
            row["error_code"] = "invalid_arm"
            return row
        if case_set == "v2" and evidence_protocol != "quote-v2":
            row["error_code"] = "invalid_evidence_protocol"
            return row
        contexts = case_to_contexts(case)
        row["scope_digests"] = [context.scope.digest for context in contexts]
        row["snapshot_digests"] = [context.snapshot_digest for context in contexts]
        result = await ImportedAnalysisRuntime(
            _ArmProvider(provider, arm), evidence_protocol=evidence_protocol
        ).run(contexts, case["question"], model, before, after)
        if source_fingerprint(case_set=case_set) != fingerprint:
            row["error_code"] = "evaluation_source_changed"
            return row
        row["status"] = "completed"
        row["result"] = result.report.model_dump(mode="json")
        row["receipts"] = [receipt.model_dump(mode="json") for receipt in result.receipts]
    except ImportedAnalysisError as error:
        row["error_code"] = error.code if error.code in RUNTIME_ERROR_CODES else "evaluation_error"
    except LLMError as error:
        row["error_code"] = error.code
    except (ValueError, KeyError, TypeError):
        row["error_code"] = "invalid_case"
    except Exception:
        row["error_code"] = "evaluation_error"
    return row
