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
