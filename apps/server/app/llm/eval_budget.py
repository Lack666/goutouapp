"""Prepaid conservative reservations, including failed and unknown-outcome calls."""

import json
from dataclasses import dataclass
from decimal import Decimal
from threading import Lock

from app.llm.errors import LLMConfigurationError

# Official CNY peak prices, checked 2026-10-26. Peak is a safe upper bound.
PRICE_VERSION = "deepseek-flash-2026-10-26-peak-cny"
PRICE_SOURCE = "https://api-docs.deepseek.com/zh-cn/quick_start/pricing/"


def cost_cny(usage: dict | None) -> float | None:
    if not usage or usage.get("input_tokens") is None or usage.get("output_tokens") is None:
        return None
    hit, miss = usage.get("cache_hit_tokens"), usage.get("cache_miss_tokens")
    if hit is None or miss is None or hit + miss != usage["input_tokens"]:
        return None
    return float(
        (Decimal(hit) * Decimal("0.04") + Decimal(miss) * 2 + Decimal(usage["output_tokens"]) * 8)
        / 1000000
    )


@dataclass
class EvalBudget:
    max_requests: int = 30
    max_tokens: int = 500000
    max_cost_cny: float = 5
    requests: int = 0
    reserved_tokens: int = 0
    reserved_cny: Decimal = Decimal(0)
    exhausted: bool = False

    def __post_init__(self):
        self._lock = Lock()
        if self.max_requests < 1 or self.max_tokens < 1 or self.max_cost_cny <= 0:
            raise LLMConfigurationError()

    def reserve(self, payload: dict) -> None:
        # UTF-8 bytes plus generous per-message framing overestimates text tokens.
        if payload.get("model") != "deepseek-flash" or not payload.get("max_tokens"):
            raise LLMConfigurationError()
        inputs = len(json.dumps(payload["messages"], ensure_ascii=False).encode()) + 4096
        outputs = payload["max_tokens"]
        upper = Decimal(inputs * 2 + outputs * 8) / 1000000
        with self._lock:
            if (
                self.requests + 1 > self.max_requests
                or self.reserved_tokens + inputs + outputs > self.max_tokens
                or self.reserved_cny + upper > Decimal(str(self.max_cost_cny))
            ):
                self.exhausted = True
                raise LLMConfigurationError()
            self.requests += 1
            self.reserved_tokens += inputs + outputs
            self.reserved_cny += upper
