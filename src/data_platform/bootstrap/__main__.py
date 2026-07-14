"""``data-platform-bootstrap`` — fetch the sealed dataset so a fresh clone can serve it.

``dist/`` is gitignored: a clone has the code and none of the data. This command downloads the
v1.0.0 release, verifies it against the digest the release published AND against the checksum
manifest the server enforces at startup, and installs it to ``dist/v1.0`` — atomically, so a
failure leaves no half-populated dataset and never damages one that already works.

    data-platform-bootstrap            # install if absent; verify and exit if already there
    data-platform-bootstrap --force    # re-download even if a verified dataset is present
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from data_platform.bootstrap import release
from data_platform.bootstrap.fetch import DownloadError, fetch_asset
from data_platform.bootstrap.install import BootstrapError, install
from data_platform.mcp import loader
from data_platform.mcp.loader import ArtifactError


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dist-root",
        type=Path,
        default=loader.REPO_ROOT / "dist",
        help="where dist/v1.0 is installed (default: the repo's dist/)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="re-download and reinstall even if a verified dataset is already present",
    )
    args = parser.parse_args(argv)

    target = args.dist_root / "v1.0"
    if not args.force and _already_installed(target):
        print(f"dataset already installed and verified at {target}")
        return 0

    asset = release.DATASET_ASSET
    print(f"downloading {asset} from the {release.RELEASE_TAG} release ...")
    try:
        payload = fetch_asset(asset)
    except DownloadError as exc:
        print(f"\n{exc}", file=sys.stderr)
        return 1

    print(f"verifying {len(payload):,} bytes against the digest the release published ...")
    try:
        installed = install(
            payload,
            dist_root=args.dist_root,
            expected_zip_sha256=release.RELEASE_ASSET_SHA256[asset],
        )
    except BootstrapError as exc:
        print(f"\nBOOTSTRAP FAILED — {exc}", file=sys.stderr)
        return 1

    print(f"verified against the manifest the server enforces; installed to {installed}")
    print("\nready: `data-platform-mcp` will now start.")
    return 0


def _already_installed(target: Path) -> bool:
    """Present AND passing the server's own gate — a corrupt dataset is not 'already installed'."""
    try:
        loader.verify_artifacts(target, loader.DEFAULT_MANIFEST)
    except ArtifactError:
        return False
    return True


if __name__ == "__main__":
    sys.exit(main())
