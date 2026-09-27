"""Validated synthetic snapshots until portfolio confirmation/persistence exists."""

import json
from functools import lru_cache
from pathlib import Path
from typing import Protocol
from uuid import UUID

from app.models.valuation import Observation, PortfolioVersion, Position

PORTFOLIO = Path(__file__).resolve().parents[4] / "evals/fixtures/portfolio"


class PortfolioRepository(Protocol):
    def get(self, version_id: UUID) -> PortfolioVersion | None: ...

    def positions(self, version_id: UUID) -> tuple[Position, ...]: ...


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
    return FilePortfolioRepository()


@lru_cache(maxsize=1)
def get_observation_repository() -> ObservationRepository:
    return FileObservationRepository()
