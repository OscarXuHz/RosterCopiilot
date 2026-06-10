"""In-memory mock scheduling engine for the MVP.

The goal is to make the product flow demonstrable before we have authoritative
NGO data and a real constraint solver. The rules below are intentionally simple:

1. Start from fixed services.
2. Add escort requests.
3. Fill missing center duty slots.
4. Apply change events and generate audit items rather than silently mutating
   everything.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date, time, timedelta
from itertools import count

from ..models import (
    AuditDecision,
    AuditItem,
    AuditStatus,
    Center,
    ChangeEvent,
    ChangeType,
    Elder,
    Employee,
    EscortRequest,
    FixedService,
    Gender,
    MockDataset,
    Period,
    ScheduleEntry,
    ScheduleParams,
    ScheduleResult,
    ServiceCode,
)
from .impact_analyzer import finalize_result

_id_counter = count(1)
_CURRENT_RESULT: ScheduleResult | None = None
_DATASET: MockDataset | None = None


def _next_id(prefix: str) -> str:
    return f"{prefix}-{next(_id_counter):04d}"


def _time(hour: int, minute: int = 0) -> time:
    return time(hour=hour, minute=minute)


def load_mock_dataset() -> MockDataset:
    """Return a fresh copy of the demo dataset."""
    week_start = date(2026, 1, 5)

    employees = [
        Employee(
            id="W001",
            display_name="娥",
            gender=Gender.FEMALE,
            home_center=Center.HSS,
            skills=[ServiceCode.HOME_CARE, ServiceCode.EXERCISE, ServiceCode.MEAL_DELIVERY],
            routes=["柴灣", "筲箕灣"],
        ),
        Employee(
            id="W002",
            display_name="炎萍",
            gender=Gender.FEMALE,
            home_center=Center.HSS,
            skills=[ServiceCode.HOME_CARE, ServiceCode.ESCORT, ServiceCode.MEAL_DELIVERY, ServiceCode.AMC_DUTY],
            routes=["灣仔", "柴灣"],
        ),
        Employee(
            id="W003",
            display_name="寶芝",
            gender=Gender.FEMALE,
            home_center=Center.AMC,
            skills=[ServiceCode.ESCORT, ServiceCode.AMC_DUTY, ServiceCode.MEAL_DELIVERY],
            routes=["灣仔", "北角"],
        ),
        Employee(
            id="W004",
            display_name="康",
            gender=Gender.MALE,
            home_center=Center.HSS,
            skills=[ServiceCode.ESCORT, ServiceCode.HOME_CARE, ServiceCode.MEAL_DELIVERY, ServiceCode.GC_DUTY],
            routes=["灣仔", "北角", "太古"],
        ),
        Employee(
            id="W005",
            display_name="嘉偉",
            gender=Gender.MALE,
            home_center=Center.HSS,
            skills=[ServiceCode.EXERCISE, ServiceCode.ESCORT, ServiceCode.MEAL_DELIVERY, ServiceCode.MRC_DUTY],
            routes=["筲箕灣", "柴灣", "小西灣"],
        ),
        Employee(
            id="W006",
            display_name="鳳",
            gender=Gender.FEMALE,
            home_center=Center.AMC,
            skills=[ServiceCode.AMC_DUTY, ServiceCode.MEAL_DELIVERY],
            routes=["灣仔"],
        ),
        Employee(
            id="W007",
            display_name="強",
            gender=Gender.MALE,
            home_center=Center.MRC,
            skills=[ServiceCode.MRC_DUTY, ServiceCode.ESCORT, ServiceCode.MEAL_DELIVERY],
            routes=["灣仔", "北角"],
        ),
        Employee(
            id="W008",
            display_name="美紅",
            gender=Gender.FEMALE,
            home_center=Center.HSS,
            skills=[ServiceCode.HOME_CARE, ServiceCode.BATH, ServiceCode.PERSONAL_CARE, ServiceCode.MEAL_DELIVERY],
            routes=["北角", "筲箕灣"],
        ),
        Employee(
            id="W009",
            display_name="秀英",
            gender=Gender.FEMALE,
            home_center=Center.HSS,
            skills=[ServiceCode.HOME_CARE, ServiceCode.ESCORT, ServiceCode.GC_DUTY],
            routes=["柴灣", "小西灣"],
        ),
    ]

    elders = [
        Elder(id="E001", display_name="Y珍", gender=Gender.FEMALE, district="柴灣", exclusive_worker_id="W001"),
        Elder(id="E002", display_name="F玲", gender=Gender.FEMALE, district="灣仔"),
        Elder(id="E003", display_name="L明", gender=Gender.MALE, district="北角"),
        Elder(id="E004", display_name="C蓮", gender=Gender.FEMALE, district="灣仔"),
        Elder(id="E005", display_name="AY娟", gender=Gender.FEMALE, district="筲箕灣"),
        Elder(id="E006", display_name="L雄", gender=Gender.MALE, district="北角"),
        Elder(id="E007", display_name="H娥", gender=Gender.FEMALE, district="柴灣"),
        Elder(id="E008", display_name="Y美", gender=Gender.FEMALE, district="筲箕灣"),
    ]

    fixed_services = [
        FixedService(
            id="FS001",
            elder_id="E001",
            service_code=ServiceCode.HOME_CARE,
            weekday=1,
            period="AM",
            assigned_worker_id="W001",
            district="柴灣",
            start_time=_time(9),
            end_time=_time(10, 30),
            week_pattern="1,3",
            exclusive=True,
            priority=40,
            notes="只要娥姐",
        ),
        FixedService(
            id="FS002",
            elder_id="E002",
            service_code=ServiceCode.HOME_CARE,
            weekday=1,
            period="AM",
            assigned_worker_id="W002",
            district="灣仔",
            start_time=_time(9),
            end_time=_time(10, 30),
            priority=45,
        ),
        FixedService(
            id="FS003",
            elder_id="E003",
            service_code=ServiceCode.HOME_CARE,
            weekday=1,
            period="PM",
            assigned_worker_id="W004",
            district="北角",
            start_time=_time(14),
            end_time=_time(15, 30),
            priority=45,
        ),
        FixedService(
            id="FS004",
            elder_id="E004",
            service_code=ServiceCode.EXERCISE,
            weekday=2,
            period="AM",
            assigned_worker_id="W005",
            district="筲箕灣",
            start_time=_time(9),
            end_time=_time(10, 30),
            exclusive=True,
            priority=35,
            notes="運動訓練，固定同工",
        ),
        FixedService(
            id="FS005",
            elder_id="E008",
            service_code=ServiceCode.BATH,
            weekday=5,
            period="PM",
            assigned_worker_id="W008",
            district="筲箕灣",
            start_time=_time(16),
            end_time=_time(17, 30),
            priority=35,
            notes="需女性同工",
        ),
        FixedService(
            id="FS006",
            elder_id="E006",
            service_code=ServiceCode.MEAL_DELIVERY,
            weekday=3,
            period="AM",
            assigned_worker_id="W007",
            district="北角",
            start_time=_time(11),
            end_time=_time(12),
            priority=65,
        ),
    ]

    escort_requests = [
        EscortRequest(
            id="ER001",
            service_date=week_start,
            period="AM",
            elder_id="E005",
            appointment_time=_time(10, 30),
            destination="QM",
            subject="骨科關節門診",
            transport="的士來回",
            notes="覆診前照 X 光",
        ),
        EscortRequest(
            id="ER002",
            service_date=week_start,
            period="AM",
            elder_id="E006",
            appointment_time=_time(10, 45),
            destination="PY",
            subject="內科",
            transport="巴士來回",
        ),
        EscortRequest(
            id="ER003",
            service_date=week_start + timedelta(days=2),
            period="PM",
            elder_id="E007",
            appointment_time=_time(15, 50),
            destination="PY",
            subject="外科",
            transport="的士",
        ),
    ]

    return MockDataset(
        employees=employees,
        elders=elders,
        fixed_services=fixed_services,
        escort_requests=escort_requests,
        params=ScheduleParams(week_start=week_start),
    )


def get_dataset() -> MockDataset:
    global _DATASET
    if _DATASET is None:
        _DATASET = load_mock_dataset()
    return deepcopy(_DATASET)


def reset_state() -> ScheduleResult:
    global _DATASET, _CURRENT_RESULT
    _DATASET = load_mock_dataset()
    _CURRENT_RESULT = generate_schedule([])
    return deepcopy(_CURRENT_RESULT)


def get_current_result() -> ScheduleResult:
    global _CURRENT_RESULT
    if _CURRENT_RESULT is None:
        _CURRENT_RESULT = generate_schedule([])
    return deepcopy(_CURRENT_RESULT)


def _week_date(week_start: date, weekday: int) -> date:
    return week_start + timedelta(days=weekday - 1)


def _weekday(service_date: date, week_start: date) -> int:
    return (service_date - week_start).days + 1


def _employee_map(dataset: MockDataset) -> dict[str, Employee]:
    return {w.id: w for w in dataset.employees}


def _elder_map(dataset: MockDataset) -> dict[str, Elder]:
    return {e.id: e for e in dataset.elders}


def _is_available(
    worker_id: str,
    service_date: date,
    period: Period,
    entries: list[ScheduleEntry],
    blocked_worker_ids: set[str] | None = None,
) -> bool:
    if blocked_worker_ids and worker_id in blocked_worker_ids:
        return False
    return not any(
        e.worker_id == worker_id
        and e.schedule_date == service_date
        and e.period == period
        and e.status in {"scheduled", "needs_review", "affected"}
        for e in entries
    )


def _gender_ok(worker: Employee, elder: Elder | None, required: Gender = Gender.ANY) -> bool:
    if required == Gender.ANY and elder:
        required = elder.gender_requirement
    if required == Gender.ANY:
        return True
    return worker.gender == required


def _district_score(worker: Employee, district: str | None) -> int:
    if not district:
        return 1
    if district in worker.routes:
        return 0
    return 2


def _find_candidate(
    *,
    service_code: ServiceCode,
    service_date: date,
    period: Period,
    dataset: MockDataset,
    entries: list[ScheduleEntry],
    district: str | None = None,
    elder: Elder | None = None,
    gender_requirement: Gender = Gender.ANY,
    exclude_worker_ids: set[str] | None = None,
) -> Employee | None:
    candidates = []
    for worker in dataset.employees:
        if not worker.can_do(service_code):
            continue
        if not _is_available(worker.id, service_date, period, entries, exclude_worker_ids):
            continue
        if not _gender_ok(worker, elder, gender_requirement):
            continue
        candidates.append(worker)
    candidates.sort(key=lambda w: (_district_score(w, district), w.home_center.value, w.display_name))
    return candidates[0] if candidates else None


def _entry_from_fixed(
    fixed: FixedService,
    dataset: MockDataset,
) -> ScheduleEntry | None:
    employees = _employee_map(dataset)
    elders = _elder_map(dataset)
    worker = employees.get(fixed.assigned_worker_id or "")
    elder = elders.get(fixed.elder_id)
    if not worker:
        return None
    service_date = _week_date(dataset.params.week_start, fixed.weekday)
    return ScheduleEntry(
        id=f"entry-{fixed.id}",
        schedule_date=service_date,
        weekday=fixed.weekday,
        period=fixed.period,
        worker_id=worker.id,
        worker_name=worker.display_name,
        service_code=fixed.service_code,
        elder_id=elder.id if elder else fixed.elder_id,
        elder_name=elder.display_name if elder else fixed.elder_id,
        district=fixed.district,
        start_time=fixed.start_time,
        end_time=fixed.end_time,
        source="template",
        notes=fixed.notes,
    )


def _entry_from_escort(
    escort: EscortRequest,
    worker: Employee,
    dataset: MockDataset,
    *,
    source: str = "escort",
    status: str = "scheduled",
) -> ScheduleEntry:
    elders = _elder_map(dataset)
    elder = elders[escort.elder_id]
    weekday = _weekday(escort.service_date, dataset.params.week_start)
    return ScheduleEntry(
        id=_next_id("escort"),
        schedule_date=escort.service_date,
        weekday=weekday,  # type: ignore[arg-type]
        period=escort.period,
        worker_id=worker.id,
        worker_name=worker.display_name,
        service_code=ServiceCode.ESCORT,
        elder_id=elder.id,
        elder_name=elder.display_name,
        district=elder.district,
        destination=escort.destination,
        start_time=escort.appointment_time,
        source=source,  # type: ignore[arg-type]
        status=status,  # type: ignore[arg-type]
        notes=escort.notes or escort.subject,
    )


def _center_service(center: Center) -> ServiceCode:
    return {
        Center.AMC: ServiceCode.AMC_DUTY,
        Center.MRC: ServiceCode.MRC_DUTY,
        Center.GC: ServiceCode.GC_DUTY,
        Center.HSS: ServiceCode.AMC_DUTY,
    }[center]


def _fill_center_duty(dataset: MockDataset, entries: list[ScheduleEntry]) -> list[AuditItem]:
    audit: list[AuditItem] = []
    week_start = dataset.params.week_start
    for day_offset in range(5):
        service_date = week_start + timedelta(days=day_offset)
        weekday = day_offset + 1
        for period in ("AM", "PM"):
            for center, required_count in dataset.params.center_duty_required.items():
                service_code = _center_service(center)
                current_count = sum(
                    1
                    for e in entries
                    if e.schedule_date == service_date
                    and e.period == period
                    and e.service_code == service_code
                    and e.status != "cancelled"
                )
                for _ in range(max(0, required_count - current_count)):
                    worker = _find_candidate(
                        service_code=service_code,
                        service_date=service_date,
                        period=period,  # type: ignore[arg-type]
                        dataset=dataset,
                        entries=entries,
                        district=center.value,
                    )
                    if not worker:
                        unassigned = ScheduleEntry(
                            id=_next_id("unassigned"),
                            schedule_date=service_date,
                            weekday=weekday,  # type: ignore[arg-type]
                            period=period,  # type: ignore[arg-type]
                            worker_id="",
                            worker_name="待分配",
                            service_code=service_code,
                            district=center.value,
                            source="standby",
                            status="unassigned",
                            notes=f"{center.value} 中心當值未能自動補位",
                        )
                        audit.append(
                            AuditItem(
                                id=_next_id("audit"),
                                kind="unassigned_task",
                                severity="high",
                                reason=f"{service_date} {period} {center.value} 中心當值未能自動分配。",
                                suggested_entry=unassigned,
                            )
                        )
                        continue
                    entry = ScheduleEntry(
                        id=_next_id("center"),
                        schedule_date=service_date,
                        weekday=weekday,  # type: ignore[arg-type]
                        period=period,  # type: ignore[arg-type]
                        worker_id=worker.id,
                        worker_name=worker.display_name,
                        service_code=service_code,
                        district=center.value,
                        source="standby",
                        status="scheduled",
                        notes="系統補齊中心當值",
                    )
                    entries.append(entry)
    return audit


def _apply_leave(
    event: ChangeEvent,
    dataset: MockDataset,
    entries: list[ScheduleEntry],
) -> list[AuditItem]:
    audit_items: list[AuditItem] = []
    if not event.worker_id:
        return audit_items

    fixed_by_entry_id = {f"entry-{f.id}": f for f in dataset.fixed_services}
    employees = _employee_map(dataset)
    elders = _elder_map(dataset)
    original_worker = employees.get(event.worker_id)
    worker_name = original_worker.display_name if original_worker else event.worker_id

    for idx, entry in enumerate(list(entries)):
        if entry.worker_id != event.worker_id or entry.schedule_date != event.change_date:
            continue
        if event.period and entry.period != event.period:
            continue

        affected = entry.model_copy(update={"status": "affected", "notes": f"受請假影響: {event.reason or ''}".strip()})
        entries[idx] = affected

        fixed = fixed_by_entry_id.get(entry.id)
        elder = elders.get(entry.elder_id or "")
        is_exclusive = bool(fixed and fixed.exclusive) or entry.service_code == ServiceCode.EXERCISE
        if elder and elder.exclusive_worker_id == event.worker_id:
            is_exclusive = True

        if is_exclusive:
            cancelled = entry.model_copy(
                update={
                    "id": _next_id("cancelled"),
                    "status": "cancelled",
                    "source": "system_reassigned",
                    "notes": "專屬服務，同工請假時先取消，待人工確認。",
                }
            )
            audit_items.append(
                AuditItem(
                    id=_next_id("audit"),
                    kind="service_cancellation",
                    severity="high",
                    reason=f"{worker_name} 請假，{entry.service_code.value}:{entry.elder_name or ''} 屬專屬服務，建議取消並由人手確認。",
                    original_entry=affected,
                    suggested_entry=cancelled,
                )
            )
            entries.append(cancelled)
            continue

        candidate = _find_candidate(
            service_code=entry.service_code,
            service_date=entry.schedule_date,
            period=entry.period,
            dataset=dataset,
            entries=entries,
            district=entry.district,
            elder=elder,
            exclude_worker_ids={event.worker_id},
        )
        if candidate:
            suggested = entry.model_copy(
                update={
                    "id": _next_id("suggestion"),
                    "worker_id": candidate.id,
                    "worker_name": candidate.display_name,
                    "source": "system_reassigned",
                    "status": "needs_review",
                    "notes": f"建議由 {candidate.display_name} 補位；同區/技能匹配。",
                }
            )
            entries.append(suggested)
            audit_items.append(
                AuditItem(
                    id=_next_id("audit"),
                    kind="replacement_suggestion",
                    severity="warning",
                    reason=f"{worker_name} 請假，建議改派 {candidate.display_name} 處理 {entry.service_code.value}:{entry.elder_name or ''}。",
                    original_entry=affected,
                    suggested_entry=suggested,
                )
            )
        else:
            unassigned = entry.model_copy(
                update={
                    "id": _next_id("unassigned"),
                    "worker_id": "",
                    "worker_name": "待分配",
                    "source": "system_reassigned",
                    "status": "unassigned",
                    "notes": "找不到技能/時間均匹配的替代人手。",
                }
            )
            audit_items.append(
                AuditItem(
                    id=_next_id("audit"),
                    kind="unassigned_task",
                    severity="high",
                    reason=f"{worker_name} 請假，{entry.service_code.value}:{entry.elder_name or ''} 未能自動分配。",
                    original_entry=affected,
                    suggested_entry=unassigned,
                )
            )
            entries.append(unassigned)
    return audit_items


def _apply_service_cancellation(
    event: ChangeEvent,
    dataset: MockDataset,
    entries: list[ScheduleEntry],
) -> list[AuditItem]:
    audit_items: list[AuditItem] = []
    if not event.elder_id:
        return audit_items

    for idx, entry in enumerate(list(entries)):
        if entry.elder_id != event.elder_id or entry.schedule_date != event.change_date:
            continue
        if event.period and entry.period != event.period:
            continue

        cancelled = entry.model_copy(
            update={
                "status": "cancelled",
                "notes": f"長者取消服務: {event.reason or ''}".strip(),
            }
        )
        entries[idx] = cancelled
        center_code = _center_service(_employee_map(dataset)[entry.worker_id].home_center)
        released_worker = _employee_map(dataset)[entry.worker_id]
        standby = ScheduleEntry(
            id=_next_id("standby"),
            schedule_date=entry.schedule_date,
            weekday=entry.weekday,
            period=entry.period,
            worker_id=released_worker.id,
            worker_name=released_worker.display_name,
            service_code=center_code,
            district=released_worker.home_center.value,
            source="system_reassigned",
            status="needs_review",
            notes="服務取消後，建議轉做中心當值/待命。",
        )
        entries.append(standby)
        audit_items.append(
            AuditItem(
                id=_next_id("audit"),
                kind="center_duty_fill",
                severity="info",
                reason=f"{entry.elder_name or event.elder_id} 取消服務，{released_worker.display_name} 空出，建議轉做 {center_code.value}。",
                original_entry=cancelled,
                suggested_entry=standby,
            )
        )
    return audit_items


def _apply_escort_quota_change(
    event: ChangeEvent,
    dataset: MockDataset,
    entries: list[ScheduleEntry],
) -> list[AuditItem]:
    audit_items: list[AuditItem] = []
    if event.new_escort_count is None:
        return audit_items

    period = event.period or "AM"
    escort_entries = [
        e
        for e in entries
        if e.schedule_date == event.change_date
        and e.period == period
        and e.service_code == ServiceCode.ESCORT
        and e.status in {"scheduled", "needs_review"}
    ]
    delta = event.new_escort_count - len(escort_entries)

    if delta > 0:
        for i in range(delta):
            elder = Elder(
                id=f"EXTRA-{i + 1}",
                display_name=f"臨時護送{i + 1}",
                gender=Gender.ANY,
                district="灣仔",
            )
            candidate = _find_candidate(
                service_code=ServiceCode.ESCORT,
                service_date=event.change_date,
                period=period,
                dataset=dataset,
                entries=entries,
                district=elder.district,
                elder=elder,
            )
            if candidate:
                suggested = ScheduleEntry(
                    id=_next_id("extra-escort"),
                    schedule_date=event.change_date,
                    weekday=_weekday(event.change_date, dataset.params.week_start),  # type: ignore[arg-type]
                    period=period,
                    worker_id=candidate.id,
                    worker_name=candidate.display_name,
                    service_code=ServiceCode.ESCORT,
                    elder_id=elder.id,
                    elder_name=elder.display_name,
                    district=elder.district,
                    destination="待補目的地",
                    source="system_reassigned",
                    status="needs_review",
                    notes="護送名額增加，系統建議補位。",
                )
                entries.append(suggested)
                audit_items.append(
                    AuditItem(
                        id=_next_id("audit"),
                        kind="escort_adjustment",
                        severity="high",
                        reason=f"{event.change_date} {period} 護送需要增加至 {event.new_escort_count} 位，建議 {candidate.display_name} 補位。",
                        suggested_entry=suggested,
                    )
                )
            else:
                unassigned = ScheduleEntry(
                    id=_next_id("unassigned"),
                    schedule_date=event.change_date,
                    weekday=_weekday(event.change_date, dataset.params.week_start),  # type: ignore[arg-type]
                    period=period,
                    worker_id="",
                    worker_name="待分配",
                    service_code=ServiceCode.ESCORT,
                    elder_id=elder.id,
                    elder_name=elder.display_name,
                    district=elder.district,
                    destination="待補目的地",
                    source="system_reassigned",
                    status="unassigned",
                    notes="護送名額增加，但沒有可用護送同工。",
                )
                entries.append(unassigned)
                audit_items.append(
                    AuditItem(
                        id=_next_id("audit"),
                        kind="unassigned_task",
                        severity="high",
                        reason=f"{event.change_date} {period} 護送增加，但未能找到第 {len(escort_entries) + i + 1} 位護送人手。",
                        suggested_entry=unassigned,
                    )
                )
    elif delta < 0:
        to_release = escort_entries[delta:]
        for entry in to_release:
            idx = entries.index(entry)
            released = entry.model_copy(update={"status": "affected", "notes": "護送名額減少，原護送安排可釋放。"})
            entries[idx] = released
            worker = _employee_map(dataset)[entry.worker_id]
            standby_code = _center_service(worker.home_center)
            standby = entry.model_copy(
                update={
                    "id": _next_id("standby"),
                    "service_code": standby_code,
                    "elder_id": None,
                    "elder_name": None,
                    "destination": None,
                    "district": worker.home_center.value,
                    "source": "system_reassigned",
                    "status": "needs_review",
                    "notes": "護送少於基準，建議轉中心當值/待命。",
                }
            )
            entries.append(standby)
            audit_items.append(
                AuditItem(
                    id=_next_id("audit"),
                    kind="escort_adjustment",
                    severity="info",
                    reason=f"{event.change_date} {period} 護送減少至 {event.new_escort_count} 位，建議釋放 {worker.display_name} 轉做 {standby_code.value}。",
                    original_entry=released,
                    suggested_entry=standby,
                )
            )
    return audit_items


def generate_schedule(changes: list[ChangeEvent] | None = None) -> ScheduleResult:
    """Generate a schedule from mock data and optional change events."""
    global _CURRENT_RESULT
    dataset = get_dataset()
    entries: list[ScheduleEntry] = []
    audit_items: list[AuditItem] = []

    for fixed in dataset.fixed_services:
        entry = _entry_from_fixed(fixed, dataset)
        if entry:
            entries.append(entry)

    for escort in dataset.escort_requests:
        if not (dataset.params.week_start <= escort.service_date < dataset.params.week_start + timedelta(days=7)):
            continue
        elder = _elder_map(dataset)[escort.elder_id]
        worker = _find_candidate(
            service_code=ServiceCode.ESCORT,
            service_date=escort.service_date,
            period=escort.period,
            dataset=dataset,
            entries=entries,
            district=elder.district,
            elder=elder,
            gender_requirement=escort.gender_requirement,
        )
        if worker:
            entries.append(_entry_from_escort(escort, worker, dataset))
        else:
            unassigned = ScheduleEntry(
                id=_next_id("unassigned"),
                schedule_date=escort.service_date,
                weekday=_weekday(escort.service_date, dataset.params.week_start),  # type: ignore[arg-type]
                period=escort.period,
                worker_id="",
                worker_name="待分配",
                service_code=ServiceCode.ESCORT,
                elder_id=elder.id,
                elder_name=elder.display_name,
                district=elder.district,
                destination=escort.destination,
                source="escort",
                status="unassigned",
                notes="未找到可用護送同工",
            )
            entries.append(unassigned)
            audit_items.append(
                AuditItem(
                    id=_next_id("audit"),
                    kind="unassigned_task",
                    severity="high",
                    reason=f"{escort.service_date} {escort.period} {elder.display_name} 護送未能自動分配。",
                    suggested_entry=unassigned,
                )
            )

    audit_items.extend(_fill_center_duty(dataset, entries))

    for event in changes or []:
        if event.type == ChangeType.LEAVE:
            audit_items.extend(_apply_leave(event, dataset, entries))
        elif event.type == ChangeType.SERVICE_CANCELLED:
            audit_items.extend(_apply_service_cancellation(event, dataset, entries))
        elif event.type in {ChangeType.ESCORT_QUOTA_CHANGED, ChangeType.EXTRA_ESCORT}:
            audit_items.extend(_apply_escort_quota_change(event, dataset, entries))

    unassigned = [e for e in entries if e.status == "unassigned"]
    result = finalize_result(
        ScheduleResult(
            week_start=dataset.params.week_start,
            entries=entries,
            audit_items=audit_items,
            unassigned=unassigned,
        )
    )
    _CURRENT_RESULT = deepcopy(result)
    return result


def get_audit_items() -> list[AuditItem]:
    return get_current_result().audit_items


def apply_audit_decision(audit_id: str, decision: AuditDecision) -> ScheduleResult:
    """Apply a human decision to the in-memory current result."""
    global _CURRENT_RESULT
    result = get_current_result()
    matched = False
    for idx, item in enumerate(result.audit_items):
        if item.id != audit_id:
            continue
        matched = True
        result.audit_items[idx] = item.model_copy(
            update={
                "status": decision.status,
                "human_note": decision.human_note,
                "suggested_entry": decision.edited_entry or item.suggested_entry,
            }
        )
        if decision.edited_entry:
            result.entries.append(decision.edited_entry.model_copy(update={"source": "manual", "status": "scheduled"}))
        elif decision.status == AuditStatus.APPROVED and item.suggested_entry:
            result.entries = [
                e.model_copy(update={"status": "scheduled"})
                if e.id == item.suggested_entry.id and e.status == "needs_review"
                else e
                for e in result.entries
            ]
        break
    if not matched:
        raise KeyError(audit_id)
    _CURRENT_RESULT = finalize_result(result)
    return deepcopy(_CURRENT_RESULT)


def example_changes() -> list[ChangeEvent]:
    return [
        ChangeEvent(
            type=ChangeType.LEAVE,
            change_date=date(2026, 1, 5),
            period="AM",
            worker_id="W001",
            reason="上午請假",
        ),
        ChangeEvent(
            type=ChangeType.ESCORT_QUOTA_CHANGED,
            change_date=date(2026, 1, 5),
            period="AM",
            new_escort_count=3,
            reason="當天護送少於基準",
        ),
        ChangeEvent(
            type=ChangeType.SERVICE_CANCELLED,
            change_date=date(2026, 1, 9),
            period="PM",
            elder_id="E008",
            reason="長者臨時入院",
        ),
    ]

