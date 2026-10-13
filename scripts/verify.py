"""Portable phase-aware equivalent of the repository Make targets."""

from __future__ import annotations

import argparse
import hashlib
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
MEMORY_MUTATION_API = PHASE >= 6 or SUBPHASE in {"6B", "6C", "6D"}
MEMORY_RETENTION = (
    PHASE >= 6
    or SUBPHASE in {"6C", "6D"}
    or (ROOT / "apps/server/app/services/memory_retention.py").is_file()
)
MEMORY_PHASE6_E2E = (
    PHASE >= 6 or SUBPHASE == "6D" or (ROOT / "apps/server/tests/test_phase6_e2e.py").is_file()
)
MOBILE_FOUNDATION = (ROOT / "apps/mobile/package.json").is_file()
MOBILE_FEATURE_UI = (ROOT / "apps/mobile/src/features/ChatScreen.tsx").is_file()
MOBILE_CONTROLS_UI = (ROOT / "apps/mobile/src/features/ImportScreen.tsx").is_file()
MOBILE_FINAL_UI = (ROOT / "apps/mobile/tests/integration.test.tsx").is_file()
PUBLIC_RESOURCES_API = (ROOT / "apps/server/app/api/v1/resources.py").is_file()
MOBILE_CONNECTED = (ROOT / "apps/mobile/src/data/resourceController.ts").is_file()
MOBILE_AGENT_CHAT = (ROOT / "apps/mobile/src/data/agentChatController.ts").is_file()
MOBILE_IMPORT = (ROOT / "apps/mobile/src/data/importController.ts").is_file()
MOBILE_MEMORY = (ROOT / "apps/mobile/src/data/memoryController.ts").is_file()
UPLOAD_SECURITY = (ROOT / "apps/server/tests/test_upload_security.py").is_file()
MEMORY_GATE_FILES = (
    "apps/mobile/src/api/memoryAdapter.ts",
    "apps/mobile/src/api/memoryErrors.ts",
    "apps/mobile/src/contracts/connectedMemory.ts",
    "apps/mobile/src/features/ConnectedMemoryPanel.tsx",
    "apps/mobile/tests/connectedMemory.test.ts",
    "apps/mobile/tests/connectedMemoryUI.test.tsx",
    "apps/mobile/memory-connected/http.spec.ts",
    "apps/mobile/memory-connected/web.spec.ts",
    "apps/mobile/playwright.memory.config.ts",
    "docs/MOBILE_MEMORY_INTEGRATION.md",
    "docs/PHASE_8E_ACCEPTANCE.md",
    "docs/adr/0035-mobile-memory-guards-and-session-recovery.md",
)
IMPORT_GATE_FILES = (
    "apps/mobile/src/data/filePicker.native.ts",
    "apps/mobile/src/data/historyController.ts",
    "apps/mobile/src/api/importAdapter.ts",
    "apps/mobile/src/features/ConnectedImportScreen.tsx",
    "apps/mobile/src/features/ConnectedHistoryScreen.tsx",
    "apps/mobile/tests/connectedImport.test.ts",
    "apps/mobile/tests/connectedHistory.test.ts",
    "apps/mobile/tests/filePicker.test.ts",
    "apps/mobile/tests/connectedImportUI.test.tsx",
    "apps/mobile/import-connected/http.spec.ts",
    "apps/mobile/import-connected/web.spec.ts",
    "apps/mobile/playwright.import.config.ts",
    "docs/PHASE_8D_API_AUDIT.md",
    "docs/PHASE_8D_ACCEPTANCE.md",
    "docs/adr/0034-mobile-import-and-relationship-history.md",
)
AGENT_CHAT_GATE_FILES = (
    "apps/mobile/src/api/agentEvents.ts",
    "apps/mobile/src/api/sseParser.ts",
    "apps/mobile/src/api/streamFetch.native.ts",
    "apps/mobile/src/features/ConnectedChatScreen.tsx",
    "apps/mobile/tests/sseParser.test.ts",
    "apps/mobile/tests/agentChat.test.ts",
    "apps/mobile/tests/connectedChatUI.test.tsx",
    "apps/mobile/agent-connected/http.spec.ts",
    "apps/mobile/agent-connected/web.spec.ts",
    "apps/mobile/playwright.agent.config.ts",
    "docs/MOBILE_AGENT_CHAT.md",
    "docs/MOBILE_STREAMING.md",
    "docs/PHASE_8C_ACCEPTANCE.md",
)
CONNECTED_GATE_FILES = (
    "apps/mobile/src/api/generated/client.ts",
    "apps/mobile/src/api/transport.ts",
    "apps/mobile/src/session/developmentSession.ts",
    "apps/mobile/src/session/tokenStorage.native.ts",
    "apps/mobile/tests/connected.test.ts",
    "apps/mobile/connected/http.spec.ts",
    "apps/mobile/connected/web.spec.ts",
    "apps/server/mobile_connected_fixture.py",
    "apps/server/tests/test_mobile_dev_cors.py",
    "tools/api-codegen/generate-api.mjs",
    "tools/api-codegen/generate-api.test.mjs",
    "docs/MOBILE_API_CLIENT.md",
    "docs/MOBILE_DEV_AUTH.md",
    "docs/MOBILE_RESOURCE_INTEGRATION.md",
    "docs/PHASE_8B_ACCEPTANCE.md",
)
RESOURCE_GATE_FILES = (
    "apps/server/app/services/resources.py",
    "apps/server/app/db/repositories/resources.py",
    "apps/server/app/schemas/resources.py",
    "apps/server/tests/test_resource_api.py",
    "apps/server/tests/test_resource_contract.py",
    "apps/server/resource_api_demo.py",
    "scripts/export_openapi.py",
    "docs/contracts/openapi.json",
    "docs/contracts/phase7d-openapi-baseline.json",
    "docs/RESOURCE_API.md",
    "docs/PHASE_8A_ACCEPTANCE.md",
)
NATIVE_CLOSEOUT_SCENES = {
    "sse_normal",
    "sse_failed",
    "sse_disconnect",
    "sse_cancel",
    "sse_back_logout",
    "resource_create",
    "rest_replay",
    "owner_isolation",
    "relationship_isolation",
    "memory_challenge",
    "memory_replay",
    "memory_restart",
    "memory_smoke_preserve",
    "memory_smoke_revoke",
    "import_history_lifecycle",
    "token_expiry",
}


def native_closeout_check() -> None:
    """A report alone cannot satisfy the completed Phase 8 marker."""
    matrix = json.loads((ROOT / "docs/PHASE_8F_CLOSEOUT_MATRIX.json").read_text("utf-8"))

    def artifact(descriptor: dict) -> Path:
        path = (ROOT / descriptor["path"]).resolve()
        if not path.is_relative_to(ROOT.resolve()) or not path.is_file():
            raise RuntimeError("Phase 8 native artifact is missing or outside the repository")
        if hashlib.sha256(path.read_bytes()).hexdigest() != descriptor["sha256"]:
            raise RuntimeError("Phase 8 native artifact hash mismatch")
        return path

    if matrix.get("status") != "PASS" or matrix.get("open_p0_p1") != []:
        raise RuntimeError("Phase 8 requires completed native acceptance without open P0/P1")
    tests = matrix["tests"]
    if (
        len(tests) != len(NATIVE_CLOSEOUT_SCENES)
        or {test["scene"] for test in tests} != NATIVE_CLOSEOUT_SCENES
    ):
        raise RuntimeError("Phase 8 native acceptance scene coverage is incomplete")
    for test in tests:
        if test["status"] != "PASS" or test["exit_code"] != 0:
            raise RuntimeError("Phase 8 native scene did not pass independently")
        for field in ("id", "preconditions", "steps", "expected", "actual", "server_evidence"):
            if not test.get(field):
                raise RuntimeError(f"Phase 8 native scene lacks {field}")
        artifacts = test["artifacts"]
        paths = {name: artifact(artifacts[name]) for name in ("log", "exit", "report", "steps")}
        if paths["exit"].read_text("utf-8").strip() != "0":
            raise RuntimeError("Phase 8 native execution exit evidence is not zero")
        report = json.loads(paths["report"].read_text("utf-8"))
        steps = json.loads(paths["steps"].read_text("utf-8"))
        completed = [
            row["command"] if row.get("status") == "done" else "state"
            for row in report
            if row.get("status") == "done" or "ui_state" in row
        ]
        expected = [step.partition(" ")[0] for step in steps if step != "stop"]
        if report[0]["execution"]["steps"] != steps or completed != expected:
            raise RuntimeError("Phase 8 native report is not one complete independent execution")
        if any(row.get("status") in {"FAIL", "failed"} for row in report):
            raise RuntimeError("Phase 8 native report contains a failure")
    pre_marker = matrix["pre_marker"]
    artifact(pre_marker["log"])
    if (
        pre_marker["exit_code"] != 0
        or artifact(pre_marker["exit"]).read_text("utf-8").strip() != "0"
    ):
        raise RuntimeError("Phase 8 requires an independently successful pre-marker root verify")


def phase_marker_check() -> None:
    if PHASE > 8 or (PHASE == 8 and SUBPHASE not in {"8F", "9A"}):
        raise RuntimeError("Phase 8 requires 8F closeout; only Phase 9A subphase is implemented")
    if SUBPHASE == "9A":
        if PHASE != 8 or not UPLOAD_SECURITY:
            raise RuntimeError("Phase 9A requires completed Phase 8 and security gates")
        from check_security_9a import check

        check(completed=True)
    if PHASE == 8:
        if not all(
            (
                MOBILE_FOUNDATION,
                MOBILE_FEATURE_UI,
                MOBILE_CONTROLS_UI,
                MOBILE_FINAL_UI,
                PUBLIC_RESOURCES_API,
                MOBILE_CONNECTED,
                MOBILE_AGENT_CHAT,
                MOBILE_IMPORT,
                MOBILE_MEMORY,
            )
        ):
            raise RuntimeError("Phase 8 requires all Mobile and integration gates")
        for name in (
            *RESOURCE_GATE_FILES,
            *CONNECTED_GATE_FILES,
            *AGENT_CHAT_GATE_FILES,
            *IMPORT_GATE_FILES,
            *MEMORY_GATE_FILES,
        ):
            if not (ROOT / name).is_file():
                raise RuntimeError(f"Missing Phase 8 gate: {name}")
        native_closeout_check()
    if PHASE == 7:
        if SUBPHASE not in {"7D", "8A", "8B", "8C", "8D", "8E"} or not all(
            (MOBILE_FOUNDATION, MOBILE_FEATURE_UI, MOBILE_CONTROLS_UI, MOBILE_FINAL_UI)
        ):
            raise RuntimeError("Phase 7 marker requires all Mobile subphase gates and 7D")
        for name in ("PHASE_7_FINAL_ACCEPTANCE.md", "PHASE_8_MOBILE_INTEGRATION_HANDOFF.md"):
            if not (ROOT / "docs" / name).is_file():
                raise RuntimeError(f"Missing Phase 7 final document: {name}")
    if SUBPHASE in {"8A", "8B", "8C", "8D", "8E"}:
        if PHASE != 7 or not PUBLIC_RESOURCES_API:
            raise RuntimeError("Phase 8A requires complete Phase 7 and resource gates")
        for name in RESOURCE_GATE_FILES:
            if not (ROOT / name).is_file():
                raise RuntimeError(f"Missing Phase 8A gate: {name}")
    if SUBPHASE in {"8B", "8C", "8D", "8E"}:
        if PHASE != 7 or not MOBILE_CONNECTED:
            raise RuntimeError("Phase 8B requires complete Phase 7 and connected Mobile gates")
        for name in CONNECTED_GATE_FILES:
            if not (ROOT / name).is_file():
                raise RuntimeError(f"Missing Phase 8B gate: {name}")
    if SUBPHASE in {"8C", "8D", "8E"}:
        if PHASE != 7 or not MOBILE_AGENT_CHAT:
            raise RuntimeError("Phase 8C requires complete Phase 7 and Agent Chat gates")
        for name in AGENT_CHAT_GATE_FILES:
            if not (ROOT / name).is_file():
                raise RuntimeError(f"Missing Phase 8C gate: {name}")
    if SUBPHASE in {"8D", "8E"}:
        if PHASE != 7 or not MOBILE_IMPORT:
            raise RuntimeError("Phase 8D requires complete Phase 7 and Import/History gates")
        for name in IMPORT_GATE_FILES:
            if not (ROOT / name).is_file():
                raise RuntimeError(f"Missing Phase 8D gate: {name}")
    if SUBPHASE == "8E":
        if PHASE != 7 or not MOBILE_MEMORY:
            raise RuntimeError("Phase 8E requires complete Phase 7 and Memory gates")
        for name in MEMORY_GATE_FILES:
            if not (ROOT / name).is_file():
                raise RuntimeError(f"Missing Phase 8E gate: {name}")


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
            # Inspect installed tools without pnpm's project-version auto-download.
            [location, "--version"],
            cwd=ROOT.parent,
            capture_output=True,
            text=True,
            check=True,
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
    if UPLOAD_SECURITY:
        uv_run("python", "scripts/check_security_9a.py")
        uv_run("python", "scripts/audit_phase8_evidence.py")
        uv_run("pytest", "-q", "apps/server/tests/test_upload_security.py")
    if MEMORY_CONTROL_API:
        uv_run("pytest", "-q", "apps/server/tests/test_memory_control.py")
        uv_run("python", "apps/server/memory_control_demo.py")
        uv_run("python", "apps/server/memory_control_http_demo.py")
    if MEMORY_MUTATION_API:
        uv_run("pytest", "-q", "apps/server/tests/test_memory_mutation.py")
        uv_run("python", "apps/server/memory_destructive_control_demo.py")
        uv_run("python", "apps/server/memory_destructive_http_demo.py")
    if MEMORY_RETENTION:
        uv_run("pytest", "-q", "apps/server/tests/test_memory_retention.py")
        uv_run("python", "apps/server/memory_retention_demo.py")
    if MEMORY_PHASE6_E2E:
        uv_run("pytest", "-q", "apps/server/tests/test_phase6_e2e.py")
        uv_run("python", "apps/server/memory_phase6_e2e_demo.py")
    if PUBLIC_RESOURCES_API:
        uv_run("python", "scripts/export_openapi.py", "--check")
        uv_run(
            "pytest",
            "-q",
            "apps/server/tests/test_resource_contract.py",
            "apps/server/tests/test_resource_api.py",
        )
        uv_run("python", "apps/server/resource_api_demo.py")
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
        "scripts/check_mobile.py",
        "scripts/export_openapi.py",
        "scripts/phase8_android_demo.py",
        "scripts/phase8_native_closeout.py",
        "scripts/check_security_9a.py",
        "scripts/audit_phase8_evidence.py",
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
        "scripts/check_mobile.py",
        "scripts/export_openapi.py",
        "scripts/phase8_android_demo.py",
        "scripts/phase8_native_closeout.py",
        "scripts/check_security_9a.py",
        "scripts/audit_phase8_evidence.py",
    )


def evals() -> None:
    if PHASE < 1:
        print("DEFERRED: golden evaluation gate begins at Phase 1")
        return
    run([sys.executable, "evals/validate.py"])


def repository_checks() -> None:
    safe_directory = f"safe.directory={ROOT.as_posix()}"
    run(["git", "-c", safe_directory, "diff", "--check"])
    run(["git", "-c", safe_directory, "diff", "--cached", "--check"])
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
        for path in list((mobile / "app").rglob("*")) + list((mobile / "src").rglob("*")):
            if path.is_file() and path.suffix in {".ts", ".tsx", ".js", ".json"}:
                content = path.read_text(encoding="utf-8")
                if "EXPO_PUBLIC_OPENAI" in content or "EXPO_PUBLIC_DEEPSEEK" in content:
                    raise RuntimeError(f"Model key prefix in mobile: {path}")
    print("Repository secret boundary check passed")


def verify() -> None:
    phase_marker_check()
    doctor()
    tests()
    evals()
    repository_checks()
    lint()
    if MOBILE_FOUNDATION:
        run([sys.executable, "scripts/check_mobile.py"])
    if MOBILE_FINAL_UI:
        pnpm = shutil.which("pnpm")
        if not pnpm:
            raise RuntimeError("pnpm is required for the Phase 7 runtime gate")
        for name in ("export:web", "smoke:web"):
            run([pnpm, "--filter", "@goutou/mobile", "run", name])
        print("PASS: Phase 7D real Expo Web export and six-surface browser regression")
    if MOBILE_CONNECTED:
        pnpm = shutil.which("pnpm")
        if not pnpm:
            raise RuntimeError("pnpm is required for connected Mobile integration")
        run([pnpm, "--filter", "@goutou/mobile", "run", "smoke:connected"])
        print("PASS: Phase 8B generated client / CLI JWT / real HTTP / PostgreSQL / Expo Web")
        print("ANDROID CONNECTED: separate native evidence; Web is not Android verification")
    if MOBILE_AGENT_CHAT:
        pnpm = shutil.which("pnpm")
        if not pnpm:
            raise RuntimeError("pnpm is required for Agent Chat integration")
        run([pnpm, "--filter", "@goutou/mobile", "run", "smoke:agent"])
        print("PASS: Phase 8C CLI JWT / Agent REST / POST SSE / PostgreSQL / Expo Web")
        print("ANDROID CONNECTED SSE: separate native evidence; never inferred from Web")
    if MOBILE_IMPORT:
        pnpm = shutil.which("pnpm")
        if not pnpm:
            raise RuntimeError("pnpm is required for Import/History integration")
        run([pnpm, "--filter", "@goutou/mobile", "run", "smoke:imports"])
        print("PASS: Phase 8D signed JWT / multipart / ImportJob / PostgreSQL / History / Expo Web")
        print("ANDROID NATIVE IMPORT: separate evidence; never inferred from Web")
    if MOBILE_MEMORY:
        pnpm = shutil.which("pnpm")
        if not pnpm:
            raise RuntimeError("pnpm is required for Memory integration")
        run([pnpm, "--filter", "@goutou/mobile", "run", "smoke:memory"])
        print(
            "PASS: Phase 8E signed JWT / Memory controls / guarded mutations / "
            "PostgreSQL / Expo Web"
        )
        print("ANDROID NATIVE MEMORY: separate evidence; never inferred from Web")
    if (ROOT / "apps/mobile/playwright.final.config.ts").is_file():
        pnpm = shutil.which("pnpm")
        if not pnpm:
            raise RuntimeError("pnpm is required for Phase 8F cross-surface integration")
        run([pnpm, "--filter", "@goutou/mobile", "run", "smoke:final"])
        print("PASS: Phase 8F real Connected six-surface Web integration")
        print("PHASE 8 FINAL: Android acceptance remains a separate required gate")
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
        print("PASS: Deterministic knowledge router, frozen loader and Golden fixture evaluation")
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
        if MEMORY_MUTATION_API:
            print("PASS: Phase 6B guarded undo, confirmed deletion and durable receipts")
        else:
            print("DEFERRED TO 6B: Undo/Delete Public Controls")
        if MEMORY_RETENTION:
            print("PASS: Phase 6C retention expiry, bounded maintenance and durable receipt safety")
            print("AUTOMATIC SCHEDULING: NOT DEPLOYED")
        else:
            print("DEFERRED TO 6C: Retention Policy")
        if MEMORY_PHASE6_E2E:
            print("PASS: Phase 6D signed HTTP Agent/Memory end-to-end integration")
        else:
            print("DEFERRED TO 6D: Phase 6 Final Acceptance")
        if not MOBILE_FOUNDATION:
            print("DEFERRED TO PHASE 7: Mobile")
    if AGENT_STREAMING:
        print("PASS: Typed runtime streaming and eight standalone Phase 3 E2E cases")
    if PUBLIC_RESOURCES_API:
        print(
            "PASS: Phase 8A public resources, signed JWT/ownership, retries/history and HTTP demo"
        )
        print("PASS: Deterministic OpenAPI generation input and Phase 7D compatibility")
    if not MOBILE_FOUNDATION:
        print("DEFERRED: Mobile lint/typecheck begin at Phase 7")
    if PHASE in {5, 6, 7, 8}:
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
        if MEMORY_MUTATION_API:
            print("PASS: Phase 6B Memory Undo, Deletion and Confirmation Boundary")
        print("DEFERRED: Chat Analysis")
        if MOBILE_FOUNDATION:
            print("PASS: Phase 7A Mobile static gates")
            print("SEPARATE GATE: Expo Web / Android runtime smoke")
            if MOBILE_FEATURE_UI:
                print("PASS: Phase 7B Chat/Relationship focused static gate")
            if MOBILE_CONTROLS_UI:
                print("PASS: Phase 7C Import/History/Settings focused static gate")
            if MOBILE_FINAL_UI:
                print("PASS: Phase 7D focused integration and real browser gates")
            else:
                print("DEFERRED: Phase 7D final acceptance")
            if MOBILE_MEMORY:
                print(
                    "PASS: Phase 8F independently recorded Android native acceptance"
                    if PHASE == 8
                    else "DEFERRED: Phase 8F whole Phase 8 final/native fault evidence"
                )
            elif MOBILE_IMPORT:
                print("DEFERRED: Phase 8E Memory; whole Phase 8 final/native fault evidence")
            elif MOBILE_AGENT_CHAT:
                print("DEFERRED: Phase 8D Import/History, Phase 8E Memory; native final evidence")
            else:
                print("DEFERRED: Phase 8C Agent REST/SSE, Phase 8D Import/History, Phase 8E Memory")
        else:
            print("DEFERRED: Mobile")
        print("DEFERRED: RAG")
        if PHASE in {6, 7, 8}:
            if not all(
                (MEMORY_CONTROL_API, MEMORY_MUTATION_API, MEMORY_RETENTION, MEMORY_PHASE6_E2E)
            ):
                raise RuntimeError("Phase 6 memory acceptance gate is incomplete")
            print("PASS: Phase 6 Memory Controls and Retention")
            print("PRODUCTION SCHEDULER / BACKUP / RESTORE REPLAY: NOT DEPLOYED")
            suffix = " and 7A static gates" if MOBILE_FOUNDATION else ""
            if MOBILE_FEATURE_UI:
                suffix += " and 7B focused gate"
            if MOBILE_CONTROLS_UI:
                suffix += " and 7C focused gate"
            if MOBILE_FINAL_UI:
                suffix += " and 7D integration/runtime gates"
            if PHASE == 8:
                print("PASS: Phase 7 Expo React Native MVP")
                print("PASS: all active Phase 0..8 gates")
                if UPLOAD_SECURITY:
                    print("PASS: Phase 9A security focused/regression gates")
                    print("Phase 9 IN PROGRESS; remaining security/privacy/reliability deferred")
                else:
                    print("Phase 9 PENDING / NOT STARTED")
            elif PHASE == 7:
                print("PASS: Phase 7 Expo React Native MVP")
                suffix = (
                    " and Phase 8A/8B/8C/8D/8E"
                    if MOBILE_MEMORY
                    else " and Phase 8A/8B/8C/8D"
                    if MOBILE_IMPORT
                    else " and Phase 8A/8B/8C"
                    if MOBILE_AGENT_CHAT
                    else " and Phase 8A/8B"
                    if MOBILE_CONNECTED
                    else " and Phase 8A"
                    if PUBLIC_RESOURCES_API
                    else ""
                )
                print(
                    f"PASS: all active Phase 0..7{suffix}; Phase 8 IN PROGRESS / NOT YET COMPLETE"
                )
            else:
                print(f"PASS: all active Phase 0..6{suffix}")
            return
        active = "Phase 0..5"
        if MEMORY_CONTROL_API:
            active += " and 6A"
        if MEMORY_MUTATION_API:
            active += " and 6B"
        if MEMORY_RETENTION:
            active += " and 6C"
        if MEMORY_PHASE6_E2E:
            active += " and 6D"
        print(f"PASS: all active {active} gates")
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
