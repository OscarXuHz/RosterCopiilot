"""Impact analysis helpers for the mock scheduler.

This module keeps the explanation layer separate from the placement logic. The
mock scheduler decides what changed; this module turns those changes into
frontend-friendly summaries and human review messages.
"""
from __future__ import annotations

from collections import Counter

from ..models import AuditItem, ImpactItem, ScheduleEntry, ScheduleResult, ServiceCode


def summarize_entries(
    entries: list[ScheduleEntry],
    audit_items: list[AuditItem],
    unassigned: list[ScheduleEntry],
) -> dict[str, int]:
    service_counts = Counter(e.service_code.value for e in entries if e.status != "cancelled")
    return {
        "total_entries": len(entries),
        "scheduled": sum(1 for e in entries if e.status == "scheduled"),
        "needs_review": sum(1 for e in entries if e.status == "needs_review"),
        "affected": sum(1 for e in entries if e.status == "affected"),
        "cancelled": sum(1 for e in entries if e.status == "cancelled"),
        "unassigned": len(unassigned),
        "audit_pending": sum(1 for a in audit_items if a.status == "pending"),
        "escort_entries": service_counts.get(ServiceCode.ESCORT.value, 0),
        "center_duty_entries": sum(
            service_counts.get(code.value, 0)
            for code in (ServiceCode.AMC_DUTY, ServiceCode.MRC_DUTY, ServiceCode.GC_DUTY)
        ),
    }


def build_impact_from_audit(audit_item: AuditItem) -> ImpactItem:
    affected_entry_ids: list[str] = []
    affected_worker_ids: list[str] = []
    affected_elder_ids: list[str] = []
    for entry in (audit_item.original_entry, audit_item.suggested_entry):
        if not entry:
            continue
        affected_entry_ids.append(entry.id)
        affected_worker_ids.append(entry.worker_id)
        if entry.elder_id:
            affected_elder_ids.append(entry.elder_id)

    title_by_kind = {
        "replacement_suggestion": "需要確認替代人手",
        "service_cancellation": "服務取消需要確認",
        "unassigned_task": "有任務未能自動分配",
        "escort_adjustment": "護送名額變動",
        "center_duty_fill": "中心當值補位建議",
    }

    return ImpactItem(
        id=f"impact-{audit_item.id}",
        severity=audit_item.severity,
        title=title_by_kind.get(audit_item.kind, "排班變動"),
        description=audit_item.reason,
        affected_entry_ids=sorted(set(affected_entry_ids)),
        affected_worker_ids=sorted(set(affected_worker_ids)),
        affected_elder_ids=sorted(set(affected_elder_ids)),
    )


def finalize_result(result: ScheduleResult) -> ScheduleResult:
    impacts = [build_impact_from_audit(item) for item in result.audit_items]
    result.impacts = impacts
    result.summary = summarize_entries(result.entries, result.audit_items, result.unassigned)
    return result

