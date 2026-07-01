"""Stage 3.5 reshape — wide / single-period source rows → long records.

Runs at the START of Stage 2 (before FMT/DEDUP/TYPE), turning the archive's non-flagship shapes
into the long, one-fact-per-row form the rest of the pipeline expects. Pure and source-agnostic —
every choice is driven by per-resource config, never per-dataset hardcode:

* :func:`simple_melt` — wide-pure tables (year-only column headers, one title-defined measure):
  one row per (id-columns × year), emitting ``_fin_year`` + ``_value``.
* :func:`compound_melt` — wide-compound tables where the metric stem AND the financial year are
  FUSED in one header (``households_provided_employment___2015_16``): split BOTH, emitting
  ``_metric`` + ``_fin_year`` + ``_value``. Refuses (never drops) a non-id column with no year.
* :func:`inject_period` — single-period tables whose FY lives in the title/as-on, not a column.
* :func:`inject_geo` — single-state tables whose state lives only in the title.

Financial-year tokens are emitted hyphenated (``2019-20`` / ``2011-2012``) and left for
R2-DATE-01 to canonicalize — reshape does not itself judge validity. The FY token regex matches a
whole ``YYYY-YY``/``YYYY-YYYY`` span as ONE token, so a full-form end-year is never mistaken for a
separate start year.
"""

from __future__ import annotations

import re

from data_platform.normalize.models import RawCell

Row = dict[str, RawCell]

# One financial-year token: a 4-digit start year then a 2- or 4-digit end, joined by - or _.
_FY_TOKEN = re.compile(r"(?:19|20)\d{2}[-_]\d{2,4}")


def _canonical_fy(token: str) -> str:
    """Hyphenate a raw FY token (``2019_20`` → ``2019-20``); R2-DATE-01 does the real validation."""
    return token.replace("_", "-")


def parse_compound_header(name: str) -> tuple[str, str] | None:
    """Split a fused ``<metric-stem>...<YYYY_YY>`` header into ``(stem, hyphenated-FY)``.

    Returns ``None`` when the header carries no FY token (e.g. an id/label column). The stem is
    everything before the year token with trailing separators stripped; anything after the token
    (a trailing ``_p`` provisional marker, say) is not part of the stem or the year.
    """
    match = _FY_TOKEN.search(name)
    if match is None:
        return None
    stem = name[: match.start()].strip("_ ")
    return stem, _canonical_fy(match.group())


def simple_melt(
    rows: list[Row],
    *,
    id_columns: list[str],
    year_columns: list[str],
) -> tuple[list[Row], list[str]]:
    """Melt year-only columns to rows: one output row per (id-columns × year)."""
    out: list[Row] = []
    for row in rows:
        for year_col in year_columns:
            token = _FY_TOKEN.search(year_col)
            fin_year = _canonical_fy(token.group()) if token is not None else year_col
            new: Row = {col: row.get(col) for col in id_columns}
            new["_fin_year"] = fin_year
            new["_value"] = row.get(year_col)
            out.append(new)
    return out, [*id_columns, "_fin_year", "_value"]


def compound_melt(
    rows: list[Row],
    *,
    id_columns: list[str],
) -> tuple[list[Row], list[str]]:
    """Melt fused ``metric___YYYY_YY`` columns to ``(_metric, _fin_year, _value)`` rows.

    Every column that is not an id column MUST carry a FY token; one that does not cannot be melted
    and would be silently lost, so this raises rather than drop it (zero-data-loss). The caller
    resolves such a column by adding it to ``id_columns`` or quarantine-deferring the dataset.
    """
    id_set = set(id_columns)
    measure_columns = [c for c in _all_columns(rows) if c not in id_set]
    parsed = {c: parse_compound_header(c) for c in measure_columns}
    unmeltable = [c for c, p in parsed.items() if p is None]
    if unmeltable:
        raise ValueError(f"compound_melt: non-id columns without a year token: {unmeltable}")

    out: list[Row] = []
    for row in rows:
        for col in measure_columns:
            stem, fin_year = parsed[col]  # type: ignore[misc]  # None ruled out above
            new: Row = {c: row.get(c) for c in id_columns}
            new["_metric"] = stem
            new["_fin_year"] = fin_year
            new["_value"] = row.get(col)
            out.append(new)
    return out, [*id_columns, "_metric", "_fin_year", "_value"]


def inject_period(
    rows: list[Row], *, fin_year: str, columns: list[str]
) -> tuple[list[Row], list[str]]:
    """Add a constant ``_fin_year`` (from the title/as-on) to each row of a single-period table."""
    out = [{**row, "_fin_year": fin_year} for row in rows]
    return out, [*columns, "_fin_year"]


def inject_geo(
    rows: list[Row], *, state_name: str, columns: list[str]
) -> tuple[list[Row], list[str]]:
    """Add a constant ``_state`` (from the title) to each row of a single-state table."""
    out = [{**row, "_state": state_name} for row in rows]
    return out, [*columns, "_state"]


def _all_columns(rows: list[Row]) -> list[str]:
    """Union of keys across rows, first-seen order (rows may be sparse)."""
    seen: dict[str, None] = {}
    for row in rows:
        for key in row:
            seen.setdefault(key, None)
    return list(seen)
