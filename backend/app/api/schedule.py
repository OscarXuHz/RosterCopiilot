"""Schedule API endpoints."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..models import AuditDecision, AuditItem, ChangeEvent, MockDataset, ScheduleResult
from ..services.mock_scheduler import (
    apply_audit_decision,
    generate_schedule,
    get_audit_items,
    get_current_result,
    get_dataset,
    reset_state,
)

router = APIRouter(prefix="/api/schedule", tags=["schedule"])


class GenerateScheduleRequest(BaseModel):
    changes: list[ChangeEvent] = Field(default_factory=list)


@router.get("/mock-data", response_model=MockDataset)
def mock_data() -> MockDataset:
    return get_dataset()


@router.get("/current", response_model=ScheduleResult)
def current_schedule() -> ScheduleResult:
    return get_current_result()


@router.post("/generate", response_model=ScheduleResult)
def generate(req: GenerateScheduleRequest) -> ScheduleResult:
    return generate_schedule(req.changes)


@router.post("/reset", response_model=ScheduleResult)
def reset() -> ScheduleResult:
    return reset_state()


@router.get("/audit", response_model=list[AuditItem])
def audit_queue() -> list[AuditItem]:
    return get_audit_items()


@router.post("/audit/{audit_id}/decision", response_model=ScheduleResult)
def decide_audit_item(audit_id: str, decision: AuditDecision) -> ScheduleResult:
    try:
        return apply_audit_decision(audit_id, decision)
    except KeyError:
        raise HTTPException(status_code=404, detail="audit item not found")

