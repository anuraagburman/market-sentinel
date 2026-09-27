"""Read-only valuation of confirmed portfolio snapshots at an explicit cutoff."""

from contextlib import asynccontextmanager
from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.domain.valuation import value_portfolio
from app.models.imports import Problem
from app.models.confirm import PortfolioResponse
from app.models.valuation import UTCTimestamp, Valuation
from app.routes.imports import ImportRoute
from app.services.imports import ImportProblem
from app.services.portfolios import (
    ObservationRepository,
    PortfolioRepository,
    get_observation_repository,
    get_portfolio_repository,
)


@asynccontextmanager
async def lifespan(app):
    for dependency in (get_portfolio_repository, get_observation_repository):
        loader = app.dependency_overrides.get(dependency, dependency)
        loader()
    yield


router = APIRouter(
    prefix="/portfolio-versions", tags=["portfolios"], route_class=ImportRoute, lifespan=lifespan
)
Portfolios = Annotated[PortfolioRepository, Depends(get_portfolio_repository)]
Observations = Annotated[ObservationRepository, Depends(get_observation_repository)]


@router.get(
    "/{id}/valuation",
    response_model=Valuation,
    responses={code: {"model": Problem} for code in (404, 409, 422)},
)
def get_valuation(
    id: str,
    cutoff: Annotated[UTCTimestamp, Query()],
    portfolios: Portfolios,
    observations: Observations,
) -> Valuation:
    """Compute USD values using closes observed and received by the UTC Z cutoff.

    Defaults use synthetic fixtures until confirmation and persistence exist.
    Missing values stay explicit; price age is left to downstream policy.
    """
    try:
        version_id = UUID(id)
    except ValueError:
        raise ImportProblem(
            "portfolio_version_not_found", "Portfolio version was not found.", 404
        ) from None
    version = portfolios.get(version_id)
    if version is None:
        raise ImportProblem("portfolio_version_not_found", "Portfolio version was not found.", 404)
    if version.status != "confirmed":
        raise ImportProblem(
            "portfolio_version_not_confirmed", "Portfolio version is not confirmed.", 409
        )
    if version.base_currency != "USD":
        raise ImportProblem(
            "base_currency_out_of_scope", "Only USD portfolio versions can be valued.", 422
        )
    instant = datetime.fromisoformat(cutoff)
    if instant < datetime.fromisoformat(version.confirmed_at):
        raise ImportProblem(
            "cutoff_before_confirmation", "Cutoff precedes portfolio confirmation.", 422
        )
    return value_portfolio(
        version, portfolios.positions(version_id), observations.observations(), instant
    )


@router.get(
    "/{id}",
    response_model=PortfolioResponse,
    response_model_exclude_unset=True,
    responses={404: {"model": Problem}},
)
def get_portfolio(id: str, portfolios: Portfolios) -> PortfolioResponse:
    try:
        version_id = UUID(id)
    except ValueError:
        raise ImportProblem(
            "portfolio_version_not_found", "Portfolio version was not found.", 404
        ) from None
    version = portfolios.get(version_id)
    if version is None:
        raise ImportProblem("portfolio_version_not_found", "Portfolio version was not found.", 404)
    return PortfolioResponse(
        portfolio_version=version, positions=list(portfolios.positions(version_id))
    )
