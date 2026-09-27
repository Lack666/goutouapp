"""Run all Golden routing constraints against semantic fixtures, without an LLM."""

import sys
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root))
    sys.path.insert(0, str(root / "apps/server"))
    from evals.phase3d_routing import evaluate_all

    count, failures = evaluate_all()
    if failures:
        raise SystemExit("\n".join(failures))
    print(f"Golden deterministic knowledge routing passed: {count} cases")


if __name__ == "__main__":
    main()
