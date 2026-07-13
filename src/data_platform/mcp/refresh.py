"""request_refresh — the sealed-record statement.

The MCP surface is read-only and the dataset is a concluded historical record: MGNREGA was repealed
effective 30 June 2026, so there is no live source to refresh from. This tool always returns the
same structured statement (never attempts a fetch), pointing the caller at the DOI-versioned
citation for the immutable release.
"""

from __future__ import annotations

from data_platform.mcp import refusals

# The scheme was repealed effective this date; the series ends at FY 2026-27 (DATA_DICTIONARY §7).
REPEAL_DATE = "2026-06-30"
# Citation pointers (see CITATION.cff): the immutable version DOI and the always-latest concept DOI.
VERSION_DOI = "10.5281/zenodo.21318927"
CONCEPT_DOI = "10.5281/zenodo.21318431"


def request_refresh() -> dict[str, object]:
    """Report that the record is sealed and cannot be refreshed, with the citation pointer."""
    return {
        "refresh_available": False,
        "code": refusals.RECORD_SEALED,
        "reason": (
            "MGNREGA was repealed effective 30 June 2026; this dataset is a closed, DOI-versioned "
            "historical record and cannot be refreshed. No new data will be published — it is "
            "served from the immutable, checksum-verified v1.0.0 release artifacts."
        ),
        "scheme_repealed_effective": REPEAL_DATE,
        "record_status": "closed historical record (DOI-versioned)",
        "citation": {
            "citation_file": "CITATION.cff",
            "doi": VERSION_DOI,
            "concept_doi": CONCEPT_DOI,
        },
    }
