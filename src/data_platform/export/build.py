"""Assemble the full canonical series over the local archive — the export's data source.

This mirrors the archive-gated harmonization fixtures EXACTLY (same public extractors + the same
``assemble_series`` engine), so the exported files carry the identical reconciled facts those tests
prove (4,216 state facts, 148 national facts). It adds one thing the fixtures do not: the flagship
**district drill-down** — district-annual FY-finals for the 8 additive metrics (which sum to the
state spine by construction) plus ``avg_wage_rate_per_day`` at its native district-monthly grain.

Impure (reads the archive); the flagship is loaded/normalized/resolved ONCE and reused across the
state rollup, the national rollup, and the district drill-down. The ``resource_map``
(``id(SourceValue) → resource_id``) is populated here as each source value is created, so the pure
records layer can emit genuine ``contributing_resource_ids`` (reconciliation lineage itself carries
only publisher-level ``source_id``). ``SourceValue`` identities survive assembly, so the map holds.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from data_platform.harmonize.config import (
    ACTIVE_WORKERS,
    ADMIN_EXPENDITURE,
    CANONICAL_UNIT,
    HOUSEHOLDS_COMPLETED_100_DAYS,
    HOUSEHOLDS_EMPLOYED,
    MATERIAL_SKILLED_EXPENDITURE,
    PERSONDAYS_GENERATED,
    TOTAL_EXPENDITURE,
    WAGES_EXPENDITURE,
)
from data_platform.harmonize.extract import (
    FLAGSHIP_CUMULATIVE_COLUMNS,
    FLAGSHIP_EXPENDITURE_COMPONENTS,
    FLAGSHIP_RANK,
    flagship_district_monthly_avg_wage,
    flagship_state_annual_cumulative,
    flagship_state_annual_persondays,
    flagship_state_annual_total_expenditure,
    roll_to_national,
)
from data_platform.harmonize.historical import (
    HISTORICAL_NATIONAL_SOURCES,
    HISTORICAL_STATE_SOURCES,
    extract_historical_state,
    extract_national_wide,
)
from data_platform.harmonize.models import CanonicalKey, SourceValue
from data_platform.harmonize.rollup import fy_final_of_cumulative
from data_platform.harmonize.series import SeriesFact, assemble_series
from data_platform.ingest.archive import read_archive_batch
from data_platform.ingest.registry import FLAGSHIP_RESOURCE_ID, SRC_FLAGSHIP
from data_platform.normalize.config import NORMALIZE_CONFIG
from data_platform.normalize.models import CleanCell, NormalizedBatch
from data_platform.normalize.pipeline import normalize_batch
from data_platform.resolve.config import RESOLVE_CONFIG
from data_platform.resolve.geo import GeoResolver
from data_platform.resolve.lgd import load_lgd_reference
from data_platform.resolve.models import GeoLevel, ResolvedBatch
from data_platform.resolve.pipeline import resolve_batch
from data_platform.wiring.specs import WIRED

Cells = dict[int, dict[str, CleanCell]]
_KeyedValue = tuple[CanonicalKey, SourceValue]
_HISTORICAL_RANK = 10

# The six flagship metrics rolled up via the plain cumulative rollup (persondays + total handled
# separately). Matches the harmonization integration fixture's ``_STATE_ANNUAL_METRICS``.
_FLAGSHIP_ROLLUP_METRICS = (
    HOUSEHOLDS_EMPLOYED,
    HOUSEHOLDS_COMPLETED_100_DAYS,
    ACTIVE_WORKERS,
    WAGES_EXPENDITURE,
    MATERIAL_SKILLED_EXPENDITURE,
    ADMIN_EXPENDITURE,
)
# The 7 additive metrics whose district-annual value is a single cumulative column's FY-final.
_DISTRICT_DIRECT_METRICS = (*_FLAGSHIP_ROLLUP_METRICS, PERSONDAYS_GENERATED)


@dataclass(frozen=True)
class ExportBundle:
    """Everything the writer needs: the three fact sets, the resource map, and the name maps."""

    state_facts: list[SeriesFact]
    national_facts: list[SeriesFact]
    district_facts: list[SeriesFact]
    resource_map: dict[int, str]
    state_names: dict[str, str]
    district_names: dict[tuple[str, str], str]


def _cells(batch: NormalizedBatch) -> Cells:
    return {r.row_index: dict(r.cells) for r in batch.records}


def _as_decimal(cell: CleanCell) -> Decimal | None:
    """Coerce a cleaned flagship cell to Decimal (numeric strings / Decimals), else None."""
    if isinstance(cell, Decimal | int):
        return Decimal(cell)
    if isinstance(cell, str):
        try:
            return Decimal(cell)
        except ArithmeticError:
            return None
    return None


def _resolver(archive: Path) -> GeoResolver:
    states, districts = load_lgd_reference(
        archive / "lgd" / "lgd_states.json", archive / "lgd" / "lgd_districts.json"
    )
    return GeoResolver.from_reference(states=states, districts=districts)


def _lgd_district_counts(archive: Path) -> dict[str, int]:
    records = json.loads((archive / "lgd" / "lgd_districts.json").read_text())["records"]
    return dict(Counter(str(r["state_code"]) for r in records))


def _name_maps(archive: Path) -> tuple[dict[str, str], dict[tuple[str, str], str]]:
    states, districts = load_lgd_reference(
        archive / "lgd" / "lgd_states.json", archive / "lgd" / "lgd_districts.json"
    )
    state_names = {s.code: s.name for s in states}
    district_names = {(d.state_code, d.code): d.name for d in districts}
    return state_names, district_names


def _full_resource_id(prefix: str) -> str:
    return next(r for r in WIRED if r.startswith(prefix))


def _tag(
    keyed: list[_KeyedValue], resource_id: str, resource_map: dict[int, str]
) -> list[_KeyedValue]:
    """Record each new source value's origin resource id, then return the keyed list unchanged."""
    for _key, source_value in keyed:
        resource_map[id(source_value)] = resource_id
    return keyed


def _flagship_resolved(
    archive: Path, resolver: GeoResolver
) -> tuple[ResolvedBatch, Cells, datetime | None]:
    """Load + normalize + resolve the flagship once (reused for state / national / district)."""
    batch = read_archive_batch(
        resource_id=FLAGSHIP_RESOURCE_ID,
        source_id=SRC_FLAGSHIP,
        source_grain="district+monthly",
        path=archive / f"{FLAGSHIP_RESOURCE_ID}.json",
    )
    normalized = normalize_batch(batch, config=NORMALIZE_CONFIG[FLAGSHIP_RESOURCE_ID])
    resolved = resolve_batch(normalized, resolver, config=RESOLVE_CONFIG[FLAGSHIP_RESOURCE_ID])
    return resolved, _cells(normalized), batch.source_as_of


def _flagship_state_annual(
    resolved: ResolvedBatch, cells: Cells, source_as_of: datetime | None, lgd: dict[str, int]
) -> list[_KeyedValue]:
    """All flagship state-annual values (2018+ era), across the 8 canonical metrics."""
    keyed: list[_KeyedValue] = []
    for metric in _FLAGSHIP_ROLLUP_METRICS:
        keyed += flagship_state_annual_cumulative(
            resolved, cells, metric=metric, source_as_of=source_as_of, lgd_district_counts=lgd
        )
    keyed += flagship_state_annual_persondays(
        resolved, cells, source_as_of=source_as_of, lgd_district_counts=lgd
    )
    keyed += flagship_state_annual_total_expenditure(
        resolved, cells, source_as_of=source_as_of, lgd_district_counts=lgd
    )
    return keyed


def _load_wired(
    archive: Path, resolver: GeoResolver, prefix: str
) -> tuple[ResolvedBatch, Cells, datetime | None, str]:
    """Load one wired historical source to (resolved, cells, source_as_of, resource_id)."""
    rid = _full_resource_id(prefix)
    spec = WIRED[rid]
    batch = read_archive_batch(
        resource_id=rid,
        source_id=spec.source_id,
        source_grain=spec.source_grain,
        path=archive / spec.file,
    )
    normalized = normalize_batch(batch, config=spec.normalize_config)
    resolved = resolve_batch(normalized, resolver, config=spec.resolve_config)
    return resolved, _cells(normalized), batch.source_as_of, rid


def _district_fy_finals(
    resolved: ResolvedBatch, cells: Cells, column: str
) -> dict[tuple[str, str, str], Decimal]:
    """FY-final cumulative value per (state, district, fin_year) for one flagship column."""
    monthly: dict[tuple[str, str, str], dict[str, Decimal]] = defaultdict(dict)
    for record in resolved.records:
        if record.state_canonical_id is None or record.district_canonical_id is None:
            continue
        row = cells[record.row_index]
        fin_year, month = row.get("fin_year"), row.get("month")
        value = _as_decimal(row.get(column))
        if isinstance(fin_year, str) and isinstance(month, str) and value is not None:
            key = (record.state_canonical_id, record.district_canonical_id, fin_year)
            monthly[key][month] = value
    finals: dict[tuple[str, str, str], Decimal] = {}
    for key, series in monthly.items():
        final = fy_final_of_cumulative(series)
        if final is not None:
            finals[key] = final[1]
    return finals


def _district_key(state: str, district: str, fin_year: str, metric: str) -> CanonicalKey:
    return CanonicalKey(
        scheme="MGNREGA",
        geo_level=GeoLevel.DISTRICT,
        state_code=state,
        district_code=district,
        fin_year=fin_year,
        month=None,
        metric=metric,
    )


def _district_source_value(
    value: Decimal, metric: str, source_as_of: datetime | None
) -> SourceValue:
    return SourceValue(
        source_id=SRC_FLAGSHIP,
        value=value,
        original_unit=CANONICAL_UNIT[metric],
        source_as_of=source_as_of,
        authority_rank=FLAGSHIP_RANK,
    )


def _flagship_district_annual(
    resolved: ResolvedBatch, cells: Cells, source_as_of: datetime | None
) -> list[_KeyedValue]:
    """District-annual FY-finals for the 8 additive metrics (7 direct + derived total).

    Each direct metric is one cumulative column's district FY-final; total_expenditure is the sum of
    the three component finals per district. By construction the district-annual values for a
    (state, FY, metric) sum to the flagship state-annual rollup for that cell.
    """
    keyed: list[_KeyedValue] = []
    for metric in _DISTRICT_DIRECT_METRICS:
        for (state, district, fin_year), value in _district_fy_finals(
            resolved, cells, FLAGSHIP_CUMULATIVE_COLUMNS[metric]
        ).items():
            keyed.append(
                (
                    _district_key(state, district, fin_year, metric),
                    _district_source_value(value, metric, source_as_of),
                )
            )

    component_finals = [
        _district_fy_finals(resolved, cells, column) for column in FLAGSHIP_EXPENDITURE_COMPONENTS
    ]
    district_years = {key for finals in component_finals for key in finals}
    for state, district, fin_year in district_years:
        total = sum(
            (finals.get((state, district, fin_year), Decimal(0)) for finals in component_finals),
            Decimal(0),
        )
        keyed.append(
            (
                _district_key(state, district, fin_year, TOTAL_EXPENDITURE),
                _district_source_value(total, TOTAL_EXPENDITURE, source_as_of),
            )
        )
    return keyed


def build_export(archive: Path) -> ExportBundle:
    """Assemble the state spine, national spine, and district drill-down over the local archive."""
    resolver = _resolver(archive)
    lgd = _lgd_district_counts(archive)
    state_names, district_names = _name_maps(archive)
    resource_map: dict[int, str] = {}

    flagship_resolved, flagship_cells, flagship_as_of = _flagship_resolved(archive, resolver)
    flagship_state = _tag(
        _flagship_state_annual(flagship_resolved, flagship_cells, flagship_as_of, lgd),
        FLAGSHIP_RESOURCE_ID,
        resource_map,
    )

    # --- STATE spine: flagship (2018+) + every wired historical state source (pre-2018) ----------
    state_keyed = list(flagship_state)
    for prefix, rules in HISTORICAL_STATE_SOURCES:
        resolved, cells, as_of, rid = _load_wired(archive, resolver, prefix)
        state_keyed += _tag(
            extract_historical_state(
                resolved, cells, rules, source_as_of=as_of, authority_rank=_HISTORICAL_RANK
            ),
            rid,
            resource_map,
        )
    state_facts = assemble_series(state_keyed, flagship_source_id=SRC_FLAGSHIP)

    # --- NATIONAL spine: flagship rolled to national + wired historical national sources ---------
    national_keyed = _tag(
        roll_to_national(flagship_state, source_id=SRC_FLAGSHIP, authority_rank=FLAGSHIP_RANK),
        FLAGSHIP_RESOURCE_ID,
        resource_map,
    )
    for prefix, rules in HISTORICAL_NATIONAL_SOURCES:
        resolved, cells, as_of, rid = _load_wired(archive, resolver, prefix)
        national_keyed += _tag(
            extract_national_wide(
                resolved,
                cells,
                rules,
                fy_column=WIRED[rid].normalize_config.grain_key_columns[0],
                source_as_of=as_of,
                authority_rank=_HISTORICAL_RANK,
            ),
            rid,
            resource_map,
        )
    national_facts = assemble_series(national_keyed, flagship_source_id=SRC_FLAGSHIP)

    # --- DISTRICT drill-down: district-annual additive metrics + native district-monthly wage ----
    district_keyed = _tag(
        _flagship_district_annual(flagship_resolved, flagship_cells, flagship_as_of),
        FLAGSHIP_RESOURCE_ID,
        resource_map,
    )
    district_keyed += _tag(
        flagship_district_monthly_avg_wage(
            flagship_resolved, flagship_cells, source_as_of=flagship_as_of
        ),
        FLAGSHIP_RESOURCE_ID,
        resource_map,
    )
    district_facts = assemble_series(district_keyed, flagship_source_id=SRC_FLAGSHIP)

    return ExportBundle(
        state_facts=state_facts,
        national_facts=national_facts,
        district_facts=district_facts,
        resource_map=resource_map,
        state_names=state_names,
        district_names=district_names,
    )
