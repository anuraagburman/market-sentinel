from uuid import uuid4

import pytest

from app.services.imports import (
    ImportProblem,
    InMemoryPreviewRepository,
    create_preview,
)


CONTENT = b"symbol,quantity,currency\nSYN01,0.000000001,USD\n"


def test_repository_round_trip_and_copy_isolation():
    repository = InMemoryPreviewRepository()
    preview = create_preview(CONTENT, repository)
    expected = preview.model_dump(mode="json")
    assert expected["received_at"].endswith("Z")
    assert expected["rows"][0]["parsed"]["quantity"] == "0.000000001"
    assert expected["rows"][0]["parsed"]["cost_basis"] is None
    preview.rows.clear()
    stored = repository.get(preview.id)
    assert stored.model_dump(mode="json") == expected
    stored.rows.clear()
    assert repository.get(preview.id).model_dump(mode="json") == expected
    assert repository.get(uuid4()) is None
    assert InMemoryPreviewRepository().get(preview.id) is None


def test_same_bytes_only_identity_and_time_differ():
    repository = InMemoryPreviewRepository()
    one = create_preview(CONTENT, repository)
    two = create_preview(CONTENT, repository)
    assert one.id != two.id
    assert one.model_dump(exclude={"id", "received_at"}) == two.model_dump(
        exclude={"id", "received_at"}
    )


def test_rejected_file_is_never_saved():
    class RejectSave:
        def save(self, preview):
            pytest.fail("Invalid CSV must not reach the repository")

    with pytest.raises(ImportProblem):
        create_preview(b"symbol\nSYN01\n", RejectSave())
