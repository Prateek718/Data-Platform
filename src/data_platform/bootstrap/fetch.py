"""The one place the bootstrap touches the network. Deliberately thin.

Everything that can be wrong with a download — truncation, substitution, a tampered file inside the
archive — is caught by verification in :mod:`install`, not here. This module's only job is to hand
those bytes over, so the tests can exercise the whole install path without a network and without
mocking anything interesting.
"""

from __future__ import annotations

from typing import Final

import httpx

from data_platform.bootstrap.release import asset_url

DEFAULT_TIMEOUT_S: Final = 300.0


class DownloadError(RuntimeError):
    """The release asset could not be downloaded."""


def fetch_asset(asset: str, *, timeout_s: float = DEFAULT_TIMEOUT_S) -> bytes:
    """Download a release asset and return its bytes. Verification happens in :mod:`install`."""
    url = asset_url(asset)
    try:
        response = httpx.get(url, follow_redirects=True, timeout=timeout_s)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise DownloadError(f"could not download {asset} from {url}: {exc}") from exc
    return response.content
