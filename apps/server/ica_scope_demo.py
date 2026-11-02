"""Run with uv run python apps/server/ica_scope_demo.py; synthetic preparation only."""

import json
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

from app.chat_import.analysis_scope import (
    AnalysisScope,
    ScopeMessage,
    budget_plan,
    calendar_window,
    prepare_context,
    preview,
)


def main():
    output = Path("docs/evidence/ica-a-v3")
    output.mkdir(parents=True, exist_ok=True)
    for days, count in [(3, 900), (7, 2100)]:
        now = datetime(2026, 11, 2, 10, tzinfo=UTC)
        start, end = calendar_window("Asia/Shanghai", now, days=days)
        scope = AnalysisScope(UUID(int=1), UUID(int=2), UUID(int=3), "Asia/Shanghai", start, end)
        messages = [
            ScopeMessage(
                UUID(int=100 + i),
                scope.owner_id,
                scope.person_id,
                scope.dataset_id,
                start + timedelta(seconds=i * 60),
                "self" if i % 2 else "person",
                "匿名合成消息😀",
            )
            for i in range(count)
        ]
        context = prepare_context(scope, messages)
        data = {
            "scope": asdict(scope),
            "preview": preview(context),
            "manifest": [asdict(c) for c in context.chunks],
            "budget": budget_plan(
                context,
                prompt_reserve_bytes=8192,
                max_output_tokens=4096,
                price_per_million=1000000,
            ),
            "tariff": "synthetic microcurrency only; not a real model quote",
        }
        (output / f"preview-{days}d.json").write_text(
            json.dumps(data, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8"
        )
        print(json.dumps(data["preview"], ensure_ascii=True))


if __name__ == "__main__":
    main()
