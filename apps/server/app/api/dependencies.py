"""HTTP-specific adapters for independent backend dependencies."""

from collections.abc import Iterator

from fastapi import Request
from sqlalchemy.orm import Session


def get_db(request: Request) -> Iterator[Session]:
    """Commit successful request work; rollback on any exception; always close."""
    with request.app.state.database.session() as session:
        try:
            yield session
            session.commit()
        except BaseException:
            session.rollback()
            raise
