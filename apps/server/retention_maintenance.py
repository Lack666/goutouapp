"""Opt-in scheduled maintenance. Never installed automatically or exposed via HTTP."""

import argparse
from threading import Event

from app.chat_import.artifacts import LocalFilesystemImportArtifactStore
from app.core.config import Settings
from app.core.logging import configure_logging
from app.db.session import Database
from app.services.import_workflow import ImportWorkflowService
from app.services.maintenance import MaintenanceLoop, MaintenanceService
from app.services.resource_admission import ResourceAdmission


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--interval-seconds", type=float, default=60)
    parser.add_argument("--iterations", type=int)
    args = parser.parse_args()
    database = None
    try:
        configure_logging()
        settings = Settings()
        database = Database(settings)
        workflow = ImportWorkflowService(
            database.session,
            LocalFilesystemImportArtifactStore(settings.chat_import_artifact_root),
            settings.chat_import_retention_hours,
        )
        loop = MaintenanceLoop(
            MaintenanceService(ResourceAdmission(database, settings), workflow),
            interval_seconds=args.interval_seconds,
        )
        loop.run(Event(), iterations=args.iterations, report=lambda r: print(r.model_dump_json()))
        return 1 if loop.failures else 0
    except KeyboardInterrupt:
        return 0
    except Exception:
        print('{"status":"failed","error":"maintenance_unavailable"}')
        return 1
    finally:
        if database is not None:
            database.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
