"""Synchronous CSV preview endpoints; no confirmation or persistent storage yet."""

from typing import Annotated
from collections.abc import Callable
from contextlib import asynccontextmanager
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, File, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from starlette.exceptions import HTTPException

from app.models.imports import ImportPreview, Problem
from app.services.imports import (
    MAX_BYTES,
    ImportProblem,
    InMemoryPreviewRepository,
    PreviewRepository,
    create_preview,
    utc_now,
)
from app.services.instruments import InstrumentRepository, get_instrument_repository


class ImportRoute(APIRoute):
    """Keep multipart and parameter errors in the import problem-body contract."""

    def get_route_handler(self):
        handler = super().get_route_handler()

        async def handle(request: Request):
            try:
                if request.method == "POST":
                    content_type = request.headers.get("content-type", "").split(";", 1)[0].lower()
                    if content_type != "multipart/form-data":
                        raise ImportProblem(
                            "unsupported_media_type",
                            "Upload a multipart form with a CSV file.",
                            415,
                        )
                return await handler(request)
            except ImportProblem as exc:
                return JSONResponse(
                    status_code=exc.status_code,
                    content=Problem(code=exc.code, message=exc.message).model_dump(),
                )
            except RequestValidationError:
                return JSONResponse(
                    status_code=422,
                    content={
                        "code": "invalid_upload",
                        "message": "A file upload named 'file' is required.",
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
    return _repository


Repository = Annotated[PreviewRepository, Depends(get_repository)]
Instruments = Annotated[InstrumentRepository, Depends(get_instrument_repository)]


def get_clock() -> Callable[[], datetime]:
    return utc_now


Clock = Annotated[Callable[[], datetime], Depends(get_clock)]


@router.post(
    "",
    status_code=201,
    response_model=ImportPreview,
    responses={code: {"model": Problem} for code in (400, 413, 415, 422)},
)
async def upload_import(
    repository: Repository,
    instruments: Instruments,
    clock: Clock,
    file: Annotated[UploadFile, File()],
) -> ImportPreview:
    """Preview a UTF-8 CSV, up to 1 MiB and 1,000 rows.

    Accept text/csv or application/csv; also accept application/vnd.ms-excel,
    text/plain, and application/octet-stream when the filename ends in .csv.

    Symbols resolve against synthetic reference data as of the upload's UTC date.
    Previews are process-local and disappear on restart.
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
    return create_preview(content, repository, instruments, clock)


@router.get("/{id}", response_model=ImportPreview, responses={404: {"model": Problem}})
def get_import(id: str, repository: Repository) -> ImportPreview:
    """Retrieve a preview from this process; unknown identifiers return 404."""
    try:
        preview_id = UUID(id)
    except ValueError:
        raise ImportProblem("import_not_found", "Import preview was not found.", 404) from None
    preview = repository.get(preview_id)
    if preview is None:
        raise ImportProblem("import_not_found", "Import preview was not found.", 404)
    return preview
