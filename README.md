# MGNREGA Canonical Series

[![CI](https://github.com/Prateek718/Data-Platform/actions/workflows/ci.yml/badge.svg)](https://github.com/Prateek718/Data-Platform/actions/workflows/ci.yml)
[![Code License: MIT](https://img.shields.io/badge/Code%20License-MIT-yellow.svg)](LICENSE)
[![Data License: CC BY 4.0](https://img.shields.io/badge/Data%20License-CC%20BY%204.0-lightgrey.svg)](LICENSE-DATA)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/release/python-3120/)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.21318431.svg)](https://doi.org/10.5281/zenodo.21318431)

A definitive, reconciled, lineage-traced record of **MGNREGA** — the Mahatma Gandhi National Rural
Employment Guarantee Act scheme, India's rural employment guarantee — assembled from the many
separately-published government datasets on [data.gov.in](https://data.gov.in) into one canonical
series covering **FY 2006-07 → FY 2026-27**. Where those sources disagree, the disagreement is
adjudicated by a defensible, source-grounded rule or published as a first-class output with full
lineage — never silently smoothed away. MGNREGA was repealed effective 1 July 2026 — replaced by the
Viksit Bharat–Guarantee for Rozgar and Ajeevika Mission (Gramin) Act, 2025, passed by Parliament in
December 2025 — so this is built as a concluded, citable reference record rather than a live feed.

## What you get

Running the export (`PYTHONPATH=src uv run python -m data_platform.export`) produces, under
`dist/v1.0/`:

| File | What it is |
|---|---|
| `state_annual_series.csv` / `.parquet` | 4,219 facts — one value per (state, financial-year, metric), 8 metrics, FY 2010-11 → 2026-27. |
| `national_annual_series.csv` / `.parquet` | 148 facts — one value per (financial-year, metric), FY 2006-07 → 2026-27. |
| `district_flagship.csv` / `.parquet` | 57,181 facts — the flagship district drill-down (2018+), single-grain **district-annual**: the 8 additive metrics (which sum to the state spine) plus `avg_wage_rate_per_day` (a cumulative-YTD ratio, published at its FY-final annual value for complete financial years only). |
| `lineage.jsonl` | 61,548 records — full per-fact provenance keyed by `fact_id`: every source seen, every rejected/superseded value with the rule that decided it, coverage descriptors, flags. |

The CSVs are flat and friendly; the deep provenance lives in `lineage.jsonl`, joined on `fact_id`.
Every column and metric is defined in **[DATA_DICTIONARY.md](DATA_DICTIONARY.md)** — a reader needs
nothing beyond it to use the data.

## Why it's hard

The divergence being reconciled is internal to data.gov.in: the same MGNREGA facts are re-published
across many datasets and departments with conflicting units (lakh vs crore), grains (district vs
state), and year-slices. Turning that into one trustworthy series meant defusing several real traps:

- **Cumulative-YTD, not monthly flows.** The flagship publishes person-days and expenditure as a
  *running year-to-date* total, so the annual figure is the year's final month — never the sum of
  the monthly rows. Summing them over-counts badly (on Goa in FY 2022-23, a naive monthly sum gives
  593,095 person-days against the correct 94,004 — a 6.31× inflation). The pipeline takes the
  financial-year-final and never sums.
- **No code mapping to canonical geography.** The flagship publishes its own internal MIS codes, not
  the government's Local Government Directory (LGD) codes — Goa is `10` in the flagship but `30` in
  LGD, and no crosswalk exists. Every source is resolved to canonical LGD geography by a curated
  name-join; a row that cannot be placed honestly is quarantined with a reason, never forced onto a
  code that does not fit.
- **Apparent conflict was mostly disguised incompleteness.** Much of what looked like cross-source
  disagreement was really *period mismatch* — an edition's mid-year partial terminal year, a
  half-year "upto 30.09" column — or one publisher re-issuing its own table across successive
  Statistical Year Book editions. Separating those out first (edition supersession labels 470 state
  cells; partial periods and partial columns are excluded before comparison) collapsed the apparent
  conflict and *revealed* real agreement: cross-publisher corroboration on households rose from 53 to
  118 cells while flagged household conflicts fell from 69 to 4.
- **The pre-2018 residual is small, and named.** After all of that, **nine** genuine cross-publisher
  material disagreements remain in the pre-2018 series: **four** in `households_employed` (Bihar FY
  2015-16, Mizoram FY 2013-14, Telangana FY 2014-15, Andaman & Nicobar FY 2014-15 — a MoSPI edition
  vs a Rajya Sabha answer, settled by a documented tie-break between equal-authority publishers) and
  **five** in `total_expenditure` (Andhra Pradesh FY 2014-15 & 2015-16, Bihar FY 2014-15, Jammu &
  Kashmir & Telangana FY 2016-17), surfaced once the RS expenditure table made RS an independent
  publisher there. Each records the rejected value and percentage in lineage. (That same wiring also
  produced **137** new cross-publisher *corroborations* pre-2018 — RS independently confirming MoSPI.)
- **The flagship era reconciles too.** Four Rajya Sabha state tables (person-days, total-expenditure,
  100-days) are peers to the flagship rollup, not dropped: across FY 2018-24 that yields **180**
  cross-publisher corroborations, **25** flagged conflicts where the flagship has whole-geography
  coverage (flagship value taken, RS value recorded), and **10** *unadjudicated* cells where a
  structurally-incomplete flagship rollup materially disagrees with the RS peer — value withheld, both
  readings in lineage. Maharashtra's FY2021-24 person-days going null is the honest outcome (flagship
  34/36 districts vs RS +11 to +19.6%), not a number silently chosen.

Edition supersession is a *source-grounded editorial hierarchy*, not "newest file wins": it is
applied to a family only after shared publication identity, dated edition markers, and empirically
(near-)unidirectional restatement are all confirmed — with the single known reversion (a one-lakh
flicker on Sikkim) documented and resolving cleanly. The full account is in
[docs/stage-4-5-series-assembly-summary.md](docs/stage-4-5-series-assembly-summary.md) and
[docs/RULES.md](docs/RULES.md).

## Architecture

```
data.gov.in MGNREGA archive (offline, gitignored under data/archive/)
  → ingest        capture the full archive locally; the portal is not a runtime dependency
  → normalize     reshape to tidy rows; clean dates, types, dedupe
  → resolve       geography → LGD code by name-join; zero-loss gate (resolve OR quarantine-with-reason)
  → harmonize     units (lakh/crore → canonical), cumulative-YTD → FY-final; Stage-4 reconciliation — deterministic rules, divergence a first-class output
  → assemble      Stage-4.5 continuous series across the 2018 seam (flagship 2018+ / historical before)
  → export        this deliverable: flat CSV/Parquet + deep lineage.jsonl
```

Principles enforced throughout: **deterministic only** (no ML/LLM inside the transforms);
**quarantine over discard** (no row and no dataset dropped without a recorded reason — see
[docs/quarantine-report.md](docs/quarantine-report.md)); **null ≠ 0** (a missing value is never
coerced to zero); and **every fact carries its lineage**. MGNREGA is the reference implementation;
the platform is architected scheme-agnostic, and is designed to be served over MCP for AI agents to
query (that serving layer is roadmap, not part of this v1 data release).

## Honest limitations

- FY 2006-07 → 2009-10 exists only in the **national** spine — no state-level source reaches before
  FY 2010-11. The gap is visible, never synthesized.
- `active_workers` is **flagship-era (2018-19 →) only**; no defensible pre-2018 value exists.
- `avg_wage_rate_per_day` is a rate at **district-annual** grain — the flagship's source column is a
  cumulative-YTD ratio (cumulative wages ÷ cumulative person-days, a verified exact identity), so its
  FY-final value is the true annual rate and the mid-year YTD ratios are not published. It does not
  sum to a state or national annual, so it is not in the spines.
- **Scope: the 9 contracted metrics.** The flagship publishes ~35 columns per district-month; the
  ~26 beyond the 9 canonical metrics (SC/ST/Women breakdowns, job-cards, works counts, DBT/payment
  timeliness, labour budget, …) are outside v1 scope — not dropped, but preserved in the deposited
  raw archive for direct use.
- Within FY 2010-11 → 2017-18, coverage is **32–33 of 35** states/UTs per metric-year (a source that
  did not report a state that year is absent, not zero).
- **FY2017-18 is thin.** MoSPI's SYB2018 edition publishes 2017-18 as a mid-year partial, excluded
  rather than published as an annual (R4-REC-11). Where an RS full-year peer exists it fills the year;
  otherwise the cell is withheld — **164 state cells** are `partial-period-only` (value null). These
  nulls are expected to be temporary (deferred RS vintages carry 2017-18 in full — a v1.1 fill).
- **10 flagship-era state cells** are **unadjudicated** (value null): a structurally-incomplete
  flagship rollup materially disagrees with the RS peer — `persondays_generated` (West Bengal
  2019-21, Maharashtra 2021-24, Telangana 2021-22), `total_expenditure` (Madhya Pradesh, Rajasthan
  2018-19), `households_completed_100_days` (West Bengal 2018-19). Both readings are in lineage.
- **22 national cells** (FY 2012-13 → 2015-16, across 7 metrics) remain **unadjudicated** (value
  null): one publisher's national vintages disagree and the edition-supersession check was verified
  only for the state families — extending it to the national tier is a documented, deferred
  follow-up. (The three `persondays_generated` cells are a subset.)
- **Known unharmonized archive overlaps are deferred, not lost** — a few RS state peers (partial
  terminal years, a scale mismatch) are held back with byte-verified machinery/defect reasons,
  listed in [DATA_DICTIONARY.md](DATA_DICTIONARY.md) §8.

The same coverage account, in full, is in [DATA_DICTIONARY.md](DATA_DICTIONARY.md).

## Reproducibility

The pipeline runs **offline** against the local archive and produces the series **byte-for-byte
identically** on every run (the export test suite asserts this for CSV, JSONL, and Parquet). See
**[REPRODUCIBILITY.md](REPRODUCIBILITY.md)** for the exact claim, environment, and how to obtain the
raw archive.

```bash
uv sync                                   # install (pinned via uv.lock)
uv run ruff check . && uv run mypy src tests && uv run pytest   # gate: lint, types, tests
PYTHONPATH=src uv run python -m data_platform.export   # regenerate dist/v1.0/ from data/archive/
```

## How to cite

Citation metadata is in **[CITATION.cff](CITATION.cff)**. The v1.0.0 release is archived on Zenodo —
cite the version DOI [10.5281/zenodo.21318927](https://doi.org/10.5281/zenodo.21318927) for this
specific release, or the concept DOI [10.5281/zenodo.21318431](https://doi.org/10.5281/zenodo.21318431),
which always resolves to the latest version (see [REPRODUCIBILITY.md](REPRODUCIBILITY.md)).

## License

Two-part licensing: the **code** (pipeline, export, tests) is under the **MIT License** (`LICENSE`);
the **derived dataset** in `dist/` is under **CC BY 4.0** (`LICENSE-DATA`) with attribution to the
original Government Open Data License – India (GODL-India) sources on data.gov.in (MoRD, MoSPI, and
Rajya Sabha material). Per-fact source resource ids are recorded in `lineage.jsonl`.

## How this was built

This project was built with an agentic workflow: a human architect/reviewer (the author) set the
data contract, rules, and design decisions and reviewed at checkpoints; Claude Code carried out the
implementation under a strict gate (tests, `ruff`, `mypy --strict`) with review between stages. The
commit history reflects that process directly.
