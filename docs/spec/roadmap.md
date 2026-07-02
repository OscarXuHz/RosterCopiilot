# Roadmap — Mock Demo to Live Operation

**Status:** v0.1 · Five phases. Each phase ends with a demo to the NGO (they asked for iterative demos) and a go/no-go. Guiding constraint: **the NGO keeps its Excel workflow at every phase** — we change what happens between the Excels, not the Excels.

---

## Phase 0 — Mock demo *(current, ~now)*

- **Scope:** existing FastAPI mock + minimal UI; hardcoded dataset upgraded to the `mock_data_spec.md` generator; demo the four flows the NGO named: leave, cancellation, escort ±quota, with audit queue and Excel-ish export.
- **Non-goals:** real data, real Excel parsing, persistence, correct duty counts, gender/skill accuracy.
- **Engineering tasks:** build `mockdata/generator.py` (seeded, per spec); replace singleton state with per-session store; wire benchmark runner skeleton (B0–B2 loose assertions); demo script.
- **Risks:** demo over-promises (mock looks smarter than data allows) → mitigate by showing the clarification packet in the same meeting.
- **Acceptance:** NGO recognises their workflow in the demo; clarification packet + templates handed over; WhatsApp group channel live.
- **Demo story:** "Friday 3pm. 娥 calls in sick for Monday. Watch: her 3 exclusive visits become cancellation cards for your approval; her escort goes to 嫦 because same district; GC duty gap fills from 金. You approve 5 cards, export, done — 4 minutes instead of 45."

## Phase 1 — Excel import/export MVP *(≈4–6 weeks after data received)*

- **Scope:** the full `excel_io_contract.md` importer for the three real workbooks (pathology-tolerant, ambiguity items); canonical SQLite store; entity resolution UI (tick-to-confirm aliases); NGO-format exporter with `RC_*` sheets and change marking; round-trip invariant green (benchmark B8).
- **Non-goals:** any automatic scheduling. Phase 1 only *reads, stores, re-renders and diffs* — trust is built on "it never mangles our file".
- **Engineering tasks:** `importer/*` per sheet family; week-pattern un-mangler; colour reader/writer; alias resolver + `/api/import/*`; templates 1–5 ingestion; PersonAlias encryption; ImportBatch reporting.
- **Risks:** real-file variance beyond the samples (other months, other years) → ask for 3 months of history early; masked-name collisions worse than expected → resolution UI is in-scope, not stretch.
- **Acceptance:** import all NGO-provided months with `silently_dropped_cells=0`; ambiguity count reviewed with NGO ≤ 1 hour; export of an *unmodified* imported week is accepted by the roster owner as "our file".
- **Demo story:** "Upload your real 分工表. Here is everything we understood — and here are the 14 cells we didn't, as questions, not guesses. Now we re-export it: open it in Excel — identical, plus one new sheet summarising what changed since last week."

## Phase 2 — Rule-based scheduler *(≈6–8 weeks)*

- **Scope:** `taskgen` + greedy engine implementing `rescheduling_algorithm.md`; shared hard-constraint validator; review queue UI with approve/edit/reject + bulk actions; ManualOverride persistence; weekly BASELINE fill of floating slots (ESC assignment, duty completion) and event-driven REPAIR; metrics dashboard; benchmarks B0–B9 green with greedy engine.
- **Non-goals:** global optimization (travel/fairness are ranking heuristics, not optimized); multi-week lookahead; automated distribution.
- **Engineering tasks:** rules/validator (single source of feasibility); greedy candidates/rank/chains; audit lifecycle + publish gate; exporter diff marking end-to-end; role-based login; parallel-run tooling (system roster vs human roster comparison view).
- **Risks:** ranking disagrees with roster owner's intuition → weekly parallel-run reviews, tune `rank()` order from rejection notes; data gaps (gender/skills) stall coverage → burn-down list is a first-class UI element.
- **Acceptance:** 4 consecutive weeks of parallel run where ≥80% of suggestions are approved unchanged; blocking review load ≤ 10 items/week; roster owner publishes from the system (even if they re-type into Excel after).
- **Demo story:** "Monday 8:30. Three things happened over the weekend. The queue shows 6 cards, ordered. You approve the batch chain for the 5th escort — every downstream move shown. Publish. The export marks 9 changed cells in orange for the team."

## Phase 3 — CP-SAT optimizer *(≈6 weeks, overlaps Phase 2 hardening)*

- **Scope:** `engine/cpsat.py` per `optimization_model.md`; weekly BASELINE solved globally (travel, fairness, workload now truly optimized); REPAIR_BATCH via solver with min-change objective; solver-vs-greedy shadow comparison; infeasibility diagnosis (assumption cores → readable conflicts); config-weight governance (hash-logged).
- **Non-goals:** replacing the greedy path for single events (it stays — faster and more explainable); any ML.
- **Engineering tasks:** model builder with pruned vars; explanation post-pass; relaxation ladder; warm-start hints; benchmark extension (cpsat ≤ greedy objective on B6; B10 pattern correctness); performance (<30 s baseline).
- **Risks:** solver choices correct but "weird" to humans → template-stability weight (5.6) tuned high, every deviation carries an explanation card; weight tuning whack-a-mole → benchmark ranges lock behaviour.
- **Acceptance:** on 4 real historical weeks, CP-SAT roster dominates the human roster on ≥3 of {travel penalty, duty fairness spread, unassigned, balance} with change-distance ≤ agreed bound and zero hard violations; roster owner prefers it blind on at least 2 weeks.
- **Demo story:** "Same Friday input. The optimizer version: 顯著 less cross-district travel for 匯珠 and 翠君, duty rotation actually even over the month, and here's the diff view against what greedy would have done — 11 cells, each with a why."

## Phase 4 — Live operational deployment *(after NGO sign-off)*

- **Scope:** install on NGO on-prem PC (or agreed host per Q-D1); real-name alias store (encrypted, local); Google Drive upload automation (if Q-D3 yes); optional chat-intake of change events as *drafts* (if Q-D4 yes, usage-cost visible); operational runbook (backup, restore, support channel); training for roster owner + deputy; holiday calendar; go-live with 2-week parallel safety net.
- **Non-goals (v1):** multi-centre tenancy beyond this NGO; payroll/attendance; elder-facing notifications; autonomous publishing (human publish stays forever).
- **Engineering tasks:** packaging (single installer / dockerless option for a Windows PC), auth hardening, backup job, Drive integration, monitoring-lite (weekly health email), data-retention policy per privacy note.
- **Risks:** single-PC fragility → nightly file backups to NGO's Drive (encrypted); key person dependency → train two users, write the runbook in Cantonese; scope creep from other centres ("其他中心都有呢個系統") → park as v2 pipeline.
- **Acceptance:** 8 consecutive weeks fully scheduled through the system; measured admin time for weekly rostering reduced ≥50% vs the baseline the NGO reports in Template 5 col G; zero privacy incidents; NGO can restore from backup unaided.
- **Demo story (go-live review):** "Two months of real weeks: 190 events processed, 96% of suggestions approved, average Friday roster time down from ~a day to under 2 hours, every change traceable to who approved it and why."

---

## Cross-phase dependencies

```
Templates returned (A-questions) ──▶ Phase 1 import accuracy ──▶ Phase 2 eligibility
Duty requirements confirmed (Q-A3) ─▶ Phase 2 coverage rule ──▶ Phase 3 hard floor
Real change cases (Template 5) ────▶ Phase 2 acceptance ─────▶ Phase 3 comparison
```

Standing cadence: fortnightly demo; clarification burn-down reviewed each demo; no phase starts its acceptance run with open blocking questions from section A of the packet.
