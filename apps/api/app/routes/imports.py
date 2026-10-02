"""CSV preview decisions and atomic process-local portfolio confirmation."""

import os

from sqlalchemy.exc import SQLAlchemyError
from app.db.errors import retry_transaction

from typing import Annotated
from collections.abc import Callable
from contextlib import asynccontextmanager
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, File, Header, Request, Response, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from starlette.exceptions import HTTPException
from starlette.concurrency import run_in_threadpool

from app.models.imports import ConfirmProblem, ImportPreview, ImportRow, Problem
from app.models.confirm import ConfirmRequest, ConfirmResponse
from app.models.instruments import InstrumentSelection
from app.services.imports import (
    confirm_import,
    decorate_preview,
    ensure_editable,
    set_exclusion,
    MAX_BYTES,
    ImportProblem,
    InMemoryPreviewRepository,
    PreviewRepository,
    create_preview,
    utc_now,
    set_resolution,
)
from app.services.instruments import InstrumentRepository, get_instrument_repository
from app.services.portfolios import PortfolioRepository, get_portfolio_repository


class ImportRoute(APIRoute):
    """Keep multipart and parameter errors in the import problem-body contract."""

    def get_route_handler(self):
        handler = super().get_route_handler()

        async def handle(request: Request):
            try:
                if request.url.path.endswith("/confirm") and request.method == "POST":
                    validate_key(request.headers.get("idempotency-key"))
                if request.method == "POST" and request.url.path.rstrip("/") == "/imports":
                    content_type = request.headers.get("content-type", "").split(";", 1)[0].lower()
                    if content_type != "multipart/form-data":
                        raise ImportProblem(
                            "unsupported_media_type",
                            "Upload a multipart form with a CSV file.",
                            415,
                        )
                return await handler(request)
            except SQLAlchemyError:
                return JSONResponse(
                    status_code=503,
                    content={
                        "code": "store_unavailable",
                        "message": "Portfolio store is unavailable; retry later.",
                    },
                )
            except ImportProblem as exc:
                return JSONResponse(
                    status_code=exc.status_code,
                    content={"code": exc.code, "message": exc.message, **exc.details},
                )
            except RequestValidationError:
                return JSONResponse(
                    status_code=422,
                    content={
                        "code": "invalid_upload"
                        if request.url.path.rstrip("/") == "/imports"
                        else "invalid_request",
                        "message": (
                            "A file upload named 'file' is required."
                            if request.url.path.rstrip("/") == "/imports"
                            else "Request parameters or body are invalid."
                        ),
                    },
                )
            except HTTPException as exc:
                if exc.status_code not in (400, 413, 422):
                    raise
                return JSONResponse(
                    status_code=exc.status_code,
                    content={
                        "code": "invalid_upload",
                        "message": "The multipart upload is malformed or exceeds its limits.",
                    },
                )

        return handle


@asynccontextmanager
async def lifespan(app):
    loader = app.dependency_overrides.get(get_instrument_repository, get_instrument_repository)
    loader()  # Fail startup before serving requests if the full master is invalid.
    yield


router = APIRouter(prefix="/imports", tags=["imports"], route_class=ImportRoute, lifespan=lifespan)
_repository = InMemoryPreviewRepository()


def get_repository() -> PreviewRepository:
    if os.environ.get("DATABASE_URL"):
        from app.db.engine import get_engine
        from app.db.repositories import PostgresPreviewRepository

        return PostgresPreviewRepository(get_engine())
    return _repository


Portfolios = Annotated[PortfolioRepository, Depends(get_portfolio_repository)]


Repository = Annotated[PreviewRepository, Depends(get_repository)]
Instruments = Annotated[InstrumentRepository, Depends(get_instrument_repository)]


def get_clock() -> Callable[[], datetime]:
    return utc_now


Clock = Annotated[Callable[[], datetime], Depends(get_clock)]


@router.post(
    "",
    status_code=201,
    response_model=ImportPreview,
    responses={code: {"model": Problem} for code in (400, 413, 415, 422, 503)},
)
async def upload_import(
    repository: Repository,
    instruments: Instruments,
    clock: Clock,
    file: Annotated[UploadFile, File()],
    portfolios: Portfolios,
) -> ImportPreview:
    """Preview a UTF-8 CSV, up to 1 MiB and 1,000 rows.

    Accept text/csv or application/csv; also accept application/vnd.ms-excel,
    text/plain, and application/octet-stream when the filename ends in .csv.

    Symbols resolve against synthetic reference data as of the upload's UTC date.
    Previews persist when DATABASE_URL is configured.
    """
    content_type = (file.content_type or "").split(";", 1)[0].strip().lower()
    csv_filename = (file.filename or "").lower().endswith(".csv")
    fallback_type = content_type in {
        "application/vnd.ms-excel",
        "text/plain",
        "application/octet-stream",
    }
    if content_type not in {"text/csv", "application/csv"} and not (csv_filename and fallback_type):
        raise ImportProblem(
            "unsupported_media_type",
            "Supply a CSV content type or a .csv filename with an Excel, plain-text, or binary content type.",
            415,
        )
    content = await file.read(MAX_BYTES + 1)

    def store_upload():
        return decorate_preview(
            create_preview(content, repository, instruments, clock), instruments, portfolios
        )

    return await run_in_threadpool(store_upload)


def parse_import_id(id: str) -> UUID:
    try:
        preview_id = UUID(id)
    except ValueError:
        raise ImportProblem("import_not_found", "Import preview was not found.", 404) from None
    return preview_id


def load_import(id: str, repository: PreviewRepository) -> ImportPreview:
    preview = repository.get(parse_import_id(id))
    if preview is None:
        raise ImportProblem("import_not_found", "Import preview was not found.", 404)
    return preview


@router.get(
    "/{id}",
    response_model=ImportPreview,
    responses={code: {"model": Problem} for code in (404, 503)},
)
def get_import(
    id: str, repository: Repository, instruments: Instruments, portfolios: Portfolios
) -> ImportPreview:
    return decorate_preview(load_import(id, repository), instruments, portfolios)


@router.put(
    "/{id}/rows/{row_number}/resolution",
    response_model=ImportRow,
    responses={code: {"model": Problem} for code in (404, 409, 422, 503)},
)
@retry_transaction
def select_resolution(
    id: str,
    row_number: int,
    selection: InstrumentSelection,
    repository: Repository,
    instruments: Instruments,
    clock: Clock,
    portfolios: Portfolios,
) -> ImportRow:
    """Select a listed instrument explicitly, retaining automatic issues and candidates."""
    with repository.import_transaction(parse_import_id(id), portfolios) as tx:
        repository, portfolios = tx, tx.portfolios
        preview = load_import(id, repository)
        ensure_editable(preview, portfolios)
        return set_resolution(
            preview, row_number, selection.instrument_id, repository, instruments, clock
        )


@router.delete(
    "/{id}/rows/{row_number}/resolution",
    response_model=ImportRow,
    responses={code: {"model": Problem} for code in (404, 409, 422, 503)},
)
@retry_transaction
def clear_resolution(
    id: str,
    row_number: int,
    repository: Repository,
    instruments: Instruments,
    portfolios: Portfolios,
) -> ImportRow:
    """Restore automatic resolution on the preview's original date."""
    with repository.import_transaction(parse_import_id(id), portfolios) as tx:
        repository, portfolios = tx, tx.portfolios
        preview = load_import(id, repository)
        ensure_editable(preview, portfolios)
        return set_resolution(preview, row_number, None, repository, instruments)


@router.put(
    "/{id}/rows/{row_number}/exclusion",
    response_model=ImportRow,
    responses={code: {"model": Problem} for code in (404, 409, 422, 503)},
)
@retry_transaction
def exclude_row(
    id: str, row_number: int, repository: Repository, portfolios: Portfolios
) -> ImportRow:
    with repository.import_transaction(parse_import_id(id), portfolios) as tx:
        repository, portfolios = tx, tx.portfolios
        preview = load_import(id, repository)
        ensure_editable(preview, portfolios)
        return set_exclusion(preview, row_number, True, repository)


@router.delete(
    "/{id}/rows/{row_number}/exclusion",
    response_model=ImportRow,
    responses={code: {"model": Problem} for code in (404, 409, 422, 503)},
)
@retry_transaction
def include_row(
    id: str, row_number: int, repository: Repository, portfolios: Portfolios
) -> ImportRow:
    with repository.import_transaction(parse_import_id(id), portfolios) as tx:
        repository, portfolios = tx, tx.portfolios
        preview = load_import(id, repository)
        ensure_editable(preview, portfolios)
        return set_exclusion(preview, row_number, False, repository)


def validate_key(key: str | None) -> None:
    if key is None or not 1 <= len(key) <= 200 or any(not 32 <= ord(c) <= 126 for c in key):
        raise ImportProblem(
            "idempotency_key_required",
            "Supply a 1–200 character printable ASCII Idempotency-Key.",
            400,
        )


@router.post(
    "/{id}/confirm",
    status_code=201,
    response_model=ConfirmResponse,
    response_model_exclude_unset=True,
    responses={
        200: {"model": ConfirmResponse},
        **{code: {"model": ConfirmProblem} for code in (400, 404, 409, 422, 503)},
    },
)
@retry_transaction
def confirm(
    id: str,
    body: ConfirmRequest,
    repository: Repository,
    instruments: Instruments,
    portfolios: Portfolios,
    clock: Clock,
    response: Response,
    idempotency_key: Annotated[str, Header(min_length=1, max_length=200, pattern=r"^[ -~]+$")],
) -> ConfirmResponse:
    validate_key(idempotency_key)
    with repository.import_transaction(parse_import_id(id), portfolios) as tx:
        repository, portfolios = tx, tx.portfolios
        result, status = confirm_import(
            load_import(id, repository),
            body.preview_revision,
            idempotency_key,
            instruments,
            portfolios,
            clock,
        )
        response.status_code = status
        return result
