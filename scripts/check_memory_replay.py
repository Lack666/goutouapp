"""Run Phase 3G Golden memory cases through the real in-memory runtime."""

import sys
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    sys.path[:0] = [str(root), str(root / "apps/server")]
    from evals.phase3g_memory import SELECTED, evaluate_memory, run_memory_case

    failures = []
    for case_id in SELECTED:
        result, service, user_id, _ = run_memory_case(case_id)
        failures.extend(
            f"{case_id}: {error}" for error in evaluate_memory(case_id, result, service, user_id)
        )
    if failures:
        raise SystemExit("\n".join(failures))
    print(f"Golden Phase 3G memory runtime replay passed: {len(SELECTED)} cases")


if __name__ == "__main__":
    main()
