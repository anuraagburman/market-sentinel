"""Resolution augments previews without changing raw input or validation status."""

import json
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

from app.services.imports import InMemoryPreviewRepository, create_preview
from app.services.instruments import FileInstrumentRepository

ROOT = Path(__file__).resolve().parents[3]
NOW = datetime(2026, 9, 25, 21, tzinfo=UTC)


def test_acceptance_portfolio():
    content = (ROOT / "evals/fixtures/portfolio/holdings.csv").read_bytes()
    repository = InMemoryPreviewRepository()
    master = FileInstrumentRepository()
    preview = create_preview(content, repository, master, lambda: NOW)
    assert preview.summary.by_resolution == {"resolved": 18, "ambiguous": 1, "unresolved": 1}
    assert preview.summary.by_status == {"ok": 18, "warning": 2, "error": 0}
    positions = json.loads((ROOT / "evals/fixtures/portfolio/positions.json").read_text())
    for index, row in enumerate(preview.rows):
        assert row.resolution.as_of == NOW.date()
        if index in (1, 4):
            continue
        assert str(row.resolution.instrument_id) == positions[index % 19]["instrument_id"]
    again = create_preview(content, repository, master, lambda: NOW)
    assert [r.resolution for r in preview.rows] == [r.resolution for r in again.rows]


def test_validation_errors_do_not_block_usable_symbols():
    content = b"symbol,quantity,currency\nSYN01,invalid,USD\n=SUM(A1),1,USD\n,1,USD\n\n"
    preview = create_preview(content, InMemoryPreviewRepository(), clock=lambda: NOW)
    assert preview.rows[0].status == "error"
    assert preview.rows[0].resolution.status == "resolved"
    assert [row.resolution.status for row in preview.rows[1:]] == ["not_attempted"] * 3
    assert all(not row.resolution.issues for row in preview.rows[1:])


def test_received_at_is_normalized_before_date_resolution():
    local = datetime(2026, 7, 1, 1, tzinfo=timezone(timedelta(hours=8)))
    preview = create_preview(
        b"symbol,quantity,currency\nSYN-RE,1,CAD\n",
        InMemoryPreviewRepository(),
        clock=lambda: local,
    )
    assert preview.received_at.isoformat() == "2026-06-30T17:00:00+00:00"
    assert str(preview.rows[0].resolution.instrument_id).endswith("000000001003")
