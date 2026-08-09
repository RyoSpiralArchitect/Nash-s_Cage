#!/usr/bin/env python3
"""Replay the declared reference command and compare deterministic outputs."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path
from typing import Any, Mapping

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from simulation import rvcim_sim as sim


def load_receipt(path: Path) -> Mapping[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise ValueError("receipt root must be an object")
    return value


def has_symlink_component(root: Path, relative: Path) -> bool:
    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            return True
    return False


def checked_repository_path(
    root: Path,
    candidate: Path,
    label: str,
    failures: list[str],
) -> Path | None:
    """Resolve one repository path without accepting symlink traversal."""

    candidate = candidate if candidate.is_absolute() else root / candidate
    try:
        relative = candidate.absolute().relative_to(root)
    except ValueError:
        failures.append(f"{label}: path escapes repository root")
        return None
    if has_symlink_component(root, relative):
        failures.append(f"{label}: path must not contain symlinks")
        return None
    resolved = candidate.resolve()
    try:
        resolved.relative_to(root)
    except ValueError:
        failures.append(f"{label}: resolved path escapes repository root")
        return None
    return resolved


def verify_replay(root: Path, reference_dir: Path) -> list[str]:
    failures: list[str] = []
    lexical_root = root.absolute()
    root = root.resolve()
    if reference_dir.is_absolute():
        reference_absolute = reference_dir.absolute()
        reference_relative: Path | None = None
        for candidate_root in (lexical_root, root):
            try:
                reference_relative = reference_absolute.relative_to(candidate_root)
                break
            except ValueError:
                continue
        if reference_relative is None or ".." in reference_relative.parts:
            return ["reference directory: path escapes repository root"]
        reference_dir = root / reference_relative
    checked_reference = checked_repository_path(
        root, reference_dir, "reference directory", failures
    )
    if checked_reference is None:
        return failures
    reference_dir = checked_reference
    if not reference_dir.is_dir():
        return ["reference directory: missing regular directory"]

    receipt_path = reference_dir / "receipt.json"
    checked_receipt = checked_repository_path(root, receipt_path, "receipt", failures)
    if checked_receipt is None or not checked_receipt.is_file():
        if checked_receipt is not None:
            failures.append("receipt: missing regular file")
        return failures

    receipt = load_receipt(checked_receipt)
    inputs = receipt.get("inputs")
    if not isinstance(inputs, Mapping):
        return ["receipt inputs must be an object"]
    for name in ("config", "source"):
        value = inputs.get(name)
        if not isinstance(value, str) or not value:
            failures.append(f"receipt input {name} must be a non-empty path")
            continue
        checked_input = checked_repository_path(
            root, reference_dir / value, f"receipt input {name}", failures
        )
        if checked_input is not None and not checked_input.is_file():
            failures.append(f"receipt input {name}: missing regular file")

    for name in sorted(sim.OUTPUT_HASH_FILES):
        checked_output = checked_repository_path(
            root, reference_dir / name, f"committed output {name}", failures
        )
        if checked_output is not None and not checked_output.is_file():
            failures.append(f"committed output {name}: missing regular file")
    if failures:
        return failures

    failures = sim.verify_receipt(checked_receipt)
    if failures:
        return ["committed receipt: " + failure for failure in failures]

    command = receipt["command"]
    config_path = (reference_dir / inputs["config"]).resolve()

    with tempfile.TemporaryDirectory(prefix="nash-cage-reference-replay-") as tmp:
        replay_dir = Path(tmp) / "reference_run"
        sim.run_experiment(
            cfg_path=config_path,
            episodes=command["episodes"],
            seed=command["seed"],
            out_dir=replay_dir,
            arms=tuple(command["arms"]),
            overwrite=False,
            overrides=tuple(command["overrides"]),
        )
        for name in sorted(sim.OUTPUT_HASH_FILES):
            committed = reference_dir / name
            replayed = replay_dir / name
            if committed.read_bytes() != replayed.read_bytes():
                failures.append(f"replay mismatch: {name}")
    return failures


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument(
        "--reference-dir",
        type=Path,
        default=Path("artifacts/reference_run"),
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    root = args.root.resolve()
    reference_dir = args.reference_dir
    if not reference_dir.is_absolute():
        reference_dir = root / reference_dir
    try:
        failures = verify_replay(root, reference_dir)
    except (OSError, ValueError, KeyError, TypeError, sim.ConfigError) as exc:
        failures = [f"cannot replay reference: {exc}"]
    if failures:
        for failure in failures:
            print(f"reference replay error: {failure}", file=sys.stderr)
        return 1
    print(
        f"OK: replayed and byte-compared {len(sim.OUTPUT_HASH_FILES)} reference outputs"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
