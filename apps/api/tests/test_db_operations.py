"""Database guards, empty startup, explicit seed and failure atomicity."""

import os
import subprocess
import sys
from uuid import uuid4

import pytest
from alembic import command
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError

from app.db.engine import API_ROOT, check_startup, dispose_engine, migration_config, new_engine
from app.db.repositories import PostgresPortfolioRepository
from app.db.seed_fixture import main as seed
from app.db.tables import confirmations, heads, versions
from app.db.tables import positions, previews
from app.main import app
from app.services.portfolios import FilePortfolioRepository
from test_confirm_repository import candidate
from test_db_workers import confirm, upload, worker

pytestmark = pytest.mark.postgres


def count(engine, table):
    with engine.connect() as connection:
        return connection.execute(select(func.count()).select_from(table)).scalar()


@pytest.mark.parametrize("table", [versions, positions, confirmations])
@pytest.mark.parametrize("operation", ["UPDATE", "DELETE"])
def test_immutable_tables(clean_postgres, table, operation):
    repository = PostgresPortfolioRepository(clean_postgres)
    repository.confirm(*candidate())
    sql = (
        f"DELETE FROM {table.name}"
        if operation == "DELETE"
        else f"UPDATE {table.name} SET tenant_id=tenant_id"
    )
    with pytest.raises(DBAPIError, match="immutable"):
        with clean_postgres.begin() as connection:
            connection.execute(text(sql))
    assert count(clean_postgres, table) > 0


def test_chain_backstop(clean_postgres):
    repository = PostgresPortfolioRepository(clean_postgres)
    record, version, holding = candidate()
    repository.confirm(record, version, holding)
    with pytest.raises(DBAPIError, match="linear_chain"):
        with clean_postgres.begin() as connection:
            row = connection.execute(select(versions)).mappings().one()
            connection.execute(versions.insert().values(**{**dict(row), "id": uuid4()}))


def test_empty_database_and_explicit_idempotent_seed(clean_postgres, monkeypatch):
    source = FilePortfolioRepository()
    with worker(clean_postgres) as client:
        assert client.get(f"/portfolio-versions/{source.version.id}").status_code == 404
        first = confirm(client, upload(client), "first")
        assert first.status_code == 201
        assert first.json()["portfolio_version"]["previous_version_id"] is None
    # Seed command is explicit, cannot be triggered by startup, and has no receipt.
    with clean_postgres.begin() as connection:
        connection.exec_driver_sql(
            "TRUNCATE portfolio_versions, positions, import_confirmations, portfolio_heads CASCADE"
        )
    monkeypatch.setenv("DATABASE_URL", clean_postgres.url.render_as_string(hide_password=False))
    monkeypatch.setenv("MS_ENV", "test")
    seed()
    seed()
    assert count(clean_postgres, versions) == 1
    assert count(clean_postgres, confirmations) == 0
    monkeypatch.setenv("MS_ENV", "prod")
    with pytest.raises(SystemExit, match="MS_ENV"):
        seed()
    result = subprocess.run(
        [sys.executable, "-m", "app.db.seed_fixture"],
        capture_output=True,
        env=os.environ.copy(),
        cwd=API_ROOT,
    )
    assert result.returncode != 0 and b"MS_ENV" in result.stderr


def test_startup_checks_head_and_reachability(clean_postgres, monkeypatch):
    config = migration_config(clean_postgres.url.render_as_string(hide_password=False))
    monkeypatch.setenv("DATABASE_URL", clean_postgres.url.render_as_string(hide_password=False))
    try:
        with clean_postgres.begin() as connection:
            connection.execute(text("UPDATE alembic_version SET version_num='below_head'"))
        with pytest.raises(RuntimeError, match="Alembic head"):
            with TestClient(app):
                pass
    finally:
        with clean_postgres.begin() as connection:
            connection.execute(text("UPDATE alembic_version SET version_num='0001'"))
        dispose_engine()
    command.check(config)
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://sentinel@127.0.0.1:1/sentinel_test")
    with pytest.raises(RuntimeError, match="Postgres startup failed"):
        with TestClient(app):
            pass
    engine = new_engine(clean_postgres.url)
    try:
        check_startup(engine)
    finally:
        engine.dispose()


@pytest.mark.parametrize(
    "sqlstate,failures,expected", [("40001", 2, 201), ("40P01", 3, 503), ("22012", 1, 503)]
)
def test_transaction_failure_retries_and_rolls_back(
    clean_postgres, monkeypatch, sqlstate, failures, expected
):
    original = PostgresPortfolioRepository.insert_version
    calls = []

    def failing_insert(self, connection, *args):
        original(self, connection, *args)
        calls.append(1)
        if len(calls) <= failures:
            connection.exec_driver_sql(
                f"DO $$ BEGIN RAISE EXCEPTION 'injected store failure' USING ERRCODE='{sqlstate}'; END $$"
            )

    monkeypatch.setattr(PostgresPortfolioRepository, "insert_version", failing_insert)
    with worker(clean_postgres) as client:
        preview = upload(client)
        result = confirm(client, preview, "failure")
        assert result.status_code == expected
        if expected == 503:
            assert result.json()["code"] == "store_unavailable"
    assert len(calls) == (3 if sqlstate in {"40001", "40P01"} else 1)
    for table in (versions, positions, confirmations, heads):
        assert count(clean_postgres, table) == (1 if expected == 201 else 0)
    assert count(clean_postgres, previews) == 1


def test_database_environment_wiring_and_disposal(clean_postgres, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", clean_postgres.url.render_as_string(hide_password=False))
    from app.db.engine import get_engine

    with TestClient(app) as client:
        assert (
            client.get(f"/portfolio-versions/{FilePortfolioRepository().version.id}").status_code
            == 404
        )
        preview = upload(client)
        result = client.post(
            f"/imports/{preview['id']}/confirm",
            headers={"Idempotency-Key": "wired"},
            json={"preview_revision": 0},
        )
        assert result.status_code == 201
        assert get_engine.cache_info().currsize == 1
    app.dependency_overrides.clear()
    assert get_engine.cache_info().currsize == 0


def test_global_key_collision_leaves_no_losing_head(clean_postgres):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    repository = PostgresPortfolioRepository(clean_postgres)
    first = candidate(key="global-key")
    other_record, other_version, other_positions = candidate(key="global-key")
    other_version = other_version.model_copy(update={"tenant_id": uuid4()})
    other = other_record, other_version, other_positions
    barrier = Barrier(2)

    # Independent tenant locks force both transactions past their receipt checks
    # before either commits, exercising the unique-violation recovery path.
    class RacingRepository(PostgresPortfolioRepository):
        def by_import(self, import_id):
            value = super().by_import(import_id)
            if value is None:
                barrier.wait(timeout=5)
            return value

    racing = RacingRepository(clean_postgres)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda args: racing.confirm(*args), [first, other]))
    assert results[0] == results[1]
    for table in (versions, confirmations, heads):
        assert count(clean_postgres, table) == 1
    assert repository.confirm(*other) == results[0]
    assert count(clean_postgres, heads) == 1
