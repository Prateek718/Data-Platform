"""Stage 3.5 — grain-aware resolve: national and state paths + peer-count metadata.

The flagship district path is covered in ``test_pipeline.py``; here we cover the two grains wired
in Stage 3.5. National rows carry NO LGD code (a ragged hierarchy resolved at the level published;
never a sentinel — R3-GEO-04). State rows resolve the state name only, with district ``None`` and
no district required. ``sources_seen`` is peer-count, driven by peer count alone — never by a
source's A/B destination label.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from data_platform.normalize.models import (
    CleanCell,
    DedupeLineage,
    NormalizationLineage,
    NormalizedBatch,
    NormalizedRecord,
)
from data_platform.resolve.config import GeoColumns, ResourceResolveConfig
from data_platform.resolve.geo import GeoResolver
from data_platform.resolve.lgd import LGDState
from data_platform.resolve.models import GeoLevel, ResolutionQuarantineReason
from data_platform.resolve.pipeline import resolve_batch

_RESOLVER = GeoResolver.from_reference(
    states=[
        LGDState(code="30", name="Goa"),
        LGDState(code="35", name="Andaman and Nicobar Islands"),
    ],
    districts=[],
)

_NATIONAL_CFG = ResourceResolveConfig(geo_level=GeoLevel.NATIONAL, scheme_label="MGNREGA")
_STATE_CFG = ResourceResolveConfig(
    geo_level=GeoLevel.STATE,
    scheme_label="MGNREGA",
    geo_columns=GeoColumns(state_name="state_ut"),
)


def _batch(*records: NormalizedRecord, resource_id: str = "RES_TEST") -> NormalizedBatch:
    return NormalizedBatch(
        source_id="SRC_TEST",
        resource_id=resource_id,
        ingested_at=datetime(2026, 6, 25, 12, 0, tzinfo=UTC),
        source_as_of=None,
        schema_version="v1",
        source_grain="test",
        pull_completeness="full",
        column_names=["state_ut", "_fin_year", "_value"],
        records=list(records),
        quarantined=[],
        dedupe=DedupeLineage(
            duplicates_collapsed=0, collapsed_row_indexes=[], tie_break_rule_id="x"
        ),
    )


def _record(row_index: int, **cells: CleanCell) -> NormalizedRecord:
    return NormalizedRecord(
        row_index=row_index, cells=cells, normalization=NormalizationLineage(per_column={})
    )


def test_national_row_resolves_with_no_lgd_code_and_no_geo_resolution() -> None:
    batch = _batch(_record(0, _fin_year="2006-07", _value=9051))
    out = resolve_batch(batch, _RESOLVER, config=_NATIONAL_CFG)
    assert out.quarantined == []
    rec = out.records[0]
    assert rec.geo_level is GeoLevel.NATIONAL
    # No LGD code exists at national level — honest None, never a sentinel/pseudo-code.
    assert rec.state_canonical_id is None
    assert rec.district_canonical_id is None
    assert rec.state_canonical_name is None
    assert rec.district_canonical_name is None
    assert rec.geo_resolution is None
    assert rec.scheme_canonical_id == "MGNREGA"


def test_national_path_never_writes_a_sentinel_code() -> None:
    batch = _batch(
        _record(0, _fin_year="2010-11", _value=1), _record(1, _fin_year="2011-12", _value=2)
    )
    out = resolve_batch(batch, _RESOLVER, config=_NATIONAL_CFG)
    for rec in out.records:
        assert rec.state_canonical_id is None and rec.district_canonical_id is None


def test_state_row_resolves_state_with_no_district_required() -> None:
    batch = _batch(_record(0, state_ut="GOA", _fin_year="2019-20", _value=42))
    out = resolve_batch(batch, _RESOLVER, config=_STATE_CFG)
    assert out.quarantined == []
    rec = out.records[0]
    assert rec.geo_level is GeoLevel.STATE
    assert rec.state_canonical_id == "30"
    assert rec.state_canonical_name == "Goa"
    assert rec.district_canonical_id is None
    assert rec.district_canonical_name is None
    assert rec.geo_resolution is not None
    assert rec.geo_resolution.district is None
    assert rec.geo_resolution.state.source_name == "GOA"  # input alias preserved in lineage
    assert rec.geo_resolution.state.lgd_code == "30"


def test_state_name_variant_resolves_via_alias_path() -> None:
    # "Andaman and Nicobar" (no "Islands") is not the exact LGD English name; the existing alias
    # table bridges it — proving the state-grain path reuses the same R3-GEO-03 alias machinery.
    batch = _batch(_record(0, state_ut="Andaman and Nicobar", _fin_year="2019-20", _value=1))
    out = resolve_batch(batch, _RESOLVER, config=_STATE_CFG)
    assert out.quarantined == []
    rec = out.records[0]
    assert rec.state_canonical_id == "35"
    assert rec.geo_resolution is not None
    assert rec.geo_resolution.state.rule_id.startswith("R3-GEO-03")


def test_unresolved_state_is_quarantined_not_guessed() -> None:
    batch = _batch(_record(0, state_ut="ATLANTIS", _fin_year="2019-20", _value=1))
    out = resolve_batch(batch, _RESOLVER, config=_STATE_CFG)
    assert out.records == []
    assert out.quarantined[0].reason is ResolutionQuarantineReason.UNRESOLVED_GEOGRAPHY


def test_sources_seen_is_peer_count_not_the_ab_label() -> None:
    # A "coverage-only A" dataset and a "subject-unique B" dataset both have exactly one source
    # for the fact here, so both must report sources_seen=1 — the label never leaks into it.
    a = resolve_batch(_batch(_record(0, state_ut="GOA")), _RESOLVER, config=_STATE_CFG)
    b = resolve_batch(
        _batch(_record(0, _fin_year="2006-07", _value=1)), _RESOLVER, config=_NATIONAL_CFG
    )
    assert a.records[0].sources_seen == 1
    assert b.records[0].sources_seen == 1


# ---------------------------------------------------------------------------------------
# Stage 3.5 quarantine-recovery — real states/UTs that failed on fixable normalization gaps
# (ampersand-vs-"and", old spellings) must now resolve; genuinely-historical entities absent
# from the current LGD must NOT (never forward-map across a reorganization — R3-SET-02).
# ---------------------------------------------------------------------------------------
_RECOVERY_RESOLVER = GeoResolver.from_reference(
    states=[
        LGDState(code="1", name="Jammu and Kashmir"),
        LGDState(code="5", name="Uttarakhand"),
        LGDState(code="11", name="Sikkim"),
        LGDState(code="21", name="Odisha"),
        LGDState(code="33", name="Tamil Nadu"),
        LGDState(code="34", name="Puducherry"),
        LGDState(code="35", name="Andaman and Nicobar Islands"),
        LGDState(code="38", name="The Dadra and Nagar Haveli and Daman and Diu"),
    ],
    districts=[],
)


@pytest.mark.parametrize(
    ("name", "code"),
    [
        ("Jammu & Kashmir", "1"),  # ampersand form of a current state
        ("JAMMU & KASHMIR", "1"),  # case-insensitive across the &->and change
        ("Andaman & Nicobar", "35"),  # ampersand + LGD "Islands" suffix (via alias)
        ("ANDAMAN & NICOBAR", "35"),
        ("Andaman & Nicobar Islands", "35"),  # ampersand, exact once &->and
        ("Orissa", "21"),  # old spelling -> current LGD name
        ("ORISSA", "21"),
        ("Uttrakhand", "5"),
        ("Tamilnadu", "33"),
        ("Pondicherry", "34"),
    ],
)
def test_variant_state_names_resolve_to_current_lgd(name: str, code: str) -> None:
    match = _RECOVERY_RESOLVER.resolve_state(name)
    assert match is not None, f"{name!r} should resolve, not quarantine"
    assert match.code == code


@pytest.mark.parametrize(
    "name",
    [
        "Daman & Diu",  # pre-2020 standalone UT, merged away — absent from current LGD
        "Dadra & Nagar Haveli",  # pre-2020 standalone UT, merged away
        "EAST DISTRICT",  # old Sikkim district name (renamed) — not a state anyway
        "NORTH DISTRICT",
        "Total",  # pseudo/roll-up row
        "None",  # null-ish artifact
    ],
)
def test_historical_or_pseudo_names_do_not_resolve_as_state(name: str) -> None:
    assert _RECOVERY_RESOLVER.resolve_state(name) is None


def test_two_pre_merger_uts_do_not_collide_onto_merged_code() -> None:
    # The never-forward-map rule: two separate pre-2020 rows must NOT both map onto the single
    # merged UT (LGD 38). Neither resolves; only the full modern merged name reaches code 38.
    assert _RECOVERY_RESOLVER.resolve_state("Daman & Diu") is None
    assert _RECOVERY_RESOLVER.resolve_state("Dadra & Nagar Haveli") is None
    merged = _RECOVERY_RESOLVER.resolve_state("The Dadra and Nagar Haveli and Daman and Diu")
    assert merged is not None and merged.code == "38"
