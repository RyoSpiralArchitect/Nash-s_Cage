#!/usr/bin/env python3
"""Fail-closed verification for the committed Nash's Cage release tree."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Mapping


MANIFEST_FORMAT = "nashs-cage-release-manifest/v1"
RELEASE = "v0.2.0"
RELEASE_STATUS = "recovery"
RELEASE_DATE = "2026-08-07"
CLAIM_LEVEL = "F0"
CLAIM_BOUNDARY = (
    "Structural toy only; not calibrated, predictive, empirically validating, "
    "or a policy recommendation."
)
REFERENCE_COMMAND = {
    "arms": [
        "weak_coupling",
        "nominal_trigger",
        "robust_reserve",
        "full_rvcim",
    ],
    "episodes": 64,
    "overrides": [],
    "seed": 7,
}
REFERENCE_INPUTS = {
    "config": "../../simulation/configs/minimal.json",
    "source": "../../simulation/rvcim_sim.py",
}
REQUIRED_FILES = frozenset(
    {
        "paper/nashs_cage_rvcim_v0_1.tex",
        "paper/nashs_cage_rvcim_v0_1.pdf",
        "paper/nashs_cage_rvcim_v0_2.tex",
        "paper/nashs_cage_rvcim_v0_2.pdf",
        "paper/references.bib",
        "simulation/rvcim_sim.py",
        "simulation/configs/minimal.json",
        "artifacts/reference_run/summary.csv",
        "artifacts/reference_run/episodes.csv",
        "artifacts/reference_run/trace.csv",
        "artifacts/reference_run/comparison.md",
        "artifacts/reference_run/resolved_config.json",
        "artifacts/reference_run/receipt.json",
    }
)
PRESERVED_V0_1 = {
    "paper/nashs_cage_rvcim_v0_1.tex": (
        66_713,
        "6f0d0d7f47df6bdb38ff41bca32b5b5108d7254f07825b069349e53f2c3ad5b7",
    ),
    "paper/nashs_cage_rvcim_v0_1.pdf": (
        389_459,
        "4ded46a5fee179182f40f671ab1345453dceda8e534b713eee775d628cf65d2e",
    ),
}
EXPECTED_FILE_PROVENANCE = {
    "paper/nashs_cage_rvcim_v0_1.tex": "exact-preserved-upload",
    "paper/nashs_cage_rvcim_v0_1.pdf": "exact-preserved-upload",
    "paper/nashs_cage_rvcim_v0_2.tex": "regenerated-from-preserved-v0.1",
    "paper/nashs_cage_rvcim_v0_2.pdf": "regenerated-from-preserved-v0.1",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> Mapping[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise ValueError("manifest root must be an object")
    return value


def verify(root: Path, manifest_path: Path) -> list[str]:
    failures: list[str] = []
    try:
        manifest = load_json(manifest_path)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        return [f"cannot read manifest: {exc}"]

    if manifest.get("format") != MANIFEST_FORMAT:
        failures.append(
            f"unsupported format: {manifest.get('format')!r}; expected {MANIFEST_FORMAT!r}"
        )
    for field, expected in (
        ("release", RELEASE),
        ("release_status", RELEASE_STATUS),
        ("release_date", RELEASE_DATE),
        ("claim_level", CLAIM_LEVEL),
        ("claim_boundary", CLAIM_BOUNDARY),
    ):
        if manifest.get(field) != expected:
            failures.append(f"{field} must be {expected!r}")

    provenance = manifest.get("provenance")
    if not isinstance(provenance, Mapping):
        failures.append("provenance must be an object")
    else:
        if provenance.get("v0_1") != "exact-preserved-upload":
            failures.append("provenance.v0_1 must be exact-preserved-upload")
        if provenance.get("v0_2") != "regenerated-from-preserved-v0.1":
            failures.append(
                "provenance.v0_2 must be regenerated-from-preserved-v0.1"
            )
        if provenance.get("historical_v0_2_byte_identity") != "not-claimed":
            failures.append(
                "provenance.historical_v0_2_byte_identity must be not-claimed"
            )
        if not isinstance(provenance.get("note"), str) or not provenance.get(
            "note"
        ):
            failures.append("provenance.note must be a non-empty string")

    files = manifest.get("files")
    if not isinstance(files, Mapping):
        return failures + ["files must be an object"]

    recorded = set(files)
    missing_records = sorted(REQUIRED_FILES - recorded)
    extra_records = sorted(recorded - REQUIRED_FILES)
    if missing_records:
        failures.append("manifest missing required records: " + ", ".join(missing_records))
    if extra_records:
        failures.append("manifest has unexpected records: " + ", ".join(extra_records))

    root = root.resolve()
    for relative in sorted(REQUIRED_FILES & recorded):
        entry = files[relative]
        if not isinstance(entry, Mapping):
            failures.append(f"{relative}: record must be an object")
            continue
        target = (root / relative).resolve()
        try:
            target.relative_to(root)
        except ValueError:
            failures.append(f"{relative}: path escapes repository root")
            continue
        if not target.is_file():
            failures.append(f"{relative}: missing regular file")
            continue
        expected_bytes = entry.get("bytes")
        expected_sha = entry.get("sha256")
        if (
            isinstance(expected_bytes, bool)
            or not isinstance(expected_bytes, int)
            or expected_bytes < 0
        ):
            failures.append(f"{relative}: bytes must be a non-negative integer")
        if (
            not isinstance(expected_sha, str)
            or len(expected_sha) != 64
            or any(character not in "0123456789abcdef" for character in expected_sha)
        ):
            failures.append(f"{relative}: sha256 must be lowercase hexadecimal")
        if not isinstance(entry.get("role"), str) or not entry.get("role"):
            failures.append(f"{relative}: role must be a non-empty string")
        actual_bytes = target.stat().st_size
        actual_sha = sha256_file(target)
        if expected_bytes != actual_bytes:
            failures.append(
                f"{relative}: size mismatch expected={expected_bytes} actual={actual_bytes}"
            )
        if expected_sha != actual_sha:
            failures.append(
                f"{relative}: hash mismatch expected={expected_sha} actual={actual_sha}"
            )

    for relative, (expected_bytes, expected_sha) in PRESERVED_V0_1.items():
        entry = files.get(relative)
        if not isinstance(entry, Mapping):
            continue
        if entry.get("bytes") != expected_bytes or entry.get("sha256") != expected_sha:
            failures.append(f"{relative}: preserved v0.1 identity changed")

    for relative, expected in EXPECTED_FILE_PROVENANCE.items():
        entry = files.get(relative)
        if isinstance(entry, Mapping) and entry.get("provenance") != expected:
            failures.append(f"{relative}: provenance must be {expected}")

    receipt_path = root / "artifacts/reference_run/receipt.json"
    try:
        receipt = load_json(receipt_path)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        failures.append(f"cannot inspect reference receipt: {exc}")
    else:
        if receipt.get("receipt_version") != 2:
            failures.append("reference receipt_version must be 2")
        if receipt.get("model_version") != "0.2.0":
            failures.append("reference model_version must be 0.2.0")
        if receipt.get("schema_version") != 1:
            failures.append("reference schema_version must be 1")
        if receipt.get("claim_level") != CLAIM_LEVEL:
            failures.append("reference claim_level must be F0")
        if receipt.get("claim_boundary") != CLAIM_BOUNDARY:
            failures.append("reference claim_boundary does not match release")
        if receipt.get("command") != REFERENCE_COMMAND:
            failures.append("reference command does not match the release contract")
        if receipt.get("inputs") != REFERENCE_INPUTS:
            failures.append("reference inputs do not match the release contract")

    return failures


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--manifest", type=Path, default=Path("RELEASE_MANIFEST.json"))
    return parser


def main() -> int:
    args = build_parser().parse_args()
    root = args.root.resolve()
    manifest = args.manifest
    if not manifest.is_absolute():
        manifest = root / manifest
    failures = verify(root, manifest)
    if failures:
        for failure in failures:
            print(f"release verification error: {failure}", file=sys.stderr)
        return 1
    print(f"OK: verified {len(REQUIRED_FILES)} committed release files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
