"""Uniform, content-minimal HTTP error responses."""

import logging
from uuid import UUID

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.auth.jwt_verifier import CredentialConfigurationError, CredentialVerificationError
from app.chat_import.artifacts import ArtifactStoreError, UploadTooLarge
from app.core.logging import LOGGER_NAME
from app.db.session import DatabaseUnavailable
from app.schemas.error import ErrorDetail, ErrorResponse
from app.services.agent_service import AgentServiceError, AgentServiceErrorCode
from app.services.erasure import ErasureError
from app.services.import_jobs import ImportJobError, ImportJobErrorCode
from app.services.import_merge import ImportMergeError, ImportMergeErrorCode
from app.services.import_workflow import ImportWorkflowError, ImportWorkflowErrorCode
from app.services.imported_analysis import AnalysisError
from app.services.memory_control import MemoryControlError, MemoryControlErrorCode
from app.services.memory_mutation import MemoryMutationError, MemoryMutationErrorCode
from app.services.resources import ResourceError, ResourceErrorCode


def error_response(
    status_code: int,
    code: str,
    message: str,
    headers: dict[str, str] | None = None,
    *,
    run_id: UUID | None = None,
    recovery_status: str | None = None,
) -> JSONResponse:
    payload = ErrorResponse(
        error=ErrorDetail(
            code=code, message=message, run_id=run_id, recovery_status=recovery_status
        )
    )
    return JSONResponse(
        status_code=status_code,
        content=payload.model_dump(mode="json", exclude_none=True),
        headers=headers,
    )


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AnalysisError)
    async def analysis_error(_request: Request, exc: AnalysisError) -> JSONResponse:
        return error_response(
            404 if exc.code == "scope_unavailable" else 409,
            exc.code,
            "Analysis scope unavailable or requires new preparation",
        )

    @app.exception_handler(ErasureError)
    async def erasure_error(_request: Request, exc: ErasureError) -> JSONResponse:
        if exc.code == "invalid_credential":
            return error_response(
                401, exc.code, "Valid Bearer credential required", {"WWW-Authenticate": "Bearer"}
            )
        if exc.code in {"not_found", "confirmation_not_found"}:
            return error_response(404, exc.code, "Resource not found")
        if exc.code == "persistence_failure":
            return error_response(503, exc.code, "Erasure unavailable")
        return error_response(409, exc.code, "Erasure requires authoritative review")

    @app.exception_handler(ResourceError)
    async def resource_error(_request: Request, exc: ResourceError) -> JSONResponse:
        if exc.code == ResourceErrorCode.UNAUTHORIZED:
            return error_response(
                401,
                "invalid_credential",
                "Valid Bearer credential required",
                {"WWW-Authenticate": "Bearer"},
            )
        if exc.code == ResourceErrorCode.NOT_FOUND:
            return error_response(404, "not_found", "Resource not found")
        if exc.code == ResourceErrorCode.CREATION_CONFLICT:
            return error_response(409, exc.code.value, "Resource ID belongs to another request")
        if exc.code == ResourceErrorCode.INVALID_CURSOR:
            return error_response(422, exc.code.value, "Invalid resource cursor")
        return error_response(503, "persistence_failure", "Resource operation unavailable")

    @app.exception_handler(MemoryMutationError)
    async def memory_mutation_error(_request: Request, exc: MemoryMutationError) -> JSONResponse:
        code = exc.code
        if code == MemoryMutationErrorCode.UNAUTHORIZED:
            return error_response(
                401,
                "invalid_credential",
                "Valid Bearer credential required",
                {"WWW-Authenticate": "Bearer"},
            )
        if code in {
            MemoryMutationErrorCode.MEMORY_NOT_FOUND,
            MemoryMutationErrorCode.PERSON_NOT_FOUND,
            MemoryMutationErrorCode.MUTATION_NOT_FOUND,
        }:
            return error_response(404, code.value, "Resource not found")
        if code == MemoryMutationErrorCode.INVALID_OPERATION_KEY:
            return error_response(400, code.value, "Invalid operation key")
        if code == MemoryMutationErrorCode.PERSISTENCE_FAILURE:
            return error_response(503, code.value, "Memory mutation unavailable")
        return error_response(409, code.value, "Memory mutation needs a new confirmation")

    @app.exception_handler(MemoryControlError)
    async def memory_control_error(_request: Request, exc: MemoryControlError) -> JSONResponse:
        code = exc.code
        if code == MemoryControlErrorCode.UNAUTHORIZED:
            return error_response(
                401,
                "invalid_credential",
                "Valid Bearer credential required",
                {"WWW-Authenticate": "Bearer"},
            )
        if code in {
            MemoryControlErrorCode.PERSON_NOT_FOUND,
            MemoryControlErrorCode.RELATIONSHIP_NOT_FOUND,
            MemoryControlErrorCode.MEMORY_NOT_FOUND,
        }:
            return error_response(404, code.value, "Resource not found")
        if code == MemoryControlErrorCode.INVALID_SCOPE:
            return error_response(400, "invalid_scope", "Invalid memory scope or cursor")
        return error_response(503, "persistence_failure", "Memory operation unavailable")

    @app.exception_handler(UploadTooLarge)
    async def upload_too_large(_request: Request, _exc: UploadTooLarge) -> JSONResponse:
        return error_response(413, "upload_too_large", "Upload exceeds configured limit")

    @app.exception_handler(ImportWorkflowError)
    async def import_workflow_error(_request: Request, exc: ImportWorkflowError) -> JSONResponse:
        code = exc.code
        if code == ImportWorkflowErrorCode.TRANSCRIPT_MISMATCH:
            return error_response(409, "transcript_mismatch", "Source integrity check failed")
        if code == ImportWorkflowErrorCode.ARTIFACT_UNAVAILABLE:
            return error_response(409, "artifact_unavailable", "Import source unavailable")
        if code == ImportWorkflowErrorCode.PARSE_FAILED:
            return error_response(422, "parse_failed", "Chat source could not be parsed")
        if code == ImportWorkflowErrorCode.UNSUPPORTED_FORMAT:
            return error_response(415, "unsupported_format", "Unsupported chat export format")
        return error_response(400, "invalid_upload", "Invalid import request")

    @app.exception_handler(ArtifactStoreError)
    async def artifact_error(_request: Request, _exc: ArtifactStoreError) -> JSONResponse:
        return error_response(503, "artifact_unavailable", "Import storage unavailable")

    @app.exception_handler(ImportJobError)
    async def import_job_error(_request: Request, exc: ImportJobError) -> JSONResponse:
        if exc.code in {
            ImportJobErrorCode.JOB_NOT_FOUND,
            ImportJobErrorCode.SPEAKER_NOT_FOUND,
            ImportJobErrorCode.PERSON_NOT_FOUND,
            ImportJobErrorCode.RELATIONSHIP_NOT_FOUND,
        }:
            return error_response(404, "job_not_found", "Import resource not found")
        if exc.code == ImportJobErrorCode.REVISION_CONFLICT:
            return error_response(409, "stale_revision", "Import binding revision changed")
        if exc.code == ImportJobErrorCode.NOT_READY:
            return error_response(409, "job_not_ready", "Import binding is incomplete")
        if exc.code == ImportJobErrorCode.INVALID_BINDING:
            return error_response(400, "binding_invalid", "Invalid speaker binding")
        if exc.code in {ImportJobErrorCode.JOB_CANCELLED, ImportJobErrorCode.JOB_IMPORTED}:
            return error_response(409, "job_not_ready", "Import job is no longer editable")
        if exc.code == ImportJobErrorCode.INVALID_ACTOR:
            return error_response(401, "invalid_credential", "Valid Bearer credential required")
        return error_response(422, "parse_failed", "Chat source could not be parsed")

    @app.exception_handler(ImportMergeError)
    async def import_merge_error(_request: Request, exc: ImportMergeError) -> JSONResponse:
        if exc.code == ImportMergeErrorCode.DATASET_DELETED:
            return error_response(409, "dataset_deleted", "Dataset was deleted")
        if exc.code == ImportMergeErrorCode.JOB_NOT_FOUND:
            return error_response(404, "job_not_found", "Import resource not found")
        if exc.code == ImportMergeErrorCode.REVISION_CONFLICT:
            return error_response(409, "stale_revision", "Import binding revision changed")
        if exc.code == ImportMergeErrorCode.TRANSCRIPT_MISMATCH:
            return error_response(409, "transcript_mismatch", "Source integrity check failed")
        if exc.code == ImportMergeErrorCode.BINDING_INVALID:
            return error_response(409, "binding_invalid", "Import binding is invalid")
        if exc.code == ImportMergeErrorCode.PERSISTENCE_FAILED:
            return error_response(503, "import_failed", "Import could not be saved")
        return error_response(409, "job_not_ready", "Import job is not ready")

    @app.exception_handler(CredentialVerificationError)
    async def invalid_credential(
        _request: Request, _exc: CredentialVerificationError
    ) -> JSONResponse:
        return error_response(
            401,
            "invalid_credential",
            "Valid Bearer credential required",
            {"WWW-Authenticate": "Bearer"},
        )

    @app.exception_handler(CredentialConfigurationError)
    async def missing_verifier(
        _request: Request, _exc: CredentialConfigurationError
    ) -> JSONResponse:
        return error_response(503, "authentication_unavailable", "Authentication unavailable")

    @app.exception_handler(AgentServiceError)
    async def service_error(_request: Request, exc: AgentServiceError) -> JSONResponse:
        if exc.code in {
            AgentServiceErrorCode.CONVERSATION_NOT_FOUND,
            AgentServiceErrorCode.CONVERSATION_FORBIDDEN,
            AgentServiceErrorCode.INVALID_RELATIONSHIP_SCOPE,
        }:
            return error_response(404, "not_found", "Resource not found")
        if exc.code == AgentServiceErrorCode.INVALID_INPUT:
            return error_response(400, "invalid_input", "Invalid request")
        if exc.code == AgentServiceErrorCode.CONVERSATION_BUSY:
            return error_response(409, "conversation_busy", "Conversation has an active run")
        if exc.code == AgentServiceErrorCode.IDEMPOTENCY_CONFLICT:
            return error_response(
                409,
                "idempotency_conflict",
                "Operation key belongs to another request",
                run_id=exc.run_id,
            )
        if exc.code == AgentServiceErrorCode.OPERATION_IN_PROGRESS:
            return error_response(
                409,
                "operation_in_progress",
                "Operation is still running",
                run_id=exc.run_id,
            )
        if exc.code == AgentServiceErrorCode.OPERATION_UNRESOLVED:
            return error_response(
                409,
                "operation_unresolved",
                "Operation requires recovery",
                run_id=exc.run_id,
            )
        if exc.code == AgentServiceErrorCode.OPERATION_FAILED:
            return error_response(
                409,
                "operation_failed",
                "Operation previously failed",
                run_id=exc.run_id,
                recovery_status="failed",
            )
        if exc.code in {AgentServiceErrorCode.INVALID_ACTOR, AgentServiceErrorCode.USER_NOT_FOUND}:
            return error_response(
                401,
                "invalid_credential",
                "Valid Bearer credential required",
                {"WWW-Authenticate": "Bearer"},
            )
        if exc.code == AgentServiceErrorCode.RUNTIME_FAILURE:
            return error_response(
                502,
                "agent_failure",
                "Agent run failed",
                run_id=exc.run_id,
                recovery_status=exc.recovery_status,
            )
        return error_response(
            503,
            "persistence_failure",
            "Agent result could not be saved",
            run_id=exc.run_id,
            recovery_status=exc.recovery_status,
        )

    @app.exception_handler(DatabaseUnavailable)
    async def database_unavailable(_request: Request, _exc: DatabaseUnavailable) -> JSONResponse:
        return error_response(503, "database_unavailable", "Database unavailable")

    @app.exception_handler(StarletteHTTPException)
    async def http_error(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
        if exc.status_code == 404:
            return error_response(404, "not_found", "Resource not found", exc.headers)
        if exc.status_code == 413:
            return error_response(413, "upload_too_large", "Upload exceeds configured limit")
        return error_response(exc.status_code, "http_error", "Request failed", exc.headers)

    @app.exception_handler(RequestValidationError)
    async def validation_error(_request: Request, _exc: RequestValidationError) -> JSONResponse:
        # FastAPI validation errors can include request input; omit them here.
        return error_response(422, "validation_error", "Invalid request")

    @app.exception_handler(Exception)
    async def unexpected_error(_request: Request, _exc: Exception) -> JSONResponse:
        # Deliberately omit exception text, request body, headers and traceback.
        logging.getLogger(LOGGER_NAME).error("Unhandled server error")
        return error_response(500, "internal_error", "Internal server error")
