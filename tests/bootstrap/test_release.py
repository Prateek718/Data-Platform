"""The release constants are a COPY of a frozen fact, and the copy must be provably faithful.

The zip digests here were read off the SHA256SUMS.txt asset the v1.0.0 GitHub release publishes.
Recording them in the repo is what lets a fresh clone verify a download before trusting it — but a
recorded constant can drift from the thing it records, so this pins it: the digest recorded for the
dataset zip must be the same one the committed MCP manifest already cites as its own provenance.

That is not a circular check. The manifest's header states where its seven file-digests came from
(the zip, by its digest); the bootstrap states which zip it will accept. If those two ever disagree,
the bootstrap would install a dataset the server refuses to serve — so they are compared here.
"""

from __future__ import annotations

from data_platform.bootstrap import release
from data_platform.mcp import loader


def test_the_dataset_zip_is_the_one_the_server_manifest_was_built_from() -> None:
    recorded = release.RELEASE_ASSET_SHA256[release.DATASET_ASSET]
    manifest_header = loader.DEFAULT_MANIFEST.read_text(encoding="utf-8")

    assert recorded in manifest_header, (
        "the zip digest the bootstrap will accept is not the one the committed MCP manifest cites "
        "as its provenance — the bootstrap would install a dataset the server refuses to serve"
    )


def test_every_recorded_digest_is_a_sha256() -> None:
    for name, digest in release.RELEASE_ASSET_SHA256.items():
        assert len(digest) == 64, name
        assert set(digest) <= set("0123456789abcdef"), name


def test_the_asset_url_points_at_the_pinned_release() -> None:
    url = release.asset_url(release.DATASET_ASSET)
    assert url.endswith(f"/download/{release.RELEASE_TAG}/{release.DATASET_ASSET}")
    assert url.startswith("https://github.com/")
