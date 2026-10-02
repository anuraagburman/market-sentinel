"""Migration lifecycle and metadata drift, on an isolated guarded database."""

import pytest
from alembic import command
from sqlalchemy import inspect

from app.db.engine import migration_config
from app.db.tables import metadata

pytestmark = pytest.mark.postgres


def test_upgrade_downgrade_and_metadata(postgres_engine):
    config = migration_config(postgres_engine.url.render_as_string(hide_password=False))
    command.check(config)
    command.downgrade(config, "base")
    assert not set(metadata.tables) & set(inspect(postgres_engine).get_table_names())
    command.upgrade(config, "head")
    assert set(metadata.tables) <= set(inspect(postgres_engine).get_table_names())
    command.check(config)


def test_explicit_migration_url_overrides_environment(postgres_engine, monkeypatch):
    test_url = postgres_engine.url.render_as_string(hide_password=False)
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://sentinel@127.0.0.1:1/other_test")
    command.check(migration_config(test_url))
