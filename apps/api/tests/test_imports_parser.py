"""Deterministic parser acceptance cases; no external services."""

from pathlib import Path

import pytest

from app.services.imports import ImportProblem, parse_csv

FIXTURES = Path(__file__).parent / "fixtures/imports"
PORTFOLIO = Path(__file__).resolve().parents[3] / "evals/fixtures/portfolio/holdings.csv"


def codes(row):
    return {issue["code"] for issue in row["issues"]}


def test_synthetic_portfolio():
    preview = parse_csv(PORTFOLIO.read_bytes())
    rows = preview["rows"]
    assert len(rows) == 20
    assert codes(rows[19]) == {"duplicate_row"}
    assert "row 1" in rows[19]["issues"][0]["message"]
    assert codes(rows[3]) == {"missing_cost_basis"}
    assert rows[3]["parsed"]["cost_basis"] is None
    assert "unavailable" in rows[3]["issues"][0]["message"]
    assert rows[1]["parsed"]["quantity"] == "2.5"
    for index in (1, 2, 4):
        assert rows[index]["status"] == "ok"
        assert rows[index]["resolution"] == "pending"
    assert preview["summary"] == {
        "by_status": {"ok": 18, "warning": 2, "error": 0},
        "by_code": {"missing_cost_basis": 1, "duplicate_row": 1},
    }
    assert [r["row_number"] for r in rows] == list(range(1, 21))
    assert parse_csv(PORTFOLIO.read_bytes()) == preview


@pytest.mark.parametrize(
    ("name", "code"),
    [
        ("formula.csv", "formula_like_value"),
        ("decimal-comma.csv", "invalid_decimal"),
        ("negative.csv", "non_positive_quantity"),
        ("lowercase-currency.csv", "invalid_currency"),
    ],
)
def test_problem_fixtures(name, code):
    row = parse_csv((FIXTURES / name).read_bytes())["rows"][0]
    assert row["status"] == "error"
    assert code in codes(row)


@pytest.mark.parametrize("value", ["1e3", "NaN", "Infinity", "$10", "", "1_000"])
def test_invalid_decimals(value):
    row = parse_csv(f"symbol,quantity,currency\nSYN01,{value},USD\n".encode())["rows"][0]
    assert "invalid_decimal" in codes(row)
    assert row["parsed"]["quantity"] is None


@pytest.mark.parametrize("value", ["=1+1", "+2", "@SUM(A1)", "\t12", "\r12", "-cmd", " =1"])
def test_formula_cells_including_unknown_columns(value):
    import csv
    import io

    stream = io.StringIO(newline="")
    writer = csv.writer(stream)
    writer.writerow(["symbol", "quantity", "currency", "notes"])
    writer.writerow(["SYN01", "1", "USD", value])
    row = parse_csv(stream.getvalue().encode())["rows"][0]
    assert "formula_like_value" in codes(row)
    assert row["raw"][-1] == value


def test_negative_is_not_a_formula():
    row = parse_csv((FIXTURES / "negative.csv").read_bytes())["rows"][0]
    assert "formula_like_value" not in codes(row)
    assert row["parsed"]["quantity"] == "-2.5"


def test_headers_bom_unknown_and_optional_cost():
    preview = parse_csv((FIXTURES / "bom.csv").read_bytes())
    assert preview["columns"][0] == {"detected": " Symbol ", "mapped": "symbol", "unknown": False}
    assert preview["rows"][0]["parsed"]["cost_basis"] is None
    extra = parse_csv((FIXTURES / "unknown-column.csv").read_bytes())
    assert extra["columns"][-1] == {"detected": "notes", "mapped": None, "unknown": True}
    assert extra["rows"][0]["raw"][-1] == "keep this"


@pytest.mark.parametrize(
    ("name", "code"),
    [("latin1.csv", "invalid_encoding"), ("missing-quantity.csv", "missing_column")],
)
def test_rejected_fixtures(name, code):
    with pytest.raises(ImportProblem) as exc:
        parse_csv((FIXTURES / name).read_bytes())
    assert exc.value.code == code
    assert exc.value.status_code == 422
    if code == "missing_column":
        assert "quantity" in exc.value.message


def test_exact_decimal_and_equivalent_duplicate():
    rows = parse_csv(
        b"symbol,quantity,cost_basis,currency\n"
        b"SYN01,1.00000000000000000000001,10.00,USD\n"
        b"SYN01,1.000000000000000000000010,10,USD\n"
    )["rows"]
    assert rows[0]["parsed"]["quantity"] == "1.00000000000000000000001"
    assert "duplicate_row" in codes(rows[1])
    assert rows[1]["raw"][1] == "1.000000000000000000000010"


def test_uneven_and_blank_rows_are_retained():
    preview = parse_csv(b"symbol,quantity,cost_basis,currency\nSYN01,1,10,USD,extra\n\nSYN02,2\n")
    assert [r["raw"] for r in preview["rows"]] == [
        ["SYN01", "1", "10", "USD", "extra"],
        [],
        ["SYN02", "2"],
    ]
    assert codes(preview["rows"][1]) == {"blank_row"}
    assert all("column_count_mismatch" in codes(preview["rows"][i]) for i in (0, 2))
    assert preview["summary"]["by_status"] == {"ok": 0, "warning": 1, "error": 2}


def test_zero_missing_symbol_and_invalid_cost_are_errors():
    row = parse_csv(b"symbol,quantity,cost_basis,currency\n,0,NaN,US\n")["rows"][0]
    assert codes(row) == {
        "missing_symbol",
        "non_positive_quantity",
        "invalid_decimal",
        "invalid_currency",
    }
    assert row["parsed"] == {"symbol": None, "quantity": "0", "cost_basis": None, "currency": None}


def test_duplicate_with_missing_cost_keeps_both_warnings():
    rows = parse_csv(b"symbol,quantity,currency\nSYN01,1,USD\nSYN01,1.0,USD\n")["rows"]
    assert codes(rows[1]) == {"missing_cost_basis", "duplicate_row"}
    assert rows[1]["status"] == "warning"


@pytest.mark.parametrize("field", ["symbol", "quantity", "cost_basis", "currency"])
def test_formula_field_has_only_its_formula_issue(field):
    cells = {"symbol": "SYN01", "quantity": "1", "cost_basis": "10", "currency": "USD"}
    cells[field] = "=1+1"
    preview = parse_csv((",".join(cells) + "\n" + ",".join(cells.values()) + "\n").encode())
    row = preview["rows"][0]
    assert row["status"] == "error"
    assert row["parsed"][field] is None
    assert len(row["issues"]) == 1
    assert row["issues"][0]["field"] == field
    assert preview["summary"]["by_code"] == {"formula_like_value": 1}


def test_formula_does_not_suppress_other_field_errors():
    preview = parse_csv(b"symbol,quantity,cost_basis,currency\n=1,0,,usd\n")
    assert codes(preview["rows"][0]) == {
        "formula_like_value",
        "non_positive_quantity",
        "missing_cost_basis",
        "invalid_currency",
    }


@pytest.mark.parametrize("newline", [b"\n", b"\r\n"])
def test_trailing_blank_line_is_one_warning(newline):
    preview = parse_csv(
        newline.join([b"symbol,quantity,cost_basis,currency", b"SYN01,1,10,USD", b"", b""])
    )
    assert len(preview["rows"]) == 2
    row = preview["rows"][1]
    assert row["row_number"] == 2
    assert row["raw"] == []
    assert all(value is None for value in row["parsed"].values())
    assert row["resolution"] == "pending"
    assert len(row["issues"]) == 1
    assert preview["summary"] == {
        "by_status": {"ok": 1, "warning": 1, "error": 0},
        "by_code": {"blank_row": 1},
    }


def test_blank_lines_count_toward_row_limit():
    with pytest.raises(ImportProblem) as exc:
        parse_csv(b"symbol,quantity,currency\n" + b"\n" * 1001)
    assert exc.value.code == "too_many_rows"


@pytest.mark.parametrize("value", ["-10", "-0.01", "0", "0.00", "10"])
def test_cost_basis_must_be_non_negative(value):
    preview = parse_csv(f"symbol,quantity,cost_basis,currency\nSYN01,1,{value},USD\n".encode())
    row = preview["rows"][0]
    assert row["parsed"]["cost_basis"] == value
    assert row["raw"][2] == value
    if value.startswith("-"):
        assert row["status"] == "error"
        assert len(row["issues"]) == 1
        assert preview["summary"]["by_code"] == {"negative_cost_basis": 1}
    else:
        assert row["status"] == "ok"
        assert row["issues"] == []
