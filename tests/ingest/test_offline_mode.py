"""T1.4 — offline / hermetic test mode (tests written first, per strict TDD).

Two guarantees:
  * HERMETICITY is proven, not trusted: the autouse network guard (conftest) fails any real
    socket/httpx call, and live fetch is gated behind an explicit ``DATA_GOV_API_KEY`` so the
    default path is offline;
  * the OFFLINE path ingests both sources end to end from committed fixtures via
    ``transport.read_offline`` — and an offline read can DECLARE its ``pull_completeness``
    (fixtures are trimmed/partial, so completeness is declared, never derived from counts),
    which the adapter then propagates onto the batch.
"""

from __future__ import annotations

import socket
from pathlib import Path

import httpx
import pytest

import data_platform.ingest.transport as transport
from data_platform.ingest.adapters.flagship import FlagshipAdapter
from data_platform.ingest.adapters.rajya_sabha import RajyaSabhaAdapter
from data_platform.ingest.registry import RS_RESOURCE_IDS, SRC_FLAGSHIP, SRC_RS

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
RS_TABLE1_ID = RS_RESOURCE_IDS[0]
FLAGSHIP_FIXTURE = FIXTURES / "flagship" / "goa_2022_2023.json"
RS_FIXTURE = FIXTURES / "rajya_sabha" / "table1_cea6ee41.json"


# ------------------------------------------------------------------------------------
# Hermeticity — the guard is active and live fetch is gated (proven, not assumed)
# ------------------------------------------------------------------------------------
def test_network_guard_blocks_a_real_socket_connection() -> None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    with pytest.raises(RuntimeError, match="offline"):
        sock.connect(("203.0.113.1", 80))  # TEST-NET-3; never actually dialled


def test_network_guard_blocks_an_httpx_request() -> None:
    with pytest.raises((httpx.HTTPError, RuntimeError)):
        httpx.get("https://api.data.gov.in/resource/anything")


def test_live_fetch_requires_explicit_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATA_GOV_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="DATA_GOV_API_KEY"):
        transport.fetch_live(FlagshipAdapter(), limit=5)


# ------------------------------------------------------------------------------------
# Offline path — both sources ingest end to end from fixtures, no network
# ------------------------------------------------------------------------------------
def test_offline_path_ingests_both_sources_end_to_end() -> None:
    flagship = FlagshipAdapter()
    flagship_batch = flagship.parse(transport.read_offline(flagship, FLAGSHIP_FIXTURE))
    assert flagship_batch.source_id == SRC_FLAGSHIP
    assert flagship_batch.records  # rows actually landed

    rs = RajyaSabhaAdapter(RS_TABLE1_ID)
    rs_batch = rs.parse(transport.read_offline(rs, RS_FIXTURE))
    assert rs_batch.source_id == SRC_RS
    assert rs_batch.records


def test_offline_read_defaults_to_partial_completeness() -> None:
    # Trimmed offline fixtures are NOT full pulls, so the fail-safe default is partial.
    flagship = FlagshipAdapter()
    payload = transport.read_offline(flagship, FLAGSHIP_FIXTURE)
    assert payload.pull_completeness == "partial"
    assert flagship.parse(payload).pull_completeness == "partial"


def test_offline_read_can_declare_completeness_which_propagates_to_batch() -> None:
    # An offline read may DECLARE full coverage (e.g. a full snapshot saved to disk); the
    # adapter must copy that declaration straight onto the batch so drift can use it.
    flagship = FlagshipAdapter()
    payload = transport.read_offline(flagship, FLAGSHIP_FIXTURE, pull_completeness="full")
    assert payload.pull_completeness == "full"  # read_offline honoured the declaration
    assert flagship.parse(payload).pull_completeness == "full"  # adapter propagated it
