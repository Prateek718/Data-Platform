"""Extract canonical metric values from the PRE-2018 historical sources (already resolved).

Stage 3.5 lands each historical source as resolved state (or national) rows with melted cells
``{_metric: <column stem>, _fin_year, _value}``. This module maps those stems to canonical metrics
and normalizes their units — the per-source "metric mapping", config-carried as explicit rules.
It is NOT adjudication: it just produces per-(geo, FY, metric) :class:`SourceValue`s that the
Stage-4 reconciler then trusts/compares. Rules are pattern-based so one rule covers a source
family's stem spelling variants (e.g. "Expenditure on (In Lakhs) - Wages -" vs "...(` In lakhs)…").
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from enum import StrEnum

from data_platform.harmonize.config import (
    ADMIN_EXPENDITURE,
    HOUSEHOLDS_COMPLETED_100_DAYS,
    HOUSEHOLDS_EMPLOYED,
    MATERIAL_SKILLED_EXPENDITURE,
    PERSONDAYS_GENERATED,
    TOTAL_EXPENDITURE,
    WAGES_EXPENDITURE,
)
from data_platform.harmonize.models import CanonicalKey, SourceValue
from data_platform.harmonize.units import CountScale, MoneyUnit, to_canonical_lakh, to_raw_count
from data_platform.normalize.models import CleanCell
from data_platform.resolve.models import GeoLevel, ResolvedBatch

Cells = dict[int, dict[str, CleanCell]]


class UnitKind(StrEnum):
    """How a source column's value must be normalized to the metric's canonical unit."""

    MONEY_LAKH = "money_lakh"  # already INR lakh → canonical money unit, no scaling
    COUNT_RAW = "count_raw"  # already a raw count
    COUNT_LAKH = "count_lakh"  # a count "in lakh" → × 100,000


@dataclass(frozen=True)
class StemRule:
    """Map a source ``_metric`` stem (by regex) to a canonical metric + its unit normalization."""

    pattern: re.Pattern[str]
    metric: str
    unit_kind: UnitKind


# Stems to skip outright — percentages, releases/funds, and per-category or rate breakdowns that are
# NOT the canonical metric (never map these; they share keywords but mean something else).
STEM_EXCLUDE = re.compile(
    r"%|percentage|central release|funds available|- scs|- sts|- others|- women"
    r"|average|beneficiary|demanded|not paid|rejection|allotted|registered|wage rate|per personday",
    re.I,
)

# The MoSPI "Financial Outcomes" family: wages / material / administration / total expenditure,
# published in INR lakh. One rule set covers all three files' stem-spelling variants.
FINANCIAL_OUTCOMES_RULES: tuple[StemRule, ...] = (
    StemRule(re.compile(r"expenditure on.*wages", re.I), WAGES_EXPENDITURE, UnitKind.MONEY_LAKH),
    StemRule(
        re.compile(r"expenditure on.*material", re.I),
        MATERIAL_SKILLED_EXPENDITURE,
        UnitKind.MONEY_LAKH,
    ),
    StemRule(
        re.compile(r"expenditure on.*(administration|admin)", re.I),
        ADMIN_EXPENDITURE,
        UnitKind.MONEY_LAKH,
    ),
    StemRule(re.compile(r"expenditure on.*total", re.I), TOTAL_EXPENDITURE, UnitKind.MONEY_LAKH),
)

# MoSPI "Implementation Report" state family: households provided + 100-days as RAW counts,
# persondays as a lakh count. (Demanded / per-category / average stems are excluded above.)
MOSPI_IMPLEMENTATION_RULES: tuple[StemRule, ...] = (
    StemRule(
        re.compile(r"households provided employment", re.I), HOUSEHOLDS_EMPLOYED, UnitKind.COUNT_RAW
    ),
    StemRule(
        re.compile(r"availed 100 days|100 days of employment", re.I),
        HOUSEHOLDS_COMPLETED_100_DAYS,
        UnitKind.COUNT_RAW,
    ),
    StemRule(
        re.compile(r"persondays in lakhs - total", re.I),
        PERSONDAYS_GENERATED,
        UnitKind.COUNT_LAKH,
    ),
)

# RS "households provided employment" tables — provided-employment counts published in lakh.
RS_HOUSEHOLDS_RULES: tuple[StemRule, ...] = (
    StemRule(
        re.compile(r"provided.?employment|hh.*provided|household.*provided", re.I),
        HOUSEHOLDS_EMPLOYED,
        UnitKind.COUNT_LAKH,
    ),
)

# RS "households completed 100 days" table — a raw count ("... in nos ...").
RS_HUNDRED_DAYS_RULES: tuple[StemRule, ...] = (
    StemRule(
        re.compile(r"completed 100 days|100 days", re.I),
        HOUSEHOLDS_COMPLETED_100_DAYS,
        UnitKind.COUNT_RAW,
    ),
)

# National sources are WIDE (one row per FY, one column per metric) — not melted. Column names use
# underscores, so patterns use ``.`` between words. Provided-employment / availed-100-days are raw
# counts; persondays is a lakh count. (The subcategory persondays "___scs/sts/…" columns don't match
# the specific "…total" pattern; "demanded"/"average" are dropped by STEM_EXCLUDE.)
NATIONAL_IMPLEMENTATION_RULES: tuple[StemRule, ...] = (
    StemRule(
        re.compile(r"households.provided.employment", re.I),
        HOUSEHOLDS_EMPLOYED,
        UnitKind.COUNT_RAW,
    ),
    StemRule(
        re.compile(r"availed.100.days", re.I), HOUSEHOLDS_COMPLETED_100_DAYS, UnitKind.COUNT_RAW
    ),
    StemRule(
        re.compile(r"persondays.in.lakhs.+total", re.I), PERSONDAYS_GENERATED, UnitKind.COUNT_LAKH
    ),
)

# Wired historical NATIONAL sources: (resource-id prefix, rules). Financial-Outcomes national reuses
# the expenditure rules — the "% Age …" and "Central Release" columns are dropped by STEM_EXCLUDE.
HISTORICAL_NATIONAL_SOURCES: tuple[tuple[str, tuple[StemRule, ...]], ...] = (
    ("04476f1d", NATIONAL_IMPLEMENTATION_RULES),
    ("1878204d", NATIONAL_IMPLEMENTATION_RULES),
    ("54d1a5fa", NATIONAL_IMPLEMENTATION_RULES),
    ("d88e2cb6", NATIONAL_IMPLEMENTATION_RULES),
    ("7496d75d", FINANCIAL_OUTCOMES_RULES),
    ("8d734637", FINANCIAL_OUTCOMES_RULES),
    ("99a91845", FINANCIAL_OUTCOMES_RULES),
)

# Which GENUINE historical STATE sources are wired, and the rule set each uses (resource-id prefix →
# rules). Verified against the archive: MoSPI raw counts vs RS lakh counts agree on clean full-year
# cells (the residual differences are real — partial-year snapshots / revisions — and get flagged).
HISTORICAL_STATE_SOURCES: tuple[tuple[str, tuple[StemRule, ...]], ...] = (
    ("d64434e9", FINANCIAL_OUTCOMES_RULES),
    ("18527128", FINANCIAL_OUTCOMES_RULES),
    ("fd7c50d2", FINANCIAL_OUTCOMES_RULES),
    ("2d0a4136", MOSPI_IMPLEMENTATION_RULES),
    ("3ebbea46", MOSPI_IMPLEMENTATION_RULES),
    ("9aefcd0f", MOSPI_IMPLEMENTATION_RULES),
    ("c11b65d4", MOSPI_IMPLEMENTATION_RULES),
    ("34a83496", RS_HOUSEHOLDS_RULES),
    ("6c12385f", RS_HOUSEHOLDS_RULES),
    ("c5c8858c", RS_HOUSEHOLDS_RULES),
    ("e5491ee9", RS_HOUSEHOLDS_RULES),
    ("cb137c04", RS_HOUSEHOLDS_RULES),
    ("2611cc74", RS_HOUSEHOLDS_RULES),
    ("22f8cdb0", RS_HOUSEHOLDS_RULES),
    ("73d68992", RS_HUNDRED_DAYS_RULES),
)


# MoSPI Statistical Year Book EDITION FAMILIES (state tier) — successive dated editions of ONE SYB
# table by one publisher (SRC_MOSPI). VERIFIED in docs/stage-4-5-series-assembly-summary.md:
# identical catalog + nesting FY spans + documented terminal-year mid-year partials + empirically
# unidirectional restatement (a later edition restates earlier ones; ~0 reversions). Reconcile
# applies R4-REC-10 (supersession) / R4-REC-11 (partial-terminal exclusion) to any value carrying
# edition markers; this set is where the markers are stamped. Membership is by resource id, but the
# span end + terminal-year flag are DATA-DERIVED (the source's own maximum FY), never hardcoded.
MOSPI_EDITION_FAMILIES: frozenset[str] = frozenset(
    {
        "18527128",  # Financial Outcomes  (SYB Table 35.3): SYB2016
        "fd7c50d2",  #                                        SYB2017
        "d64434e9",  #                                        SYB2018
        "3ebbea46",  # Implementation Report (SYB Table 35.1): SYB2015
        "9aefcd0f",  #                                         SYB2016
        "2d0a4136",  #                                         SYB2017
        "c11b65d4",  #                                         SYB2018
    }
)


def _stamp_edition_markers(
    out: list[tuple[CanonicalKey, SourceValue]], resource_id: str
) -> list[tuple[CanonicalKey, SourceValue]]:
    """Stamp the DATA-DERIVED edition span-end + terminal-year flag on an edition family's values.

    No-op unless ``resource_id`` names a registered MoSPI SYB edition file. The edition's span end
    is the source's own maximum financial-year (the latest year it covers); a value whose year is
    that span end is the edition's terminal year — a documented mid-year partial (R4-REC-11).
    Reconcile ranks editions by this span end so the latest supersedes earlier ones (R4-REC-10).
    """
    if not out or not any(resource_id.startswith(prefix) for prefix in MOSPI_EDITION_FAMILIES):
        return out
    span_end = max(key.fin_year for key, _ in out)
    return [
        (
            key,
            value.model_copy(
                update={
                    "edition_span_end": span_end,
                    "is_edition_terminal": key.fin_year == span_end,
                }
            ),
        )
        for key, value in out
    ]


# A period-narrowing marker anywhere in a WIDE national column name (national sources are not
# compound-melted, so the qualifier is not split out into a cell — it stays in the header).
# Letter-only lookarounds (not \b): headers separate words with underscores, which are \w, so \b
# never fires at `_upto_`. This still refuses "till" inside "still".
_PARTIAL_COLUMN = re.compile(r"(?<![a-z])(?:up ?to|up ?til|till|as ?on|as ?of)(?![a-z])", re.I)


def _count_lakh_epsilon(value: Decimal) -> Decimal:
    """R4-REC-01a slack for a count published "in lakh": half the value's declared precision step.

    A lakh figure printed to k decimals resolves counts to a granularity of ``10**-k`` lakh =
    ``100_000 * 10**-k`` raw units, so any true count within HALF that step rounds to the same
    printed figure. Derived from the source's OWN precision — not a blanket tolerance. (2-dp lakh →
    1,000-unit granularity → ±500, matching the persondays ``RS_ROUNDING_EPSILON``.)
    """
    exponent = value.as_tuple().exponent
    if not isinstance(exponent, int):  # non-finite Decimal — no meaningful precision
        return Decimal(0)
    return Decimal(100_000) * Decimal(10) ** exponent / 2


def _normalize(value: Decimal, unit_kind: UnitKind) -> tuple[Decimal, str, Decimal]:
    """Normalize to the canonical unit; return (value, original_unit, rounding_epsilon).

    ``rounding_epsilon`` is the R4-REC-01a agreement slack: non-zero only for a count published in
    lakh (its lakh precision maps to a raw-count rounding step); exact raw counts and money (which
    reconciles on a % band) carry 0.
    """
    if unit_kind is UnitKind.MONEY_LAKH:
        out = to_canonical_lakh(value, MoneyUnit.LAKH)
        return out.value_lakh, out.original_unit, Decimal(0)  # type: ignore[return-value]  # non-None
    if unit_kind is UnitKind.COUNT_LAKH:
        out2 = to_raw_count(value, CountScale.LAKH)
        return out2.value, out2.original_unit, _count_lakh_epsilon(value)  # type: ignore[return-value]
    out3 = to_raw_count(value, CountScale.COUNT)
    return out3.value, out3.original_unit, Decimal(0)  # type: ignore[return-value]


def extract_national_wide(
    resolved: ResolvedBatch,
    cells: Cells,
    rules: tuple[StemRule, ...],
    *,
    fy_column: str,
    source_as_of: datetime | None,
    authority_rank: int,
) -> list[tuple[CanonicalKey, SourceValue]]:
    """Map a WIDE national source (one row per FY, one column per metric) to national SourceValues.

    ``fy_column`` names the financial-year column (the source's grain key). Each other column is
    matched against ``rules`` (after ``STEM_EXCLUDE``); the matching cell's value is normalized.
    """
    out: list[tuple[CanonicalKey, SourceValue]] = []
    for record in resolved.records:
        if record.geo_level is not GeoLevel.NATIONAL:
            continue
        row = cells[record.row_index]
        fin_year = row.get(fy_column)
        if not isinstance(fin_year, str):
            continue
        for column, raw in row.items():
            if column == fy_column or raw is None or STEM_EXCLUDE.search(column):
                continue
            if _PARTIAL_COLUMN.search(column):  # partial-year slice — a different period
                continue
            rule = next((r for r in rules if r.pattern.search(column)), None)
            if rule is None:
                continue
            try:
                value = Decimal(str(raw))
            except InvalidOperation:
                continue
            canonical_value, original_unit, epsilon = _normalize(value, rule.unit_kind)
            key = CanonicalKey(
                scheme="MGNREGA",
                geo_level=GeoLevel.NATIONAL,
                state_code=None,
                district_code=None,
                fin_year=fin_year,
                month=None,
                metric=rule.metric,
            )
            out.append(
                (
                    key,
                    SourceValue(
                        source_id=resolved.source_id,
                        value=canonical_value,
                        original_unit=original_unit,
                        source_as_of=source_as_of,
                        authority_rank=authority_rank,
                        rounding_epsilon=epsilon,
                    ),
                )
            )
    return out


def extract_historical_state(
    resolved: ResolvedBatch,
    cells: Cells,
    rules: tuple[StemRule, ...],
    *,
    source_as_of: datetime | None,
    authority_rank: int,
) -> list[tuple[CanonicalKey, SourceValue]]:
    """Map a resolved historical STATE batch to per-(state, FY, metric) SourceValues."""
    out: list[tuple[CanonicalKey, SourceValue]] = []
    for record in resolved.records:
        if record.state_canonical_id is None:
            continue
        row = cells[record.row_index]
        stem = row.get("_metric")
        fin_year = row.get("_fin_year")
        raw = row.get("_value")
        if not isinstance(stem, str) or not isinstance(fin_year, str) or raw is None:
            continue
        if row.get("_period_qualifier"):  # partial-year slice — a different period, never full-year
            continue
        if STEM_EXCLUDE.search(stem):
            continue
        rule = next((r for r in rules if r.pattern.search(stem)), None)
        if rule is None:
            continue
        try:
            value = Decimal(str(raw))
        except InvalidOperation:
            continue
        canonical_value, original_unit, epsilon = _normalize(value, rule.unit_kind)
        key = CanonicalKey(
            scheme="MGNREGA",
            geo_level=GeoLevel.STATE,
            state_code=record.state_canonical_id,
            district_code=None,
            fin_year=fin_year,
            month=None,
            metric=rule.metric,
        )
        out.append(
            (
                key,
                SourceValue(
                    source_id=resolved.source_id,
                    value=canonical_value,
                    original_unit=original_unit,
                    source_as_of=source_as_of,
                    authority_rank=authority_rank,
                    rounding_epsilon=epsilon,
                ),
            )
        )
    return _stamp_edition_markers(out, resolved.resource_id)
