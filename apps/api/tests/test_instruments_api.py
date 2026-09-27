from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.routes.imports import get_clock
from app.services.instruments import FileInstrumentRepository, get_instrument_repository


@pytest.fixture
def client():
    app.dependency_overrides[get_instrument_repository] = lambda: FileInstrumentRepository()
    app.dependency_overrides[get_clock] = lambda: lambda: datetime(2026, 6, 30, tzinfo=UTC)
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def test_lookup_exact_and_default_utc_date(client):
    response = client.get("/instruments", params={"symbol": " syn01 "})
    assert response.status_code == 200
    assert response.json()[0]["instrument"]["name"] == "Synthela 01"
    assert response.json()[0]["mapping"]["symbol"] == "SYN01"
    assert client.get("/instruments?symbol=SYN.01").json() == []
    assert client.get("/instruments?symbol=SYN-RE").json()[0]["instrument"]["name"] == "Synthela 21"
    after = client.get("/instruments?symbol=SYN-RE&as_of=2026-07-01").json()
    assert after[0]["instrument"]["name"] == "Synthela 22"
    ambiguous = client.get("/instruments?symbol=SYN-AMB").json()
    assert len(ambiguous) == 2
    assert [i["instrument"]["id"] for i in ambiguous] == sorted(
        i["instrument"]["id"] for i in ambiguous
    )


@pytest.mark.parametrize("url", ["/instruments", "/instruments?symbol=X&as_of=bad"])
def test_problem_parameters(client, url):
    response = client.get(url)
    assert response.status_code == 422
    assert set(response.json()) == {"code", "message"}


def test_bad_master_fails_startup():
    def broken():
        raise ValueError("Invalid master record SYN-BAD")

    app.dependency_overrides[get_instrument_repository] = broken
    try:
        with pytest.raises(ValueError, match="SYN-BAD"), TestClient(app):
            pass
    finally:
        app.dependency_overrides.clear()
