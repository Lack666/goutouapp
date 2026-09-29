"""Portable phase-aware equivalent of the repository Make targets."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PHASE_STATE = json.loads((ROOT / "project-phase.json").read_text(encoding="utf-8"))
PHASE = PHASE_STATE["completed_phase"]
SUBPHASE = PHASE_STATE.get("completed_subphase")
BACKEND_FOUNDATION = PHASE >= 2 or SUBPHASE in {"2A", "2B", "2C", "2D"}
DATABASE_FOUNDATION = PHASE >= 2 or SUBPHASE in {"2B", "2C", "2D"}
LLM_FOUNDATION = PHASE >= 2 or SUBPHASE in {"2C", "2D"}
INTEGRATION_FOUNDATION = PHASE >= 2 or SUBPHASE == "2D"
AGENT_CONTRACTS = PHASE >= 3 or SUBPHASE in {"3A", "3B", "3C", "3D", "3E", "3F", "3G"}
AGENT_RUNTIME = PHASE >= 3 or SUBPHASE in {"3B", "3C", "3D", "3E", "3F", "3G"}
AGENT_SEMANTIC = PHASE >= 3 or SUBPHASE in {"3C", "3D", "3E", "3F", "3G"}
AGENT_KNOWLEDGE = PHASE >= 3 or SUBPHASE in {"3D", "3E", "3F", "3G"}
AGENT_ANALYSIS = PHASE >= 3 or SUBPHASE in {"3E", "3F", "3G"}
AGENT_ACTION_RESPONSE = PHASE >= 3 or SUBPHASE in {"3F", "3G"}
AGENT_MEMORY = PHASE >= 3 or SUBPHASE == "3G"
AGENT_STREAMING = PHASE >= 3 or SUBPHASE == "3H"
AGENT_SERVICE = PHASE >= 4 or SUBPHASE in {"4A", "4B", "4C", "4D"}
AGENT_REST = PHASE >= 4 or SUBPHASE in {"4B", "4C", "4D"}
AGENT_STREAM_TRANSPORT = PHASE >= 4 or SUBPHASE in {"4C", "4D"}
AGENT_IDEMPOTENCY = PHASE >= 4 or SUBPHASE == "4D"
CHAT_IMPORT_PARSER = PHASE >= 5 or SUBPHASE in {"5A", "5B", "5C", "5D"}
CHAT_IMPORT_JOBS = PHASE >= 5 or SUBPHASE in {"5B", "5C", "5D"}
CHAT_IMPORT_MERGE = PHASE >= 5 or SUBPHASE in {"5C", "5D"}
CHAT_IMPORT_API = PHASE >= 5 or SUBPHASE == "5D"
MEMORY_CONTROL_API = PHASE >= 6 or SUBPHASE in {"6A", "6B", "6C", "6D"}


def run(command: list[str]) -> None:
    print("+", " ".join(command), flush=True)
    subprocess.run(command, cwd=ROOT, check=True)


def doctor() -> None:
    print(f"Python {sys.version.split()[0]}")
    if sys.version_info < (3, 12):  # noqa: UP036 - doctor checks before uv starts
        raise RuntimeError("Python 3.12+ is required")
    for name in ("git", "uv", "node", "pnpm"):
        location = shutil.which(name)
        if not location:
            raise RuntimeError(f"Required tool missing: {name}")
        version = subprocess.run(
            [location, "--version"], capture_output=True, text=True, check=True
        ).stdout.strip()
        print(f"{name}: {version} ({location})")
    print(f"make: {shutil.which('make') or 'use make.cmd on Windows'}")
    docker = shutil.which("docker")
    if docker:
        version = subprocess.run(
            [docker, "--version"], capture_output=True, text=True, check=True
        ).stdout.strip()
        print(f"docker: {version} ({docker})")
    else:
        print("docker: MISSING (required for Phase 2B PostgreSQL demo)")
    print(f"Completed phase: {PHASE}")
    if SUBPHASE:
        print(f"Completed subphase: {SUBPHASE}")


def uv_run(*args: str) -> None:
    command = ["uv", "--cache-dir", str(ROOT / ".cache" / "uv")]
    if sys.platform == "win32":
        command.append("--no-managed-python")
    command.extend(["run", "--locked"])
    if (ROOT / ".env").is_file():
        command.extend(["--env-file", ".env"])
    run([*command, *args])


def tests() -> None:
    run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"])
    run([sys.executable, "knowledge/goutoujunshi/scripts/validate_skill.py"])
    if DATABASE_FOUNDATION:
        uv_run("python", "scripts/check_db_migrations.py")
    if LLM_FOUNDATION:
        uv_run(
            "pytest",
            "-q",
            "apps/server/tests/test_llm_mock.py",
            "apps/server/tests/test_llm_openai_compatible.py",
        )
    if INTEGRATION_FOUNDATION:
        uv_run("pytest", "-q", "apps/server/tests/test_backend_integration.py")
    if AGENT_CONTRACTS:
        uv_run("pytest", "-q", "apps/server/tests/test_agent_contracts.py")
    if AGENT_RUNTIME:
        uv_run("pytest", "-q", "apps/server/tests/test_agent_runtime.py")
    if AGENT_SEMANTIC:
        uv_run("pytest", "-q", "apps/server/tests/test_agent_semantic.py")
    if AGENT_KNOWLEDGE:
        uv_run("pytest", "-q", "apps/server/tests/test_agent_knowledge.py")
        uv_run("python", "scripts/check_knowledge_routing.py")
    if AGENT_ANALYSIS:
        uv_run("pytest", "-q", "apps/server/tests/test_agent_analysis.py")
        uv_run("python", "scripts/check_analysis_replay.py")
    if AGENT_ACTION_RESPONSE:
        uv_run("pytest", "-q", "apps/server/tests/test_agent_action_response.py")
        uv_run("python", "scripts/check_action_response_replay.py")
    if AGENT_MEMORY:
        uv_run("pytest", "-q", "apps/server/tests/test_agent_memory.py")
        uv_run("pytest", "-q", "apps/server/tests/test_memory_database.py")
        uv_run("python", "scripts/check_memory_replay.py")
    if AGENT_STREAMING:
        uv_run("pytest", "-q", "apps/server/tests/test_agent_streaming.py")
        uv_run("pytest", "-q", "apps/server/tests/test_phase3_e2e.py")
    if AGENT_SERVICE:
        uv_run("pytest", "-q", "apps/server/tests/test_agent_service.py")
        uv_run("python", "apps/server/agent_service_demo.py")
    if AGENT_REST:
        uv_run(
            "pytest",
            "-q",
            "apps/server/tests/test_auth_jwt.py",
            "apps/server/tests/test_agent_rest_contract.py",
            "apps/server/tests/test_agent_rest.py",
        )
        uv_run("python", "apps/server/agent_rest_demo.py")
    if AGENT_STREAM_TRANSPORT:
        uv_run(
            "pytest",
            "-q",
            "apps/server/tests/test_agent_stream_contract.py",
            "apps/server/tests/test_agent_stream_api.py",
            "apps/server/tests/test_agent_stream_disconnect.py",
        )
        uv_run("python", "apps/server/agent_stream_demo.py")
    if AGENT_IDEMPOTENCY:
        uv_run("pytest", "-q", "apps/server/tests/test_phase4_idempotency.py")
    if CHAT_IMPORT_PARSER:
        uv_run("pytest", "-q", "apps/server/tests/test_chat_import.py")
        uv_run("python", "apps/server/chat_import_demo.py")
    if CHAT_IMPORT_JOBS:
        uv_run("pytest", "-q", "apps/server/tests/test_import_jobs.py")
        uv_run("python", "apps/server/import_job_demo.py")
    if CHAT_IMPORT_MERGE:
        uv_run("pytest", "-q", "apps/server/tests/test_import_merge.py")
        uv_run("python", "apps/server/import_merge_demo.py")
    if CHAT_IMPORT_API:
        uv_run("pytest", "-q", "apps/server/tests/test_import_api.py")
        uv_run("python", "apps/server/import_api_demo.py")
    if MEMORY_CONTROL_API:
        uv_run("pytest", "-q", "apps/server/tests/test_memory_control.py")
        uv_run("python", "apps/server/memory_control_demo.py")
        uv_run("python", "apps/server/memory_control_http_demo.py")
    if BACKEND_FOUNDATION:
        uv_run("pytest", "-q", "apps/server/tests")


def lint() -> None:
    if not BACKEND_FOUNDATION:
        print("DEFERRED: backend lint begins at Phase 2A")
        return
    uv_run(
        "ruff",
        "check",
        "apps/server",
        "evals/phase3c_semantic.py",
        "evals/phase3d_routing.py",
        "evals/phase3e_analysis.py",
        "evals/phase3f_action_response.py",
        "evals/phase3g_memory.py",
        "scripts/verify.py",
        "scripts/check_knowledge_routing.py",
        "scripts/check_analysis_replay.py",
        "scripts/check_action_response_replay.py",
        "scripts/check_memory_replay.py",
        "scripts/check_db_migrations.py",
    )
    uv_run(
        "ruff",
        "format",
        "--check",
        "apps/server",
        "evals/phase3c_semantic.py",
        "evals/phase3d_routing.py",
        "evals/phase3e_analysis.py",
        "evals/phase3f_action_response.py",
        "evals/phase3g_memory.py",
        "scripts/verify.py",
        "scripts/check_knowledge_routing.py",
        "scripts/check_analysis_replay.py",
        "scripts/check_action_response_replay.py",
        "scripts/check_memory_replay.py",
        "scripts/check_db_migrations.py",
    )


def evals() -> None:
    if PHASE < 1:
        print("DEFERRED: golden evaluation gate begins at Phase 1")
        return
    run([sys.executable, "evals/validate.py"])


def repository_checks() -> None:
    safe_directory = f"safe.directory={ROOT.as_posix()}"
    tracked = (
        subprocess.run(
            ["git", "-c", safe_directory, "ls-files", "-z"],
            cwd=ROOT,
            capture_output=True,
            check=True,
        )
        .stdout.decode("utf-8", errors="surrogateescape")
        .split("\0")
    )
    forbidden = [
        name
        for name in tracked
        if Path(name).name.startswith(".env") and Path(name).name != ".env.example"
    ]
    if forbidden:
        raise RuntimeError("Tracked environment secret file found: " + ", ".join(forbidden))
    if not (ROOT / ".env.example").is_file():
        raise RuntimeError("Missing .env.example")
    for name in (".env", ".env.local"):
        ignored = subprocess.run(
            ["git", "-c", safe_directory, "check-ignore", "-q", "--", name],
            cwd=ROOT,
            check=False,
        )
        if ignored.returncode != 0:
            raise RuntimeError(f"Git does not ignore {name}")
    mobile = ROOT / "apps" / "mobile"
    if mobile.exists():
        for path in mobile.rglob("*"):
            if path.is_file() and path.suffix in {".ts", ".tsx", ".js", ".json"}:
                content = path.read_text(encoding="utf-8")
                if "EXPO_PUBLIC_OPENAI" in content or "EXPO_PUBLIC_DEEPSEEK" in content:
                    raise RuntimeError(f"Model key prefix in mobile: {path}")
    print("Repository secret boundary check passed")


def verify() -> None:
    doctor()
    tests()
    evals()
    repository_checks()
    lint()
    if DATABASE_FOUNDATION:
        print("PASS: PostgreSQL migration and integration gate")
    elif BACKEND_FOUNDATION:
        print("DEFERRED: PostgreSQL models, migrations and Docker demo begin at Phase 2B")
    else:
        print("DEFERRED: backend foundation begins at Phase 2A")
    if LLM_FOUNDATION:
        print("PASS: LLM Provider unit gate")
    if INTEGRATION_FOUNDATION:
        print("PASS: Backend integration smoke gate")
    if AGENT_CONTRACTS:
        print("PASS: Agent contracts and Golden schema compatibility gate")
    if AGENT_RUNTIME:
        print("PASS: Minimal standalone LangGraph runtime gate")
    else:
        print("DEFERRED: Minimal LangGraph runtime")
    if AGENT_SEMANTIC:
        print("PASS: Safety, Scenario and FIU node/24-case replay gate")
    else:
        print("DEFERRED: Safety, Scenario and FIU semantic nodes")
    if AGENT_KNOWLEDGE:
        print("PASS: Deterministic knowledge router, frozen loader and 81-case fixture evaluation")
    else:
        print("DEFERRED: Knowledge router and reference loader")
    if AGENT_ANALYSIS:
        print("PASS: Structured relationship analysis and 30-case Mock replay gate")
    else:
        print("DEFERRED: Relationship analysis")
    if AGENT_ACTION_RESPONSE:
        print("PASS: Structured action/response generation and 38-case Mock replay gate")
    else:
        print("DEFERRED: Action/response generation")
    if AGENT_MEMORY:
        print("PASS: Consent-gated memory runtime, PostgreSQL persistence and 14-case Mock replay")
        print("DEFERRED: full live-model Golden runtime eval")
    else:
        print("DEFERRED: memory and full live-model Golden runtime eval")
    if AGENT_SERVICE:
        print("PASS: Phase 4A Agent Application Service")
    if AGENT_REST:
        print("PASS: Phase 4B REST/Auth, signed-JWT PostgreSQL integration and real HTTP demo")
    if AGENT_STREAM_TRANSPORT:
        print("PASS: Phase 4C Streaming Transport, disconnect policy and socket demo")
    if AGENT_IDEMPOTENCY:
        print(
            "PASS: Phase 4D persistent and cross-transport idempotency, "
            "PostgreSQL race and replay demo"
        )
    if CHAT_IMPORT_PARSER:
        print("PASS: Phase 5A chat import parser, dry run and 10k-message fixture")
    if CHAT_IMPORT_JOBS:
        print("PASS: Phase 5B persistent jobs, binding and PostgreSQL demo")
    if CHAT_IMPORT_MERGE:
        print("PASS: Phase 5C atomic relationship message merge and 10k PostgreSQL import")
    if CHAT_IMPORT_API:
        print("PASS: Phase 5D authenticated one-upload import, cleanup, pagination and 10k HTTP")
    if MEMORY_CONTROL_API:
        print("PASS: Phase 6A Memory Control Service, signed API and Agent integration")
        print("DEFERRED TO 6B: Undo/Delete Public Controls")
        print("DEFERRED TO 6C: Retention Policy")
        print("DEFERRED TO PHASE 7: Mobile")
    if AGENT_STREAMING:
        print("PASS: Typed runtime streaming and eight standalone Phase 3 E2E cases")
    if PHASE < 7:
        print("DEFERRED: Mobile lint/typecheck begin at Phase 7")
    if PHASE > 5:
        raise RuntimeError(
            "Later-phase verification is not implemented; do not mark that phase complete"
        )
    if PHASE == 5:
        if not all(
            (
                AGENT_CONTRACTS,
                AGENT_RUNTIME,
                AGENT_SEMANTIC,
                AGENT_KNOWLEDGE,
                AGENT_ANALYSIS,
                AGENT_ACTION_RESPONSE,
                AGENT_MEMORY,
                AGENT_STREAMING,
                AGENT_SERVICE,
                AGENT_REST,
                AGENT_STREAM_TRANSPORT,
                AGENT_IDEMPOTENCY,
                CHAT_IMPORT_PARSER,
                CHAT_IMPORT_JOBS,
                CHAT_IMPORT_MERGE,
                CHAT_IMPORT_API,
            )
        ):
            raise RuntimeError("Phase 5 import pipeline gate is incomplete")
        print("PASS: Phase 4 API")
        print("PASS: Phase 5 Chat Import and Relationship Data Pipeline")
        if MEMORY_CONTROL_API:
            print("PASS: Phase 6A Memory Control Service and Public Contracts")
        print("DEFERRED: Chat Analysis")
        print("DEFERRED: Mobile")
        print("DEFERRED: RAG")
        print(
            "PASS: all active Phase 0..5 and 6A gates"
            if MEMORY_CONTROL_API
            else "PASS: all active Phase 0..5 gates"
        )
        return
    if PHASE == 4:
        if not all(
            (
                AGENT_CONTRACTS,
                AGENT_RUNTIME,
                AGENT_SEMANTIC,
                AGENT_KNOWLEDGE,
                AGENT_ANALYSIS,
                AGENT_ACTION_RESPONSE,
                AGENT_MEMORY,
                AGENT_STREAMING,
                AGENT_SERVICE,
                AGENT_REST,
                AGENT_STREAM_TRANSPORT,
                AGENT_IDEMPOTENCY,
            )
        ):
            raise RuntimeError("Phase 4 API gate is incomplete")
        print("PASS: Phase 3 Agent Runtime")
        print("PASS: Phase 4 Application Service / REST / Auth / Streaming / Idempotency")
        if CHAT_IMPORT_PARSER:
            print("PASS: Phase 5A Chat Import Contract and Parser Foundation")
            if CHAT_IMPORT_JOBS:
                print("PASS: Phase 5B Persistent Import Jobs and Speaker / Relationship Binding")
            else:
                print("DEFERRED: Persistent Import Jobs")
                print("DEFERRED: Speaker Binding")
            if CHAT_IMPORT_MERGE:
                print("PASS: Phase 5C Imported Message Persistence and Idempotent Merge")
            else:
                print("DEFERRED: Imported Message DB Persistence")
        else:
            print("DEFERRED: Chat Import")
        print("DEFERRED: Mobile")
        print("DEFERRED: RAG")
        print(
            "PASS: all active Phase 0..4 and Phase 5A/5B/5C gates"
            if CHAT_IMPORT_MERGE
            else "PASS: all active Phase 0..4 and Phase 5A/5B gates"
            if CHAT_IMPORT_JOBS
            else "PASS: all active Phase 0..4 and Phase 5A gates"
            if CHAT_IMPORT_PARSER
            else "PASS: all active Phase 0..4 gates"
        )
        return
    if PHASE == 3:
        if not all(
            (
                AGENT_CONTRACTS,
                AGENT_RUNTIME,
                AGENT_SEMANTIC,
                AGENT_KNOWLEDGE,
                AGENT_ANALYSIS,
                AGENT_ACTION_RESPONSE,
                AGENT_MEMORY,
                AGENT_STREAMING,
            )
        ):
            raise RuntimeError("Phase 3 Agent Runtime gate is incomplete")
        print("PASS: Phase 3 Agent Runtime")
        print("DEFERRED: RAG")
        if AGENT_STREAM_TRANSPORT:
            print("DEFERRED: Persistent Idempotency")
        elif AGENT_REST:
            print("DEFERRED: Network Streaming, Persistent Idempotency")
        else:
            print(
                "DEFERRED: REST API, Network Streaming, Authentication Transport, "
                "Full API Idempotency"
            )
        print("DEFERRED: Mobile")
        if AGENT_STREAM_TRANSPORT:
            print("PASS: all active Phase 0..3 and Phase 4A..4C gates")
        elif AGENT_REST:
            print("PASS: all active Phase 0..3, Phase 4A and Phase 4B gates")
        elif AGENT_SERVICE:
            print("PASS: all active Phase 0..3 and Phase 4A gates")
        else:
            print("PASS: all active Phase 0..3 gates")
        return
    if PHASE == 2:
        print("PASS: Phase 2 Backend Foundation")
        if AGENT_CONTRACTS:
            print("PASS: Phase 3A Agent State and Runtime Contracts")
            if AGENT_RUNTIME:
                print("PASS: Phase 3B Minimal Standalone LangGraph Runtime")
                if AGENT_SEMANTIC:
                    print("PASS: Phase 3C Safety, Scenario and FIU Semantic Nodes")
                    if AGENT_KNOWLEDGE:
                        print("PASS: Phase 3D Knowledge Router and Reference Loading Runtime")
                        if AGENT_ANALYSIS:
                            print("PASS: Phase 3E Relationship Analysis Runtime")
                            if AGENT_ACTION_RESPONSE:
                                print("PASS: Phase 3F Action Plan and Response Generation")
                                if AGENT_MEMORY:
                                    print("PASS: Phase 3G Memory Candidate and Persistence Runtime")
                                    print("PASS: all active Phase 0..2 and 3A..3G gates")
                                else:
                                    print("PASS: all active Phase 0..2 and 3A..3F gates")
                            else:
                                print("PASS: all active Phase 0..2 and 3A..3E gates")
                        else:
                            print("PASS: all active Phase 0..2 and 3A..3D gates")
                    else:
                        print("PASS: all active Phase 0..2 and 3A..3C gates")
                else:
                    print("PASS: all active Phase 0..2 and 3A..3B gates")
            else:
                print("PASS: all active Phase 0..2 and 3A gates")
        else:
            print("PASS: all active Phase 0..2 gates")
        return
    passed = f"Phase 0..{PHASE}"
    if BACKEND_FOUNDATION:
        passed += " and Phase 2A"
    if DATABASE_FOUNDATION:
        passed += " and Phase 2B"
    if LLM_FOUNDATION:
        passed += " and Phase 2C"
    print(f"PASS: all active {passed} gates")


def dev() -> None:
    if not BACKEND_FOUNDATION:
        raise RuntimeError("No development service exists before Phase 2A")
    uv_run("python", "apps/server/run.py")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("target", choices=("doctor", "dev", "test", "lint", "eval", "verify"))
    args = parser.parse_args()
    try:
        {
            "doctor": doctor,
            "dev": dev,
            "test": tests,
            "lint": lint,
            "eval": evals,
            "verify": verify,
        }[args.target]()
    except (RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
