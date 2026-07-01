# Stage 0 · T0.3 — Divergence Findings (cross-department, within data.gov.in)

> **NOTE — this is a bounded, point-in-time divergence *check*, not a scope statement.** It
> compares one (state, year, metric) head-to-head, pulled **live** on 2026-06-23. Project scope
> has since expanded: the **full MGNREGA archive** (88 API/JSON + 42 file-only CSVs + LGD) is now
> captured **offline under `data/archive/`**, and ongoing builds do **not** hit the live API. The
> "two RS resources" here are the two person-days tables used for this head-to-head — **not** the
> extent of RS coverage or of project scope. The live-pull numbers below are retained as the
> evidentiary record of the check.
>
> Status: **COMPLETE.** This is the last premise check before ingestion. It proves the same
> MGNREGA fact, published by different departments inside data.gov.in, genuinely conflicts.
> Authoritative refs: `docs/DATA_CONTRACT.md` (esp. revised §3), `docs/notes/sources.md`.
> All numbers below are real, pulled live via the keyed API on 2026-06-23. Bounded pulls only
> (one state, one FY); no full-dataset fetches.

---

## VERDICT (two parts, up front)

- **Sources diverge on VALUES: NO** (for the head-to-head metric) — once units and grain are
  aligned, the flagship and the Rajya Sabha tables agree to **0.0043%** (94,004 vs 94,000
  person-days). This is the honest result and it is a *good* one: it means the platform's
  reconciliation will produce a trustworthy golden value, not paper over a data error.
  **Caveat:** values DO diverge between the two Rajya Sabha tables themselves (same state, same
  year, two resources) — see §4. So "values agree" holds for flagship-vs-RS, not universally.
- **Sources diverge STRUCTURALLY: YES** — decisively, on **units, grain, persondays semantics,
  and year-slice packaging**. This structural conflict alone fully justifies building the
  pipeline: a consumer cannot compare these sources without the exact reconciliation logic the
  platform provides. Details in §3.

---

## 1. The two sources compared

| | SRC_FLAGSHIP | SRC_RS (two resources) |
|---|---|---|
| title | District-wise MGNREGA Data at a Glance | "State/UT-wise Details of Employment Provided (in person-days generated) … MGNREGA …" |
| resource id | `ee03643a-ee4c-48c2-ac30-9f2ff26ab722` | `cea6ee41-2b18-4266-b42b-0af54c13b18c` (FY 2019-20→2023-24) and `e289a8fe-3fd4-4964-9579-5bddb88e36b8` (FY 2021-22→2023-24) |
| department / org | Ministry of Rural Development / Dept. of Land Resources | **Rajya Sabha** (parliamentary answers) |
| grain | **district + monthly** | **state/UT + annual (year-slice)** |
| persondays field | `Persondays_of_Central_Liability_so_far` (cumulative-YTD, raw person-days) | `_2022_23` (table 1) / `person_days_generated__in_lakh____2022_23` (table 2) |
| declared unit | **raw person-days** (no scaling) | table 2: **"in Lakh"** (explicit); table 1: **unlabelled** (inferred lakh — see §3.1) |
| as-of | `updated_date` 2026-06-22T17:00:22Z (refreshed continuously) | table 1: 2025-03-07; table 2: 2024-11-02 (frozen at answer-tabling) |
| rows pulled | 24 (GOA, FY 2022-2023: 2 districts × 12 months) | 35 each (one row per state/UT + a "Total" row) |

Chosen overlap key: **(state = Goa, financial-year = 2022-23, metric = persondays_generated)** —
present in flagship and in both RS tables. Goa chosen because it has only 2 districts
(NORTH GOA, SOUTH GOA), keeping the flagship→state roll-up small and fully auditable.

Reproduce (key redacted):
```
# flagship slice
GET api.data.gov.in/resource/ee03643a-…?format=json&limit=50&filters[state_name]=GOA&filters[fin_year]=2022-2023
# RS table 1 / table 2
GET api.data.gov.in/resource/cea6ee41-…?format=json&limit=40
GET api.data.gov.in/resource/e289a8fe-…?format=json&limit=40
```

---

## 2. THE VALUE COMPARISON (one state, one year, one metric)

### 2.1 Aggregating the flagship UP to state+annual (the non-trivial part)

`Persondays_of_Central_Liability_so_far` is **cumulative within the FY** (per sources.md
OQ-OGD-1), confirmed again here: NORTH GOA rises monotonically Apr→Mar
(2,523 → 6,389 → … → 39,224 → **42,253**). Therefore:

- **FY total per district = the March (final) cumulative value**, NOT a sum of monthly rows.
- **State annual = sum of district March finals.**

| district | March (final cumulative) person-days | naive sum of all 12 monthly cumulatives (WRONG) |
|---|---|---|
| NORTH GOA | 42,253 | 242,071 |
| SOUTH GOA | 51,751 | 351,024 |
| **Goa state, FY 2022-23** | **94,004** | 593,095 |

> ⚠ The naive sum-of-monthlies gives **593,095** — **6.31× inflated**. This is the exact trap
> the harmonization stage (Stage 4) must encode: cumulative-YTD metrics roll up by taking the
> period-final value, not by summing. Recording it here so the rule is grounded in a real number.

### 2.2 Flagship-derived vs Rajya Sabha — head to head

| source | raw value | declared unit | value in raw person-days |
|---|---|---|---|
| SRC_FLAGSHIP (district→state→annual roll-up) | 94,004 | person-days | **94,004** |
| SRC_RS table 1 (`cea6ee41…`, `_2022_23`) | 0.94 | (unlabelled → lakh) | 94,000 |
| SRC_RS table 2 (`e289a8fe…`, `…in_lakh…2022_23`) | 0.94 | **lakh** person-days | 94,000 |

- **Absolute difference:** 4 person-days.
- **% difference:** **0.0043%** — i.e. the RS figure (0.94 lakh, rounded to 2 decimals)
  back-resolves to 94,000; the flagship roll-up is 94,004. 94,004 rounds to 0.94004 ≈ 0.94 lakh.
  The entire gap is RS's 2-decimal rounding of a lakh figure.

**→ The values agree once unit (×100,000) and grain (district-monthly-cumulative → state-annual)
are reconciled.** They are NOT comparable as published.

### 2.3 Expenditure (flagship side only — recorded, not head-to-head)

Flagship `Total_Exp` is also cumulative-YTD; Goa FY 2022-23 state annual (sum of district March
finals) = **422.18 lakh = 4.2218 crore**. No RS *expenditure* table for Goa 2022-23 was pulled
within bounded effort, so this is recorded for provenance, not as a value comparison. Note this
metric carries the **lakh-vs-crore** unit hazard called out in DATA_CONTRACT §3 and OQ-OGD-2.

---

## 3. STRUCTURAL DIVERGENCE (this is the YES)

### 3.1 Unit mismatch — and a *latent* unit ambiguity
- Flagship publishes **raw person-days** (94,004). RS publishes **lakh person-days** (0.94).
  A factor-of-100,000 mismatch; comparing the published numbers directly is off by 5 orders of
  magnitude.
- Worse: RS **table 1** (`cea6ee41…`) labels its columns only `2019-20`, `2020-21`, … with **no
  unit at all**. The unit is only knowable by cross-referencing table 2 (`e289a8fe…`, which says
  "in Lakh") and confirming the values match (Andhra Pradesh 2022-23: 2396.03 vs 2395.43; Goa:
  0.94 vs 0.94). An unlabelled-unit column that can only be decoded by a second dataset is
  exactly the cross-department hazard the platform exists to neutralise.

### 3.2 Grain mismatch
- Flagship: **district + monthly** (24 rows just for Goa/2022-23).
- RS: **state/UT + annual year-slice** (1 row per state per year).
- No shared key without rolling the flagship up across two axes (district→state, monthly→annual).

### 3.3 Persondays semantics mismatch
- Flagship persondays is **cumulative-within-FY** (`…_so_far`); the annual figure is the March
  value. RS persondays is a **single annual figure** already.
- A consumer who doesn't know this will either sum monthly cumulatives (→ 6.31× too high, §2.1)
  or compare a mid-year cumulative against an RS annual. Both are silently wrong.

### 3.4 Year-slice / packaging fragmentation
- The *same* fact (Goa person-days by year) is split across **two RS resources** with
  **overlapping** windows (2019-20→2023-24 and 2021-22→2023-24), tabled on different dates
  (2025-03 vs 2024-11). The canonical store must dedupe/reconcile these overlapping slices.

### 3.5 State-name spelling / coverage
- State labels differ in form: flagship uses upper-case (`GOA`, `NORTH GOA`); RS uses title-case
  (`Goa`). Across the full RS list, names like `Jammu and Kashmir`, `Dadra and Nagar Haveli and
  Daman and Diu`, `Andaman and Nicobar Islands` will need alias resolution against the flagship's
  `state_name`/`state_code` (LGD) — the Stage 3 geography job.
- RS tables include a synthetic **`Total`** row (35 rows = 34 states/UTs + Total). That Total row
  is **not** a state and must be quarantined on ingest, or it double-counts.

---

## 4. SECONDARY FINDING — values DO diverge *between* the two RS tables

Same metric, same state, same year, two data.gov.in resources — different numbers:

| state / year | table 1 `cea6ee41…` | table 2 `e289a8fe…` | diff |
|---|---|---|---|
| Goa 2023-24 | 0.42 | 0.43 | 0.01 lakh (~2.4%) |
| Goa 2021-22 | 0.95 | 0.95 | 0 |
| Goa 2022-23 | 0.94 | 0.94 | 0 |
| Andhra Pradesh 2021-22 | 2417.19 | 2414.87 | 2.32 lakh |
| Andhra Pradesh 2022-23 | 2396.03 | 2395.43 | 0.60 lakh |
| Andhra Pradesh 2023-24 | 2554.96 | 2554.97 | 0.01 lakh |

These are small (revision-level) differences from two parliamentary answers tabled months apart,
but they are **real value disagreements between two same-department sources** for an identical
(state, year, metric) key. This is precisely the disagreement Stage 4's resolution rule
(`disagreement = {pct, rejected_source, rule_id}`, DATA_CONTRACT §4) must record rather than
silently pick one — and it confirms divergence is not merely a units artefact.

---

## 5. CONCLUSION — does this justify the pipeline?

**Yes, unambiguously, on structure.** Even though the flagship and RS person-days agree to four
decimal places of a lakh once reconciled (a reassuring data-quality signal), they are
**incomparable as published**: different units (one unlabelled), different grain, different
persondays semantics, fragmented across overlapping year-slices, with non-canonical state names
and a Total pseudo-row. A consumer cannot answer "how many person-days did Goa generate in
2022-23?" from these sources without exactly the deterministic reconciliation the platform
builds. The premise holds.

Per the Stage 0 review-gate rule (`tasks/stage0-todo.md`): NO-on-values + YES-on-structure →
**proceed**, with confidence that the chosen anchor (flagship) is corroborated by the RS
cross-check.

### What this hands to later stages
- **Stage 2 (normalize):** raw field `Persondays_of_Central_Liability_so_far` is raw person-days;
  RS columns are lakh person-days — unit normalisation is mandatory and grounded here.
- **Stage 3 (geo resolution):** `GOA`→`Goa`, plus the multi-word UT names and the `Total` row.
- **Stage 4 (harmonize):** (a) cumulative-YTD → take period-final, never sum (6.31× error shown);
  (b) reconcile the two RS tables' overlapping year-slices and record their small disagreements;
  (c) lakh/crore handling for expenditure (OQ-OGD-2 still open).

### Honest limits of this check
- One (state, year, metric) head-to-head (Goa / 2022-23 / persondays). Bounded by design; a
  broader sweep is Stage 1's job, not this premise check.
- No RS *expenditure* table pulled for the same state-year, so the lakh-vs-crore value
  comparison is asserted structurally (from declared units), not demonstrated head-to-head.
- RS "as-of" is the resource's data.gov.in `updated_date`, a proxy for the parliamentary answer
  tabling date.
</content>
</invoke>
