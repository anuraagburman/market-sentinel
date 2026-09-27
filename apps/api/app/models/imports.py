"""Import preview API models; decimal values remain JSON strings."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.instruments import Resolution, ResolutionStatus

FieldName = Literal["symbol", "quantity", "cost_basis", "currency"]
RowStatus = Literal["ok", "warning", "error"]


class ImportModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ImportIssue(ImportModel):
    code: str
    field: str | None
    message: str


class ImportColumn(ImportModel):
    detected: str
    mapped: FieldName | None
    unknown: bool


class ParsedHolding(ImportModel):
    symbol: str | None
    quantity: str | None
    cost_basis: str | None
    currency: str | None


class ImportRow(ImportModel):
    row_number: int
    raw: list[str]
    parsed: ParsedHolding
    status: RowStatus
    issues: list[ImportIssue]
    resolution: Resolution


class ImportSummary(ImportModel):
    by_status: dict[RowStatus, int]
    by_code: dict[str, int]
    by_resolution: dict[ResolutionStatus, int]


class ImportPreview(ImportModel):
    id: UUID
    file_sha256: str
    received_at: datetime
    columns: list[ImportColumn]
    rows: list[ImportRow]
    summary: ImportSummary


class Problem(ImportModel):
    code: str
    message: str
