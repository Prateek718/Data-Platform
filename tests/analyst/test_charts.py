"""Charts are claims too: they may plot only figures the verifier already passed.

The chart pipeline reads report.json — never the dataset — so it has no way to obtain a number the
report did not verify. Its manifest names the exact figure ids behind every point, so a reader can
walk from a plotted point to a fact_id to its lineage.
"""

from __future__ import annotations

import re
from decimal import Decimal

import pytest

from data_platform.analyst import chart_specs, charts
from data_platform.analyst.charts import Annotation, Point


def _report(series: list[dict[str, object]], cohorts: list[dict[str, object]]) -> dict[str, object]:
    return {
        "sections": [
            {"key": "national_series", "series": series, "series_cohorts": []},
            {"key": "coverage", "series": [], "series_cohorts": cohorts},
        ]
    }


def test_a_chart_plots_only_verified_series_figures() -> None:
    report = _report(
        series=[
            {
                "id": "series_persondays_2006_07",
                "period": "2006-07",
                "value": "905054000",
                "metric": "persondays_generated",
            },
            {
                "id": "series_persondays_2020_21",
                "period": "2020-21",
                "value": "3881318918",
                "metric": "persondays_generated",
            },
        ],
        cohorts=[],
    )
    built = chart_specs.build_charts(report)
    assert [c.id for c in built] == ["national-persondays"]
    chart = built[0]
    # The manifest names exactly the figures plotted — nothing else can get in.
    assert chart.source_ids == ("series_persondays_2006_07", "series_persondays_2020_21")
    assert chart.manifest_entry()["plots"] == list(chart.source_ids)
    assert chart.manifest_entry()["file"] == "charts/national-persondays.svg"


def test_counts_per_year_become_a_bar_chart() -> None:
    report = _report(
        series=[],
        cohorts=[
            {"id": "nulls_by_year_2016_17", "value": "0", "query": {"fy_from": "2016-17"}},
            {"id": "nulls_by_year_2017_18", "value": "163", "query": {"fy_from": "2017-18"}},
        ],
    )
    built = chart_specs.build_charts(report)
    assert [c.id for c in built] == ["nulls-by-year"]
    assert built[0].source_ids == ("nulls_by_year_2016_17", "nulls_by_year_2017_18")


def test_a_report_with_no_series_draws_no_charts() -> None:
    assert chart_specs.build_charts({"sections": []}) == []


def test_the_svg_is_self_contained_and_theme_aware() -> None:
    chart = charts.line_chart(
        id="t",
        title="Person-days",
        caption="c",
        section_key="national_series",
        points=[
            Point("2006-07", Decimal("905054000"), "a"),
            Point("2020-21", Decimal("3881318918"), "b"),
        ],
        y_label="billion person-days",
        y_scale=Decimal(1_000_000_000),
        annotations=(Annotation("2020-21", "COVID-year peak"),),
    )
    svg = chart.svg
    assert svg.startswith("<svg") and svg.endswith("</svg>")
    assert "prefers-color-scheme: dark" in svg  # readable in either theme
    assert "COVID-year peak" in svg
    assert "http" not in svg.replace("http://www.w3.org/2000/svg", "")  # no network, no CDN
    assert "<script" not in svg


def test_a_chart_needs_a_point() -> None:
    with pytest.raises(ValueError, match="at least one point"):
        charts.bar_chart(id="t", title="t", caption="c", section_key="s", points=[], y_label="n")


def test_the_line_breaks_where_the_record_withholds_a_year() -> None:
    """A null year must be drawn as a gap, never bridged.

    The national series has no person-days for FY 2012-13 to 2014-15. Spacing the points evenly and
    joining them would draw a straight line across a three-year hole — the visual equivalent of
    coercing a null to a value. The axis is the real span of years; the path lifts and restarts.
    """
    chart = charts.line_chart(
        id="t",
        title="t",
        caption="c",
        section_key="national_series",
        points=[
            Point("2011-12", Decimal("2187636000"), "a"),
            Point("2015-16", Decimal("2352090000"), "b"),
        ],
        y_label="billion person-days",
        y_scale=Decimal(1_000_000_000),
    )
    path = chart.svg.split('class="series" d="')[1].split('"')[0]
    assert path.count("M") == 2  # two runs of data, not one line across the hole
    assert "2013-14" in chart.svg  # the withheld years still occupy the axis
    assert "no line where the record withholds a year" in chart.svg


def test_the_repeal_stub_year_is_never_plotted() -> None:
    """FY 2026-27 holds April 2026 alone: one month cannot be a point among full years.

    Plotting it would draw a collapse that never happened. It is a real fact, reported in the prose
    and the figure tables — but it is stated as a note beneath the chart, not drawn as a datapoint.
    """
    report = _report(
        series=[
            {
                "id": "series_persondays_2025_26",
                "period": "2025-26",
                "value": "2209959751",
                "metric": "persondays_generated",
            },
            {
                "id": "series_persondays_2026_27",
                "period": "2026-27",
                "value": "12914539",
                "metric": "persondays_generated",
            },
        ],
        cohorts=[],
    )
    chart = chart_specs.build_charts(report)[0]
    assert chart.source_ids == ("series_persondays_2025_26",)
    assert "2026-27" not in chart.svg
    assert "FY 2026-27 is omitted" in chart.caption


def _ticks(svg: str) -> list[tuple[str, float]]:
    """The x-axis year labels and their x positions, as rendered."""
    pattern = re.compile(
        r'<text class="tick" x="([0-9.]+)" y="[0-9.]+" '
        r'text-anchor="middle">([0-9]{4}-[0-9]{2})</text>'
    )
    return [(period, float(x)) for x, period in pattern.findall(svg)]


def _points(svg: str) -> list[float]:
    return [float(x) for x in re.findall(r'<circle class="point" cx="([0-9.]+)"', svg)]


def _full_series_chart() -> charts.Chart:
    """One point per year, 2006-07 to 2025-26 — so point i IS year i on the axis."""
    points = [Point(f"{y}-{str(y + 1)[2:]}", Decimal(y), f"f{y}") for y in range(2006, 2026)]
    return charts.line_chart(
        id="t",
        title="t",
        caption="c",
        section_key="national_series",
        points=points,
        y_label="n",
    )


def test_tick_positions_are_the_year_positions_the_points_use() -> None:
    """The invariant that made the old defect diagnosable.

    A tick must sit exactly where the year it names sits. If ticks are placed on their own rhythm
    while points are placed on the year axis, the labels drift off the data and the chart lies about
    when things happened — quietly, because both halves look plausible alone.
    """
    svg = _full_series_chart().svg
    ticks = _ticks(svg)
    point_x = _points(svg)
    assert len(point_x) == 20  # one per year, 2006-07 .. 2025-26

    for period, x in ticks:
        year_index = int(period[:4]) - 2006
        assert x == pytest.approx(point_x[year_index], abs=0.05), (
            f"the tick for {period} is not where the {period} datapoint is"
        )


def test_labelled_ticks_are_evenly_spaced_in_years() -> None:
    """A constant rhythm: every second year, with no irregular interval at the right edge."""
    ticks = _ticks(_full_series_chart().svg)
    years = [int(period[:4]) for period, _ in ticks]
    gaps = {b - a for a, b in zip(years, years[1:], strict=False)}
    assert gaps == {2}, f"tick years are not evenly spaced: {years}"


def test_withheld_years_are_shaded_and_named_in_the_chart() -> None:
    """A gap in a line reads as a kink. The band says what it is, without claiming why."""
    chart = charts.line_chart(
        id="t",
        title="t",
        caption="c",
        section_key="national_series",
        points=[
            Point("2011-12", Decimal("2187636000"), "a"),
            Point("2015-16", Decimal("2352090000"), "b"),
        ],
        y_label="billion person-days",
        y_scale=Decimal(1_000_000_000),
    )
    assert 'class="withheld"' in chart.svg
    assert "record withholds 2012-13 – 2014-15" in chart.svg
