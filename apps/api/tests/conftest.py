"""Real committed Postgres tests, guarded against touching developer databases."""

import os

import pytest
from alembic import command
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from app.db.engine import migration_config, new_engine

DATABASE_URL = os.environ.get("DATABASE_URL")
if DATABASE_URL and not (make_url(DATABASE_URL).database or "").endswith("_test"):
    raise pytest.UsageError("DATABASE_URL database name must end in _test when running tests")

URL = os.environ.get("TEST_DATABASE_URL")
if os.environ.get("CI", "").lower() == "true" and not URL:
    raise pytest.UsageError("CI requires TEST_DATABASE_URL; Postgres tests must not be skipped")
if URL and not (make_url(URL).database or "").endswith("_test"):
    raise pytest.UsageError("TEST_DATABASE_URL database name must end in _test")


def pytest_configure(config):
    config.addinivalue_line("markers", "postgres: requires guarded local TEST_DATABASE_URL")


@pytest.fixture(scope="session")
def postgres_engine():
    if not URL:
        pytest.skip("Postgres requires TEST_DATABASE_URL (database name ending in _test)")
    url = make_url(URL)
    admin = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin.connect() as connection:
        exists = connection.execute(
            text("SELECT 1 FROM pg_database WHERE datname=:name"), {"name": url.database}
        ).scalar()
        if not exists:
            name = connection.dialect.identifier_preparer.quote(url.database)
            connection.exec_driver_sql(f"CREATE DATABASE {name}")
    admin.dispose()
    command.upgrade(migration_config(URL), "head")
    engine = new_engine(URL)
    yield engine
    engine.dispose()


@pytest.fixture
def clean_postgres(postgres_engine):
    from app.db.tables import metadata

    names = ", ".join(metadata.tables)
    if names:
        with postgres_engine.begin() as connection:
            connection.exec_driver_sql(f"TRUNCATE {names} CASCADE")
    return postgres_engine
