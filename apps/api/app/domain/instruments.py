"""Pure exact-symbol resolution; no clock, I/O, fuzzy matches or conversions."""

from datetime import date
from uuid import UUID

from app.models.instruments import Candidate, Instrument, Resolution, ResolutionIssue
from app.services.instruments import InstrumentRepository

ASCII_UPPER = str.maketrans("abcdefghijklmnopqrstuvwxyz", "ABCDEFGHIJKLMNOPQRSTUVWXYZ")


def normalize_symbol(symbol: str) -> str:
    return symbol.strip().translate(ASCII_UPPER)


def display_symbol(
    instrument_id: UUID, as_of: date, repository: InstrumentRepository
) -> str | None:
    active = [m for m in repository.mappings() if m.active(as_of)]
    symbols = {m.symbol for m in active if m.instrument_id == instrument_id}
    # Prefer an unambiguous alias for display, with a lexical tie-break. Identity
    # selection never uses this display-only ordering.
    return min(symbols, key=lambda s: (sum(m.symbol == s for m in active), s), default=None)


def candidate(instrument: Instrument, as_of: date, repository: InstrumentRepository) -> Candidate:
    return Candidate(
        instrument_id=instrument.id,
        name=instrument.name,
        asset_type=instrument.asset_type,
        display_symbol=display_symbol(instrument.id, as_of, repository),
    )


def currency_issues(instrument: Instrument, currency: str | None) -> list[ResolutionIssue]:
    if currency is None or currency == instrument.currency:
        return []
    return [
        ResolutionIssue(
            code="currency_mismatch",
            field="currency",
            message=f"Warning: row currency {currency} differs from {instrument.name} currency {instrument.currency}; nothing converted.",
        )
    ]


def resolve(
    symbol: str | None, currency: str | None, as_of: date, repository: InstrumentRepository
) -> Resolution:
    if symbol is None:
        return Resolution(status="not_attempted", as_of=as_of)
    matching = [m for m in repository.mappings() if m.symbol == normalize_symbol(symbol)]
    active_ids = sorted({m.instrument_id for m in matching if m.active(as_of)})
    if len(active_ids) == 1:
        instrument = repository.get(active_ids[0])
        assert instrument is not None
        issues = currency_issues(instrument, currency)
        earlier_ids = sorted(
            {
                m.instrument_id
                for m in matching
                if m.instrument_id != instrument.id
                and m.valid_from < as_of
                and m.valid_to is not None
                and m.valid_to <= as_of
            }
        )
        for earlier_id in earlier_ids:
            earlier = repository.get(earlier_id)
            assert earlier is not None
            issues.append(
                ResolutionIssue(
                    code="symbol_reassigned",
                    field="symbol",
                    message=f"Warning: symbol previously identified {earlier.name} ({earlier.id}).",
                )
            )
        return Resolution(
            status="resolved",
            method="exact_symbol",
            instrument_id=instrument.id,
            display_symbol=display_symbol(instrument.id, as_of, repository),
            issues=issues,
            as_of=as_of,
        )
    if active_ids:
        return Resolution(
            status="ambiguous",
            as_of=as_of,
            candidates=[candidate(repository.get(i), as_of, repository) for i in active_ids],
            issues=[
                ResolutionIssue(
                    code="symbol_ambiguous",
                    field="symbol",
                    message="Error: symbol has multiple active instruments; select explicitly.",
                )
            ],
        )
    retired_ids = sorted(
        {m.instrument_id for m in matching if m.valid_to is not None and m.valid_to <= as_of}
    )
    if retired_ids:
        candidates = [candidate(repository.get(i), as_of, repository) for i in retired_ids]
        labels = "; ".join(
            f"{c.name}: {c.display_symbol or 'no active symbol'}" for c in candidates
        )
        return Resolution(
            status="unresolved",
            as_of=as_of,
            candidates=candidates,
            issues=[
                ResolutionIssue(
                    code="symbol_retired",
                    field="symbol",
                    message=f"Error: retired symbol; current labels on {as_of}: {labels}.",
                )
            ],
        )
    return Resolution(
        status="unresolved",
        as_of=as_of,
        issues=[
            ResolutionIssue(
                code="symbol_not_found",
                field="symbol",
                message="Error: no symbol mapping active on this date.",
            )
        ],
    )
