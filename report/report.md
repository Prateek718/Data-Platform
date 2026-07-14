# MGNREGA, 2006-2026: what the record says

*Generated 2026-07-14T10:41:32+00:00 from the MGNREGA Canonical Series v1.0.0 (DOI [10.5281/zenodo.21318927](https://doi.org/10.5281/zenodo.21318927)) by Prateek, served read-only over MCP.*

> **Every number in this document was machine-verified against the served dataset.** The prose was written by a language model that could see the record only through the query server, and that never chose a number: each figure it was given was re-checked against the data after drafting, each derived figure was recomputed from its inputs, and a section whose numbers failed to check was blocked from the report. The tables beneath each section are the evidence — every figure with its `fact_id` and its sources.

## Abstract

This document is a reconciled, lineage-traced record of MGNREGA, India's rural employment guarantee, in force from FY 2006-07 until its repeal, assembled from many separately-published government datasets on data.gov.in into one canonical annual series and read by an analyst through a governed query interface. At its peak in FY 2020-21, the scheme generated 3.88 billion person-days, a scale 4.29 times that of its first year. Across the state annual series, publishers materially disagree in 34 state-year cells, and the record withholds 164 state-year cells as partial-period-only rather than guessing. Every number in this document was machine-verified against served data, and any figure that could not be verified was blocked rather than printed.

| figure | value | unit | period | fact_id | sources |
|---|---|---|---|---|---|
| person-days generated at the scheme's peak, FY 2020-21 | 3881318918 | person-days | 2020-21 | `5dbb027fdfca056a` | SRC_FLAGSHIP (ee03643a-ee4c-48c2-ac30-9f2ff26ab722, as of 2026-06-29T17:00:24+00:00) |
| person-days generated in the first year, FY 2006-07 | 905054000 | person-days | 2006-07 | `7a994fb98ad65b7c` | SRC_MOSPI (04476f1d-c61c-4584-9e0a-b1cb62410f5f, as of 2018-11-30T04:47:52+00:00); SRC_MOSPI (1878204d-9048-4016-8e56-a2fe2cf4fe97, as of None); SRC_MOSPI (54d1a5fa-7663-4c10-84ce-c184c7761fcc, as of None); SRC_MOSPI (d88e2cb6-842b-48ed-884c-a561c8f113ff, as of None) |

| count | value | selected by (the complete predicate) | members |
|---|---|---|---|
| state-year cells where publishers materially disagree | 34 | `table = state_annual_series AND confidence == flagged-disagreement` | 34 fact ids in report.json |
| state-year cells the record withholds as partial-period-only | 164 | `table = state_annual_series AND confidence == partial-period-only` | 164 fact ids in report.json |

| derived figure | operation | inputs | value |
|---|---|---|---|
| peak-year person-days, in billions | to_billions | `5dbb027fdfca056a` | 3.88 |
| peak-year person-days as a multiple of the first year's | ratio_2dp | `5dbb027fdfca056a`, `7a994fb98ad65b7c` | 4.29 |

## Introduction

The Mahatma Gandhi National Rural Employment Guarantee Act, enacted in 2005, operated as India's rural employment guarantee from financial year 2006-07. Under its provisions, rural households held a legal right to a fixed annual quota of paid manual labour, with the state bound to supply that work on demand. Administrative measurement tracked effort in person-days, expenditure in rupees, and reach in households employed. The scheme was repealed with effect from 30 June 2026, rendering its archival record permanently closed.

This document is a reading of a reconciled dataset built from the multiple government publications on India's open-data portal, sources that diverge on units, geographic boundaries, and the numerical values themselves. It is not an assessment of the scheme's policy merits and it advances no causal claims, limiting itself to stating what the record contains, the confidence attached, and the points where it withholds answer. The covered span runs from financial year 2006-07 through financial year 2026-27, with 2025-26 standing as the last complete year and generating 2.21 billion person-days of work. The terminal financial year 2026-27 is incomplete, its available figure confined to April 2026.

The record refuses to supply information beyond the repeal horizon. When asked for figures from 2027-28 onward, it responds: "No data on or after 2027-28: MGNREGA was repealed effective 30 June 2026, so the canonical series ends at FY 2026-27 and this is a closed historical record." No successor programme appears in the data, and this report therefore asserts nothing about any replacement.

| figure | value | unit | period | fact_id | sources |
|---|---|---|---|---|---|
| national person-days generated in the last complete year, FY 2025-26 | 2209959751 | person-days | 2025-26 | `83c83d273e27ab9a` | SRC_FLAGSHIP (ee03643a-ee4c-48c2-ac30-9f2ff26ab722, as of 2026-06-29T17:00:24+00:00) |

| derived figure | operation | inputs | value |
|---|---|---|---|
| last complete year's person-days, in billions | to_billions | `83c83d273e27ab9a` | 2.21 |

> **The record refuses:** `query(table="national_annual_series", fy_from="2027-28")`
> → `record_sealed` — No data on or after 2027-28: MGNREGA was repealed effective 30 June 2026, so the canonical series ends at FY 2026-27 and this is a closed historical record.

## Methodology

From FY 2018-19, the government's own district-level management information system acts as the primary production authority and contributes 72 national facts. Prior to that year, the same system published nothing, so the record carries 76 national facts from archived secondary sources, including statistical yearbooks and tables tabled in Parliament in answer to questions, for the years back to 2006-07. The transition between these two bodies of data is a seam that the report acknowledges rather than conceals.

When two publishers of comparable standing report conflicting numbers for the same cell, the pipeline applies a documented rule and preserves the rejected value, its publisher, and the size of the gap within the lineage, so the disagreement stays published. Where the district-level management information system disagrees with a figure tabled in Parliament for the same cell, the primary system stands and the divergence is recorded as a flagged note rather than adjudicated between peers. A conflict is entered into the record only if it meets a two-part materiality floor, demanding both a large absolute difference and a large difference relative to the value, ensuring rounding noise is never reported as a conflict.

Cells where the only available reading covers part of a year, or where an incomplete aggregate contradicts a complete one, are left empty with the reason for omission attached, and such cells are never written as zero. The record also declines to answer a request for the state annual series filed under the year '2019', stating: "Malformed financial year '2019'. Expected exactly 'YYYY-YY', where the two-digit suffix is the start year plus one — e.g. '2018-19' for the year running April 2018 to March 2019."

The prose of this report was written by a language model, but the model never selected a number. Each figure was retrieved from the query server by code with its provenance attached, and any combined figures such as sums or ratios were computed by code and recomputed independently afterward. Every number in the finished text was checked back against the served data, and any figure that failed the check blocked its section from the report entirely. The model cannot query the data or perform arithmetic; it can only narrate what it was handed.

| count | value | selected by (the complete predicate) | members |
|---|---|---|---|
| national facts carried by the pre-2018 archived sources | 76 | `table = national_annual_series AND era_basis == historical` | 76 fact ids in report.json |
| national facts carried by the district management information system | 72 | `table = national_annual_series AND era_basis == flagship-rollup` | 72 fact ids in report.json |

> **The record refuses:** `query(table="state_annual_series", fy_from="2019")`
> → `invalid_period` — Malformed financial year '2019'. Expected exactly 'YYYY-YY', where the two-digit suffix is the start year plus one — e.g. '2018-19' for the year running April 2018 to March 2019.

## The twenty-year record, 2006-07 to 2026-27

MGNREGA's national record opens in financial year 2006-07 with 0.91 billion person-days generated under the scheme. Employment scaled to a peak in 2020-21, when 3.88 billion person-days were recorded, a level 4.29 times that of the first year. The final complete financial year, 2025-26, saw 2.21 billion person-days. In the peak year of 2020-21, total expenditure reached 1.1 lakh crore rupees and the scheme employed 75.5 million households.

The annual national series is assembled from two distinct sourcing eras. It draws on 76 facts from the pre-2018 archive classified as the historical era, and on 72 facts sourced from the flagship district management information system covering FY 2018-19 onward.

Financial year 2026-27 is not a full year but a stub limited to April 2026, reporting 12.91 million person-days that cannot be compared with complete-year totals; the scheme was repealed effective 30 June 2026, leaving 2025-26 as the last complete financial year. The record carries no figures from 2027-28 onward, and the data server states in response to such queries: "No data on or after 2027-28: MGNREGA was repealed effective 30 June 2026, so the canonical series ends at FY 2026-27 and this is a closed historical record."

![Person-days of employment generated, all-India, FY 2006-07 to 2025-26](charts/national-persondays.svg)

*Every point is a verified fact in the canonical series; a year the record withholds is drawn as no point, never as zero, and the line breaks there. FY 2026-27 is omitted: the scheme was repealed effective 30 June 2026, so that year holds April 2026 alone and a single month cannot be plotted against full years. Its figures are reported in the text and the tables. Plotted from 17 verified figures; the figure ids are listed in `report.json` under `charts`.*

![Total expenditure, all-India, FY 2008-09 to 2025-26](charts/national-expenditure.svg)

*Expenditure in lakh crore rupees, reconciled across publishers. The pre-2018 points come from archived MoSPI and Rajya Sabha sources; from FY 2018-19 the flagship district MIS is the production authority. FY 2026-27 is omitted: the scheme was repealed effective 30 June 2026, so that year holds April 2026 alone and a single month cannot be plotted against full years. Its figures are reported in the text and the tables. Plotted from 16 verified figures; the figure ids are listed in `report.json` under `charts`.*

| figure | value | unit | period | fact_id | sources |
|---|---|---|---|---|---|
| national person-days generated, FY 2006-07 (the first year) | 905054000 | person-days | 2006-07 | `7a994fb98ad65b7c` | SRC_MOSPI (04476f1d-c61c-4584-9e0a-b1cb62410f5f, as of 2018-11-30T04:47:52+00:00); SRC_MOSPI (1878204d-9048-4016-8e56-a2fe2cf4fe97, as of None); SRC_MOSPI (54d1a5fa-7663-4c10-84ce-c184c7761fcc, as of None); SRC_MOSPI (d88e2cb6-842b-48ed-884c-a561c8f113ff, as of None) |
| national person-days generated, FY 2020-21 (the peak year) | 3881318918 | person-days | 2020-21 | `5dbb027fdfca056a` | SRC_FLAGSHIP (ee03643a-ee4c-48c2-ac30-9f2ff26ab722, as of 2026-06-29T17:00:24+00:00) |
| national person-days generated, FY 2025-26 (the last complete year) | 2209959751 | person-days | 2025-26 | `83c83d273e27ab9a` | SRC_FLAGSHIP (ee03643a-ee4c-48c2-ac30-9f2ff26ab722, as of 2026-06-29T17:00:24+00:00) |
| national person-days generated, FY 2026-27 (April 2026 only — a repeal stub) | 12914539 | person-days | 2026-27 | `8091ebe4d569f7bc` | SRC_FLAGSHIP (ee03643a-ee4c-48c2-ac30-9f2ff26ab722, as of 2026-06-29T17:00:24+00:00) |
| national total expenditure, FY 2020-21 | 10999798.601773694 | INR lakh | 2020-21 | `1283dfe2b4694161` | SRC_FLAGSHIP (ee03643a-ee4c-48c2-ac30-9f2ff26ab722, as of 2026-06-29T17:00:24+00:00) |
| national households employed, FY 2020-21 | 75500579 | count | 2020-21 | `4da0d36e5d5d1ff1` | SRC_FLAGSHIP (ee03643a-ee4c-48c2-ac30-9f2ff26ab722, as of 2026-06-29T17:00:24+00:00) |

| count | value | selected by (the complete predicate) | members |
|---|---|---|---|
| national facts sourced from the pre-2018 archive (historical era) | 76 | `table = national_annual_series AND era_basis == historical` | 76 fact ids in report.json |
| national facts sourced from the flagship district MIS (FY 2018-19 onward) | 72 | `table = national_annual_series AND era_basis == flagship-rollup` | 72 fact ids in report.json |

| derived figure | operation | inputs | value |
|---|---|---|---|
| peak-year person-days divided by first-year person-days (2 decimal places) | ratio_2dp | `5dbb027fdfca056a`, `7a994fb98ad65b7c` | 4.29 |
| first-year person-days, in billions | to_billions | `7a994fb98ad65b7c` | 0.91 |
| peak-year person-days, in billions | to_billions | `5dbb027fdfca056a` | 3.88 |
| last complete year's person-days, in billions | to_billions | `83c83d273e27ab9a` | 2.21 |
| the repeal stub's person-days, in millions | to_millions | `8091ebe4d569f7bc` | 12.91 |
| peak-year total expenditure, in lakh crore rupees | lakh_to_lakh_crore | `1283dfe2b4694161` | 1.1 |
| peak-year households employed, in millions | to_millions | `4da0d36e5d5d1ff1` | 75.5 |

> **The record refuses:** `query(table="national_annual_series", fy_from="2027-28")`
> → `record_sealed` — No data on or after 2027-28: MGNREGA was repealed effective 30 June 2026, so the canonical series ends at FY 2026-27 and this is a closed historical record.

## Where the publishers disagree, and what the record does about it

The record separates pre-2018 state-year cells where MoSPI and Rajya Sabha parliamentary answers materially disagreed from flagship-era state-year cells where the primary district MIS diverged from figures tabled in Parliament. The first set, adjudicated between sources of comparable standing under cross-source reconciliation, comprises 9 cells. The second set, recorded as flagged notes under the authority rule that favours the production authority for its covered period, comprises 25 cells. Both sets passed the same two-part materiality floor requiring a disagreement to clear an absolute and a relative threshold before being counted.

One such case is Telangana's total expenditure for FY 2016-17, for which the record publishes a canonical value of 2108.98 crore rupees drawn from the Rajya Sabha figure, not the size of the gap between publishers. The rejected MoSPI value remains in lineage, and the disagreement stays visible rather than smoothed away.

One such case is Lakshadweep's person-days generated in FY 2023-24, for which the record publishes a canonical value of 3,510 person-days from the primary district MIS, not the magnitude of divergence from the Parliament-tabled figure. The Parliament-tabled number is retained in lineage as a flagged note, reflecting the authority accorded to the primary district MIS for that period.

Across the two separately-counted phenomena, the record carries 34 flagged cells in total. This separation and retention of rejected values demonstrates that the scheme's archive surfaces its disagreements instead of concealing them.

| figure | value | unit | period | fact_id | sources |
|---|---|---|---|---|---|
| Telangana total expenditure, FY 2016-17 — one pre-2018 case: this is the CANONICAL VALUE the record publishes (the Rajya Sabha figure), not the size of the gap; MoSPI's rejected value is kept in lineage | 210898.07 | INR lakh | 2016-17 | `744999f0f06a48a9` | SRC_MOSPI (d64434e9-fc81-4834-954b-5e494e0ee2c7, as of None); SRC_RS (57bff16a-6423-45b2-9700-ebcde6709937, as of 2021-03-23T11:28:45+00:00) |
| Lakshadweep person-days, FY 2023-24 — one flagship-era case: this is the CANONICAL VALUE the record publishes (the district MIS figure), not the size of the gap; the Parliament-tabled figure is kept in lineage | 3510 | person-days | 2023-24 | `cfa86a20e8b191f3` | SRC_FLAGSHIP (ee03643a-ee4c-48c2-ac30-9f2ff26ab722, as of 2026-06-29T17:00:24+00:00); SRC_RS (cea6ee41-2b18-4266-b42b-0af54c13b18c, as of 2025-03-07T05:53:39+00:00); SRC_RS (e289a8fe-3fd4-4964-9579-5bddb88e36b8, as of 2024-11-02T17:56:25+00:00) |

| count | value | selected by (the complete predicate) | members |
|---|---|---|---|
| pre-2018 cross-publisher material disagreements, ADJUDICATED between MoSPI and Rajya Sabha (state series) | 9 | `table = state_annual_series AND fy <= 2017-18 AND confidence == flagged-disagreement` | 9 fact ids in report.json |
| flagship-era divergences between the primary district MIS and figures tabled in Parliament, RECORDED as flagged notes (state series, FY 2018-19 onward) | 25 | `table = state_annual_series AND fy >= 2018-19 AND confidence == flagged-disagreement` | 25 fact ids in report.json |

| derived figure | operation | inputs | value |
|---|---|---|---|
| flagged cells in the record (the two sets added together) | sum | `pre_2018_disagreements`, `flagship_era_divergences` (34 facts; enumerated in report.json) | 34 |
| Telangana's canonical FY 2016-17 total expenditure, in crore rupees | lakh_to_crore | `744999f0f06a48a9` | 2108.98 |

## Goa, FY 2022-23: the spine reconciles, and the rate refuses to

In FY 2022-23, the Goa state series records 94,004 person-days generated under the employment guarantee scheme. North Goa accounted for 42,253 person-days and South Goa for 51,751 person-days, and the difference between the state total and the sum of these two district figures is 0 person-days, confirming exact reconciliation at the district drill-down.

The average wage rate per day is a rate metric served only at district-annual grain, with North Goa at 383.78 rupees per day and South Goa at 330.93 rupees per day for the same year. Because it is not an additive count, combining the two district values into a single figure is not a meaningful operation, and the state series does not provide a wage rate aggregate.

When queried for the wage rate at state grain, the data server responded: "Metric 'avg_wage_rate_per_day' is not available at this grain; it lives in district_flagship. Call get_schema for a table's metrics." The record is annual-only, and a request for a monthly figure produced the statement: "The series is annual-grain only; monthly figures are not served. In particular, monthly avg_wage_rate_per_day values are cumulative year-to-date ratios, not valid monthly rates — the wage rate is published only as the financial-year-final annual value at district-annual grain. Remove 'month' to query the annual series."

| figure | value | unit | period | fact_id | sources |
|---|---|---|---|---|---|
| North Goa person-days generated, FY 2022-23 | 42253 | person-days | 2022-23 | `daf9afc0d6e9f3b7` | SRC_FLAGSHIP (ee03643a-ee4c-48c2-ac30-9f2ff26ab722, as of 2026-06-29T17:00:24+00:00) |
| South Goa person-days generated, FY 2022-23 | 51751 | person-days | 2022-23 | `fee085bea82444c5` | SRC_FLAGSHIP (ee03643a-ee4c-48c2-ac30-9f2ff26ab722, as of 2026-06-29T17:00:24+00:00) |
| Goa state person-days generated, FY 2022-23 | 94004 | person-days | 2022-23 | `ad36ce29ea24bc59` | SRC_FLAGSHIP (ee03643a-ee4c-48c2-ac30-9f2ff26ab722, as of 2026-06-29T17:00:24+00:00); SRC_RS (cea6ee41-2b18-4266-b42b-0af54c13b18c, as of 2025-03-07T05:53:39+00:00); SRC_RS (e289a8fe-3fd4-4964-9579-5bddb88e36b8, as of 2024-11-02T17:56:25+00:00) |
| North Goa average wage rate per day, FY 2022-23 | 383.782169313422 | INR | 2022-23 | `60979827dc6c1ac9` | SRC_FLAGSHIP (ee03643a-ee4c-48c2-ac30-9f2ff26ab722, as of 2026-06-29T17:00:24+00:00) |
| South Goa average wage rate per day, FY 2022-23 | 330.927390775057 | INR | 2022-23 | `5031de1acacf402e` | SRC_FLAGSHIP (ee03643a-ee4c-48c2-ac30-9f2ff26ab722, as of 2026-06-29T17:00:24+00:00) |

| derived figure | operation | inputs | value |
|---|---|---|---|
| North Goa plus South Goa person-days | sum | `daf9afc0d6e9f3b7`, `fee085bea82444c5` | 94004 |
| state person-days minus the district sum | difference | `ad36ce29ea24bc59`, `daf9afc0d6e9f3b7`, `fee085bea82444c5` | 0 |
| North Goa's average wage rate per day, to the paisa | round_2dp | `60979827dc6c1ac9` | 383.78 |
| South Goa's average wage rate per day, to the paisa | round_2dp | `5031de1acacf402e` | 330.93 |

> **The record refuses:** `query(table="state_annual_series", metrics=["avg_wage_rate_per_day"], states=["Goa"])`
> → `unknown_metric` — Metric 'avg_wage_rate_per_day' is not available at this grain; it lives in district_flagship. Call get_schema for a table's metrics.

> **The record refuses:** `query(table="district_flagship", states=["Goa"], month="2022-04")`
> → `monthly_wage_unavailable` — The series is annual-grain only; monthly figures are not served. In particular, monthly avg_wage_rate_per_day values are cumulative year-to-date ratios, not valid monthly rates — the wage rate is published only as the financial-year-final annual value at district-annual grain. Remove 'month' to query the annual series.

## The wage rate the record will not price by the month

The record supplies average wage rate per day only at the district-annual grain for completed financial years, serving 5,645 such facts from FY 2018-19 through FY 2025-26. It does not provide this wage metric at state grain, because the underlying data holds the figure exclusively within district-level records. The scheme’s wage rate is never priced by the month.

For FY 2026-27, the record contains 0 wage-rate facts. The scheme was repealed effective 30 June 2026, leaving that year incomplete, and an unfinished financial year yields no annual rate; the record therefore withholds any part-year ratio rather than presenting it as a wage.

The record declines to provide monthly wage figures. The data source states: "The series is annual-grain only; monthly figures are not served. In particular, monthly avg_wage_rate_per_day values are cumulative year-to-date ratios, not valid monthly rates — the wage rate is published only as the financial-year-final annual value at district-annual grain. Remove 'month' to query the annual series."

A small number of financial-year-final rates are implausibly high and must not be read as observed wages: 9 such rates exceed Rs 1,000 per day, and the highest is 3,582 INR in Hooghly, West Bengal for FY 2023-24. A plausible MGNREGA daily wage is an order of magnitude lower than these figures. These values are data-quality artifacts of the source series, carried faithfully into the record with their lineage rather than deleted, and a reader must not interpret them as amounts paid to any worker.

| figure | value | unit | period | fact_id | sources |
|---|---|---|---|---|---|
| the highest financial-year-final wage rate in the record: Hooghly, West Bengal, FY 2023-24 — an artifact, not a wage anyone was paid | 3582 | INR | 2023-24 | `d8fff0db43079540` | SRC_FLAGSHIP (ee03643a-ee4c-48c2-ac30-9f2ff26ab722, as of 2026-06-29T17:00:24+00:00) |

| count | value | selected by (the complete predicate) | members |
|---|---|---|---|
| district-annual wage-rate facts the record serves (FY 2018-19 to 2025-26) | 5645 | `table = district_flagship AND metric in (avg_wage_rate_per_day)` | 5645 fact ids in report.json |
| wage-rate facts for FY 2026-27, the repeal-truncated year | 0 | `table = district_flagship AND metric in (avg_wage_rate_per_day) AND fy == 2026-27` | 0 fact ids in report.json |
| financial-year-final wage rates above Rs 1,000/day — source data-quality artifacts, not observed wages | 9 | `table = district_flagship AND metric in (avg_wage_rate_per_day) AND value > 1000 (implausible as a daily wage)` | 9 fact ids in report.json |

> **The record refuses:** `query(table="district_flagship", metrics=["avg_wage_rate_per_day"], month="2022-04")`
> → `monthly_wage_unavailable` — The series is annual-grain only; monthly figures are not served. In particular, monthly avg_wage_rate_per_day values are cumulative year-to-date ratios, not valid monthly rates — the wage rate is published only as the financial-year-final annual value at district-annual grain. Remove 'month' to query the annual series.

> **The record refuses:** `query(table="state_annual_series", metrics=["avg_wage_rate_per_day"])`
> → `unknown_metric` — Metric 'avg_wage_rate_per_day' is not available at this grain; it lives in district_flagship. Call get_schema for a table's metrics.

## What the record does not contain

The record treats a null cell as a datum carrying a reason rather than a gap coerced to zero. At state grain, 164 cells are withheld as partial-period-only because the only reading was an edition’s mid-year partial, and 10 are withheld as unadjudicated after a structurally incomplete aggregate materially disagreed with a whole-geography peer. At national grain, 19 cells are withheld as single-publisher divergence where one publisher’s own vintages disagree with no defensible order between them. All reasons together account for 193 null cells in the record.

In FY 2017-18, the year before the district system begins and the point where the record’s two sourcing eras meet, 163 state cells are withheld as partial-period-only. The record declines to supply state-grain observations before FY 2010-11, responding with the statement "The state series starts at FY 2010-11; no state-grain data exists before it. The national series covers FY 2006-07 onward — query national_annual_series instead."

The national nulls fall only in FY 2012-13 (6 cells), FY 2013-14 (4 cells), FY 2014-15 (7 cells) and FY 2015-16 (2 cells), and there are no national nulls in any other year. These withheld cells are distributed across the 8 metrics that the national series carries rather than concentrated in one.

Among those metrics, households employed, wages expenditure and total expenditure each account for 2 withheld cells, while households completed 100 days, persondays generated and admin expenditure each account for 3, material skilled expenditure accounts for 4, and active workers is the one metric untouched, with no pre-2018 values to disagree about.

The national expenditure series does not open with the scheme, as the count of national total-expenditure facts in FY 2006-07 and FY 2007-08 is 0, whereas person-days and households are recorded from the first year; this is an absence of source data rather than a withheld value and explains why the expenditure chart starts two years later than the person-days chart. Active workers is a metric absent rather than null, existing only from FY 2018-19 onward, and the count of such facts at state grain in that first year is 33, so any comparison of workers across the full twenty years would set a metric against its own absence.

![Null cells in the state series, by financial year](charts/nulls-by-year.svg)

*A null cell is data carrying a reason, never a zero. Almost all of them fall in FY 2017-18 — the seam between the two sourcing eras, the year before the flagship MIS begins. The record's weakest year is exactly where its two eras meet. FY 2026-27 is omitted: the scheme was repealed effective 30 June 2026, so that year holds April 2026 alone and a single month cannot be plotted against full years. Its figures are reported in the text and the tables. Plotted from 16 verified figures; the figure ids are listed in `report.json` under `charts`.*

| count | value | selected by (the complete predicate) | members |
|---|---|---|---|
| state-series null cells withheld as partial-period-only | 164 | `table = state_annual_series AND confidence == partial-period-only` | 164 fact ids in report.json |
| state-series null cells withheld as unadjudicated | 10 | `table = state_annual_series AND confidence == unadjudicated` | 10 fact ids in report.json |
| national-series null cells withheld as single-publisher divergence | 19 | `table = national_annual_series AND confidence == single-publisher divergence` | 19 fact ids in report.json |
| state cells that are BOTH in FY 2017-18 AND withheld as partial-period-only (the seam between the two sourcing eras) | 163 | `table = state_annual_series AND fy == 2017-18 AND confidence == partial-period-only` | 163 fact ids in report.json |
| national total-expenditure facts in FY 2006-07 and FY 2007-08 — none exist; the spending series starts two years after the work series | 0 | `table = national_annual_series AND metric in (total_expenditure) AND fy >= 2006-07 AND fy <= 2007-08` | 0 fact ids in report.json |
| active-workers facts at state grain in FY 2018-19, the metric's first year | 33 | `table = state_annual_series AND metric in (active_workers) AND fy == 2018-19` | 33 fact ids in report.json |
| national cells withheld as single-publisher divergence in FY 2012-13 | 6 | `table = national_annual_series AND fy == 2012-13 AND confidence == single-publisher divergence` | 6 fact ids in report.json |
| national cells withheld as single-publisher divergence in FY 2013-14 | 4 | `table = national_annual_series AND fy == 2013-14 AND confidence == single-publisher divergence` | 4 fact ids in report.json |
| national cells withheld as single-publisher divergence in FY 2014-15 | 7 | `table = national_annual_series AND fy == 2014-15 AND confidence == single-publisher divergence` | 7 fact ids in report.json |
| national cells withheld as single-publisher divergence in FY 2015-16 | 2 | `table = national_annual_series AND fy == 2015-16 AND confidence == single-publisher divergence` | 2 fact ids in report.json |
| national households employed cells withheld as single-publisher divergence | 2 | `table = national_annual_series AND metric in (households_employed) AND confidence == single-publisher divergence` | 2 fact ids in report.json |
| national households completed 100 days cells withheld as single-publisher divergence | 3 | `table = national_annual_series AND metric in (households_completed_100_days) AND confidence == single-publisher divergence` | 3 fact ids in report.json |
| national active workers cells withheld as single-publisher divergence | 0 | `table = national_annual_series AND metric in (active_workers) AND confidence == single-publisher divergence` | 0 fact ids in report.json |
| national persondays generated cells withheld as single-publisher divergence | 3 | `table = national_annual_series AND metric in (persondays_generated) AND confidence == single-publisher divergence` | 3 fact ids in report.json |
| national wages expenditure cells withheld as single-publisher divergence | 2 | `table = national_annual_series AND metric in (wages_expenditure) AND confidence == single-publisher divergence` | 2 fact ids in report.json |
| national material skilled expenditure cells withheld as single-publisher divergence | 4 | `table = national_annual_series AND metric in (material_skilled_expenditure) AND confidence == single-publisher divergence` | 4 fact ids in report.json |
| national admin expenditure cells withheld as single-publisher divergence | 3 | `table = national_annual_series AND metric in (admin_expenditure) AND confidence == single-publisher divergence` | 3 fact ids in report.json |
| national total expenditure cells withheld as single-publisher divergence | 2 | `table = national_annual_series AND metric in (total_expenditure) AND confidence == single-publisher divergence` | 2 fact ids in report.json |

| derived figure | operation | inputs | value |
|---|---|---|---|
| null cells in the record, all reasons together | sum | `partial_period_nulls`, `unadjudicated_nulls`, `national_divergence_nulls` (193 facts; enumerated in report.json) | 193 |

> **The record refuses:** `query(table="state_annual_series", fy_to="2008-09")`
> → `state_series_floor` — The state series starts at FY 2010-11; no state-grain data exists before it. The national series covers FY 2006-07 onward — query national_annual_series instead.

## The district set is not a constant

The number of districts reporting person-days under the flagship component was not constant across the scheme's life. In the flagship's first year, FY 2018-19, 666 districts reported person-days. By the last complete financial year, FY 2025-26, 738 districts reported. The net increase of 72 districts between those years comprises additions minus any that stopped reporting; the record does not state that no districts ceased reporting, so the figure is a net change rather than a count of districts added.

Under the scheme's data practices, each district person-days fact remains filed under the geography that existed in its own financial year and is never forward-mapped across a subsequent split. Redistributing an earlier district's value across its successors would require an allocation the source never published, which would amount to inventing data. Consequently, the district count observed in any year reflects the administrative map operative in that year.

The growth in reporting districts is consistent with existing districts dividing rather than territory being added, though the record does not establish the cause of the rise. It documents only the larger count at the later date without linking the change to specific boundary events.

The record declines to supply district-level figures before the flagship era. In its own words, "The district drill-down starts at FY 2018-19 (the flagship era); no district-level data exists before it. Use the state or national series for earlier years." No district counts preceding FY 2018-19 can therefore be drawn from this series.

![Districts reporting person-days, by financial year](charts/districts-by-year.svg)

*Districts split over the life of the scheme. Each fact stays filed under the geography that existed at its own period and is never forward-mapped across a split, so the rise is districts dividing, not territory being added. FY 2026-27 is omitted: the scheme was repealed effective 30 June 2026, so that year holds April 2026 alone and a single month cannot be plotted against full years. Its figures are reported in the text and the tables. Plotted from 8 verified figures; the figure ids are listed in `report.json` under `charts`.*

| count | value | selected by (the complete predicate) | members |
|---|---|---|---|
| districts reporting person-days in FY 2018-19 (the flagship's first year) | 666 | `table = district_flagship AND metric in (persondays_generated) AND fy == 2018-19` | 666 fact ids in report.json |
| districts reporting person-days in FY 2025-26 (the last complete year) | 738 | `table = district_flagship AND metric in (persondays_generated) AND fy == 2025-26` | 738 fact ids in report.json |

| derived figure | operation | inputs | value |
|---|---|---|---|
| NET increase in districts reporting between FY 2018-19 and FY 2025-26 (additions minus any that stopped reporting — not a count of districts added) | difference | `districts_2025_26`, `districts_2018_19` (1404 facts; enumerated in report.json) | 72 |

> **The record refuses:** `query(table="district_flagship", fy_to="2015-16")`
> → `district_series_floor` — The district drill-down starts at FY 2018-19 (the flagship era); no district-level data exists before it. Use the state or national series for earlier years.

## What this record refuses to answer

The closed historical record of MGNREGA refuses any request for data on or after the financial year 2027-28, protecting the sealed series from extension beyond its repeal. The scheme was repealed effective 30 June 2026, and the canonical series ends at FY 2026-27. The record's answer is: "No data on or after 2027-28: MGNREGA was repealed effective 30 June 2026, so the canonical series ends at FY 2026-27 and this is a closed historical record."

A request for a monthly figure is declined because the series is annual-grain only, and the wage rate is published solely as a financial-year-final annual value at district-annual grain. The record says: "The series is annual-grain only; monthly figures are not served. In particular, monthly avg_wage_rate_per_day values are cumulative year-to-date ratios, not valid monthly rates — the wage rate is published only as the financial-year-final annual value at district-annual grain. Remove 'month' to query the annual series." A query for the average wage rate at state grain is likewise refused, since that metric resides in the district drill-down rather than the state table. The reason given is: "Metric 'avg_wage_rate_per_day' is not available at this grain; it lives in district_flagship. Call get_schema for a table's metrics." These refusals protect against treating a non-additive rate as if it were comparable across grains.

District-level data before the flagship era is not supplied, because the district drill-down begins at FY 2018-19 and no finer geography exists earlier. The record instructs: "The district drill-down starts at FY 2018-19 (the flagship era); no district-level data exists before it. Use the state or national series for earlier years." A malformed financial-year label is rejected rather than silently compared as a string that would yield a wrong answer. The refusal reads: "Malformed financial year '2019'. Expected exactly 'YYYY-YY', where the two-digit suffix is the start year plus one — e.g. '2018-19' for the year running April 2018 to March 2019." An unknown geography is not guessed but refused with a pointer to valid identifiers. The stated reason is: "Unknown state 'Atlantis' (give an LGD code or current LGD name)." Each of these protects the record from invalid keys and from false drill-downs.

The lineage table cannot be retrieved through the analytical query verb, and the record redirects to the provenance-specific call. It answers: "The lineage table is not queryable via query(); it is per-fact provenance. Use get_lineage(fact_id) instead." This preserves lineage as per-fact provenance rather than a queryable table.

> **The record refuses:** `query(table="national_annual_series", fy_from="2027-28")`
> → `record_sealed` — No data on or after 2027-28: MGNREGA was repealed effective 30 June 2026, so the canonical series ends at FY 2026-27 and this is a closed historical record.

> **The record refuses:** `query(table="district_flagship", month="2022-04")`
> → `monthly_wage_unavailable` — The series is annual-grain only; monthly figures are not served. In particular, monthly avg_wage_rate_per_day values are cumulative year-to-date ratios, not valid monthly rates — the wage rate is published only as the financial-year-final annual value at district-annual grain. Remove 'month' to query the annual series.

> **The record refuses:** `query(table="state_annual_series", metrics=["avg_wage_rate_per_day"])`
> → `unknown_metric` — Metric 'avg_wage_rate_per_day' is not available at this grain; it lives in district_flagship. Call get_schema for a table's metrics.

> **The record refuses:** `query(table="district_flagship", fy_to="2015-16")`
> → `district_series_floor` — The district drill-down starts at FY 2018-19 (the flagship era); no district-level data exists before it. Use the state or national series for earlier years.

> **The record refuses:** `query(table="state_annual_series", fy_from="2019")`
> → `invalid_period` — Malformed financial year '2019'. Expected exactly 'YYYY-YY', where the two-digit suffix is the start year plus one — e.g. '2018-19' for the year running April 2018 to March 2019.

> **The record refuses:** `query(table="state_annual_series", states=["Atlantis"])`
> → `unknown_geography` — Unknown state 'Atlantis' (give an LGD code or current LGD name).

> **The record refuses:** `query(table="lineage")`
> → `table_not_queryable` — The lineage table is not queryable via query(); it is per-fact provenance. Use get_lineage(fact_id) instead.

## Limitations

The record does not provide monthly figures at any level of geography, and it declines to answer such queries. It states: "The series is annual-grain only; monthly figures are not served. In particular, monthly avg_wage_rate_per_day values are cumulative year-to-date ratios, not valid monthly rates — the wage rate is published only as the financial-year-final annual value at district-annual grain. Remove 'month' to query the annual series." Consequently, figures that circulate elsewhere and are derived from those monthly columns cannot be reproduced or checked here, and this document does not repeat them.

In FY 2017-18 the record withholds 163 cells, marking this year as a weak point in the series where comparisons that straddle it should be made with care. The withheld entries appear in the state annual series for that financial year.

The record carries 9 district-year wage rates above Rs 1,000 a day, the highest being 3,582 INR in Hooghly, West Bengal, for FY 2023-24. These values are not wages paid to workers but defects of the source series, carried into the record faithfully with their provenance rather than quietly deleted so that a reader can see and discount them.

The active workers metric is reported only from FY 2018-19 onward, with 33 active-workers facts at state grain in that first year. Comparing this metric across the full span of the scheme would compare a measure against its own absence before that point.

| figure | value | unit | period | fact_id | sources |
|---|---|---|---|---|---|
| the highest district-year wage rate in the record (Hooghly, West Bengal, FY 2023-24) | 3582 | INR | 2023-24 | `d8fff0db43079540` | SRC_FLAGSHIP (ee03643a-ee4c-48c2-ac30-9f2ff26ab722, as of 2026-06-29T17:00:24+00:00) |

| count | value | selected by (the complete predicate) | members |
|---|---|---|---|
| cells the record withholds in FY 2017-18, the seam year | 163 | `table = state_annual_series AND fy == 2017-18 AND value_is_null` | 163 fact ids in report.json |
| district-year wage rates above Rs 1,000 a day (source artifacts, not wages paid) | 9 | `table = district_flagship AND metric in (avg_wage_rate_per_day) AND value > 1000 (implausible as a daily wage)` | 9 fact ids in report.json |
| active-workers facts at state grain in FY 2018-19, the metric's first year | 33 | `table = state_annual_series AND metric in (active_workers) AND fy == 2018-19` | 33 fact ids in report.json |

> **The record refuses:** `query(table="district_flagship", month="2022-04")`
> → `monthly_wage_unavailable` — The series is annual-grain only; monthly figures are not served. In particular, monthly avg_wage_rate_per_day values are cumulative year-to-date ratios, not valid monthly rates — the wage rate is published only as the financial-year-final annual value at district-annual grain. Remove 'month' to query the annual series.

## How to cite, and how to check this

The dataset this report reads is a sealed, DOI-versioned release: **MGNREGA Canonical Series v1.0.0**, DOI [10.5281/zenodo.21318927](https://doi.org/10.5281/zenodo.21318927). MGNREGA was repealed effective 30 June 2026, so the record is closed — it will not change, and neither will the figures below.

**To reproduce this report**, from a checkout of the repository with the release artifacts in `dist/v1.0/` (the server checksum-verifies them at startup and refuses to run if a byte differs):

```bash
OPENROUTER_API_KEY=...  PYTHONPATH=src uv run python -m data_platform.analyst
```

Any OpenAI-compatible endpoint works; the model writes the prose and nothing else.

**To cite this report:**

> Prateek (2026). *MGNREGA, 2006-2026: what the record says.* Generated from the MGNREGA Canonical Series v1.0.0 [dataset], DOI [10.5281/zenodo.21318927](https://doi.org/10.5281/zenodo.21318927).

**To cite the dataset itself:** Prateek (2026). *MGNREGA Canonical Series* (v1.0.0) [dataset]. Zenodo. DOI [10.5281/zenodo.21318927](https://doi.org/10.5281/zenodo.21318927). That is the **version** DOI — it pins this immutable release, which is what a citation needs. The **concept** DOI [10.5281/zenodo.21318431](https://doi.org/10.5281/zenodo.21318431) resolves to the record across all its versions. Cite the dataset for the figures and this report for the reading of them.

**To check any single number**, take its `fact_id` from the table beneath the section, start the query server (`PYTHONPATH=src uv run python -m data_platform.mcp`) and call `get_lineage(fact_id)`. You will get back every source that carried the fact, its resource id on the open-data portal, its as-of date, the value it reported, and — where publishers disagreed — the value that was rejected and the rule that decided it. The full payload is also embedded in `report.json`, so the answer is already in your hands; the record is sealed, so the live lookup cannot return anything different.
