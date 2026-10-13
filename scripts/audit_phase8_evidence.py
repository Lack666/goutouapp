"""Read-only privacy screening; print counts/hashes, never matched secret values."""

from __future__ import annotations

import base64
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JWT = re.compile(r"[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{20,}")
PATTERNS = {
    "database_password": re.compile(r"postgres(?:ql)?(?:\+psycopg)?://[^\s:@]+:[^\s@]+@"),
    "provider_key": re.compile(r"\bsk-[A-Za-z0-9_-]{20,}"),
    "authorization_value": re.compile(r"Bearer\s+[A-Za-z0-9_.-]{20,}"),
}


def categories(content: str) -> list[str]:
    found = [name for name, pattern in PATTERNS.items() if pattern.search(content)]
    for match in JWT.finditer(content):
        try:
            header = json.loads(base64.urlsafe_b64decode(match.group().split(".")[0] + "==="))
            if isinstance(header, dict) and "alg" in header:
                found.append("jwt")
                break
        except (ValueError, UnicodeError):
            continue
    return sorted(set(found))


def audit(root: Path = ROOT) -> dict:
    paths = sorted((root / "docs/evidence/phase8f-closeout").iterdir())
    paths.append(root / "docs/PHASE_8F_CLOSEOUT_MATRIX.json")
    inventory = {}
    findings = []
    for path in paths:
        if not path.is_file():
            continue
        data = path.read_bytes()
        name = path.relative_to(root).as_posix()
        inventory[name] = hashlib.sha256(data).hexdigest()
        hits = categories(data.decode("utf-8", errors="replace"))
        if hits:
            findings.append({"path": name, "categories": hits})
    digest = hashlib.sha256(json.dumps(inventory, sort_keys=True).encode()).hexdigest()
    return {"files": len(inventory), "inventory_sha256": digest, "findings": findings}


if __name__ == "__main__":
    result = audit()
    print(json.dumps(result, indent=2))
    raise SystemExit(1 if result["findings"] else 0)
