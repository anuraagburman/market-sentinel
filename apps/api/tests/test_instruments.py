"""Effective dates and exact matching must never silently guess an identity."""

from datetime import date

import pytest

from app.domain.instruments import resolve
from app.services.instruments import FileInstrumentRepository


@pytest.fixture
def master():
    return FileInstrumentRepository()


def result(master, symbol, day="2026-09-25", currency="USD"):
    return resolve(symbol, currency, date.fromisoformat(day), master)


@pytest.mark.parametrize("symbol", ["SYN01", "syn01", " SYN01 "])
def test_exact_symbol(master, symbol):
    resolution = result(master, symbol)
    assert resolution.status == "resolved"
    assert str(resolution.instrument_id).endswith("000000000001")
    assert resolution.method == "exact_symbol"
    assert resolution.display_symbol == "SYN01"
    assert resolution.issues == []


def test_ambiguity_and_no_fuzzy_matching(master):
    resolution = result(master, "SYN-AMB")
    assert resolution.status == "ambiguous"
    assert resolution.instrument_id is None
    assert [c.name for c in resolution.candidates] == ["Synthela 02", "Synthela 02 Preferred"]
    assert [c.display_symbol for c in resolution.candidates] == ["SYN02", "SYN02P"]
    for symbol in ["SYN-TYPO", "SYN.01", "ſyn01"]:
        assert result(master, symbol).issues[0].code == "symbol_not_found"
    assert result(master, None).status == "not_attempted"


def test_ticker_change_boundary(master):
    before = result(master, "SYN-OLD20", "2026-05-31")
    assert before.status == "resolved"
    assert before.display_symbol == "SYN-OLD20"
    after = result(master, "SYN-OLD20", "2026-06-01")
    assert after.status == "unresolved"
    assert after.issues[0].code == "symbol_retired"
    assert after.candidates[0].display_symbol == "SYN20"
    assert "SYN20" in after.issues[0].message
    assert result(master, "SYN20", "2026-05-31").status == "unresolved"


def test_reuse_and_currency(master):
    before = result(master, "SYN-RE", "2026-06-30", "CAD")
    after = result(master, "SYN-RE", "2026-07-01")
    assert before.instrument_id != after.instrument_id
    assert before.issues == []
    assert after.status == "resolved"
    assert after.issues[0].code == "symbol_reassigned"
    assert "Synthela 21" in after.issues[0].message
    mismatch = result(master, "SYN21")
    assert mismatch.status == "resolved"
    assert mismatch.issues[0].code == "currency_mismatch"
    assert "warning" in mismatch.issues[0].message.lower()
    assert result(master, "SYN21", currency=None).issues == []
