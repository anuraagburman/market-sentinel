"""Validated contract inputs and valuation responses; rounding occurs on serialization only."""

from datetime import datetime
from decimal import ROUND_HALF_EVEN, Decimal, localcontext
from typing import Annotated, Literal
from uuid import UUID

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    PlainSerializer,
    field_validator,
    model_validator,
)

DecimalString = Annotated[str, Field(pattern=r"^-?\d+(\.\d+)?$", strict=True)]
Currency = Annotated[str, Field(pattern=r"^[A-Z]{3}$", strict=True)]
Feed = Literal["iex", "sip", "delayed_15m", "eod", "fixture"]


def real_timestamp(value: str) -> str:
    datetime.fromisoformat(value)
    return value


UTCTimestamp = Annotated[
    str,
    Field(pattern=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,6})?Z$", strict=True),
    AfterValidator(real_timestamp),
]


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Cash(Record):
    amount: DecimalString
    currency: Currency


class PortfolioVersion(Record):
    id: UUID
    tenant_id: UUID
    base_currency: Currency
    imported_at: UTCTimestamp
    source_hash: Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]
    status: Literal["preview", "confirmed"]
    confirmed_at: UTCTimestamp | None = None
    previous_version_id: UUID | None = None
    cash: Cash | None = None

    @model_validator(mode="after")
    def confirmed_timestamp(self):
        if self.status == "confirmed" and self.confirmed_at is None:
            raise ValueError("Confirmed versions require confirmed_at")
        return self


class Position(Record):
    portfolio_version_id: UUID
    instrument_id: UUID
    display_symbol: str | None = None
    account_label: str | None = None
    quantity: DecimalString
    cost_basis: DecimalString | None
    currency: Currency

    @field_validator("quantity")
    @classmethod
    def positive_quantity(cls, value: str) -> str:
        if Decimal(value) <= 0:
            raise ValueError("Quantity must be positive")
        return value


class Observation(Record):
    id: UUID
    instrument_id: UUID
    metric: Literal["last_price", "close", "open", "high", "low", "volume", "fx_rate"]
    value: DecimalString
    unit: str
    feed: Feed
    session: Literal["regular", "pre", "post", "closed", "half_day"]
    adjustment: Literal["none", "split_adjusted", "split_and_dividend_adjusted"]
    observed_at: UTCTimestamp
    received_at: UTCTimestamp


def fixed(value: Decimal, places: str) -> str:
    with localcontext() as context:
        # Formatting must also support a large integral part after domain arithmetic.
        context.prec = max(34, value.adjusted() + len(places) + 2)
        return format(value.quantize(Decimal(places), rounding=ROUND_HALF_EVEN), "f")


Money = Annotated[Decimal, PlainSerializer(lambda v: fixed(v, "0.01"), return_type=str)]
Weight = Annotated[Decimal, PlainSerializer(lambda v: fixed(v, "0.000001"), return_type=str)]
Reason = Literal[
    "no_price",
    "conflicting_prices",
    "unit_mismatch",
    "currency_out_of_scope",
    "market_value_unavailable",
    "cost_basis_unknown",
    "no_priced_value",
    "cash_unknown",
    "positions_unpriced",
]


class Calculation(Record):
    kind: Literal["calculation"] = "calculation"
    value: Money
    basis: str


class WeightCalculation(Record):
    kind: Literal["calculation"] = "calculation"
    value: Weight
    basis: str


class Unavailable(Record):
    kind: Literal["unavailable"] = "unavailable"
    reason: Reason


Amount = Annotated[Calculation | Unavailable, Field(discriminator="kind")]
WeightAmount = Annotated[WeightCalculation | Unavailable, Field(discriminator="kind")]


class Price(Record):
    value: DecimalString
    observation_id: UUID
    observed_at: UTCTimestamp
    feed: Feed


class ValuedPosition(Record):
    instrument_id: UUID
    display_symbol: str | None
    quantity: DecimalString
    cost_basis: DecimalString | None
    price: Price | None
    market_value: Amount
    unrealized_pl: Amount
    weight: WeightAmount


class Totals(Record):
    priced_value: Amount
    cash: Amount
    total_value: Amount


class Coverage(Record):
    positions: int
    priced: int
    unpriced: int
    by_reason: dict[Reason, int]


class Valuation(Record):
    portfolio_version_id: UUID
    base_currency: Literal["USD"] = "USD"
    cutoff: datetime
    positions: list[ValuedPosition]
    totals: Totals
    coverage: Coverage
