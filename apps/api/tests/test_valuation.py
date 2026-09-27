"""Offline valuation specification: exact arithmetic before response rounding."""

import json
from datetime import datetime
from decimal import Decimal, localcontext
from itertools import permutations
from pathlib import Path

import pytest

from app.domain.valuation import value_portfolio
from app.models.valuation import Observation, PortfolioVersion, Position

FIXTURES = Path(__file__).resolve().parents[3] / "evals/fixtures/portfolio"
CUTOFF = datetime.fromisoformat("2026-09-25T21:00:00+00:00")


def records():
    version = json.loads((FIXTURES / "portfolio_version.json").read_text())
    positions = json.loads((FIXTURES / "positions.json").read_text())
    observations = json.loads((FIXTURES / "observations.json").read_text())
    return version, positions, observations


def calculate(version, positions, observations):
    return value_portfolio(
        PortfolioVersion.model_validate(version),
        tuple(Position.model_validate(p) for p in positions),
        tuple(Observation.model_validate(o) for o in observations),
        CUTOFF,
    )


def unavailable(reason):
    return {"kind": "unavailable", "reason": reason}


def test_frozen_acceptance():
    result = calculate(*records()).model_dump(mode="json")
    assert result["coverage"] == {
        "positions": 19,
        "priced": 18,
        "unpriced": 1,
        "by_reason": {"no_price": 1},
    }
    assert result["totals"]["priced_value"]["value"] == "12812.83"
    assert result["totals"]["cash"] == unavailable("cash_unknown")
    assert result["totals"]["total_value"] == unavailable("positions_unpriced")
    expected = {
        "SYN01": ("6255.00", "455.00", "0.488183"),
        "SYN02": ("125.00", "15.00", "0.009756"),
        "SYN04": ("216.18", None, "0.016872"),
        "SYN05": ("139.75", "19.75", "0.010907"),
        "SYN19": ("412.65", "122.65", "0.032206"),
    }
    for row in result["positions"]:
        if row["display_symbol"] in expected:
            mv, pl, weight = expected[row["display_symbol"]]
            assert row["market_value"]["value"] == mv
            assert row["weight"]["value"] == weight
            assert (
                row["unrealized_pl"] == unavailable("cost_basis_unknown")
                if pl is None
                else row["unrealized_pl"]["value"] == pl
            )
    first, second, third, fourth = result["positions"][:4]
    assert first["price"]["value"] == "625.50"
    assert first["price"]["observation_id"] == records()[2][0]["id"]
    assert first["price"]["observed_at"] == "2026-09-25T20:00:00Z"
    assert first["price"]["feed"] == "fixture"
    assert second["quantity"] == "2.5"
    assert fourth["cost_basis"] is None
    assert third["price"] is None
    assert third["market_value"] == unavailable("no_price")
    for field in ("unrealized_pl", "weight"):
        assert third[field] == unavailable("market_value_unavailable")


@pytest.mark.parametrize(
    "change",
    [
        {"received_at": "2026-09-25T21:00:01Z"},
        {"observed_at": "2026-09-25T21:00:01Z"},
        {"session": "pre"},
        {"session": "post"},
        {"session": "closed"},
        {"metric": "last_price"},
        {"adjustment": "split_adjusted"},
        {"adjustment": "split_and_dividend_adjusted"},
    ],
)
def test_ineligible_close_falls_back_or_is_missing(change):
    v, p, o = records()
    bad = dict(o[0], **change)
    earlier = dict(o[0], id=o[1]["id"], value="2", observed_at="2026-09-24T20:00:00Z")
    assert calculate(v, p[:1], [bad, earlier]).positions[0].market_value.value == Decimal("20")
    assert calculate(v, p[:1], [bad]).positions[0].market_value.reason == "no_price"


def test_half_day_and_cutoff_inclusive():
    v, p, o = records()
    close = dict(
        o[0],
        session="half_day",
        observed_at="2026-09-25T21:00:00Z",
        received_at="2026-09-25T21:00:00Z",
    )
    assert calculate(v, p[:1], [close]).positions[0].market_value.value == Decimal("6255")


@pytest.mark.parametrize("value,reason", [("625.51", "conflicting_prices"), ("625.500", None)])
def test_latest_ties_are_order_independent(value, reason):
    v, p, o = records()
    other = dict(o[0], id=o[1]["id"], value=value)
    older = dict(o[0], id=o[2]["id"], observed_at="2026-09-24T20:00:00Z", value="1")
    for observations in permutations([o[0], other, older]):
        row = calculate(v, p[:1], observations).positions[0]
        if reason:
            assert row.price is None
            assert row.market_value.reason == reason
        else:
            assert str(row.price.observation_id) == o[0]["id"]


@pytest.mark.parametrize(
    "currency,unit,reason",
    [("CAD", "USD", "currency_out_of_scope"), ("USD", "CAD", "unit_mismatch")],
)
def test_currency_reasons(currency, unit, reason):
    v, p, o = records()
    result = calculate(v, [dict(p[0], currency=currency)], [dict(o[0], unit=unit)])
    assert result.positions[0].market_value.reason == reason
    assert result.coverage.by_reason == {reason: 1}
    assert result.totals.priced_value.reason == "no_priced_value"
    if currency == "CAD":
        assert result.positions[0].price is None
        assert (
            calculate(v, [dict(p[0], currency=currency)], []).positions[0].market_value.reason
            == reason
        )


@pytest.mark.parametrize(
    "cash,reason",
    [
        (None, "cash_unknown"),
        ({"amount": "1000.00", "currency": "CAD"}, "currency_out_of_scope"),
        ({"amount": "1000.00", "currency": "USD"}, None),
    ],
)
def test_cash_and_total_precedence(cash, reason):
    v, p, o = records()
    if cash is not None:
        v["cash"] = cash
    result = calculate(v, p[:1], o)
    if reason:
        assert result.totals.cash.reason == reason
        assert result.totals.total_value.reason == reason
    else:
        assert result.totals.total_value.value == Decimal("7255")
    assert calculate(v, p, o).totals.total_value.reason == "positions_unpriced"


def test_all_missing_and_zero_priced_denominator():
    v, p, o = records()
    result = calculate(v, p, [])
    assert result.totals.priced_value.reason == "no_priced_value"
    assert result.coverage.unpriced == 19
    assert all(row.weight.reason == "market_value_unavailable" for row in result.positions)
    zero = calculate(v, p[:1], [dict(o[0], value="0")])
    assert zero.positions[0].market_value.value == Decimal(0)
    assert zero.positions[0].weight.reason == "no_priced_value"
    assert zero.coverage.priced == 1


def test_permutations_scaling_and_exact_sum():
    v, p, o = records()
    baseline = calculate(v, p, o)
    reordered = calculate(v, list(reversed(p)), list(reversed(o)))
    assert reordered.positions == list(reversed(baseline.positions))
    assert reordered.totals == baseline.totals
    for k in ("0.1", "2", "7.25"):
        scaled = dict(p[0], quantity=str(Decimal(p[0]["quantity"]) * Decimal(k)))
        assert calculate(v, [scaled], o).positions[0].market_value.value == baseline.positions[
            0
        ].market_value.value * Decimal(k)
    assert baseline.totals.priced_value.value == sum(
        row.market_value.value
        for row in baseline.positions
        if row.market_value.kind == "calculation"
    )


def test_round_once_half_even_and_local_precision():
    v, p, o = records()
    positions = [dict(row, quantity="1", cost_basis="0.000") for row in p[:2]]
    observations = [dict(row, value="0.005") for row in o[:2]]
    with localcontext() as context:
        context.prec = 3
        result = calculate(v, positions, observations)
        response = result.model_dump(mode="json")
        assert context.prec == 3
    assert result.totals.priced_value.value == Decimal("0.010")
    assert [row["market_value"]["value"] for row in response["positions"]] == ["0.00", "0.00"]
    assert response["totals"]["priced_value"]["value"] == "0.01"
    assert response["positions"][0]["cost_basis"] == "0.000"
    assert (
        calculate(v, positions[:1], [dict(o[0], value="0.015")]).model_dump(mode="json")[
            "positions"
        ][0]["market_value"]["value"]
        == "0.02"
    )


def test_precision_34_is_independent_of_callers_rounding():
    from decimal import ROUND_UP

    v, p, o = records()
    positions = [dict(row, quantity="1") for row in p[:2]]
    observations = [dict(o[0], value="1"), dict(o[1], value="2")]
    with localcontext() as context:
        context.prec = 2
        context.rounding = ROUND_UP
        result = calculate(v, positions, observations)
        response = result.model_dump(mode="json")
        assert context.prec == 2
        assert context.rounding == ROUND_UP
    assert result.positions[0].weight.value == Decimal("0.3333333333333333333333333333333333")
    assert response["positions"][0]["weight"]["value"] == "0.333333"
    assert response["positions"][1]["weight"]["value"] == "0.666667"


def test_weight_half_even_ties():
    v, p, o = records()
    positions = [dict(row, quantity="1") for row in p[:2]]
    for first, second, expected in (("1", "127", "0.007812"), ("3", "125", "0.023438")):
        observations = [dict(o[0], value=first), dict(o[1], value=second)]
        response = calculate(v, positions, observations).model_dump(mode="json")
        assert response["positions"][0]["weight"]["value"] == expected
