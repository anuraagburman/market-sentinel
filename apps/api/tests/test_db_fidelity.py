"""Exact decimal/timestamp text and unset/null distinction survive SQL storage."""

import pytest

from app.db.repositories import PostgresPortfolioRepository
from test_confirm_repository import candidate

pytestmark = pytest.mark.postgres


@pytest.mark.parametrize("quantity", ["10", "10.50", "0.000001"])
@pytest.mark.parametrize("cash", ["absent", None])
def test_exact_wire_round_trip(clean_postgres, quantity, cash):
    repository = PostgresPortfolioRepository(clean_postgres)
    record, version, positions = candidate()
    data = version.model_dump(exclude_unset=True)
    data.pop("cash", None)
    if cash is None:
        data["cash"] = None
    data["imported_at"] = "2026-09-25T21:00:00Z"
    data["confirmed_at"] = "2026-09-25T21:00:00.1Z"
    version = type(version).model_validate(data)
    positions = (positions[0].model_copy(update={"quantity": quantity, "cost_basis": None}),)
    repository.confirm(record, version, positions)
    expected = version.model_copy(update={"previous_version_id": None})
    assert repository.get(version.id) == expected
    assert repository.get(version.id).model_dump_json(
        exclude_unset=True
    ) == expected.model_dump_json(exclude_unset=True)
    assert repository.positions(version.id) == positions
    assert repository.positions(version.id)[0].model_dump_json(exclude_unset=True) == positions[
        0
    ].model_dump_json(exclude_unset=True)
    assert repository.by_import(record.import_id) == record
    assert repository.by_idempotency_key(record.idempotency_key) == record
