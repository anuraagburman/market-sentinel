import json
from datetime import datetime
from decimal import Decimal, localcontext
from pathlib import Path

from app.domain.valuation import value_portfolio
from app.models.valuation import Observation, PortfolioVersion, Position
from app.policy.exposure import Exposure, exposure_for

FIXTURES = Path(__file__).resolve().parents[3] / "evals/fixtures/portfolio"


def valuation():
    def load(name):
        return json.loads((FIXTURES / name).read_text())

    return value_portfolio(
        PortfolioVersion.model_validate(load("portfolio_version.json")),
        tuple(Position.model_validate(p) for p in load("positions.json")),
        tuple(Observation.model_validate(o) for o in load("observations.json")),
        datetime.fromisoformat("2026-09-25T21:00:00+00:00"),
    )


def weights():
    return {
        str(p.instrument_id): p.weight.value
        for p in valuation().positions
        if p.weight.kind != "unavailable"
    }


def event(*suffixes):
    return {"instrument_ids": [f"00000000-0000-4000-8000-000000000{s}" for s in suffixes]}


def test_held_instrument_carries_its_valuation_weight():
    rows = weights()
    exposure = exposure_for(event("001"), valuation())
    assert exposure == Exposure(weight=rows["00000000-0000-4000-8000-000000000001"], held=True)
    assert Decimal(0) < exposure.weight < Decimal(1)


def test_weights_of_several_held_instruments_are_summed():
    rows = weights()
    exposure = exposure_for(event("001", "002"), valuation())
    with localcontext() as context:
        context.prec = 34
        expected = sum(rows[i] for i in event("001", "002")["instrument_ids"])
    assert exposure.weight == expected


def test_instrument_not_held_is_a_real_zero():
    assert exposure_for(event("999"), valuation()) == Exposure(weight=Decimal(0), held=False)


def test_held_instrument_without_market_value_is_unavailable_not_zero():
    assert exposure_for(event("003"), valuation()) is None
    assert exposure_for(event("001", "003"), valuation()) is None
