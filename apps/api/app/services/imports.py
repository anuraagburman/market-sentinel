"""CSV validation and instrument resolution; cells are data only, never formulas."""

import csv
import hashlib
import io
import re
from collections import Counter
from collections.abc import Callable
from contextlib import contextmanager
from datetime import UTC, datetime
from decimal import Decimal
from threading import RLock
from typing import Protocol
from uuid import UUID, uuid4

from app.domain.confirm import build_portfolio, excluded_rows, is_blank, readiness
from app.models.confirm import Confirmation, ConfirmationRecord, ConfirmResponse
from app.services.portfolios import PortfolioRepository

from app.models.imports import ImportPreview, ImportRow
from app.domain.instruments import currency_issues, display_symbol, resolve
from app.models.instruments import Resolution
from app.services.instruments import InstrumentRepository, get_instrument_repository

MAX_BYTES = 1024 * 1024
MAX_ROWS = 1000
FIELDS = ("symbol", "quantity", "cost_basis", "currency")
REQUIRED = ("symbol", "quantity", "currency")
PLAIN_DECIMAL = re.compile(r"-?(?:[0-9]+(?:\.[0-9]+)?|\.[0-9]+)\Z")
# Permit a cell up to the total upload limit; the default CSV limit is smaller.
csv.field_size_limit(MAX_BYTES)


class ImportProblem(Exception):
    def __init__(self, code: str, message: str, status_code: int = 422, **details):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details


def formula_like(value: str) -> bool:
    trimmed = value.strip()
    return (
        value.startswith(("\t", "\r"))
        or trimmed.startswith(("=", "+", "@"))
        or (trimmed.startswith("-") and not PLAIN_DECIMAL.fullmatch(trimmed))
    )


def parse_csv(content: bytes) -> dict:
    """Return deterministic preview data, before identity/time or storage is added.

    Raw cells are ordered arrays, retaining even extra cells and duplicate unknown
    column names. Header mappings use the same order. Uneven rows remain visible
    with a row-level error; duplicate mapped headers are rejected as ambiguous.
    """
    if len(content) > MAX_BYTES:
        raise ImportProblem("file_too_large", "CSV exceeds the 1 MiB limit.", 413)
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ImportProblem("invalid_encoding", "CSV must be UTF-8 encoded.") from exc
    if "\x00" in text:
        raise ImportProblem("invalid_csv", "CSV must not contain NUL bytes.")
    reader = csv.reader(io.StringIO(text, newline=""), strict=True)
    try:
        headers = next(reader, [])
        mapped = [h.strip().lower() if h.strip().lower() in FIELDS else None for h in headers]
        missing = [f for f in REQUIRED if f not in mapped]
        if missing:
            raise ImportProblem(
                "missing_column", f"Missing required column(s): {', '.join(missing)}."
            )
        if any(mapped.count(f) > 1 for f in FIELDS):
            raise ImportProblem("duplicate_column", "A recognized column appears more than once.")
        columns = [
            {"detected": h, "mapped": m, "unknown": m is None}
            for h, m in zip(headers, mapped, strict=True)
        ]
        rows = []
        seen = {}
        for number, raw in enumerate(reader, 1):
            if number > MAX_ROWS:
                raise ImportProblem("too_many_rows", "CSV exceeds the 1,000 data-row limit.")
            if not raw:
                rows.append(
                    {
                        "row_number": number,
                        "raw": raw,
                        "parsed": {field: None for field in FIELDS},
                        "status": "warning",
                        "resolution": "pending",
                        "issues": [
                            {
                                "code": "blank_row",
                                "field": None,
                                "message": "Blank row retained for review.",
                            }
                        ],
                    }
                )
                continue
            issues = []
            has_error = False

            def issue(code, field, message, *, warning=False):
                nonlocal has_error
                has_error |= not warning
                issues.append({"code": code, "field": field, "message": message})

            if len(raw) != len(headers):
                issue(
                    "column_count_mismatch",
                    None,
                    "Cell count does not match the header; review this row.",
                )
            unsafe = set()
            for index, value in enumerate(raw):
                if formula_like(value):
                    unsafe.add(index)
                    field = (mapped[index] or headers[index]) if index < len(headers) else None
                    issue(
                        "formula_like_value",
                        field,
                        "Formula-like cell is not accepted; supply a literal value.",
                    )
            unsafe_fields = {mapped[index] for index in unsafe if index < len(mapped)}
            cells = {
                field: raw[index].strip() if index < len(raw) and index not in unsafe else None
                for index, field in enumerate(mapped)
                if field is not None
            }
            parsed = {field: cells.get(field) or None for field in FIELDS}
            if "symbol" not in unsafe_fields and not parsed["symbol"]:
                issue("missing_symbol", "symbol", "Symbol is required.")
            for field in ("quantity", "cost_basis"):
                if field in unsafe_fields:
                    continue
                value = cells.get(field)
                if field == "cost_basis" and not value:
                    parsed[field] = None
                    issue("missing_cost_basis", field, "Cost basis is unavailable.", warning=True)
                elif value is None or not PLAIN_DECIMAL.fullmatch(value):
                    parsed[field] = None
                    issue(
                        "invalid_decimal",
                        field,
                        "Use a plain decimal without grouping, exponents, or currency symbols.",
                    )
                else:
                    decimal = Decimal(value)
                    parsed[field] = format(decimal, "f")
                    if field == "cost_basis" and decimal < 0:
                        issue(
                            "negative_cost_basis",
                            field,
                            "Cost basis must be non-negative; review this value.",
                        )
                    if field == "quantity" and decimal <= 0:
                        issue(
                            "non_positive_quantity",
                            field,
                            "Quantity must be positive; shorts require review.",
                        )
            if "currency" not in unsafe_fields and not re.fullmatch(
                r"[A-Z]{3}", parsed["currency"] or ""
            ):
                parsed["currency"] = None
                issue("invalid_currency", "currency", "Currency must be three uppercase letters.")
            if not has_error:
                key = (
                    parsed["symbol"],
                    Decimal(parsed["quantity"]),
                    Decimal(parsed["cost_basis"]) if parsed["cost_basis"] is not None else None,
                    parsed["currency"],
                )
                if key in seen:
                    issue(
                        "duplicate_row",
                        None,
                        f"Same holding as row {seen[key]}; kept separately pending review.",
                        warning=True,
                    )
                else:
                    seen[key] = number
            rows.append(
                {
                    "row_number": number,
                    "raw": raw,
                    "parsed": parsed,
                    "status": "error" if has_error else "warning" if issues else "ok",
                    "issues": issues,
                    "resolution": "pending",
                }
            )
    except csv.Error as exc:
        raise ImportProblem("invalid_csv", "CSV has invalid quoting or an oversized cell.") from exc
    counts = Counter(row["status"] for row in rows)
    return {
        "file_sha256": hashlib.sha256(content).hexdigest(),
        "columns": columns,
        "rows": rows,
        "summary": {
            "by_status": {status: counts[status] for status in ("ok", "warning", "error")},
            "by_code": dict(Counter(i["code"] for row in rows for i in row["issues"])),
        },
    }


class PreviewRepository(Protocol):
    """Preview snapshots and per-import decision transactions."""

    def save(self, preview: ImportPreview) -> None: ...

    def get(self, preview_id: UUID) -> ImportPreview | None: ...

    def import_transaction(self, import_id: UUID, portfolios: PortfolioRepository): ...


class InMemoryPreviewRepository:
    """Temporary process-local storage: lost on restart, not shared across workers.

    Copies isolate stored previews from mutations by callers. No auth/tenant or
    persistence semantics are implied; this repository is for the preview MVP.
    """

    def __init__(self):
        self._previews: dict[UUID, dict] = {}
        self._guard = RLock()
        self._locks = {}

    @contextmanager
    def import_transaction(self, import_id, portfolios):
        with self._guard:
            lock = self._locks.setdefault(import_id, RLock())
        with lock:
            tx = InMemoryPreviewRepository()
            preview = self.get(import_id)
            if preview is not None:
                tx.save(preview)
            tx.portfolios = portfolios
            yield tx
            updated = tx.get(import_id)
            if updated is not None:
                self.save(updated)

    def save(self, preview: ImportPreview) -> None:
        self._previews[preview.id] = preview.model_dump(exclude={"readiness", "confirmation"})

    def get(self, preview_id: UUID) -> ImportPreview | None:
        preview = self._previews.get(preview_id)
        return ImportPreview.model_validate(preview) if preview is not None else None


def utc_now() -> datetime:
    return datetime.now(UTC)


def create_preview(
    content: bytes,
    repository: PreviewRepository,
    instruments: InstrumentRepository | None = None,
    clock: Callable[[], datetime] = utc_now,
) -> ImportPreview:
    received_at = clock()
    if received_at.tzinfo is None or received_at.utcoffset() is None:
        raise ValueError("Preview clock must return a timezone-aware datetime")
    received_at = received_at.astimezone(UTC)
    data = parse_csv(content)
    instruments = instruments if instruments is not None else get_instrument_repository()
    for row in data["rows"]:
        symbol = row["parsed"]["symbol"]
        if any(i["code"] == "formula_like_value" and i["field"] == "symbol" for i in row["issues"]):
            symbol = None
        row["excluded"] = any(i["code"] == "blank_row" for i in row["issues"])
        row["resolution"] = resolve(
            symbol, row["parsed"]["currency"], received_at.date(), instruments
        )
    data["summary"]["by_resolution"] = dict(Counter(r["resolution"].status for r in data["rows"]))
    preview = ImportPreview(id=uuid4(), received_at=received_at, **data)
    repository.save(preview)
    return preview


def set_resolution(
    preview: ImportPreview,
    row_number: int,
    instrument_id: UUID | None,
    repository: PreviewRepository,
    instruments: InstrumentRepository,
    clock: Callable[[], datetime] = utc_now,
) -> ImportRow:
    row = next((row for row in preview.rows if row.row_number == row_number), None)
    if row is None:
        raise ImportProblem("row_not_found", "Import row was not found.", 404)
    if any(issue.code == "blank_row" for issue in row.issues):
        raise ImportProblem("row_not_resolvable", "Blank rows cannot be resolved.", 409)
    as_of = preview.received_at.astimezone(UTC).date()
    symbol = row.parsed.symbol
    if any(i.code == "formula_like_value" and i.field == "symbol" for i in row.issues):
        symbol = None
    automatic = resolve(symbol, row.parsed.currency, as_of, instruments)
    if instrument_id is None:
        row.resolution = automatic
    else:
        instrument = instruments.get(instrument_id)
        if instrument is None:
            raise ImportProblem("unknown_instrument", "Instrument was not found.")
        label = display_symbol(instrument_id, as_of, instruments)
        if label is None:
            raise ImportProblem(
                "instrument_not_listed", "Instrument has no active mapping on the preview date."
            )
        selected_at = clock()
        if selected_at.tzinfo is None or selected_at.utcoffset() is None:
            raise ValueError("Selection clock must return a timezone-aware datetime")
        row.resolution = Resolution(
            status="resolved",
            method="user_selected",
            instrument_id=instrument_id,
            display_symbol=label,
            candidates=automatic.candidates,
            issues=[i for i in automatic.issues if i.code != "currency_mismatch"]
            + currency_issues(instrument, row.parsed.currency),
            as_of=as_of,
            selected_at=selected_at.astimezone(UTC),
        )
    preview.summary.by_resolution = dict(Counter(r.resolution.status for r in preview.rows))
    preview.revision += 1
    repository.save(preview)
    return row


def decorate_preview(
    preview: ImportPreview, instruments: InstrumentRepository, portfolios: PortfolioRepository
) -> ImportPreview:
    instrument_ids = {
        r.resolution.instrument_id
        for r in preview.rows
        if r.resolution.instrument_id is not None
        and instruments.get(r.resolution.instrument_id) is not None
    }
    preview.readiness = readiness(preview.rows, instrument_ids)
    record = portfolios.by_import(preview.id)
    if record is not None:
        version = portfolios.get(record.portfolio_version_id)
        preview.confirmation = Confirmation(
            portfolio_version_id=version.id, confirmed_at=version.confirmed_at
        )
    return preview


def ensure_editable(preview: ImportPreview, portfolios: PortfolioRepository) -> None:
    if portfolios.by_import(preview.id) is not None:
        raise ImportProblem("import_confirmed", "Confirmed imports cannot be edited.", 409)


def set_exclusion(
    preview: ImportPreview, row_number: int, excluded: bool, repository: PreviewRepository
) -> ImportRow:
    row = next((r for r in preview.rows if r.row_number == row_number), None)
    if row is None:
        raise ImportProblem("row_not_found", "Import row was not found.", 404)
    if is_blank(row) and not excluded:
        raise ImportProblem("row_not_includable", "Blank rows cannot be included.", 409)
    row.excluded = excluded
    preview.revision += 1
    repository.save(preview)
    return row


def confirmation_response(
    record: ConfirmationRecord, portfolios: PortfolioRepository
) -> ConfirmResponse:
    return ConfirmResponse(
        portfolio_version=portfolios.get(record.portfolio_version_id),
        positions=list(portfolios.positions(record.portfolio_version_id)),
        import_id=record.import_id,
        excluded_rows=list(record.excluded_rows),
    )


def check_receipt(record: ConfirmationRecord, import_id: UUID, key: str, fingerprint: str) -> None:
    if record.idempotency_key == key:
        if record.import_id != import_id or record.request_fingerprint != fingerprint:
            raise ImportProblem(
                "idempotency_key_reused", "Key was already used for another request.", 422
            )
    else:
        raise ImportProblem(
            "import_already_confirmed",
            "Import was already confirmed.",
            409,
            portfolio_version_id=str(record.portfolio_version_id),
        )


def confirm_import(
    preview: ImportPreview,
    revision: int,
    key: str,
    instruments: InstrumentRepository,
    portfolios: PortfolioRepository,
    clock: Callable[[], datetime],
) -> tuple[ConfirmResponse, int]:
    fingerprint = str(revision)
    existing = portfolios.by_idempotency_key(key) or portfolios.by_import(preview.id)
    if existing is not None:
        check_receipt(existing, preview.id, key, fingerprint)
        return confirmation_response(existing, portfolios), 200
    if preview.revision != revision:
        raise ImportProblem("preview_changed", "Preview changed; review the current revision.", 409)
    preview = decorate_preview(preview, instruments, portfolios)
    if not preview.readiness.confirmable:
        raise ImportProblem(
            "import_not_confirmable",
            "Review blocking rows before confirming.",
            409,
            blockers=[b.model_dump() for b in preview.readiness.blockers],
        )
    version, positions = build_portfolio(preview, uuid4(), clock())
    record = ConfirmationRecord(
        import_id=preview.id,
        idempotency_key=key,
        request_fingerprint=fingerprint,
        portfolio_version_id=version.id,
        excluded_rows=tuple(excluded_rows(preview.rows)),
    )
    stored = portfolios.confirm(record, version, positions)
    check_receipt(stored, preview.id, key, fingerprint)
    status = 201 if stored.portfolio_version_id == version.id else 200
    return confirmation_response(stored, portfolios), status
