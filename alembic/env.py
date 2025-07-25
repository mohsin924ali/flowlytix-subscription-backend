"""
Alembic Environment Configuration

Database migration environment setup for Flowlytix Subscription Server.
Follows Instructions file standards for database migrations.
"""

import asyncio
import os
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# This is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Add your model's MetaData object here
# for 'autogenerate' support
from app.core.database import Base
from app.infrastructure.database.models import subscription  # noqa: F401

target_metadata = Base.metadata

# Other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def get_database_url() -> str:
    """
    Get database URL from environment variable or config.
    
    Follows Instructions file standards for configuration management.
    """
    # Try to get from environment variable first
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        # Convert Railway PostgreSQL URL to asyncpg format if needed
        if database_url.startswith("postgresql://") and "+asyncpg" not in database_url:
            database_url = database_url.replace("postgresql://", "postgresql+asyncpg://")
        return database_url
    
    # Fallback to config file
    url = config.get_main_option("sqlalchemy.url")
    if url and url.startswith("postgresql://") and "+asyncpg" not in url:
        url = url.replace("postgresql://", "postgresql+asyncpg://")
    return url


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """
    Run migrations with database connection.
    
    Follows Instructions file standards for transaction management.
    """
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """
    Run migrations in async mode.
    
    Follows Instructions file standards for async database operations.
    """
    configuration = config.get_section(config.config_ini_section)
    
    # Override URL with environment variable if available (already converted in get_database_url)
    database_url = get_database_url()
    configuration["sqlalchemy.url"] = database_url
    
    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    asyncio.run(run_async_migrations())


# Determine if we're running in offline or online mode
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online() 