"""Unit tests for request_refresh (Stage 7 step 5)."""

from __future__ import annotations

from typing import Any, cast

from data_platform.mcp import refresh, refusals


def test_request_refresh_reports_sealed_record() -> None:
    result = refresh.request_refresh()
    assert result["refresh_available"] is False
    assert result["code"] == refusals.RECORD_SEALED
    assert result["scheme_repealed_effective"] == "2026-06-30"
    assert "repealed" in cast(str, result["reason"]).lower()


def test_request_refresh_includes_citation_pointer() -> None:
    citation = cast(dict[str, Any], refresh.request_refresh()["citation"])
    assert citation["citation_file"] == "CITATION.cff"
    assert citation["doi"].startswith("10.5281/zenodo.")
