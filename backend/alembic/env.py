"""Alembic environment configuration for FaceAttend.

Alembic runs migrations using psycopg2 (sync) while the FastAPI app uses
asyncpg. This avoids asyncpg's extended-query-protocol limitations with DDL
(e.g. CREATE TYPE inside PL/pgSQL DO blocks or idempotency checks).
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

from app.core.config import settings
from app.models import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Convert asyncpg URL to psycopg2 for synchronous migration execution.
_sync_url = settings.database_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Generate SQL without a live DB connection (used by CI / review)."""
    context.configure(
        url=_sync_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Apply migrations against a live database using psycopg2."""
    connectable = create_engine(_sync_url, poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
