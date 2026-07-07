"""V1 export — serialize the assembled canonical series to the public deliverable files.

Not a pipeline stage: it reads the same reconciled series the archive-gated harmonization tests
prove, and writes it to flat, friendly CSV/Parquet plus a deep per-fact ``lineage.jsonl``. Pure
transforms live in :mod:`records`; archive assembly in :mod:`build`; I/O in :mod:`write`.
"""
