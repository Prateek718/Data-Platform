"""Stage 2 — normalization (single-source cleanup).

Pure, deterministic transforms over a single source batch: numeric/format cleaning
(R2-FMT-01), type coercion (R2-TYPE-01), date/FY normalization (R2-DATE-01), and
intra-batch snapshot dedupe (R2-DEDUP-01 / tie-break R2-DEDUP-TB-01). No cross-source
logic — that is Stage 3/4. See ``docs/RULES.md`` Stage 2 and ``docs/DATA_CONTRACT.md`` §4.
"""
