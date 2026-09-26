"""Invalid reference data must fail atomically, naming the offending record."""

import json

import pytest

from app.services.instruments import MASTER, FileInstrumentRepository


@pytest.mark.parametrize(
    "kind", ["duplicate", "equal_dates", "reverse_dates", "unknown", "overlap"]
)
def test_reject_invalid_master(tmp_path, kind):
    instruments = json.loads((MASTER / "instruments.json").read_text())
    mappings = json.loads((MASTER / "symbol_mappings.json").read_text())
    if kind == "duplicate":
        instruments.append(instruments[0])
    elif kind in {"equal_dates", "reverse_dates"}:
        mappings[0]["valid_to"] = "2020-01-01" if kind == "equal_dates" else "2019-12-31"
    elif kind == "unknown":
        mappings[0]["instrument_id"] = "00000000-0000-4000-8000-999999999999"
    else:
        mappings.append(mappings[0] | {"valid_from": "2025-01-01"})
    (tmp_path / "instruments.json").write_text(json.dumps(instruments))
    (tmp_path / "symbol_mappings.json").write_text(json.dumps(mappings))
    with pytest.raises(ValueError, match="00000000-"):
        FileInstrumentRepository(tmp_path)


def test_adjacent_intervals_and_aliases_allowed(tmp_path):
    instruments = json.loads((MASTER / "instruments.json").read_text())
    first = {
        "symbol": "ALIAS",
        "instrument_id": instruments[0]["id"],
        "valid_from": "2020-01-01",
        "valid_to": "2026-01-01",
    }
    mappings = [
        first,
        first | {"valid_from": "2026-01-01", "valid_to": None},
        first | {"symbol": "SECOND"},
    ]
    (tmp_path / "instruments.json").write_text(json.dumps(instruments))
    (tmp_path / "symbol_mappings.json").write_text(json.dumps(mappings))
    assert len(FileInstrumentRepository(tmp_path).mappings()) == 3
