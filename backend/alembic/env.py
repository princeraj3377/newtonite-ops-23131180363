


from logging.config import fileConfig
import os
from pathlib import Path

from sqlalchemy import engine_from_config, pool
from alembic import context
from dotenv import dotenv_values

from app.database import Base, DATABASE_URL
import app.models


# Alembic configuration
config = context.config


# ----------------------------------------
# DATABASE SELECTION
# ----------------------------------------

if os.getenv("USE_TEST_DB") == "1":

    # Load the test database configuration
    test_env_path = (
        Path(__file__).resolve().parents[1] / ".env.test"
    )

    test_config = dotenv_values(test_env_path)

    database_url = test_config.get("DATABASE_URL")

    if not database_url:
        raise RuntimeError(
            "DATABASE_URL missing in .env.test"
        )

    # Safety check: allow only the test database
    from sqlalchemy.engine import make_url

    database_name = make_url(database_url).database

    if database_name != "newtonite_ops_test":
        raise RuntimeError(
            "Refusing to run test migrations "
            "on a non-test database"
        )

else:
    # Use the main database
    database_url = DATABASE_URL
    from sqlalchemy.engine import make_url
    database_name = make_url(database_url).database


# Set the selected database URL
config.set_main_option(
    "sqlalchemy.url",
    database_url.replace("%", "%%")
)

print("Alembic target database:", database_name)


# ----------------------------------------
# LOGGING CONFIGURATION
# ----------------------------------------

if config.config_file_name is not None:
    fileConfig(config.config_file_name)


# ----------------------------------------
# SQLALCHEMY METADATA
# ----------------------------------------

target_metadata = Base.metadata


# ----------------------------------------
# OFFLINE MIGRATIONS
# ----------------------------------------

def run_migrations_offline() -> None:

    url = config.get_main_option("sqlalchemy.url")

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


# ----------------------------------------
# ONLINE MIGRATIONS
# ----------------------------------------

def run_migrations_online() -> None:

    connectable = engine_from_config(
        config.get_section(
            config.config_ini_section,
            {}
        ),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:

        context.configure(
            connection=connection,
            target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


# ----------------------------------------
# RUN MIGRATIONS
# ----------------------------------------

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
