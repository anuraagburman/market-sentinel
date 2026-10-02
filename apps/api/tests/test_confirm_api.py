"""Confirmation acceptance through real routes; synthetic, deterministic, no I/O APIs."""

import json
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.routes.imports import get_clock, get_repository
from app.services.imports import InMemoryPreviewRepository
from app.services.instruments import get_instrument_repository
from app.services.portfolios import PORTFOLIO, InMemoryPortfolioRepository, get_portfolio_repository

UPLOAD = datetime(2026, 9, 25, 20, 30, tzinfo=UTC)
CONFIRM = datetime(2026, 9, 25, 21, tzinfo=UTC)
SIMPLE = b"symbol,quantity,cost_basis,currency\nSYN01,10,,USD\n"


@pytest.fixture
def client():
    previews = InMemoryPreviewRepository()
    portfolios = InMemoryPortfolioRepository()
    app.dependency_overrides[get_repository] = lambda: previews
    app.dependency_overrides[get_portfolio_repository] = lambda: portfolios
    app.dependency_overrides[get_clock] = lambda: lambda: UPLOAD
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def upload(client, content=SIMPLE):
    response = client.post("/imports", files={"file": ("holdings.csv", content, "text/csv")})
    assert response.status_code == 201
    return response.json()


def confirm(client, preview, key="key", revision=None):
    app.dependency_overrides[get_clock] = lambda: lambda: CONFIRM
    return client.post(
        f"/imports/{preview['id']}/confirm",
        headers={"Idempotency-Key": key},
        json={"preview_revision": preview["revision"] if revision is None else revision},
    )


def test_fixture_walkthrough_and_valuation(client):
    preview = upload(client, (PORTFOLIO / "holdings.csv").read_bytes())
    assert preview["revision"] == 0 and preview["confirmation"] is None
    expected = [
        (1, "duplicate_instrument"),
        (2, "row_unresolved"),
        (5, "row_unresolved"),
        (20, "duplicate_instrument"),
    ]
    assert [(b["row_number"], b["code"]) for b in preview["readiness"]["blockers"]] == expected
    blocked = confirm(client, preview)
    assert blocked.status_code == 409
    assert blocked.json()["blockers"] == preview["readiness"]["blockers"]
    positions = json.loads((PORTFOLIO / "positions.json").read_text())
    for row in (2, 5):
        assert (
            client.put(
                f"/imports/{preview['id']}/rows/{row}/resolution",
                json={"instrument_id": positions[row - 1]["instrument_id"]},
            ).status_code
            == 200
        )
    assert client.put(f"/imports/{preview['id']}/rows/20/exclusion").status_code == 200
    ready = client.get(f"/imports/{preview['id']}").json()
    assert ready["revision"] == 3 and ready["readiness"] == {"confirmable": True, "blockers": []}
    stale = confirm(client, preview)
    assert stale.status_code == 409 and stale.json()["code"] == "preview_changed"
    response = confirm(client, ready)
    assert response.status_code == 201
    body = response.json()
    version = body["portfolio_version"]
    expected_version = json.loads((PORTFOLIO / "portfolio_version.json").read_text())
    fixture_id = expected_version["id"]
    assert version == {**expected_version, "id": version["id"], "previous_version_id": None}
    assert body["positions"] == [{**p, "portfolio_version_id": version["id"]} for p in positions]
    assert body["excluded_rows"] == [{"row_number": 20, "reason": "user_excluded"}]
    assert confirm(client, ready).content == response.content
    snapshot = client.get(f"/portfolio-versions/{version['id']}").json()
    assert snapshot == {k: body[k] for k in ("portfolio_version", "positions")}
    valuation = client.get(
        f"/portfolio-versions/{version['id']}/valuation?cutoff=2026-09-25T21:00:00Z"
    ).json()
    app.dependency_overrides.pop(get_portfolio_repository)
    fixture_valuation = client.get(
        f"/portfolio-versions/{fixture_id}/valuation?cutoff=2026-09-25T21:00:00Z"
    ).json()
    assert valuation == {**fixture_valuation, "portfolio_version_id": version["id"]}


def test_idempotency_and_post_confirm_edits(client):
    p = upload(client)
    response = confirm(client, p)
    assert response.status_code == 201
    retry = confirm(client, p)
    assert retry.status_code == 200 and retry.content == response.content
    assert confirm(client, p, revision=1).json()["code"] == "idempotency_key_reused"
    second = upload(client)
    assert confirm(client, second).status_code == 422
    other = confirm(client, p, key="other")
    assert other.status_code == 409
    assert other.json()["portfolio_version_id"] == response.json()["portfolio_version"]["id"]
    for method, suffix, kwargs in [
        ("put", "resolution", {"json": {"instrument_id": str(UUID(int=1))}}),
        ("delete", "resolution", {}),
        ("put", "exclusion", {}),
        ("delete", "exclusion", {}),
    ]:
        result = getattr(client, method)(f"/imports/{p['id']}/rows/1/{suffix}", **kwargs)
        assert result.status_code == 409 and result.json()["code"] == "import_confirmed"
    stored = client.get(f"/imports/{p['id']}").json()
    assert stored["confirmation"] == {
        "portfolio_version_id": response.json()["portfolio_version"]["id"],
        "confirmed_at": "2026-09-25T21:00:00Z",
    }
    assert stored["revision"] == 0
    next_version = confirm(client, second, key="second").json()["portfolio_version"]
    assert next_version["previous_version_id"] == response.json()["portfolio_version"]["id"]


@pytest.mark.parametrize("key", [None, "", "x" * 201, "bad\tkey", "bad\x7fkey"])
def test_invalid_keys(client, key):
    p = upload(client)
    response = client.post(
        f"/imports/{p['id']}/confirm",
        json={"preview_revision": 0},
        headers={} if key is None else {"Idempotency-Key": key},
    )
    assert response.status_code == 400 and response.json()["code"] == "idempotency_key_required"


def test_unknown_and_invalid_requests(client):
    p = {"id": str(uuid4()), "revision": 0}
    assert confirm(client, p).json()["code"] == "import_not_found"
    assert client.get(f"/portfolio-versions/{p['id']}").status_code == 404
    assert client.get("/portfolio-versions/invalid").status_code == 404
    p = upload(client)
    for revision in (-1, True, "0", None):
        response = client.post(
            f"/imports/{p['id']}/confirm",
            headers={"Idempotency-Key": "a"},
            json={"preview_revision": revision},
        )
        assert response.status_code == 422 and response.json()["code"] == "invalid_request"


def test_concurrent_confirmation(client):
    p = upload(client)
    with ThreadPoolExecutor(max_workers=10) as pool:
        responses = list(pool.map(lambda n: confirm(client, p, key=f"key-{n}"), range(10)))
    assert sorted(r.status_code for r in responses) == [201] + [409] * 9
    winner = next(r.json()["portfolio_version"]["id"] for r in responses if r.status_code == 201)
    assert all(
        r.json()["portfolio_version_id"] == winner for r in responses if r.status_code == 409
    )


def test_blank_error_and_currency_rows(client):
    p = upload(client, b"symbol,quantity,cost_basis,currency\n\nSYN01,-1,,USD\nSYN02,2,,CAD\n")
    assert p["rows"][0]["excluded"]
    url = f"/imports/{p['id']}/rows"
    assert client.delete(f"{url}/1/exclusion").json()["code"] == "row_not_includable"
    assert confirm(client, p).json()["code"] == "import_not_confirmable"
    original = p["rows"][1]
    excluded = client.put(f"{url}/2/exclusion").json()
    assert excluded == {**original, "excluded": True}
    response = confirm(client, p, revision=1)
    assert response.status_code == 201
    assert response.json()["excluded_rows"] == [
        {"row_number": 1, "reason": "blank_row"},
        {"row_number": 2, "reason": "user_excluded"},
    ]
    version_id = response.json()["portfolio_version"]["id"]
    valuation = client.get(
        f"/portfolio-versions/{version_id}/valuation?cutoff=2026-09-25T21:00:00Z"
    ).json()
    assert valuation["coverage"]["by_reason"] == {"currency_out_of_scope": 1}


def test_exclusion_roundtrip_and_noop_revisions(client):
    p = upload(client, SIMPLE + b"SYN01,20,,USD\n")
    url = f"/imports/{p['id']}"
    assert len(p["readiness"]["blockers"]) == 2
    for _ in range(2):
        assert client.put(f"{url}/rows/2/exclusion").status_code == 200
    assert client.get(url).json()["revision"] == 2
    assert client.get(url).json()["readiness"]["confirmable"]
    client.delete(f"{url}/rows/2/exclusion")
    assert client.get(url).json()["readiness"] == p["readiness"]
    for row in (1, 2):
        client.put(f"{url}/rows/{row}/exclusion")
    blockers = client.get(url).json()["readiness"]["blockers"]
    assert [(b["row_number"], b["code"]) for b in blockers] == [(None, "no_included_rows")]


def test_missing_instrument_and_no_reresolution(client):
    p = upload(client)
    original = get_instrument_repository()
    instrument_id = UUID(p["rows"][0]["resolution"]["instrument_id"])

    class ChangedRepository:
        missing = True

        def get(self, id):
            return None if self.missing else original.get(id)

        def mappings(self):
            raise AssertionError("Confirm must not re-resolve")

    changed = ChangedRepository()
    app.dependency_overrides[get_instrument_repository] = lambda: changed
    assert confirm(client, p).json()["blockers"][0]["code"] == "instrument_missing"
    changed.missing = False
    assert confirm(client, p).json()["positions"][0]["instrument_id"] == str(instrument_id)


def test_duplicate_exclusion_permutation_and_both_excluded(client):
    results = []
    for removed in (1, 2):
        p = upload(client, SIMPLE + b"SYN01,10,,USD\nSYN02,3,,USD\n")
        client.put(f"/imports/{p['id']}/rows/{removed}/exclusion")
        body = confirm(client, p, key=f"permute-{removed}", revision=1).json()
        assert body["excluded_rows"] == [{"row_number": removed, "reason": "user_excluded"}]
        results.append(
            [
                {k: v for k, v in position.items() if k != "portfolio_version_id"}
                for position in body["positions"]
            ]
        )
    assert results[0] == results[1]
    p = upload(client, (PORTFOLIO / "holdings.csv").read_bytes())
    positions = json.loads((PORTFOLIO / "positions.json").read_text())
    for row in (2, 5):
        client.put(
            f"/imports/{p['id']}/rows/{row}/resolution",
            json={"instrument_id": positions[row - 1]["instrument_id"]},
        )
    for row in (1, 20):
        client.put(f"/imports/{p['id']}/rows/{row}/exclusion")
    response = confirm(client, p, key="both", revision=4)
    assert response.status_code == 201
    assert len(response.json()["positions"]) == 18
    assert all(row["display_symbol"] != "SYN01" for row in response.json()["positions"])


def test_same_key_concurrent_retries(client):
    p = upload(client)
    with ThreadPoolExecutor(max_workers=8) as pool:
        responses = list(pool.map(lambda _: confirm(client, p), range(8)))
    assert sorted(r.status_code for r in responses) == [200] * 7 + [201]
    assert len({r.content for r in responses}) == 1


def test_edit_cannot_cross_confirmation_transaction(client):
    from threading import Event

    entered, release, edit_started = Event(), Event(), Event()
    store = app.dependency_overrides[get_portfolio_repository]()
    original = store.confirm

    def paused_confirm(*args):
        entered.set()
        assert release.wait(5)
        return original(*args)

    store.confirm = paused_confirm
    p = upload(client)

    def edit():
        edit_started.set()
        return client.put(f"/imports/{p['id']}/rows/1/exclusion")

    with ThreadPoolExecutor(max_workers=2) as pool:
        confirmation = pool.submit(confirm, client, p)
        try:
            assert entered.wait(5)
            editing = pool.submit(edit)
            assert edit_started.wait(5)
        finally:
            release.set()
        assert confirmation.result().status_code == 201
        assert editing.result().json()["code"] == "import_confirmed"
    assert client.get(f"/imports/{p['id']}").json()["revision"] == 0
