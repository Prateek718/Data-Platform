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
lineage — never silently smoothed away. **MGNREGA's last day in force was 30 June 2026** — the date
the served record itself states — and it stands repealed from 1 July 2026, when the Viksit Bharat –
Guarantee for Rozgar and Ajeevika Mission (Gramin) Act, 2025, passed by Parliament in December 2025,
commenced ([PIB, Government of India](https://www.pib.gov.in/PressReleasePage.aspx?PRID=2259691)).
The successor programme is context from outside this record: the dataset holds no fact about it, and
nothing here depends on it. This is therefore built as a concluded, citable reference record rather
than a live feed.

**Start with the report.** [**`report/report.md`**](report/report.md) is a researcher-grade reading of
the whole record — twenty years, what it shows, where the publishers disagree, and what it refuses to
answer. Every number in it was machine-verified against the served dataset and carries its lineage;
figures that could not be verified were **blocked from printing**, not guessed. It is the best way to
see what this dataset is, in about ten minutes.

| | |
|---|---|
| **The reading** | [`report/report.md`](report/report.md) — the record, in prose, with charts |
| **The data** | the [v1.0.0 release](https://github.com/Prateek718/Data-Platform/releases/tag/v1.0.0) (`dist/` is gitignored — [fetch it](#serve-the-record)) |
| **The citation** | DOI [10.5281/zenodo.21318927](https://doi.org/10.5281/zenodo.21318927) (this release) |
| **Every field, defined** | [DATA_DICTIONARY.md](DATA_DICTIONARY.md) |

## What you get

Running the export (`data-platform-export`) produces, under
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

## Serve the record

A read-only [MCP](https://modelcontextprotocol.io) server exposes this release to AI agents as a
governed query surface. It serves the **checksum-verified v1.0.0 release artifacts** only: at
startup it verifies every file in `dist/v1.0/` against a committed SHA-256 manifest (itself derived
from the published release zip) and **refuses to start** on any mismatch or missing file. It loads
them into an in-memory DuckDB, opens no network connection, and exposes no mutation verb — the
record is sealed (MGNREGA was repealed 30 June 2026).

**A fresh clone has no data.** `dist/` is gitignored: the dataset lives in the
[v1.0.0 release](https://github.com/Prateek718/Data-Platform/releases/tag/v1.0.0). Fetch it once —
the download is verified against the SHA-256 the release published, then the seven extracted files
are verified against the manifest the server itself enforces at startup, and the install is
atomic (a failure leaves no half-populated `dist/`, and never damages one that already works):

```bash
uv sync                    # installs the project + its console commands
data-platform-bootstrap    # ~5 MB; downloads, verifies twice, installs to dist/v1.0
data-platform-mcp          # the server, over stdio
```

Claude Desktop config (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "mgnrega-canonical-series": {
      "command": "uv",
      "args": ["run", "data-platform-mcp"],
      "cwd": "/path/to/Data-Platform"
    }
  }
}
```

### Or run it as a container

The server is a stdio MCP server, and a container does not change that: `docker run -i` connects the
client's pipes straight to the process's, so a client spawns the container exactly as it would spawn
the local command. No port is opened and no HTTP transport is added.

```bash
docker build -t data-platform .
docker run -i --rm -v dp-dataset:/data data-platform     # fetches + verifies the dataset on first run
```

The dataset is **not baked into the image**: it is fetched into the mounted volume at container
start and verified twice on the way in, so an image can never carry an unverified dataset. For an
offline image, bake it: `docker build --build-arg BAKE_DATASET=1 -t data-platform .`

Claude Desktop, against the container:

```json
{
  "mcpServers": {
    "mgnrega-canonical-series": {
      "command": "docker",
      "args": ["run", "-i", "--rm", "-v", "dp-dataset:/data", "data-platform"]
    }
  }
}
```

`docker compose` wires the same thing with a named volume — `docker compose run --rm -T mcp` for the
server, and the analyst as a one-shot job that takes its API key from the environment (never from
the image):

```bash
OPENROUTER_API_KEY=... docker compose run --rm analyst
```

**Tools:**

| Tool | What it does |
|---|---|
| `list_datasets` | The three data tables + lineage, each with row count, financial-year coverage window, grain, and metric list. |
| `get_schema(table)` | Columns and types, per-metric unit and unit-class, grain, join key (`fact_id`), and null semantics. |
| `query(table, metrics?, states?, districts?, fy_from?, fy_to?)` | Constrained filter (no raw SQL; parameters only). Geography by LGD code or current LGD name. Returns rows carrying `fact_id` in a result envelope, or a structured refusal. |
| `get_lineage(fact_id \| [fact_id])` | Full provenance per fact: each source with resource id and as-of date, reconciliation status, rejected value, materiality, and null reason. |
| `request_refresh` | Reports that the record is sealed and cannot be refreshed, with the citation pointer. |

### Three queries, including one the record refuses

**1. Read a figure.** `query` returns rows in an envelope, each carrying the `fact_id` that unlocks
its provenance:

```jsonc
query(table="national_annual_series", metrics=["persondays_generated"],
      fy_from="2020-21", fy_to="2020-21")
→ { "financial_year": "2020-21", "metric": "persondays_generated",
    "value": 3881318918.0, "unit": "person-days",
    "era_basis": "flagship-rollup", "confidence": "single-source",
    "fact_id": "5dbb027fdfca056a" }
```

**2. Ask where a number came from — including what was rejected.** This is the point of the whole
project: a contested cell shows both publishers, the value the record took, the value it rejected,
the rule that decided, and how far apart they were.

```jsonc
get_lineage("744999f0f06a48a9")   // Telangana total expenditure, FY 2016-17
→ { "value": "210898.07", "unit": "INR lakh",
    "reconciliation_status": "flagged conflict", "resolution_rule_id": "R4-REC-02",
    "sources":  [ { "source_id": "SRC_MOSPI", "value": "257475.31", "as_of": null },
                  { "source_id": "SRC_RS",    "value": "210898.07", "as_of": "2021-03-23" } ],
    "rejected": [ { "source_id": "SRC_MOSPI", "value": "257475.31" } ],
    "materiality": { "absolute": "46577.24", "relative_pct": "22.09", "material": true } }
```

**3. Ask for something the record cannot honestly answer.** It refuses, and says why — a refusal is
a first-class result, never an empty table:

```jsonc
query(table="district_flagship", metrics=["avg_wage_rate_per_day"], month="2022-04")
→ { "refused": true, "code": "monthly_wage_unavailable",
    "reason": "The series is annual-grain only; monthly figures are not served. In particular,
               monthly avg_wage_rate_per_day values are cumulative year-to-date ratios, not valid
               monthly rates — the wage rate is published only as the financial-year-final annual
               value at district-annual grain. Remove 'month' to query the annual series." }
```

The record refuses a period after FY 2026-27 (it is sealed), any monthly figure (the series is
annual-only), a coverage-floor miss, an unknown metric or geography, and a malformed financial-year
label. **A refusal is not a null.** A null *data cell* is returned as data, carrying the reason it is
empty — the record distinguishes "I will not answer that" from "the value is unknown, and here is
why".

## The analyst and its report

[`report/report.md`](report/report.md) is a researcher-grade document — abstract, introduction,
methodology, findings, limitations — written by an AI analyst that can only see this dataset through
the MCP server above. It has no other access to the data, and no ability to compute.
[`report/report.json`](report/report.json) is the same report as a structured artifact: every figure
is a typed object carrying its value, unit, metric, geography, period, `fact_id`, the exact query
that produced it, and its **full lineage payload** (each source, its data.gov.in resource id, and
its as-of date), captured at generation time from the checksum-verified release artifacts.

The [charts](report/charts) are drawn by code from `report.json` — never from the dataset — so a
chart cannot plot a number the report did not verify, and each one's manifest entry names the exact
figure ids behind every point. Two consequences of that discipline are visible in them: the
person-days line **breaks** across FY 2012-13 to 2014-15 rather than interpolating over three years
the record withholds, and FY 2026-27 (which holds April 2026 alone) is **omitted** from every chart
rather than drawn as a collapse that never happened. Both are stated in the captions and reported in
the prose.

**How the no-bluffing guarantee works.** The model writes prose; it never chooses a number. The
pipeline around it is deterministic:

1. **Retrieve** — code queries the server for each figure a section needs and pulls its lineage in
   the same breath. A figure with no provenance never reaches the model.
2. **Derive** — ratios, sums and differences are computed *by code* in exact decimal, over input
   facts listed by id. Counts ("193 null cells") record every member `fact_id` and a named,
   replayable filter.
3. **Draft** — the model is handed those figures and *nothing else*, and told every number it writes
   must be one of them, copied exactly.
4. **Verify** — deterministic, no model involved. Every number in the prose must be a declared
   figure or derivation, spelled exactly as served: **undeclared rounding is rejected** ("roughly
   1.0 million" is not `1,000,000`; readable forms like "3.88 billion" are *declared* derivations
   the verifier recomputes). Every derivation is recomputed from its declared inputs. Every backing
   query is re-executed against the served data. A figure without a lineage reference blocks the
   section. And a long span in quotation marks must be **verbatim** — the model may paraphrase the
   server, but not inside quotes: a reworded "quotation" is a forgery even when every number in it
   is right.
5. **Loop or fail** — a section that fails goes back to the model with the verifier's complaints
   attached, and after a bounded number of attempts the run **fails loudly and writes nothing**. A
   model that bluffs produces no report, never a wrong one.

Any figure's trace can be re-derived independently — run the MCP server and call
`get_lineage(fact_id)`. Because the record is sealed, a live lookup cannot return anything different
from the embedded copy.

**Regenerating it** needs any OpenAI-compatible chat-completions endpoint — there is no dependency
on a specific vendor, and no Anthropic account is required:

```bash
export OPENROUTER_API_KEY=...                                  # required
export OPENROUTER_MODEL=tencent/hy3:free                       # optional; free-model ids churn
export OPENROUTER_BASE_URL=https://openrouter.ai/api/v1        # optional; any compatible endpoint
export OPENROUTER_MAX_TOKENS=12000                             # optional; reasoning models need headroom

data-platform-analyst                                          # writes report/report.{json,md}
```

This is the only path in the repo that calls a live model. The test suite never does: it drives the
graph with scripted fakes — including one that lies about a number, to prove the verifier blocks it.

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

Principles enforced throughout: **deterministic only** (no ML/LLM inside the transforms — the only
model in the system writes the report's prose, and cannot choose a number); **quarantine over
discard** (no row and no dataset dropped without a recorded reason); **null ≠ 0** (a missing value is
never coerced to zero); and **every fact carries its lineage**. MGNREGA is the reference
implementation; the platform is architected scheme-agnostic.

**Where the reasoning lives.** Nothing below is summarized here — these are the documents that decide
things, and they are the ones to read if you want to argue with a rule:

| Document | What it settles |
|---|---|
| [docs/DATA_CONTRACT.md](docs/DATA_CONTRACT.md) | The canonical schema, the geography anchor (LGD), source priority, and the lineage every fact must carry. |
| [docs/RULES.md](docs/RULES.md) | Every named rule, by id: normalization (R2), entity resolution (R3), harmonization and reconciliation (R4), serving (R7). A rule id in `lineage.jsonl` resolves here. |
| [DATA_DICTIONARY.md](DATA_DICTIONARY.md) | Every column and metric, unit, null semantics, and the full coverage account. |
| [REPRODUCIBILITY.md](REPRODUCIBILITY.md) | The byte-for-byte claim, the environment, and how to get the raw archive. |
| [docs/BUILD_SEQUENCE.md](docs/BUILD_SEQUENCE.md) | The twelve stages and what delivered each. |
| [docs/stage-4-5-series-assembly-summary.md](docs/stage-4-5-series-assembly-summary.md) | How the continuous series was assembled across the 2018 seam, with the divergence accounting. |
| [docs/quarantine-report.md](docs/quarantine-report.md) | What was quarantined, and why — nothing is dropped silently. |
| [docs/notes/](docs/notes/) | The working record: source reconnaissance, divergence findings, the Stage 8 claim inventory and fork facts. |

## Scope, coverage and caveats

Read this before you use a number. The full statement, with every figure verified against the served
data, is the **[Limitations section of the report](report/report.md)**; this is the summary.

**Scope boundaries — what the record is, and is not.**

- **Annual grain, at every level.** The sources publish month-by-month columns, but those columns are
  cumulative *year-to-date* running totals, not monthly figures. The record therefore publishes annual
  values only, and the server **refuses** monthly questions rather than serving a number that looks
  monthly and is not.
- **The state series starts at FY 2010-11**; FY 2006-07 → 2009-10 exists only in the **national**
  spine, because no state-level source reaches further back. The gap is visible, never synthesized.
- **The district drill-down starts at FY 2018-19** — the flagship MIS era. Nothing below state grain
  exists before it.
- **The expenditure series starts later than the work series**: there are no national
  `total_expenditure` values for FY 2006-07 or FY 2007-08. That is an absence of source data, not a
  withheld value.
- **FY 2026-27 is a stub, not a year.** MGNREGA was repealed effective 30 June 2026 and the record
  carries April 2026 alone, so that year's figures are not comparable to a full one. The last
  **complete** financial year is 2025-26.
- **Nine contracted metrics.** The flagship publishes ~35 columns per district-month; the ~26 beyond
  the 9 canonical metrics (SC/ST/Women breakdowns, job-cards, works counts, DBT/payment timeliness,
  labour budget, …) are outside v1 scope — not dropped, but preserved in the deposited raw archive.

**Data caveats — where the record is uncertain, and says so.**

- **Two kinds of publisher disagreement, counted separately.** Never as one number. Pre-2018, **9**
  state-year cells where two archived publishers of comparable standing (MoSPI and Rajya Sabha
  answers) materially disagree: reconciliation *adjudicates* a canonical value and keeps the rejected
  value, its publisher and the gap in lineage. Flagship-era, **25** cells where the primary district
  MIS diverges from figures tabled in Parliament: authority decides — the primary system stands and
  the divergence is *recorded* as a flagged note, not adjudicated between peers. Both sets cleared the
  same two-part materiality floor (absolute **and** relative), so rounding noise is never reported as
  a conflict.
- **193 null cells, each carrying its reason** — and a null is never a zero. At state grain: **164**
  withheld as `partial-period-only` (the only reading was a mid-year partial) and **10** as
  `unadjudicated` (a structurally-incomplete aggregate materially disagrees with a whole-geography
  peer). At national grain: **19** withheld as `single-publisher divergence` (one publisher's own
  vintages disagree with no defensible order between them).
- **The FY 2017-18 seam.** 163 of the 164 `partial-period-only` nulls fall in that single year — the
  year *before* the flagship MIS begins, where the record's two sourcing eras meet. It is the record's
  weakest year, and comparisons that straddle it should be made with care.
- **Wage-rate artifacts survive into the annual figures.** `avg_wage_rate_per_day` is served only at
  **district-annual** grain, only for a *complete* financial year (so FY 2026-27 has none), and never
  by the month — the source column is a cumulative-YTD ratio, distorted early in a year by arrears
  paid for the previous year's work. Even at FY-final, **9 of 5,645** district-year rates exceed
  ₹1,000/day (highest: ₹3,582, Hooghly, FY 2023-24). **These are not wages anyone was paid** — a
  plausible MGNREGA daily wage is an order of magnitude lower. They are defects of the source series,
  carried into the record with their provenance rather than quietly deleted, so a reader can see and
  discount them. The rate is not additive: it does not sum to a state or national figure, and the
  server refuses it at state grain.
- **`active_workers` has a bounded span**: FY 2018-19 onward only. Comparing it across the full twenty
  years would compare a metric against its own absence.
- **Coverage within FY 2010-11 → 2016-17 is 31–33 of the 35 states/UTs** per metric-year (FY 2017-18,
  29–32). A source that did not report a state in a year is *absent*, not zero.
- **Known unharmonized archive overlaps are deferred, not lost** — a few Rajya Sabha state peers
  (partial terminal years, a scale mismatch) are held back with byte-verified reasons, listed in
  [DATA_DICTIONARY.md](DATA_DICTIONARY.md) §8.

The same account, per column and per metric, is in **[DATA_DICTIONARY.md](DATA_DICTIONARY.md)**.

## Reproducibility

The pipeline runs **offline** against the local archive and produces the series **byte-for-byte
identically** on every run (the export test suite asserts this for CSV, JSONL, and Parquet). See
**[REPRODUCIBILITY.md](REPRODUCIBILITY.md)** for the exact claim, environment, and how to obtain the
raw archive.

```bash
uv sync                                   # install (pinned via uv.lock)
uv run ruff check . && uv run mypy src tests && uv run pytest   # gate: lint, types, tests
data-platform-export                      # regenerate dist/v1.0/ from data/archive/
```

*(The reproduce line inside [report/report.md](report/report.md) still shows the older
`PYTHONPATH=src uv run python -m data_platform.analyst` form. That is not an oversight: the report is
a **generated, verified artifact** of the sealed v1.0 dataset, and editing its text by hand would
break the guarantee that every word of it came out of a checked pipeline. Both commands do the same
thing; the packaged one is the current form.)*

## Future work

Deferred items are documented where they were deferred, so they stay findable:

- **v1.1 data fills.** The FY 2017-18 `partial-period-only` nulls are expected to be temporary
  (deferred Rajya Sabha vintages carry 2017-18 in full); extending the edition-supersession check to
  the **national** tier would resolve the 19 national nulls. See
  [DATA_DICTIONARY.md](DATA_DICTIONARY.md) and [docs/RULES.md](docs/RULES.md).
- **A discrete-monthly wage rate** (Δwages ÷ Δperson-days between consecutive months) needs a
  payment-timing/arrears rule before it can be published honestly — deferred with its reasoning in
  [docs/notes/sources.md](docs/notes/sources.md) (OQ-OGD-4).
- **Packaging hardening.** The container runs the bootstrap at start and fetches over the network;
  an air-gapped deployment should use `--build-arg BAKE_DATASET=1`. The image is ~860 MB because the
  serving path and the report-generating path share one dependency set — splitting the analyst's
  dependencies (LangGraph, the LLM client) out of the server's would make a lean serving image, and
  is a dependency-graph change, not a Dockerfile tweak.
- **The report's own open questions** are stated in its
  [Limitations section](report/report.md), and the claims the served data could **not** back are
  recorded as verification-FAILED — not quietly dropped — in
  [docs/notes/STAGE8-CLAIM-INVENTORY.md](docs/notes/STAGE8-CLAIM-INVENTORY.md).

## Authors

- **Prateek** — architect and reviewer: the data contract, the rules, the design decisions, and the
  review gate between every stage. Author of record for the citable dataset
  ([CITATION.cff](CITATION.cff)).
- **Claude Code** (Anthropic) — implementation, under that direction and behind the project's test,
  lint and type gates. See [How this was built](#how-this-was-built) for the division of labour.

The tool, cited in the standard form for a language-model tool:

> Anthropic. (2026). *Claude Code* (Claude Opus 4.8) [Large language model]. https://claude.com/claude-code

## How to cite

Citation metadata is in **[CITATION.cff](CITATION.cff)**. The v1.0.0 release is archived on Zenodo —
cite the version DOI [10.5281/zenodo.21318927](https://doi.org/10.5281/zenodo.21318927) for this
specific release, or the concept DOI [10.5281/zenodo.21318431](https://doi.org/10.5281/zenodo.21318431),
which always resolves to the latest version (see [REPRODUCIBILITY.md](REPRODUCIBILITY.md)).

**The dataset** (what a researcher cites for the figures):

> Prateek (2026). *MGNREGA Canonical Series* (v1.0.0) [Data set]. Zenodo. https://doi.org/10.5281/zenodo.21318927

**The report** (what they cite for the reading of them) carries its own citation block, generated
with it — see [report/report.md](report/report.md).

## License

Two-part licensing: the **code** (pipeline, export, tests) is under the **MIT License** (`LICENSE`);
the **derived dataset** in `dist/` is under **CC BY 4.0** (`LICENSE-DATA`) with attribution to the
original Government Open Data License – India (GODL-India) sources on data.gov.in (MoRD, MoSPI, and
Rajya Sabha material). Per-fact source resource ids are recorded in `lineage.jsonl`.

## How this was built

This is an agentic build, and it is worth being precise about who did what. A human
architect/reviewer (the author) set the data contract, the rules, and the design decisions, and
reviewed at a gate between every stage — reading actual artifacts (a claim inventory, a pilot
section, a rendered chart, a diff), not summaries, and sending work back when a claim outran its
evidence. Claude Code wrote the implementation under that direction, test-first, behind a strict gate
(`pytest`, `ruff`, `mypy --strict`) that every commit had to pass. The commit history records the
process directly, including the reversals.

Neither party gets to claim the other's work. The code was written by the tool, not typed by the
human; the decisions that shaped it — what counts as a defensible reconciliation rule, which claims
were allowed to ship, what to do when sources disagree — were made by the human, and several of the
most important corrections in the project came from a human reading generated output closely enough
to catch prose that outran its numbers. That division is also why the report has a deterministic
verifier rather than a careful prompt: a review gate catches what it reads, and the verifier catches
what nobody reads. The model writes the report's prose and never chooses a number.
