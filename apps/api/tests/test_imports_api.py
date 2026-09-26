"""Upload boundaries and HTTP contract, using isolated in-memory repositories."""

import hashlib
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.routes.imports import get_repository
from app.services.imports import MAX_BYTES, InMemoryPreviewRepository

FIXTURES = Path(__file__).parent / "fixtures/imports"
PORTFOLIO = Path(__file__).resolve().parents[3] / "evals/fixtures/portfolio/holdings.csv"


@pytest.fixture
def client():
    class RecordingRepository(InMemoryPreviewRepository):
        def __init__(self):
            super().__init__()
            self.saved = []

        def save(self, preview):
            self.saved.append(preview.id)
            super().save(preview)

    repository = RecordingRepository()
    app.dependency_overrides[get_repository] = lambda: repository
    try:
        with TestClient(app) as test_client:
            yield test_client, repository
    finally:
        app.dependency_overrides.pop(get_repository)


def upload(client, content, media_type="text/csv"):
    return client.post("/imports", files={"file": ("holdings.csv", content, media_type)})


def test_portfolio_round_trip(client):
    http, repository = client
    content = PORTFOLIO.read_bytes()
    response = upload(http, content)
    assert response.status_code == 201
    preview = response.json()
    assert preview["file_sha256"] == hashlib.sha256(content).hexdigest()
    assert preview["received_at"].endswith("Z")
    assert len(preview["rows"]) == 20
    assert len(repository.saved) == 1
    assert preview["summary"]["by_status"] == {"ok": 18, "warning": 2, "error": 0}
    assert http.get(f"/imports/{preview['id']}").json() == preview
    again = upload(http, content).json()
    assert again["id"] != preview["id"]
    for key in preview.keys() - {"id", "received_at"}:
        assert again[key] == preview[key]


@pytest.mark.parametrize("identifier", [str(uuid4()), "unknown"])
def test_unknown_import(client, identifier):
    response = client[0].get(f"/imports/{identifier}")
    assert response.status_code == 404
    assert response.json() == {
        "code": "import_not_found",
        "message": "Import preview was not found.",
    }


@pytest.mark.parametrize(
    ("content", "media_type", "status", "code"),
    [
        (b"x" * (MAX_BYTES + 1), "text/csv", 413, "file_too_large"),
        ((FIXTURES / "latin1.csv").read_bytes(), "text/csv", 422, "invalid_encoding"),
        ((FIXTURES / "missing-quantity.csv").read_bytes(), "text/csv", 422, "missing_column"),
        (b"symbol,quantity,currency\n" + b"SYN01,1,USD\n" * 1001, "text/csv", 422, "too_many_rows"),
        (
            b"symbol,quantity,currency\nSYN01,1,USD\n",
            "application/json",
            415,
            "unsupported_media_type",
        ),
        (b'symbol,quantity,currency\n"unterminated,1,USD', "text/csv", 422, "invalid_csv"),
        (b"symbol,quantity, Quantity ,currency\n", "text/csv", 422, "duplicate_column"),
        (b"", "text/csv", 422, "missing_column"),
    ],
)
def test_file_rejections_never_save(client, content, media_type, status, code):
    http, repository = client
    response = upload(http, content, media_type)
    assert response.status_code == status
    assert set(response.json()) == {"code", "message"}
    assert response.json()["code"] == code
    assert repository.saved == []


@pytest.mark.parametrize("limit", ["bytes", "rows"])
def test_exact_limits_accepted(client, limit):
    if limit == "bytes":
        content = b"symbol,quantity,cost_basis,currency,notes\nSYN01,1,10,USD,"
        content += b"x" * (MAX_BYTES - len(content))
    else:
        content = b"symbol,quantity,cost_basis,currency\n" + b"SYN01,1,10,USD\n" * 1000
    response = upload(client[0], content)
    assert response.status_code == 201
    assert len(response.json()["rows"]) == (1000 if limit == "rows" else 1)


@pytest.mark.parametrize("name", ["bom.csv", "unknown-column.csv"])
def test_header_fixtures_accepted(client, name):
    content = (FIXTURES / name).read_bytes()
    response = upload(client[0], content, "application/csv")
    assert response.status_code == 201
    assert response.json()["file_sha256"] == hashlib.sha256(content).hexdigest()


def test_row_errors_are_previews_not_file_rejections(client):
    response = upload(client[0], (FIXTURES / "formula.csv").read_bytes())
    assert response.status_code == 201
    row = response.json()["rows"][0]
    assert row["raw"][0] == "=SUM(A1)"
    assert row["parsed"]["symbol"] is None
    assert row["status"] == "error"
    assert row["resolution"]["status"] == "not_attempted"
    assert any(i["code"] == "formula_like_value" for i in row["issues"])


def test_non_multipart_request(client):
    response = client[0].post(
        "/imports", content=b"symbol,quantity,currency", headers={"content-type": "text/csv"}
    )
    assert response.status_code == 415
    assert response.json()["code"] == "unsupported_media_type"
    assert client[1].saved == []


def test_missing_file_and_malformed_multipart(client):
    http, repository = client
    response = http.post("/imports", files={"other": ("holdings.csv", b"", "text/csv")})
    assert response.status_code == 422
    assert set(response.json()) == {"code", "message"}
    malformed = http.post(
        "/imports", content=b"invalid", headers={"content-type": "multipart/form-data"}
    )
    assert malformed.status_code == 400
    assert set(malformed.json()) == {"code", "message"}
    assert repository.saved == []


def test_openapi_import_contract():
    schema = app.openapi()
    post = schema["paths"]["/imports"]["post"]
    assert "multipart/form-data" in post["requestBody"]["content"]
    assert post["responses"]["201"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/ImportPreview"
    }
    for status in (400, 413, 415, 422):
        assert post["responses"][str(status)]["content"]["application/json"]["schema"] == {
            "$ref": "#/components/schemas/Problem"
        }


@pytest.mark.parametrize(
    "media_type", ["application/vnd.ms-excel", "text/plain", "application/octet-stream"]
)
@pytest.mark.parametrize(
    "filename", ["holdings.csv", "HOLDINGS.CSV", "holdings.xls", "holdings.csv.exe"]
)
def test_fallback_media_types_require_csv_filename(client, media_type, filename):
    response = client[0].post(
        "/imports", files={"file": (filename, PORTFOLIO.read_bytes(), media_type)}
    )
    if filename.lower().endswith(".csv"):
        assert response.status_code == 201
        assert len(response.json()["rows"]) == 20
    else:
        assert response.status_code == 415
        assert client[1].saved == []


@pytest.mark.parametrize(
    "media_type", ["application/vnd.ms-excel", "text/plain", "application/octet-stream"]
)
def test_fallback_media_types_still_validate_content(client, media_type):
    response = upload(client[0], (FIXTURES / "latin1.csv").read_bytes(), media_type)
    assert response.status_code == 422
    assert response.json()["code"] == "invalid_encoding"
    assert client[1].saved == []
