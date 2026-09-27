"""Confirmation responses and internal immutable receipt."""

from typing import Literal
from uuid import UUID

from pydantic import Field

from app.models.valuation import PortfolioVersion, Position, Record, UTCTimestamp


class Blocker(Record):
    row_number: int | None
    code: str
    message: str


class Readiness(Record):
    confirmable: bool
    blockers: list[Blocker] = Field(default_factory=list)


class Confirmation(Record):
    portfolio_version_id: UUID
    confirmed_at: UTCTimestamp


class ExcludedRow(Record):
    row_number: int
    reason: Literal["user_excluded", "blank_row"]


class ConfirmationRecord(Record):
    import_id: UUID
    idempotency_key: str
    request_fingerprint: str
    portfolio_version_id: UUID
    excluded_rows: tuple[ExcludedRow, ...]


class ConfirmRequest(Record):
    preview_revision: int = Field(ge=0, strict=True)


class PortfolioResponse(Record):
    portfolio_version: PortfolioVersion
    positions: list[Position]


class ConfirmResponse(PortfolioResponse):
    import_id: UUID
    excluded_rows: list[ExcludedRow]
