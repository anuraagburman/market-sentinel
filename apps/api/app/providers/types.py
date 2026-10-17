"""Provider-independent result and provenance helpers."""

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from uuid import NAMESPACE_URL, UUID, uuid5

from app.providers.transport import ErrorKind


@dataclass(frozen=True)
class Error:
    kind: ErrorKind
    instrument_id: UUID


@dataclass
class Result[T]:
    records: list[T] = field(default_factory=list)
    errors: list[Error] = field(default_factory=list)
    requested: tuple[str, ...] = ()
    covered: tuple[str, ...] = ()
    excluded: tuple[str, ...] = ()
    complete: bool = False


def utc(value: datetime) -> str:
    if value.utcoffset() != timedelta(0):
        raise ValueError("UTC required")
    return value.isoformat().replace("+00:00", "Z")


def timestamp(value: str) -> datetime:
    if not isinstance(value, str) or "T" not in value:
        raise ValueError("Timestamp required")
    parsed = datetime.fromisoformat(value)
    utc(parsed)
    return parsed


def decimal(value, *, positive=False):
    if isinstance(value, (bool, float)) or value is None:
        raise ValueError("Decimal required")
    try:
        number = Decimal(value)
    except (InvalidOperation, TypeError):
        raise ValueError("Decimal required") from None
    if not number.is_finite() or number < 0 or (positive and number == 0):
        raise ValueError("Invalid value")
    # Fixed-point, trailing fractional zeros removed without Decimal context rounding.
    result = format(number, "f")
    return (result.rstrip("0").rstrip(".") if "." in result else result) if number else "0"


def canonical(record):
    return json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def identity(record):
    return uuid5(NAMESPACE_URL, canonical(record))


def digest(record):
    return "sha256:" + hashlib.sha256(canonical(record).encode("utf-8")).hexdigest()
