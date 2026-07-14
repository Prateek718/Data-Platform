"""What the v1.0.0 release publishes, recorded so a fresh clone can verify before it trusts.

These digests are a **copy of a frozen fact**: they were read off the ``SHA256SUMS.txt`` asset that
the v1.0.0 GitHub release publishes alongside the zips. Recording them here creates no new release
artifact — it puts the release's own claim inside the repo, where a clone can check a download
against it *before* unpacking anything.

The release is sealed (MGNREGA was repealed 30 June 2026; the dataset is DOI-versioned and
immutable), so these values cannot go stale. If a download ever fails to match one of them, the
right conclusion is that the download is wrong, not that the constant is.
"""

from __future__ import annotations

from typing import Final

REPO: Final = "Prateek718/Data-Platform"
RELEASE_TAG: Final = "v1.0.0"

# The dataset the MCP server serves: seven files under dist/v1.0/.
DATASET_ASSET: Final = "mgnrega-canonical-series-v1.0.0.zip"

# The frozen raw archive the pipeline was built from. Not needed to SERVE the record — only to
# rebuild it from source — so the bootstrap does not fetch it by default (it is 78 MB against 5).
ARCHIVE_ASSET: Final = "mgnrega-raw-archive-frozen-2026-06-30.zip"

# Copied verbatim from the release's published SHA256SUMS.txt asset:
#   https://github.com/Prateek718/Data-Platform/releases/download/v1.0.0/SHA256SUMS.txt
RELEASE_ASSET_SHA256: Final[dict[str, str]] = {
    DATASET_ASSET: "b57ead8eaed72396372933ae5269b5528e986bdd6ae4b1bbd0d60fc76be00d4b",
    ARCHIVE_ASSET: "5d35917d3477b698ea98339d25e04edea26c21f971a4102f10647cf0ee4a0144",
}


def asset_url(asset: str) -> str:
    """The download URL for a release asset, pinned to the sealed tag."""
    return f"https://github.com/{REPO}/releases/download/{RELEASE_TAG}/{asset}"
