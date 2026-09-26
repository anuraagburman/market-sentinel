from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel

from app.routes.imports import router as imports_router

app = FastAPI(title="Market Sentinel API", version="0.1.0")
app.include_router(imports_router)


class HealthResponse(BaseModel):
    status: Literal["ok"]


@app.get("/health", response_model=HealthResponse, tags=["health"])
def health() -> HealthResponse:
    """Process liveness only; does not assert dependency readiness."""
    return HealthResponse(status="ok")
