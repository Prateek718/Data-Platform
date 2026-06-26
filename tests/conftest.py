"""Shared pytest fixtures — including the hermetic network guard (Stage 1 T1.4).

Ingestion must run fully offline. Rather than trust that tests don't touch the
network, we actively block real socket connections so any accidental live fetch
fails loudly. Live fetch (transport.fetch_live) is exercised only in an explicit,
separately-marked path — never in the default hermetic suite.
"""

from __future__ import annotations

import socket
from typing import Any, NoReturn

import pytest


class NetworkBlockedError(RuntimeError):
    """Raised when a test attempts real network I/O under the hermetic guard."""


@pytest.fixture(autouse=True)
def _no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fail any test that opens a real socket connection (hermetic mode)."""

    def _blocked(*_args: Any, **_kwargs: Any) -> NoReturn:
        raise NetworkBlockedError(
            "Network access is disabled in tests; ingestion must run offline."
        )

    monkeypatch.setattr(socket.socket, "connect", _blocked)
    monkeypatch.setattr(socket.socket, "connect_ex", _blocked)
