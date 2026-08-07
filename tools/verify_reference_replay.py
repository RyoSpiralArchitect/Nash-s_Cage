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


def verify_replay(root: Path, reference_dir: Path) -> list[str]:
    receipt_path = reference_dir / "receipt.json"
    failures = sim.verify_receipt(receipt_path)
    if failures:
        return ["committed receipt: " + failure for failure in failures]

    receipt = load_receipt(receipt_path)
    command = receipt["command"]
    inputs = receipt["inputs"]
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
        failures = verify_replay(root, reference_dir.resolve())
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
