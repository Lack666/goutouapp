"""Database readiness is separate from process liveness."""

from fastapi import APIRouter, Request
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.errors import error_response
from app.db.session import DatabaseUnavailable

router = APIRouter()


@router.get("/ready", tags=["health"], responses={503: {"description": "Database unavailable"}})
def ready(request: Request):
    try:
        with request.app.state.database.engine().connect() as connection:
            connection.execute(text("SELECT 1"))
    except (DatabaseUnavailable, SQLAlchemyError, OSError, ValueError):
        return error_response(503, "database_unavailable", "Database unavailable")
    return {"status": "ready"}
