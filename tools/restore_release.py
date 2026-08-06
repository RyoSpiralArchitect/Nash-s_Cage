#!/usr/bin/env python3
"""Restore the complete verified release from the repository's archive branch.

This is an offline-friendly fallback for environments where GitHub Actions is
not available. It fetches eight text chunks already stored in this repository,
verifies the compressed archive, safely extracts it, and copies only the large
or generated files that are intentionally absent from the lightweight main
branch.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import io
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
from typing import Iterable

REMOTE_BRANCH = "feat/executable-rvcim-v0-2"
REMOTE_REF = f"refs/remotes/origin/{REMOTE_BRANCH}"
ARCHIVE_SHA256 = "c1f21cea9f7e48ae4b1546ddf34e4744e00ec244fe4f987e4f2466657b607d8d"
ORIGINAL_PDF_SHA256 = "4ded46a5fee179182f40f671ab1345453dceda8e534b713eee775d628cf65d2e"
ORIGINAL_TEX_SHA256 = "6f0d0d7f47df6bdb38ff41bca32b5b5108d7254f07825b069349e53f2c3ad5b7"

RESTORE_PATHS = (
    "paper/nashs_cage_rvcim_v0_1.tex",
    "paper/nashs_cage_rvcim_v0_1.pdf",
    "paper/nashs_cage_rvcim_v0_2.tex",
    "paper/nashs_cage_rvcim_v0_2.pdf",
    "paper/references.bib",
    "simulation/rvcim_sim.py",
    "artifacts/reference_run",
)


def run_git(*args: str, check: bool = True) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git", *args],
        check=check,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def ensure_archive_ref() -> None:
    if run_git("rev-parse", "--verify", REMOTE_REF, check=False).returncode == 0:
        return
    print(f"Fetching archive branch {REMOTE_BRANCH!r} ...")
    run_git(
        "fetch",
        "--no-tags",
        "origin",
        f"{REMOTE_BRANCH}:{REMOTE_REF}",
    )


def read_archive() -> bytes:
    ensure_archive_ref()
    encoded_parts: list[bytes] = []
    for index in range(8):
        path = f".bootstrap/text.{index:02d}"
        result = run_git("show", f"{REMOTE_REF}:{path}")
        encoded_parts.append(b"".join(result.stdout.split()))
    encoded = b"".join(encoded_parts)
    archive = base64.b64decode(encoded, validate=True)
    digest = hashlib.sha256(archive).hexdigest()
    if digest != ARCHIVE_SHA256:
        raise RuntimeError(
            f"Release archive checksum mismatch: expected {ARCHIVE_SHA256}, got {digest}"
        )
    return archive


def safe_members(tar: tarfile.TarFile, destination: Path) -> Iterable[tarfile.TarInfo]:
    root = destination.resolve()
    for member in tar.getmembers():
        if member.issym() or member.islnk():
            raise RuntimeError(f"Refusing archive link: {member.name}")
        target = (destination / member.name).resolve()
        if os.path.commonpath((str(root), str(target))) != str(root):
            raise RuntimeError(f"Refusing unsafe archive member: {member.name}")
        yield member


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def locate_release_root(extracted: Path) -> Path:
    expected = extracted / "paper" / "nashs_cage_rvcim_v0_1.pdf"
    if expected.is_file():
        return extracted
    directories = [entry for entry in extracted.iterdir() if entry.is_dir()]
    if len(directories) == 1 and (
        directories[0] / "paper" / "nashs_cage_rvcim_v0_1.pdf"
    ).is_file():
        return directories[0]
    raise RuntimeError("The verified archive does not contain the expected release tree")


def copy_entry(source: Path, destination: Path, overwrite: bool) -> None:
    if destination.exists() and not overwrite:
        raise FileExistsError(
            f"{destination} already exists; rerun with --overwrite to replace it"
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    if source.is_dir():
        shutil.copytree(source, destination, dirs_exist_ok=overwrite)
    else:
        shutil.copy2(source, destination)


def restore(destination: Path, overwrite: bool) -> None:
    archive = read_archive()
    with tempfile.TemporaryDirectory(prefix="nash-cage-release-") as temporary:
        extracted = Path(temporary)
        with tarfile.open(fileobj=io.BytesIO(archive), mode="r:xz") as tar:
            tar.extractall(extracted, members=safe_members(tar, extracted))
        root = locate_release_root(extracted)

        pdf = root / "paper" / "nashs_cage_rvcim_v0_1.pdf"
        tex = root / "paper" / "nashs_cage_rvcim_v0_1.tex"
        if sha256(pdf) != ORIGINAL_PDF_SHA256:
            raise RuntimeError("Original v0.1 PDF checksum mismatch")
        if sha256(tex) != ORIGINAL_TEX_SHA256:
            raise RuntimeError("Original v0.1 TeX checksum mismatch")

        for relative in RESTORE_PATHS:
            source = root / relative
            if not source.exists():
                raise RuntimeError(f"Missing expected release entry: {relative}")
            copy_entry(source, destination / relative, overwrite=overwrite)

    print("Restored the complete verified release tree.")
    print(f"  destination: {destination.resolve()}")
    print(f"  original PDF SHA-256: {ORIGINAL_PDF_SHA256}")
    print(f"  original TeX SHA-256: {ORIGINAL_TEX_SHA256}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--destination",
        type=Path,
        default=Path.cwd(),
        help="repository working tree to receive restored files (default: current directory)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="replace existing generated or large release files",
    )
    args = parser.parse_args()
    restore(args.destination, overwrite=args.overwrite)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
