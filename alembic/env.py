from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context
import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import SQLModel and your models
from sqlmodel import SQLModel
from app.models import Task  # Import all your table models

# this is the Alembic Config object
config = context.config

# Override sqlalchemy.url with environment variable
config.set_main_option("sqlalchemy.url", os.getenv("DATABASE_URL"))

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Use SQLModel's metadata
target_metadata = SQLModel.metadata


def render_item(type_, obj, autogen_context):
    """Render SQLModel types as standard SQLAlchemy types in migrations."""
    # Import here to avoid issues if sqlmodel isn't installed
    from sqlmodel.sql.sqltypes import AutoString
    from sqlalchemy import String
    
    # Convert AutoString to standard String
    if isinstance(type_, type) and issubclass(type_, AutoString):
        # Get the length from the type
        if hasattr(obj, 'length'):
            return f"sa.String(length={obj.length})"
        return "sa.String()"
    
    # Default rendering
    return False


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_item=render_item,  # Add custom renderer
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        render_item=render_item,  # Add custom renderer
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in 'online' mode with async support."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()