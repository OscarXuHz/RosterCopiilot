# Excel Round-Trip Contract

**Status:** v0.1 · Pipeline: **Excel input → canonical data → schedule result → Excel output.** The NGO keeps working in Excel/Google Drive (RB-PUB-02); the system must meet them there. Builds on `excel_semantics.md` / `data_dictionary.md`.

```
 NGO workbooks ──▶ [IMPORTER] ──▶ ImportBatch + canonical rows + import_ambiguity items
                                        │
                                  [TASK GENERATOR] ─▶ weekly tasks
                                        │
                                   [SOLVER/REPAIR] ─▶ ScheduleVersion
                                        │
 NGO workbooks ◀── [EXPORTER] ◀── published version (+ audit pack)
```

## 1. Imported sheets and patterns

| Sheet | Imported? | What is parsed |
|---|---|---|
| 分工表 · `恆常服務` | ✔ core | worker columns (R2 + fills), weekday/period blocks, session slot-pairs, assignment-cell grammar, detail cells (time/district/manager), hours row R108, Saturday A/B row R93, cell comments |
| 分工表 · `個案轉移紀錄_*` | ✔ | transfer rows → effective-dated FixedService updates (TBC rows → review only) |
| 分工表 · `新同工跟服務紀錄表` | ✔ | skill/route tick matrix → WorkerSkill / WorkerRouteQualification |
| HC 時間表 · month sheets | ✔ | Case/單位/節數/時間/照顧員/日期/更改 blocks incl. 其他服務 section; used to *validate & enrich* FixedServices (patterns, exceptions), not as an independent truth |
| 護送總表 · month sheets | ✔ core | day/period grid → EscortRequest; 備註 constraint mining (lead time, preferences); bottom 取消/更改 section → change events |
| Any other sheet | ✘ | listed in ImportBatch as `ignored_sheets[]` |

## 2. Value vs inference per field

**Read directly from values:** worker aliases, weekday/period position, service codes matching the vocabulary, elder alias+unit, times, districts (parenthesised), escort columns A–M, ticks, hours, dates.

**Inferred (each inference recorded with `parse_confidence`):**

| Inference | Method | Confidence |
|---|---|---|
| Session index | slot-pair position in block; time midpoint fallback | high |
| District of a fixed service | detail-cell `(district)`; else elder's known district; else null | high/medium |
| Week pattern | `節數` incl. **Excel-date un-mangling** (date `2024-01-05` → `1,5` when column is a pattern column) | medium — always +flag |
| Exclusivity | service default (E+RO) ∨ note keywords (`只要`, `安排X`) | medium — per-case confirm |
| Worker active status | header fill gray + transfer notes | medium |
| Escort preference must/prefer | keyword map (`只要/安排`→must, `建議/盡量`→prefer) | medium |
| Elder↔alias identity across workbooks | alias+unit exact match; fuzzy (fullwidth/halfwidth, `Ｌ`↔`L`, spaces) → candidate pair | exact=high, fuzzy=**low, review required** |
| Pickup lead | 備註 regex `提早(\d+|一)小時|(\d+)分鐘` | medium |
| Case manager | trailing token of detail cell matching known manager aliases | medium |

**Never inferred (fail-safe null + flag):** gender, duty required_count semantics (counted values are labelled `source=counted_from_excel`), meanings of unknown codes, `長周`/`BL`, ED/HSS units.

## 3. Formatting that must eventually be preserved (exporter, Phase 1 targets)

1. 恆常服務 grid geometry: worker columns in original order, merged weekday/period blocks, slot-pair rows.
2. **Fill-colour semantics** (they are load-bearing): duty colours per centre, yellow ESC, orange HC, blue kitchen, pink E+RO, gray departed.
3. Cell text grammar (`E+RO:Y容(EH)` style) — staff read this fluently; do not "improve" it.
4. Escort sheet: per-day merged date cells, AM/PM rows, empty weekend rows, driver-cell note kept.
5. Fonts/row heights: best effort; not contractual in v1.
6. Elder aliases in exports exactly as the NGO writes them (no re-masking of already-masked names; re-mask only leaked full names, with a mapping note in the review pack).

## 4. Sheets the system may add

- `RC_變更摘要` (Change Summary): per-cell diff list vs previous published version — date/worker/before/after/reason/audit-id.
- `RC_審核` (Review Pack): open audit items in reviewer order (mirrors `human_review_policy.md`).
- `RC_未分配` (Unassigned): the `u[t]` list with diagnosis.
- `RC_meta` (hidden): version id, config hash, import batch ids — round-trip anchor.
Never modify the NGO's own auxiliary sheets in place.

## 5. Marking changed & review-required cells

- **Changed vs parent version:** thick orange cell border + comment `RC: 改動 — <reason> (#audit-id)`. (Border not fill — fills are already semantic.)
- **Needs review / blocking:** red corner marker (comment prefix `RC:待審`) + row in `RC_審核`.
- **Cancelled:** strikethrough text, fill preserved.
- **Unassigned slot:** text `待分配` + red border.
- All markers are additive and idempotent: re-export clears previous `RC:` comments first.

## 6. Unparsed / ambiguous cell handling

1. Cell fails grammar → canonical `UNPARSED` row keeps `raw_text` + `source_ref`; excluded from solving; one `import_ambiguity` AuditItem.
2. Ambiguous name match → both candidates listed; entity frozen (`resolution=pending`) until human picks; dependent rows solve with the *union* of constraints when safe, else held out.
3. Contradictions between workbooks (HC sheet vs division sheet worker mismatch) → prefer division sheet (it is the operative roster), flag `source_conflict`.
4. Numeric sanity: times outside 07:00–19:00, PM rows with AM-looking times (`02:30`) → normalised with flag.
5. Batch report: ImportBatch summarises counts (`parsed`, `inferred`, `flagged`, `ignored`) — the importer's honesty budget; `silently_dropped_cells` must equal 0 (benchmark B8).

## 7. Round-trip invariants

- Import→export with no solve must reproduce the input workbook cell-for-cell (modulo `RC_*` sheets and normalised whitespace) — proves we can be trusted with their file.
- Export→import (our own output) must parse with zero ambiguity items.
- Every exported change traces to an AuditItem; every AuditItem traces to events/cells (`human_review_policy.md` §6).

## 8. Versioned file conventions

Input: NGO uploads current workbooks (or Drive sync later). Output name: `分工表_<week-start>_v<n>_RC.xlsx`; the system never overwrites an NGO file in place. Google Drive automation is Phase 4 (deployment question Q-D3 in `clarification_packet.md`).
