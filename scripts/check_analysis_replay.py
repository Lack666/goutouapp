"""Run Phase 3E Mock replay and structural evaluator without a live model."""

import asyncio
import sys
from pathlib import Path
from uuid import uuid4


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root))
    sys.path.insert(0, str(root / "apps/server"))

    from app.agent import AgentInput, AgentResult
    from app.agent.dependencies import RuntimeDependencies
    from app.agent.runtime import AgentRuntime
    from app.llm.mock import MockLLMProvider
    from evals.phase3c_semantic import replay_outputs
    from evals.phase3e_analysis import evaluate_analysis, fixture_analysis, selected_cases
    from evals.phase3f_action_response import fixture_action, fixture_response

    failures: list[str] = []
    cases = selected_cases()
    for case in cases:
        provider = MockLLMProvider()
        outputs = replay_outputs(case)
        for output in outputs:
            provider.queue_structured(output)
        expected = case["expected"]
        if expected["route"] != "safety":
            provider.queue_structured(
                fixture_analysis(
                    alias=expected["knowledge"]["required_any"][0],
                    fiu=outputs[2],
                    route=expected["route"],
                    assertions=expected["assertions"],
                )
            )
            action = fixture_action(
                scenario=expected["scenario"],
                route=expected["route"],
                assertions=expected["assertions"],
            )
            provider.queue_structured(action)
            provider.queue_structured(fixture_response(action))
        result = asyncio.run(
            AgentRuntime(dependencies=RuntimeDependencies(llm_provider=provider)).run(
                AgentInput(user_id=uuid4(), conversation_id=uuid4(), message=case["input"])
            )
        )
        if not isinstance(result, AgentResult):
            failures.append(f"{case['id']}: runtime failure")
        else:
            failures.extend(f"{case['id']}: {error}" for error in evaluate_analysis(case, result))
    if failures:
        raise SystemExit("\n".join(failures))
    print(f"Golden structural analysis Mock replay passed: {len(cases)} cases")


if __name__ == "__main__":
    main()
