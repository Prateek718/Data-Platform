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
  agreeing sources → one canonical value, labelled by INDEPENDENCE: `cross-publisher` when ≥2
  distinct publishers agree, `single-publisher` when only multiple vintages of ONE publisher agree
  (weaker evidence); material disagreement → a winner is taken and the rejected value(s) recorded,
  `flagged-disagreement`; a lone source → `single-source`.
- The **seam is continuous** at state-annual grain: each fact carries its `basis` + `confidence` +
  the full `Reconciliation` lineage (sources seen with ids and as-of, any disagreement, the rule).

## STATE-annual spine

- **4,151 facts**, 8 canonical metrics, **35 states/UTs**, **FY 2010-11 → FY 2026-27**.

Counts are totals across both eras (cross-/single-publisher and flagged fall entirely in the
pre-2018 multi-source years; 2018+ is single-source flagship). `cross-publisher` = ≥2 independent
publishers agreed; `single-publisher` = ≥2 vintages of ONE publisher agreed.

| metric | pre-2018 cells | 2018+ cells | cross-publisher | single-publisher | single-source | flagged |
|---|--:|--:|--:|--:|--:|--:|
| households_employed | 254 | 304 | 53 | 14 | 337 | 154 |
| households_completed_100_days | 254 | 304 | 0 | 38 | 369 | 151 |
| persondays_generated | 189 | 304 | 0 | 105 | 337 | 51 |
| active_workers | 0 | 304 | 0 | 0 | 304 | 0 |
| wages_expenditure | 255 | 304 | 0 | 90 | 369 | 100 |
| material_skilled_expenditure | 257 | 304 | 0 | 84 | 371 | 106 |
| admin_expenditure | 255 | 304 | 0 | 113 | 369 | 77 |
| total_expenditure | 255 | 304 | 0 | 95 | 369 | 95 |

`households_employed` is the ONLY pre-2018 state metric with two independent publishers (MoSPI +
Rajya Sabha), so it is the only one with `cross-publisher` cells; every other pre-2018 metric is
MoSPI-only, hence `single-publisher` (cross-vintage) at best — never overstated as independent.

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

The national historical sources are all MoSPI, so national agreement is `single-publisher`
(cross-vintage) — never `cross-publisher` (0 across every metric).

| metric | cross-publisher | single-publisher | single-source | flagged |
|---|--:|--:|--:|--:|
| households_employed | 0 | 4 | 11 | 6 |
| households_completed_100_days | 0 | 4 | 13 | 4 |
| persondays_generated | 0 | 7 | 10 | 2 |
| active_workers | 0 | 0 | 9 | 0 |
| wages_expenditure | 0 | 5 | 11 | 3 |
| material_skilled_expenditure | 0 | 4 | 11 | 4 |
| admin_expenditure | 0 | 4 | 11 | 4 |
| total_expenditure | 0 | 5 | 11 | 3 |

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

## How divergence is kept truthful (three corrections applied)

The `flagged` counts above are only the cells where sources genuinely disagree — three non-conflict
artifacts are handled BEFORE comparison so the flag means "real disagreement", not noise:

- **Partial-year columns are excluded from full-year comparison.** A compound header like
  `..._2015_16_upto_30_09_2015` reports only PART of the financial year (a different period). Reshape
  now detects the period-narrowing suffix (`upto` / `till` / `as-on` + date) and surfaces it as
  `_period_qualifier`; the historical extractors do NOT promote such a value into the full-year
  `(state, FY, metric)` cell (the value still lives in the normalized layer — not dropped). The two
  known cases (`34a83496` FY2015-16, `6c12385f` FY2016-17, `households_employed`) previously injected
  a ~half-year value into every state, flagging ~all 32 states each at 10-66 %. `households_employed`
  flagged fell **206 → 154**; median pre-2018 household disagreement **≈10 % → ≈2 %**.
- **Precision-aware count agreement (R4-REC-01a).** Count metrics require exact equality, so an RS
  lakh-rounded count (e.g. 36.07 lakh → 3,607,000) was flagged against a MoSPI raw count
  (3,606,783) despite agreeing to the RS rounding. Each count-in-lakh value now carries a
  `rounding_epsilon` DERIVED FROM ITS OWN DECLARED PRECISION — half the last-decimal step (2-dp lakh
  → ±500; 1-dp lakh → ±5,000) — not a blanket tolerance, so genuine small-state gaps (RS 129,000 vs
  MoSPI 94,674, a real 26 %) stay flagged. This surfaces real MoSPI+RS agreement previously hidden by
  exact match: `households_employed` `cross-publisher` cells rose **15 → 53**.
- **Cross-publisher vs cross-vintage corroboration.** Agreement is now labelled by INDEPENDENCE.
  Three vintages of ONE publisher (e.g. the MoSPI Financial-Outcomes files for `total_expenditure`)
  agreeing is `single-publisher` (95 pre-2018 total_expenditure cells), NOT the stronger
  `cross-publisher` — which requires ≥2 distinct publishers. Only `households_employed` earns
  `cross-publisher` in the state spine; the national spine (all MoSPI) earns it nowhere.

Residual pre-2018 `households_employed` flags (154): median ≈2 %, and the divergence is genuine
cross-source / cross-vintage reporting differences (e.g. two RS answers of 35.95 vs 36.07 lakh) plus
near-zero-denominator UTs — no partial-year or lakh-rounding artifact remains.

## Design fork flagged for review — pre-2018 peer authority

All pre-2018 historical sources are given **equal `authority_rank = 10`** (MoSPI and Rajya Sabha as
peers). No MoSPI-over-RS hierarchy was invented — an entity/harmonization ordering not written in
`RULES.md` is an Open Question, not something to guess (TIER 1 rule 1).

Consequence: when two equal-rank peers disagree beyond tolerance, the reused reconcile engine's
deterministic tiebreak (**latest `source_as_of`, then `source_id`**) takes a winner and records the
rejected peer(s) + max pairwise % as `flagged-disagreement` — the divergence is **published in
lineage, not hidden**. The `flagged` counts in the tables above are exactly the cells this tiebreak
decided (e.g. 154 state `households_employed` cells, after the three corrections above).

Verified this is genuine divergence, not a unit bug: MoSPI raw counts and RS lakh counts (× 100,000)
agree within the RS rounding band on clean full-year cells (now treated as agreement, not a flag);
the residual flagged cells are genuine cross-source / cross-vintage reporting differences and
near-zero-denominator UTs (Lakshadweep: 0 vs 100-500 households → large %). Median pre-2018 household
disagreement ≈ 2 %.

**Question for review:** is the equal-rank recency tiebreak the desired resolution for pre-2018 peer
disagreement, or should a grounded authority ordering (e.g. MoSPI/MoRD final figures over an RS
answer for the same fact) be written into `RULES.md` and applied? Proceeding with equal-rank peers
until that rule is decided.
