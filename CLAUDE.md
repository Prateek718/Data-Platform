# CLAUDE.md — Data Platform

> **Data Platform** — A governed data layer that reconciles MGNREGA facts published across
> multiple datasets and departments within data.gov.in into one contracted, lineage-tracked
> dataset (one canonical series, **FY 2006–07 → FY 2026–27**), served over MCP for AI agents to
> query. The **full MGNREGA archive** (88 API/JSON datasets + 41 file-only CSVs + LGD) is captured
> **offline under `data/archive/` (gitignored)**; everything builds against that local archive —
> the portal is not a live runtime dependency. Pre-2018 history comes from non-flagship sources.
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

## TIER 2 — WORKFLOW & EXECUTION

### Think before coding (don't assume, don't hide confusion, surface tradeoffs)
- State assumptions explicitly. If uncertain, ask — don't run with a silent guess.
- If multiple interpretations exist, present them; don't pick one quietly.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop, name what's confusing, and ask. (This is the behavioural
  side of TIER 1 rule 1: an unspecified rule is an Open Question, never an invention.)

### Plan, then build
- Non-trivial task (3+ steps or any design decision) → enter plan mode, write the plan to
  `tasks/<stage>-todo.md`, check in before implementing.
- One pipeline stage at a time, in BUILD_SEQUENCE order. Review gate between stages.

### TDD rhythm (goal-driven — define success, loop until verified)
- Turn instructions into verifiable goals before coding: "fix the bug" → "write a test that
  reproduces it, then make it pass"; "add validation" → "write tests for invalid inputs,
  then make them pass."
- Write tests first, confirm they fail, commit the failing tests, implement until green.
  Do NOT modify tests to make them pass.
- Every invariant gets a guarding test, not a comment.

### Simplicity first (minimum code that solves the problem; nothing speculative)
- No features, abstractions, "flexibility", or error handling beyond what the task needs.
- No abstractions for single-use code.
- If you wrote 200 lines and it could be 50, rewrite it. The test: "would a senior engineer
  call this overcomplicated?" If yes, simplify.
- Note: config-carried thresholds (tolerances, staleness, tie-breaks) are a deliberate
  requirement, NOT speculative configurability — they are mandated below and override the
  "nothing configurable unless asked" default.

### Surgical changes (touch only what you must; clean up only your own mess)
- Every changed line should trace directly to the task. Don't "improve" adjacent code,
  comments, or formatting; don't refactor what isn't broken; match existing style.
- Remove imports/variables/functions YOUR change orphaned. Don't delete pre-existing dead
  code — mention it instead.

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

---
> Workflow guidelines in TIER 2 (think-before-coding, simplicity, surgical changes,
> goal-driven TDD) adapt Andrej Karpathy's observations on LLM coding pitfalls to this
> project. They bias toward caution over speed; for trivial changes, use judgment. On any
> conflict, TIER 1 hard rules and DATA_CONTRACT.md / RULES.md win.
