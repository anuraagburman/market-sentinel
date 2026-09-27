"""Endpoint contract and dependency injection; no live feeds or wall clock."""

from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.valuation import Observation, PortfolioVersion, Position
from app.services.portfolios import get_observation_repository, get_portfolio_repository
from test_valuation import records

CUTOFF = "2026-09-25T21:00:00Z"
VERSION_ID = records()[0]["id"]
URL = f"/portfolio-versions/{VERSION_ID}/valuation"


class Portfolios:
    def __init__(self, version, positions):
        self.version = PortfolioVersion.model_validate(version)
        self.rows = tuple(Position.model_validate(row) for row in positions)

    def get(self, version_id):
        return self.version if version_id == self.version.id else None

    def positions(self, version_id):
        assert version_id == self.version.id
        return self.rows


class Observations:
    def __init__(self, observations):
        self.rows = tuple(Observation.model_validate(row) for row in observations)

    def observations(self):
        return self.rows


@pytest.fixture(autouse=True)
def restore_overrides():
    previous = app.dependency_overrides.copy()
    yield
    app.dependency_overrides.clear()
    app.dependency_overrides.update(previous)


def inject(version, positions, observations):
    app.dependency_overrides[get_portfolio_repository] = lambda: Portfolios(version, positions)
    app.dependency_overrides[get_observation_repository] = lambda: Observations(observations)


def test_default_fixture_endpoint():
    with TestClient(app) as client:
        response = client.get(URL, params={"cutoff": CUTOFF})
    assert response.status_code == 200
    result = response.json()
    assert result["portfolio_version_id"] == VERSION_ID
    assert result["cutoff"] == CUTOFF
    assert result["base_currency"] == "USD"
    assert result["totals"]["priced_value"]["value"] == "12812.83"
    assert result["coverage"] == {
        "positions": 19,
        "priced": 18,
        "unpriced": 1,
        "by_reason": {"no_price": 1},
    }


@pytest.mark.parametrize(
    "cutoff",
    [
        None,
        "",
        "2026-09-25",
        "2026-09-25T21:00:00",
        "2026-09-25T21:00:00+00:00",
        "2026-09-25T22:00:00+01:00",
        "2026-02-30T21:00:00Z",
        "2026-09-25T25:00:00Z",
        "2026-09-25t21:00:00z",
    ],
)
def test_invalid_cutoff_problem(cutoff):
    with TestClient(app) as client:
        response = client.get(URL, params={} if cutoff is None else {"cutoff": cutoff})
    assert response.status_code == 422
    assert response.json()["code"] == "invalid_request"
    assert set(response.json()) == {"code", "message"}


@pytest.mark.parametrize("identifier", [str(UUID(int=0)), "unknown"])
def test_unknown_version(identifier):
    with TestClient(app) as client:
        response = client.get(
            f"/portfolio-versions/{identifier}/valuation", params={"cutoff": CUTOFF}
        )
    assert response.status_code == 404
    assert response.json()["code"] == "portfolio_version_not_found"


@pytest.mark.parametrize(
    "change,status,code",
    [
        ({"status": "preview"}, 409, "portfolio_version_not_confirmed"),
        ({"base_currency": "CAD"}, 422, "base_currency_out_of_scope"),
        ({"confirmed_at": "2026-09-25T21:00:01Z"}, 422, "cutoff_before_confirmation"),
    ],
)
def test_version_errors(change, status, code):
    v, p, o = records()
    inject(dict(v, **change), p, o)
    with TestClient(app) as client:
        response = client.get(URL, params={"cutoff": CUTOFF})
    assert response.status_code == status
    assert response.json()["code"] == code


def test_injected_snapshot_preserves_order_and_has_cash_total():
    v, p, o = records()
    v["cash"] = {"amount": "1000.00", "currency": "USD"}
    inject(v, [p[1], p[0]], o)
    with TestClient(app) as client:
        response = client.get(URL, params={"cutoff": CUTOFF})
    assert response.status_code == 200
    result = response.json()
    assert [row["display_symbol"] for row in result["positions"]] == ["SYN02", "SYN01"]
    assert result["totals"]["total_value"]["value"] == "7380.00"
    assert result["coverage"]["unpriced"] == 0


@pytest.mark.parametrize("dependency", [get_portfolio_repository, get_observation_repository])
def test_bad_repository_prevents_startup(dependency):
    def fail():
        raise ValueError("Invalid snapshot")

    app.dependency_overrides[dependency] = fail
    with pytest.raises(ValueError, match="Invalid snapshot"), TestClient(app):
        pytest.fail("Startup should have rejected the snapshot")
