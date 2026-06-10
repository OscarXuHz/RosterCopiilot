"""Excel export endpoints."""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import FileResponse

from ..models import ExportRequest
from ..services.excel_export import save_schedule_export

router = APIRouter(prefix="/api/export", tags=["export"])


@router.get("/current")
def export_current() -> FileResponse:
    path = save_schedule_export()
    return FileResponse(
        path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=path.name,
    )


@router.post("/excel")
def export_excel(req: ExportRequest) -> FileResponse:
    path = save_schedule_export(req)
    return FileResponse(
        path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=path.name,
    )

