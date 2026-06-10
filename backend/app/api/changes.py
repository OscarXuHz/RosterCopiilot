"""Change-event simulation endpoints."""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from ..models import ChangeEvent, ScheduleResult
from ..services.mock_scheduler import example_changes, generate_schedule

router = APIRouter(prefix="/api/changes", tags=["changes"])


class ChangeSimulationRequest(BaseModel):
    changes: list[ChangeEvent] = Field(default_factory=list)


@router.get("/examples", response_model=list[ChangeEvent])
def examples() -> list[ChangeEvent]:
    return example_changes()


@router.post("/simulate", response_model=ScheduleResult)
def simulate(req: ChangeSimulationRequest) -> ScheduleResult:
    return generate_schedule(req.changes)

