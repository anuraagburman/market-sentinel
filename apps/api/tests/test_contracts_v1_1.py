"""Producers conform to the shared v1.1 schemas (ADR-004); format checking is on."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

from app.main import app
from app.services.instruments import FileInstrumentRepository
from app.services.portfolios import get_observation_repository, get_portfolio_repository
from test_valuation import records
from test_valuation_api import CUTOFF, URL, Observations, Portfolios

SCHEMAS = Path(__file__).resolve().parents[3] / "packages/contracts/schemas"
_schemas = {p.name: json.loads(p.read_text()) for p in SCHEMAS.glob("*.schema.json")}
_registry = Registry().with_resources(
    (s["$id"], Resource.from_contents(s)) for s in _schemas.values()
)


def validator(name):
    return Draft202012Validator(
        _schemas[f"{name}.schema.json"], registry=_registry, format_checker=FormatChecker()
    )


@pytest.fixture(autouse=True)
def restore_overrides():
    previous = app.dependency_overrides.copy()
    yield
    app.dependency_overrides.clear()
    app.dependency_overrides.update(previous)


def valuation(version, positions, observations):
    app.dependency_overrides[get_portfolio_repository] = lambda: Portfolios(version, positions)
    app.dependency_overrides[get_observation_repository] = lambda: Observations(observations)
    response = TestClient(app).get(URL, params={"cutoff": CUTOFF})
    assert response.status_code == 200, response.text
    return response.json()


def test_synthetic_portfolio_valuation_conforms():
    body = valuation(*records())
    assert body["coverage"]["unpriced"] > 0, "fixture should exercise unavailable amounts"
    validator("valuation").validate(body)


def test_empty_portfolio_with_unknown_cash_conforms():
    version, _, observations = records()
    version = {k: v for k, v in version.items() if k != "cash"}
    body = valuation(version, [], observations)
    assert body["totals"]["cash"] == {"kind": "unavailable", "reason": "cash_unknown"}
    validator("valuation").validate(body)


@pytest.mark.parametrize("close", ["0", "-1", "-0.00"])
@pytest.mark.parametrize("companions", ["none", "older", "simultaneous", "both"])
def test_non_positive_producer_returns_unavailable_and_conforms(close, companions):
    version, positions, observations = records()
    candidates = [dict(observations[0], value=close)]
    if companions in ("older", "both"):
        candidates.append(
            dict(observations[0], id=observations[2]["id"], observed_at="2026-09-24T20:00:00Z")
        )
    if companions in ("simultaneous", "both"):
        candidates.append(dict(observations[0], id=observations[3]["id"]))
    body = valuation(version, positions[:2], [*candidates, observations[1]])
    row, priced = body["positions"]
    assert row["price"] is None
    assert row["market_value"] == {"kind": "unavailable", "reason": "no_price"}
    for field in ("unrealized_pl", "weight"):
        assert row[field] == {"kind": "unavailable", "reason": "market_value_unavailable"}
    assert priced["weight"]["value"] == "1.000000"
    assert body["coverage"] == {
        "positions": 2,
        "priced": 1,
        "unpriced": 1,
        "by_reason": {"no_price": 1},
    }
    assert body["totals"]["priced_value"]["value"] == "125.00"
    assert body["totals"]["total_value"] == {"kind": "unavailable", "reason": "positions_unpriced"}
    validator("valuation").validate(body)


def test_instrument_master_conforms():
    repository = FileInstrumentRepository()
    mappings = repository.mappings()
    assert mappings
    for mapping in mappings:
        validator("symbol_mapping").validate(mapping.model_dump(mode="json"))
        instrument = repository.get(mapping.instrument_id)
        validator("instrument").validate(instrument.model_dump(mode="json"))
