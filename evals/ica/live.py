"""One claimed synthetic evaluation batch; durable prepaid budget, never automatic replay."""

import argparse
import asyncio
import hashlib
import json
import os
import re
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from time import perf_counter
from uuid import NAMESPACE_URL, uuid5

from pydantic import SecretStr

from app.llm.errors import LLMConfigurationError
from app.llm.openai_compatible import OpenAICompatibleProvider

ROOT = Path(__file__).resolve().parents[2]
PRICE = {
    "version": "deepseek-flash-2026-11-04-peak-cny",
    "source": "https://api-docs.deepseek.com/zh-cn/quick_start/pricing/",
    "checked_at": "2026-11-04",
    "model": "deepseek-flash",
    "documented_version": "DeepSeek-V4.1-Flash-1017",
    "currency": "CNY",
    "hit_per_million": "0.04",
    "miss_per_million": "2",
    "output_per_million": "8",
}


def write_new(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as output:
        json.dump(value, output, ensure_ascii=False, indent=2)
        output.write("\n")
        output.flush()
        os.fsync(output.fileno())


def append(path, value):
    with path.open("a", encoding="utf-8", newline="\n") as output:
        output.write(json.dumps(value, ensure_ascii=False) + "\n")
        output.flush()
        os.fsync(output.fileno())


def fingerprint():
    paths = [
        *sorted((ROOT / "apps/server/app/agent").rglob("*.py")),
        *sorted((ROOT / "apps/server/app/llm").glob("*.py")),
        *sorted((ROOT / "evals/ica").glob("*.py")),
        ROOT / "evals/ica/v1/cases.jsonl",
        ROOT / "evals/ica/v1/manifest.json",
        ROOT / "evals/ica/safety_role_cases.v1.json",
        ROOT / "knowledge/upstream-manifest.json",
        ROOT / "evals/reference_map.json",
        ROOT / "apps/server/app/chat_import/analysis_scope.py",
        *(ROOT / "knowledge/goutoujunshi").rglob("*.md"),
        ROOT / "uv.lock",
    ]
    entries = [
        (p.relative_to(ROOT).as_posix(), hashlib.sha256(p.read_bytes()).hexdigest()) for p in paths
    ]
    return hashlib.sha256(json.dumps(entries).encode()).hexdigest()


class BatchBudget:
    def __init__(self, directory, plan):
        self.path = directory / "calls.jsonl"
        if self.path.exists():
            raise ValueError("Existing call ledger: automatic replay forbidden")
        self.plan, self.context = plan, {}
        self.tariff = plan.get("tariff", PRICE)
        self.calls, self.tokens, self.reserved, self.exhausted = [], 0, Decimal(0), False

    def reserve(self, payload):
        if payload.get("model") != self.plan["model"]:
            raise LLMConfigurationError()
        output = payload.get("max_tokens")
        if type(output) is not int or output != self.plan["max_output_tokens"]:
            raise LLMConfigurationError()
        # The actual adapter payload already contains the full inline JSON Schema.
        size = len(json.dumps(payload, ensure_ascii=False).encode())
        inputs = size + 4096
        upper = (
            inputs * Decimal(self.tariff["miss_per_million"])
            + output * Decimal(self.tariff["output_per_million"])
        ) / 1_000_000
        if (
            self.exhausted
            or len(self.calls) >= self.plan["max_requests"]
            or self.tokens + inputs + output > self.plan["max_reserved_tokens"]
            or self.reserved + upper > Decimal(self.plan["max_cost_cny"])
        ):
            self.exhausted = True
            raise LLMConfigurationError()
        call = {
            "call_id": len(self.calls) + 1,
            **self.context,
            "status": "admitted",
            "wire_bytes": size,
            "reserved_tokens": inputs + output,
            "reserved_cny": str(upper),
            "at": datetime.now(UTC).isoformat(),
        }
        # Durable admission precedes the HTTP send. Failed/unknown reservations remain spent.
        append(self.path, call)
        self.calls.append(call)
        self.tokens += inputs + output
        self.reserved += upper

    def finish(self, index, result, error, elapsed):
        call = self.calls[index]
        usage = result.usage.model_dump() if result and result.usage else None
        actual = None
        if (
            usage
            and usage.get("input_tokens") is not None
            and usage.get("output_tokens") is not None
        ):
            # Peak, cache-miss estimate remains an upper bound when cache detail is absent.
            actual = str(
                (
                    usage["input_tokens"] * Decimal(self.tariff["miss_per_million"])
                    + usage["output_tokens"] * Decimal(self.tariff["output_per_million"])
                )
                / 1_000_000
            )
        event = {
            "call_id": call["call_id"],
            "status": "returned" if result else "unknown",
            "error_code": error,
            "elapsed_ms": round(elapsed * 1000, 2),
            "usage": usage,
            "observed_peak_cost_upper_cny": actual,
            "returned_model": result.model if result else None,
        }
        # Only visible synthetic output; the adapter discards hidden reasoning fields.
        if result:
            event["synthetic_visible_output"] = result.content
        append(self.path, event)
        call.update(event)
        if usage and (
            usage["input_tokens"] is None
            or usage["output_tokens"] is None
            or usage["input_tokens"] + usage["output_tokens"] > call["reserved_tokens"]
        ):
            self.exhausted = True


class RecordedProvider(OpenAICompatibleProvider):
    async def _chat_request(self, *args, **kwargs):
        index, start = len(self._budget.calls), perf_counter()
        try:
            result = await super()._chat_request(*args, **kwargs)
        except Exception as exc:
            if len(self._budget.calls) > index:
                self._budget.finish(index, None, type(exc).__name__, perf_counter() - start)
            raise
        self._budget.finish(index, result, None, perf_counter() - start)
        return result


def private_key():
    value = os.getenv("LLM_API_KEY")
    if not value:
        path = ROOT / "api.txt"
        matches = re.findall(r"sk-[A-Za-z0-9_-]+", path.read_text(encoding="utf-8-sig"))
        if len(matches) != 1:
            raise ValueError("Exactly one existing private backend key required")
        value = matches[0]
    return SecretStr(value)


async def run_batch(directory):
    from app.agent.contracts import AgentInput, AgentResult
    from app.agent.dependencies import RuntimeDependencies
    from app.agent.runtime import AgentRuntime
    from evals.ica.runner import evaluate_case, load_cases

    plan = json.loads((directory / "plan.json").read_text(encoding="utf-8"))
    if plan["source_fingerprint"] != fingerprint() or plan["tariff"] != PRICE:
        raise ValueError("Frozen source/tariff mismatch")
    if plan["max_cost_cny"] != "20" or not plan["no_retries"]:
        raise ValueError("This authorization is a single no-retry CNY20 batch")
    write_new(
        directory / "claimed.json",
        {"at": datetime.now(UTC).isoformat(), "source_fingerprint": fingerprint()},
    )
    budget = BatchBudget(directory, plan)
    provider = RecordedProvider(
        base_url="https://api.deepseek.com",
        api_key=private_key(),
        model=plan["model"],
        max_output_tokens=plan["max_output_tokens"],
        temperature=0,
        thinking="disabled",
        timeout_seconds=60,
        budget=budget,
    )
    # The explicit role regressions are development material, never a new blind holdout.
    roles = json.loads((ROOT / "evals/ica/safety_role_cases.v1.json").read_text(encoding="utf-8"))
    for case in roles:
        budget.context = {"case_id": case["case_id"], "arm": "role_regression", "stage": "safety"}
        row = {"case_id": case["case_id"], "status": "failed", "result": None}
        try:
            result = await AgentRuntime(
                dependencies=RuntimeDependencies(llm_provider=provider)
            ).run(
                AgentInput(
                    user_id=uuid5(NAMESPACE_URL, case["case_id"] + "/user"),
                    conversation_id=uuid5(NAMESPACE_URL, case["case_id"] + "/conversation"),
                    message=case["input"],
                    memory_enabled=False,
                )
            )
            if not isinstance(result, AgentResult):
                raise ValueError("role_runtime_failed")
            row.update(status="completed", result=result.model_dump(mode="json"))
            row["role_match"] = (
                result.safety.user_role == case["expected_role"]
                and result.route.value == case["expected_route"]
            )
        except Exception as exc:
            row["error_code"] = type(exc).__name__
        append(directory / "role-results.jsonl", row)
        print(json.dumps({"role_case": case["case_id"], "status": row["status"]}), flush=True)
        if not row.get("role_match"):
            budget.exhausted = True
        if budget.exhausted:
            break
    cases = {case["case_id"]: case for case in load_cases("holdout")}
    for case_id in plan["case_ids"]:
        for arm in plan["arms"]:
            if budget.exhausted:
                row = {
                    "case_id": case_id,
                    "arm": arm,
                    "status": "not_run",
                    "result": None,
                    "error_code": "batch_stopped",
                    "calls": [],
                    "source_fingerprint": plan["source_fingerprint"],
                }
            else:

                async def before(stage, chunk_id, messages, schema, cid=case_id, branch=arm):
                    budget.context = {
                        "case_id": cid,
                        "arm": branch,
                        "stage": stage,
                        "chunk_id": chunk_id,
                    }
                    return str(len(budget.calls) + 1)

                start = len(budget.calls)
                row = await evaluate_case(
                    cases[case_id], provider, plan["model"], arm=arm, before_call=before
                )
                row["calls"] = budget.calls[start:]
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
            "external_provider_calls": len(budget.calls),
            "reserved_cny": str(budget.reserved),
            "reserved_tokens": budget.tokens,
            "stopped": budget.exhausted,
            "unknown_calls": sum(c["status"] == "unknown" for c in budget.calls),
            "no_retries": True,
            "tariff": PRICE,
        },
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["plan", "run"])
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    if args.command == "run":
        asyncio.run(run_batch(args.directory))
        return
    from evals.ica.runner import load_cases

    args.directory.mkdir(parents=True, exist_ok=True)
    cases = load_cases("holdout")
    write_new(
        args.directory / "plan.json",
        {
            "version": "ica-bq-batch-v1",
            "source_fingerprint": fingerprint(),
            "tariff": PRICE,
            "model": PRICE["model"],
            "case_ids": [c["case_id"] for c in cases if c["split"] == "holdout"],
            "arms": ["event", "baseline"],
            "max_requests": 400,
            "max_reserved_tokens": 10_000_000,
            "max_cost_cny": "20",
            "max_output_tokens": 4096,
            "no_retries": True,
            "synthetic_only": True,
            "human_quality": "pending independent human review",
            "stop_conditions": [
                "budget admission failure",
                "usage above reservation",
                "safety role regression failure",
                "manual stop",
            ],
        },
    )


if __name__ == "__main__":
    main()
