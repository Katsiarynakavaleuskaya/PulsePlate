"""Alembic configuration for PulsePlate.

RU: Конфигурация Alembic для управления миграциями.
EN: Alembic configuration for managing database migrations.
"""

from __future__ import annotations

import logging
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context
from core.db_alembic_comparison import compare_postgresql_server_default
from core.db import Base, get_database_url

# Interpret the config file for Python logging.
config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

logger = logging.getLogger("alembic.env")

# Set SQLAlchemy URL dynamically so env vars win over alembic.ini defaults.
config.set_main_option("sqlalchemy.url", get_database_url())

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """RU: Запустить миграции в offline-режиме.

    EN: Run migrations in offline mode.
    """

    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_server_default=compare_postgresql_server_default,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """RU: Запустить миграции в online-режиме с непосредственным подключением.

    EN: Run migrations in online mode using a live connection.
    """

    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_server_default=compare_postgresql_server_default,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
