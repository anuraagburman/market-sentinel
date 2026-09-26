from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Market Sentinel API", version="0.1.0")


class HealthResponse(BaseModel):
    status: Literal["ok"]


@app.get("/health", response_model=HealthResponse, tags=["health"])
def health() -> HealthResponse:
    """Process liveness only; does not assert dependency readiness."""
    return HealthResponse(status="ok")
