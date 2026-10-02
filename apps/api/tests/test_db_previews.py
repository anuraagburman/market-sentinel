"""Shared preview contract: snapshots and copies, with computed fields omitted."""

from uuid import uuid4

import pytest

from app.services.imports import InMemoryPreviewRepository, create_preview


@pytest.fixture(params=["memory", "postgres"])
def previews(request):
    if request.param == "memory":
        return InMemoryPreviewRepository()
    from app.db.repositories import PostgresPreviewRepository

    return PostgresPreviewRepository(request.getfixturevalue("clean_postgres"))


def test_preview_round_trip_and_isolation(previews):
    preview = create_preview(b"symbol,quantity,currency\nSYN01,10,USD\n", previews)
    assert previews.get(preview.id) == preview
    loaded = previews.get(preview.id)
    loaded.rows[0].raw[0] = "changed"
    preview.rows.clear()
    assert previews.get(loaded.id).rows[0].raw[0] == "SYN01"
    assert previews.get(uuid4()) is None
