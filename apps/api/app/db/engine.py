"""Lazy process engine and explicit schema readiness checks."""

import os
from functools import lru_cache
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, text

API_ROOT = Path(__file__).resolve().parents[2]


def migration_config(url: str | None = None) -> Config:
    config = Config(str(API_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(API_ROOT / "migrations"))
    if url:
        config.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    return config


def new_engine(url: str):
    return create_engine(
        url,
        pool_size=16,
        max_overflow=8,
        pool_pre_ping=True,
        isolation_level="READ COMMITTED",
        connect_args={"connect_timeout": 5},
    )


@lru_cache(maxsize=1)
def get_engine():
    return new_engine(os.environ["DATABASE_URL"])


def check_startup(engine):
    try:
        with engine.connect() as connection:
            current = connection.execute(text("SELECT version_num FROM alembic_version")).scalar()
        head = ScriptDirectory.from_config(migration_config()).get_current_head()
        if current != head:
            raise RuntimeError("Database schema is not at Alembic head; run alembic upgrade head")
    except Exception as exc:
        raise RuntimeError(f"Postgres startup failed: {exc}") from exc


def dispose_engine():
    if get_engine.cache_info().currsize:
        get_engine().dispose()
        get_engine.cache_clear()
