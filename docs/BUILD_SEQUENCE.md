# Data Platform — BUILD_SEQUENCE.md — the locked stage order

> **Data Platform** — A governed data layer that reconciles MGNREGA facts published across
> multiple datasets and departments within data.gov.in into one contracted, lineage-tracked
> dataset (one canonical series, **FY 2006–07 → FY 2026–27**), served over MCP for AI agents to
> query. The **full MGNREGA archive** (88 API/JSON + 41 file-only CSVs + LGD) is captured
> **offline under `data/archive/`**; everything builds against that local archive, not the live
> portal.
>
> The build proceeds **one stage at a time, in the order below**, with a **review gate between
> stages** (CLAUDE.md TIER 2). This file documents the established sequence; it does not invent
> stages. Per-stage detail lives in `docs/specs/`, with rules in `docs/RULES.md` and the
> canonical schema in `docs/DATA_CONTRACT.md` (both authoritative — never override them here).

The pipeline spine (CLAUDE.md):

```
messy multi-source MGNREGA data
  → ingest → normalize → entity-resolution → metric-harmonization
  → validation gate → governed store + lineage → MCP query surface
  → autonomous analyst (read-only) → traceable report
```

## The 12 stages

| # | Stage | One-line scope | Status |
|---|---|---|---|
| 0 | **Source reconnaissance + divergence verification** | Prove the cross-department divergence is real (units/grain/year-slice); capture verbatim source field names. | ✅ done |
| 1 | **Ingestion (landing)** | Drift-aware adapters land raw source rows verbatim with batch-level lineage breadcrumbs; quarantine, never drop. | ✅ done |
| 2 | **Normalization (single-source cleanup)** | Per-row format/date/type cleanup + snapshot dedupe (R2-*). No cross-source logic. | ✅ done |
| 3 | **Entity resolution** | Resolve scheme + geography to canonical LGD identity by name join (R3-*); quarantine the unresolvable. | ✅ done |
| 4 | **Metric harmonization** | Cross-source unit/definition/value reconciliation to one trustworthy canonical value per metric (R4-*). | ✅ done — the R4 rule family and the `harmonize` module produce the canonical series shipped in the v1.0 release. |
| 5 | **Validation gate** | Enforce the quarantine handoff (R4-Q-01): impossible/un-normalizable rows excluded from the golden store but kept queryable. | ✅ done — the quarantine handoff is enforced in the pipeline: impossible rows are excluded from the golden store and remain queryable as quarantined. |
| 6 | **Governed store + lineage** | Materialize the golden dataset with every DATA_CONTRACT §4 lineage field populated per fact. | ✅ done — the lineage-bearing export: every published fact carries per-fact provenance in `lineage.jsonl` in the v1.0 release. |
| 7 | **MCP query surface** | Standards-compliant, **read-only** MCP server exposing query + `get_lineage`; no mutation verb. | ✅ done — the read-only MCP server over the sealed v1.0 dataset, checksum-gated at startup; refusals are first-class objects. |
| 8 | **Autonomous analyst (read-only)** | The only LLM use in the system — an agent that queries the surface to answer questions. | ✅ done — a LangGraph agent that reads the record only through the MCP surface; a deterministic verifier re-checks every number it writes, and a section whose numbers fail to check is blocked. |
| 9 | **Traceable report** | The analyst's output: every claim cited back through lineage to source. | ✅ done — delivered with Stage 8 under `report/`: every figure carries its `fact_id` and full lineage; claims the served data cannot back are recorded as verification-FAILED, not printed. |
| 10 | **Packaging & deployment** | `docker compose up` brings the full stack up clean on a fresh checkout. | ✅ done — delivered as bootstrap-then-serve: a fresh checkout has no data (`dist/` is gitignored), so `data-platform-bootstrap` fetches the sealed v1.0.0 release and verifies it twice — the zip against the release's published digest, the extracted files against the manifest the server enforces at startup — before `docker compose run --rm -T mcp` (or `data-platform-mcp`) serves it. All-or-nothing install; a failed fetch never leaves a partial or damaged dataset. |
| 11 | **README & disclosure** | Project README + honest disclosure of limitations, scope boundaries, and known data caveats. | pending |

## Notes on the order

- **Stages 2–4 are pure transforms** — side-effect-free, unit-tested with golden fixtures
  (CLAUDE.md CONVENTIONS). Stages 3 and 4 are the two hard stages.
- **The boundary that splits 2 vs 4:** single-source cleanup is Stage 2; anything needing
  cross-source comparison is Stage 4 (RULES.md placement test).
- **LLM use is confined to Stage 8+** (the analyst consumer). No probabilistic/ML matching or LLM
  calls inside the Stage 2–4 transforms — deterministic only (CLAUDE.md TIER 1).
- **Review gate between every stage:** do not begin stage N+1 until stage N is reviewed.
