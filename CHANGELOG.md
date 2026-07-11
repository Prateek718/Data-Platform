# Changelog

Notable changes to the MGNREGA Canonical Series. Format loosely follows
[Keep a Changelog](https://keepachangelog.com/); the version tracks the **dataset** release.

## [1.0.0] — 2026-07-06

First public release: the complete, reconciled MGNREGA canonical series and its public-facing
artifacts.

### Dataset (`dist/v1.0/`)
- **State spine** — 4,219 facts, one value per (state, financial-year, metric), 8 canonical metrics,
  FY 2010-11 → 2026-27, each LGD-anchored and lineage-traced.
- **National spine** — 148 facts, FY 2006-07 → 2026-27 (the only tier reaching back to 2006-07).
- **District drill-down** (`district_flagship`) — 57,724 flagship-era (2018+) facts, single-grain
  district-annual: 8 additive metrics (they sum to the state spine) plus `avg_wage_rate_per_day`
  (a cumulative-YTD ratio, published at its FY-final annual value — see below).
- **`lineage.jsonl`** — 62,091 per-fact provenance records keyed by `fact_id`: every source seen,
  every superseded/rejected value with the deciding rule, coverage descriptors, and flags.
- Both CSV and Parquet for every table; deterministic and byte-identical across runs.

### How it was reconciled
- Continuous series across the 2018 seam: flagship (district-monthly, rolled up) for 2018+, wired
  historical sources (MoSPI Statistical Year Book editions, Rajya Sabha answers) before.
- Person-days corrected from cumulative-YTD to financial-year-final (never summed across months). The
  `avg_wage_rate_per_day` column, verified to be a cumulative-YTD ratio (cumulative wages ÷ cumulative
  person-days, an exact identity across the flagship), is likewise taken at its FY-final annual value;
  its mid-year year-to-date ratios (April can read ₹18,623/day) are not published as monthly rates.
- Geography resolved to current LGD codes by name-join; unresolvable rows quarantined with a reason,
  not dropped (see `docs/quarantine-report.md`).
- Edition supersession (source-grounded editorial hierarchy) labels 470 state cells; after separating
  period-mismatch and single-publisher re-issues, **9** genuine cross-publisher material disagreements
  remain in the pre-2018 series — 4 in `households_employed`, 5 in `total_expenditure` (surfaced once
  the RS expenditure table made RS an independent publisher) — each published with its rejected value.
- Flagship-era reconciliation against four Rajya Sabha state peers (person-days, total-expenditure,
  100-days): **180** cross-publisher corroborations, **25** flagged conflicts (whole-geography
  flagship value taken), and **10** unadjudicated cells where a structural-gap flagship rollup
  materially disagrees — value withheld, both readings in lineage.
- Amended R4-REC-11: MoSPI's SYB2018 edition publishes FY2017-18 as a documented mid-year partial;
  it is now excluded even with no superseding edition — filled by an RS full-year peer where one
  exists, else withheld (164 `partial-period-only` state cells, value null). A single two-floor
  materiality standard (1% relative + a unit-scaled absolute floor) governs counts and money alike.
- `null` is never coerced to `0`; divergence with no groundable adjudication is published unadjudicated.

### Added (tooling & docs)
- `data_platform.export` module + CLI (`python -m data_platform.export`) with hermetic and
  archive-gated tests (row counts, CSV↔lineage join, byte-identity, district→state decomposition).
- `DATA_DICTIONARY.md`, front-door `README.md`, `REPRODUCIBILITY.md`, `LICENSE-PROPOSAL.md`,
  `CITATION.cff`, and this changelog.
- `pyarrow` added (dev/export group) for Parquet output; core runtime deps unchanged.

### Known limitations
- FY 2006-07 → 2009-10: national spine only (no state-level source before FY 2010-11).
- `active_workers`: flagship-era (2018+) only. `avg_wage_rate_per_day`: district-annual only (a rate;
  not in the state/national spines).
- FY 2010-11 → 2017-18 state coverage is 32–33 of 35 states/UTs per metric-year.
- FY2017-18 is thin: MoSPI's SYB2018 mid-year partial is withheld where no full-year peer exists —
  164 `partial-period-only` state cells (value null); expected temporary (v1.1 fill).
- 10 flagship-era state cells are unadjudicated (structural-gap flagship vs a materially-disagreeing
  RS peer, value null): persondays (WB, Maharashtra, Telangana), total_expenditure (MP, Rajasthan),
  households_completed_100_days (WB).
- 22 national cells (FY 2012-13 → 2015-16, 7 metrics) remain unadjudicated pending national
  edition-supersession (documented, deferred); the 3 `persondays_generated` cells are a subset.
- A few RS state peers remain deferred for machinery/defect reasons (partial terminal years, a scale
  mismatch), listed in `DATA_DICTIONARY.md` §8 — never silently dropped.
- Full account in `DATA_DICTIONARY.md` and `docs/stage-4-5-series-assembly-summary.md`.

### Not in this release (roadmap)
- The MCP serving layer and the autonomous read-only analyst are architected but not part of the v1
  data release.

[1.0.0]: https://github.com/Prateek718/Data-Platform/releases/tag/v1.0.0
