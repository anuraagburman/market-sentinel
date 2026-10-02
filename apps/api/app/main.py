import logging
import os
from contextlib import asynccontextmanager
from typing import Literal

from starlette.concurrency import run_in_threadpool
from app.db.engine import check_startup, dispose_engine, get_engine

from fastapi import FastAPI
from pydantic import BaseModel

from app.routes.imports import router as imports_router
from app.routes.instruments import router as instruments_router
from app.routes.portfolios import router as portfolios_router


@asynccontextmanager
async def lifespan(app):
    try:
        if os.environ.get("DATABASE_URL"):
            await run_in_threadpool(lambda: check_startup(get_engine()))
        else:
            logging.getLogger(__name__).warning(
                "DATABASE_URL unset; using process-local memory stores"
            )
        yield
    finally:
        await run_in_threadpool(dispose_engine)


app = FastAPI(title="Market Sentinel API", version="0.1.0", lifespan=lifespan)
app.include_router(imports_router)
app.include_router(instruments_router)
app.include_router(portfolios_router)


class HealthResponse(BaseModel):
    status: Literal["ok"]


@app.get("/health", response_model=HealthResponse, tags=["health"])
def health() -> HealthResponse:
    """Process liveness only; does not assert dependency readiness."""
    return HealthResponse(status="ok")
