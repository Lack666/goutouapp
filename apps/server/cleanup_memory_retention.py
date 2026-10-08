"""Privileged maintenance CLI. Output contains counts and generic errors only."""

import argparse
import json

from app.core.config import Settings
from app.db.session import Database
from app.retention import RetentionPolicy
from app.services.memory_retention import MemoryRetentionService


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--execute", action="store_true")
    parser.add_argument("--batch-size", type=int)
    parser.add_argument("--max-batches", type=int, default=1)
    args = parser.parse_args()
    database = None
    try:
        settings = Settings()
        policy = RetentionPolicy.from_settings(settings)
        database = Database(settings)
        result = MemoryRetentionService(database.session, policy=policy).run(
            dry_run=not args.execute, batch_size=args.batch_size, max_batches=args.max_batches
        )
        print(result.model_dump_json())
        return 0 if result.status == "ok" else 1
    except Exception:
        print(json.dumps({"status": "failed", "error": "retention_cleanup_failed"}))
        return 1
    finally:
        if database is not None:
            database.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
