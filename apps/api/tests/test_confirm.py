"""Pure confirm rules preserve reviewed identity and exact parsed values."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.domain.confirm import build_portfolio, readiness
from app.services.imports import InMemoryPreviewRepository, create_preview
from app.services.portfolios import PORTFOLIO

NOW = datetime(2026, 9, 25, 20, 30, tzinfo=UTC)


def preview(content=b"symbol,quantity,cost_basis,currency\nSYN01,10.00,,CAD\n"):
    return create_preview(content, InMemoryPreviewRepository(), clock=lambda: NOW)


def ids(p):
    return {r.resolution.instrument_id for r in p.rows if r.resolution.instrument_id}


def test_fixture_blockers_are_in_row_order():
    p = preview((PORTFOLIO / "holdings.csv").read_bytes())
    result = readiness(p.rows, ids(p))
    assert not result.confirmable
    assert [(b.row_number, b.code) for b in result.blockers] == [
        (1, "duplicate_instrument"),
        (2, "row_unresolved"),
        (5, "row_unresolved"),
        (20, "duplicate_instrument"),
    ]


def test_errors_missing_instruments_duplicates_and_exclusions():
    p = preview(b"symbol,quantity,cost_basis,currency\nSYN01,-1,,USD\nSYN01,2,,USD\n")
    assert [(b.row_number, b.code) for b in readiness(p.rows, set()).blockers] == [
        (1, "row_has_errors"),
        (1, "instrument_missing"),
        (1, "duplicate_instrument"),
        (2, "instrument_missing"),
        (2, "duplicate_instrument"),
    ]
    p.rows[0].excluded = True
    assert readiness(p.rows, ids(p)).confirmable
    p.rows[1].excluded = True
    assert [(b.row_number, b.code) for b in readiness(p.rows, ids(p)).blockers] == [
        (None, "no_included_rows")
    ]


def test_mapping_preserves_strings_null_and_currency():
    p = preview()
    version_id, previous = uuid4(), uuid4()
    version, positions = build_portfolio(p, version_id, NOW + timedelta(minutes=30), previous)
    assert version.id == version_id
    assert version.previous_version_id == previous
    assert version.imported_at == "2026-09-25T20:30:00Z"
    assert version.confirmed_at == "2026-09-25T21:00:00Z"
    assert version.source_hash == "sha256:" + p.file_sha256
    assert "cash" not in version.model_dump(exclude_unset=True)
    assert positions[0].model_dump(exclude_unset=True) == {
        "portfolio_version_id": version_id,
        "instrument_id": p.rows[0].resolution.instrument_id,
        "display_symbol": "SYN01",
        "quantity": "10.00",
        "cost_basis": None,
        "currency": "CAD",
    }


@pytest.mark.parametrize("instant", [NOW - timedelta(seconds=1), NOW.replace(tzinfo=None)])
def test_invalid_clock_rejected(instant):
    with pytest.raises(ValueError):
        build_portfolio(preview(), uuid4(), instant, None)
