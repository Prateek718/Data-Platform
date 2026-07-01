"""Stage 3.5 — zero-data-loss coverage assertion + quarantine-reason audit.

The hard guarantee of this stage: EVERY archived dataset ends in exactly one of
{resolved-geo, resolved-national, quarantined/deferred} — no dataset and no row silently missing.
These tests prove it two ways:

* dataset coverage — every resource in the manifest is the flagship, a wired spec, or a deferral
  with an honest reason; the three partitions are disjoint and their union is the whole manifest;
* row conservation — each wired resource, run through ingest → normalize → resolve, emits
  ``resolved + quarantined == normalized rows`` (every row lands somewhere), and every quarantined
  row and every deferral carries a specific, non-empty reason.

Skipped when the gitignored ``data/archive/`` snapshot is absent (e.g. a fresh CI checkout); the
committed spec JSON is still validated structurally by the loader import.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from data_platform.resolve.geo import GeoResolver
from data_platform.resolve.lgd import load_lgd_reference
from data_platform.resolve.models import GeoLevel, ResolutionQuarantineReason
from data_platform.wiring.driver import WiringOutcome, wire_resource
from data_platform.wiring.specs import DEFERRED, WIRED

ARCHIVE = Path(__file__).resolve().parents[2] / "data" / "archive"
_MANIFEST = ARCHIVE / "_manifest.json"
_LGD_STATES = ARCHIVE / "lgd" / "lgd_states.json"
_FLAGSHIP = "ee03643a-ee4c-48c2-ac30-9f2ff26ab722"

pytestmark = pytest.mark.skipif(
    not (_MANIFEST.exists() and _LGD_STATES.exists()),
    reason="local archive snapshot not present",
)


@pytest.fixture(scope="module")
def resolver() -> GeoResolver:
    states, districts = load_lgd_reference(_LGD_STATES, ARCHIVE / "lgd" / "lgd_districts.json")
    return GeoResolver.from_reference(states=states, districts=districts)


@pytest.fixture(scope="module")
def outcomes(resolver: GeoResolver) -> dict[str, WiringOutcome]:
    return {rid: wire_resource(res, resolver) for rid, res in WIRED.items()}


def _manifest_resource_ids() -> set[str]:
    manifest = json.loads(_MANIFEST.read_text())
    return {r["resource_id"] for r in manifest["resources"]}


def test_every_manifest_dataset_is_accounted_for_exactly_once() -> None:
    manifest_ids = _manifest_resource_ids()
    wired = set(WIRED)
    deferred = set(DEFERRED)
    # Disjoint partitions.
    assert wired.isdisjoint(deferred)
    assert _FLAGSHIP not in wired and _FLAGSHIP not in deferred
    # Union == the whole manifest (flagship + wired + deferred), nothing missing or extra.
    assert wired | deferred | {_FLAGSHIP} == manifest_ids


def test_every_deferral_has_a_specific_nonempty_reason() -> None:
    for resource_id, reason in DEFERRED.items():
        assert reason and reason.strip(), f"empty deferral reason for {resource_id}"
    # The one dataset with no bytes on disk stays a recorded gap (never fabricated).
    assert any("no bytes on disk" in r for r in DEFERRED.values())


def test_all_wired_resources_resolve_without_runtime_deferral(
    outcomes: dict[str, WiringOutcome],
) -> None:
    runtime_deferred = {rid: o.deferred_reason for rid, o in outcomes.items() if not o.is_resolved}
    assert runtime_deferred == {}, f"wired specs that failed at runtime: {runtime_deferred}"


def test_row_conservation_every_row_lands_somewhere(outcomes: dict[str, WiringOutcome]) -> None:
    for rid, o in outcomes.items():
        resolved = o.resolved
        assert resolved is not None
        landed = len(resolved.records) + len(resolved.quarantined)
        assert landed == o.normalized_rows, (
            f"{rid}: {landed} != {o.normalized_rows} normalized rows"
        )


def test_national_resolved_rows_carry_no_lgd_code(outcomes: dict[str, WiringOutcome]) -> None:
    for o in outcomes.values():
        resolved = o.resolved
        assert resolved is not None
        for rec in resolved.records:
            if rec.geo_level is GeoLevel.NATIONAL:
                assert rec.state_canonical_id is None and rec.district_canonical_id is None


def test_every_quarantined_row_has_a_typed_reason_and_detail(
    outcomes: dict[str, WiringOutcome],
) -> None:
    valid = set(ResolutionQuarantineReason)
    for o in outcomes.values():
        resolved = o.resolved
        assert resolved is not None
        for q in resolved.quarantined:
            assert q.reason in valid
            assert q.detail and q.detail.strip()
