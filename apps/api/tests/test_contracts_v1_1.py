"""Producers conform to the shared v1.1 schemas (ADR-004); format checking is on."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator, FormatChecker, ValidationError
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


@pytest.mark.xfail(
    strict=True,
    raises=ValidationError,
    reason="Producer still prices non-positive closes (T-008 carry-forward); ADR-004 requires price > 0",
)
@pytest.mark.parametrize("close", ["0", "-1"])
def test_non_positive_close_conforms(close):
    version, positions, observations = records()
    observations = [{**o, "value": close} if o["metric"] == "close" else o for o in observations]
    validator("valuation").validate(valuation(version, positions, observations))


def test_instrument_master_conforms():
    repository = FileInstrumentRepository()
    mappings = repository.mappings()
    assert mappings
    for mapping in mappings:
        validator("symbol_mapping").validate(mapping.model_dump(mode="json"))
        instrument = repository.get(mapping.instrument_id)
        validator("instrument").validate(instrument.model_dump(mode="json"))
