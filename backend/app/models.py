"""Domain models for the RosterCopiilot mock scheduling MVP.

The MVP intentionally uses Pydantic models and in-memory mock data instead of a
database. These models are shaped so the API can later be backed by SQLModel or
another persistence layer without changing the frontend contract too much.
"""
from __future__ import annotations

from datetime import date, time
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


Period = Literal["AM", "PM"]
Weekday = Literal[1, 2, 3, 4, 5]


class Gender(str, Enum):
    MALE = "M"
    FEMALE = "F"
    ANY = "ANY"


class Center(str, Enum):
    AMC = "AMC"
    MRC = "MRC"
    GC = "GC"
    HSS = "HSS"


class ServiceCode(str, Enum):
    MEAL_DELIVERY = "D"
    ESCORT = "ESC"
    HOME_CARE = "HC"
    PERSONAL_CARE = "PC"
    BATH = "B"
    EXERCISE = "E+RO"
    AMC_DUTY = "AMC"
    MRC_DUTY = "MRC"
    GC_DUTY = "GC"
    KITCHEN = "KITCHEN"
    TRANSPORT = "FOLLOW_CAR"
    OFF = "OFF"


class ChangeType(str, Enum):
    LEAVE = "leave"
    SERVICE_CANCELLED = "service_cancelled"
    ESCORT_QUOTA_CHANGED = "escort_quota_changed"
    EXTRA_ESCORT = "extra_escort"


class AuditStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EDITED = "edited"


class Employee(BaseModel):
    id: str
    display_name: str
    gender: Gender
    home_center: Center = Center.HSS
    skills: list[ServiceCode] = Field(default_factory=list)
    routes: list[str] = Field(default_factory=list)
    daily_hours: int = 8
    is_part_time: bool = False

    def can_do(self, service_code: ServiceCode) -> bool:
        if service_code == ServiceCode.MEAL_DELIVERY:
            return True
        if service_code in {
            ServiceCode.AMC_DUTY,
            ServiceCode.MRC_DUTY,
            ServiceCode.GC_DUTY,
        }:
            return service_code in self.skills or ServiceCode.AMC_DUTY in self.skills
        return service_code in self.skills


class Elder(BaseModel):
    id: str
    display_name: str
    gender: Gender
    district: str
    address_label: str | None = None
    gender_requirement: Gender = Gender.ANY
    exclusive_worker_id: str | None = None
    notes: str | None = None


class FixedService(BaseModel):
    id: str
    elder_id: str
    service_code: ServiceCode
    weekday: Weekday
    period: Period
    assigned_worker_id: str | None = None
    district: str
    route: str | None = None
    start_time: time | None = None
    end_time: time | None = None
    week_pattern: str = "weekly"
    exclusive: bool = False
    priority: int = 50
    notes: str | None = None


class EscortRequest(BaseModel):
    id: str
    service_date: date
    period: Period
    elder_id: str
    appointment_time: time | None = None
    destination: str
    subject: str | None = None
    transport: str | None = None
    gender_requirement: Gender = Gender.ANY
    notes: str | None = None


class ScheduleParams(BaseModel):
    week_start: date
    escort_baseline_per_period: int = 4
    center_duty_required: dict[Center, int] = Field(
        default_factory=lambda: {Center.AMC: 1, Center.MRC: 1, Center.GC: 1}
    )
    service_priority: list[ServiceCode] = Field(
        default_factory=lambda: [
            ServiceCode.AMC_DUTY,
            ServiceCode.MRC_DUTY,
            ServiceCode.GC_DUTY,
            ServiceCode.ESCORT,
            ServiceCode.EXERCISE,
            ServiceCode.HOME_CARE,
            ServiceCode.PERSONAL_CARE,
            ServiceCode.BATH,
            ServiceCode.MEAL_DELIVERY,
        ]
    )
    districts: list[str] = Field(default_factory=lambda: ["灣仔", "北角", "筲箕灣", "柴灣"])


class ChangeEvent(BaseModel):
    id: str | None = None
    type: ChangeType
    change_date: date
    period: Period | None = None
    worker_id: str | None = None
    elder_id: str | None = None
    service_id: str | None = None
    new_escort_count: int | None = None
    reason: str | None = None


class ScheduleEntry(BaseModel):
    id: str
    schedule_date: date
    weekday: Weekday
    period: Period
    worker_id: str
    worker_name: str
    service_code: ServiceCode
    elder_id: str | None = None
    elder_name: str | None = None
    district: str | None = None
    destination: str | None = None
    start_time: time | None = None
    end_time: time | None = None
    source: Literal["template", "escort", "system_reassigned", "manual", "standby"] = "template"
    status: Literal["scheduled", "affected", "cancelled", "unassigned", "needs_review"] = "scheduled"
    notes: str | None = None


class ImpactItem(BaseModel):
    id: str
    severity: Literal["info", "warning", "high"]
    title: str
    description: str
    affected_entry_ids: list[str] = Field(default_factory=list)
    affected_worker_ids: list[str] = Field(default_factory=list)
    affected_elder_ids: list[str] = Field(default_factory=list)


class AuditItem(BaseModel):
    id: str
    status: AuditStatus = AuditStatus.PENDING
    kind: Literal[
        "replacement_suggestion",
        "service_cancellation",
        "unassigned_task",
        "escort_adjustment",
        "center_duty_fill",
    ]
    severity: Literal["info", "warning", "high"] = "warning"
    reason: str
    original_entry: ScheduleEntry | None = None
    suggested_entry: ScheduleEntry | None = None
    alternatives: list[ScheduleEntry] = Field(default_factory=list)
    human_note: str | None = None


class ScheduleResult(BaseModel):
    week_start: date
    entries: list[ScheduleEntry]
    impacts: list[ImpactItem] = Field(default_factory=list)
    audit_items: list[AuditItem] = Field(default_factory=list)
    unassigned: list[ScheduleEntry] = Field(default_factory=list)
    summary: dict[str, int] = Field(default_factory=dict)


class AuditDecision(BaseModel):
    status: AuditStatus
    human_note: str | None = None
    edited_entry: ScheduleEntry | None = None


class MockDataset(BaseModel):
    employees: list[Employee]
    elders: list[Elder]
    fixed_services: list[FixedService]
    escort_requests: list[EscortRequest]
    params: ScheduleParams


class ExportRequest(BaseModel):
    result: ScheduleResult | None = None
    include_audit: bool = True

