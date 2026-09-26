"""Exact effective-dated instrument lookup against temporary synthetic data."""

from datetime import date

from fastapi import APIRouter, Query

from app.domain.instruments import normalize_symbol
from app.models.imports import Problem
from app.models.instruments import InstrumentMatch
from app.routes.imports import Clock, ImportRoute, Instruments

router = APIRouter(prefix="/instruments", tags=["instruments"], route_class=ImportRoute)


@router.get("", response_model=list[InstrumentMatch], responses={422: {"model": Problem}})
def lookup_instruments(
    instruments: Instruments,
    clock: Clock,
    symbol: str = Query(..., min_length=1),
    as_of: date | None = None,
) -> list[InstrumentMatch]:
    """Return all exact active matches, never pick one of several candidates."""
    from datetime import UTC

    day = as_of if as_of is not None else clock().astimezone(UTC).date()
    mappings = sorted(
        (
            m
            for m in instruments.mappings()
            if m.symbol == normalize_symbol(symbol) and m.active(day)
        ),
        key=lambda m: (m.instrument_id, m.valid_from),
    )
    return [
        InstrumentMatch(instrument=instruments.get(m.instrument_id), mapping=m) for m in mappings
    ]
