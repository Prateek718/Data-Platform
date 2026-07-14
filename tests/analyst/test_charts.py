"""Charts are claims too: they may plot only figures the verifier already passed.

The chart pipeline reads report.json — never the dataset — so it has no way to obtain a number the
report did not verify. Its manifest names the exact figure ids behind every point, so a reader can
walk from a plotted point to a fact_id to its lineage.
"""

from __future__ import annotations

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
