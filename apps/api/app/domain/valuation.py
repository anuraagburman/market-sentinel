"""Cutoff-safe USD valuation. No I/O, clock, or binary floating point."""

from collections import Counter
from collections.abc import Sequence
from datetime import datetime, timedelta
from decimal import ROUND_HALF_EVEN, Decimal, localcontext

from app.models.valuation import (
    Calculation,
    Coverage,
    Observation,
    PortfolioVersion,
    Position,
    Price,
    Totals,
    Unavailable,
    Valuation,
    ValuedPosition,
    WeightCalculation,
)


def select_price(position: Position, observations: Sequence[Observation], cutoff: datetime):
    if position.currency != "USD":
        return None, Unavailable(reason="currency_out_of_scope")
    eligible = [
        observation
        for observation in observations
        if observation.instrument_id == position.instrument_id
        and observation.metric == "close"
        and observation.session in ("regular", "half_day")
        and observation.adjustment == "none"
        and datetime.fromisoformat(observation.observed_at) <= cutoff
        and datetime.fromisoformat(observation.received_at) <= cutoff
    ]
    if not eligible:
        return None, Unavailable(reason="no_price")
    latest = max(datetime.fromisoformat(o.observed_at) for o in eligible)
    candidates = [o for o in eligible if datetime.fromisoformat(o.observed_at) == latest]
    if len({Decimal(o.value) for o in candidates}) > 1:
        return None, Unavailable(reason="conflicting_prices")
    selected = min(candidates, key=lambda o: o.id)
    price = Price(
        value=selected.value,
        observation_id=selected.id,
        observed_at=selected.observed_at,
        feed=selected.feed,
    )
    if selected.unit != position.currency:
        return None, Unavailable(reason="unit_mismatch")
    return price, Calculation(
        value=Decimal(position.quantity) * Decimal(selected.value), basis="quantity × close"
    )


def value_portfolio(
    version: PortfolioVersion,
    positions: Sequence[Position],
    observations: Sequence[Observation],
    cutoff: datetime,
) -> Valuation:
    """Return unquantized values; response serialization alone rounds amounts.

    The route checks existence/status/base currency and confirmation cutoff. This
    guard also prevents accidental use of the pure function outside that boundary.
    """
    if cutoff.utcoffset() != timedelta(0):
        raise ValueError("Cutoff must be timezone-aware UTC")
    if version.status != "confirmed" or version.base_currency != "USD":
        raise ValueError("Valuation requires a confirmed USD version")
    if cutoff < datetime.fromisoformat(version.confirmed_at):
        raise ValueError("Cutoff precedes confirmation")
    with localcontext() as context:
        context.prec = 34
        context.rounding = ROUND_HALF_EVEN
        selected = [select_price(p, observations, cutoff) for p in positions]
        values = [amount.value for _, amount in selected if isinstance(amount, Calculation)]
        # Stable summation order also makes precision-boundary results independent of row order.
        priced_value = sum(sorted(values), Decimal(0))
        rows = []
        reasons = Counter()
        for position, (price, market_value) in zip(positions, selected, strict=True):
            if isinstance(market_value, Unavailable):
                reasons[market_value.reason] += 1
                pl = Unavailable(reason="market_value_unavailable")
                weight = Unavailable(reason="market_value_unavailable")
            else:
                pl = (
                    Unavailable(reason="cost_basis_unknown")
                    if position.cost_basis is None
                    else Calculation(
                        value=market_value.value - Decimal(position.cost_basis),
                        basis="market value − total cost basis",
                    )
                )
                weight = (
                    WeightCalculation(
                        value=market_value.value / priced_value,
                        basis="share of priced value (excludes cash and unpriced positions)",
                    )
                    if priced_value > 0
                    else Unavailable(reason="no_priced_value")
                )
            rows.append(
                ValuedPosition(
                    instrument_id=position.instrument_id,
                    display_symbol=position.display_symbol,
                    quantity=position.quantity,
                    cost_basis=position.cost_basis,
                    price=price,
                    market_value=market_value,
                    unrealized_pl=pl,
                    weight=weight,
                )
            )
        cash = (
            Unavailable(reason="cash_unknown")
            if version.cash is None
            else Unavailable(reason="currency_out_of_scope")
            if version.cash.currency != "USD"
            else Calculation(value=Decimal(version.cash.amount), basis="supplied USD cash")
        )
        total = (
            Unavailable(reason="positions_unpriced")
            if reasons
            else cash
            if isinstance(cash, Unavailable)
            else Calculation(
                value=priced_value + cash.value, basis="exact priced value + supplied USD cash"
            )
        )
        return Valuation(
            portfolio_version_id=version.id,
            cutoff=cutoff,
            positions=rows,
            totals=Totals(
                priced_value=Calculation(
                    value=priced_value, basis="exact sum of available market values, rounded once"
                )
                if values
                else Unavailable(reason="no_priced_value"),
                cash=cash,
                total_value=total,
            ),
            coverage=Coverage(
                positions=len(positions),
                priced=len(values),
                unpriced=len(positions) - len(values),
                by_reason=dict(reasons),
            ),
        )
