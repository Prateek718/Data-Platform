# Data Dictionary — MGNREGA Canonical Series (v1.0)

This document defines every file, every column, and every metric in the published dataset, plus
the conventions (units, nulls, confidence, era) needed to read it. It is written to be usable by a
reader who has never spoken to the author. If a term is not defined here, that is a bug — please
report it.

**What the dataset is.** One reconciled, lineage-traced record of the **Mahatma Gandhi National
Rural Employment Guarantee Act (MGNREGA)** scheme — India's rural employment guarantee — assembled
from many separately-published government datasets on [data.gov.in](https://data.gov.in) into a
single canonical series. It has three grains, each in its own file, plus a deep lineage file that
explains where every value came from.

---

## 1. The files

| File | Grain | Rows | Span |
|---|---|--:|---|
| `state_annual_series.csv` / `.parquet` | one value per (state, financial-year, metric) | 4,219 | FY 2010-11 → 2026-27 |
| `national_annual_series.csv` / `.parquet` | one value per (financial-year, metric) | 148 | FY 2006-07 → 2026-27 |
| `district_flagship.csv` / `.parquet` | flagship drill-down: (state, district, FY, metric) annual + monthly wage | 120,724 | FY 2018-19 → 2026-27 |
| `lineage.jsonl` | one JSON object per exported fact, keyed by `fact_id` | 125,091 | — |

The CSVs are flat and friendly; the deep provenance (every source seen, every rejected/superseded
value, coverage descriptors) lives in `lineage.jsonl`, joined to the CSVs on **`fact_id`**. The
`.parquet` files carry the identical rows with typed columns (`value` as float64,
`sources_seen_count` as int64, everything else as string). CSV and Parquet are byte-identical across
re-runs of the export.

FY 2026-27 is in progress (the flagship carries April 2026 only), so the last **complete** financial
year is 2025-26.

---

## 2. Columns

### 2.1 `state_annual_series` (the state spine)

| Column | Type | Meaning |
|---|---|---|
| `state_lgd_code` | string | The state/UT's **LGD** code — the Local Government Directory code, India's authoritative register of administrative areas. This is the canonical geographic identity. |
| `state_name` | string | The state/UT's **current** LGD English name (canonical display; a record from a period when the area was named differently still shows today's name). |
| `financial_year` | string | Indian financial year (April→March), e.g. `2019-20`. |
| `metric` | string | One of the eight canonical metrics (§3). |
| `value` | number | The reconciled value in the metric's canonical `unit`. **Empty means null** (unknown, unadjudicated, or withheld as a documented partial), never zero (§5). |
| `unit` | string | The canonical unit for the metric (§3). |
| `era_basis` | string | `flagship-rollup` (value derived from the district-monthly flagship, FY 2018-19 →) or `historical` (value from a non-flagship source — the pre-2018 sources, or a flagship-era RS peer in a year the flagship has no such state, the three Telangana cells in §8). The 2018 seam is explained in §7. |
| `confidence` | string | How much cross-source support the value has (§6). |
| `sources_seen_count` | integer | How many source **values** were seen for this fact (all of them — including editions later superseded and peers later rejected; nothing is dropped from the count). |
| `contributing_resource_ids` | string | The distinct data.gov.in **resource ids** that carried a value for this fact, `;`-separated. (Reconciliation records publisher identity; these resource ids are recovered by the export. The per-source breakdown is in `lineage.jsonl`.) |
| `fact_id` | string | Stable 16-char id for this (scheme, geography, period, metric) fact — the join key to `lineage.jsonl`. |

### 2.2 `national_annual_series` (the national spine)

Identical columns to the state spine **minus `state_lgd_code` and `state_name`**. The national tier
has **no LGD code by design**: LGD starts at the state level, so a national aggregate has no
administrative code — that absence is honest, not a missing value.

### 2.3 `district_flagship` (the flagship drill-down)

The finest grain the flagship supports, for the flagship era (FY 2018-19 →). Additive metrics are
at **district-annual** grain and sum to the state spine (§7); the average wage rate is at its native
**district-monthly** grain.

| Column | Type | Meaning |
|---|---|---|
| `state_lgd_code`, `state_name` | string | As in the state spine. |
| `district_lgd_code` | string | The district's LGD code. |
| `district_name` | string | The district's current LGD English name. |
| `financial_year` | string | Indian financial year. |
| `month` | string | Calendar month number `01`–`12` for the monthly wage rows (`01` = January, which falls late in an April→March financial year — combine with `financial_year` for the actual date); **empty for the annual rows**. |
| `metric` | string | One of the eight additive metrics (annual rows) or `avg_wage_rate_per_day` (monthly rows). |
| `value` | number | Canonical-unit value; empty = null. |
| `unit` | string | Canonical unit. |
| `grain` | string | `district-annual` or `district-monthly`. |
| `confidence` | string | Always `single-source` here (the flagship is the sole source at this grain). |
| `sources_seen_count`, `contributing_resource_ids`, `fact_id` | — | As in the state spine. |

### 2.4 `lineage.jsonl`

One object per exported fact. Keys: `fact_id`; `key` (scheme, geo_level, state_code, district_code,
fin_year, month, metric); `value`; `unit`; `basis`; `confidence`; `resolution_rule_id` (the Stage-4
rule that decided the outcome); `adjudicated`; `quarantined` / `quarantine_reason`; `sources_seen`
(every source with its `source_id` publisher, `resource_id`, value, `original_unit`, `source_as_of`,
`authority_rank`, edition markers, and `aggregate_coverage`); `disagreement` (pct, rejected_sources,
rule_id, material); and the removed-before-adjudication buckets `coverage_absent`,
`scale_quarantined`, `edition_superseded`, `partial_period`. Numbers are serialized as strings to
preserve exactness.

---

## 3. Metrics and canonical units

Every source is normalized onto the canonical unit below before any comparison. "Count" is a raw
integer count of households/workers.

| Metric | Canonical unit | Definition |
|---|---|---|
| `households_employed` | count | Households provided employment under the scheme in the year. |
| `households_completed_100_days` | count | Households that completed the 100 days of wage employment the Act guarantees. |
| `active_workers` | count | Workers classed as active. **Flagship-era only** — no defensible pre-2018 value exists (§8). |
| `persondays_generated` | person-days | Person-days of employment generated (Central-liability). Source data is **cumulative year-to-date**, corrected to the financial-year-final figure (§7). |
| `wages_expenditure` | INR lakh | Expenditure on wages. |
| `material_skilled_expenditure` | INR lakh | Expenditure on material and skilled wages. |
| `admin_expenditure` | INR lakh | Administrative expenditure. |
| `total_expenditure` | INR lakh | Total expenditure. **Derived** as wages + material/skilled + admin; where a source also states its own total, the two are compared and any gap is recorded in lineage (the derived value is the one published). |
| `avg_wage_rate_per_day` | INR | Average wage rate per day per person. A **rate**, kept at its native district-monthly grain (it does not sum to an annual total), so it appears only in `district_flagship` (§8). |

### Units conventions (lakh / crore)

Indian figures use the **lakh** (1 lakh = 100,000) and **crore** (1 crore = 100 lakh =
10,000,000). The canonical money unit is **INR lakh**; a source published in crore is converted to
lakh. Counts are canonicalized to **raw counts**: a source that published a count "in lakh" (e.g. a
Rajya Sabha table stating `36.07 lakh` households) is multiplied out to `3,607,000`. Because a
lakh-rounded count carries only the precision it was printed to, agreement between such a count and a
raw count is judged within that printed precision, not by exact equality (this is why a rounded RS
count and an exact MoSPI count can register as agreeing).

---

## 4. Geography

Canonical geographic identity is the **LGD code**; the canonical display name is the **current** LGD
name. A source's own state/district codes are internal (MIS) codes, not LGD codes, and are never
used as identity — each source is resolved to LGD by name-join (no code mapping between the flagship
and LGD exists). Rows that could not be resolved to a current LGD geography are **not** in these
files; they are quarantined with a reason and accounted for in `docs/quarantine-report.md`.

---

## 5. Null / NA semantics — null is never zero

An **empty `value` cell is null**: the figure is unknown, not reported, or deliberately left
unadjudicated. It is **never** coerced to `0`. A genuine reported zero is written as `0`. This
distinction is load-bearing: a state that a historical source simply did not cover that year is
absent (null), not a state with zero households employed. When reading the CSVs, treat empty as
missing.

---

## 6. Confidence states

`confidence` records how the value was supported or why it was withheld. Agreement is split by
**independence**: two independent *publishers* agreeing is stronger evidence than several editions of
*one* publisher agreeing.

| Value | Meaning |
|---|---|
| `cross-publisher` | ≥2 **independent publishers** reported the fact and agreed within tolerance — the strongest support. |
| `single-publisher multi-vintage` | ≥2 sources agreed, but all from **one** publisher (multiple editions/vintages) — internal consistency, not independent corroboration. |
| `edition-superseded` | One publisher re-issued the same table across dated editions; the **latest edition** restated an earlier one and was taken (see below). |
| `single-source` | Only one source carried the fact. |
| `flagged-disagreement` | A **material** disagreement between two **independent** publishers. The displayed value is the whole-geography / higher-authority reading — the flagship rollup where its district coverage is complete, or (between equal-rank historical publishers, e.g. a MoSPI edition and a Rajya Sabha answer) the one a documented deterministic tie-break selects; the rejected value and the gap are recorded in lineage. |
| `immaterial divergence` | Sources differed, but below the materiality floor. **One standard across metrics** (config-carried): a disagreement is material only if its largest spread clears BOTH an absolute floor — in the metric's own unit, **1,000** for raw counts / **100 lakh** for money (a spread is dimensional, so the absolute floor is sized to the unit, not a single cross-unit number) — AND a **1%** relative floor. A near-zero-base swing (77 vs 174 completers, a Lakshadweep 38-vs-27-lakh UT) fails the absolute floor; a rounding-level split on a large base fails the 1%. Both readings stay in lineage. |
| `single-publisher divergence` | A material disagreement among **one** publisher's vintages with no groundable edition order — **no winner is invented**; the value is left null and the divergence published (see §8, the national divergence table). |
| `unadjudicated` | A structural-coverage divergence: the authoritative source is a **structurally-incomplete** aggregate (its district universe < the state's LGD districts) that materially disagrees with a native whole-geography peer — value withheld. Realized on **10 flagship-era state cells** (`persondays_generated`, `total_expenditure`, `households_completed_100_days`) where a structural-gap flagship rollup disagrees with an RS peer (§8). |
| `partial-period-only` | The only reading for the year was an edition's **documented terminal-year mid-year partial** (R4-REC-11) — excluded rather than published as an annual, with no full-year peer to fill it — so the value is **withheld**. Realized on the **164 FY2017-18 state cells** where MoSPI's SYB2018 edition (a mid-year partial) is the sole source (§8). |

**Edition supersession.** Most pre-2018 corroboration comes from one publisher (MoSPI) that
re-issued the same statistical table across successive Statistical Year Book editions. These are one
publisher's successive drafts, not independent readings; where a later edition restated an earlier
one, the latest edition is taken and the earlier value kept in lineage as `edition_superseded`. This
is a source-grounded editorial hierarchy (same catalog, dated edition markers, verified
one-directional restatement), applied to **472** state cells — not a blind "newest file wins".

---

## 7. Era basis and the 2018 seam

The series joins two eras at a continuous state-annual grain:

- **FY 2018-19 → 2026-27** (`era_basis = flagship-rollup`): the flagship *District-wise MGNREGA Data
  at a Glance* (district + monthly) is authoritative, rolled up to state-annual. The finer
  district-monthly detail is the `district_flagship` drill-down.
- **FY 2006-07 / 2010-11 → 2017-18** (`era_basis = historical`): assembled from the historical
  datasets (MoSPI Statistical Year Book tables, Rajya Sabha parliamentary answers), reconciled and
  labelled by the confidence states above.

**Person-days are cumulative-YTD, corrected to the FY-final.** The flagship publishes person-days
(and expenditure) as a running year-to-date total, so the annual value is the **final** month's
figure, never the sum of the monthly rows. Summing the monthly cumulatives over-counts massively —
on Goa in FY 2022-23, a naive monthly sum gives 593,095 person-days against the correct FY-final of
94,004, a 6.31× inflation. The pipeline takes the FY-final and never sums. This is also **why the
flagship's raw monthly cumulative snapshots are not exported as flat facts**: they exist inside the
pipeline but publishing them as if each month were a monthly flow would invite exactly that
over-count, so `district_flagship` carries the additive metrics at **district-annual** (FY-final)
grain instead. The one genuinely monthly flagship quantity, `avg_wage_rate_per_day`, is a rate (not
cumulative) and is exported at its native district-monthly grain.

---

## 8. Honest coverage — what the series does and does not contain

- **FY 2006-07 → 2009-10 exists only in the national spine.** No state-level source reaches before
  FY 2010-11, so the state spine starts at 2010-11; those four earlier years are present only
  nationally (the national historical sources reach back to 2006-07). The gap is visible, never
  filled by synthesis.
- **`active_workers` is 2018-19 onward only**, in both spines. The one pre-2018 candidate is a single
  mid-year snapshot with no corroborating peer and no flagship overlap; it is excluded as coverage,
  not a defensible series value.
- **`avg_wage_rate_per_day` is district-monthly only.** It is a rate, native to district-monthly
  grain and single-source; it does not sum to a state or national annual, so it is kept only in
  `district_flagship`, never forced into the spines.
- **Pre-2018 genuine cross-publisher material disagreements: nine, in two metrics.** After edition
  supersession and materiality filtering, the residual pre-2018 disagreements are:
  - **Four in `households_employed`** (a MoSPI edition vs a Rajya Sabha answer): **Bihar FY 2015-16**
    (~4.2%), **Mizoram FY 2013-14** (~3.1%), **Telangana FY 2014-15** (~1.3%), **Andaman & Nicobar
    Islands FY 2014-15** (~7.7%). MoSPI and RS carry equal authority, so a documented deterministic
    tie-break (the more recent vintage) selects the displayed value.
  - **Five in `total_expenditure`** — surfaced once the RS expenditure table (`57bff16a`) made RS an
    independent publisher on expenditure: **Andhra Pradesh FY 2014-15** (~1.9%) & **FY 2015-16**
    (~1.8%), **Bihar FY 2014-15** (~2.0%), **Jammu & Kashmir FY 2016-17** (~1.4%), **Telangana FY
    2016-17** (~22%).

  Each records the rejected value and the percentage in lineage — surfaced, not hidden. (Wiring RS
  expenditure also produced **117 new `total_expenditure` and 20 `households_completed_100_days`
  cross-publisher corroborations** pre-2018 — RS independently confirming MoSPI.)
- **Flagship-era (FY 2018-19 →) reconciliation against the RS state peers.** Four Rajya Sabha state
  tables are reconciled against the flagship rollup: person-days (`cea6ee41` 2019-24, `e289a8fe`
  2021-24), total-expenditure (`57bff16a`, to 2018-19) and households-completed-100-days
  (`a1c9803c`, to 2018-19). Outcomes by metric (corroborated / flagged / unadjudicated):

  | metric | cross-publisher | flagged | unadjudicated |
  |---|--:|--:|--:|
  | `persondays_generated` | 146 | 12 | 7 |
  | `total_expenditure` | 12 | 10 | 2 |
  | `households_completed_100_days` | 22 | 3 | 1 |

  - **Corroboration** (e.g. Goa FY2022-23 persondays, flagship 94,004 vs RS 94,000) — agreement
    within the RS tables' lakh precision.
  - **Flagged** — the flagship has whole-geography coverage but the RS peer materially disagrees; the
    flagship value is taken and the rejected RS value + percentage recorded.
  - **Unadjudicated (10 cells)** — a **structural-gap** flagship rollup materially disagrees with the
    RS peer, so no value is asserted (`value` null, rule `R4-REC-05`); flagship + both RS readings in
    lineage: `persondays` — West Bengal 2019-20/2020-21/2021-22, Maharashtra 2021-22/2022-23/2023-24,
    Telangana 2021-22; `total_expenditure` — Madhya Pradesh & Rajasthan 2018-19; `households_completed_100_days`
    — West Bengal 2018-19.

  Three cells are **RS-only** (a year the flagship "at a glance" does not cover — Telangana enters the
  flagship in 2020-21), carried single-source from the RS table with `era_basis = historical`:
  Telangana **FY2019-20 persondays** (107,114,000), **FY2018-19 total_expenditure**, and **FY2018-19
  households_completed_100_days**. These are the three state-spine rows beyond the 4,216
  flagship-anchored cells (**4,219** total).
- **FY2017-18 is thin: MoSPI's SYB2018 edition publishes it as a mid-year partial, so it is withheld
  where no full-year peer exists.** SYB2018's terminal year (2017-18) is a documented mid-year partial
  (R4-REC-11); it is excluded rather than published as an annual. Where an RS full-year peer covers it
  the RS value stands (`total_expenditure`, `households_completed_100_days`); otherwise the cell is
  **withheld** — **164 state cells** are `partial-period-only` (value null): `persondays_generated`
  33, `households_employed`/`wages`/`material`/`admin` 32 each, `households_completed_100_days` 3. The
  MoSPI partial is kept in each cell's lineage. **These nulls are expected to be temporary**: the
  deferred RS vintages `7efb084d`/`ec1ee20d` carry FY2017-18 as a NON-terminal (full) year and are
  queued for v1.1 to fill them.
- **The national spine carries 22 unadjudicated `single-publisher divergence` cells** (FY 2012-13 →
  2015-16, across 7 metrics), where one publisher's (MoSPI) national vintages disagree materially and
  no groundable edition order exists. Their `value` is null and every reading is in lineage
  (`confidence = single-publisher divergence`, rule `R4-REC-09`). Extending the state
  edition-supersession mechanism to the national tier is a documented, deferred follow-up.

  | FY | unadjudicated metrics |
  |---|---|
  | 2012-13 | households_employed, households_completed_100_days, persondays_generated, wages_expenditure, material_skilled_expenditure, admin_expenditure, total_expenditure (7) |
  | 2013-14 | households_completed_100_days, persondays_generated, wages_expenditure, material_skilled_expenditure, admin_expenditure, total_expenditure (6) |
  | 2014-15 | households_employed, households_completed_100_days, persondays_generated, wages_expenditure, material_skilled_expenditure, admin_expenditure, total_expenditure (7) |
  | 2015-16 | material_skilled_expenditure, admin_expenditure (2) |

  (The three `persondays_generated` rows — 2012-13, 2013-14, 2014-15 — are the persondays subset.)
- **Within FY 2010-11 → 2017-18, coverage is 32-33 states/UTs per metric-year, not the full 35.** A
  state a given historical source did not report that year is simply absent (null ≠ 0).
- **The `district_flagship` drill-down is flagship-era (FY 2018-19 →) only** — there is no
  district-level pre-2018 source. Its additive district-annual values sum to the state spine by
  construction; where a state's flagship district set is smaller than its current LGD district count,
  that structural incompleteness is recorded in each fact's `aggregate_coverage` in lineage.
- **Known unharmonized archive overlaps (deferred, not lost).** A few RS state peers remain unwired,
  each held back for a byte-verified **machinery-reach or defect** reason (no source is deferred for
  scope alone): RS persondays vintages whose **terminal year is itself a mid-year partial**
  (`7efb084d`, `ec1ee20d`) and a compound total-expenditure table likewise (`aeca8112`) — these carry
  FY2017-18 as a non-terminal full year and are the v1.1 path to fill the FY2017-18 nulls, but need
  per-vintage partial handling not yet built; an RS total-expenditure table whose **scale does not
  reconcile** to the flagship (`8e7b41be`); and tables **never eligible** as a canonical peer —
  `eeb479a7` (persons, not households, provided employment), `0fecf99b` (ST-subcategory persondays),
  `fc212c38` (crore/partial); and RS tables measuring a **non-canonical subject or an unverified
  metric identity** — `d1d29e37` (asset-works expenditure by category, not scheme total), `bd9922fb`
  (employment demanded/offered/provided — the "provided" column's identity vs `households_employed`
  needs byte-verification before it can peer a headline metric), `5dcb2b3e` (wage-rate text +
  average-days, neither a canonical additive metric), `c0350589` (one value per FY, metric ambiguous
  from the bytes). All remain in the archive and in `docs/`; none is deferred for scope alone.

For the full account of rows set aside during geography resolution (and why), see
`docs/quarantine-report.md`. For the reconciliation mechanics summarized above, see
`docs/stage-4-5-series-assembly-summary.md`.
