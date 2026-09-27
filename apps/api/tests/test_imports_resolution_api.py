"""Selection/clear round trips, audit retention, and problem responses."""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.instruments import Instrument, SymbolMapping
from app.routes.imports import get_clock, get_repository
from app.services.imports import InMemoryPreviewRepository
from app.services.instruments import FileInstrumentRepository, get_instrument_repository

ROOT = Path(__file__).resolve().parents[3]
NOW = datetime(2026, 9, 25, 21, tzinfo=UTC)
ID = "00000000-0000-4000-8000-000000000002"


class TestMaster:
    __test__ = False

    def __init__(self):
        self.base = FileInstrumentRepository()
        self.retired = Instrument(
            id=UUID(int=1234), name="Retired", asset_type="common_stock", currency="USD"
        )

    def get(self, instrument_id):
        return self.retired if instrument_id == self.retired.id else self.base.get(instrument_id)

    def mappings(self):
        return self.base.mappings() + (
            SymbolMapping(
                symbol="RETIRED",
                instrument_id=self.retired.id,
                valid_from="2020-01-01",
                valid_to="2021-01-01",
            ),
        )


@pytest.fixture
def client():
    master = TestMaster()
    repository = InMemoryPreviewRepository()
    app.dependency_overrides[get_instrument_repository] = lambda: master
    app.dependency_overrides[get_repository] = lambda: repository
    app.dependency_overrides[get_clock] = lambda: lambda: NOW
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def upload(client, content=None):
    content = (
        content
        if content is not None
        else (ROOT / "evals/fixtures/portfolio/holdings.csv").read_bytes()
    )
    response = client.post("/imports", files={"file": ("holdings.csv", content, "text/csv")})
    assert response.status_code == 201
    return response.json()


def test_acceptance_selection_clear_and_audit(client):
    preview = upload(client)
    positions = json.loads((ROOT / "evals/fixtures/portfolio/positions.json").read_text())
    for number in (2, 5):
        url = f"/imports/{preview['id']}/rows/{number}/resolution"
        original = preview["rows"][number - 1]
        response = client.put(url, json={"instrument_id": positions[number - 1]["instrument_id"]})
        assert response.status_code == 200
        row = response.json()
        assert row["raw"] == original["raw"] and row["parsed"] == original["parsed"]
        assert row["status"] == original["status"] and row["issues"] == original["issues"]
        resolution = row["resolution"]
        assert resolution["instrument_id"] == positions[number - 1]["instrument_id"]
        assert resolution["method"] == "user_selected"
        assert resolution["selected_at"] == "2026-09-25T21:00:00Z"
        assert resolution["candidates"] == original["resolution"]["candidates"]
        assert resolution["issues"] == original["resolution"]["issues"]
        app.dependency_overrides[get_clock] = lambda: lambda: NOW + timedelta(seconds=5)
        repeat = client.put(url, json={"instrument_id": resolution["instrument_id"]}).json()
        assert repeat["resolution"].pop("selected_at") == "2026-09-25T21:00:05Z"
        row["resolution"].pop("selected_at")
        assert repeat == row
        app.dependency_overrides[get_clock] = lambda: lambda: NOW
    stored = client.get(f"/imports/{preview['id']}").json()
    assert stored["summary"]["by_resolution"] == {"resolved": 20}
    for number in (2, 5):
        restored = client.delete(f"/imports/{preview['id']}/rows/{number}/resolution")
        assert restored.status_code == 200
        assert restored.json() == preview["rows"][number - 1]
    assert client.get(f"/imports/{preview['id']}").json() == {**preview, "revision": 6}


def test_selection_recomputes_currency_warning(client):
    preview = upload(client, b"symbol,quantity,currency\nSYN21,1,USD\n")
    assert preview["rows"][0]["resolution"]["issues"][0]["code"] == "currency_mismatch"
    url = f"/imports/{preview['id']}/rows/1/resolution"
    assert client.put(url, json={"instrument_id": ID}).json()["resolution"]["issues"] == []
    cad = "00000000-0000-4000-8000-000000001003"
    row = client.put(url, json={"instrument_id": cad}).json()
    assert [i["code"] for i in row["resolution"]["issues"]] == ["currency_mismatch"]
    assert client.delete(url).json() == preview["rows"][0]


@pytest.mark.parametrize("method", ["put", "delete"])
@pytest.mark.parametrize(
    "case,expected,code",
    [
        ("import", 404, "import_not_found"),
        ("row", 404, "row_not_found"),
        ("blank", 409, "row_not_resolvable"),
    ],
)
def test_missing_and_blank(client, method, case, expected, code):
    preview = upload(client, b"symbol,quantity,currency\n\nSYN01,1,USD\n")
    import_id = "unknown" if case == "import" else preview["id"]
    number = 99 if case == "row" else 1
    kwargs = {"json": {"instrument_id": ID}} if method == "put" else {}
    response = getattr(client, method)(f"/imports/{import_id}/rows/{number}/resolution", **kwargs)
    assert response.status_code == expected
    assert response.json()["code"] == code


@pytest.mark.parametrize(
    "instrument_id,code",
    [(str(UUID(int=777)), "unknown_instrument"), (str(UUID(int=1234)), "instrument_not_listed")],
)
def test_unknown_and_unlisted(client, instrument_id, code):
    preview = upload(client)
    response = client.put(
        f"/imports/{preview['id']}/rows/2/resolution", json={"instrument_id": instrument_id}
    )
    assert response.status_code == 422
    assert response.json()["code"] == code
    assert client.get(f"/imports/{preview['id']}").json() == preview


def test_selection_uses_preview_date_and_problem_validation(client):
    app.dependency_overrides[get_clock] = lambda: lambda: datetime(2019, 1, 1, tzinfo=UTC)
    preview = upload(client)
    app.dependency_overrides[get_clock] = lambda: lambda: NOW
    url = f"/imports/{preview['id']}/rows/1/resolution"
    assert client.put(url, json={"instrument_id": ID}).json()["code"] == "instrument_not_listed"
    response = client.put(url, json={"instrument_id": "bad"})
    assert response.status_code == 422
    assert response.json()["code"] == "invalid_request"
