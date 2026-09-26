"""CSV import validation. Cells are data only; no symbol resolution or valuation."""

import csv
import hashlib
import io
import re
from collections import Counter
from datetime import UTC, datetime
from decimal import Decimal
from typing import Protocol
from uuid import UUID, uuid4

from app.models.imports import ImportPreview

MAX_BYTES = 1024 * 1024
MAX_ROWS = 1000
FIELDS = ("symbol", "quantity", "cost_basis", "currency")
REQUIRED = ("symbol", "quantity", "currency")
PLAIN_DECIMAL = re.compile(r"-?(?:[0-9]+(?:\.[0-9]+)?|\.[0-9]+)\Z")
# Permit a cell up to the total upload limit; the default CSV limit is smaller.
csv.field_size_limit(MAX_BYTES)


class ImportProblem(Exception):
    def __init__(self, code: str, message: str, status_code: int = 422):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


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
    """Storage boundary for future persistence; confirmation is outside this task."""

    def save(self, preview: ImportPreview) -> None: ...

    def get(self, preview_id: UUID) -> ImportPreview | None: ...


class InMemoryPreviewRepository:
    """Temporary process-local storage: lost on restart, not shared across workers.

    Copies isolate stored previews from mutations by callers. No auth/tenant or
    persistence semantics are implied; this repository is for the preview MVP.
    """

    def __init__(self):
        self._previews: dict[UUID, ImportPreview] = {}

    def save(self, preview: ImportPreview) -> None:
        self._previews[preview.id] = preview.model_copy(deep=True)

    def get(self, preview_id: UUID) -> ImportPreview | None:
        preview = self._previews.get(preview_id)
        return preview.model_copy(deep=True) if preview is not None else None


def create_preview(content: bytes, repository: PreviewRepository) -> ImportPreview:
    received_at = datetime.now(UTC)
    data = parse_csv(content)
    preview = ImportPreview(id=uuid4(), received_at=received_at, **data)
    repository.save(preview)
    return preview
