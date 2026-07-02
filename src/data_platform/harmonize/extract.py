"""Source-specific extraction of the starter metric (persondays) to a common canonical grain.

The flagship and the Rajya Sabha person-days tables meet only at **state + annual**: the flagship
is district + monthly and cumulative-YTD, the RS tables are state + annual in lakh. To compare
them, each is brought to state-annual raw person-days here, tagged with the canonical key and the
source's authority rank; the assembler then reconciles across sources. These extractors encode the
grounded per-source facts (which column holds the metric, its unit, its shape) for the starter
slice — the per-resource metric-mapping config, kept explicit.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from decimal import Decimal, InvalidOperation

from data_platform.harmonize.config import PERSONDAYS_GENERATED
from data_platform.harmonize.models import CanonicalKey, SourceValue
from data_platform.harmonize.rollup import fy_final_of_cumulative
from data_platform.normalize.models import CleanCell
from data_platform.resolve.models import GeoLevel, ResolvedBatch

# Grounded per-source facts (sources.md §3, divergence-findings): the flagship persondays column
# (cumulative-YTD, raw person-days) and the melted RS value column (state-annual, in lakh).
FLAGSHIP_PERSONDAYS_COLUMN = "Persondays_of_Central_Liability_so_far"
RS_VALUE_COLUMN = "_value"
_LAKH = Decimal(100_000)

# Authority ranks (DATA_CONTRACT §3): the primary district-monthly flagship outranks the
# downstream state-annual RS summary for the periods the flagship covers.
FLAGSHIP_RANK = 0
RS_RANK = 1

Cells = dict[int, dict[str, CleanCell]]


def _state_annual_key(state_code: str, fin_year: str) -> CanonicalKey:
    return CanonicalKey(
        scheme="MGNREGA",
        geo_level=GeoLevel.STATE,
        state_code=state_code,
        district_code=None,
        fin_year=fin_year,
        month=None,
        metric=PERSONDAYS_GENERATED,
    )


def flagship_state_annual_persondays(
    resolved: ResolvedBatch, cells: Cells, *, source_as_of: datetime | None
) -> list[tuple[CanonicalKey, SourceValue]]:
    """Roll the flagship district-monthly cumulative persondays up to state-annual.

    Per district-year, the annual figure is the FY-final cumulative value (never the sum of
    monthlies); the state-annual figure is the sum of those district finals.
    """
    # (state, fin_year) -> district -> {month: cumulative persondays}
    monthly: dict[tuple[str, str], dict[str, dict[str, int]]] = defaultdict(
        lambda: defaultdict(dict)
    )
    for record in resolved.records:
        if record.state_canonical_id is None or record.district_canonical_id is None:
            continue
        row = cells[record.row_index]
        fin_year, month, value = (
            row.get("fin_year"),
            row.get("month"),
            row.get(FLAGSHIP_PERSONDAYS_COLUMN),
        )
        if isinstance(fin_year, str) and isinstance(month, str) and isinstance(value, int):
            monthly[(record.state_canonical_id, fin_year)][record.district_canonical_id][month] = (
                value
            )

    out: list[tuple[CanonicalKey, SourceValue]] = []
    for (state_code, fin_year), districts in monthly.items():
        total = Decimal(0)
        have_final = False
        for district_series in districts.values():
            final = fy_final_of_cumulative(district_series)
            if final is not None:
                total += Decimal(final[1])
                have_final = True
        if have_final:
            out.append(
                (
                    _state_annual_key(state_code, fin_year),
                    SourceValue(
                        source_id=resolved.source_id,
                        value=total,
                        original_unit="person-days",
                        source_as_of=source_as_of,
                        authority_rank=FLAGSHIP_RANK,
                    ),
                )
            )
    return out


def rs_state_annual_persondays(
    resolved: ResolvedBatch, cells: Cells, *, source_as_of: datetime | None
) -> list[tuple[CanonicalKey, SourceValue]]:
    """Convert the melted RS state-annual persondays (in lakh) to raw person-days."""
    out: list[tuple[CanonicalKey, SourceValue]] = []
    for record in resolved.records:
        if record.state_canonical_id is None:
            continue
        row = cells[record.row_index]
        fin_year, value = row.get("_fin_year"), row.get(RS_VALUE_COLUMN)
        if not isinstance(fin_year, str) or value is None:
            continue
        try:
            lakh = Decimal(str(value))
        except InvalidOperation:
            continue
        out.append(
            (
                _state_annual_key(record.state_canonical_id, fin_year),
                SourceValue(
                    source_id=resolved.source_id,
                    value=lakh * _LAKH,
                    original_unit="lakh",
                    source_as_of=source_as_of,
                    authority_rank=RS_RANK,
                ),
            )
        )
    return out
