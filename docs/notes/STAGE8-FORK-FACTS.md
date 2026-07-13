# Stage 8 — Fork Facts: embedded traces vs live traces

> The report shows a number; the reader wants to see where it came from. There are two ways to
> serve that trace, and the choice shapes `report.json`, the Stage 9 viewer, and what a reader can
> do with the repo offline.
>
> **This document contains facts and options only — no recommendation.** The presentation shape is
> the human's decision at the Stage 8 checkpoint. Every number below was measured on this machine
> against the real `dist/v1.0` (`scripts/stage8_fork_facts.py`, plus the pilot run itself).

---

## What a "trace" actually is

The `get_lineage` payload for one fact: the metric, unit, period, geography, value, confidence,
reconciliation status, resolution rule id, **every source that carried the fact** (source id,
data.gov.in resource id, that source's value, its as-of date, its authority rank), any rejected
values, the materiality reading, and the null reason where the cell is null.

That is what "clicking a number" would reveal, on either path.

---

## Path A — embedded traces (the trace travels inside `report.json`)

**Measured, per figure** (pilot section, real dist):

| fact | sources | lineage payload |
|---|---|---|
| North Goa person-days | 1 | 609 bytes |
| South Goa person-days | 1 | 609 bytes |
| Goa state person-days | 3 | 928 bytes |
| North Goa wage rate | 1 | 624 bytes |
| South Goa wage rate | 1 | 624 bytes |

Median **624 bytes**; range 609–928. The **fattest trace in the entire record** is a flagged
cross-publisher disagreement carrying **10 sources: 2,812 bytes**.

**The pilot's actual `report.json`** (5 figures, 2 derivations, 2 refusal exhibits, embedded traces,
full prose): **9,635 bytes** compact, 13,994 pretty-printed. Of the compact bytes, **3,394 (35%) are
the lineage payloads**, 819 the refusal objects, 1,606 the prose.

**Projection to a full report** (median trace / worst case, lineage bytes only):

| figures in report | median traces | all-worst-case traces |
|---|---|---|
| 40 | ~24 KiB | ~110 KiB |
| 80 | ~49 KiB | ~220 KiB |
| 120 | ~73 KiB | ~330 KiB |

A realistic full report (the claim inventory's surviving sections, on the order of 40–80 figures)
lands at roughly **30–120 KiB total** — a single self-contained JSON file, comfortably smaller than
one photograph.

**What clicking a number shows from embedded data alone:** everything above — sources, resource ids,
as-of dates, rejected values, the % spread, the rule that adjudicated it, the null reason. The trace
is complete for the figures the report cites. What it *cannot* do is let the reader pivot to a fact
the report never cited (a different state, a different year): those traces are not in the file.

---

## Path B — live traces (the viewer asks the server on click)

**Measured, this machine, real dist:**

| operation | time |
|---|---|
| cold start: spawn the server subprocess + checksum-gate the release artifacts + load DuckDB + MCP `initialize` | **1.076 s** |
| warm `get_lineage`, one fact, over stdio (n=25) | **6.3 ms** median (5.8–6.9) |
| warm `get_lineage`, batched, all 5 pilot facts in one call | **9.1 ms** |
| the same call in-process, no protocol | 1.3 ms (0.39 s cold load) |

So: one ~1.1 s cost on first click (or at page load, if warmed eagerly), then traces arrive in
single-digit milliseconds. Latency is not the constraint on this path. **Mechanism is.**

**The mechanical problem:** the MCP server speaks **JSON-RPC over stdio to a child process**. A
static HTML file opened from disk (`file://`) or served from GitHub Pages cannot spawn a process,
cannot open a pipe, and cannot speak stdio. Something has to bridge that gap.

The data it would need to reach is not small: **`lineage.jsonl` is 55.3 MiB** (against 0.1 MiB for
the state series and 1.0 MiB for the district table). "Just ship the lineage next to the viewer" is
therefore not a free option — it is a 55 MiB download, and it is also **gitignored**, so it is not in
the repo a reader clones.

**Realistic options for a static-file viewer to reach a stdio process:**

| option | what it is | effort / fragility |
|---|---|---|
| **Local bridge process** | The reader runs one command (`uv run python -m …`) that starts an HTTP server on localhost, which proxies to the MCP server (or hosts the query core directly) and serves the viewer page. | Low effort (small HTTP shim). Robust — but the viewer only works while the reader is running it; a shared link to the report is dead on someone else's machine. |
| **Viewer-launched subprocess** (Electron/Tauri, or a local Python GUI) | The viewer *is* a process, so it can spawn the server itself. | High effort (a desktop app for a report). Robust once built, but a heavyweight dependency for reading a document, and no longer "a static file". |
| **Hosted MCP/HTTP endpoint** | Run the server somewhere public; the viewer fetches over HTTPS. | Medium effort, but it introduces a **live runtime dependency and hosting cost for a sealed, DOI-frozen record** — and if the host ever dies, the report's traces die with it. Contradicts "the portal is not a runtime dependency". |
| **Ship the lineage to the browser** (bundle `lineage.jsonl`, or a pruned subset, and query it client-side) | No server at all; the viewer reads a data file. | Low-to-medium effort. Full file is 55 MiB and gitignored; a *pruned* subset (only the cited facts) is exactly Path A with extra steps. |
| **Pre-rendered trace files** (one JSON per cited fact, emitted at report-generation time) | The generator writes `traces/<fact_id>.json`; the viewer fetches them lazily. | Low effort. Works from any static host. Same total bytes as Path A, split across files — buys lazy loading, not new capability. |

**What a live path would additionally allow that embedding does not:** the reader could query facts
the report never cited — walk to another state, another year, another metric — because the whole
served surface is behind the click, not just the figures the report chose. That is the real
difference between the two paths, and it is a product question, not a performance one.

---

## The pilot run itself (facts, for the record)

Real model, real dist, MCP over stdio, one section (Goa FY 2022-23):

- **54.8 s** wall clock end to end; **1 drafting attempt**; 5 figures, 2 derivations, 2 refusal
  exhibits; every number machine-checked against the served data.
- Model: `tencent/hy3:free` via OpenRouter (a reasoning model: it spends ~1,900 reasoning tokens
  before writing a word — which is why the completion budget is config-carried).
- The two defects the live run exposed — a token budget swallowed by reasoning, and the verifier
  reading a quoted refusal's `month="2022-04"` argument as a financial-year claim — are fixed, with
  tests. An earlier run of the same section took **2 attempts**: the verifier rejected the first
  draft and the drafter recovered from the mismatch report. The loop is not decorative.
