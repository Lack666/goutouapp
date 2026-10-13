"""Read-only credential screen; preserve all historical acceptance bytes."""

import hashlib
import json
from collections import Counter
from pathlib import Path

from audit_phase8_evidence import categories

ROOT = Path(__file__).resolve().parents[1]


def audit(root=ROOT):
    groups = {}
    findings = []
    inventory = {}
    types = Counter()
    for group in ("phase8f-closeout", "phase9a", "phase9b", "phase9c", "phase9d", "phase9e"):
        paths = sorted((root / "docs/evidence" / group).glob("*"))
        matrix = (
            root
            / "docs"
            / {
                "phase8f-closeout": "PHASE_8F_CLOSEOUT_MATRIX.json",
                "phase9a": "PHASE_9A_MATRIX.json",
                "phase9b": "PHASE_9B_MATRIX.json",
                "phase9c": "PHASE_9C_MATRIX.json",
                "phase9d": "PHASE_9D_MATRIX.json",
                "phase9e": "PHASE_9E_MATRIX.json",
            }[group]
        )
        if matrix.is_file():
            paths.append(matrix)
        groups[group] = 0
        for path in paths:
            if not path.is_file():
                continue
            data = path.read_bytes()
            name = path.relative_to(root).as_posix()
            inventory[name] = hashlib.sha256(data).hexdigest()
            groups[group] += 1
            types[path.suffix] += 1
            if path.suffix not in {".json", ".log", ".exit"}:
                findings.append({"path": name, "categories": ["unreviewed_file_type"]})
                continue
            hits = categories(data.decode("utf-8", errors="replace"))
            if hits:
                findings.append({"path": name, "categories": hits})
    return {
        "groups": groups,
        "file_types": dict(types),
        "files": len(inventory),
        "findings": findings,
        "inventory_sha256": hashlib.sha256(
            json.dumps(inventory, sort_keys=True).encode()
        ).hexdigest(),
        "limit": (
            "Pattern screening only; provenance and manual sampling are separate documented work"
        ),
    }


if __name__ == "__main__":
    result = audit()
    print(json.dumps(result, indent=2))
    raise SystemExit(1 if result["findings"] else 0)
