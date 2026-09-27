"""Loaders reject invalid snapshots before exposing any records."""

import json
from uuid import UUID

import pytest

from app.services.portfolios import FileObservationRepository, FilePortfolioRepository
from test_valuation import records


def write_records(directory, version, positions, observations):
    for name, data in zip(
        ("portfolio_version", "positions", "observations"),
        (version, positions, observations),
        strict=True,
    ):
        (directory / f"{name}.json").write_text(json.dumps(data))


def test_fixture_repository_order_and_unknown_version():
    v, p, o = records()
    portfolios = FilePortfolioRepository()
    observations = FileObservationRepository()
    version_id = UUID(v["id"])
    assert portfolios.get(version_id).id == version_id
    assert [str(row.instrument_id) for row in portfolios.positions(version_id)] == [
        row["instrument_id"] for row in p
    ]
    assert [str(row.id) for row in observations.observations()] == [row["id"] for row in o]
    assert portfolios.get(UUID(int=0)) is None
    assert portfolios.positions(UUID(int=0)) == ()


@pytest.mark.parametrize(
    "case",
    [
        "foreign_key",
        "duplicate",
        "zero",
        "negative",
        "number",
        "null_cost_missing",
        "wrong_shape",
        "unconfirmed",
        "bad_timestamp",
    ],
)
def test_invalid_portfolios_fail(tmp_path, case):
    v, p, o = records()
    if case == "foreign_key":
        p[0]["portfolio_version_id"] = str(UUID(int=0))
    elif case == "duplicate":
        p.append(p[0])
    elif case in ("zero", "negative", "number"):
        p[0]["quantity"] = {"zero": "0", "negative": "-1", "number": 1}[case]
    elif case == "null_cost_missing":
        del p[0]["cost_basis"]
    elif case == "wrong_shape":
        p = {}
    elif case == "unconfirmed":
        del v["confirmed_at"]
    else:
        v["confirmed_at"] = "2026-02-30T21:00:00Z"
    write_records(tmp_path, v, p, o)
    with pytest.raises(ValueError):
        FilePortfolioRepository(tmp_path)


@pytest.mark.parametrize(
    "case", ["duplicate", "wrong_shape", "float", "offset", "invalid_date", "nan"]
)
def test_invalid_observations_fail(tmp_path, case):
    v, p, o = records()
    if case == "duplicate":
        o.append(o[0])
    elif case == "wrong_shape":
        o = {}
    elif case == "float":
        o[0]["value"] = 1.25
    elif case == "nan":
        o[0]["value"] = "NaN"
    else:
        o[0]["received_at"] = (
            "2026-09-25T21:00:00+00:00" if case == "offset" else "2026-02-30T21:00:00Z"
        )
    write_records(tmp_path, v, p, o)
    with pytest.raises(ValueError):
        FileObservationRepository(tmp_path)
