"""The bootstrap: fetch the sealed release, verify it twice, and never leave a half-populated dist.

A fresh clone has no data — `dist/` is gitignored — so "comes up clean" means *fetch the released
artifacts, verify them, then serve them*. Verification is two-layer, and both layers are attacks
here:

1. the downloaded zip against the SHA-256 the release itself published, and
2. the seven extracted files against the manifest committed in this repo — the same gate the MCP
   server enforces at startup, and the authoritative one.

The invariant these tests exist for: **a failure at either layer leaves `dist/v1.0` absent
entirely, never partial — and if a good `dist/v1.0` was already there, a failed refresh must not
destroy it.**
"""

from __future__ import annotations

import hashlib
import io
import zipfile
from pathlib import Path

import pytest

from data_platform.bootstrap import install as install_mod
from data_platform.bootstrap.install import BootstrapError, install
from tests.fixtures.synthetic_dist import build_synthetic_dist

_MEMBERS = (
    "state_annual_series.csv",
    "state_annual_series.parquet",
    "national_annual_series.csv",
    "national_annual_series.parquet",
    "district_flagship.csv",
    "district_flagship.parquet",
    "lineage.jsonl",
)


@pytest.fixture
def release(tmp_path: Path) -> tuple[bytes, str, Path]:
    """A stand-in release: the synthetic dist zipped exactly as the real asset is laid out.

    Returns the zip bytes, their digest, and the manifest that gates the extracted files — so the
    tests exercise the real two-layer verification without touching the network or the real dist.
    """
    source = tmp_path / "source" / "dist" / "v1.0"
    build_synthetic_dist(source)

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name in _MEMBERS:
            archive.write(source / name, f"dist/v1.0/{name}")
    payload = buffer.getvalue()
    return payload, hashlib.sha256(payload).hexdigest(), source / "SHA256SUMS.txt"


def _install(tmp_path: Path, release: tuple[bytes, str, Path], **overrides: object) -> Path:
    payload, digest, manifest = release
    return install(
        overrides.get("zip_bytes", payload),  # type: ignore[arg-type]
        dist_root=tmp_path / "dist",
        expected_zip_sha256=str(overrides.get("expected_zip_sha256", digest)),
        manifest_path=manifest,
    )


def test_it_installs_the_seven_files(tmp_path: Path, release: tuple[bytes, str, Path]) -> None:
    installed = _install(tmp_path, release)

    assert installed == tmp_path / "dist" / "v1.0"
    assert sorted(p.name for p in installed.iterdir()) == sorted(_MEMBERS)


def test_it_leaves_no_staging_directory_behind(
    tmp_path: Path, release: tuple[bytes, str, Path]
) -> None:
    _install(tmp_path, release)
    assert not list((tmp_path / "dist").glob(".staging*"))
    assert not list((tmp_path / "dist").glob(".backup*"))


def test_the_staging_directory_sits_beside_its_target(
    tmp_path: Path, release: tuple[bytes, str, Path]
) -> None:
    """Staging must share a filesystem with the target, or the final move is a copy, not a rename.

    A copy can be interrupted halfway and leave exactly the half-populated dist this whole design
    exists to prevent.
    """
    assert install_mod.STAGING_DIR_NAME.startswith(".")
    staging = install_mod.staging_dir(tmp_path / "dist")
    assert staging.parent == tmp_path / "dist"


def test_a_corrupt_download_leaves_no_dist_at_all(
    tmp_path: Path, release: tuple[bytes, str, Path]
) -> None:
    """Layer 1: the zip's digest does not match what the release published."""
    payload, _digest, _manifest = release
    with pytest.raises(BootstrapError, match="does not match"):
        _install(tmp_path, release, zip_bytes=payload[:-500])  # a truncated (partial) download

    assert not (tmp_path / "dist" / "v1.0").exists()
    assert not list((tmp_path / "dist").glob(".staging*"))


def test_a_tampered_file_inside_a_well_formed_zip_leaves_no_dist(
    tmp_path: Path, release: tuple[bytes, str, Path]
) -> None:
    """Layer 2: the zip is intact, but a file inside it is not what the committed manifest gates.

    This is the layer that matters: it is the same check the server runs at startup, so anything the
    bootstrap installs is something the server will agree to serve.
    """
    _payload, _digest, manifest = release
    source = manifest.parent

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name in _MEMBERS:
            data = (source / name).read_bytes()
            if name == "national_annual_series.csv":
                data += b"\n# an extra line nobody signed\n"
            archive.writestr(f"dist/v1.0/{name}", data)
    tampered = buffer.getvalue()

    with pytest.raises(BootstrapError, match="checksum"):
        install(
            tampered,
            dist_root=tmp_path / "dist",
            expected_zip_sha256=hashlib.sha256(tampered).hexdigest(),  # layer 1 passes
            manifest_path=manifest,
        )

    assert not (tmp_path / "dist" / "v1.0").exists()
    assert not list((tmp_path / "dist").glob(".staging*"))


def test_a_failed_refresh_does_not_destroy_a_good_dist(
    tmp_path: Path, release: tuple[bytes, str, Path]
) -> None:
    """The one that would really hurt: re-bootstrapping over a working install, and failing."""
    payload, digest, manifest = release
    dist_root = tmp_path / "dist"
    installed = install(
        payload, dist_root=dist_root, expected_zip_sha256=digest, manifest_path=manifest
    )
    before = {p.name: p.read_bytes() for p in installed.iterdir()}

    with pytest.raises(BootstrapError):
        install(
            payload[:-500],
            dist_root=dist_root,
            expected_zip_sha256=digest,
            manifest_path=manifest,
        )

    after = {p.name: p.read_bytes() for p in installed.iterdir()}
    assert after == before  # the working dataset survived the failed refresh, byte for byte
    assert not list(dist_root.glob(".staging*"))
    assert not list(dist_root.glob(".backup*"))


def test_a_zip_that_escapes_its_directory_is_refused(
    tmp_path: Path, release: tuple[bytes, str, Path]
) -> None:
    """A member path that climbs out of dist/v1.0 is an attack, not an artifact."""
    _payload, _digest, manifest = release

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("dist/v1.0/../../escaped.txt", b"pwned")
    evil = buffer.getvalue()

    with pytest.raises(BootstrapError, match="unexpected member"):
        install(
            evil,
            dist_root=tmp_path / "dist",
            expected_zip_sha256=hashlib.sha256(evil).hexdigest(),
            manifest_path=manifest,
        )

    assert not (tmp_path / "escaped.txt").exists()
    assert not (tmp_path / "dist" / "v1.0").exists()


def test_a_zip_missing_a_file_the_manifest_gates_is_refused(
    tmp_path: Path, release: tuple[bytes, str, Path]
) -> None:
    _payload, _digest, manifest = release
    source = manifest.parent

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name in _MEMBERS[:-1]:  # lineage.jsonl left out
            archive.write(source / name, f"dist/v1.0/{name}")
    short = buffer.getvalue()

    with pytest.raises(BootstrapError, match="missing"):
        install(
            short,
            dist_root=tmp_path / "dist",
            expected_zip_sha256=hashlib.sha256(short).hexdigest(),
            manifest_path=manifest,
        )

    assert not (tmp_path / "dist" / "v1.0").exists()
