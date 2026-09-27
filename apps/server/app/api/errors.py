"""Uniform, content-minimal HTTP error responses."""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import LOGGER_NAME
from app.db.session import DatabaseUnavailable
from app.schemas.error import ErrorDetail, ErrorResponse


def error_response(
    status_code: int, code: str, message: str, headers: dict[str, str] | None = None
) -> JSONResponse:
    payload = ErrorResponse(error=ErrorDetail(code=code, message=message))
    return JSONResponse(status_code=status_code, content=payload.model_dump(), headers=headers)


def register_error_handlers(app: FastAPI) -> None:
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
