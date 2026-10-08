"""Mobile static and Phase 7B focused gates; runtime smoke stays separate."""

from __future__ import annotations

import json
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
        r"|\b(?:localStorage|sessionStorage|AsyncStorage|SecureStore)\b|console\.\w+\s*\("
    )
    for directory in (MOBILE / "app", MOBILE / "src"):
        for path in directory.rglob("*"):
            if path.is_file() and path.suffix in {".ts", ".tsx", ".js", ".json"}:
                content = path.read_text(encoding="utf-8")
                if forbidden.search(content):
                    raise RuntimeError(f"Mobile secret/network boundary violation: {path}")
                if directory.name == "src" and {"features", "components"} & set(path.parts):
                    if re.search(r"from\s+['\"].*(?:demoSource|featureFixtures)['\"]", content):
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
    feature_ui = (MOBILE / "src/features/ChatScreen.tsx").is_file()
    if feature_ui:
        commands.append([pnpm, "--filter", "@goutou/mobile", "run", "test:features"])
    for command in commands:
        print("+", " ".join(command), flush=True)
        subprocess.run(command, cwd=ROOT, check=True)
    peers = subprocess.run(
        [pnpm, "peers", "check"], cwd=ROOT, capture_output=True, text=True, check=True
    )
    print(peers.stdout, flush=True)
    if "No peer dependency issues found" not in peers.stdout:
        raise RuntimeError("Mobile dependency peer audit failed")
    print("PASS: Phase 7A Mobile static gates; runtime smoke is a separate command")
    if feature_ui:
        print("PASS: Phase 7B Chat/Relationship focused gate; runtime smoke is separate")


if __name__ == "__main__":
    main()
