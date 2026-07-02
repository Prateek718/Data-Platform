"""R4-REC — cross-source value reconciliation for one canonical key.

Given the values several sources report for the same (scheme, geo, period, metric), produce ONE
canonical value with the rule recorded — resolving conservatively (CLAUDE.md philosophy):

* **R4-REC-04** — one source only: take it; ``sources_seen`` has one entry, no disagreement.
* **R4-REC-01** — multiple sources within tolerance: they agree; take the most authoritative
  (lowest ``authority_rank``); no disagreement recorded.
* **R4-REC-02** — multiple sources disagree beyond tolerance: still take the most authoritative
  (a grounded source-priority rule adjudicates — DATA_CONTRACT §3), but RECORD the disagreement
  (max pairwise %, the rejected sources) in lineage. The rejected values are never discarded.

Tolerance is config-carried (``config.tolerance_for``); ``None`` means exact equality is required
(pure counts). Pure and deterministic — no I/O.
"""

from __future__ import annotations

from data_platform.harmonize.models import Reconciliation, SourceValue


def reconcile(values: list[SourceValue], *, metric: str) -> Reconciliation | None:
    """Reconcile the per-source values for one canonical key into a single outcome (or None)."""
    raise NotImplementedError
