# Stage 8 — Claim Inventory (evidence-first, pre-prose)

> The report's candidate skeleton. Every figure here was produced by an **executed round-trip**
> against the served surface (the Stage 7 tools over the sealed `dist/v1.0`) — never from memory,
> never from the pipeline docs. A claim that the served data cannot back is recorded as **FAIL**
> and stays out of the report unless the decision at the Stage 8 checkpoint says otherwise.
>
> Status: **RESOLVED AT THE CHECKPOINT.** The decision: the report includes C1, C2, C3′, C4′ and
> C5–C9 — everything that verified. C3 and C4 (the "6.31×" and "₹18,623/day" monthly figures) stay
> recorded here as **verification-FAILED**, and appear nowhere in the report.
>
> Two framing constraints were imposed and are enforced in the section briefs (`analyst/sections.py`):
> **C2** must present its two phenomena separately — never "34 disagreements" as one homogeneous
> count — naming the rule family behind each and stating that both cleared the two-part materiality
> floor. **C4′** must present the nine surviving >₹1,000/day rates as source data-quality artifacts
> carried faithfully into the record with lineage, explicitly NOT as observed wages, and say that a
> plausible MGNREGA daily wage is an order of magnitude lower.
>
> The shipped report is `report/report.md` (+ `report.json` and `report/charts/`). It carries
> **eleven** sections: the seven findings above, plus an abstract, an introduction, a methodology
> and a limitations section added by a later amendment so the document reads cover to cover for a
> stranger. The two FAILED claims (C3, C4) get their honest home in **Limitations** — as prose
> explaining why no monthly data exists and why figures derived from the source's cumulative
> monthly columns cannot be reproduced or checked here, carrying no lineage-backed monthly figures
> and repeating none of the numbers that circulate elsewhere.
>
> All eleven sections passed verification on the first drafting attempt.

## Classification key

| class | meaning |
|---|---|
| **finding** | a genuine claim about the MGNREGA record itself |
| **semantics** | a claim about what the data *means* / how it must be read (not a claim about the scheme) |
| **example** | a worked illustration, true at the stated scope, not generalized |

Verification: **PASS** = the query and lineage round-trips in the row were executed and returned
these exact figures. **FAIL** = the served surface cannot produce the figure.

---

## The surface being interrogated

`list_datasets` (executed):

| table | rows | coverage | grain |
|---|---|---|---|
| `national_annual_series` | 148 | 2006-07 → 2026-27 | national-annual |
| `state_annual_series` | 4,219 | 2010-11 → 2026-27 | state-annual |
| `district_flagship` | 57,181 | 2018-19 → 2026-27 | district-annual |
| `lineage` | 61,548 | 2006-07 → 2026-27 | per-fact provenance |

**The record is annual-only at every grain.** `get_schema` on all three tables returns no month
column, and `query(month=…)` refuses (`monthly_wage_unavailable`). This single fact decides the
fate of two candidate sections below (C3, C4).

---

## C1 — The continuous 2006→2026 national series · **finding** · PASS

**Claim:** MGNREGA's national record runs unbroken across 20 financial years, from FY 2006-07 to
its repeal-truncated final year FY 2026-27, and the series is stitched from two different eras of
sourcing.

Query: `query("national_annual_series")` → 148 rows.

| figure | value | FY | lineage (source · resource_id · as-of) |
|---|---|---|---|
| person-days, first year | 905,054,000 | 2006-07 | SRC_MOSPI · `04476f1d-c61c-4584-9e0a-b1cb62410f5f` · 2018-11-30 (+3 more MOSPI vintages) |
| person-days, peak | 3,881,318,918 | 2020-21 | SRC_FLAGSHIP · `ee03643a-ee4c-48c2-ac30-9f2ff26ab722` · 2026-06-29 |
| person-days, last complete FY | 2,209,959,751 | 2025-26 | SRC_FLAGSHIP · same · 2026-06-29 |
| person-days, terminal partial | 12,914,539 | 2026-27 | SRC_FLAGSHIP · same · 2026-06-29 |
| total expenditure, peak | 10,999,799 INR lakh | 2020-21 | SRC_FLAGSHIP · same · 2026-06-29 |
| households employed, peak | 75,500,579 | 2020-21 | SRC_FLAGSHIP · same · 2026-06-29 |

Era split (from the served `era_basis` column): **76 historical / 72 flagship-rollup** of the 148
national facts. Pre-2018 facts carry `R4-REC-01` / `R4-REC-04` over MOSPI and Rajya Sabha sources;
FY 2018-19 onward carry the flagship MIS (`single-source`, `R4-REC-04`).

- The 2020-21 peak (COVID year) is the largest value in every headline metric — verified as the
  series maximum, not asserted from outside knowledge.
- **Derived figures available** (deterministic, over listed input facts): peak ÷ first-year
  person-days = 4.29×; sum of person-days over the 18 non-null years = 41,694,690,493.

**Rejected derivation (named, so nobody computes it by accident):** summing `households_employed`
across years gives 928,438,460 — this is **not** "928 million households", it double-counts a
household in every year it worked. Arithmetically computable, semantically void. Excluded.

---

## C2 — Cross-publisher material disagreements · **finding** · PASS (with a correction)

**Claim (kickoff):** "the nine genuine cross-publisher material disagreements (pre-2018)".
**Verified:** exactly nine — and there are **25 more in the flagship era** that the kickoff did not
mention. The record carries **34** flagged disagreements in total, all cross-publisher, all
material, every one adjudicated by `R4-REC-02` with the rejected value retained in lineage.

Query: `query("state_annual_series")` → filter `confidence == "flagged-disagreement"` → 34 rows;
`get_lineage` on all 34.

**The nine pre-2018 (MOSPI vs Rajya Sabha, `era_basis = historical`):**

| state | FY | metric | canonical value | spread |
|---|---|---|---|---|
| Telangana | 2016-17 | total_expenditure | 210,898.07 | 22.09% |
| Andaman & Nicobar Is. | 2014-15 | households_employed | 13,000 | 7.69% |
| Bihar | 2015-16 | households_employed | 1,487,000 | 4.17% |
| Mizoram | 2013-14 | households_employed | 178,000 | 3.06% |
| Bihar | 2014-15 | total_expenditure | 105,649.39 | 2.01% |
| Andhra Pradesh | 2014-15 | total_expenditure | 289,514.19 | 1.93% |
| Andhra Pradesh | 2015-16 | total_expenditure | 473,782.96 | 1.83% |
| Jammu & Kashmir | 2016-17 | total_expenditure | 83,350.50 | 1.43% |
| Telangana | 2014-15 | households_employed | 2,433,000 | 1.27% |

**The 25 flagship-era (flagship MIS vs Rajya Sabha, `era_basis = flagship-rollup`):** concentrated
in `total_expenditure` (11 states, FY 2018-19) and `persondays_generated` (Chhattisgarh, Odisha and
Himachal Pradesh, each in FY 2021-22 / 2022-23 / 2023-24). Largest: Lakshadweep FY 2023-24
person-days, 14.53% (flagship 3,510 vs RS 3,000/4,000).

Every row carries, from `get_lineage`: the winning source + resource_id + as-of, the rejected
source + resource_id + value, the % spread, `material: true`, and `resolution_rule_id: R4-REC-02`.

*Presentation note (not a data question): these are two different stories. Pre-2018 is "two
secondary publishers of the same statistic disagree"; flagship-era is "the primary MIS disagrees
with what was tabled in Parliament". Whether the report tells one or both is a checkpoint call.*

---

## C3 — The cumulative-YTD worked example (Goa FY2022-23, "6.31×") · **example** · **FAIL**

**Claim as scoped in the kickoff:** a naive sum of the twelve monthly values inflates Goa's
FY2022-23 person-days by 6.31×, because the monthly column is cumulative year-to-date.

**VERIFICATION FAILED — recorded, not dropped.** The claim cannot be backed by any query against
the served data, so it cannot appear in the report as a verified, lineage-carrying figure.

*Reason:* the record is **annual-only at every grain** (`get_schema` — no month column on any
table; `query(month=…)` refuses). Monthly rows were deliberately excluded at v1.0 **because** the
published monthly columns are cumulative year-to-date, not monthly — the very defect the 6.31×
illustrates. The figure is a property of the *source* flagship data in `data/archive/`, which the
pipeline corrected; the correction's input was never published in `dist/v1.0`. A figure derived
from data the record does not serve is exactly what the verifier is built to block.

*Open at the checkpoint (not mine to decide):* whether the cumulative-YTD story appears in the
report as a **methodology narrative** — explaining *why* the record is annual-only, carrying no
lineage-backed monthly figures — rather than as a claim with numbers.

What IS served for the same geography and year, and passes:

**C3′ — the additive spine reconciles exactly (Goa FY2022-23) · finding/semantics · PASS**

Queries: `query("district_flagship", states=["Goa"], fy_from="2022-23", fy_to="2022-23")` and
`query("state_annual_series", states=["Goa"], fy_from="2022-23", fy_to="2022-23")`.

All **eight additive metrics** sum from the two districts to the state value with **zero
residual** — e.g. person-days: North Goa 42,253 (`daf9afc0d6e9f3b7`) + South Goa 51,751
(`fee085bea82444c5`) = **94,004** = the state fact (`ad36ce29ea24bc59`). Same exact match for
households_employed, households_completed_100_days, active_workers, wages / material-skilled /
admin / total expenditure.

The ninth metric, `avg_wage_rate_per_day`, **does not sum** — it is a rate, served only at
district-annual grain, and the state series refuses it (`unknown_metric`, pointing to
`district_flagship`). Summing the two districts' rates yields 714.71, a number with no meaning.
That refusal *is* the cumulative-YTD story, told with figures the record can actually back:
the state person-days fact is `cross-publisher`-corroborated (flagship 94,004 vs Rajya Sabha
94,000, `R4-REC-01`), while the wage rate is a ratio that neither sums nor exists monthly.

---

## C4 — The wage-rate artifact story · **semantics** · PARTIAL (PASS / FAIL split)

**FAIL — not servable:** the "₹18,623/day" April artifact. It is a *monthly* figure; the record
serves no monthly data and refuses the request. It is documented in `docs/RULES.md` (R4-DEF-03)
from the archive, not from `dist/v1.0`. It **cannot appear as a verified claim** — recorded here
as failed, not dropped. The server's monthly-wage **refusal object is itself a verifiable
artifact** and remains available as section material (below).

**PASS — servable, and it makes the same point:**

1. **The refusal object itself** (executed, verbatim): `query("district_flagship", month="2022-04")`
   → `{"refused": true, "code": "monthly_wage_unavailable", "reason": "The series is annual-grain
   only; monthly figures are not served. In particular, monthly avg_wage_rate_per_day values are
   cumulative year-to-date ratios, not valid monthly rates — the wage rate is published only as the
   financial-year-final annual value at district-annual grain. Remove 'month' to query the annual
   series."}` The server explains the artifact in the act of refusing to serve it.
2. **The wage surface that IS served:** 5,645 district-annual wage facts, FY 2018-19 → 2025-26.
   **Zero for FY 2026-27** — the repeal-truncated year never completed, so no annual rate exists
   (a permanently partial FY, honestly absent rather than a stale April ratio).
3. **Residual implausibility survives even at FY-final:** 9 of 5,645 facts (0.16%) exceed
   ₹1,000/day — max **₹3,582/day**, West Bengal / Hooghly, FY 2023-24 (`d8fff0db43079540`); seven
   of the nine are Manipur districts in FY 2022-23. A daily wage rate of ₹3,582 is not a daily
   wage; the arrears/payment-timing contamination the rule describes is visible in the *served*
   record, not only in the archive.
4. **Four zero-valued wage facts** (Nicobars FY2018-19/19-20/20-21; Palwal FY2022-23). The served
   surface states the value is 0.0; *why* is not determinable from the served surface alone.
   Recorded as an observation, not a claim.

---

## C5 — Coverage honesty: the nulls · **finding** · PASS (with a correction)

**Claim (kickoff):** "the 174 NULL cells split by reason".
**Verified:** 174 is the **state** table only. The record carries **193 null cells** in total.

| where | count | reason (from `get_lineage.null_reason`) |
|---|---|---|
| state_annual_series | 164 | `partial-period-only` — an edition's terminal-year mid-year partial; withheld rather than published as an annual |
| state_annual_series | 10 | `unadjudicated` — a structurally-incomplete aggregate materially disagrees with a whole-geography peer; value withheld |
| national_annual_series | 19 | `single-publisher divergence` — one publisher's vintages disagree with no groundable edition order |
| district_flagship | 0 | — |

**The shape of the hole is the story.** 163 of the 164 `partial-period-only` nulls fall in a single
year, **FY 2017-18** — the year before the flagship era begins. Of that year's 224 state cells,
**163 are null**; only `total_expenditure` (32 states) and `households_completed_100_days` (29)
survive. The record's weakest year is the seam between its two sourcing eras, and it says so.

The 10 `unadjudicated` nulls are named facts: West Bengal person-days (FY2019-20, 20-21, 21-22) and
households_completed_100_days (FY2018-19); Maharashtra person-days (FY2021-22, 22-23, 23-24);
Telangana person-days (FY2021-22); Madhya Pradesh and Rajasthan total_expenditure (FY2018-19).
The 19 national nulls are all MOSPI-vintage divergences in FY 2012-13 → 2015-16.

**null ≠ 0** is enforced and served: `get_schema` returns the null semantics, and every null cell
carries its reason through `get_lineage`.

---

## C6 — "What this record refuses to answer" · **finding** (governance) · PASS

Every refusal below was executed; each returns a structured object, never an empty result or an
exception. The refusal surface is the product, not an error path.

| ask | code | what the record says |
|---|---|---|
| data after the repeal (`fy_from="2027-28"`) | `record_sealed` | series ends FY 2026-27; MGNREGA repealed 30 June 2026 |
| a monthly figure | `monthly_wage_unavailable` | annual-grain only; monthly wage values are cumulative-YTD ratios, not rates |
| wage rate at state grain | `unknown_metric` | it is a rate — lives only in `district_flagship` |
| district data before FY 2018-19 | `district_series_floor` | the drill-down starts at the flagship era |
| state data before FY 2010-11 | `state_series_floor` | use the national series (FY 2006-07 →) |
| an unknown geography (`"Atlantis"`) | `unknown_geography` | give an LGD code or current LGD name |
| a malformed FY (`"2019"`) | `invalid_period` | expects `YYYY-YY`; a malformed label would otherwise compare lexicographically and silently mis-answer (R7-SRV-01) |
| the whole district table at once | `row_cap_exceeded` | 57,181 rows > 10,000 cap; narrow the filters |
| `query("lineage")` | `table_not_queryable` | lineage is per-fact provenance — use `get_lineage` |
| `request_refresh()` | `record_sealed` | closed, DOI-versioned historical record; no new data will ever be published |

---

## C7 — The district set grew from 666 to 738 · **finding** · PASS

Query: `query("district_flagship", metrics=[…])` per metric, distinct `district_lgd_code` per FY.

| FY | 2018-19 | 2019-20 | 2020-21 | 2021-22 | 2022-23 | 2023-24 | 2024-25 | 2025-26 | 2026-27 |
|---|---|---|---|---|---|---|---|---|---|
| districts | 666 | 669 | 710 | 714 | 732 | 738 | 738 | 738 | 737 |

738 distinct districts across 34 states/UTs. Districts split over the period; each fact stays filed
under the LGD geography that existed at its own period and is never forward-mapped across a split
(that would require inventing an allocation the source never published — R3-SET-02).

---

## C8 — The terminal year is a repeal stub · **finding** · PASS

FY 2026-27 carries the flagship's April 2026 only: national person-days **12,914,539** against
2,209,959,751 in FY 2025-26 (0.58%), and **no** `avg_wage_rate_per_day` fact at any district (an
incomplete FY has no annual rate). The last **complete** financial year of MGNREGA is **2025-26**.

---

## C9 — `active_workers` exists only in the flagship era · **semantics** · PASS

At state grain, `active_workers` is served for FY 2018-19 → 2026-27 only (33–34 states per year);
it has no pre-2018 values at all. A reader comparing "workers" across the full 20 years would be
comparing a metric to its own absence.

---

## Summary — what survives verification

| # | candidate | class | verdict |
|---|---|---|---|
| C1 | continuous 2006→2026 national series, scale, era-based sourcing | finding | **PASS** |
| C2 | 34 cross-publisher material disagreements (9 pre-2018 + 25 flagship-era) | finding | **PASS** (kickoff undercounted) |
| C3 | Goa FY2022-23 cumulative-YTD "6.31×" | example | **FAIL — not servable** |
| C3′ | Goa FY2022-23 additive spine reconciles to zero residual; the rate does not sum | finding/semantics | **PASS** |
| C4 | wage-rate artifact: "₹18,623/day" | semantics | **FAIL — not servable** |
| C4′ | wage-rate artifact via the refusal object + 9 surviving >₹1,000/day FY-final rates | semantics | **PASS** |
| C5 | coverage honesty: 193 nulls by reason; the FY2017-18 hole | finding | **PASS** (174 → 193) |
| C6 | the refusal surface as a governance feature (10 refusals) | finding | **PASS** |
| C7 | district set 666 → 738, never forward-mapped | finding | **PASS** |
| C8 | FY 2026-27 is a repeal stub; last complete FY is 2025-26 | finding | **PASS** |
| C9 | `active_workers` is flagship-era only | semantics | **PASS** |

**Two kickoff sections do not survive** (C3, C4) for the same root cause: both are stories about
*monthly* data, and the sealed record is annual-only by construction. Both have served substitutes
(C3′, C4′) that make the same point with figures the verifier can actually check. Whether to run
the substitutes, or to admit an explicitly-labelled class of "documented in the pipeline, not
verifiable from the served surface" figures, is a **checkpoint decision** — it is not mine to make.
