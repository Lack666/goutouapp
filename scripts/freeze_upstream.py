"""Explicitly regenerate the upstream inventory after reviewing a new checkout."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "upstream" / "goutoujunshi"
MANIFEST = ROOT / "upstream" / "manifest.json"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--commit", required=True, help="Full reviewed upstream commit")
    args = parser.parse_args()
    if len(args.commit) != 40 or any(c not in "0123456789abcdef" for c in args.commit):
        parser.error("--commit must be a 40-character lowercase SHA-1")
    files = {
        p.relative_to(SNAPSHOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(SNAPSHOT.rglob("*"))
        if p.is_file() and "__pycache__" not in p.parts
    }
    payload = {
        "source_url": "https://github.com/shengjidaguai-china/goutoujunshi",
        "commit": args.commit,
        "license": "MIT",
        "files": files,
    }
    MANIFEST.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Frozen {len(files)} upstream files at {args.commit}")


if __name__ == "__main__":
    main()
