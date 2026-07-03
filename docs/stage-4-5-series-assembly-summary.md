# Stage 4.5 — Series Assembly Summary

The deliverable: **one continuous canonical MGNREGA series at STATE-ANNUAL grain**, one
authoritative value per `(state, financial-year, metric)`, each fully lineage-traced — plus a
**parallel NATIONAL-ANNUAL spine**. Both are assembled by the same era policy, using the Stage-4
reconcile engine purely as the trust tool (no new adjudication machinery).

Numbers below are produced over the local archive by
`tests/harmonize/test_series_integration.py` (the committed, archive-gated proof) and reproduce
exactly. This is a coverage report, not new logic.

## Era policy (as built)

- **2018-19 → 2026-27** — the flagship (district-monthly MIS) rolled up to state-annual is
  authoritative (`authority_rank = 0`, basis `flagship (district-monthly, rolled up)`). The finer
  district-monthly detail is not discarded; it rides beneath, reachable via lineage.
- **2006-07 → 2017-18** — assembled from historical sources (`authority_rank = 10`). Multiple
  agreeing sources → one canonical value, `corroborated`; material disagreement → a winner is taken
  and the rejected value(s) recorded, `flagged-disagreement`; a lone source → `single-source`.
- The **seam is continuous** at state-annual grain: each fact carries its `basis` + `confidence` +
  the full `Reconciliation` lineage (sources seen with ids and as-of, any disagreement, the rule).

## STATE-annual spine

- **4,151 facts**, 8 canonical metrics, **35 states/UTs**, **FY 2010-11 → FY 2026-27**.

| metric | pre-2018 cells | 2018+ cells | corroborated | single-source | flagged |
|---|--:|--:|--:|--:|--:|
| households_employed | 254 | 304 | 15 | 337 | 206 |
| households_completed_100_days | 254 | 304 | 38 | 369 | 151 |
| persondays_generated | 189 | 304 | 104 | 337 | 52 |
| active_workers | 0 | 304 | 0 | 304 | 0 |
| wages_expenditure | 255 | 304 | 90 | 369 | 100 |
| material_skilled_expenditure | 257 | 304 | 84 | 371 | 106 |
| admin_expenditure | 255 | 304 | 113 | 369 | 77 |
| total_expenditure | 255 | 304 | 95 | 369 | 95 |

Sources wired: flagship (2018+, all metrics); MoSPI Financial Outcomes state files (expenditure,
INR lakh); MoSPI Implementation Report state files (households / 100-days as raw counts, persondays
in lakh); Rajya Sabha "households provided employment" (lakh) and "completed 100 days" (raw) tables.

## NATIONAL-annual spine (parallel — no LGD anchor, not merged into the state series)

- **146 facts**, 8 metrics. Households / 100-days / persondays span **FY 2006-07 → 2026-27**;
  expenditure spans **FY 2008-09 → 2026-27** (the national financial sources begin 2008-09).
- Pre-2018 (2006-07 → 2017-18) comes from the wide national historical sources — MoSPI
  Implementation (national) and Financial Outcomes (national); 2018+ is the flagship rolled to a
  national total (national = sum of reporting states, additive metrics). persondays corroborates
  across up to **7** national sources pre-2018.

| metric | corroborated | single-source | flagged |
|---|--:|--:|--:|
| households_employed | 4 | 11 | 6 |
| households_completed_100_days | 4 | 13 | 4 |
| persondays_generated | 7 | 10 | 2 |
| active_workers | 0 | 9 | 0 |
| wages_expenditure | 5 | 11 | 3 |
| material_skilled_expenditure | 4 | 11 | 4 |
| admin_expenditure | 4 | 11 | 4 |
| total_expenditure | 5 | 11 | 3 |

## Honest gaps (year × metric × state cells with NO source)

- **FY 2006-07 → 2009-10 has no STATE-level source.** The earliest wired historical *state* source
  is FY 2010-11, so the state spine starts there. These four years exist only in the **national**
  spine (national historical sources reach back to 2006-07). Not filled — a visible gap, never
  synthesized.
- **`active_workers` has no pre-2018 value** in either spine. The one historical candidate
  (`c8687507…`) is a single FY 2016-17 mid-year snapshot with zero flagship overlap and no
  corroborating peer; it is coverage, not a defensible series value, so it is excluded. Active
  workers is a flagship-era (2018+) metric.
- **`avg_wage_rate_per_day` is not in the state-annual spine.** It is a *rate* (INR/day/person),
  native to district-monthly grain and single-source; it does not sum to a state-annual total, so
  it is kept at its native grain (via flagship lineage), not forced into this series.
- Within 2010-2017, coverage is 32-33 states/UTs per metric-year (not the full 35) — states that a
  given historical source did not report that year are simply absent (null ≠ 0).

## Design fork flagged for review — pre-2018 peer authority

All pre-2018 historical sources are given **equal `authority_rank = 10`** (MoSPI and Rajya Sabha as
peers). No MoSPI-over-RS hierarchy was invented — an entity/harmonization ordering not written in
`RULES.md` is an Open Question, not something to guess (TIER 1 rule 1).

Consequence: when two equal-rank peers disagree beyond tolerance, the reused reconcile engine's
deterministic tiebreak (**latest `source_as_of`, then `source_id`**) takes a winner and records the
rejected peer(s) + max pairwise % as `flagged-disagreement` — the divergence is **published in
lineage, not hidden**. The `flagged` counts in the tables above are exactly the cells this tiebreak
decided (e.g. 206 state `households_employed` cells).

Verified this is genuine divergence, not a unit bug: MoSPI raw counts and RS lakh counts (× 100,000)
agree to ~0 % on clean full-year cells; the flagged cells are dominated by RS **partial-year**
columns (e.g. "upto 30.09.2015") and near-zero-denominator UTs (Lakshadweep: 0 vs 100-500
households → large %). Median pre-2018 household disagreement ≈ 10 %.

**Question for review:** is the equal-rank recency tiebreak the desired resolution for pre-2018 peer
disagreement, or should a grounded authority ordering (e.g. MoSPI/MoRD final figures over an RS
answer for the same fact) be written into `RULES.md` and applied? Proceeding with equal-rank peers
until that rule is decided.
