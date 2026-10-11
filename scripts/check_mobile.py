"""Mobile static, Phase 7 regression and Phase 8B–8F connected gates."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MOBILE = ROOT / "apps/mobile"


def boundary_check() -> None:
    forbidden = re.compile(
        r"EXPO_PUBLIC_\w*(?:KEY|SECRET|TOKEN)|DATABASE_URL|JWT_SECRET|"
        r"(?:sk-|sk-ant-)[A-Za-z0-9_-]{16,}|postgres(?:ql)?://|"
        r"api\.(?:openai|deepseek|anthropic)\.com|"
        r"\b(?:fetch|XMLHttpRequest|WebSocket|EventSource)\s*\(|"
        r"from\s+['\"](?:openai|anthropic|pg|postgres|axios)['\"]"
        r"|\b(?:localStorage|sessionStorage|AsyncStorage)\b|console\.\w+\s*\("
    )
    for directory in (MOBILE / "app", MOBILE / "src"):
        for path in directory.rglob("*"):
            if path.is_file() and path.suffix in {".ts", ".tsx", ".js", ".json"}:
                content = path.read_text(encoding="utf-8")
                if forbidden.search(content):
                    raise RuntimeError(f"Mobile secret/network boundary violation: {path}")
                if (
                    "SecureStore" in content
                    and path != MOBILE / "src/session/tokenStorage.native.ts"
                ):
                    raise RuntimeError(f"Credential storage outside platform adapter: {path}")
                if directory.name == "src" and {"features", "components"} & set(path.parts):
                    if re.search(
                        r"from\s+['\"].*(?:demoSource|featureFixtures|controlFixtures)['\"]",
                        content,
                    ):
                        raise RuntimeError(f"Screen coupled to fixtures: {path}")
    for name in ("index", "chat", "relationship", "import", "history", "settings"):
        if not (MOBILE / "app" / f"{name}.tsx").is_file():
            raise RuntimeError(f"Missing Mobile route: {name}")
    config = json.loads((MOBILE / "tsconfig.json").read_text(encoding="utf-8"))
    if config["compilerOptions"].get("strict") is not True:
        raise RuntimeError("Mobile TypeScript must remain strict")
    if not (ROOT / "pnpm-lock.yaml").is_file():
        raise RuntimeError("Missing workspace lockfile")
    if any((ROOT / name).exists() for name in ("package-lock.json", "yarn.lock")):
        raise RuntimeError("Mixed package-manager lockfiles")
    print("PASS: Mobile six routes, strict contracts, fixture and secret/network boundaries")


def main() -> None:
    pnpm = shutil.which("pnpm")
    if not pnpm:
        raise RuntimeError("pnpm is required")
    expected = json.loads((ROOT / "package.json").read_text())["packageManager"].split("@")[1]
    actual = subprocess.check_output([pnpm, "--version"], cwd=ROOT, text=True).strip()
    if actual != expected:
        raise RuntimeError(f"Project pnpm mismatch: expected {expected}, got {actual}")
    print(f"PASS: project pnpm {actual}", flush=True)
    boundary_check()
    # --frozen-lockfile detects drift; offline prevents a static gate from downloading.
    commands = [[pnpm, "install", "--frozen-lockfile", "--offline"]]
    commands.extend(
        [pnpm, "--filter", "@goutou/mobile", "run", name]
        for name in ("compatibility", "typecheck", "lint", "format:check", "test")
    )
    if (MOBILE / "src/api/generated/client.ts").is_file():
        commands.append([pnpm, "run", "api:check"])
        commands.append([pnpm, "--filter", "@goutou/mobile", "exec", "expo-doctor"])
        commands.append([pnpm, "--filter", "@goutou/mobile", "run", "test:connected"])
    if (MOBILE / "src/data/agentChatController.ts").is_file():
        for name in ("test:sse", "test:agent-chat"):
            commands.append([pnpm, "--filter", "@goutou/mobile", "run", name])
    if (MOBILE / "src/data/importController.ts").is_file():
        commands.append([pnpm, "--filter", "@goutou/mobile", "run", "test:imports"])
    if (MOBILE / "src/data/memoryController.ts").is_file():
        commands.append([pnpm, "--filter", "@goutou/mobile", "run", "test:memory"])
    if (MOBILE / "tests/fullMobileIntegration.test.ts").is_file():
        commands.append([pnpm, "--filter", "@goutou/mobile", "run", "test:final"])
    feature_ui = (MOBILE / "src/features/ChatScreen.tsx").is_file()
    if feature_ui:
        commands.append([pnpm, "--filter", "@goutou/mobile", "run", "test:features"])
    controls_ui = (MOBILE / "src/features/ImportScreen.tsx").is_file()
    if controls_ui:
        for name in ("ImportScreen", "HistoryScreen", "SettingsScreen"):
            if not (MOBILE / "src/features" / f"{name}.tsx").is_file():
                raise RuntimeError(f"Missing Phase 7C screen: {name}")
        for name in ("import", "history", "settings", "controls"):
            if not (MOBILE / "tests" / f"{name}.test.tsx").is_file():
                raise RuntimeError(f"Missing Phase 7C test suite: {name}")
        commands.append([pnpm, "--filter", "@goutou/mobile", "run", "test:controls"])
    integration_ui = (MOBILE / "tests/integration.test.tsx").is_file()
    if integration_ui:
        if not (MOBILE / "smoke/integration.spec.ts").is_file():
            raise RuntimeError("Missing Phase 7D six-surface browser journey")
        commands.append([pnpm, "--filter", "@goutou/mobile", "run", "test:integration"])
    for command in commands:
        print("+", " ".join(command), flush=True)
        env = None
        if command[-1] == "expo-doctor":
            preload = ROOT / "scripts/expo_doctor_fetch.cjs"
            options = os.environ.get("NODE_OPTIONS", "")
            node_options = f'{options} --require "{preload.as_posix()}"'.strip()
            env = {**os.environ, "NODE_OPTIONS": node_options}
        subprocess.run(command, cwd=ROOT, env=env, check=True)
    peers = subprocess.run(
        [pnpm, "peers", "check"], cwd=ROOT, capture_output=True, text=True, check=True
    )
    print(peers.stdout, flush=True)
    if "No peer dependency issues found" not in peers.stdout:
        raise RuntimeError("Mobile dependency peer audit failed")
    print("PASS: Phase 7A Mobile static gates; runtime smoke is a separate command")
    if feature_ui:
        print("PASS: Phase 7B Chat/Relationship focused gate; runtime smoke is separate")
    if controls_ui:
        print("PASS: Phase 7C Import/History/Settings focused gate; runtime smoke is separate")
    if integration_ui:
        print("PASS: Phase 7D integration/recovery focused gate; runtime smoke is separate")


if __name__ == "__main__":
    main()
