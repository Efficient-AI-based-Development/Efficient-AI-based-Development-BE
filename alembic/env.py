"""Alembic environment configuration for database migrations.

이 파일은 Alembic의 환경 설정 파일입니다.
데이터베이스 모델을 가져와서 마이그레이션 스크립트를 생성합니다.

주의:
- 우리의 모든 모델(Base.metadata에 등록된 모든 테이블)을 import해야 함
- config.py에서 데이터베이스 URL을 가져옴
- Oracle 특화 설정이 필요할 수 있음
"""

# app의 config와 models를 import
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config, pool

from alembic import context

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import settings
from app.db.database import Base
from app.db.models import (  # noqa: F401
    Document,
    GenJob,
    MCPConnection,
    MCPRun,
    MCPSession,
    Project,
    Task,
    TaskLink,
)

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def get_database_url():
    """환경 변수에서 데이터베이스 URL 가져오기"""
    # alembic.ini의 sqlalchemy.url을 설정 파일의 값으로 덮어씀
    db_url = settings.get_database_url
    config.set_main_option("sqlalchemy.url", db_url)
    return db_url


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

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


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    # 연결 URL 설정
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = settings.get_database_url

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

