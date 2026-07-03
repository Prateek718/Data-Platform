# Stage 4.5 — Corroboration Source Inventory (analysis-only)

> **Read-only inventory. No extractors written, nothing wired, no pipeline changed.** For each of
> the six metrics Stage 4 currently harmonizes single-source (flagship only), this classifies every
> keyword-candidate dataset in the local archive by reading its actual columns/values, to establish
> the *real* corroboration scope — evidence, not keyword counts. Base: `stage4-harmonization`.

## How each candidate was classified
- **GENUINE** — reports THIS metric at a grain + unit that can reconcile against the flagship
  (state-annual on `(state, fin_year)`, or district on `(state, district, fin_year)`; convertible
  unit; per-year values). The wire-them set.
- **DIFFERENT-METRIC** — shares a keyword but reports something else (a rate not a count/amount,
  "demanded" not "worked", funds released not spent, a percentage, a complaint count). Skip.
- **UNRECONCILABLE** — reports the metric but at a grain/coverage that can't align without inventing
  an allocation (a subset of states, a single local body). Quarantine-with-reason if ever wired.
- **NATIONAL (separate axis)** — the All-India Implementation/Financial Outcomes series. It
  corroborates the *national* tier, not the state series, so it is listed apart.

Canonical alignment: flagship `households_employed` = `Total_Households_Worked`; `wages/material/
admin` = the flagship expenditure components; all are cumulative-YTD, INR lakh (money) or counts.

Note on units: several RS/MoSPI tables publish counts "in lakh" (×100,000 to raw) — convertible, so
not a blocker. "in lakhs" for money is already the flagship's canonical unit.

---

## 1. households_employed  (flagship: `Total_Households_Worked`, count, state-annual)

Canonical concept = households that **worked / were provided employment** (NOT "demanded").

| resource_id | dept | class | grain | unit | FY span | metric column | wire? | reason |
|---|---|---|---|---|---|---|---|---|
| 34a83496 | RS | GENUINE | state | count | 2012–16 | `household_provided_employment___YYYY` | y | provided-employment count, per-year, keys on (state, fy) |
| 6c12385f | RS | GENUINE | state | count | 2013–16 | `no_of_hh_provided_employment___YYYY` | y | as above |
| c5c8858c | RS | GENUINE | state | count | 2014–16 | `number_of_households_provided_employment___YYYY` | y | as above |
| e5491ee9 | RS | GENUINE | state | count | 2014–15 | `No. of Household provided employment - YYYY` | y | as above |
| cb137c04 | RS | GENUINE | state | count | 2013–15 | `No. of HH provided employment - YYYY` | y | also carries persondays (bonus cross-check) |
| 2611cc74 | RS | GENUINE | state | count | 2014–16 | `households_provided_employment___YYYY` | y | has provided cols (its "demanded" cols are a sibling metric) |
| 22f8cdb0 | RS | GENUINE | state | lakh→count | 2014–15 | `no__of_hhs_provided_employment__in_lakh____YYYY` | y | provided count in lakh (×1e5) |
| 2d0a4136 | MoSPI | GENUINE | state | count | 2010–15 | `No.of households provided employment - YYYY` | y | Implementation Report; provided col per-year |
| 3ebbea46 | MoSPI | GENUINE | state | count | 2010–13 | `No.of households provided employment-YYYY` | y | as above |
| 9aefcd0f | MoSPI | GENUINE | state | count | 2010–14 | `No.of households provided employment - YYYY` | y | as above |
| c11b65d4 | MoSPI | GENUINE | state | count | 2010–17 | `No.of households provided employment - YYYY` | y | as above (widest state span) |
| 79d89e44 | RS | GENUINE | district | count | 2019–20 | `Households Provided Employment` | y | district grain → keys on (state, district, fy) |
| fcebf9f9 | RS | GENUINE | district | count | 2015–17 | `households_provided_employment_in_nos_YYYY` | y | district grain, per-year |
| 2485c8e1 | MoRD | GENUINE* | district | count | 2011–12 | `Total_households_worked` | y* | district/block; only 31 rows — likely a partial pull, confirm coverage before trusting |
| 428fa054 | MoRD | GENUINE* | district | count | 2014–15 | `Total_households_worked` | y* | as above (31 rows) |
| 49214697 | MoRD | GENUINE* | district | count | 2015–16 | `Total_households_worked` | y* | as above (31 rows) |
| a000738b | MoRD | GENUINE* | district | count | 2012–13 | `Total_households_worked` | y* | as above (31 rows) |
| c6575501 | MoRD | GENUINE* | district | count | 2013–14 | `Total_households_worked` | y* | as above (31 rows) |
| b0f2d01a | RS | DIFFERENT | state | count | 2014–15 | `no__of_household_demanded_employment___YYYY` | n | DEMANDED, not worked/provided |
| cadde395 | RS | DIFFERENT | district | — | 2015–19 | (title: "Employment Demanded by Households") | n | demanded, not worked |
| 51a18f1b | RS | DIFFERENT | state | — | 2013–15 | (title: "average days of employment provided") | n | average-days rate, not a household count |
| 73d68992 | RS | DIFFERENT | state | count | 2014–15 | `no__of_households_completed_100_days…` | n | this is the 100-days metric, not households_employed |
| a1c9803c | RS | DIFFERENT | state | count | 2016–18 | bare-year cols ("Completing 100 days") | n | 100-days metric |
| 26837e5a | RS | UNRECONCILABLE | state | count | 2015 | (title: ">100 days, drought-affected 10 States) | n | only 10 drought states — a subset, not the full series |
| 04476f1d | MoSPI | NATIONAL | national | count | 2006–14 | `no_of_households_provided_employment` | axis | All-India — corroborates national tier |
| 1878204d | MoSPI | NATIONAL | national | count | 2006–15 | `No.of households provided employment` | axis | All-India |
| 54d1a5fa | MoSPI | NATIONAL | national | count | 2013 | `No.of households provided employment` | axis | All-India |
| d88e2cb6 | MoSPI | NATIONAL | national | count | 2006–17 | `No. of Households Provided Employment` | axis | All-India (deepest history) |

**Counts:** GENUINE **18** (11 state + 7 district; 5 of the 7 district are 31-row partial pulls) · DIFFERENT **6** · UNRECONCILABLE **1** · NATIONAL **4**.

---

## 2. households_100_days  (flagship: `Total_No_of_HHs_completed_100_Days…`, count, state-annual)

| resource_id | dept | class | grain | unit | FY span | metric column | wire? | reason |
|---|---|---|---|---|---|---|---|---|
| 73d68992 | RS | GENUINE | state | count | 2014–15 | `no__of_households_completed_100_days__in_nos____YYYY` | y | completed-100-days count, per-year |
| a1c9803c | RS | GENUINE | state | count | 2016–18 | bare-year cols (title "Completing 100 days") | y | per-year; confirm unit is count at wiring |
| 2d0a4136 | MoSPI | GENUINE | state | count | 2010–15 | `Number of Households Availed 100 days… - YYYY` | y | Implementation Report |
| 3ebbea46 | MoSPI | GENUINE | state | count | 2010–13 | `Number of Households Availed 100 days…-YYYY` | y | as above |
| 9aefcd0f | MoSPI | GENUINE | state | count | 2010–14 | `Number of Households Availed 100 days… - YYYY` | y | as above |
| c11b65d4 | MoSPI | GENUINE | state | count | 2010–17 | `Number of Households Availed 100 days… - YYYY` | y | as above |
| 26837e5a | RS | UNRECONCILABLE | state | count | 2015 | (>100 days, drought 10 states) | n | subset of 10 states, not the full series |
| fca48797 | ? | UNRECONCILABLE | local body | count | 2022–24 | `Families who have completed 100 days… - Total` | n | single Thane Zilla Parishad, SC/ST/Total split — not a state series |
| 1878204d | MoSPI | NATIONAL | national | count | 2006–15 | `Number of Households who availed 100 days…` | axis | All-India |
| 54d1a5fa | MoSPI | NATIONAL | national | count | 2013 | `Number of Households Availed 100 days…` | axis | All-India |
| d88e2cb6 | MoSPI | NATIONAL | national | count | 2006–17 | `Number of Households who availed 100 days…` | axis | All-India |

**Counts:** GENUINE **6** (state) · UNRECONCILABLE **2** · NATIONAL **3**.

---

## 3. active_workers  (flagship: `Total_No_of_Active_Workers`, count, state-annual)

| resource_id | dept | class | grain | unit | FY span | metric column | wire? | reason |
|---|---|---|---|---|---|---|---|---|
| c8687507 | RS | GENUINE | state | lakh→count | 2016–17 | `active_workers_in_lakh_` | y | active-workers count in lakh (×1e5); single year, keys on (state, fy) |

**Counts:** GENUINE **1** (state, one year only) · DIFFERENT **0** · UNRECONCILABLE **0** · NATIONAL **0**.
active_workers is essentially single-source by nature — only one other dataset reports it, for one year.

---

## 4. wages_expenditure  (flagship: `Wages`, INR lakh, state-annual)

| resource_id | dept | class | grain | unit | FY span | metric column | wire? | reason |
|---|---|---|---|---|---|---|---|---|
| d64434e9 | MoSPI | GENUINE | state | INR lakh | 2010–17 | `Expenditure on (In Lakhs) - Wages - YYYY` | y | wage expenditure, per-year, keys on (state, fy) |
| 18527128 | MoSPI | GENUINE | state | INR lakh | 2010–14 | `Expenditure on (in lakhs) - Wages - YYYY` | y | Financial Outcomes; as above |
| fd7c50d2 | MoSPI | GENUINE | state | INR lakh | 2010–15 | `Expenditure on (` In lakhs) -Wages - YYYY` | y | Financial Outcomes; as above |
| 720e21aa | RS | DIFFERENT | state | INR/day | 2012–16 | `average_wage_per_personday__in_rs_____YYYY` | n | wage RATE, not expenditure |
| 4c262a70 | RS | DIFFERENT | state | INR/day | 2019–20 | `mgnrega_wage_rate_as_per_gazette…` | n | notified wage rate |
| 5dcb2b3e | RS | DIFFERENT | state | INR/day | 2018–19 | `wage_rate_in_rs__per_day…` | n | wage rate |
| e0b14917 | RS | DIFFERENT | state | INR/day | 2018–19 | `wage_rate_in_rs__per_day…` | n | wage rate |
| 102ee4c0 | RS | DIFFERENT | state | INR/day | 2011–19 | (notified wage rates) | n | wage rate |
| 27d1d629 | RS | DIFFERENT | state | INR/day | 2016–17 | `mgnrega_notified_wage_rate___fy…` | n | wage rate (vs agri wage) |
| 6ae541ca | RS | DIFFERENT | national | INR/day | 2014–18 | `average_wage_rate_per_day_per_person…` | n | wage rate, and national |
| 9ea040fa | RS | DIFFERENT | state | INR lakh | 2016 | `wage_liability_rs_in_lakh_` | n | payment DUE (liability), not spent |
| c0350589 | RS | DIFFERENT | state | INR lakh | 2018–21 | (Central Funds Released for Wage/Material) | n | funds RELEASED, not expenditure |
| 886d58ec | RS | DIFFERENT | state | count | 2015 | `Wages not paid` | n | complaint count |
| b30c524a | RS | DIFFERENT | state | count | 2015 | `wages_not_paid` | n | complaint count |
| 81043a7e | RS | DIFFERENT | national | count | 2018–19 | (wage-transaction rejections) | n | rejection count |
| 484bf9c5 | RS | DIFFERENT | national | percent | 2016–18 | `percentage_of_expenditure_on_wages_component` | n | a percentage, not the amount |
| 7496d75d | MoSPI | NATIONAL | national | INR lakh | 2008–17 | `Expenditure on - Wages (In lakhs)` | axis | All-India wage expenditure |
| 8d734637 | MoSPI | NATIONAL | national | INR lakh | 2008–15 | `Expenditure on (` In lakhs) - Wages` | axis | All-India |
| 99a91845 | MoSPI | NATIONAL | national | INR lakh | 2008–14 | `Expenditure on (in lakhs) - Wages` | axis | All-India |

**Counts:** GENUINE **3** (state) · DIFFERENT **13** · NATIONAL **3**.

---

## 5. material_expenditure  (flagship: `Material_and_skilled_Wages`, INR lakh, state-annual)

| resource_id | dept | class | grain | unit | FY span | metric column | wire? | reason |
|---|---|---|---|---|---|---|---|---|
| d64434e9 | MoSPI | GENUINE | state | INR lakh | 2010–17 | `Expenditure on (In Lakhs) - Material - YYYY` | y | material expenditure, per-year |
| 18527128 | MoSPI | GENUINE | state | INR lakh | 2010–14 | `Expenditure on (in lakhs) - Material - YYYY` | y | as above |
| fd7c50d2 | MoSPI | GENUINE | state | INR lakh | 2010–15 | `Expenditure on (` In lakhs) -Material - YYYY` | y | as above |
| 484bf9c5 | RS | DIFFERENT | national | percent | 2016–18 | `percentage_of_expenditure_on_material_component` | n | a percentage, not the amount |
| c0350589 | RS | DIFFERENT | state | INR lakh | 2018–21 | (Central Funds Released for Material) | n | funds released, not spent |
| 7496d75d | MoSPI | NATIONAL | national | INR lakh | 2008–17 | `Expenditure on - Material (In lakhs)` | axis | All-India |
| 8d734637 | MoSPI | NATIONAL | national | INR lakh | 2008–15 | `Expenditure on (` In lakhs) - Material` | axis | All-India |
| 99a91845 | MoSPI | NATIONAL | national | INR lakh | 2008–14 | `Expenditure on (in lakhs) - Material` | axis | All-India |

**Counts:** GENUINE **3** (state) · DIFFERENT **2** · NATIONAL **3**.

> Semantic caveat: the flagship column is `Material_and_skilled_Wages` (material **plus skilled
> wages**); the MoSPI "Material" column may or may not fold in skilled wages. Confirm the exact
> definition at wiring before treating a gap as a real disagreement.

---

## 6. admin_expenditure  (flagship: `Total_Adm_Expenditure`, INR lakh, state-annual)

The keyword scan initially reported 0 (the column reads "Administration", not "admin/administrative").
The genuine candidates are the same Financial Outcomes family, which carries an Administration
expenditure column.

| resource_id | dept | class | grain | unit | FY span | metric column | wire? | reason |
|---|---|---|---|---|---|---|---|---|
| d64434e9 | MoSPI | GENUINE | state | INR lakh | 2010–17 | `Expenditure on (In Lakhs) - Administration - YYYY` | y | admin expenditure, per-year |
| 18527128 | MoSPI | GENUINE | state | INR lakh | 2010–14 | `Expenditure on (in lakhs) - Administration - YYYY` | y | as above |
| fd7c50d2 | MoSPI | GENUINE | state | INR lakh | 2010–15 | `Expenditure on (` In lakhs) - Administration - YYYY` | y | as above |
| 7496d75d | MoSPI | NATIONAL | national | INR lakh | 2008–17 | `Expenditure on - Administration (In lakhs)` | axis | All-India |
| 8d734637 | MoSPI | NATIONAL | national | INR lakh | 2008–15 | `Expenditure on (` In lakhs) - Administration` | axis | All-India |
| 99a91845 | MoSPI | NATIONAL | national | INR lakh | 2008–14 | `Expenditure on (in lakhs) - Administration` | axis | All-India |

**Counts:** GENUINE **3** (state) · DIFFERENT **0** · NATIONAL **3**.

---

## Summary — real corroboration scope (evidence, not keyword counts)

For each of the six metrics, how many genuinely-corroborating sources actually exist (able to
reconcile against the flagship state series), versus the earlier title-keyword counts:

| metric | keyword hits (earlier) | GENUINE state | GENUINE district | NATIONAL (separate tier) | DIFFERENT / UNRECON. |
|---|---|---|---|---|---|
| households_employed | ~36 | 11 | 7 (5 partial pulls) | 4 | 7 |
| households_100_days | ~11 | 6 | 0 | 3 | 2 |
| active_workers | ~1 | 1 | 0 | 0 | 0 |
| wages_expenditure | ~19 | 3 | 0 | 3 | 13 |
| material_expenditure | ~8 | 3 | 0 | 3 | 3 |
| admin_expenditure | ~6 | 3 | 0 | 3 | 3 |

Plain-English readout:
- **households_employed** — the richest: **11 state** sources (RS per-year "provided employment"
  tables + the MoSPI Implementation Report series) plus **7 district** (RS + MoRD "households
  worked"; 5 of those are 31-row partial pulls to verify). Genuine multi-source corroboration.
- **households_100_days** — **6 state** sources (the same MoSPI Implementation Report series + two
  RS 100-days tables). Real corroboration.
- **wages / material / admin expenditure** — each has exactly **3 state** sources, and they are the
  *same three datasets* (the MoSPI "Financial Outcomes" state series, 2010–2017), which carry all
  three expenditure components together. So the three money metrics share one corroboration source
  family, not independent ones. The many wage keyword hits (19) are mostly wage **rate** and
  funds-released tables — different metrics.
- **active_workers** — genuinely near single-source: **1** other dataset, one year (2016-17). Wiring
  it buys a single-year cross-check, little more.
- **National tier** — an All-India Implementation Report (households, 100-days; back to 2006-07) and
  All-India Financial Outcomes (wages/material/admin; from 2008-09) series corroborate the national
  aggregate, a different reconciliation axis from the state series.

**Net:** the real wire-them scope is far smaller than keyword counts suggest — dominated by two
source families (the MoSPI Implementation Report for household counts, the MoSPI Financial Outcomes
for the three expenditure components), plus scattered RS per-year household tables, and one
single-year active-workers table. Everything else sharing a keyword is a different metric (rate,
demanded, funds-released, percentage, complaint) or an unreconcilable subset/local-body. No wiring,
extractor, or reconciliation decision is made here — this inventory only establishes the scope.
