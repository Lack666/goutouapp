"""Alembic environment using the same secret-backed DATABASE_URL setting."""

from alembic import context
from sqlalchemy import create_engine

import app.db.models  # noqa: F401 - registers model metadata
from app.core.config import get_settings
from app.db.base import Base

config = context.config
target_metadata = Base.metadata


def database_url() -> str:
    override = config.attributes.get("database_url")
    if override is not None:
        return str(override)
    secret = get_settings().database_url
    if secret is None:
        raise RuntimeError("DATABASE_URL is required for migrations")
    return secret.get_secret_value()


def run_migrations_offline() -> None:
    context.configure(url=database_url(), target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(database_url(), pool_pre_ping=True, hide_parameters=True)
    try:
        with engine.connect() as connection:
            context.configure(connection=connection, target_metadata=target_metadata)
            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
