"""Pure confirmation policy; reviewed resolutions are never recomputed."""

from collections import Counter
from datetime import UTC, datetime
from uuid import UUID

from app.models.confirm import Blocker, ExcludedRow, Readiness
from app.models.imports import ImportPreview, ImportRow
from app.models.valuation import PortfolioVersion, Position

# Fixture tenant placeholder until authentication and tenancy are implemented.
TENANT_ID = UUID("00000000-0000-4000-8000-000000000101")


def is_blank(row: ImportRow) -> bool:
    return any(issue.code == "blank_row" for issue in row.issues)


def excluded_rows(rows: list[ImportRow]) -> list[ExcludedRow]:
    return [
        ExcludedRow(row_number=r.row_number, reason="blank_row" if is_blank(r) else "user_excluded")
        for r in rows
        if r.excluded or is_blank(r)
    ]


def readiness(rows: list[ImportRow], instrument_ids: set[UUID]) -> Readiness:
    included = [r for r in rows if not r.excluded and not is_blank(r)]
    counts = Counter(
        r.resolution.instrument_id for r in included if r.resolution.status == "resolved"
    )
    blockers = []
    for row in included:

        def block(code: str, message: str) -> None:
            blockers.append(Blocker(row_number=row.row_number, code=code, message=message))

        if row.status == "error":
            block("row_has_errors", "Resolve row errors or exclude this row.")
        if row.resolution.status != "resolved":
            block("row_unresolved", "Select an instrument or exclude this row.")
        else:
            if row.resolution.instrument_id not in instrument_ids:
                block("instrument_missing", "The reviewed instrument is no longer available.")
            if counts[row.resolution.instrument_id] > 1:
                block("duplicate_instrument", "Exclude duplicate positions for this instrument.")
    if not included:
        blockers.append(
            Blocker(row_number=None, code="no_included_rows", message="Include at least one row.")
        )
    return Readiness(confirmable=not blockers, blockers=blockers)


def build_portfolio(
    preview: ImportPreview,
    version_id: UUID,
    confirmed_at: datetime,
    previous_version_id: UUID | None,
) -> tuple[PortfolioVersion, tuple[Position, ...]]:
    """Map a ready preview, retaining parsed strings and explicit unknown cost."""
    if confirmed_at.tzinfo is None or confirmed_at.utcoffset() is None:
        raise ValueError("Confirmation clock must be timezone-aware")
    if confirmed_at < preview.received_at:
        raise ValueError("Confirmation clock precedes import")
    version = PortfolioVersion(
        id=version_id,
        tenant_id=TENANT_ID,
        base_currency="USD",
        imported_at=preview.received_at.astimezone(UTC).isoformat().replace("+00:00", "Z"),
        source_hash="sha256:" + preview.file_sha256,
        status="confirmed",
        confirmed_at=confirmed_at.astimezone(UTC).isoformat().replace("+00:00", "Z"),
        previous_version_id=previous_version_id,
    )
    positions = tuple(
        Position(
            portfolio_version_id=version_id,
            instrument_id=row.resolution.instrument_id,
            display_symbol=row.resolution.display_symbol,
            quantity=row.parsed.quantity,
            cost_basis=row.parsed.cost_basis,
            currency=row.parsed.currency,
        )
        for row in preview.rows
        if not row.excluded and not is_blank(row)
    )
    return version, positions
