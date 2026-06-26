"""Stage 2 orchestrator — ``normalize_batch`` (T2.6 STUB — red checkpoint).

Pure transform: a Stage 1 ``RawLandingBatch`` in, a :class:`NormalizedBatch` out. Composes the
Stage 2 rules in the locked order — R2-FMT-01 (every cell) → R2-DEDUP-01 (on FMT-cleaned grain
keys) → R2-TYPE-01 / R2-DATE-01 (on surviving rows, per the config column-type spec) — and
records all per-cell + dedupe lineage. Implemented in the green commit ``feat(stage2): …``.
"""

from __future__ import annotations

from data_platform.ingest.landing import RawLandingBatch
from data_platform.normalize.models import NormalizedBatch


def normalize_batch(batch: RawLandingBatch) -> NormalizedBatch:
    """Normalize one landing batch. STUB — raises until the green commit."""
    raise NotImplementedError("T2.6 normalize_batch — implemented in the green commit")
