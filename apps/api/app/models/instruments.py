"""Effective-dated synthetic reference data and row resolution contracts."""

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class InstrumentModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Instrument(InstrumentModel):
    id: UUID
    name: str = Field(min_length=1)
    asset_type: Literal["common_stock", "preferred_stock"]
    currency: str = Field(pattern=r"^[A-Z]{3}$")


class SymbolMapping(InstrumentModel):
    symbol: str = Field(min_length=1)
    instrument_id: UUID
    valid_from: date
    valid_to: date | None

    def active(self, as_of: date) -> bool:
        return self.valid_from <= as_of and (self.valid_to is None or as_of < self.valid_to)


class ResolutionIssue(InstrumentModel):
    code: str
    field: str | None
    message: str


class Candidate(InstrumentModel):
    instrument_id: UUID
    display_symbol: str | None
    name: str
    asset_type: Literal["common_stock", "preferred_stock"]


ResolutionStatus = Literal["resolved", "ambiguous", "unresolved", "not_attempted"]


class Resolution(InstrumentModel):
    status: ResolutionStatus
    method: Literal["exact_symbol", "user_selected"] | None = None
    instrument_id: UUID | None = None
    display_symbol: str | None = None
    candidates: list[Candidate] = Field(default_factory=list)
    issues: list[ResolutionIssue] = Field(default_factory=list)
    as_of: date
    selected_at: datetime | None = None


class InstrumentMatch(InstrumentModel):
    instrument: Instrument
    mapping: SymbolMapping


class InstrumentSelection(InstrumentModel):
    instrument_id: UUID
