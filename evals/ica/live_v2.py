"""Quote-v2 batch preparation; a fresh plan-bound approval is required before key access."""

import argparse
import asyncio
import hashlib
import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from app.agent.imported_quote import STAGE_SCHEMAS
from app.llm.errors import LLMConfigurationError
from evals.ica.live import (
    PRICE,
    ROOT,
    BatchBudget,
    RecordedProvider,
    append,
    private_key,
    write_new,
)
from evals.ica.runner import case_paths, case_to_contexts, evaluate_case, load_cases
from evals.ica.runner import source_fingerprint as graph_fingerprint

VERSION = "ica-bq-batch-v2"
TARIFF = {**PRICE, "version": "deepseek-flash-2026-11-09-peak-cny", "checked_at": "2026-11-09"}
MAX_INPUT_BYTES = 128 * 1024


def sha(value):
    return hashlib.sha256(value).hexdigest()


def json_hash(value):
    return sha(json.dumps(value, sort_keys=True, ensure_ascii=False).encode())


def schemas():
    return {stage: json_hash(schema.model_json_schema()) for stage, schema in STAGE_SCHEMAS.items()}


def fingerprint():
    paths = (
        ROOT / "docs/ICA_BQ_V2_EVAL_CONTRACT.md",
        ROOT / "docs/ICA_BQ_V2_HUMAN_REVIEW.md",
        ROOT / "evals/ica/v2/AUTHORING_PROVENANCE.md",
        ROOT / "evals/ica/v2/author_cases.py",
        *sorted((ROOT / "apps/server/app/agent").rglob("*.py")),
        *sorted((ROOT / "apps/server/app/llm").glob("*.py")),
    )
    return json_hash(
        {
            "graph": graph_fingerprint(case_set="v2"),
            "additional": {p.relative_to(ROOT).as_posix(): sha(p.read_bytes()) for p in paths},
            "schemas": schemas(),
        }
    )


def build_plan():
    cases = load_cases("holdout", case_set="v2")
    dataset, manifest = case_paths("v2")
    scopes, order = [], []
    for index, case in enumerate(cases):
        contexts = case_to_contexts(case)
        k = sum(len(context.chunks) for context in contexts)
        scopes.append(
            {
                "case_id": case["case_id"],
                "messages": sum(len(c.messages) for c in contexts),
                "K": k,
                "graph_requests_upper": 3 * k + 2,
                "scope_requests_upper": 3 * k + 8,
            }
        )
        arms = ["event", "baseline"] if index % 2 == 0 else ["baseline", "event"]
        order.extend({"case_id": case["case_id"], "arm": arm} for arm in arms)
    graph_upper = 2 * sum(s["graph_requests_upper"] for s in scopes)
    reserve_per_call = MAX_INPUT_BYTES + 4096 + 4096
    cost_per_call = (
        (MAX_INPUT_BYTES + 4096) * Decimal(TARIFF["miss_per_million"])
        + 4096 * Decimal(TARIFF["output_per_million"])
    ) / 1_000_000
    return {
        "version": VERSION,
        "case_set": "v2",
        "evidence_protocol": "quote-v2",
        "source_fingerprint": fingerprint(),
        "wire_schema_sha256": schemas(),
        "cases_sha256": sha(dataset.read_bytes()),
        "manifest_sha256": sha(manifest.read_bytes()),
        "provider_base_url": "https://api.deepseek.com",
        "model": TARIFF["model"],
        "thinking": "disabled",
        "temperature": 0,
        "tariff": TARIFF,
        "case_ids": [c["case_id"] for c in cases],
        "arms": ["event", "baseline"],
        "execution_order": order,
        "scopes": scopes,
        "max_requests": 400,
        "max_reserved_tokens": 10_000_000,
        "max_cost_cny": "20",
        "max_output_tokens": 4096,
        "max_input_bytes": MAX_INPUT_BYTES,
        "graph_requests_upper": graph_upper,
        "scope_requests_upper": 2 * sum(s["scope_requests_upper"] for s in scopes),
        "worst_envelope_reserved_tokens": graph_upper * reserve_per_call,
        "worst_envelope_cost_cny": str(graph_upper * cost_per_call),
        "complete_envelope_within_budget": graph_upper <= 400
        and graph_upper * reserve_per_call <= 10_000_000
        and graph_upper * cost_per_call <= Decimal("20"),
        "full_completion_guaranteed": False,
        "no_retries": True,
        "synthetic_only": True,
        "new_budget_approval_required": True,
        "human_quality": "pending independent human review",
        "stop_conditions": [
            "budget admission failure",
            "unknown response or missing usage",
            "source/schema drift",
            "usage above reservation",
            "safety oracle route mismatch",
            "manual stop",
        ],
    }


def validate_plan(plan):
    if json_hash(plan) != json_hash(build_plan()):
        raise ValueError("Frozen v2 plan/source/schema/tariff mismatch")


def read_plan(directory):
    raw = (directory / "plan.json").read_bytes()
    plan = json.loads(raw)
    validate_plan(plan)
    return plan, sha(raw)


def authorize(directory, *, confirmed, approval_reference, now=None):
    plan, digest = read_plan(directory)
    if (
        confirmed is not True
        or not isinstance(approval_reference, str)
        or not approval_reference.strip()
    ):
        raise ValueError("Fresh explicit user budget approval reference required")
    now = now or datetime.now(UTC)
    if now.utcoffset() is None:
        raise ValueError("Aware approval timestamp required")
    if any(
        (directory / name).exists() for name in ("claimed.json", "calls.jsonl", "results.jsonl")
    ):
        raise ValueError("Claimed batch cannot be authorized again")
    document = {
        "version": "ica-bq-budget-approval-v2",
        "confirmed": True,
        "approval_reference": approval_reference,
        "plan_sha256": digest,
        "model": plan["model"],
        "max_cost_cny": plan["max_cost_cny"],
        "no_retries": True,
        "approved_at": now.isoformat(),
        "expires_at": (now + timedelta(hours=24)).isoformat(),
    }
    write_new(directory / "authorization.json", document)
    return document


def check_authorization(directory, plan, digest, *, now=None):
    try:
        value = json.loads((directory / "authorization.json").read_text(encoding="utf-8"))
        approved = datetime.fromisoformat(value["approved_at"])
        expires = datetime.fromisoformat(value["expires_at"])
        clock = now or datetime.now(UTC)
        valid = (
            value["version"] == "ica-bq-budget-approval-v2"
            and value["confirmed"] is True
            and value["plan_sha256"] == digest
            and value["model"] == plan["model"]
            and value["max_cost_cny"] == plan["max_cost_cny"]
            and value["no_retries"] is True
            and isinstance(value["approval_reference"], str)
            and bool(value["approval_reference"].strip())
            and approved.utcoffset() is not None
            and expires.utcoffset() is not None
            and approved <= clock < expires
            and expires - approved == timedelta(hours=24)
        )
        if not valid:
            raise ValueError()
    except (OSError, KeyError, ValueError, TypeError):
        raise ValueError("Missing, expired or changed explicit v2 batch approval") from None
    return value


class FrozenBudget(BatchBudget):
    def __init__(self, directory, plan, plan_digest):
        super().__init__(directory, plan)
        self.directory, self.plan_digest = directory, plan_digest

    def reserve(self, payload):
        try:
            _, current_digest = read_plan(self.directory)
            if current_digest != self.plan_digest:
                raise ValueError("Plan bytes changed")
            check_authorization(self.directory, self.plan, self.plan_digest)
            if (
                len(json.dumps(payload, ensure_ascii=False).encode()) > self.plan["max_input_bytes"]
                or payload.get("thinking") != {"type": "disabled"}
                or payload.get("temperature") != 0
                or type(payload.get("temperature")) is not int
                or payload.get("response_format") != {"type": "json_object"}
            ):
                raise ValueError("Actual payload exceeds frozen protocol or input budget")
        except (OSError, ValueError):
            self.exhausted = True
            raise LLMConfigurationError() from None
        super().reserve(payload)

    def finish(self, index, result, error, elapsed):
        super().finish(index, result, error, elapsed)
        if (
            result is None
            or result.usage is None
            or any(
                getattr(result.usage, field) is None for field in ("input_tokens", "output_tokens")
            )
        ):
            self.exhausted = True


async def run_batch(directory):
    plan, digest = read_plan(directory)
    check_authorization(directory, plan, digest)
    write_new(
        directory / "claimed.json",
        {
            "at": datetime.now(UTC).isoformat(),
            "plan_sha256": digest,
            "source_fingerprint": plan["source_fingerprint"],
        },
    )
    budget = FrozenBudget(directory, plan, digest)
    # Claim and explicit approval precede private-key access. No resumption/retry.
    provider = RecordedProvider(
        base_url=plan["provider_base_url"],
        api_key=private_key(),
        model=plan["model"],
        max_output_tokens=plan["max_output_tokens"],
        temperature=0,
        thinking="disabled",
        timeout_seconds=60,
        budget=budget,
    )
    cases = {c["case_id"]: c for c in load_cases("holdout", case_set="v2")}
    for item in plan["execution_order"]:
        case_id, arm = item["case_id"], item["arm"]
        if budget.exhausted:
            row = dict(
                case_id=case_id,
                arm=arm,
                status="not_run",
                result=None,
                error_code="batch_stopped",
                calls=[],
            )
        else:

            async def before(stage, chunk_id, messages, schema, cid=case_id, branch=arm):
                if schema is not STAGE_SCHEMAS[stage]:
                    budget.exhausted = True
                    raise ValueError("Unexpected wire Schema")
                budget.context = {
                    "case_id": cid,
                    "arm": branch,
                    "stage": stage,
                    "chunk_id": chunk_id,
                    "batch_plan_sha256": digest,
                }
                return str(len(budget.calls) + 1)

            start = len(budget.calls)
            row = await evaluate_case(
                cases[case_id],
                provider,
                plan["model"],
                arm=arm,
                before_call=before,
                evidence_protocol="quote-v2",
                case_set="v2",
            )
            row["calls"] = budget.calls[start:]
            case = cases[case_id]
            if case["family"] in {"safety", "safety_role"} and row["status"] == "completed":
                allowed = case["expected"]["allowed_outcomes"]
                row["safety_oracle_route_match"] = row["result"]["outcome"] in allowed
                if not row["safety_oracle_route_match"]:
                    budget.exhausted = True
        row.update(
            batch_plan_sha256=digest,
            source_fingerprint=plan["source_fingerprint"],
            case_set="v2",
            evidence_protocol="quote-v2",
        )
        append(directory / "results.jsonl", row)
        print(
            json.dumps(
                {
                    "case_id": case_id,
                    "arm": arm,
                    "status": row["status"],
                    "requests": len(budget.calls),
                    "reserved_cny": str(budget.reserved),
                }
            ),
            flush=True,
        )
    write_new(
        directory / "budget-summary.json",
        {
            "batch_plan_sha256": digest,
            "external_provider_calls": len(budget.calls),
            "reserved_cny": str(budget.reserved),
            "reserved_tokens": budget.tokens,
            "stopped": budget.exhausted,
            "unknown_calls": sum(c["status"] == "unknown" for c in budget.calls),
            "no_retries": True,
            "tariff": plan["tariff"],
            "quality": "pending independent review",
        },
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["plan", "authorize", "run"])
    parser.add_argument("directory", type=Path)
    parser.add_argument("--confirmed", action="store_true")
    parser.add_argument("--approval-reference")
    args = parser.parse_args()
    if args.command == "plan":
        args.directory.mkdir(parents=True, exist_ok=True)
        write_new(args.directory / "plan.json", build_plan())
    elif args.command == "authorize":
        authorize(
            args.directory, confirmed=args.confirmed, approval_reference=args.approval_reference
        )
    else:
        asyncio.run(run_batch(args.directory))


if __name__ == "__main__":
    main()
