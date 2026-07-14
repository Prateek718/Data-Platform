# MGNREGA, 2006-2026: what the record says

*Generated 2026-07-14T04:48:45+00:00 from the MGNREGA canonical series v1.0.0 (DOI [10.5281/zenodo.21318431](https://doi.org/10.5281/zenodo.21318431)), served read-only over MCP.*

> **Every number in this document was machine-verified against the served dataset.** The prose was written by a language model that could see the record only through the query server, and that never chose a number: each figure it was given was re-checked against the data after drafting, each derived figure was recomputed from its inputs, and a section whose numbers failed to check was blocked from the report. The tables beneath each section are the evidence — every figure with its `fact_id` and its sources.

## Abstract

This document is a reconciled, lineage-traced record of MGNREGA, India's rural employment guarantee in force from 2006 until its repeal effective 30 June 2026, assembled from the many separately-published government datasets on data.gov.in into one canonical annual series and read here by an analyst who can see it only through a governed query interface. At its peak in FY 2020-21 the scheme generated 3.88 billion person-days, a scale 4.29 times that of its first year in FY 2006-07. Across the compiled state-year series, publishers materially disagree in 34 cells. The compilation withholds 164 state-year cells as partial-period-only rather than estimating missing values. Every number in this record was machine-verified against served data, and any figure that could not be verified was blocked from printing instead of being guessed.

| figure | value | unit | period | fact_id | sources |
|---|---|---|---|---|---|
| person-days generated at the scheme's peak, FY 2020-21 | 3881318918 | person-days | 2020-21 | `5dbb027fdfca056a` | SRC_FLAGSHIP (ee03643a-ee4c-48c2-ac30-9f2ff26ab722, as of 2026-06-29T17:00:24+00:00) |
| person-days generated in the first year, FY 2006-07 | 905054000 | person-days | 2006-07 | `7a994fb98ad65b7c` | SRC_MOSPI (04476f1d-c61c-4584-9e0a-b1cb62410f5f, as of 2018-11-30T04:47:52+00:00); SRC_MOSPI (1878204d-9048-4016-8e56-a2fe2cf4fe97, as of None); SRC_MOSPI (54d1a5fa-7663-4c10-84ce-c184c7761fcc, as of None); SRC_MOSPI (d88e2cb6-842b-48ed-884c-a561c8f113ff, as of None) |

| count | value | counted over | filter | members |
|---|---|---|---|---|
| state-year cells where publishers materially disagree | 34 | state_annual_series | `confidence == flagged-disagreement` | 34 fact ids in report.json |
| state-year cells the record withholds as partial-period-only | 164 | state_annual_series | `confidence == partial-period-only` | 164 fact ids in report.json |

| derived figure | operation | inputs | value |
|---|---|---|---|
| peak-year person-days, in billions | to_billions | `5dbb027fdfca056a` | 3.88 |
| peak-year person-days as a multiple of the first year's | ratio_2dp | `5dbb027fdfca056a`, `7a994fb98ad65b7c` | 4.29 |

## Introduction

The Mahatma Gandhi National Rural Employment Guarantee Act, enacted in 2005, operated as India's rural employment guarantee from financial year 2006-07, granting rural households a legal right to a fixed annual quota of paid manual work that the state was obliged to supply on demand. Work performed under the programme was recorded in person-days, expenditures in rupees, and participation through the count of households employed. The scheme was repealed effective 30 June 2026 and superseded by a successor programme, rendering its administrative record a closed historical archive to which no new data will be added.

This document is a reading of a reconciled dataset assembled from the multiple government datasets separately published on India's open-data portal, sources that disagree with one another on units, geography, and even the values themselves. It is not an evaluation of the scheme's policy merits and it draws no causal conclusions; instead it reports what the record contains, the confidence attached to those contents, and the points at which it declines to answer. The reconciled series spans financial years from 2006-07 to 2026-27, with 2025-26 the last complete year and the final year's recorded figure covering April 2026 alone. In that last complete year the national person-days generated totalled 2.21 billion person-days.

The record refuses to extend beyond the sealed period, and a request for data on or after 2027-28 returned the explanation "No data on or after 2027-28: MGNREGA was repealed effective 30 June 2026, so the canonical series ends at FY 2026-27 and this is a closed historical record." Consequently, no figures for any period after the repeal will appear in this report.

| figure | value | unit | period | fact_id | sources |
|---|---|---|---|---|---|
| national person-days generated in the last complete year, FY 2025-26 | 2209959751 | person-days | 2025-26 | `83c83d273e27ab9a` | SRC_FLAGSHIP (ee03643a-ee4c-48c2-ac30-9f2ff26ab722, as of 2026-06-29T17:00:24+00:00) |

| derived figure | operation | inputs | value |
|---|---|---|---|
| last complete year's person-days, in billions | to_billions | `83c83d273e27ab9a` | 2.21 |

> **The record refuses:** `query(table="national_annual_series", fy_from="2027-28")`
> → `record_sealed` — No data on or after 2027-28: MGNREGA was repealed effective 30 June 2026, so the canonical series ends at FY 2026-27 and this is a closed historical record.

## Methodology

From the financial year 2018-19 onward, the scheme's national figures derive from the government's district-level management information system, which served as the primary production authority for that period. The years back to 2006-07, when that flagship system published nothing, are instead carried by archived secondary sources such as statistical yearbooks and parliamentary tables, forming a distinct seam that this report does not obscure. The archived sources supply 76 national facts, while the district management information system contributes 72 national facts.

Where two publishers of comparable standing report conflicting numbers for the same cell, the pipeline applies a documented rule and retains the rejected value alongside its publisher and the size of the gap in the lineage, so the disagreement stays visible. If a primary source diverges from a secondary republication of the same statistic, the primary prevails and the divergence is recorded as a flagged note rather than arbitrated between peers. A conflict enters the record only when it is both large in absolute terms and large relative to the value, ensuring that rounding noise is never treated as a dispute.

Cells where an honest assertion is impossible—such as a reading that covers only part of a year or an incomplete aggregate that contradicts a complete one—are left empty and bear the reason for omission; an empty cell is never rendered as a zero.

The prose of this document was composed by a language model that never selected a numeral; every figure was fetched from the query server by code with its provenance attached, and any combined totals or ratios were computed and independently recomputed by code, with each printed number checked back against the served data, blocking the section if a mismatch occurred. The model itself could not query the data or perform arithmetic, and when a request sought the state annual series using the label '2019', the record declined to answer, stating: "Malformed financial year '2019'. Expected exactly 'YYYY-YY', where the two-digit suffix is the start year plus one — e.g. '2018-19' for the year running April 2018 to March 2019."

| count | value | counted over | filter | members |
|---|---|---|---|---|
| national facts carried by the pre-2018 archived sources | 76 | national_annual_series | `era_basis == historical` | 76 fact ids in report.json |
| national facts carried by the district management information system | 72 | national_annual_series | `era_basis == flagship-rollup` | 72 fact ids in report.json |

> **The record refuses:** `query(table="state_annual_series", fy_from="2019")`
> → `invalid_period` — Malformed financial year '2019'. Expected exactly 'YYYY-YY', where the two-digit suffix is the start year plus one — e.g. '2018-19' for the year running April 2018 to March 2019.

## The twenty-year record, 2006-07 to 2026-27

In its inaugural financial year 2006-07, MGNREGA generated 0.91 billion person-days across India. The scheme reached a peak of 3.88 billion person-days in 2020-21, a volume 4.29 times that of the first year. The final complete financial year, 2025-26, recorded 2.21 billion person-days.

During the peak year 2020-21, total expenditure stood at 1.1 lakh crore rupees and the scheme employed 75.5 million households. The national series combines two sourcing eras: 76 facts derive from pre-2018 archived publishers such as MoSPI and Rajya Sabha answers, while 72 facts from FY 2018-19 onward come from the flagship district management information system.

FY 2026-27 is not a full year but a repeal stub, covering only April 2026 with 12.91 million person-days, and is not comparable to a complete annual tally; the scheme was repealed effective 30 June 2026, making 2025-26 the last complete financial year. The record declines to provide figures for 2027-28 and afterward, quoting the reason: "No data on or after 2027-28: MGNREGA was repealed effective 30 June 2026, so the canonical series ends at FY 2026-27 and this is a closed historical record."

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

| count | value | counted over | filter | members |
|---|---|---|---|---|
| national facts sourced from the pre-2018 archive (historical era) | 76 | national_annual_series | `era_basis == historical` | 76 fact ids in report.json |
| national facts sourced from the flagship district MIS (FY 2018-19 onward) | 72 | national_annual_series | `era_basis == flagship-rollup` | 72 fact ids in report.json |

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

The record maintains two distinct and separately counted classes of publisher disagreement over MGNREGA statistics, and the two are never merged into a single homogeneous tally. Before 2018, nine state-year cells exhibit material disagreement between two archived publishers of the same statistic, the Ministry of Statistics and Programme Implementation and Rajya Sabha parliamentary answers, with reconciliation adjudicating a canonical value between these corroborating sources of comparable standing. From fiscal year 2018-19 onward, twenty-five state-year cells show divergence between the primary district management information system and figures tabled in Parliament, a mismatch recorded as a flagged note rather than adjudicated between peers. Both sets clear the same two-part materiality floor, under which a disagreement qualifies only if it passes both an absolute threshold and a relative threshold.

The largest pre-2018 cross-publisher disagreement occurs in Telangana for total expenditure in fiscal year 2016-17, where the record adopts the Rajya Sabha value of 210898.07 INR lakh while preserving the rejected MoSPI estimate in lineage so the variance remains visible. In this earlier class, the winning figure is entered and the rejected publisher is kept, ensuring the disagreement stays exposed rather than smoothed away.

The largest flagship-era divergence appears in Lakshadweep for person-days generated in fiscal year 2023-24, where the record takes the primary district MIS count of 3510 person-days and retains the Parliament-tabled figure in lineage as a flagged note. The primary district MIS, as the production authority for the period it covers, prevails in such cases, and the tabled parliamentary number is not discarded.

Across both sets, the record contains 34 cells carrying flagged disagreements within the historical MGNREGA record. This governance posture surfaces mismatches between publishers instead of concealing them, demonstrating that the scheme's dataset documents its own contradictions rather than hiding them.

| figure | value | unit | period | fact_id | sources |
|---|---|---|---|---|---|
| Telangana total expenditure, FY 2016-17 — the largest pre-2018 disagreement; the record takes the Rajya Sabha value and keeps MoSPI's rejected value in lineage | 210898.07 | INR lakh | 2016-17 | `744999f0f06a48a9` | SRC_MOSPI (d64434e9-fc81-4834-954b-5e494e0ee2c7, as of None); SRC_RS (57bff16a-6423-45b2-9700-ebcde6709937, as of 2021-03-23T11:28:45+00:00) |
| Lakshadweep person-days, FY 2023-24 — the largest flagship-era divergence; the record takes the MIS value and records the Parliament-tabled figure in lineage | 3510 | person-days | 2023-24 | `cfa86a20e8b191f3` | SRC_FLAGSHIP (ee03643a-ee4c-48c2-ac30-9f2ff26ab722, as of 2026-06-29T17:00:24+00:00); SRC_RS (cea6ee41-2b18-4266-b42b-0af54c13b18c, as of 2025-03-07T05:53:39+00:00); SRC_RS (e289a8fe-3fd4-4964-9579-5bddb88e36b8, as of 2024-11-02T17:56:25+00:00) |

| count | value | counted over | filter | members |
|---|---|---|---|---|
| pre-2018 cross-publisher material disagreements, ADJUDICATED between MoSPI and Rajya Sabha (state series) | 9 | state_annual_series | `confidence == flagged-disagreement` | 9 fact ids in report.json |
| flagship-era divergences between the primary district MIS and figures tabled in Parliament, RECORDED as flagged notes (state series, FY 2018-19 onward) | 25 | state_annual_series | `confidence == flagged-disagreement` | 25 fact ids in report.json |

| derived figure | operation | inputs | value |
|---|---|---|---|
| flagged cells in the record (the two sets added together) | sum | `pre_2018_disagreements`, `flagship_era_divergences` (34 facts; enumerated in report.json) | 34 |

## Goa, FY 2022-23: the spine reconciles, and the rate refuses to

North Goa generated 42,253 person-days under MGNREGA in FY 2022-23. South Goa generated 51,751 person-days in the same year. These district figures sum to 94,004 person-days. The Goa state series for person-days generated reports the identical total, with the difference between state and district sum computed as 0 person-days.

The average wage rate per day is a rate metric served only at district-annual grain for Goa in FY 2022-23. North Goa shows an average wage rate of 383.782169313422 INR for that year. South Goa shows 330.927390775057 INR for the same period. The state series does not contain this metric at state grain; when asked for the wage rate at state level, the server states: "Metric 'avg_wage_rate_per_day' is not available at this grain; it lives in district_flagship. Call get_schema for a table's metrics." Summing the two district rates would not yield a valid state wage rate.

The dataset is annual-grain only for this scheme. When queried for a monthly figure, the server responds: "The series is annual-grain only; monthly figures are not served. In particular, monthly avg_wage_rate_per_day values are cumulative year-to-date ratios, not valid monthly rates — the wage rate is published only as the financial-year-final annual value at district-annual grain. Remove 'month' to query the annual series." Consequently, person-days aggregate without residual across districts, but the average wage rate refuses both state consolidation and monthly dissection.

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

> **The record refuses:** `query(table="state_annual_series", metrics=["avg_wage_rate_per_day"], states=["Goa"])`
> → `unknown_metric` — Metric 'avg_wage_rate_per_day' is not available at this grain; it lives in district_flagship. Call get_schema for a table's metrics.

> **The record refuses:** `query(table="district_flagship", states=["Goa"], month="2022-04")`
> → `monthly_wage_unavailable` — The series is annual-grain only; monthly figures are not served. In particular, monthly avg_wage_rate_per_day values are cumulative year-to-date ratios, not valid monthly rates — the wage rate is published only as the financial-year-final annual value at district-annual grain. Remove 'month' to query the annual series.

## The wage rate the record will not price by the month

The record provides an average wage rate per day solely at district-annual grain for completed financial years, serving 5645 such facts from FY 2018-19 to 2025-26. This wage rate is published only as the financial-year-final annual value and is not offered at any coarser geographic aggregation within the served tables.

For FY 2026-27, the year never completed because the scheme was repealed effective 30 June 2026, and the record contains 0 wage-rate facts; an incomplete year yields no annual rate, so the record withholds any part-year ratio rather than presenting it as a wage.

Monthly wage figures are refused outright. The server states: "The series is annual-grain only; monthly figures are not served. In particular, monthly avg_wage_rate_per_day values are cumulative year-to-date ratios, not valid monthly rates — the wage rate is published only as the financial-year-final annual value at district-annual grain. Remove 'month' to query the annual series."

A small number of financial-year-final rates are implausibly high, with 9 such rates exceeding Rs 1,000 per day; these are data-quality artifacts of the source series, not observed wages. The highest stands at 3582 INR, recorded for Hooghly, West Bengal in FY 2023-24. A plausible MGNREGA daily wage is an order of magnitude lower than these figures, and they are carried faithfully with their lineage rather than deleted, so a reader must not interpret them as amounts paid to any worker.

| figure | value | unit | period | fact_id | sources |
|---|---|---|---|---|---|
| the highest financial-year-final wage rate in the record: Hooghly, West Bengal, FY 2023-24 — an artifact, not a wage anyone was paid | 3582 | INR | 2023-24 | `d8fff0db43079540` | SRC_FLAGSHIP (ee03643a-ee4c-48c2-ac30-9f2ff26ab722, as of 2026-06-29T17:00:24+00:00) |

| count | value | counted over | filter | members |
|---|---|---|---|---|
| district-annual wage-rate facts the record serves (FY 2018-19 to 2025-26) | 5645 | district_flagship | `all` | 5645 fact ids in report.json |
| wage-rate facts for FY 2026-27, the repeal-truncated year | 0 | district_flagship | `all` | 0 fact ids in report.json |
| financial-year-final wage rates above Rs 1,000/day — source data-quality artifacts, not observed wages | 9 | district_flagship | `value > 1000 (implausible as a daily wage)` | 9 fact ids in report.json |

> **The record refuses:** `query(table="district_flagship", metrics=["avg_wage_rate_per_day"], month="2022-04")`
> → `monthly_wage_unavailable` — The series is annual-grain only; monthly figures are not served. In particular, monthly avg_wage_rate_per_day values are cumulative year-to-date ratios, not valid monthly rates — the wage rate is published only as the financial-year-final annual value at district-annual grain. Remove 'month' to query the annual series.

> **The record refuses:** `query(table="state_annual_series", metrics=["avg_wage_rate_per_day"])`
> → `unknown_metric` — Metric 'avg_wage_rate_per_day' is not available at this grain; it lives in district_flagship. Call get_schema for a table's metrics.

## What the record does not contain

The record withholds 164 state-series null cells because only a mid-year partial reading existed, refusing publication as if it were an annual figure. A further 10 state-series null cells are withheld as unadjudicated, where a structurally incomplete aggregate materially disagrees with a whole-geography peer and no value is asserted. The national series contributes 19 null cells withheld due to single-publisher divergence, where one publisher's own vintages disagree with no defensible order. Across all reasons, the record contains 193 null cells.

Of the partial-period withholdings, 163 occur in FY 2017-18, the seam between the two eras. This concentration makes FY 2017-18 the record's weakest year, exactly at the meeting point of its two sourcing eras.

The active workers metric exists only from FY 2018-19 onward, with 33 active-workers facts recorded at state grain in that first year. Any comparison of worker counts across the full twenty years would therefore set a metric against its own absence.

The state series does not provide data before FY 2010-11. When asked for the state series for FY 2008-09, the server declined, stating "The state series starts at FY 2010-11; no state-grain data exists before it. The national series covers FY 2006-07 onward — query national_annual_series instead." No state-grain observations exist prior to FY 2010-11, while the national series extends back to FY 2006-07.

![Null cells in the state series, by financial year](charts/nulls-by-year.svg)

*A null cell is data carrying a reason, never a zero. Almost all of them fall in FY 2017-18 — the seam between the two sourcing eras, the year before the flagship MIS begins. The record's weakest year is exactly where its two eras meet. FY 2026-27 is omitted: the scheme was repealed effective 30 June 2026, so that year holds April 2026 alone and a single month cannot be plotted against full years. Its figures are reported in the text and the tables. Plotted from 16 verified figures; the figure ids are listed in `report.json` under `charts`.*

| count | value | counted over | filter | members |
|---|---|---|---|---|
| state-series null cells withheld as partial-period-only | 164 | state_annual_series | `confidence == partial-period-only` | 164 fact ids in report.json |
| state-series null cells withheld as unadjudicated | 10 | state_annual_series | `confidence == unadjudicated` | 10 fact ids in report.json |
| national-series null cells withheld as single-publisher divergence | 19 | national_annual_series | `confidence == single-publisher divergence` | 19 fact ids in report.json |
| state-series null cells in FY 2017-18 alone, the seam between the two eras | 163 | state_annual_series | `value_is_null` | 163 fact ids in report.json |
| active-workers facts at state grain in FY 2018-19, the metric's first year | 33 | state_annual_series | `all` | 33 fact ids in report.json |

| derived figure | operation | inputs | value |
|---|---|---|---|
| null cells in the record, all reasons together | sum | `partial_period_nulls`, `unadjudicated_nulls`, `national_divergence_nulls` (193 facts; enumerated in report.json) | 193 |

> **The record refuses:** `query(table="state_annual_series", fy_to="2008-09")`
> → `state_series_floor` — The state series starts at FY 2010-11; no state-grain data exists before it. The national series covers FY 2006-07 onward — query national_annual_series instead.

## The district set is not a constant

The administrative geography underpinning MGNREGA's district-level reporting was not static during the scheme's operation. In the flagship's inaugural financial year, FY 2018-19, 666 districts reported person-days.

By FY 2023-24, the count of districts reporting person-days had risen to 738, a net increase of 72 districts across the interval. Each district's annual person-days fact remains archived under the boundaries that prevailed in that district's own reporting period. The source does not forward-map a pre-split district's figures onto the successor jurisdictions created by later reorganisation, because any such redistribution would demand an allocation ratio that the dataset never published and would constitute fabrication of values.

The expansion in the number of reporting districts reflects the splitting of existing districts rather than the addition of new territory to the scheme's remit. The historical person-days for a district that was later divided therefore continue to sit wholly with the original unit as it existed at the time.

The record does not extend below the state level for periods before the flagship era. It declines to supply district-level data prior to FY 2018-19, stating: "The district drill-down starts at FY 2018-19 (the flagship era); no district-level data exists before it. Use the state or national series for earlier years."

![Districts reporting person-days, by financial year](charts/districts-by-year.svg)

*Districts split over the life of the scheme. Each fact stays filed under the geography that existed at its own period and is never forward-mapped across a split, so the rise is districts dividing, not territory being added. FY 2026-27 is omitted: the scheme was repealed effective 30 June 2026, so that year holds April 2026 alone and a single month cannot be plotted against full years. Its figures are reported in the text and the tables. Plotted from 8 verified figures; the figure ids are listed in `report.json` under `charts`.*

| count | value | counted over | filter | members |
|---|---|---|---|---|
| districts reporting person-days in FY 2018-19 (the flagship's first year) | 666 | district_flagship | `all` | 666 fact ids in report.json |
| districts reporting person-days in FY 2023-24 | 738 | district_flagship | `all` | 738 fact ids in report.json |

| derived figure | operation | inputs | value |
|---|---|---|---|
| districts added between FY 2018-19 and FY 2023-24 | difference | `districts_2023_24`, `districts_2018_19` (1404 facts; enumerated in report.json) | 72 |

> **The record refuses:** `query(table="district_flagship", fy_to="2015-16")`
> → `district_series_floor` — The district drill-down starts at FY 2018-19 (the flagship era); no district-level data exists before it. Use the state or national series for earlier years.

## What this record refuses to answer

The historical record of MGNREGA is a closed account of a scheme repealed effective 30 June 2026, and it declines to extend beyond that boundary. Requests for data on or after the financial year 2027-28 are met with the plain statement: "No data on or after 2027-28: MGNREGA was repealed effective 30 June 2026, so the canonical series ends at FY 2026-27 and this is a closed historical record." The same protective stance applies to temporal grain, as the record refuses monthly figures because it holds only annual observations, noting "The series is annual-grain only; monthly figures are not served. In particular, monthly avg_wage_rate_per_day values are cumulative year-to-date ratios, not valid monthly rates — the wage rate is published only as the financial-year-final annual value at district-annual grain. Remove 'month' to query the annual series."

At the level of metric definitions, the record will not supply a wage rate at state grain because that measure is confined to district detail, and it responds: "Metric 'avg_wage_rate_per_day' is not available at this grain; it lives in district_flagship. Call get_schema for a table's metrics." A similar boundary guards the district drill-down, which the record limits to the flagship era; it refuses earlier district data with the explanation "The district drill-down starts at FY 2018-19 (the flagship era); no district-level data exists before it. Use the state or national series for earlier years."

The record also refuses a malformed financial-year label, stating "Malformed financial year '2019'. Expected exactly 'YYYY-YY', where the two-digit suffix is the start year plus one" and an unknown geography is rejected outright: "Unknown state 'Atlantis' (give an LGD code or current LGD name)." Finally, the lineage table is not available through the query verb, with the direction "The lineage table is not queryable via query(); it is per-fact provenance. Use get_lineage(fact_id) instead."

Across these refusals, each identifies the invalid element and directs the inquirer to another grain, series, or verb. The record thereby confines itself to the exact scope of the sealed historical scheme rather than producing conjectural output.

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

This record does not contain monthly MGNREGA figures at any level of geography, because the series is annual-grain only. The source’s response to a request for a monthly value was: "The series is annual-grain only; monthly figures are not served. In particular, monthly wage-rate values are cumulative year-to-date ratios, not valid monthly rates — the wage rate is published only as the financial-year-final annual value at district-annual grain. Remove the month parameter to query the annual series." Consequently, figures derived from monthly columns that circulate elsewhere cannot be reproduced or checked within this document, and they are not repeated here.

The year FY 2017-18, immediately before the district system begins, is the weakest point in the series, with 163 cells withheld in that single year. Comparisons that straddle this seam should therefore be made with caution.

Nine district-year wage rates stand above Rs 1,000 a day, and the highest of these artifacts is 3582 INR from Hooghly, West Bengal in FY 2023-24. These values are not wages that any worker received; a plausible MGNREGA daily wage is an order of magnitude lower. They are defects of the source series carried into the record with their provenance rather than deleted, so a reader can see and discount them.

Active workers is a metric reported only from FY 2018-19 onward, and in that first year the record holds 33 such facts at state grain. Any comparison across the scheme’s full span would set this metric against its own absence before that point.

| figure | value | unit | period | fact_id | sources |
|---|---|---|---|---|---|
| the highest district-year wage rate in the record (Hooghly, West Bengal, FY 2023-24) | 3582 | INR | 2023-24 | `d8fff0db43079540` | SRC_FLAGSHIP (ee03643a-ee4c-48c2-ac30-9f2ff26ab722, as of 2026-06-29T17:00:24+00:00) |

| count | value | counted over | filter | members |
|---|---|---|---|---|
| cells the record withholds in FY 2017-18, the seam year | 163 | state_annual_series | `value_is_null` | 163 fact ids in report.json |
| district-year wage rates above Rs 1,000 a day (source artifacts, not wages paid) | 9 | district_flagship | `value > 1000 (implausible as a daily wage)` | 9 fact ids in report.json |
| active-workers facts at state grain in FY 2018-19, the metric's first year | 33 | state_annual_series | `all` | 33 fact ids in report.json |

> **The record refuses:** `query(table="district_flagship", month="2022-04")`
> → `monthly_wage_unavailable` — The series is annual-grain only; monthly figures are not served. In particular, monthly avg_wage_rate_per_day values are cumulative year-to-date ratios, not valid monthly rates — the wage rate is published only as the financial-year-final annual value at district-annual grain. Remove 'month' to query the annual series.

## How to cite, and how to check this

The dataset this report reads is a sealed, DOI-versioned release: **MGNREGA canonical series v1.0.0**, DOI [10.5281/zenodo.21318431](https://doi.org/10.5281/zenodo.21318431). MGNREGA was repealed effective 30 June 2026, so the record is closed — it will not change, and neither will the figures below.

**To reproduce this report**, from a checkout of the repository with the release artifacts in `dist/v1.0/` (the server checksum-verifies them at startup and refuses to run if a byte differs):

```bash
OPENROUTER_API_KEY=...  PYTHONPATH=src uv run python -m data_platform.analyst
```

Any OpenAI-compatible endpoint works; the model writes the prose and nothing else.

**To check any single number**, take its `fact_id` from the table beneath the section, start the query server (`PYTHONPATH=src uv run python -m data_platform.mcp`) and call `get_lineage(fact_id)`. You will get back every source that carried the fact, its resource id on the open-data portal, its as-of date, the value it reported, and — where publishers disagreed — the value that was rejected and the rule that decided it. The full payload is also embedded in `report.json`, so the answer is already in your hands; the record is sealed, so the live lookup cannot return anything different.
