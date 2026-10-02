"""Atomic temporary portfolio storage and validated synthetic observations."""

import json
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Protocol
from threading import RLock

from app.models.confirm import ConfirmationRecord
from uuid import UUID

from app.models.valuation import Observation, PortfolioVersion, Position

PORTFOLIO = Path(__file__).resolve().parents[4] / "evals/fixtures/portfolio"


class PortfolioRepository(Protocol):
    def get(self, version_id: UUID) -> PortfolioVersion | None: ...

    def positions(self, version_id: UUID) -> tuple[Position, ...]: ...

    def confirm(
        self, record: ConfirmationRecord, version: PortfolioVersion, positions: tuple[Position, ...]
    ) -> ConfirmationRecord: ...

    def by_import(self, import_id: UUID) -> ConfirmationRecord | None: ...

    def by_idempotency_key(self, key: str) -> ConfirmationRecord | None: ...

    def latest(self, tenant_id: UUID) -> PortfolioVersion | None: ...


class ObservationRepository(Protocol):
    def observations(self) -> tuple[Observation, ...]: ...


def read_array(directory: Path, name: str) -> list:
    data = json.loads((directory / f"{name}.json").read_text())
    if not isinstance(data, list):
        raise ValueError(f"{name} must be an array")
    return data


class FilePortfolioRepository:
    def __init__(self, directory: Path = PORTFOLIO):
        version = PortfolioVersion.model_validate_json(
            (directory / "portfolio_version.json").read_text()
        )
        positions = tuple(Position.model_validate(p) for p in read_array(directory, "positions"))
        seen = set()
        for position in positions:
            if position.portfolio_version_id != version.id:
                raise ValueError("Unknown portfolio_version_id in position")
            key = (position.portfolio_version_id, position.instrument_id)
            if key in seen:
                raise ValueError("Duplicate position for portfolio version and instrument")
            seen.add(key)
        self._version = version
        self._positions = positions

    def get(self, version_id: UUID) -> PortfolioVersion | None:
        return self._version if version_id == self._version.id else None

    def positions(self, version_id: UUID) -> tuple[Position, ...]:
        return self._positions if version_id == self._version.id else ()


class InMemoryPortfolioRepository:
    """Atomic process-local store, replaced by Postgres in T-012.

    The lock covers uniqueness, latest-version selection, and all writes. Reads
    are copies. T-012 must enforce unique import_id and idempotency_key and select
    the tenant's predecessor inside the same transaction as the insert.
    """

    def __init__(self, seed: FilePortfolioRepository | None = None):
        self._lock = RLock()
        self._versions = {}
        self._positions = {}
        self._imports = {}
        self._keys = {}
        self._latest = {}
        if seed is not None:
            version = seed._version.model_copy(deep=True)
            self._versions[version.id] = version
            self._positions[version.id] = tuple(
                p.model_copy(deep=True) for p in seed.positions(version.id)
            )
            self._latest[version.tenant_id] = version.id

    def get(self, version_id: UUID) -> PortfolioVersion | None:
        with self._lock:
            value = self._versions.get(version_id)
            return value.model_copy(deep=True) if value is not None else None

    def positions(self, version_id: UUID) -> tuple[Position, ...]:
        with self._lock:
            return tuple(p.model_copy(deep=True) for p in self._positions.get(version_id, ()))

    def by_import(self, import_id: UUID) -> ConfirmationRecord | None:
        with self._lock:
            value = self._imports.get(import_id)
            return value.model_copy(deep=True) if value is not None else None

    def by_idempotency_key(self, key: str) -> ConfirmationRecord | None:
        with self._lock:
            value = self._keys.get(key)
            return value.model_copy(deep=True) if value is not None else None

    def latest(self, tenant_id: UUID) -> PortfolioVersion | None:
        with self._lock:
            return self.get(self._latest.get(tenant_id))

    def confirm(
        self, record: ConfirmationRecord, version: PortfolioVersion, positions: tuple[Position, ...]
    ) -> ConfirmationRecord:
        with self._lock:
            # A losing request never writes, including when a key is used on another import.
            existing = self._keys.get(record.idempotency_key) or self._imports.get(record.import_id)
            if existing is not None:
                return existing.model_copy(deep=True)
            record = ConfirmationRecord.model_validate(record.model_dump())
            version = PortfolioVersion.model_validate(version.model_dump(exclude_unset=True))
            positions = tuple(
                Position.model_validate(p.model_dump(exclude_unset=True)) for p in positions
            )
            if version.id != record.portfolio_version_id or version.id in self._versions:
                raise ValueError("Invalid or existing version identity")
            if version.status != "confirmed" or datetime.fromisoformat(
                version.confirmed_at
            ) < datetime.fromisoformat(version.imported_at):
                raise ValueError("Invalid confirmed version")
            if not positions or any(p.portfolio_version_id != version.id for p in positions):
                raise ValueError("Positions must belong to the confirmed version")
            if len({p.instrument_id for p in positions}) != len(positions):
                raise ValueError("Duplicate instrument")
            # Derive predecessor under the write lock, including concurrent different imports.
            version = version.model_copy(
                update={"previous_version_id": self._latest.get(version.tenant_id)}
            )
            self._versions[version.id] = version
            self._positions[version.id] = positions
            self._imports[record.import_id] = record
            self._keys[record.idempotency_key] = record
            self._latest[version.tenant_id] = version.id
            return record.model_copy(deep=True)


class FileObservationRepository:
    def __init__(self, directory: Path = PORTFOLIO):
        observations = tuple(
            Observation.model_validate(o) for o in read_array(directory, "observations")
        )
        if len({o.id for o in observations}) != len(observations):
            raise ValueError("Duplicate observation id")
        self._observations = observations

    def observations(self) -> tuple[Observation, ...]:
        return self._observations


@lru_cache(maxsize=1)
def get_portfolio_repository() -> PortfolioRepository:
    return InMemoryPortfolioRepository(FilePortfolioRepository())


@lru_cache(maxsize=1)
def get_observation_repository() -> ObservationRepository:
    return FileObservationRepository()
