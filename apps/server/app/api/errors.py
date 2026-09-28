"""Uniform, content-minimal HTTP error responses."""

import logging
from uuid import UUID

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.auth.jwt_verifier import CredentialConfigurationError, CredentialVerificationError
from app.core.logging import LOGGER_NAME
from app.db.session import DatabaseUnavailable
from app.schemas.error import ErrorDetail, ErrorResponse
from app.services.agent_service import AgentServiceError, AgentServiceErrorCode


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
