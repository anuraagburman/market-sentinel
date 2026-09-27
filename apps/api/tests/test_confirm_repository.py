"""Reusable store contract: add the T-012 factory to repository parametrization."""

from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest

from app.models.confirm import ConfirmationRecord
from app.services.portfolios import FilePortfolioRepository, InMemoryPortfolioRepository


@pytest.fixture(params=[InMemoryPortfolioRepository], ids=["memory"])
def repository(request):
    return request.param()


def candidate(import_id=None, key=None):
    source = FilePortfolioRepository()
    version = source._version.model_copy(update={"id": uuid4()})
    positions = tuple(
        p.model_copy(update={"portfolio_version_id": version.id}) for p in source._positions
    )
    record = ConfirmationRecord(
        import_id=import_id or uuid4(),
        idempotency_key=key or str(uuid4()),
        request_fingerprint="0",
        portfolio_version_id=version.id,
        excluded_rows=(),
    )
    return record, version, positions


def test_atomic_validation_and_immutable_reads(repository):
    record, version, positions = candidate()
    with pytest.raises(ValueError):
        repository.confirm(record, version, positions + positions)
    assert repository.get(version.id) is None
    assert repository.by_import(record.import_id) is None
    assert repository.by_idempotency_key(record.idempotency_key) is None
    assert repository.latest(version.tenant_id) is None
    repository.confirm(record, version, positions)
    # Even bypassing frozen-model protection must not mutate storage.
    object.__setattr__(version, "source_hash", "changed")
    object.__setattr__(repository.get(version.id), "source_hash", "changed")
    object.__setattr__(repository.positions(version.id)[0], "quantity", "999")
    object.__setattr__(repository.by_import(record.import_id), "request_fingerprint", "changed")
    assert repository.get(version.id).source_hash != "changed"
    assert repository.positions(version.id)[0].quantity == "10"
    assert repository.by_idempotency_key(record.idempotency_key).request_fingerprint == "0"
    assert not hasattr(repository, "update") and not hasattr(repository, "delete")


def test_single_winner_and_key_uniqueness(repository):
    import_id = uuid4()
    candidates = [candidate(import_id) for _ in range(12)]
    with ThreadPoolExecutor(max_workers=12) as pool:
        receipts = list(pool.map(lambda args: repository.confirm(*args), candidates))
    assert len({r.portfolio_version_id for r in receipts}) == 1
    assert sum(repository.get(v.id) is not None for _, v, _ in candidates) == 1
    winner = receipts[0]
    other = candidate(key=winner.idempotency_key)
    assert repository.confirm(*other) == winner
    assert repository.get(other[1].id) is None


def test_latest_is_selected_atomically(repository):
    candidates = [candidate() for _ in range(10)]
    with ThreadPoolExecutor(max_workers=10) as pool:
        list(pool.map(lambda args: repository.confirm(*args), candidates))
    current = repository.latest(candidates[0][1].tenant_id)
    visited = set()
    while current is not None:
        assert current.id not in visited
        visited.add(current.id)
        current = repository.get(current.previous_version_id)
    assert visited == {v.id for _, v, _ in candidates}
