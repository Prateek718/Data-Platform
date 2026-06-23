# CLAUDE.md — Data Platform

> **Data Platform** — A governed data layer that reconciles MGNREGA facts published across
> multiple datasets and departments within data.gov.in into one contracted, lineage-tracked
> dataset, served over MCP for AI agents to query.
> (MGNREGA is the reference implementation; the platform is architected scheme-agnostic.)
>
> Steering file. Auto-loaded every session. Kept lean on purpose.
> Treat DATA_CONTRACT.md and RULES.md as authoritative — do not invent schema or rules.

## TIER 1 — HARD RULES (check before every action)
1. **Never invent canonical schema, entity-resolution rules, or harmonization rules.**
   These live in `docs/DATA_CONTRACT.md` and `docs/RULES.md`. If something you need is not
   specified there, STOP and write it as an Open Question — do not guess.
2. **Deterministic only.** No probabilistic/ML matching, no LLM calls inside the pipeline
   transforms. The only LLM use is the analyst consumer (Stage 8+).
3. **Read before acting.** Never claim what a source file or module does without opening it.
4. **null ≠ 0.** Missing metric values are null, never coerced to zero.
5. **Consumers are read-only.** The MCP surface exposes no mutation verb to consumers.

## TIER 2 — WORKFLOW
- Non-trivial task (3+ steps or any design decision) → enter plan mode, write plan to
  `tasks/<stage>-todo.md`, check in before implementing.
- TDD: write tests first, confirm they fail, commit failing tests, implement until green,
  do not modify tests to make them pass.
- One pipeline stage at a time, in the order in BUILD_SEQUENCE (below). Review gate between.

## ARCHITECTURE (one line)
messy multi-source MGNREGA data → ingest → normalize → Stage3 entity-resolution →
Stage4 metric-harmonization → validation gate → governed store + lineage →
standards-compliant MCP query surface → autonomous analyst (read-only) → traceable report.

## STACK
Python 3.12 · uv · ruff · mypy (strict) · pytest · Pydantic (contracts) ·
Postgres (governed store) · MCP server SDK · LangGraph (analyst) · Docker Compose.
[DECISION NEEDED: confirm Postgres vs other store; confirm LangGraph for analyst.]

## BUILD & TEST
- `uv run pytest` — tests
- `uv run ruff check . && uv run mypy .` — lint + types (must pass after every edit)
- `docker compose up` — full stack (must come up clean on a fresh checkout)

## CONVENTIONS ENFORCED IN REVIEW
- Pure transforms (Stage 2–4) are side-effect-free and unit-tested with golden fixtures.
- Every lineage field in DATA_CONTRACT §4 is populated — a fact without lineage is a bug.
- Config-carried thresholds (tolerances, staleness) — never hardcoded magic numbers.

## SPECS
Per-stage specs live in `docs/specs/`. Build order in `docs/BUILD_SEQUENCE.md`.
Foundational decisions in `docs/DATA_CONTRACT.md` and `docs/RULES.md` — authoritative.
