"""Synthetic, temporary reference repository until provider reference data (T-008)."""

import json
from functools import lru_cache
from pathlib import Path
from typing import Protocol
from uuid import UUID

from app.models.instruments import Instrument, SymbolMapping

MASTER = Path(__file__).resolve().parents[4] / "evals/fixtures/instruments"


class InstrumentRepository(Protocol):
    def get(self, instrument_id: UUID) -> Instrument | None: ...

    def mappings(self) -> tuple[SymbolMapping, ...]: ...


class FileInstrumentRepository:
    """Load and validate the entire master before exposing any records.

    Aliases may coexist. Only overlapping intervals for the same instrument AND
    symbol are invalid; a symbol shared by instruments represents ambiguity.
    """

    def __init__(self, directory: Path = MASTER):
        instruments = [
            Instrument.model_validate(item) for item in self._read(directory, "instruments")
        ]
        mappings = [
            SymbolMapping.model_validate(item) for item in self._read(directory, "symbol_mappings")
        ]
        by_id = {}
        for instrument in instruments:
            if instrument.id in by_id:
                raise ValueError(f"Duplicate instrument id: {instrument.id}")
            by_id[instrument.id] = instrument
        intervals: dict[tuple[UUID, str], list[SymbolMapping]] = {}
        for mapping in mappings:
            label = f"{mapping.symbol} / {mapping.instrument_id} / {mapping.valid_from}"
            if mapping.instrument_id not in by_id:
                raise ValueError(f"Unknown instrument in mapping: {label}")
            if mapping.valid_to is not None and mapping.valid_to <= mapping.valid_from:
                raise ValueError(f"Invalid mapping date interval: {label}")
            if mapping.symbol != mapping.symbol.strip() or any(
                "a" <= c <= "z" for c in mapping.symbol
            ):
                raise ValueError(f"Mapping symbol must be trimmed and ASCII-uppercase: {label}")
            key = (mapping.instrument_id, mapping.symbol)
            for prior in intervals.get(key, []):
                if (prior.valid_to is None or mapping.valid_from < prior.valid_to) and (
                    mapping.valid_to is None or prior.valid_from < mapping.valid_to
                ):
                    raise ValueError(f"Overlapping mapping: {label}")
            intervals.setdefault(key, []).append(mapping)
        self._instruments = by_id
        self._mappings = tuple(mappings)

    @staticmethod
    def _read(directory: Path, name: str) -> list:
        path = directory / f"{name}.json"
        data = json.loads(path.read_text())
        if not isinstance(data, list):
            raise ValueError(f"Master must be an array: {path}")
        return data

    def get(self, instrument_id: UUID) -> Instrument | None:
        return self._instruments.get(instrument_id)

    def mappings(self) -> tuple[SymbolMapping, ...]:
        return self._mappings


@lru_cache(maxsize=1)
def get_instrument_repository() -> InstrumentRepository:
    return FileInstrumentRepository()
