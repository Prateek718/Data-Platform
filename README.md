# MGNREGA Canonical Series

A definitive, reconciled, lineage-traced record of **MGNREGA** — the Mahatma Gandhi National Rural
Employment Guarantee Act scheme, India's rural employment guarantee — assembled from the many
separately-published government datasets on [data.gov.in](https://data.gov.in) into one canonical
series covering **FY 2006-07 → FY 2026-27**. Where those sources disagree, the disagreement is
adjudicated by a defensible, source-grounded rule or published as a first-class output with full
lineage — never silently smoothed away. MGNREGA was repealed effective 1 July 2026 — replaced by the
Viksit Bharat–Guarantee for Rozgar and Ajeevika Mission (Gramin) Act, 2025, passed by Parliament in
December 2025 — so this is built as a concluded, citable reference record rather than a live feed.

## What you get

Running the export (`uv run python -m data_platform.export`) produces, under `dist/v1.0/`:

| File | What it is |
|---|---|
| `state_annual_series.csv` / `.parquet` | 4,216 facts — one value per (state, financial-year, metric), 8 metrics, FY 2010-11 → 2026-27. |
| `national_annual_series.csv` / `.parquet` | 148 facts — one value per (financial-year, metric), FY 2006-07 → 2026-27. |
| `district_flagship.csv` / `.parquet` | 120,724 facts — the flagship district drill-down (2018+): additive metrics at district-annual grain, plus `avg_wage_rate_per_day` at its native district-monthly grain. |
| `lineage.jsonl` | 125,088 records — full per-fact provenance keyed by `fact_id`: every source seen, every rejected/superseded value with the rule that decided it, coverage descriptors, flags. |

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
  Statistical Year Book editions. Separating those out first (edition supersession labels 472 state
  cells; partial periods and partial columns are excluded before comparison) collapsed the apparent
  conflict and *revealed* real agreement: cross-publisher corroboration on households rose from 53 to
  118 cells while flagged household conflicts fell from 69 to 4.
- **The honest residual is small, and named.** After all of that, exactly **four** genuine
  cross-publisher material disagreements remain in the whole pre-2018 series — all in
  `households_employed` (Bihar FY 2015-16, Mizoram FY 2013-14, Telangana FY 2014-15, Andaman &
  Nicobar FY 2014-15), each between a MoSPI edition and a Rajya Sabha answer of equal authority.
  Because no authority ordering separates them, a documented deterministic tie-break (the more
  recent source vintage) selects the displayed value; the rejected value and the percentage are
  recorded in lineage.

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
- `avg_wage_rate_per_day` is a rate, kept at its native **district-monthly** grain only — it does
  not sum to a state or national annual, so it is not in the spines.
- Within FY 2010-11 → 2017-18, coverage is **32–33 of 35** states/UTs per metric-year (a source that
  did not report a state that year is absent, not zero).
- **Three national `persondays_generated` cells** (FY 2012-13, 2013-14, 2014-15) remain
  **unadjudicated** (value null): one publisher's national vintages disagree and the
  edition-supersession check was verified only for the state families — extending it to the national
  tier is a documented, deferred follow-up.

The same coverage account, in full, is in [DATA_DICTIONARY.md](DATA_DICTIONARY.md).

## Reproducibility

The pipeline runs **offline** against the local archive and produces the series **byte-for-byte
identically** on every run (the export test suite asserts this for CSV, JSONL, and Parquet). See
**[REPRODUCIBILITY.md](REPRODUCIBILITY.md)** for the exact claim, environment, and how to obtain the
raw archive.

```bash
uv sync                                   # install (pinned via uv.lock)
uv run ruff check . && uv run mypy src tests && uv run pytest   # gate: lint, types, tests
uv run python -m data_platform.export     # regenerate dist/v1.0/ from data/archive/
```

## How to cite

Citation metadata is in **[CITATION.cff](CITATION.cff)**. A DOI is minted on release via Zenodo (see
[REPRODUCIBILITY.md](REPRODUCIBILITY.md)); cite that DOI for a specific version.

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
