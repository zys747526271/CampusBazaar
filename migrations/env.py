"""Alembic 环境：直接复用 Flask app 的数据库配置，避免出现两套连接串。"""
from __future__ import annotations

from logging.config import fileConfig

from alembic import context

from backend import create_app
from backend.extensions import db
import backend.models  # noqa: F401  确保所有模型被注册到 metadata

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

app = create_app()
target_metadata = db.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=app.config["SQLALCHEMY_DATABASE_URI"],
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    with app.app_context():
        connection = db.engine.connect()
        try:
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                compare_type=True,
                render_as_batch=True,
            )
            with context.begin_transaction():
                context.run_migrations()
        finally:
            connection.close()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
