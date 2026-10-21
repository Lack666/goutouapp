"""A disposable PostgreSQL database per pytest run; never touch the development DB."""

import os
from collections.abc import Iterator
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session


@pytest.fixture(scope="session")
def database_engine() -> Iterator[Engine]:
    raw_url = os.getenv("TEST_DATABASE_URL")
    if not raw_url:
        pytest.fail("TEST_DATABASE_URL is required for Phase 2B database tests")
    url = make_url(raw_url)
    if url.drivername != "postgresql+psycopg" or not (url.database or "").endswith("_test"):
        pytest.fail("TEST_DATABASE_URL must use psycopg and a database name ending _test")
    dev_url = os.getenv("DATABASE_URL")
    if dev_url and make_url(dev_url).database == url.database:
        pytest.fail("TEST_DATABASE_URL must differ from DATABASE_URL")

    name = f"{url.database}_{uuid4().hex[:12]}"
    isolated_url = url.set(database=name)
    admin = create_engine(
        url.set(database="postgres"), isolation_level="AUTOCOMMIT", hide_parameters=True
    )
    engine = None
    try:
        with admin.connect() as connection:
            connection.execute(text(f'CREATE DATABASE "{name}"'))
        config = Config("alembic.ini")
        config.attributes["database_url"] = isolated_url.render_as_string(hide_password=False)
        command.upgrade(config, "head")
        engine = create_engine(isolated_url, hide_parameters=True)
        yield engine
    finally:
        if engine is not None:
            engine.dispose()
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


@pytest.fixture
def db_session(database_engine: Engine) -> Iterator[Session]:
    with database_engine.connect() as connection:
        outer = connection.begin()
        try:
            with Session(bind=connection, join_transaction_mode="create_savepoint") as session:
                yield session
        finally:
            outer.rollback()


@pytest.fixture
def recovery_database_engine() -> Iterator[Engine]:
    # Recovery archives contain every owner. Unresolved synthetic fault rows from
    # a different test must not be silently treated as quiescent current authority.
    # Keep incident/restore tests in independently migrated disposable databases.
    from memory_control_demo import disposable_database

    with disposable_database() as engine:
        yield engine
