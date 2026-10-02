"""Independent workers share committed previews, a linear chain and durable receipts."""

from concurrent.futures import ThreadPoolExecutor
from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.db.engine import new_engine
from app.db.repositories import PostgresPortfolioRepository, PostgresPreviewRepository
from app.db.tables import versions
from app.routes.imports import get_clock, get_repository, router as imports_router
from app.routes.portfolios import router as portfolios_router
from app.services.portfolios import get_portfolio_repository
from test_confirm_api import CONFIRM, SIMPLE, UPLOAD

pytestmark = pytest.mark.postgres


def worker(engine):
    app = FastAPI()
    app.include_router(imports_router)
    app.include_router(portfolios_router)
    app.dependency_overrides[get_repository] = lambda: PostgresPreviewRepository(engine)
    app.dependency_overrides[get_portfolio_repository] = lambda: PostgresPortfolioRepository(engine)
    app.dependency_overrides[get_clock] = lambda: lambda: UPLOAD
    return TestClient(app)


def upload(client):
    result = client.post("/imports", files={"file": ("holdings.csv", SIMPLE, "text/csv")})
    assert result.status_code == 201
    return result.json()


def confirm(client, preview, key):
    client.app.dependency_overrides[get_clock] = lambda: lambda: CONFIRM
    return client.post(
        f"/imports/{preview['id']}/confirm",
        headers={"Idempotency-Key": key},
        json={"preview_revision": preview["revision"]},
    )


def test_workers_share_revision_and_single_winner(clean_postgres):
    second = new_engine(clean_postgres.url)
    try:
        with worker(clean_postgres) as a, worker(second) as b:
            preview = upload(a)
            path = f"/imports/{preview['id']}"
            assert b.get(path).json() == a.get(path).json()
            assert b.put(path + "/rows/1/exclusion").status_code == 200
            stale = confirm(a, preview, "stale")
            assert stale.status_code == 409 and stale.json()["code"] == "preview_changed"
            assert b.delete(path + "/rows/1/exclusion").status_code == 200
            ready = b.get(path).json()
            with ThreadPoolExecutor(max_workers=2) as pool:
                futures = [pool.submit(confirm, a, ready, "a"), pool.submit(confirm, b, ready, "b")]
                results = [f.result() for f in futures]
            assert sorted(r.status_code for r in results) == [201, 409]
            assert (
                next(r for r in results if r.status_code == 409).json()["code"]
                == "import_already_confirmed"
            )
            with clean_postgres.connect() as connection:
                assert connection.execute(select(func.count()).select_from(versions)).scalar() == 1
    finally:
        second.dispose()


def test_different_imports_have_linear_chain(clean_postgres):
    second = new_engine(clean_postgres.url)
    try:
        with worker(clean_postgres) as a, worker(second) as b:
            first, other = upload(a), upload(b)
            with ThreadPoolExecutor(max_workers=2) as pool:
                futures = [pool.submit(confirm, a, first, "a"), pool.submit(confirm, b, other, "b")]
                responses = [f.result() for f in futures]
            assert [r.status_code for r in responses] == [201, 201]
            stored = [r.json()["portfolio_version"] for r in responses]
            root = next(v for v in stored if v["previous_version_id"] is None)
            child = next(v for v in stored if v["previous_version_id"] is not None)
            assert child["previous_version_id"] == root["id"]
    finally:
        second.dispose()


def test_restart_retains_identical_response_and_valuation(clean_postgres):
    engine = new_engine(clean_postgres.url)
    with worker(engine) as a:
        preview = upload(a)
        response = confirm(a, preview, "durable")
        assert response.status_code == 201
        version_id = response.json()["portfolio_version"]["id"]
        path = f"/portfolio-versions/{version_id}"
        snapshot = a.get(path).content
        valuation = a.get(path + "/valuation?cutoff=2026-09-25T21:00:00Z").content
    engine.dispose()
    fresh = new_engine(clean_postgres.url)
    try:
        with worker(fresh) as b:
            assert (
                b.get(f"/imports/{preview['id']}").json()["confirmation"]["portfolio_version_id"]
                == version_id
            )
            assert b.get(path).content == snapshot
            assert b.get(path + "/valuation?cutoff=2026-09-25T21:00:00Z").content == valuation
            replay = confirm(b, preview, "durable")
            assert replay.status_code == 200 and replay.content == response.content
            assert PostgresPortfolioRepository(fresh).get(UUID(version_id)) is not None
    finally:
        fresh.dispose()
