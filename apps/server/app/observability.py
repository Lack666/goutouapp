"""Bounded content-free diagnostics; never serialize state, prompts or exceptions."""

from collections import deque
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import UTC, datetime
from time import perf_counter

GRAPH_VERSION = "phase3h-observed-v1"
PROMPT_VERSION = "phase11-source-first-v5"
_run: ContextVar[str | None] = ContextVar("observed_run", default=None)
_node: ContextVar[str | None] = ContextVar("observed_node", default=None)
_capture: ContextVar[dict | None] = ContextVar("provider_capture", default=None)


@dataclass
class TraceBuffer:
    capacity: int = 4096
    retention_seconds: int = 86400
    events: deque = field(default_factory=deque)

    def emit(self, event: dict) -> None:
        now = datetime.now(UTC).timestamp()
        while self.events and self.events[0][0] < now - self.retention_seconds:
            self.events.popleft()
        self.events.append((now, event))
        while len(self.events) > self.capacity:
            self.events.popleft()

    def snapshot(self) -> list[dict]:
        cutoff = datetime.now(UTC).timestamp() - self.retention_seconds
        return [dict(event) for stamp, event in list(self.events) if stamp >= cutoff]


TRACES = TraceBuffer()


def emit(kind: str, **fields) -> None:
    try:
        TRACES.emit(
            {
                "kind": kind,
                "time": datetime.now(UTC).isoformat(),
                "run_id": _run.get(),
                "node": _node.get(),
                **fields,
            }
        )
    except Exception:
        pass  # Diagnostics must never change business outcomes.


def error_category(exc: BaseException) -> str:
    from app.agent.errors import AgentError
    from app.llm.errors import LLMError

    if isinstance(exc, (LLMError, AgentError)):
        return exc.code
    return "cancelled" if not isinstance(exc, Exception) else "internal_error"


@contextmanager
def run_scope(run_id):
    token = _run.set(str(run_id))
    started = perf_counter()
    emit("run_start", graph_version=GRAPH_VERSION, prompt_version=PROMPT_VERSION)
    try:
        yield
    finally:
        emit("run_end", duration_ms=(perf_counter() - started) * 1000)
        _run.reset(token)


@contextmanager
def node_scope(name: str):
    token = _node.set(name)
    start = perf_counter()
    emit("node_start")
    status, error = "completed", None
    try:
        yield
    except BaseException as exc:
        status, error = "failed", error_category(exc)
        raise
    finally:
        emit("node_end", duration_ms=(perf_counter() - start) * 1000, status=status, error=error)
        _node.reset(token)


def capture_response(result) -> None:
    capture = _capture.get()
    if capture is not None:
        capture["model"] = result.model
        if result.usage is not None:
            capture["usage"] = result.usage.model_dump()


def capture_schema_errors(errors: list[dict]) -> None:
    capture = _capture.get()
    if capture is not None:
        # Pydantic error messages, locations and inputs may contain private text.
        allowed = {
            "missing",
            "extra_forbidden",
            "literal_error",
            "value_error",
            "json_invalid",
            "string_type",
            "list_type",
            "bool_type",
            "string_too_long",
            "string_too_short",
        }
        capture["schema_errors"] = sorted(
            {e["type"] if e["type"] in allowed else "validation_error" for e in errors}
        )[:10]


@contextmanager
def provider_scope(provider, operation: str):
    record = {
        "provider": "openai_compatible",
        "model": provider._model,
        "operation": operation,
        "usage": None,
        "ttft_ms": None,
    }
    token = _capture.set(record)
    start = perf_counter()
    record["status"], record["error"] = "completed", None
    try:
        yield record
    except BaseException as exc:
        record["status"], record["error"] = "failed", error_category(exc)
        raise
    finally:
        record["duration_ms"] = (perf_counter() - start) * 1000
        from app.llm.eval_budget import PRICE_VERSION, cost_cny

        record["cost_cny_upper_bound"] = (
            cost_cny(record["usage"]) if record["model"] == "deepseek-flash" else None
        )
        record["price_version"] = PRICE_VERSION if record["model"] == "deepseek-flash" else None
        emit("provider", **record)
        _capture.reset(token)
