"""Explicit single-server cleanup for expired and crash-orphan import sources."""

import json

from app.chat_import.artifacts import LocalFilesystemImportArtifactStore
from app.core.config import get_settings
from app.db.session import Database
from app.services.import_workflow import ImportWorkflowService


def main() -> None:
    settings = get_settings()
    database = Database(settings)
    try:
        service = ImportWorkflowService(
            database.session,
            LocalFilesystemImportArtifactStore(settings.chat_import_artifact_root),
            settings.chat_import_retention_hours,
        )
        removed, orphans = service.cleanup_expired()
        print(json.dumps({"expired_or_terminal_removed": removed, "orphan_removed": orphans}))
    finally:
        database.dispose()


if __name__ == "__main__":
    main()
