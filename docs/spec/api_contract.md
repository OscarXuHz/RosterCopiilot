# API Contract

**Status:** v0.1 · REST/JSON, FastAPI. Extends the existing mock (`/api/schedule`, `/api/changes`, `/api/export`, `/api/health`) — existing routes keep working during Phase 1 migration, marked *(mock-compat)*. All payloads conform to `schema.json` / `audit_item_schema.json`. Errors: RFC 7807 problem+json. IDs are opaque strings. Times HKT.

## 1. Health & meta

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | liveness + mode (mock/live) + engine + config hash |
| GET | `/api/meta/service-types` | ServiceType reference table |
| GET | `/api/meta/config` | solver weights/priorities (read-only view) |

## 2. Import

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/import/workbooks` | multipart upload of 1–3 workbooks → `ImportBatch` (async if >5 s) |
| GET | `/api/import/batches/{id}` | batch status + stats (`parsed/inferred/flagged/ignored`, sheet list) |
| GET | `/api/import/batches/{id}/ambiguities` | `import_ambiguity` audit items for this batch |
| POST | `/api/import/resolutions` | resolve alias/entity ambiguities `{ambiguity_id, resolution}` |

## 3. Master data (canonical)

| Method | Path | Purpose |
|---|---|---|
| GET/POST/PATCH | `/api/employees`, `/api/employees/{id}` | list/create/update (effective-dated); `?include=skills,routes` |
| PUT | `/api/employees/{id}/skills` | replace skill rows (bulk, from NGO template) |
| GET/POST/PATCH | `/api/elders`, `/api/elders/{id}` | as above; `?needs_clarification=true` filter |
| GET/POST/PATCH | `/api/fixed-services` | recurring commitments; PATCH supports `effective_from` |
| GET/POST/PATCH/DELETE | `/api/escort-requests` | weekly escort demand; DELETE = status→cancelled |
| GET/PUT | `/api/duty-requirements` | CenterDutyRequirement matrix (PUT bulk replaces, `source=ngo_confirmed`) |
| GET | `/api/data-gaps` | outstanding unknowns (gender/skill/unit) — the clarification burn-down list |

## 4. Events

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/events` | create ChangeEvent (leave/cancellation/escort_quota/escort_new/…) — validates payload per type |
| GET | `/api/events?week=YYYY-MM-DD&unprocessed=true` | queue view |
| GET | `/api/changes/examples` *(mock-compat)* | canned demo events |

## 5. Scheduling

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/schedule/solve` | `{week_start, mode: BASELINE, engine?: greedy|cpsat, config_overrides?}` → draft `ScheduleVersion` (202 + poll if long) |
| POST | `/api/schedule/repair` | `{baseline_version_id, event_ids[] | events[]}` → draft repair version; auto-picks greedy vs batch solver per policy §9.4 |
| GET | `/api/schedule/versions?week=` | version tree (id, kind, parent, status, metrics, diff_summary) |
| GET | `/api/schedule/versions/{id}` | full version `?include=entries,audit,metrics,diff` |
| GET | `/api/schedule/versions/{id}/entries?worker=&date=&status=` | filtered entries |
| POST | `/api/schedule/versions/{id}/publish` | freeze; **409** with blocking-item list if any blocking audit item pending |
| POST | `/api/schedule/versions/{id}/entries/{eid}` | manual edit (validated; violations require `override_note`) → new `manual_edit` version |
| GET | `/api/schedule/current` *(mock-compat)* | latest version for current week |
| POST | `/api/schedule/generate` *(mock-compat)* | alias of solve(BASELINE) |
| POST | `/api/schedule/reset` *(mock-compat, mock mode only)* | reload mock dataset |

## 6. Review

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/review/queue?version=&severity=&kind=&blocking=true` | ordered queue (blocking first, then severity, then created_at) |
| GET | `/api/review/items/{id}` | full item incl. alternatives, chain, depends_on |
| POST | `/api/review/items/{id}/decision` | `{status: approved|rejected|edited, note?, override_note?, edited_entry?}` — 422 if reject without note; chains decide atomically via `depends_on` |
| POST | `/api/review/bulk-decision` | `{kind, item_ids[], status}` — warning/info only |
| GET | `/api/overrides?active=true&scope=recurring` | ManualOverride list |
| POST | `/api/overrides` / DELETE (sets `effective_to`) | manage standing overrides |
| GET | `/api/review/digest?month=` | monthly recurring-override digest (template fold-in suggestions) |

## 7. Export

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/export/jobs` | `{version_id, format: division_sheet|escort_sheet|hc_sheet|review_pack, options:{mark_changes:true,…}}` → ExportJob |
| GET | `/api/export/jobs/{id}` | status; `GET /file` → xlsx download |
| GET | `/api/export/current` *(mock-compat)* | one-shot current-version review pack |

## 8. Metrics & benchmarks

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/metrics/versions/{id}` | full metric block (`evaluation_metrics.md`) |
| GET | `/api/metrics/weekly-report?week=` | dashboard aggregate incl. review workload |
| POST | `/api/benchmark/run` *(dev only)* | run `benchmark_cases.json` suite → pass/fail table |

## 9. Conventions

- **Versioning:** any mutation of schedule state creates a new immutable `ScheduleVersion`; clients always operate on version ids, never "the schedule".
- **Blocking semantics:** `publish` is the only gate; drafts may contain anything.
- **Idempotency:** POSTs accept `Idempotency-Key` header (events may arrive twice from chat-based intake later).
- **Pagination:** `?limit/offset`, default 200 — dataset is small.
- **Privacy:** API returns aliases only; a separate NGO-local endpoint namespace `/api/local/aliases` (bound to 127.0.0.1) resolves real names for the on-site UI (RB-PRIV-01).
- **AuthZ (Phase 2+):** roles owner/reviewer/viewer; publish & override require owner.
