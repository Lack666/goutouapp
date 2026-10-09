"""FastAPI transport assembly with lazy, shutdown-owned database resources."""

from contextlib import asynccontextmanager
from threading import RLock

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.errors import register_error_handlers
from app.api.health import router as health_router
from app.api.import_upload_limit import ImportUploadBodyLimit
from app.api.readiness import router as readiness_router
from app.api.v1.router import router as v1_router
from app.chat_import.artifacts import LocalFilesystemImportArtifactStore
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging
from app.db.session import Database
from app.schemas.error import ErrorResponse
from app.services.import_workflow import ImportWorkflowService

ERROR_RESPONSES = {
    400: {"model": ErrorResponse, "description": "Invalid request"},
    401: {"model": ErrorResponse, "description": "Authentication required"},
    404: {"model": ErrorResponse, "description": "Resource not found"},
    409: {"model": ErrorResponse, "description": "Active run or idempotency conflict"},
    422: {"model": ErrorResponse, "description": "Validation error"},
    502: {"model": ErrorResponse, "description": "Agent execution failed"},
    503: {"model": ErrorResponse, "description": "Dependency unavailable"},
    500: {"model": ErrorResponse, "description": "Internal server error"},
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        yield
    finally:
        app.state.database.dispose()


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(debug=settings.app_debug)
    # APP_DEBUG controls local logging and reload, not traceback responses.
    app = FastAPI(
        title="Goutoujunshi Server",
        version="0.1.0",
        debug=False,
        responses=ERROR_RESPONSES,
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.database = Database(settings)
    app.state.import_artifact_store = LocalFilesystemImportArtifactStore(
        settings.chat_import_artifact_root
    )
    app.state.import_workflow = ImportWorkflowService(
        app.state.database.session,
        app.state.import_artifact_store,
        settings.chat_import_retention_hours,
    )
    app.state.agent_service = None
    app.state.agent_service_lock = RLock()
    register_error_handlers(app)
    app.add_middleware(ImportUploadBodyLimit, max_file_bytes=settings.max_chat_import_bytes)
    if settings.dev_cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.dev_cors_origins,
            allow_credentials=False,
            allow_methods=["GET", "POST"],
            allow_headers=["Authorization", "Content-Type"],
        )
    app.include_router(health_router)
    app.include_router(readiness_router)
    app.include_router(v1_router)
    return app


app = create_app()
