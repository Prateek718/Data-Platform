"""Install the sealed dataset into ``dist/v1.0`` — verified twice, and all-or-nothing.

A fresh clone has no data: ``dist/`` is gitignored, and the dataset lives in the v1.0.0 GitHub
release. This module fetches it, and the shape of the fetch is the whole point:

**Two layers of verification, both mandatory.**

1. The downloaded zip against the SHA-256 the release itself published (:mod:`release`). Catches a
   truncated or substituted download before a single byte is unpacked.
2. The seven extracted files against ``src/data_platform/mcp/SHA256SUMS.txt`` — the manifest
   committed in this repo, and the same gate :mod:`data_platform.mcp.loader` enforces at server
   startup. This is the authoritative layer: it is what makes "the bootstrap installed it" and "the
   server will serve it" the same statement.

**All-or-nothing.** Everything is unpacked and verified in a staging directory *inside* ``dist/``
— on the same filesystem as the target, so the final move is an atomic rename and not a copy that
can be interrupted halfway. Nothing is put in place until both layers have passed. If a good
``dist/v1.0`` already exists, it is moved aside and restored on any failure: a failed refresh must
never destroy a working dataset.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import zipfile
from io import BytesIO
from pathlib import Path
from typing import Final

from data_platform.mcp import loader
from data_platform.mcp.loader import ArtifactError

# The directory inside the zip, and the one it becomes on disk.
ZIP_PREFIX: Final = "dist/v1.0/"
TARGET_DIR_NAME: Final = "v1.0"

# Staging and backup live INSIDE dist/, never in /tmp: a rename across filesystems is a copy, and a
# copy can be interrupted, which is exactly the half-populated dist this design exists to prevent.
STAGING_DIR_NAME: Final = ".staging-v1.0"
BACKUP_DIR_NAME: Final = ".backup-v1.0"


class BootstrapError(RuntimeError):
    """The dataset could not be installed. ``dist/v1.0`` is left absent, or left as it was."""


def staging_dir(dist_root: Path) -> Path:
    return dist_root / STAGING_DIR_NAME


def install(
    zip_bytes: bytes,
    *,
    dist_root: Path,
    expected_zip_sha256: str,
    manifest_path: Path = loader.DEFAULT_MANIFEST,
) -> Path:
    """Verify, unpack, verify again, and swap into place. Returns the installed directory.

    Pure with respect to the network: the caller supplies the bytes. Everything that can fail is
    failed *before* the target directory is touched.
    """
    _verify_zip(zip_bytes, expected_zip_sha256)

    target = dist_root / TARGET_DIR_NAME
    staging = staging_dir(dist_root)
    backup = dist_root / BACKUP_DIR_NAME

    dist_root.mkdir(parents=True, exist_ok=True)
    _clear(staging)
    _clear(backup)

    try:
        _unpack(zip_bytes, staging)
        _verify_files(staging, manifest_path)
    except BootstrapError:
        _clear(staging)
        raise

    _swap(staging, target, backup)
    return target


def _verify_zip(zip_bytes: bytes, expected: str) -> None:
    """Layer 1: is this the archive the release published?"""
    actual = hashlib.sha256(zip_bytes).hexdigest()
    if actual != expected:
        raise BootstrapError(
            "the downloaded archive does not match the digest the release published "
            f"(expected {expected}, got {actual}). The download was truncated or the file is not "
            "the sealed release. Nothing was installed."
        )


def _unpack(zip_bytes: bytes, staging: Path) -> None:
    """Extract the seven files, flat, into staging. A member outside dist/v1.0/ is an attack."""
    staging.mkdir(parents=True)
    with zipfile.ZipFile(BytesIO(zip_bytes)) as archive:
        for info in archive.infolist():
            if info.is_dir():
                continue
            name = info.filename
            if not name.startswith(ZIP_PREFIX) or "/" in name[len(ZIP_PREFIX) :]:
                raise BootstrapError(
                    f"unexpected member in the release archive: {name!r}. Only files directly "
                    f"under {ZIP_PREFIX} are installed. Nothing was installed."
                )
            (staging / Path(name).name).write_bytes(archive.read(info))


def _verify_files(staging: Path, manifest_path: Path) -> None:
    """Layer 2: the authoritative gate — the same one the server runs at startup."""
    try:
        loader.verify_artifacts(staging, manifest_path)
    except ArtifactError as exc:
        raise BootstrapError(
            f"the extracted files failed the checksum manifest the server enforces: {exc}. "
            "Nothing was installed."
        ) from exc


def _swap(staging: Path, target: Path, backup: Path) -> None:
    """Put the verified directory in place atomically, keeping any existing dataset recoverable."""
    had_previous = target.exists()
    if had_previous:
        os.replace(target, backup)  # same filesystem: a rename, not a copy

    try:
        os.replace(staging, target)
    except OSError as exc:
        if had_previous:
            os.replace(backup, target)  # put the working dataset back exactly as it was
        _clear(staging)
        raise BootstrapError(f"could not move the verified dataset into place: {exc}") from exc

    _clear(backup)


def _clear(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
