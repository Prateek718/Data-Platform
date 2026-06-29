# Data Platform — DATA_CONTRACT.md — Canonical Schema & Source Contract

> **Data Platform** — A governed data layer that reconciles MGNREGA facts published across
> multiple datasets and departments within data.gov.in into one contracted, lineage-tracked
> dataset, served over MCP for AI agents to query.
> (Built for MGNREGA as the reference implementation; architected scheme-agnostic.)
>
> The architectural spine. Every downstream spec (ingestion, resolution, harmonization,
> validation, store, MCP) consumes this. This is the document that pins the decisions
> Claude Code must NOT make on its own.
>
> Status: DRAFT. Items marked **[DECISION NEEDED]** require Prateek's call before lock.
> Items marked **[ASSUMED]** are decisions I (the architect's drafting assistant) made on
> defensible grounds; override any you disagree with.

---

## 1. Scope of the canonical model

The platform fuses MGNREGA data published across multiple datasets and departments within
data.gov.in into ONE governed "golden" dataset. The canonical grain is:

**One row = one (scheme, state, district, financial-year, month, metric-set).**

- `scheme` — always MGNREGA here, but modeled as a field so the platform is scheme-agnostic
  (the "architected for any central scheme" claim). [ASSUMED: monthly grain]
- Geographic grain: **district** (rolls up to state). [ASSUMED — see §6 open Q]
- Temporal grain: **financial-year + month** (Indian FY: Apr–Mar). [ASSUMED]

**[LOCKED — TEMPORAL GRAIN]**: monthly. (Richer as-of/temporal story per definition-of-done.)

---

## 2. Canonical entities

### 2.1 Scheme entity
| field | type | notes |
|---|---|---|
| scheme_canonical_id | str | always `MGNREGA` |
| scheme_aliases | list[str] | `NREGA`, `MNREGA`, `MGNREGS`, full Act name — resolved in Stage 3 |

### 2.2 Geography entity (the hard one)
| field | type | notes |
|---|---|---|
| state_canonical_id | str | LGD state code — canonical identity |
| state_canonical_name | str | current LGD name — canonical display |
| district_canonical_id | str | LGD district code — canonical identity |
| district_canonical_name | str | current LGD name — canonical display |
| valid_from / valid_to | date | districts split/merge over time — see Stage 3 |

**[LOCKED — GEOGRAPHY ANCHOR (Option A: source-local → LGD translation)]** Canonical
geographic *identity* is the **LGD (Local Government Directory)** code; the canonical *display*
name is the **current LGD name**. A source's own state/district codes are NOT LGD codes and are
never used as canonical identity — verification confirmed the flagship publishes
source-internal (MIS) codes, not LGD (e.g. flagship Goa `state_code=10` vs LGD Goa `30`;
flagship districts `1001`/`1002` are sequential internal codes, not LGD district codes). Each
source therefore carries a **maintained per-source translation table** mapping its local
state/district codes → the LGD code; the applied mapping is recorded in the `geo_resolution`
lineage field (§4). Source NAMES are **input aliases only** — used (alongside the codes) to
resolve to the LGD code, then dropped from the golden record but preserved in lineage; a source
name is never canonical. (The translation-table *contents* are populated from live data in
Stage 3 — this contract specifies only that the mechanism exists and where it is recorded.)

**[v1 BOUNDARY — CURRENT-LGD NAMES]** Canonical names are the *current* LGD names: the golden
record shows the present-day LGD name even for a record from a period when the geography was
named differently. Resolving a historical *display name* as-of the record's period stays OUT OF
SCOPE for v1. Period-correct *geography* itself is handled by **R3-SET-02 [LOCKED — option (a):
keep-both-with-validity]** (file each record under the LGD geography that existed at its period,
with `valid_from`/`valid_to`, never merged or forward-mapped across a split); only historical
name *display* remains deferred.

### 2.3 Metric set (the canonical facts)
Drawn from fields OBSERVED in real sources (GitHub analysis + data.gov.in dataset titles).
[ASSUMED] canonical metric list — trim/extend as you like:

| canonical metric | unit | observed source field(s) |
|---|---|---|
| persondays_generated | person-days | "Persondays", "Employment provided" |
| households_employed | count | "Households engaged in Work" |
| households_completed_100_days | count | "HH completed 100 days" |
| active_workers | count | "Active workers" |
| avg_wage_rate_per_day | INR | "average wage rate per day per person" |
| wages_expenditure | INR lakhs | "Wages" |
| material_skilled_expenditure | INR lakhs | "Material and skilled Wages" |
| admin_expenditure | INR lakhs | "Total Adm Expenditure" |
| total_expenditure | INR lakhs | derived or direct — see Stage 4 |

**[LOCKED — METRIC SCOPE & BUILD ORDER]**: All 9 metrics are in the canonical schema and
are in the final deliverable. BUILD ORDER: implement and verify the first end-to-end slice
with 3 metrics — one per harmonization shape — then add the remaining 6 (mechanical repetition
of proven patterns, not new architecture):
- Starter 3: `persondays_generated` (count), `avg_wage_rate_per_day` (rate), `total_expenditure` (money).
- Remaining 6 added after the slice works: households_employed, households_completed_100_days,
  active_workers, wages_expenditure, material_skilled_expenditure, admin_expenditure.

---

## 3. Sources (the contract with reality)

The pipeline ingests from **data.gov.in only**. The divergence the platform reconciles is
**internal to data.gov.in**: the same MGNREGA facts are published across multiple datasets and
multiple departments, with conflicting units (lakh vs crore), grains (district vs state), and
year-slices. Reconciling that cross-department conflict is the core job — not fusing distinct
portals.

| id | dataset / department (within data.gov.in) | grain | role |
|---|---|---|---|
| SRC_FLAGSHIP | "District-wise MGNREGA Data at a Glance" — DRD (resource id `ee03643a-ee4c-48c2-ac30-9f2ff26ab722`) | district + monthly | **primary anchor** |
| SRC_RS | Rajya Sabha parliamentary-answer tables | state, year-slice (typ.) | cross-check / divergence source |
| SRC_MOSPI | MoSPI-published MGNREGA tables | state/district, varies | cross-check / divergence source |

**[LOCKED — SOURCE SCOPE]** Ingest from data.gov.in only. The flagship anchor is
**"District-wise MGNREGA Data at a Glance"** (resource id `ee03643a-ee4c-48c2-ac30-9f2ff26ab722`),
district + monthly grain. Other data.gov.in datasets and departments (e.g. Rajya Sabha
parliamentary-answer tables, MoSPI) publish the same facts at conflicting units (lakh vs crore),
grains (district vs state), and year-slices — that cross-department conflict is the divergence
the pipeline reconciles.

**Source priority for conflict resolution** [LOCKED]: the district-monthly flagship
(SRC_FLAGSHIP) is authoritative for *published statistical* facts; SRC_RS and SRC_MOSPI are
cross-checks. On disagreement, reconcile units/grains and flag in lineage (pct, rejected source,
rule id) rather than silently discarding the divergent value. Used by Stage 4 on disagreement.

---

## 4. Lineage record (what the definition-of-done requires)

Every canonical fact row MUST carry:
| field | notes |
|---|---|
| source_id | which source supplied the winning value |
| sources_seen | all sources that had this fact + their values |
| disagreement | null, or {pct, rejected_source, rule_id} |
| resolution_rule_id | the Stage 4 rule that picked the winner |
| geo_resolution | how the district/state was canonicalized (alias rule id, or "exact") |
| quarantined | bool + reason if excluded |
| source_as_of | each source's own sync/update date |
| ingested_at | when our pipeline pulled it |
| schema_version | which source schema version this came through |
| normalization_rules | Stage 2 single-source cleanup applied to this value (R2-FMT-01 / R2-DATE-01 / R2-TYPE-01, incl. delivered→coerced type — the type the value arrived as, NOT the source's discarded declared type) |
| dedupe | always present: {duplicates_collapsed, collapsed_row_indexes, tie_break_rule_id} — zeros/empty when nothing collapsed (absence of dedupe is itself signal for the trust report) |

This is the structure `get_lineage` returns. It is the definition-of-done made concrete.

---

## 5. What this contract deliberately does NOT cover (scope boundaries)

- No probabilistic/ML entity matching — deterministic only (production extension).
- No automated cross-system lineage inference — application-level recorded only.
- No sub-district (block/panchayat/village) grain in v1 — district is the floor.
- No write/mutation surface for consumers.
- Third-party republishers (e.g. DeshSeva, dataful) and the operational NREGA MIS are evaluated and excluded from v1 — out of scope.

---

## 6. Decisions — status

**LOCKED:**
1. Temporal grain: **monthly**.
2. Geography anchor: **LGD code = canonical identity; current LGD name = canonical display.**
   Source-local codes are source-internal (MIS) codes, NOT LGD — they are mapped to LGD via a
   maintained per-source translation table, recorded in the `geo_resolution` lineage field;
   source names are input aliases only (preserved in lineage, never canonical). Canonical names
   are current-LGD; historical-name-*display*-as-of-period is out of scope for v1 (see the §2.2
   boundary); geography temporal validity itself is now **R3-SET-02 LOCKED-(a)** (see item 7).
   Full locked detail in §2.2.
3. Metrics: **all 9 in schema & final deliverable; build 3 first** (persondays_generated,
   avg_wage_rate_per_day, total_expenditure), then the other 6.
4. Sources: **data.gov.in only.** Divergence is internal cross-department (flagship
   "District-wise MGNREGA Data at a Glance" vs Rajya Sabha parliamentary-answer tables vs MoSPI),
   reconciled across conflicting units/grains/year-slices. Third-party republishers (SYNC:
   DeshSeva/dataful) and the operational NREGA MIS are evaluated and excluded from v1.
5. District grain floor: **district** (no block/village in v1).
6. Stage 2 snapshot dedupe tie-break: **`R2-DEDUP-TB-01` (`latest_source_as_of`)** — keep
   latest `source_as_of`, ties → last occurrence in file. Config-carried (flippable without
   rewriting dedupe logic); active id recorded in lineage `dedupe.tie_break_rule_id`.
   Rationale: person-days is cumulative YTD, so a later snapshot is a more-complete version
   of the same fact, not a contradiction.
7. District split/merge temporal validity (**R3-SET-02**): **LOCKED — option (a),
   keep-both-with-validity.** File each record under the LGD geography that existed at its
   period, with `valid_from`/`valid_to`; never merge or forward-map values across a split
   (forward-mapping would fabricate an allocation the source never provided — same principle as
   row-atomic dedupe). Split recorded as a lineage note. Future-only (not v1): a successor
   pointer for navigability, never value redistribution.

**STILL OPEN (Stage 3/4 — needed when those stages are built, ~30–40%):**
- R4-DEF-01: total_expenditure — derive-and-compare (rec) vs take source field directly.
- R4-REC-01: disagreement tolerance — 0.5% expenditure / exact counts (rec), config-carried.
- R4-REC-03: staleness threshold (days of lag that flags a value stale).

**STILL OPEN (later, ~50%+):**
- Store: confirm Postgres. Analyst framework: confirm LangGraph.
