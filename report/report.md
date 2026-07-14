# MGNREGA, 2006-2026: what the record says

*Generated 2026-07-14T05:22:29+00:00 from the MGNREGA canonical series v1.0.0 (DOI [10.5281/zenodo.21318431](https://doi.org/10.5281/zenodo.21318431)), served read-only over MCP.*

> **Every number in this document was machine-verified against the served dataset.** The prose was written by a language model that could see the record only through the query server, and that never chose a number: each figure it was given was re-checked against the data after drafting, each derived figure was recomputed from its inputs, and a section whose numbers failed to check was blocked from the report. The tables beneath each section are the evidence — every figure with its `fact_id` and its sources.

## Abstract

This document is a reconciled, lineage-traced record of MGNREGA, India's rural employment guarantee scheme that remained in force from 2006 until its repeal effective 30 June 2026, compiled from the numerous separately published government datasets on data.gov.in into a single canonical annual series and accessed here solely through a governed query interface. At its peak in fiscal year 2020-21, the scheme generated 3.88 billion person-days of work, a volume equal to 4.29 times the person-days recorded in its inaugural fiscal year of 2006-07. Within the state-year grid, publishers materially disagree in 34 cells, while the record withholds 164 cells as covering only partial periods rather than estimating missing values. What distinguishes this compilation is that each quantity it presents has been machine-verified against the served data, and any figure that could not be confirmed was suppressed from publication instead of being printed.

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

The Mahatma Gandhi National Rural Employment Guarantee Act was enacted in 2005 and functioned as India's rural employment guarantee from financial year 2006-07. It granted rural households a legal right to a fixed annual quota of paid manual work, with the state obligated to provide that employment on demand. Administrative records expressed work in person-days, spending in rupees, and participation through households employed. The scheme was repealed effective 30 June 2026 and superseded by a successor programme, leaving its historical record closed with no new data to be published.

This report is a reading of a reconciled dataset assembled from the many separately published government datasets on India's open-data portal, which diverge on units, geography, and the figures themselves. It is not an assessment of the scheme's policy merits and it advances no causal claims, limiting itself to stating what the record holds, the degree of confidence, and where it withholds answer. The record spans financial years 2006-07 to 2026-27, with the last complete financial year being 2025-26 and the closing year's available coverage restricted to April 2026.

The record furnishes no information on or after 2027-28, and the server's stated reason is: "No data on or after 2027-28: MGNREGA was repealed effective 30 June 2026, so the canonical series ends at FY 2026-27 and this is a closed historical record."

| figure | value | unit | period | fact_id | sources |
|---|---|---|---|---|---|
| national person-days generated in the last complete year, FY 2025-26 | 2209959751 | person-days | 2025-26 | `83c83d273e27ab9a` | SRC_FLAGSHIP (ee03643a-ee4c-48c2-ac30-9f2ff26ab722, as of 2026-06-29T17:00:24+00:00) |

| derived figure | operation | inputs | value |
|---|---|---|---|
| last complete year's person-days, in billions | to_billions | `83c83d273e27ab9a` | 2.21 |

> **The record refuses:** `query(table="national_annual_series", fy_from="2027-28")`
> → `record_sealed` — No data on or after 2027-28: MGNREGA was repealed effective 30 June 2026, so the canonical series ends at FY 2026-27 and this is a closed historical record.

## Methodology

From the financial year 2018-19 onward, the scheme's national figures derive from the government's district-level management information system, which served as the primary production authority for that period. For the earlier years back to 2006-07, the flagship system published no comparable records, so archived secondary sources—statistical yearbooks and tables tabled in Parliament in answer to questions—carry the series. The national facts carried by that district management information system number 72, while the pre-2018 archived sources supply 76 national facts. The join between these two bodies of data is a seam, and the report makes no claim of continuity beyond what the sources themselves provide.

Where two publishers of comparable standing report conflicting values for the same cell, the pipeline applies a documented rule and retains the rejected value alongside its publisher and the size of the gap in the lineage, so the disagreement is published rather than concealed. If a primary source diverges from a secondary republication of the same statistic, the primary figure stands and the divergence is recorded as a flagged note instead of being adjudicated between peers. A disagreement enters the record only when it satisfies a two-part materiality floor, requiring both a large absolute difference and a large difference relative to the value, ensuring that rounding noise is never treated as conflict.

When the pipeline cannot honestly assert a value—because the only available reading covers part of a year or because an incomplete aggregate contradicts a complete one—the cell is left empty and bears the reason for its omission. An empty cell is never rendered as a zero, preserving the distinction between absence of data and a true null count.

The prose of this document was written by a language model that never selected a number; each figure was retrieved from the query server by code with its provenance attached, and any figures the report combines were computed by code and recomputed independently afterward. Every numeric claim in the finished text was checked back against the served data, and a number that failed the check blocked its section from the report entirely. The model cannot query the data or perform arithmetic, and can only narrate what it was handed. The record declined to answer a request for a state-level annual record using the financial year 2019, returning the reason "Malformed financial year '2019'. Expected exactly 'YYYY-YY', where the two-digit suffix is the start year plus one — e.g. '2018-19' for the year running April 2018 to March 2019."

| count | value | counted over | filter | members |
|---|---|---|---|---|
| national facts carried by the pre-2018 archived sources | 76 | national_annual_series | `era_basis == historical` | 76 fact ids in report.json |
| national facts carried by the district management information system | 72 | national_annual_series | `era_basis == flagship-rollup` | 72 fact ids in report.json |

> **The record refuses:** `query(table="state_annual_series", fy_from="2019")`
> → `invalid_period` — Malformed financial year '2019'. Expected exactly 'YYYY-YY', where the two-digit suffix is the start year plus one — e.g. '2018-19' for the year running April 2018 to March 2019.

## The twenty-year record, 2006-07 to 2026-27

MGNREGA's national record opens in 2006-07 with 0.91 billion person-days generated under the scheme. The programme reached its highest annual scale in 2020-21, when 3.88 billion person-days were recorded, a volume 4.29 times that of the inaugural year. The final complete financial year of operation, 2025-26, accounted for 2.21 billion person-days.

In the peak year of 2020-21, total expenditure amounted to 1.1 lakh crore rupees and 75.5 million households were employed. The national time series is stitched from two distinct sourcing eras, comprising 76 facts from the pre-2018 archive derived from archived publishers such as MoSPI and Rajya Sabha answers, and 72 facts from the flagship district MIS beginning in FY 2018-19.

Financial year 2026-27 is a stub rather than a full annual cycle, carrying only 12.91 million person-days from April 2026, and the scheme was repealed effective 30 June 2026 so this partial count is not comparable to a complete year; the last complete financial year therefore remains 2025-26. The record holds no data from 2027-28 onward because, as the data server stated, "No data on or after 2027-28: MGNREGA was repealed effective 30 June 2026, so the canonical series ends at FY 2026-27 and this is a closed historical record."

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

The closed MGNREGA record maintains two distinct and separately counted classes of publisher disagreement that must not be merged into a single homogeneous tally. Before 2018, state-year cells where the archived MoSPI series and Rajya Sabha parliamentary answers reported materially different statistics were reconciled by adjudicating a canonical value between corroborating sources of comparable standing, with the winning figure recorded and the rejected publisher's value preserved in lineage so the divergence remains visible. From FY 2018-19 onward, the flagship-era class captures state-year cells where the primary district MIS diverges from figures tabled in Parliament; the authority rule grants precedence to the production authority's MIS, and the mismatch is entered as a flagged note while the Parliament-tabled number is retained in lineage rather than discarded. Both sets cleared the same two-part materiality floor, admitting a disagreement only when it satisfies both an absolute and a relative threshold. The pre-2018 adjudicated cross-publisher disagreements comprise 9 state-series cells, the flagship-era recorded divergences comprise 25 state-series cells, and the combined flagged cells in the record total 34.

The largest pre-2018 cross-publisher disagreement occurs in Telangana total expenditure for FY 2016-17, where the record adopts the Rajya Sabha value and keeps MoSPI's rejected figure in lineage, amounting to 210898.07 INR lakh. This extreme case sits among the adjudicated cells that preserve both sources rather than suppressing the conflict.

The largest flagship-era divergence appears in Lakshadweep person-days for FY 2023-24, where the record takes the MIS value and records the Parliament-tabled figure in lineage, with a magnitude of 3510 person-days. That outlier falls within the set of flagged notes that crown the primary MIS without peer adjudication.

By retaining rejected values and tabled alternatives in lineage and by marking divergences as flags rather than erasing them, the archive demonstrates its disagreements instead of hiding them, a governance property rather than a scandal.

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

In FY 2022-23, MGNREGA person-days generated at the Goa state level numbered 94004. North Goa generated 42253 person-days and South Goa 51751 person-days under the scheme that year. The district totals combine to match the state aggregate with a residual of 0 person-days.

The average wage rate per day is a distinct metric, observed at district-annual grain only. North Goa's rate was 383.782169313422 INR and South Goa's 330.927390775057 INR for FY 2022-23. The state series does not provide a wage rate figure, so no state sum can be computed from the district values.

When queried for the wage rate at state level, the record declines to supply it, stating: "Metric 'avg_wage_rate_per_day' is not available at this grain; it lives in district_flagship. Call get_schema for a table's metrics." The dataset therefore limits this metric to the two district values for the year.

Any request for a monthly figure is refused. The server responds: "The series is annual-grain only; monthly figures are not served. In particular, monthly avg_wage_rate_per_day values are cumulative year-to-date ratios, not valid monthly rates — the wage rate is published only as the financial-year-final annual value at district-annual grain. Remove 'month' to query the annual series." Consequently, the average wage rate per day exists in the record solely as financial-year-final annual values for North Goa and South Goa.

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

The record provides 5645 district-annual average wage rate per day facts for MGNREGA, spanning the complete financial years from 2018-19 to 2025-26, and it does so exclusively at district-annual grain. The wage rate is not offered at state aggregation; the record declines to supply it there because the metric lives only in the district-level series.

For the truncated financial year 2026-27, which ended incomplete when the scheme was repealed effective 30 June 2026, the record holds 0 wage-rate facts, as an unfinished year produces no annual rate and the record withholds any part-year ratio rather than publish it as a wage. Monthly wage figures are refused outright. The record states: "The series is annual-grain only; monthly figures are not served. In particular, monthly avg_wage_rate_per_day values are cumulative year-to-date ratios, not valid monthly rates — the wage rate is published only as the financial-year-final annual value at district-annual grain. Remove 'month' to query the annual series."

A small number of financial-year-final rates are implausibly high and are not observed wages: 9 district-annual rates exceed Rs 1,000 per day, and the highest is 3582 INR for Hooghly, West Bengal in 2023-24. These values are data-quality artifacts of the source series, carried into the record with their lineage instead of being quietly deleted, and a plausible MGNREGA daily wage is an order of magnitude lower than they are. A reader must not treat them as amounts paid to any worker.

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

The MGNREGA record treats a null cell as a substantive datum carrying an explicit reason, never coercing it to zero. Across the state series, 164 annual values were withheld as partial-period-only readings where only a mid-year partial existed, and a further 10 were withheld as unadjudicated because a structurally incomplete aggregate materially disagreed with a whole-geography peer. The national series contributed 19 null cells arising from single-publisher divergence, where one publisher's vintages disagreed with no defensible ordering. Taken together, the record contains 193 null cells across all such reasons.

Almost all of the partial-period-only nulls concentrate in a single financial year, FY 2017-18, which accounts for 163 of those state-series cells. This year sits at the seam between the scheme's two sourcing eras, immediately before the flagship management information system begins. The record thus identifies its weakest coverage exactly at the junction of its two data-collection regimes.

A distinct absence appears in the form of a metric rather than a null cell: active workers are present only from FY 2018-19 onward, with 33 state-grain observations recorded in that inaugural year. Any comparison of 'workers' across the scheme's full twenty-year span would therefore set a measured quantity against a period where the metric simply does not exist.

The record also declines to supply state-level annual data for periods before its state series commences. When queried for FY 2008-09, it returned the explanation: "The state series starts at FY 2010-11; no state-grain data exists before it. The national series covers FY 2006-07 onward — query national_annual_series instead." This refusal confirms that the absence of earlier state-grain figures is a defined boundary of the dataset, not an unrecorded gap.

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

In the flagship's first year of FY 2018-19, 666 districts reported person-days under the rural employment guarantee scheme. Each district's annual person-days figure remains filed under the geography that existed in its own period, and the record never forward-maps a split district's value onto its successors.

By FY 2023-24, the number of reporting districts had risen to 738. The intervening addition of 72 districts reflects boundary reorganisations rather than the creation of new territory. Redistributing an earlier district's person-days across successor jurisdictions would demand an allocation the source never published, which would constitute inventing data.

The record declines to answer requests for district-level data before the flagship era. It states: "The district drill-down starts at FY 2018-19 (the flagship era); no district-level data exists before it. Use the state or national series for earlier years."

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

MGNREGA's governed history is sealed after the scheme's repeal effective 30 June 2026, and the record provides no data on or after 2027-28 because the canonical series ends at FY 2026-27 as a closed historical record: "No data on or after 2027-28: MGNREGA was repealed effective 30 June 2026, so the canonical series ends at FY 2026-27 and this is a closed historical record." The dataset is annual-grain only and does not serve monthly figures such as a 2022-04 district cut, because monthly avg_wage_rate_per_day values are cumulative year-to-date ratios rather than valid monthly rates: "The series is annual-grain only; monthly figures are not served. In particular, monthly avg_wage_rate_per_day values are cumulative year-to-date ratios, not valid monthly rates — the wage rate is published only as the financial-year-final annual value at district-annual grain. Remove 'month' to query the annual series."

The average daily wage rate is not available at the state annual grain, and a request for that metric at state level is declined because the measure resides in the district flagship table: "Metric 'avg_wage_rate_per_day' is not available at this grain; it lives in district_flagship. Call get_schema for a table's metrics." District-level drill-down is unavailable before the flagship era, with the floor set at FY 2018-19, so queries for district data ending at 2015-16 are refused: "The district drill-down starts at FY 2018-19 (the flagship era); no district-level data exists before it. Use the state or national series for earlier years."

A financial year must be expressed exactly as a start year and two-digit suffix, and the label '2019' is rejected rather than silently compared: "Malformed financial year '2019'. Expected exactly 'YYYY-YY', where the two-digit suffix is the start year plus one — e.g. '2018-19' for the year running April 2018 to March 2019." The record will not invent a subdivision for an unknown place, and a state named 'Atlantis' is returned as unknown: "Unknown state 'Atlantis' (give an LGD code or current LGD name)."

Provenance for individual facts is not reachable through the general query verb, and the lineage table is directed to a dedicated function instead: "The lineage table is not queryable via query(); it is per-fact provenance. Use get_lineage(fact_id) instead."

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

The scheme's documented history provides no monthly measurements at any geographic level; all figures are annual aggregates. The underlying source did emit month-columned tables, but those columns represented cumulative year-to-date totals rather than discrete monthly values, and its wage-rate column was a running ratio of funds disbursed to days logged that early in a fiscal year was skewed by arrears from prior-year labor. Consequently, any attempt to extract a monthly figure is declined; the data server states: "The series is annual-grain only; monthly figures are not served. In particular, monthly avg_wage_rate_per_day values are cumulative year-to-date ratios, not valid monthly rates — the wage rate is published only as the financial-year-final annual value at district-annual grain. Remove 'month' to query the annual series." Estimates circulating in other venues that were derived from those monthly columns therefore cannot be reproduced or verified within this record, and they are not repeated here.

The fiscal year 2017-18 marks the transition before the district-level reporting system commences, and it is the least complete year in the archive. In that single year, the record withholds 163 cells of data. Analyses that bridge this seam to later periods should be undertaken with caution because of the missing entries.

Defects from the source series persist into the annual wage-rate figures, where 9 district-year observations exceed Rs 1,000 a day. The highest among them is 3582 INR, recorded for Hooghly, West Bengal, in FY 2023-24. These values are not payments received by any worker; a plausible MGNREGA daily wage lies an order of magnitude below such amounts. They are retained in the record with their provenance flagged rather than expunged, so that a reader may identify and discount them.

Active workers is a metric that appears only from FY 2018-19 onward in the dataset. In its inaugural year at the state grain, the count of such facts is 33. Any comparison of this indicator across the scheme's entire lifespan would therefore set a measured quantity against a span where it was not recorded at all.

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
