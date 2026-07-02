# RosterCopiilot Technical Specification v0.1

**Date:** 2026-07-01 · **Audience:** implementing engineers + project stakeholders.
This is the umbrella document: each section states the essentials and binds to a detailed sub-document in `docs/spec/`. The sub-documents are normative; this file resolves precedence and gives the reading order.

| # | Section | Normative document |
|---|---|---|
| 1 | Problem framing & current workflow | this file |
| 2 | Excel interpretation | `excel_semantics.md`, `data_dictionary.md` |
| 3 | Canonical data model | `canonical_schema.md`, `schema.json` |
| 4 | Rulebook | `rulebook.md` |
| 5 | Optimization model | `optimization_model.md` |
| 6 | Rescheduling algorithm | `rescheduling_algorithm.md` |
| 7 | Human review & audit | `human_review_policy.md`, `audit_item_schema.json` |
| 8 | Excel I/O contract | `excel_io_contract.md` |
| 9 | API & architecture | `system_architecture.md`, `api_contract.md` |
| 10 | Mock data & benchmark | `mock_data_spec.md`, `benchmark_cases.json`, `evaluation_metrics.md` |
| 11 | Clarification questions | `clarification_packet.md`, `ngo_data_request_templates.md` |
| 12 | Roadmap | `roadmap.md` |

---

## 1. Problem framing

**Client:** 循道衛理中心 社區照顧服務 (Hong Kong Island). ~50 care workers, ~400 elders/week, five teams (three centres — 2 Wan Chai, 1 North Point — plus two home-care teams EH/IH), Mon–Sat, weekly roster published every Friday for the following week.

**The job to be done:** the weekly roster is a manual Excel craft. A colleague drafts, the supervisor reworks, it goes to Google Drive. The painful part is not the fixed template — it is the weekly interaction of: escort appointments (0–5 per half-day vs a 4-slot baseline), staff leave, elder cancellations/hospitalisations, centre-duty coverage across three centres, gender constraints on body-contact services, worker–elder exclusive bindings (exercise training), route-qualified meal delivery, and travel-time geography from Wan Chai to Siu Sai Wan. Today this consumes "the most administrative time of anything the centre does" (transcript).

**Objective:** convert this human-experience workflow into a **computable, explainable, auditable, and eventually optimizable** system, without forcing the NGO off Excel. The system drafts; a human reviews, edits, approves, publishes. Every automatic decision carries an explanation traceable to a rule and a source cell.

**Non-negotiable stances** (asserted throughout the sub-documents):
- Do not assume clean data — the real files contain corrupted week patterns, inconsistent name masking, constraints hidden in free text, and mid-year staff transitions.
- Never invent business rules — 38 rules are extracted with evidence classes (explicit/implied/inferred) in `rulebook.md`; 12 open questions are tracked, not guessed.
- Fail-safe on unknowns — unknown gender/skill means *ineligible + flagged*, not *assumed fine*.
- Human override always wins and is always recorded.

## 2. Current workflow & Excel interpretation (summary)

Three workbooks (analysed in `excel_semantics.md`, field-level in `data_dictionary.md`):

1. **照顧員工作分工表 (division sheet)** — the master weekly template *and* output format. Worker columns × weekday/period rows; two session slots per half-day; cell grammar `CODE:Elder(UNIT)`; **fill colours are semantic** (yellow = floating escort slots, per-centre duty colours, gray = departing staff); working-hours row; Saturday A/B rotation. Plus a case-transfer audit log and a new-staff skill/route tick matrix.
2. **HC 時間表** — monthly expansion of home-cleaning patterns (weeks 1,3 / 2,4 / 單月/雙月…), including Excel-corrupted pattern cells (`1,5` stored as a date) — evidence that import must un-mangle and flag.
3. **護送個案總表** — per-month escort demand log, per day/half-day, with constraints (pickup lead, preferences like 只要娥姐/建議安排菲菲) buried in remarks, and a cancel/change section.

Key structural insight: the division sheet is simultaneously the input template, the output artifact, and the constraint carrier. The canonical model (§3) exists precisely to break that conflation while the Excel I/O contract (§8) preserves it at the boundary.

## 3. Canonical data model (summary)

18 entities (`canonical_schema.md`, JSON Schema in `schema.json`): Employee, Elder, ServiceType, WorkerSkill, WorkerRouteQualification, OrgUnit, FixedService, EscortRequest, CenterDutyRequirement, WorkerAvailability, LeaveEvent, ServiceCancellationEvent, EscortQuotaOverride, ScheduleEntry, ScheduleVersion, AuditItem, ManualOverride, ExportJob (+ PersonAlias, ImportBatch, Gazetteer, TravelMatrix, ChangeEvent envelope).

Distinctive choices: effective-dating on every relationship; half-day period + session-index slot model; demand separated from assignment; per-field provenance (`source_ref`, `parse_confidence`); pseudonymisation boundary (real names only in an encrypted NGO-local table). Every field is annotated with whether the current Excel files can supply it and whether NGO clarification is required — worker/elder **gender and the full skill matrix are the two blocking data gaps**.

## 4. Rulebook (summary)

38 operative rules + 12 tracked unknowns (`rulebook.md`), each with evidence, formal interpretation, and priority tier (P0 never violate → P4 tie-break). Headlines: skill/gender/exclusivity/no-double-booking are P0; exclusive services **cancel rather than substitute** when the bound worker is absent (with mandatory human confirmation); centre duty is the top of the priority cascade and the absorber of freed capacity; escort baseline 4/half-day flexes 0–5 with chain-impact reporting; travel *time* (not distance) is the geographic objective; published rosters are repaired minimally, never reshuffled; weekly batch is systematic while micro-changes stay manual but recorded.

## 5. Optimization model (summary)

CP-SAT formulation (`optimization_model.md`): assignment Bools `x[w,t]` over eligibility-pruned pairs, cover-or-flag (`u[t]`) so shortage becomes ranked unassigned items instead of infeasibility; hard constraints for availability, session/interval no-overlap, duty floors, pins; soft objective tiers — unassigned π (duty 1000 > escort 800 > fixed 500 > misc 200), travel + ping-pong penalties, duty fairness & affinity, template stability, preferences, workload balance, and min-change distance in REPAIR mode. Explainability is a required output: per-entry explanations, per-unassigned diagnoses, assumption-based conflict reports, diff reports, metric blocks. Relaxation ladder is fixed and audited; skill/gender/exclusivity/availability are never auto-relaxed.

## 6. Rescheduling (summary)

Event-driven repair (`rescheduling_algorithm.md`): five-stage pipeline (detect affected → generate candidates → deterministic explainable ranking → propose as AuditItems → human decision → new version). Nine scenarios specified with pseudocode, including exclusive-worker absence (cancel/override/reschedule-occurrence options), escort over-quota displacement chains (depth ≤ 2, atomic approval), open-ended hospitalisation suspension, and multi-event batches (free-before-consume ordering, dependency-grouped approvals, escalation to solver REPAIR when > K entries move). The greedy path *is* Phase 2's product; Phase 3 keeps it for single events and validates both paths with one shared hard-constraint validator.

## 7. Human review & audit (summary)

`human_review_policy.md`: blocking triggers (exclusive cancellations, any unassigned, duty under-coverage, displacement chains, relaxations, rule conflicts) gate publication; warnings are bulk-approvable; info is notify-only; undecided warnings escalate at the Friday deadline. Approve/edit/reject flow writes ManualOverrides (entry/week/recurring scopes) that survive re-solves and feed a monthly template fold-in digest. Full traceability chain from Excel cell → import → entry → audit item → decision → next version. Review workload is itself a metric with targets.

## 8. Excel I/O contract (summary)

`excel_io_contract.md`: which sheets/patterns are parsed, which fields are read vs inferred (each inference confidence-tagged), colour semantics preserved on export, `RC_*` additive sheets (change summary, review pack, unassigned, hidden meta), changed-cell marking via borders+comments (fills stay semantic), ambiguity handling with a zero-silent-drop guarantee, and round-trip invariants (import→export identity; export→import zero ambiguity).

## 9. Architecture & API (summary)

`system_architecture.md`: keep the mock's shapes, replace its in-memory singletons with SQLite (SQLModel), split into importer / rules-validator / taskgen / engine (greedy | cpsat behind one Protocol) / review / exporter / metrics. Engines are pure functions; the validator is the single source of feasibility; LLM features (chat-based event intake, remark parsing) sit **outside** the decision path, off by default, pseudonymised-only — weekly scheduling runs offline at zero marginal cost, matching the NGO's cost sensitivity. `api_contract.md` defines the full REST surface (import, master data, events, solve/repair/versions/publish, review queue/decisions/overrides, export jobs, metrics) with mock-compat aliases.

## 10. Mock data & benchmark (summary)

`mock_data_spec.md`: 52 workers / 380 elders / 3 centres with realistic skill segments, gender scarcity pressure, week-pattern mix, escort week including over- and under-quota days, and 18 injected data pathologies mirroring the real files. `benchmark_cases.json`: B0 baseline + B1–B7 event scenarios + B8 importer round-trip + B9 gender-scarcity stress + B10 pattern-expansion correctness; hard invariants exact, quality metrics as ranges. `evaluation_metrics.md` defines the 10 required metrics (hard_constraint_violations=0 always, coverage, unassigned, duty coverage, escort fulfilment, travel penalty, balance, change distance, review count, exclusive-cancel count) plus live-operation health measures.

## 11. Clarifications (summary)

`clarification_packet.md`: 7 blocking questions (gender, full skill matrix, duty requirements, week-of-month definition, Saturday A/B anchor, degraded-mode policy, master lists), 10 optimization-quality questions, 10 mockable-defaults, 6 deployment/privacy questions — all with tick-box answers. `ngo_data_request_templates.md`: five pre-filled Excel templates (employee skills, elder requirements, service-code dictionary, centre-duty rules, real change cases) whose columns map 1:1 to canonical fields and whose returns flow through the normal importer.

## 12. Roadmap (summary)

`roadmap.md`: Phase 0 mock demo (now) → Phase 1 Excel import/export MVP (trust: "it never mangles our file") → Phase 2 rule-based scheduler with parallel-run acceptance (≥80% suggestions approved unchanged over 4 weeks) → Phase 3 CP-SAT optimizer (must dominate the human roster on ≥3 quality metrics with bounded change distance) → Phase 4 on-prem live deployment (8 clean weeks, ≥50% admin-time reduction, restorable backups). No phase starts acceptance with open blocking questions.

---

## Precedence & change control

Where documents disagree, precedence: `rulebook.md` (business truth) > `canonical_schema.md`/`schema.json` (data truth) > `optimization_model.md`/`rescheduling_algorithm.md` (behaviour) > everything else. All spec changes go through PRs referencing rule ids; NGO answers to the clarification packet are folded in as rule-status upgrades (U→E) with the answer archived as evidence.

## Known limitations of v0.1

- Built from **one month of each workbook** and one meeting transcript; volume and seasonal variance unverified (3 months of history requested).
- The transcript is a noisy auto-transcription; every rule sourced only from it is marked and double-checked against the PDF digest where possible.
- Duty requirements, Saturday semantics, week-of-month definition, and all gender data are pending NGO confirmation — the model runs today only on fail-safe defaults plus the mock dataset.
- `New/docs/problem_description.md` referenced in the project brief does not exist in the workspace; if it exists elsewhere it should be reconciled against this spec.
