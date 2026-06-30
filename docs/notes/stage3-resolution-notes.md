# Stage 3 · Entity Resolution — closeout notes

> Status: **COMPLETE.** Companion to `docs/RULES.md` (Stage 3) and `docs/DATA_CONTRACT.md` §2.2.
> Records the two closeout decisions that are not obvious from the code alone. Offline build
> against `data/archive/` + `data/archive/lgd/` (the authoritative LGD reference).

---

## 1. R3-SET-02 validity dates — DEFERRED to the store layer (confirmed)

The locked R3-SET-02 behaviour — **keep-both-with-validity, never merge, never forward-map across
a district split** — is fully implemented and tested (`tests/resolve/test_set_reconciliation.py`):
split successors resolve to separate LGD identities, and a geography absent from the current LGD
snapshot is quarantined rather than forward-mapped onto a successor.

The `valid_from` / `valid_to` **date fields** are **not populated in Stage 3**. The archived LGD
reference is a *current snapshot* with no split-date / validity columns, so assigning real dates
would be invention (CLAUDE.md TIER-1 rule 1). The dates are therefore deferred to the **store
layer**, which is where the canonical Geography entity (DATA_CONTRACT §2.2) is materialised. This
defers only the date *display*; the rule's data-integrity guarantee (no merge, no forward-map) is
already enforced structurally upstream. No further Stage 3 action.

## 2. West Bengal — Darjeeling / GTA region (investigated)

**Question:** is the Gorkhaland Territorial Administration (GTA) the *sole* carrier of the
Darjeeling region's employment data, or does clean per-district data also exist?

**Finding (from the flagship archive):** the Darjeeling region is published as **three
sub-district fragments**, each a distinct flagship unit code:

| flagship label | unit code | resolves? |
|---|---|---|
| `KALIMPONG` | 3221 | **Yes** → LGD Kalimpong (clean district, all years) |
| `Darjeeling Gorkha Hill Council (DGHC)` | 3219 | No — hill subdivisions of LGD Darjeeling |
| `GORKHALAND TERRITORIAL ADMINISTRATION (GTA)` | 3219 | No — successor label to DGHC (same unit) |
| `SILIGURI MAHAKUMA PARISAD` | 3204 | No — plains subdivision of LGD Darjeeling |

- DGHC coexists with the clean `KALIMPONG` label in **every** year it appears, so DGHC/GTA is the
  **hill subdivisions of Darjeeling** (not Darjeeling+Kalimpong combined). GTA = renamed DGHC
  (same unit 3219; 2025-26 is the transition year carrying both labels).
- **GTA is NOT the sole carrier**, and there is **no clean district-grain Darjeeling row.**
  Darjeeling exists only as two fragments (DGHC/GTA hill + Siliguri plains). LGD has no
  autonomous-body identity for any of them (only the districts *Darjeeling* and *Kalimpong*).

**Decision (no user call needed — the flag-condition "sole carrier AND clean presentation path"
is not met):** DGHC / GTA / Siliguri Mahakuma Parisad stay **quarantined** (R3-GEO-05) and are
**never aliased to Darjeeling** — a single fragment resolved as the district would under-count,
and summing fragments would fabricate a district total the source never published (R3-SET-02
principle; below the v1 district floor, §5). To honour "no unique data lost", their quarantine
detail is enriched (`GEO_QUARANTINE_NOTES`, `src/data_platform/resolve/aliases.py`) to name each
entity and the LGD district it fragments, so the rows stay **presented and queryable**, not
buried. Kalimpong's data is fully preserved (resolves cleanly). Guarded by
`tests/resolve/test_quarantine_detail.py`.
