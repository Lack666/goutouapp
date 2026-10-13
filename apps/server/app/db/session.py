"""Lazy database engine and sessions, independent of HTTP transport."""

from threading import RLock

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings


class DatabaseUnavailable(Exception):
    """Connection configuration or reachability failed; do not expose DB internals."""


class Database:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._lock = RLock()
        self._engine: Engine | None = None
        self._factory: sessionmaker[Session] | None = None

    def engine(self) -> Engine:
        with self._lock:
            if self._engine is None:
                if self._settings.database_url is None:
                    raise DatabaseUnavailable
                url = self._settings.database_url.get_secret_value()
                if not url.startswith("postgresql+psycopg://"):
                    raise DatabaseUnavailable
                self._engine = create_engine(
                    url,
                    pool_pre_ping=True,
                    hide_parameters=True,
                    pool_size=self._settings.database_pool_size,
                    max_overflow=self._settings.database_max_overflow,
                    pool_timeout=self._settings.database_pool_timeout_seconds,
                    connect_args={"connect_timeout": 2, "options": "-c timezone=UTC"},
                )
            return self._engine

    def session(self) -> Session:
        with self._lock:
            if self._factory is None:
                self._factory = sessionmaker(bind=self.engine(), expire_on_commit=False)
            return self._factory()

    def dispose(self) -> None:
        with self._lock:
            if self._engine is not None:
                self._engine.dispose()
            self._engine = None
            self._factory = None
