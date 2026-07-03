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
from typing import Literal

from pydantic import BaseModel, ConfigDict

from data_platform.normalize.models import RawCell

Row = dict[str, RawCell]

# Lineage notes stamped on synthesized columns so the applied reshape is auditable (§4).
_MELT_NOTE = {"simple": "R3.5-MELT-SIMPLE", "compound": "R3.5-MELT-COMPOUND"}
_PERIOD_NOTE = "R3.5-PERIOD-FROM-TITLE"
_GEO_NOTE = "R3.5-GEO-FROM-TITLE"

# One financial-year token: a 4-digit start year then a 2- or 4-digit end, joined by - or _.
_FY_TOKEN = re.compile(r"(?:19|20)\d{2}[-_]\d{2,4}")

# A period-NARROWING suffix after the FY token (`..._2015_16_upto_30_09_2015`): the column reports a
# PARTIAL slice of the financial year (upto / till a mid-year date), a DIFFERENT period — not a
# full-year value. A trailing provisional marker (`_p_`) narrows nothing and must NOT match.
_PERIOD_NARROWING = re.compile(r"^(?:up ?to|up ?til|till|as ?on|as ?of)\b", re.I)


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


def compound_period_qualifier(name: str) -> str | None:
    """The period-narrowing suffix of a compound header, or ``None`` for a full-year column.

    A header like ``hh_provided___2015_16_upto_30_09_2015`` reports only PART of FY2015-16 (a
    different period), so the suffix after the FY token is surfaced (space-normalized) to keep the
    value out of the full-year comparison. Returns ``None`` when there is no FY token, no suffix, or
    a suffix that narrows nothing (e.g. a ``_p_`` provisional marker).
    """
    match = _FY_TOKEN.search(name)
    if match is None:
        return None
    suffix = name[match.end() :].strip("_ ").replace("_", " ")
    return suffix if suffix and _PERIOD_NARROWING.search(suffix) else None


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

    qualifiers = {c: compound_period_qualifier(c) for c in measure_columns}
    out: list[Row] = []
    for row in rows:
        for col in measure_columns:
            stem, fin_year = parsed[col]  # type: ignore[misc]  # None ruled out above
            new: Row = {c: row.get(c) for c in id_columns}
            new["_metric"] = stem
            new["_fin_year"] = fin_year
            new["_value"] = row.get(col)
            new["_period_qualifier"] = qualifiers[col]
            out.append(new)
    return out, [*id_columns, "_metric", "_fin_year", "_value", "_period_qualifier"]


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


class ReshapeSpec(BaseModel):
    """Per-resource reshape rule applied before Stage-2 cleaning (a no-op default for long tables).

    ``melt`` selects the melt shape (``none`` for already-long / single-period tables); the
    ``inject_*`` fields add a constant column derived from the dataset title (the FY of a
    single-period table, the state of a single-state table). Melt runs first, then the injections.
    """

    model_config = ConfigDict(strict=True, frozen=True)

    melt: Literal["none", "simple", "compound"] = "none"
    id_columns: list[str] = []
    year_columns: list[str] = []
    inject_fin_year: str | None = None
    inject_state: str | None = None


def apply_reshape(
    rows: list[Row], columns: list[str], spec: ReshapeSpec
) -> tuple[list[Row], list[str]]:
    """Run a resource's configured reshape, returning the long rows + their column names."""
    if spec.melt == "simple":
        rows, columns = simple_melt(
            rows, id_columns=spec.id_columns, year_columns=spec.year_columns
        )
    elif spec.melt == "compound":
        rows, columns = compound_melt(rows, id_columns=spec.id_columns)
    if spec.inject_fin_year is not None:
        rows, columns = inject_period(rows, fin_year=spec.inject_fin_year, columns=columns)
    if spec.inject_state is not None:
        rows, columns = inject_geo(rows, state_name=spec.inject_state, columns=columns)
    return rows, columns


def reshape_notes(spec: ReshapeSpec) -> dict[str, str]:
    """The lineage note for each column synthesized by ``spec`` (empty when reshape is a no-op)."""
    notes: dict[str, str] = {}
    if spec.melt != "none":
        note = _MELT_NOTE[spec.melt]
        notes["_fin_year"] = note
        notes["_value"] = note
        if spec.melt == "compound":
            notes["_metric"] = note
            notes["_period_qualifier"] = note
    if spec.inject_fin_year is not None:
        notes["_fin_year"] = _PERIOD_NOTE
    if spec.inject_state is not None:
        notes["_state"] = _GEO_NOTE
    return notes
