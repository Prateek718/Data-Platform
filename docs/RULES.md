# Data Platform — RULES.md — Stage 2 (Normalization), Stage 3 (Entity Resolution) & Stage 4 (Metric Harmonization)

> **Data Platform** — A governed data layer that fuses multiple public sources into one
> contracted, lineage-tracked dataset, served over MCP for AI agents to query.
>
> Stage 2 is mechanical single-source cleanup; Stages 3 and 4 are the two hard stages.
> These rules are the project's credibility. Written as explicit,
> named, deterministic rules so Claude Code IMPLEMENTS them rather than inventing logic.
> Each rule has an id (used in lineage), a trigger, an action, and a quarantine fallback.
>
> Status: DRAFT. [ASSUMED] = defensible default I chose; [DECISION NEEDED] = your call.

---

## STAGE 2 — NORMALIZATION (single-source cleanup)

> **Boundary** — Stage 2 = single-source cleanup; Stage 4 = cross-source reconciliation.
> Placement test: *can this be done on one row from one source, or does it need to compare
> sources?* One row / one source → here. Needs comparison across sources or scheme semantics
> → Stage 4.

Goal: make each source's rows individually clean and correctly typed, BEFORE any
cross-source comparison. Everything here operates on a single row from a single source:
strip formatting, normalize single-row dates, coerce declared-vs-delivered type mismatches,
and collapse a source's own duplicate snapshots to one canonical row. NO source-vs-source
logic happens in Stage 2.

### Numeric & format cleaning
- **R2-FMT-01**: numeric cleaning — strip commas, handle blanks/`NA`/`-` as null (not zero).
  [IMPORTANT: null ≠ 0. A missing person-days value is NOT zero employment.]

### Date normalization
- **R2-DATE-01**: normalize all dates to ISO; map FY strings ("2023-24") to canonical FY.
  Single-row formatting only — no cross-source period reconciliation. Un-parseable FY/month
  cell → set that cell to null and record `R2-DATE-01:parse_failed` on that column in
  `normalization_rules` (keep the row) — same cell-null-and-flag principle as the R2-TYPE-01
  amendment (row-quarantine is reserved for whole-row failures).

### Type coercion (deferred from Stage 1)
- **R2-TYPE-01**: when a source's declared schema type does not match what it delivers
  (OBSERVED in Stage 1: source declares `long`, delivers decimal-strings), coerce to the real
  type after R2-FMT-01 cleaning. Record the coercion as **delivered-type → target** (e.g.
  `R2-TYPE-01:str→decimal`) in `normalization_rules`, so the mismatch is auditable, not silent
  — NOT source-declared-type → target: Stage 1 deliberately discarded the source's unreliable
  declared types (it declares `long` for decimal-strings), so the honest audit record is the
  type the value actually arrived as. Un-coercible cell → set that cell to null and
  record `R2-TYPE-01:coercion_failed` on that column in `normalization_rules` (keep the row).
  Row-quarantine is reserved for whole-row failures — consistent with the landing layer's
  refusal to drop a row over one bad cell.

### Snapshot dedupe (deferred from Stage 1)
- **R2-DEDUP-01**: a single source can ship duplicate rows for the same source-level key
  (its own state/district + FY + month) — duplicate district-month snapshots. Pick ONE
  canonical row deterministically and drop the rest; record `duplicates_collapsed` (count)
  and the active `tie_break_rule_id` in lineage. Single-source dedupe only — cross-source
  agreement remains Stage 4 (R4-REC-*).
  - **[LOCKED] tie-break `R2-DEDUP-TB-01` (`latest_source_as_of`)**: keep the row with the
    latest `source_as_of`; if `source_as_of` ties, keep the last occurrence in file order.
    Config-carried (a named setting, not a hardcoded magic value) so the strategy can be
    flipped without rewriting dedupe logic; the active strategy's id is what lands in
    lineage `dedupe.tie_break_rule_id`. Rationale: person-days is cumulative year-to-date, so
    a later snapshot is a more-complete version of the SAME fact, not a contradiction —
    "latest wins" matches what the data means.

---

## STAGE 3 — ENTITY RESOLUTION

Goal: decide when records from different sources refer to the SAME real thing
(same scheme, same state, same district), despite different spellings, codes, and district sets.

### Scheme identity
- **R3-SCHEME-01 [LOCKED]**: normalize scheme name (uppercase, strip spaces/punctuation) →
  if in {NREGA, MGNREGA, MNREGA, MGNREGS, MAHATMAGANDHI...} → canonical `MGNREGA`.
  No-match → quarantine with reason `unknown_scheme`. Lockable now with no live data: the
  variant set is a known, closed list of MGNREGA aliases and the match is on the normalized
  (uppercased, space/punctuation-stripped) form. Confirmed as written.

### State / district name normalization
- **R3-GEO-01 (normalize)**: lowercase, trim, collapse whitespace, strip punctuation,
  expand known abbreviations via alias table (e.g. "DN HAVELI AND DD" →
  "dadra and nagar haveli and daman and diu"). [OBSERVED real case]
- **R3-GEO-02 (exact match on normalized name)**: if normalized name matches exactly one
  canonical geography → resolve. Record `geo_resolution = exact`.
- **R3-GEO-03 (alias table)**: maintained lookup of known variant→canonical mappings for
  cases R3-GEO-02 misses. Record `geo_resolution = alias:<id>`.
- **R3-GEO-04 (code authority = LGD; translate, don't match) [LOCKED]**: LGD is the canonical
  code authority. A source's own state/district code is a source-internal (MIS) code, NOT an LGD
  code (DATA_CONTRACT §2.2) — so it is **translated to the LGD code via the maintained per-source
  translation table**, never matched directly against canonical codes. When a source carries a
  code, code-translation is the preferred identity path over name resolution (R3-GEO-02/03); the
  applied mapping is recorded in `geo_resolution`. A source code with no entry in its translation
  table → quarantine via R3-GEO-05 (`unresolved_geography`). (Translation-table contents are
  populated from live data in Stage 3; this rule fixes only the authority and the mechanism.)
- **R3-GEO-05 (no-match → quarantine)**: if a district can't be confidently resolved,
  DO NOT guess. Quarantine row, reason `unresolved_geography`, surface in trust report.

### District-set reconciliation (the observed hard case)
Sources disagree on WHICH districts exist (755 vs 740+ vs other).
- **R3-SET-01**: a district present in one source but absent in another is NOT an error by
  itself — record it as `present_in: [sources]`. Only quarantine a *fact* if it can't be
  geo-resolved at all (R3-GEO-05).
- **R3-SET-02 (temporal validity) [LOCKED — option (a): keep-both-with-validity]**: districts
  split/merge over time. Each record is filed under the LGD geography that existed **at the
  record's period**, carrying `valid_from`/`valid_to` validity dates; records are **never merged
  or forward-mapped across a split**, and the split is recorded as a lineage note.
  Rationale: forward-mapping (the rejected option (b)) would require splitting an old aggregate
  value across the new boundaries using an allocation ratio the source does not provide — that is
  fabrication, the same principle as row-atomic snapshot dedupe (R2-DEDUP-01): never invent
  values, preserve citation integrity. Option (a) preserves each fact exactly as the source
  published it, with the split traceable via the validity dates plus the lineage note.
  Future enhancement (NOT v1): a successor POINTER in lineage ("old-X became new-Y, new-Z") for
  navigability — a pointer ONLY, never redistributing values across successors.

---

## STAGE 4 — METRIC HARMONIZATION

> **Boundary** — Stage 4 = cross-source reconciliation; Stage 2 = single-source cleanup.
> Placement test: *can this be done on one row from one source, or does it need to compare
> sources?* Needs comparison across sources or scheme semantics → here. One row / one source
> → Stage 2 (formatting, dates, typing, snapshot dedupe).

Goal: produce ONE trustworthy canonical value per metric per row, with the rule recorded.

### Unit normalization (cross-source)
- **R4-UNIT-01**: expenditure fields → normalize all to INR lakhs (sources vary: rupees,
  lakhs, crores). Record original unit in lineage. Stays in Stage 4: choosing one canonical
  unit so values from different sources are comparable is cross-source by nature.

### Definition harmonization (the subtle part)
- **R4-DEF-01 (total_expenditure)**: [DECISION NEEDED] — is canonical total_expenditure
  taken DIRECTLY from a source field, or DERIVED as wages + material_skilled + admin?
  Risk: if derived, it may not equal a source's own "total" (rounding, what's included).
  I recommend: derive it, AND compare to any source-provided total; if they differ beyond
  tolerance, record the discrepancy in lineage. That discrepancy IS a finding worth showing.
- **R4-DEF-02 (persondays)**: confirm all sources mean the same by "persondays" (one day of
  work by one person). [ASSUMED yes — it's a legally standardized MGNREGA term.]

### Cross-source value reconciliation (when sources disagree on the same number)
- **R4-REC-01 (agreement check)**: for a given canonical (geo, period, metric), compare
  values across sources. If within tolerance → agree, take primary (SRC_OGD).
  [DECISION NEEDED — TOLERANCE]: what % counts as "agreement"? I recommend 0.5% for
  expenditure, exact for counts — but this is a real call and should be config-carried,
  not hardcoded (mirrors your Project 2 "threshold not statistical test" decision).
- **R4-REC-02 (disagreement → resolve + record)**: beyond tolerance → take source-priority
  winner (SRC_OGD > SRC_SYNC > SRC_MIS for published statistical facts), record
  {winning_value, rejected_value(s), pct_diff, rule_id} in lineage. This populates the trust
  report's "sources disagreed" line. NOTE: when MIS (operational) disagrees with OGD
  (published), flag it rather than silently discarding — MIS may be more current/granular.
- **R4-REC-03 (staleness)**: if a source's `source_as_of` lags the primary by more than
  [DECISION NEEDED: N days?], flag the value as stale in lineage even if it agrees.
  (DeshSeva explicitly warns its syncs lag — this rule operationalizes that.)
- **R4-REC-04 (single-source value)**: if only one source has the fact, take it but mark
  `sources_seen = 1` so the trust report can flag "unverified by a second source."

### Quarantine (the validation-gate handoff)
- **R4-Q-01**: any row failing unit normalization (R4-UNIT-01) — or already quarantined
  upstream by Stage 2 cleanup (R2-FMT-01 / R2-TYPE-01) — or carrying an impossible value
  (negative expenditure, persondays > active_workers × days_in_period), is quarantined with
  a typed reason and excluded from the golden store — but remains queryable as quarantined.

---

## OPEN QUESTIONS for Prateek (Stage 2/3/4 — batched)

1. ~~**R3-SET-02 district split/merge**: keep-both-with-validity (my rec) or successor-mapping?~~
   — **RESOLVED & LOCKED (a)**: keep-both-with-validity — file each record under the
   period-correct LGD geography with `valid_from`/`valid_to`, never merge or forward-map across a
   split (forward-mapping would fabricate an allocation the source never provided); the split is
   a lineage note. Future-only: a successor pointer for navigability (pointer, never value
   redistribution). See R3-SET-02.
2. ~~**R3-GEO-04 / code authority**: LGD codes as the match key?~~ — **RESOLVED & LOCKED**:
   LGD is the code authority; source-local (MIS) codes are *translated* to LGD via a per-source
   table, not matched directly (see R3-GEO-04 and DATA_CONTRACT §2.2).
3. **R4-DEF-01 total_expenditure**: derive-and-compare (my rec) or take source field directly?
4. **R4-REC-01 tolerance**: 0.5% expenditure / exact counts (my rec), config-carried?
5. **R4-REC-03 staleness threshold**: how many days' lag flags a value stale?
6. **R2-DEDUP-01 snapshot dedupe (Stage 2)**: tie-break when duplicate snapshots differ —
   latest `source_as_of`, else last-in-file? (config-carried)
