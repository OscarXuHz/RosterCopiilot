# System Architecture

**Status:** v0.1 · Review of the existing mock MVP and the target architecture through Phase 3. Companion: `api_contract.md`.

## 1. Existing mock MVP — assessment

`backend/app/` (FastAPI + Pydantic, in-memory):

| Piece | Verdict | Notes |
|---|---|---|
| `models.py` | **Keep, evolve** | Good instincts (ScheduleEntry status lifecycle, AuditItem with original/suggested/alternatives). Gaps vs canonical model: no ScheduleVersion, no session_index, no ManualOverride persistence, week_pattern is a bare string, no effective dating, `Employee.can_do` hardcodes rules, Center enum conflates centres with HSS |
| `services/mock_scheduler.py` | **Replace incrementally** | Global mutable singletons (`_CURRENT_RESULT`, `_DATASET`) — fine for demo, must go; greedy `_find_candidate` ranking is a rough draft of `rescheduling_algorithm.md#rank` |
| `services/impact_analyzer.py` | Keep pattern | Explanation layer separated from placement — correct instinct, extend to templated explanations |
| `services/excel_export.py` | Keep for review-pack; **does not** meet RB-PUB-02 (invents its own layout instead of the NGO's) | becomes `RC_*` sheets; NGO-format exporter is new work |
| `api/*` | Keep shape | Routes map well to target API; add versions/import/overrides |
| State | In-memory only | No persistence, no concurrency safety — Phase 1 fixes |

## 2. Target module layout

```
backend/app/
├── domain/            # canonical entities (pydantic) ⇔ schema.json, validation
├── store/             # persistence: SQLite via SQLModel (Phase 1) — single-file DB
│                      # fits NGO on-prem; Postgres-ready via SQLModel if ever hosted
├── importer/          # excel_io_contract §1–2,6: one parser per sheet family
│   ├── division.py    # 恆常服務 grammar + colours + comments
│   ├── hc_timetable.py
│   ├── escort.py      # incl. 備註 constraint mining
│   ├── skills.py, transfers.py
│   └── resolve.py     # alias/entity resolution + ambiguity items
├── rules/             # rulebook.md as code: eligibility, availability, validator
│   └── validator.py   # THE shared hard-constraint checker (solver, greedy,
│                      #   human edits all go through it)
├── taskgen/           # weekly task expansion (patterns, effective dates, overrides)
├── engine/            # SchedulerEngine interface + implementations
│   ├── base.py        # solve(week, snapshot, mode, baseline?) -> Proposal
│   ├── greedy.py      # Phase 2: rescheduling_algorithm.md pseudocode
│   └── cpsat.py       # Phase 3: optimization_model.md (OR-Tools)
├── review/            # audit items, decisions, ManualOverride application
├── exporter/          # NGO-format writer + RC_* sheets + diff marking
├── metrics/           # evaluation_metrics.md calculators
├── mockdata/          # generator (mock_data_spec.md) + benchmark runner
└── api/               # FastAPI routers (api_contract.md)
frontend/              # review UI (existing index.html → SPA later)
```

## 3. Service boundaries

- **Importer** is pure: files in → canonical rows + ambiguity items out; never writes schedules.
- **Engine** is pure and swappable: `(snapshot, events, config) → Proposal{entries, audit_items, metrics}`; no I/O, no store access. Greedy and CP-SAT implement the same interface; **both are validated by `rules/validator.py` before anything is shown** — a proposal that fails validation is a bug, not a review item.
- **Review** owns state transitions (pending→…) and is the only writer of ManualOverride.
- **Exporter** reads published versions only.
- **AI/LLM sits outside the decision path.** Per the transcript's cost discussion, weekly generation must run without AI ("如果咁樣嘅改動就唔需要透過AI"). Optional LLM adapters (Phase 3+, feature-flagged): natural-language change-event intake (Teams/WhatsApp message → ChangeEvent draft) and free-text 備註 pre-parsing — always producing *drafts flagged for review*, pseudonymised aliases only (RB-PRIV-01).

## 4. Data persistence

- SQLite file per deployment (`data/roster.db`), append-only tables for versions/audit/overrides/import batches; nightly file backup (copy) — the NGO already lives with files.
- Real names: `person_alias` table encrypted at rest (SQLCipher or app-level Fernet), key held by the NGO machine only; exports/API never join it except the NGO-local UI.
- All timestamps HKT; week starts Monday.

## 5. Scheduler engine interface

```python
class SchedulerEngine(Protocol):
    def solve(self, req: SolveRequest) -> Proposal: ...

@dataclass
class SolveRequest:
    week_start: date
    snapshot: CanonicalSnapshot          # frozen input data (import + events + overrides)
    mode: Literal["BASELINE", "REPAIR", "REPAIR_BATCH"]
    baseline: ScheduleVersion | None     # required for REPAIR*
    events: list[ChangeEvent]
    config: SolverConfig                 # weights, priorities, limits (hash-logged)

@dataclass
class Proposal:
    entries: list[ScheduleEntry]         # statuses: scheduled/needs_review/cancelled/unassigned
    audit_items: list[AuditItem]
    metrics: dict
    diff: DiffSummary | None
```

The API layer turns an accepted Proposal into a `ScheduleVersion(kind=…, parent=…)`. CP-SAT integration point = one new `engine/cpsat.py` implementing this Protocol; nothing else changes (the review UI, exporter and metrics are engine-agnostic).

## 6. Human review workflow (system view)

```
import → snapshot → engine.solve → Proposal → store as draft version
   → review queue (blocking first) → decisions (+ManualOverride writes)
   → re-validate → publish (freeze) → export → distribute (manual upload Phase 1-3)
Intra-week: events → engine.solve(REPAIR, baseline=published) → repeat from queue
```

Concurrency: single-writer model (one roster owner at a time per week); optimistic locking via version ids is enough — this is a 1–3 user system.

## 7. Deployment shape

- Phase 0–2: single process (uvicorn) on an NGO Windows PC or our laptop for demos; SQLite; no external calls.
- Phase 3: same + OR-Tools wheel (pure local).
- Phase 4 options (deployment questions Q-D1..D4): on-prem PC (default, matches privacy stance) vs. HK-region cloud; Google Drive upload automation; optional LLM API usage with per-call cost display (the NGO explicitly asked about usage-based cost).
- No auth in Phase 0–1 (localhost); Phase 2+: simple login + role (owner/reviewer/viewer) — the transcript distinguishes office staff who self-schedule from managed front-line staff.

## 8. Non-functional targets

Baseline solve <30 s, repair <5 s (per `optimization_model.md` §7-8); import of 3 workbooks <10 s; memory <1 GB; fully offline-capable; deterministic under fixed seed/config for demos and audits.
