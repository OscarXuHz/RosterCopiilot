# Human Review & Audit Policy

**Status:** v0.1 · The system proposes; the roster owner disposes. This document defines when review is mandatory, how decisions flow, and how traceability is preserved. Machine-readable item schema: `audit_item_schema.json`.

Design stance (from the transcript): the NGO's supervisor already reviews a colleague's draft today ("同事初稿，跟住我就再做，跟住就發出去"). The system replaces the *draft*, not the *review*. Nothing reaches elders or workers without a human having seen — or deliberately bulk-approved — it.

---

## 1. When human review is required

**Blocking** (publication of the affected day/week is blocked until decided):

| Trigger | Item kind | Why |
|---|---|---|
| Exclusive service cancellation (RB-EXCL-02) | `exclusive_cancellation` | Elder-facing commitment; NGO must control communication |
| Any unassigned task (`u[t]=1`) | `unassigned_task` | Service would silently not happen |
| Centre duty under-coverage (RB-DUTY-01) | `duty_under_coverage` | Highest-priority rule in the NGO's own cascade |
| Displacement chain (escort over quota etc.) | `displacement_chain` | Multi-entry atomic change; downstream impact |
| Solver relaxation used (`optimization_model.md` §7) | `constraint_relaxed` | A hard rule was softened to find any solution |
| Rule conflict detected (two rules demand contradictory placements) | `rule_conflict` | Cannot be resolved by policy |

**Non-blocking, must-review** (roster publishes with items open, flagged in export):

| Trigger | Item kind |
|---|---|
| Replacement suggestion after leave | `replacement_suggestion` |
| Escort quota change handling (up or down) | `escort_adjustment` |
| Gender constraint uncertainty (`gender_ok_unverified` — worker or elder gender unknown) | `data_gap_gender` |
| Skill uncertainty (candidate excluded/included on `unknown` skill) | `data_gap_skill` |
| Low-confidence Excel parse (unparsed cell, un-mangled week pattern, ambiguous name match) | `import_ambiguity` |
| Template deviation (5.6 stability penalty paid) | `template_deviation` |

**Notify-only** (info feed, auto-approved):
refill of freed worker into duty (`refill`), auto-cancelled escorts of a hospitalised elder, idle release with no gap to fill.

## 2. Severity levels

| Level | Meaning | UI behaviour |
|---|---|---|
| `high` | Service delivery or safety at stake; blocking set above | Red; top of queue; blocks publish of affected scope |
| `warning` | Judgment call; system has a default it believes in | Amber; bulk-approve allowed per kind |
| `info` | FYI; auto-approved after publish | Gray; collapsible feed |

Escalation: any `warning` item older than the publication deadline (Friday cut-off) without decision escalates to `high` — silence must not publish surprises.

## 3. Approve / edit / reject flow

```
pending ──approve──▶ approved: suggested_entry status needs_review→scheduled
   │
   ├────edit──────▶ edited:   reviewer modifies entry (worker/time/…);
   │                          hard-constraint validator re-checks; violation ⇒ warn + require override note;
   │                          saved as ManualOverride(scope=entry, origin_audit_item_id=this)
   │
   └────reject────▶ rejected: suggested entries withdrawn; task returns to
                              unassigned/cancelled state; system generates the
                              next-best alternative once (no loops); if none →
                              stays as high-severity unassigned
```

Rules:
- Decisions are per-item; `displacement_chain` and `depends_on` groups decide atomically (approve-all or reject-all).
- Bulk approval allowed only for `warning`/`info` of the same kind; each bulk action records one decision with the item list.
- Every decision captures `decided_by`, `decided_at`, optional `note`; rejects **require** a note (that note is training data for better ranking later).
- A reviewer edit that violates a hard rule is allowed only with `override_note` — the system never blocks the human, it documents them (design principle: explainability over enforcement).

## 4. How manual overrides affect future schedules

1. **Entry-scope** override → applies to that occurrence only; next weekly solve ignores it.
2. **Week-scope** → pin/forbid for the remainder of the week's versions.
3. **Recurring** → written back as `ManualOverride(scope=recurring)`; the weekly task generator applies it like template data (e.g. "從今以後 L明 只由美紅跟" becomes a `must` binding). Recurring overrides appear in a monthly digest so the template owner can fold them into the real template (or the system proposes updating `FixedService.assigned_worker_id` after 4 consecutive identical overrides — suggestion only).
4. Overrides are effective-dated and never deleted — superseded ones get `effective_to`.

## 5. Explaining recommendations

Every suggested entry carries `explanation` composed from templated fragments (no free-form generation in the decision path):

- eligibility summary: "美紅: HC-qualified ✓, 女 ✓ (elder requires F), available Tue AM ✓"
- ranking justification: "chosen over 翠君: same-day district match (柴灣, +0 min travel vs +35 min)"
- cascade provenance: "freed because Y珍 hospitalised (event #E-2031); fills GC duty gap (required 2, had 1)"
- data caveats: "note: 美紅's ESC skill is unverified — see data gap item #A-114"

The audit item stores `evidence_refs[]` (rule ids, event ids, source cells) so any explanation can be traced to `rulebook.md` and the original Excel cell.

## 6. Traceability chain

```
Excel cell (source_ref) → ImportBatch → FixedService/EscortRequest
      → ScheduleEntry(origin_*) → AuditItem(evidence_refs) → Decision(by/at/note)
      → ManualOverride(origin_audit_item_id) → next ScheduleVersion(parent_version_id, trigger_event_ids)
```

Retention: versions and audit items are append-only; exports embed `version_id` in the workbook (hidden metadata sheet) so a printed roster can always be traced back.

## 7. Review workload budget

Target (per benchmark suite): a normal week ≤ 10 blocking items, ≤ 30 bulk-approvable warnings; a heavy-disruption day (3 simultaneous events) ≤ 8 blocking items. `manual_review_count` is a first-class metric (`evaluation_metrics.md`) — if the system floods the reviewer, it has failed at its actual job of saving admin time.
