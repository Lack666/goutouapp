"""Run Alembic's migration cycle and schema check on a disposable DB."""

import os
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {
    "users",
    "persons",
    "relationships",
    "conversations",
    "messages",
    "agent_runs",
    "memory_controls",
    "memory_records",
    "memory_operations",
    "memory_confirmations",
    "memory_mutations",
    "chat_import_jobs",
    "chat_import_artifacts",
    "chat_import_speakers",
    "relationship_messages",
    "resource_admission_states",
    "upload_reservations",
}


def main() -> None:
    raw = os.getenv("TEST_DATABASE_URL")
    if not raw:
        raise RuntimeError("TEST_DATABASE_URL is required for the database gate")
    url = make_url(raw)
    if url.drivername != "postgresql+psycopg" or not (url.database or "").endswith("_test"):
        raise RuntimeError("TEST_DATABASE_URL must target a separate psycopg _test namespace")
    dev = os.getenv("DATABASE_URL")
    if dev and make_url(dev).database == url.database:
        raise RuntimeError("TEST_DATABASE_URL must differ from DATABASE_URL")

    name = f"{url.database}_{uuid4().hex[:12]}"
    isolated = url.set(database=name)
    admin = create_engine(
        url.set(database="postgres"), isolation_level="AUTOCOMMIT", hide_parameters=True
    )
    try:
        with admin.connect() as connection:
            connection.execute(text(f'CREATE DATABASE "{name}"'))
        env = os.environ.copy()
        env["DATABASE_URL"] = isolated.render_as_string(hide_password=False)
        for action, target, expected in (
            ("upgrade", "head", EXPECTED),
            ("downgrade", "base", set()),
            ("upgrade", "head", EXPECTED),
        ):
            print(f"+ alembic {action} {target}", flush=True)
            subprocess.run(["alembic", action, target], cwd=ROOT, env=env, check=True)
            engine = create_engine(isolated, hide_parameters=True)
            try:
                tables = set(inspect(engine).get_table_names()) - {"alembic_version"}
                if tables != expected:
                    raise RuntimeError(
                        f"Unexpected tables after alembic {action} {target}: {tables}"
                    )
            finally:
                engine.dispose()
        print("+ alembic check", flush=True)
        subprocess.run(["alembic", "check"], cwd=ROOT, env=env, check=True)
        print("PASS: isolated Alembic upgrade head / downgrade base / upgrade head / check")
    finally:
        with admin.connect() as connection:
            connection.execute(
                text(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                    "WHERE datname = :database AND pid <> pg_backend_pid()"
                ),
                {"database": name},
            )
            connection.execute(text(f'DROP DATABASE IF EXISTS "{name}"'))
        admin.dispose()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        print("FAIL: database migration acceptance", file=sys.stderr)
        raise SystemExit(1) from None
