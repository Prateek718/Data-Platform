# Changelog

Notable changes to the MGNREGA Canonical Series. Format loosely follows
[Keep a Changelog](https://keepachangelog.com/); the version tracks the **dataset** release.

## [1.0.0] — 2026-07-06

First public release: the complete, reconciled MGNREGA canonical series and its public-facing
artifacts.

### Dataset (`dist/v1.0/`)
- **State spine** — 4,216 facts, one value per (state, financial-year, metric), 8 canonical metrics,
  FY 2010-11 → 2026-27, each LGD-anchored and lineage-traced.
- **National spine** — 148 facts, FY 2006-07 → 2026-27 (the only tier reaching back to 2006-07).
- **District drill-down** (`district_flagship`) — 120,724 flagship-era (2018+) facts: 8 additive
  metrics at district-annual grain (they sum to the state spine) plus `avg_wage_rate_per_day` at its
  native district-monthly grain.
- **`lineage.jsonl`** — 125,088 per-fact provenance records keyed by `fact_id`: every source seen,
  every superseded/rejected value with the deciding rule, coverage descriptors, and flags.
- Both CSV and Parquet for every table; deterministic and byte-identical across runs.

### How it was reconciled
- Continuous series across the 2018 seam: flagship (district-monthly, rolled up) for 2018+, wired
  historical sources (MoSPI Statistical Year Book editions, Rajya Sabha answers) before.
- Person-days corrected from cumulative-YTD to financial-year-final (never summed across months).
- Geography resolved to current LGD codes by name-join; unresolvable rows quarantined with a reason,
  not dropped (see `docs/quarantine-report.md`).
- Edition supersession (source-grounded editorial hierarchy) labels 472 state cells; after separating
  period-mismatch and single-publisher re-issues, exactly **4** genuine cross-publisher material
  disagreements remain in the pre-2018 series, each published with its rejected value and lineage.
- `null` is never coerced to `0`; divergence with no groundable adjudication is published unadjudicated.

### Added (tooling & docs)
- `data_platform.export` module + CLI (`python -m data_platform.export`) with hermetic and
  archive-gated tests (row counts, CSV↔lineage join, byte-identity, district→state decomposition).
- `DATA_DICTIONARY.md`, front-door `README.md`, `REPRODUCIBILITY.md`, `LICENSE-PROPOSAL.md`,
  `CITATION.cff`, and this changelog.
- `pyarrow` added (dev/export group) for Parquet output; core runtime deps unchanged.

### Known limitations
- FY 2006-07 → 2009-10: national spine only (no state-level source before FY 2010-11).
- `active_workers`: flagship-era (2018+) only. `avg_wage_rate_per_day`: district-monthly only.
- FY 2010-11 → 2017-18 state coverage is 32–33 of 35 states/UTs per metric-year.
- 3 national `persondays_generated` cells (FY 2012-13/2013-14/2014-15) remain unadjudicated pending
  national edition-supersession (documented, deferred).
- Full account in `DATA_DICTIONARY.md` and `docs/stage-4-5-series-assembly-summary.md`.

### Not in this release (roadmap)
- The MCP serving layer and the autonomous read-only analyst are architected but not part of the v1
  data release.

[1.0.0]: https://github.com/Prateek718/Data-Platform/releases/tag/v1.0.0
