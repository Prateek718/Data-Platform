"""Stage 4 orchestrator — produce the full set of harmonized canonical facts.

Ties the per-metric extractors, the assembler, and the cross-metric quarantine into one call: it
maps each canonical metric off the flagship (the seven cumulative metrics rolled to state-annual,
total_expenditure by derive-and-compare, and the district-annual FY-final wage rate), folds in the
cross-source RS person-days values, reconciles per canonical key, then applies the cross-metric
R4-Q-01 person-days plausibility check. Dependency-injected (already-resolved batches in) so it
stays pure and testable; the caller supplies the ingest→normalize→resolve products.
"""

from __future__ import annotations

from datetime import datetime

from data_platform.harmonize.assemble import assemble
from data_platform.harmonize.extract import (
    FLAGSHIP_CUMULATIVE_COLUMNS,
    flagship_district_annual_avg_wage,
    flagship_state_annual_cumulative,
    flagship_state_annual_total_expenditure,
)
from data_platform.harmonize.models import CanonicalFact, CanonicalKey, SourceValue
from data_platform.harmonize.validate import flag_implausible_persondays
from data_platform.normalize.models import CleanCell
from data_platform.resolve.models import ResolvedBatch


def harmonize_starter_metrics(
    flagship_resolved: ResolvedBatch,
    flagship_cells: dict[int, dict[str, CleanCell]],
    rs_persondays: list[tuple[CanonicalKey, SourceValue]],
    *,
    source_as_of: datetime | None,
    lgd_district_counts: dict[str, int],
) -> list[CanonicalFact]:
    """Harmonize all nine canonical metrics into reconciled facts (cross-metric Q-01 applied).

    ``rs_persondays`` are the RS state-annual person-days values already extracted from the resolved
    RS batches (the only cross-source peers in the starter slice); they join the flagship's own
    person-days at the same canonical keys so reconciliation sees every source.
    """
    keyed: list[tuple[CanonicalKey, SourceValue]] = []

    # The seven cumulative-YTD metrics (persondays, household/worker counts, wage/material/admin
    # expenditure) rolled up to state-annual.
    for metric in FLAGSHIP_CUMULATIVE_COLUMNS:
        keyed += flagship_state_annual_cumulative(
            flagship_resolved,
            flagship_cells,
            metric=metric,
            source_as_of=source_as_of,
            lgd_district_counts=lgd_district_counts,
        )
    # total_expenditure is derived-and-compared, not a plain rollup.
    keyed += flagship_state_annual_total_expenditure(
        flagship_resolved,
        flagship_cells,
        source_as_of=source_as_of,
        lgd_district_counts=lgd_district_counts,
    )
    # avg_wage is a cumulative-YTD ratio → published at district-annual (FY-final) grain, not month.
    keyed += flagship_district_annual_avg_wage(
        flagship_resolved,
        flagship_cells,
        source_as_of=source_as_of,
    )
    keyed += rs_persondays

    return flag_implausible_persondays(assemble(keyed))
