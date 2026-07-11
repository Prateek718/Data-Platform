"""End-to-end export over the real archive — the deterministic-artifact proof.

Builds the full series, writes the deliverables, and asserts: the documented row counts
(state 4,219 / national 148); the CSV↔lineage join on fact_id; byte-identical repeated runs
(CSV + JSONL + Parquet); the district-annual decomposition (Σ district = state spine, structural-gap
cells checked not skipped, unadjudicated + peer-only cells accounted); the pre-2018 headline facts
(4 cross-publisher disagreements, 3 unadjudicated national persondays, 472 edition-superseded);
and the flagship-era RS-peer reconciliation (corroboration / flagged / unadjudicated); null≠0.

Skips when the gitignored archive snapshot is absent; parquet assertions skip if pyarrow is absent.
"""

from __future__ import annotations

import json
from collections import defaultdict
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import pytest

from data_platform.export.build import ExportBundle, build_export
from data_platform.export.records import DISTRICT_COLUMNS, NATIONAL_COLUMNS, STATE_COLUMNS
from data_platform.export.write import write_all
from data_platform.harmonize.models import CoverageStatus
from data_platform.harmonize.series import Confidence, SeriesFact
from data_platform.ingest.registry import FLAGSHIP_RESOURCE_ID
from data_platform.resolve.models import GeoLevel

ARCHIVE = Path(__file__).resolve().parents[2] / "data" / "archive"
_Written = tuple[Path, Path, dict[str, int]]

pytestmark = pytest.mark.skipif(
    not (ARCHIVE / f"{FLAGSHIP_RESOURCE_ID}.json").exists(),
    reason="local archive snapshot not present",
)

_ADDITIVE = {
    "households_employed",
    "households_completed_100_days",
    "active_workers",
    "persondays_generated",
    "wages_expenditure",
    "material_skilled_expenditure",
    "admin_expenditure",
    "total_expenditure",
}


@pytest.fixture(scope="module")
def bundle() -> ExportBundle:
    return build_export(ARCHIVE)


@pytest.fixture(scope="module")
def written(bundle: ExportBundle, tmp_path_factory: pytest.TempPathFactory) -> _Written:
    d1 = tmp_path_factory.mktemp("dist_a")
    d2 = tmp_path_factory.mktemp("dist_b")
    counts = write_all(d1, bundle)
    write_all(d2, bundle)
    return d1, d2, counts


def _name_to_code(bundle: ExportBundle) -> dict[str, str]:
    return {name: code for code, name in bundle.state_names.items()}


# --- documented row counts ----------------------------------------------------------------------


def test_state_spine_matches_documented_shape(bundle: ExportBundle) -> None:
    metrics = {f.key.metric for f in bundle.state_facts}
    years = {f.key.fin_year for f in bundle.state_facts}
    states = {f.key.state_code for f in bundle.state_facts}
    assert len(bundle.state_facts) == 4219  # 4216 flagship-anchored + 3 RS-only (Telangana)
    assert metrics == _ADDITIVE
    assert min(years) == "2010-11" and max(years) == "2026-27"
    assert len(states) == 35


def test_national_spine_matches_documented_shape(bundle: ExportBundle) -> None:
    assert len(bundle.national_facts) == 148
    years = sorted(f.key.fin_year for f in bundle.national_facts)
    assert years[0] == "2006-07" and years[-1] == "2026-27"
    for f in bundle.national_facts:
        assert f.key.geo_level is GeoLevel.NATIONAL
        assert f.key.state_code is None and f.key.district_code is None
    exp_years = sorted(
        f.key.fin_year for f in bundle.national_facts if f.key.metric == "wages_expenditure"
    )
    assert exp_years[0] == "2008-09"  # national financial sources begin 2008-09


def test_district_drilldown_is_single_grain_district_annual(bundle: ExportBundle) -> None:
    # avg_wage_rate is a cumulative-YTD ratio (Wages ÷ persondays), so its FY-final value IS the
    # annual rate and it is published at DISTRICT-ANNUAL grain like the additive metrics — the raw
    # monthly YTD ratios are NOT exported. district_flagship is therefore single-grain.
    monthly = [f for f in bundle.district_facts if f.key.month is not None]
    assert monthly == []  # no monthly-grain facts are exported
    annual = [f for f in bundle.district_facts if f.key.month is None]
    assert {f.key.metric for f in annual} == _ADDITIVE | {"avg_wage_rate_per_day"}  # 9 metrics
    additive = [f for f in annual if f.key.metric in _ADDITIVE]
    wage = [f for f in annual if f.key.metric == "avg_wage_rate_per_day"]
    assert len(additive) == 51536
    assert len(wage) == 5645  # FY-final rate per COMPLETE-FY district-year (March final, pd > 0)
    # the rate is NOT forced into the state spine (it does not sum to a state annual)
    assert "avg_wage_rate_per_day" not in {f.key.metric for f in bundle.state_facts}


def test_anantnag_2018_19_avg_wage_is_fy_final_annual(bundle: ExportBundle) -> None:
    # Verified identity: Average_Wage_rate = cumulative Wages(lakh)·1e5 / cumulative persondays; the
    # FY-final (March) value IS the annual average wage rate. Anantnag FY2018-19: 540,957,654 /
    # 5,232,066 = 103.39274 — published once at annual grain, not as 12 monthly YTD ratios.
    names = bundle.district_names
    hits = [
        f
        for f in bundle.district_facts
        if f.key.metric == "avg_wage_rate_per_day"
        and f.key.fin_year == "2018-19"
        and names.get((f.key.state_code or "", f.key.district_code or ""), "").upper() == "ANANTNAG"
    ]
    assert len(hits) == 1
    assert hits[0].key.month is None  # annual grain, not one row per month
    assert hits[0].value == Decimal("103.392742752098")  # FY-final = 103.39274 (5dp)


def test_no_wage_facts_for_permanently_partial_2026_27(bundle: ExportBundle) -> None:
    # avg_wage is a cumulative-YTD ratio → a genuine annual rate only for a COMPLETE FY (March). FY
    # 2026-27 is April-only and PERMANENTLY partial (MGNREGA repealed 30 Jun 2026, so it never
    # completes); its arrears-contaminated ratio is not an annual rate → no wage fact for it.
    wage_2026 = [
        f
        for f in bundle.district_facts
        if f.key.metric == "avg_wage_rate_per_day" and f.key.fin_year == "2026-27"
    ]
    assert wage_2026 == []
    # the ADDITIVE metrics still cover 2026-27 (only the rate is gated on a complete FY)
    additive_2026 = [
        f
        for f in bundle.district_facts
        if f.key.metric in _ADDITIVE and f.key.fin_year == "2026-27"
    ]
    assert additive_2026


# --- files, join, determinism -------------------------------------------------------------------


def test_csv_row_counts_match_assembled_series(written: _Written) -> None:
    d1, _d2, counts = written
    assert counts["state_annual_series"] == 4219
    assert counts["national_annual_series"] == 148
    assert counts["district_flagship"] == 57181  # 51,536 additive + 5,645 complete-FY wage
    assert counts["lineage"] == 4219 + 148 + 57181

    def data_rows(path: Path) -> int:
        return len(path.read_text().splitlines()) - 1  # minus header

    assert data_rows(d1 / "state_annual_series.csv") == 4219
    assert data_rows(d1 / "national_annual_series.csv") == 148
    assert data_rows(d1 / "district_flagship.csv") == 57181


def test_every_fact_id_joins_csv_to_lineage_exactly_once(written: _Written) -> None:
    d1, _d2, _counts = written
    lineage_ids = [
        json.loads(line)["fact_id"] for line in (d1 / "lineage.jsonl").read_text().splitlines()
    ]
    assert len(lineage_ids) == len(set(lineage_ids)) == 61548  # unique, one per exported fact

    csv_ids: set[str] = set()
    for name, columns in (
        ("state_annual_series.csv", STATE_COLUMNS),
        ("national_annual_series.csv", NATIONAL_COLUMNS),
        ("district_flagship.csv", DISTRICT_COLUMNS),
    ):
        idx = columns.index("fact_id")
        rows = (d1 / name).read_text().splitlines()[1:]
        csv_ids |= {r.split(",")[idx] for r in rows}
    assert csv_ids == set(lineage_ids)  # exact CSV↔lineage correspondence


def test_repeated_runs_are_byte_identical(written: _Written) -> None:
    d1, d2, _counts = written
    names = [
        "state_annual_series.csv",
        "national_annual_series.csv",
        "district_flagship.csv",
        "lineage.jsonl",
    ]
    if (d1 / "state_annual_series.parquet").exists():  # pyarrow installed
        names += [
            "state_annual_series.parquet",
            "national_annual_series.parquet",
            "district_flagship.parquet",
        ]
    for name in names:
        assert (d1 / name).read_bytes() == (d2 / name).read_bytes(), f"non-deterministic: {name}"


# --- decomposition (district-annual sums to the state spine) ------------------------------------


def test_district_annual_decomposes_the_state_spine(bundle: ExportBundle) -> None:
    dsum: dict[tuple[str, str, str], Decimal] = defaultdict(lambda: Decimal(0))
    for f in bundle.district_facts:
        if f.key.month is None and f.value is not None:
            dsum[(f.key.state_code or "", f.key.fin_year, f.key.metric)] += f.value

    checked = 0
    structural_gap = 0
    unadjudicated = 0
    peer_only = 0
    for f in bundle.state_facts:
        if f.key.fin_year < "2018" or f.key.metric not in _ADDITIVE:
            continue
        flagship = next(
            (s for s in f.reconciliation.sources_seen if s.source_id == "SRC_FLAGSHIP"), None
        )
        if flagship is None:
            # a flagship-era RS peer filled a year the flagship lacks (Telangana 2019-20 persondays)
            # — a real single-source fact, no flagship districts to decompose to
            peer_only += 1
            assert f.value is not None
            continue
        # every flagship-anchored 2018+ cell exposes its coverage descriptor (never silently absent)
        assert flagship.aggregate_coverage is not None
        if f.value is None:
            # structural-gap flagship + material RS disagreement → unadjudicated (not summed)
            assert f.confidence is Confidence.UNADJUDICATED
            unadjudicated += 1
            continue
        checked += 1
        got = dsum[(f.key.state_code or "", f.key.fin_year, f.key.metric)]
        assert abs(float(f.value) - float(got)) <= 1.0, f"{f.key} state={f.value} Σdistrict={got}"
        if flagship.aggregate_coverage.status is CoverageStatus.STRUCTURAL_GAP:
            structural_gap += 1
    assert checked == 2422
    assert structural_gap == 622  # structurally-incomplete cells still decompose exactly
    assert unadjudicated == 10  # structural-gap + material RS disagreement → value withheld
    assert peer_only == 3  # Telangana RS-only (persondays 2019-20; total_exp + hh_100d 2018-19)


# --- headline reconciliation facts (verified, at scope) -----------------------------------------


def test_pre_2018_cross_publisher_disagreements(bundle: ExportBundle) -> None:
    # PRE-2018 pin. Two metrics carry genuine cross-publisher disagreements pre-2018: the four
    # households_employed cells (a MoSPI edition vs an RS answer) and five total_expenditure cells
    # (the RS expenditure table 57bff16a made RS an independent publisher on expenditure). Both are
    # MoSPI vs RS. Flagship-era (2018+) flagged sets are pinned separately (the peer tests below).
    name = dict(bundle.state_names)
    flagged: dict[str, set[tuple[str | None, str]]] = defaultdict(set)
    for f in bundle.state_facts:
        if f.key.fin_year < "2018" and f.confidence is Confidence.FLAGGED_DISAGREEMENT:
            state = name.get(f.key.state_code or "", f.key.state_code)
            flagged[f.key.metric].add((state, f.key.fin_year))
    assert set(flagged) == {"households_employed", "total_expenditure"}
    assert flagged["households_employed"] == {
        ("Bihar", "2015-16"),
        ("Mizoram", "2013-14"),
        ("Telangana", "2014-15"),
        ("Andaman And Nicobar Islands", "2014-15"),
    }
    assert flagged["total_expenditure"] == {
        ("Andhra Pradesh", "2014-15"),
        ("Andhra Pradesh", "2015-16"),
        ("Bihar", "2014-15"),
        ("Jammu And Kashmir", "2016-17"),
        ("Telangana", "2016-17"),
    }
    # every pre-2018 flagged cell is genuinely two independent publishers (MoSPI + RS)
    for f in bundle.state_facts:
        if f.key.fin_year < "2018" and f.confidence is Confidence.FLAGGED_DISAGREEMENT:
            publishers = {s.source_id for s in f.reconciliation.sources_seen}
            assert {"SRC_MOSPI", "SRC_RS"} <= publishers
    # the documented households_employed divergence percentages (DATA_DICTIONARY §8 / README)
    pct: dict[tuple[str | None, str], Decimal] = {}
    for f in bundle.state_facts:
        if (
            f.key.fin_year >= "2018"
            or f.key.metric != "households_employed"
            or f.confidence is not Confidence.FLAGGED_DISAGREEMENT
        ):
            continue
        disagreement = f.reconciliation.disagreement
        assert disagreement is not None
        cell = (name.get(f.key.state_code or "", f.key.state_code), f.key.fin_year)
        pct[cell] = disagreement.pct.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
    assert pct == {
        ("Bihar", "2015-16"): Decimal("4.2"),
        ("Mizoram", "2013-14"): Decimal("3.1"),
        ("Telangana", "2014-15"): Decimal("1.3"),
        ("Andaman And Nicobar Islands", "2014-15"): Decimal("7.7"),
    }


# --- flagship-era peer reconciliation (RS persondays tables cea6ee41 + e289a8fe) ----------------
# The two RS state persondays tables Stage 4 uses are peers to the flagship rollup. The three
# outcome classes the assembly design requires, each pinned on a real cell:


def _state_fact(bundle: ExportBundle, state: str, fin_year: str, metric: str) -> SeriesFact:
    code = _name_to_code(bundle)[state]
    hits = [
        f
        for f in bundle.state_facts
        if f.key.state_code == code and f.key.fin_year == fin_year and f.key.metric == metric
    ]
    assert len(hits) == 1, f"{state} {fin_year} {metric}: {len(hits)} facts"
    return hits[0]


def test_maharashtra_2023_24_persondays_unadjudicated_structural_gap(bundle: ExportBundle) -> None:
    # flagship 34/36 districts (STRUCTURAL_GAP) vs a native RS peer that materially disagrees
    # (~+19.6%) → no winner is invented: value withheld, every reading kept in lineage.
    f = _state_fact(bundle, "Maharashtra", "2023-24", "persondays_generated")
    assert f.value is None
    assert f.confidence is Confidence.UNADJUDICATED
    assert f.reconciliation.resolution_rule_id == "R4-REC-05"
    publishers = {s.source_id for s in f.reconciliation.sources_seen}
    assert {"SRC_FLAGSHIP", "SRC_RS"} <= publishers  # the RS peer is recorded, not dropped
    flagship = next(s for s in f.reconciliation.sources_seen if s.source_id == "SRC_FLAGSHIP")
    assert flagship.aggregate_coverage is not None
    assert flagship.aggregate_coverage.status is CoverageStatus.STRUCTURAL_GAP


def test_goa_2022_23_persondays_cross_publisher_corroboration(bundle: ExportBundle) -> None:
    # flagship complete-coverage FY-final 94,004 and the RS peer's 94,000 agree within the RS
    # table's lakh precision → two independent publishers corroborate.
    f = _state_fact(bundle, "Goa", "2022-23", "persondays_generated")
    assert f.value == Decimal("94004")  # flagship FY-final retained
    assert f.confidence is Confidence.CROSS_PUBLISHER
    publishers = {s.source_id for s in f.reconciliation.sources_seen}
    assert {"SRC_FLAGSHIP", "SRC_RS"} <= publishers


def test_odisha_2023_24_persondays_complete_coverage_flagged(bundle: ExportBundle) -> None:
    # flagship complete-coverage but the RS peer materially disagrees (~+3.8%) → flagged: the
    # whole-geography flagship value is taken and the rejected RS value recorded in lineage.
    f = _state_fact(bundle, "Odisha", "2023-24", "persondays_generated")
    assert f.value == Decimal("176245707")  # flagship value taken (whole geography)
    assert f.confidence is Confidence.FLAGGED_DISAGREEMENT
    assert f.reconciliation.resolution_rule_id == "R4-REC-02"
    assert f.reconciliation.disagreement is not None
    assert "SRC_RS" in f.reconciliation.disagreement.rejected_sources
    flagship = next(s for s in f.reconciliation.sources_seen if s.source_id == "SRC_FLAGSHIP")
    assert flagship.aggregate_coverage is not None
    assert flagship.aggregate_coverage.status is CoverageStatus.COMPLETE


# --- SYB2018 terminal-partial exclusion (amended R4-REC-11) + the RS expenditure/100-days peers ---


def test_syb2018_terminal_partial_withheld_when_no_full_year_peer(bundle: ExportBundle) -> None:
    # MoSPI's SYB2018 edition publishes FY2017-18 as a mid-year partial (its terminal year). With no
    # full-year peer for persondays 2017-18, the amended R4-REC-11 withholds it: value null, the
    # partial kept in lineage — not published as an annual.
    f = _state_fact(bundle, "Uttar Pradesh", "2017-18", "persondays_generated")
    assert f.value is None
    assert f.confidence is Confidence.PARTIAL_ONLY
    assert f.reconciliation.resolution_rule_id == "R4-REC-11"
    assert [s.source_id for s in f.reconciliation.partial_period] == ["SRC_MOSPI"]


def test_rs_expenditure_supersedes_the_2017_18_partial(bundle: ExportBundle) -> None:
    # For total_expenditure 2017-18 an RS full-year peer (57bff16a) exists: the MoSPI partial is
    # excluded, the RS full-year stands as the value — single-source (the excluded partial is not
    # corroboration), with the partial recorded in lineage.
    f = _state_fact(bundle, "Andhra Pradesh", "2017-18", "total_expenditure")
    assert f.value == Decimal("643118.93")  # the RS full-year figure, not the MoSPI partial
    assert f.confidence is Confidence.SINGLE_SOURCE
    assert f.reconciliation.resolution_rule_id == "R4-REC-11"
    assert [s.source_id for s in f.reconciliation.partial_period] == ["SRC_MOSPI"]


def test_rs_expenditure_corroborates_mospi_pre_2018(bundle: ExportBundle) -> None:
    # On a full-year pre-2018 year the RS expenditure table corroborates the MoSPI edition final:
    # two independent publishers agree → cross-publisher (a real gain from wiring 57bff16a).
    f = _state_fact(bundle, "Kerala", "2016-17", "total_expenditure")
    assert f.confidence is Confidence.CROSS_PUBLISHER
    assert {"SRC_MOSPI", "SRC_RS"} <= {s.source_id for s in f.reconciliation.sources_seen}


def test_three_national_persondays_cells_unadjudicated(bundle: ExportBundle) -> None:
    unadjudicated = [
        f
        for f in bundle.national_facts
        if f.key.metric == "persondays_generated" and f.value is None
    ]
    assert {f.key.fin_year for f in unadjudicated} == {"2012-13", "2013-14", "2014-15"}
    for f in unadjudicated:
        assert f.reconciliation.resolution_rule_id == "R4-REC-09"  # single-publisher divergence
        assert f.confidence is Confidence.SINGLE_PUBLISHER_DIVERGENCE


def test_edition_supersession_labels_470_state_cells(bundle: ExportBundle) -> None:
    # 470 (was 472): two total_expenditure cells where the RS peer now corroborates the latest
    # edition upgrade from edition-superseded to cross-publisher.
    superseded = [f for f in bundle.state_facts if f.confidence is Confidence.EDITION_SUPERSEDED]
    assert len(superseded) == 470


def test_active_workers_has_no_pre_2018_value(bundle: ExportBundle) -> None:
    for facts in (bundle.state_facts, bundle.national_facts):
        assert not [
            f for f in facts if f.key.metric == "active_workers" and f.key.fin_year < "2018"
        ]


def test_goa_2022_23_persondays_spot_value(bundle: ExportBundle) -> None:
    code = _name_to_code(bundle)["Goa"]
    goa: list[SeriesFact] = [
        f
        for f in bundle.state_facts
        if f.key.state_code == code
        and f.key.fin_year == "2022-23"
        and f.key.metric == "persondays_generated"
    ]
    assert len(goa) == 1
    assert goa[0].value == Decimal("94004")  # FY-final rollup, not the 6.31× naive monthly sum


def test_unadjudicated_national_cells_export_null_not_zero(written: _Written) -> None:
    d1, _d2, _counts = written
    value_idx = NATIONAL_COLUMNS.index("value")
    fy_idx = NATIONAL_COLUMNS.index("financial_year")
    metric_idx = NATIONAL_COLUMNS.index("metric")
    rows = (d1 / "national_annual_series.csv").read_text().splitlines()[1:]
    persondays_2013 = [
        r.split(",")
        for r in rows
        if r.split(",")[metric_idx] == "persondays_generated" and r.split(",")[fy_idx] == "2013-14"
    ]
    assert len(persondays_2013) == 1
    assert persondays_2013[0][value_idx] == ""  # empty (null), never "0"
