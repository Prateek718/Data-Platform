# SPEC — Stage 0 (Data Fetch + Divergence Check) & Stage 1 (Ingestion)

> **STATUS: HISTORICAL (Stages 0–1 complete).** The source taxonomy in this spec
> (`SRC_OGD / SRC_SYNC / SRC_MIS`) predates the current `SRC_FLAGSHIP / SRC_RS / SRC_MOSPI`
> model; SYNC/MIS were evaluated and **excluded** (DATA_CONTRACT §5). Actual scope is the **full
> MGNREGA archive on data.gov.in**, captured **offline under `data/archive/`** (FY 2006–07 →
> 2026–27), processed toward one canonical series. T1.4's "run fully offline against fixtures, no
> network" requirement is what the project actually does; live fetch is a separate explicit mode.
> Retained as the historical Stage 0–1 plan.
>
> Project: Data Platform. Authoritative refs: `docs/DATA_CONTRACT.md`, `docs/RULES.md`.
> Read both before starting. Do NOT invent schema, rules, or canonical fields — they live there.
> Workflow: for each stage, enter plan mode, write the task plan to `tasks/stageN-todo.md`,
> check in (this is a human review gate), then implement task-by-task with TDD where noted.
> If any required detail is missing or ambiguous, STOP and write it as an Open Question — do not guess.

---

## STAGE 0 — Data Fetch + Divergence Verification

**Purpose:** Pull real MGNREGA data from the three sources and PROVE the reconciliation story
is real before building any machinery. This stage is throwaway-ish exploration that produces
two durable artifacts: raw sample data on disk, and a written divergence finding.

### Context you need
- Sources (see DATA_CONTRACT §3): SRC_OGD (data.gov.in, official CSV/JSON/API),
  SRC_SYNC (third-party sync e.g. DeshSeva/dataful), SRC_MIS (nrega.nic.in MIS, JS-rendered).
- Build sequencing: OGD → SYNC → MIS (easiest first). For STAGE 0 the priority is OGD + SYNC
  (the two cleanest pulls) to get the divergence check done fast; attempt MIS but it's allowed
  to be the hard/partial one here.
- Starter metrics only (DATA_CONTRACT §2.3 LOCKED): persondays_generated,
  avg_wage_rate_per_day, total_expenditure. Geography grain: district. Temporal grain: monthly.

### Tasks
**T0.1 — Source reconnaissance (no code yet, write findings to `docs/notes/sources.md`)**
- For each of OGD, SYNC, MIS: identify the exact URL(s)/endpoint(s) that expose the starter
  metrics at district + monthly grain, the format (CSV/JSON/HTML), and whether auth is needed
  (none should be). Record actual field names as they appear in each source (raw, verbatim).
- Acceptance: `docs/notes/sources.md` lists, per source, the access URL, format, raw field
  names for the 3 starter metrics, and the geography/period fields. Note any source that does
  NOT expose monthly/district grain (a real finding — flag it, don't paper over it).

**T0.2 — Fetch raw samples to disk**
- Write a small fetch script per source that pulls a bounded sample (e.g. one state, a few
  districts, a few months — enough to compare, not the whole dataset). Save raw, unmodified,
  to `data/raw/<source_id>/...` with the fetch timestamp.
- Acceptance: raw sample files exist on disk for OGD and SYNC at minimum; MIS attempted (if
  MIS fetch is blocked by JS-rendering, document the blocker in sources.md and move on —
  do NOT spend more than a bounded effort here; MIS adapter is sequenced last anyway).

**T0.3 — THE DIVERGENCE CHECK (the point of Stage 0)**
- Pick the SAME (state, district, month, metric) present in ≥2 sources. Compare the values.
- Produce `docs/notes/divergence-findings.md` recording: the chosen keys, each source's value,
  whether they agree/differ, by how much (% and absolute), and each source's own as-of/sync date.
- Also record any STRUCTURAL divergence observed: district-name spelling differences, district
  presence/absence across sources, scheme-name variants (NREGA/MGNREGA/etc.).
- Acceptance: divergence-findings.md exists and states a clear verdict: "sources diverge on
  values: YES/NO" and "sources diverge structurally: YES/NO" with evidence for each.

### STAGE 0 REVIEW GATE — STOP HERE
Report back (via Prateek) before Stage 1:
- The divergence verdict (value-level and structural).
- The real field names per source (these feed Stage 2 mapping).
- Any source that couldn't deliver district/monthly grain.
**Do not begin Stage 1 until this is reviewed.** If divergence is NO on values but YES on
structure, that's fine and expected — proceed; the structural mess justifies the pipeline.
If divergence is NO on BOTH, STOP and surface it — that's a project-level finding.

---

## STAGE 1 — Ingestion (drift-aware, lineage breadcrumbs)

**Purpose:** Reliably pull each source into a raw landing zone, recording provenance breadcrumbs.
NOT normalization, NOT resolution — just get raw data in, tagged with where/when/what-version.

### Design constraints (from CLAUDE.md TIER 1)
- Deterministic, no LLM calls. `null` for missing values, never 0.
- Every ingested batch is tagged (this is the first half of the lineage chain in DATA_CONTRACT §4).
- Pure-ish: fetch has side effects (network/disk) but parsing into records must be unit-testable.

### Tasks
**T1.1 — Define the raw landing record (TDD)**
- A Pydantic model for a raw ingested batch carrying: `source_id`, `ingested_at`,
  `schema_version` (a hash or detected version of the incoming schema), `source_as_of`
  (the source's own date if available), and the raw rows (un-normalized).
- Write tests FIRST: a well-formed sample parses; a malformed row is captured as a typed
  parse-failure (not silently dropped, not crashing the batch). Confirm tests fail, commit
  failing tests, then implement until green. Do not modify tests to pass.
- Acceptance: model + passing tests; malformed rows are quarantined-at-ingestion with reason,
  good rows pass through.

**T1.2 — Source adapters (one per source, sequenced OGD → SYNC → MIS)**
- Each adapter: fetch (or read from `data/raw/` for offline/test runs) → emit raw landing
  records. Adapters share an interface so a new source is an added adapter, not a rewrite
  (this is the scheme/source-agnostic claim — keep the interface clean).
- OGD and SYNC adapters must work end-to-end. MIS adapter: implement the interface; if live
  JS-rendered fetch is impractical, support reading a manually-saved MIS export from disk and
  document that as a known limitation (honest scope note, not a hidden gap).
- Acceptance: OGD + SYNC adapters ingest the Stage 0 samples into raw landing records with
  full breadcrumbs; MIS adapter exists and ingests at least a saved sample.

**T1.3 — Schema-version / drift detection (TDD)**
- On ingest, detect the incoming schema (column set/shape) and assign `schema_version`. If an
  incoming batch's schema differs from the last seen for that source, flag it (drift detected)
  — do not silently accept. (Full drift-handling is Stage 2; here we only DETECT and TAG.)
- Tests FIRST: same schema → same version; changed schema (added/renamed/removed column) →
  drift flagged. Confirm fail, commit, implement to green.
- Acceptance: drift detection tests pass; a deliberately altered sample triggers the flag.

**T1.4 — Offline/test mode**
- Ingestion must run fully offline against `data/raw/` fixtures (no network) so tests and CI
  are hermetic. Live fetch is a separate explicit mode.
- Acceptance: `uv run pytest` passes with no network access.

### STAGE 1 REVIEW GATE — STOP HERE
Report back (via Prateek):
- The raw landing record model and the breadcrumb fields actually populated.
- Which adapters work live vs. from-disk (esp. MIS).
- Drift-detection demo: show a normal ingest and a drift-flagged ingest.
- Confirmation that `uv run pytest` and `uv run ruff check . && uv run mypy .` pass.
**Do not begin Stage 2 until reviewed.**

---

## What I (the reviewer) will check at these gates
- Stage 0: Is the divergence finding real and specific (actual numbers/keys), or hand-wavy?
  Are the raw field names captured verbatim (Stage 2 depends on them)?
- Stage 1: Are lineage breadcrumbs ACTUALLY populated on every record (a record without
  provenance is a bug per CLAUDE.md)? Is `null` preserved (never coerced to 0)? Are malformed
  rows quarantined-not-dropped? Do tests run offline? Is the adapter interface clean enough
  that MIS slots in without rewriting OGD/SYNC?

## Open questions to surface if hit
- If OGD/SYNC/MIS don't expose monthly grain (only annual), STOP — that contradicts the LOCKED
  monthly decision and needs a re-decision, not a silent fallback to annual.
- If a source needs auth/payment unexpectedly, STOP and report.
