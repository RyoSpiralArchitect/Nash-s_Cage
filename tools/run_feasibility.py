#!/usr/bin/env python3
"""Run and replay the fixed, failure-first v0.3 F0 experiment (no live actions)."""

from __future__ import annotations

import argparse
import csv
import dataclasses
import hashlib
import io
import json
import math
import sys
from pathlib import Path
from statistics import fmean
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from simulation import feasibility as model
from simulation import rvcim_sim as legacy

PLAN_PATH = "simulation/configs/feasibility_stress_plan.json"
CONFIG_PATH = "simulation/configs/feasibility_v03.json"
INPUT_FILES = (
    "simulation/__init__.py",
    "simulation/rvcim_sim.py",
    "simulation/feasibility.py",
    "simulation/configs/minimal.json",
    CONFIG_PATH,
    PLAN_PATH,
    "docs/FEASIBILITY_V03_CONTRACT.md",
    "tools/run_feasibility.py",
)
DATA_FILES = frozenset({
    "episodes.csv", "summary.json", "trace.csv", "resolved_plan.json", "comparison.md"
})
OUTPUT_FILES = DATA_FILES | {"receipt.json"}
FORMAT = "nash-feasibility-experiment/v1"
CLAIM = "F0 synthetic experiment; not empirical validation, a safety certificate, or authority to act."
NUMERIC_DECIMALS = 9
NUMERIC_ENCODING = "finite floats rounded to 9 decimal places; missing values preserved"


def canonical_numbers(value: Any) -> Any:
    """Round exports, never controller inputs; hide no missing/nonfinite values."""
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("non-finite numeric value")
        rounded = round(value, NUMERIC_DECIMALS)
        return 0.0 if rounded == 0.0 else rounded
    if isinstance(value, dict):
        return {key: canonical_numbers(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [canonical_numbers(item) for item in value]
    return value


def json_bytes(value: Any) -> bytes:
    return (json.dumps(canonical_numbers(value), sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")


def digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


# A receipt must describe the source loaded by this process, not edited files
# that appeared after import. The CLI always starts a fresh interpreter.
LOADED_SOURCE_HASHES = {
    name: digest((ROOT / name).read_bytes()) for name in INPUT_FILES if name.endswith(".py")
}


def csv_bytes(rows: list[dict[str, Any]]) -> bytes:
    if not rows:
        raise ValueError("CSV output must have rows")
    fields = sorted(rows[0])
    handle = io.StringIO(newline="")
    writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        if set(row) != set(fields):
            raise ValueError("inconsistent CSV schema")
        for value in row.values():
            if isinstance(value, float) and not math.isfinite(value):
                raise ValueError("non-finite CSV value")
        writer.writerow(canonical_numbers(row))
    return handle.getvalue().encode("utf-8")


def positive_int(value: Any, label: str, *, zero: bool = False) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < (0 if zero else 1):
        raise ValueError(f"{label}: invalid integer")


def validate_plan(plan: Mapping[str, Any]) -> None:
    required = {
        "format", "study_id", "claim_level", "registration_status", "legacy_source_sha256",
        "legacy_config_sha256", "phases", "controllers", "trace_episodes_per_seed", "scenarios",
    }
    if not isinstance(plan, dict) or set(plan) != required:
        raise ValueError("plan must contain exactly the declared fields")
    if plan["format"] != "nash-feasibility-stress-plan/v1" or plan["claim_level"] != "F0":
        raise ValueError("invalid plan format or claim level")
    if plan["controllers"] != ["threshold", "threshold_hysteresis", "reserve"]:
        raise ValueError("plan must retain all three declared controllers")
    if not isinstance(plan["study_id"], str) or not plan["study_id"]:
        raise ValueError("study_id must be a nonempty string")
    if not isinstance(plan["registration_status"], str) or not plan["registration_status"]:
        raise ValueError("registration_status must be a nonempty string")
    for key in ("legacy_source_sha256", "legacy_config_sha256"):
        value = plan[key]
        if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
            raise ValueError("legacy identities must be lowercase SHA-256 digests")
    positive_int(plan["trace_episodes_per_seed"], "trace_episodes_per_seed")
    if not isinstance(plan["phases"], dict) or set(plan["phases"]) != {"development", "evaluation"}:
        raise ValueError("both development and evaluation phases are required")
    used: set[int] = set()
    for phase in plan["phases"].values():
        if not isinstance(phase, dict) or set(phase) != {"master_seeds", "episodes_per_seed"}:
            raise ValueError("invalid phase fields")
        positive_int(phase["episodes_per_seed"], "episodes_per_seed")
        seeds = phase["master_seeds"]
        if not isinstance(seeds, list) or not seeds:
            raise ValueError("master_seeds must be a nonempty list")
        for seed in seeds:
            positive_int(seed, "master_seed", zero=True)
            if seed in used:
                raise ValueError("master seeds must be unique across both phases")
            used.add(seed)
        if plan["trace_episodes_per_seed"] > phase["episodes_per_seed"]:
            raise ValueError("trace episode count exceeds phase episode count")
    if not isinstance(plan["scenarios"], list) or not plan["scenarios"]:
        raise ValueError("scenarios must be a nonempty list")
    ids: set[str] = set()
    allowed = {f.name for f in dataclasses.fields(model.FeasibilityConfig)} - {"base", "schema_version"}
    for scenario in plan["scenarios"]:
        if not isinstance(scenario, dict) or set(scenario) != {"id", "config_overrides", "environment_overrides"}:
            raise ValueError("invalid scenario fields")
        name = scenario["id"]
        if not isinstance(name, str) or not name or name in ids:
            raise ValueError("scenario ids must be unique nonempty strings")
        ids.add(name)
        overrides = scenario["config_overrides"]
        if not isinstance(overrides, dict) or not set(overrides) <= allowed:
            raise ValueError("unknown scenario configuration override")
        env = scenario["environment_overrides"]
        if not isinstance(env, dict) or not set(env) <= {
            "true_boundary_scale", "model_boundary_shift", "observation_bias_shift"
        }:
            raise ValueError("unknown environment override")
        for key, value in env.items():
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError("environment overrides must be finite numbers")
            if key == "true_boundary_scale" and value <= 0:
                raise ValueError("true_boundary_scale must be positive")


def load_inputs() -> tuple[model.FeasibilityConfig, dict[str, Any]]:
    plan = json.loads((ROOT / PLAN_PATH).read_text(encoding="utf-8"))
    validate_plan(plan)
    for path, field in (
        ("simulation/rvcim_sim.py", "legacy_source_sha256"),
        ("simulation/configs/minimal.json", "legacy_config_sha256"),
    ):
        if digest((ROOT / path).read_bytes()) != plan[field]:
            raise ValueError(f"preserved legacy identity mismatch: {path}")
    return model.load_config(ROOT / CONFIG_PATH), plan


def transform_environment(environment: legacy.Environment, patch: Mapping[str, float]) -> legacy.Environment:
    return dataclasses.replace(
        environment,
        true_boundary=environment.true_boundary * patch.get("true_boundary_scale", 1.0),
        model_boundaries=tuple(x + patch.get("model_boundary_shift", 0.0) for x in environment.model_boundaries),
        observation_bias=environment.observation_bias + patch.get("observation_bias_shift", 0.0),
    )


def summarize(episodes: list[dict[str, Any]], plan: Mapping[str, Any], phase: str) -> dict[str, Any]:
    groups: list[dict[str, Any]] = []
    paired: list[dict[str, Any]] = []
    for scenario in plan["scenarios"]:
        name = scenario["id"]
        selected = [row for row in episodes if row["scenario"] == name]
        by_controller = {}
        for controller in plan["controllers"]:
            rows = [row for row in selected if row["controller"] == controller]
            by_controller[controller] = {(row["master_seed"], row["episode"]): row for row in rows}
            record = {"scenario": name, "controller": controller, "episodes": len(rows)}
            for key in ("irreversible_entry", "justice_floor_violation"):
                record[key + "_count"] = sum(row[key] for row in rows)
            for key in (
                "total_cost", "remaining_budget", "budget_exhausted_steps", "active_emergency_steps",
                "effective_emergency_steps", "requested_normal_steps", "unknown_steps", "final_pressure",
            ):
                record[key + "_mean"] = fmean(row[key] for row in rows)
            groups.append(record)
        for baseline in ("threshold", "threshold_hysteresis"):
            reserve = by_controller["reserve"]
            other = by_controller[baseline]
            if set(reserve) != set(other):
                raise ValueError("unpaired controller outcomes")
            counts = {"reserve_only_success": 0, "baseline_only_success": 0, "both_success": 0, "both_failure": 0}
            cost_deltas = []
            for key in reserve:
                a, b = reserve[key], other[key]
                if a["environment_seed"] != b["environment_seed"]:
                    raise ValueError("paired environment seed mismatch")
                fail_a, fail_b = bool(a["irreversible_entry"]), bool(b["irreversible_entry"])
                label = ("both_failure" if fail_a else "both_success") if fail_a == fail_b else (
                    "baseline_only_success" if fail_a else "reserve_only_success"
                )
                counts[label] += 1
                cost_deltas.append(a["total_cost"] - b["total_cost"])
            paired.append({
                "scenario": name, "baseline": baseline, "pairs": len(reserve), **counts,
                "reserve_minus_baseline_cost_mean": fmean(cost_deltas),
            })
    return {
        "format": FORMAT, "model_version": model.VERSION, "claim_level": "F0", "claim_boundary": CLAIM,
        "study_id": plan["study_id"], "phase": phase,
        "comparison_scope": "Identical capability coefficients and initial budget, not identical actual spending.",
        "statistical_scope": "Descriptive synthetic paired outcomes; no universal ranking or empirical causal claim.",
        "groups": groups, "paired_comparisons": paired,
    }


def render_comparison(summary: Mapping[str, Any]) -> bytes:
    lines = [
        "# Failure-first feasibility experiment", "", "> " + CLAIM, "",
        "Phase: " + summary["phase"] + "; model: " + model.VERSION + ".", "",
        "Same capability parameters and initial budget; realized cost is reported, not forced equal.", "",
        "| Scenario | Controller | Irreversible / episodes | Justice violations | Mean cost | Mean emergency-active steps | Mean unknown steps |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for row in summary["groups"]:
        lines.append(
            f"| {row['scenario']} | {row['controller']} | {row['irreversible_entry_count']} / {row['episodes']} | "
            f"{row['justice_floor_violation_count']} | {row['total_cost_mean']:.6f} | "
            f"{row['active_emergency_steps_mean']:.3f} | {row['unknown_steps_mean']:.3f} |"
        )
    lines.extend(["", "All scenarios, unfavorable outcomes, and paired comparisons are retained in summary.json.",
                  "Requested/active/effective modes and delivered resources are distinct. Positive CR is not a feasibility proof.",
                  "Missing evidence is not safety; unknown-period behavior is a declared fallback assumption.", ""])
    return "\n".join(lines).encode("utf-8")


def compute_data(config: model.FeasibilityConfig, plan: dict[str, Any], phase: str) -> dict[str, bytes]:
    validate_plan(plan)
    if phase not in plan["phases"]:
        raise ValueError("unknown phase")
    sample = plan["phases"][phase]
    episodes: list[dict[str, Any]] = []
    traces: list[dict[str, Any]] = []
    resolved = []
    for scenario in plan["scenarios"]:
        cfg = dataclasses.replace(config, **scenario["config_overrides"])
        cfg.validate()
        resolved.append({"scenario": scenario["id"], "config": cfg.to_mapping(), "environment_overrides": scenario["environment_overrides"]})
        for master_seed in sample["master_seeds"]:
            for episode in range(sample["episodes_per_seed"]):
                seed = legacy.stable_seed(master_seed, "environment", episode)
                environment = transform_environment(
                    legacy.sample_environment(cfg.base, seed, episode), scenario["environment_overrides"]
                )
                for controller in plan["controllers"]:
                    metrics, trace = model.run_episode(
                        cfg, controller, environment, collect_trace=episode < plan["trace_episodes_per_seed"]
                    )
                    labels = {"scenario": scenario["id"], "master_seed": master_seed, "controller": controller, "phase": phase}
                    episodes.append({**metrics, **labels})
                    traces.extend({**row, **labels} for row in trace)
    summary = summarize(episodes, plan, phase)
    return {
        "episodes.csv": csv_bytes(episodes), "trace.csv": csv_bytes(traces),
        "summary.json": json_bytes(summary), "comparison.md": render_comparison(summary),
        "resolved_plan.json": json_bytes({"plan": plan, "phase": phase, "scenarios": resolved}),
    }


def source_hashes() -> dict[str, str]:
    hashes = {}
    for name in INPUT_FILES:
        current = ROOT
        for part in Path(name).parts:
            current = current / part
            if current.is_symlink():
                raise ValueError(f"input symlink is not allowed: {name}")
        hashes[name] = digest(current.read_bytes())
    if any(hashes[name] != value for name, value in LOADED_SOURCE_HASHES.items()):
        raise ValueError("loaded Python sources changed; start a fresh process")
    return hashes


def build_bundle(phase: str) -> dict[str, bytes]:
    before = source_hashes()
    config, plan = load_inputs()
    data = compute_data(config, plan, phase)
    if before != source_hashes():
        raise ValueError("inputs changed during computation")
    receipt = {
        "format": FORMAT, "model_version": model.VERSION, "claim_level": "F0", "claim_boundary": CLAIM,
        "study_id": plan["study_id"], "phase": phase,
        "numeric_encoding": NUMERIC_ENCODING,
        "input_sha256": before, "output_sha256": {name: digest(data[name]) for name in sorted(data)},
        "trust_model": "internal consistency only; no external attestation or empirical validity",
    }
    return {**data, "receipt.json": json_bytes(receipt)}


def publish_new(output: Path, bundle: Mapping[str, bytes]) -> None:
    if set(bundle) != OUTPUT_FILES:
        raise ValueError("incomplete bundle")
    if output.exists() or output.is_symlink():
        raise FileExistsError(f"output already exists; choose a new path: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.mkdir()  # exclusive reservation; never replace even an empty directory
    for name in sorted(DATA_FILES) + ["receipt.json"]:
        with (output / name).open("xb") as handle:
            handle.write(bundle[name])


def verify_bundle(output: Path, *, replay: bool = False) -> list[str]:
    if output.is_symlink() or not output.is_dir():
        return ["output must be a regular directory, not a symlink"]
    entries = list(output.iterdir())
    if {p.name for p in entries} != OUTPUT_FILES:
        return ["output must contain exactly the six declared files"]
    if any(p.is_symlink() or not p.is_file() for p in entries):
        return ["output contains nonregular files or symlinks"]
    try:
        receipt = json.loads((output / "receipt.json").read_text(encoding="utf-8"))
        if not isinstance(receipt, dict):
            return ["receipt must be an object"]
        config, plan = load_inputs()
        expected = {
            "format": FORMAT, "model_version": model.VERSION, "claim_level": "F0", "claim_boundary": CLAIM,
            "study_id": plan["study_id"], "phase": receipt.get("phase"),
            "numeric_encoding": NUMERIC_ENCODING,
            "input_sha256": source_hashes(), "output_sha256": receipt.get("output_sha256"),
            "trust_model": "internal consistency only; no external attestation or empirical validity",
        }
        if receipt != expected or receipt.get("phase") not in plan["phases"]:
            return ["receipt metadata or current input hashes do not match"]
        hashes = receipt.get("output_sha256")
        if not isinstance(hashes, dict) or set(hashes) != DATA_FILES:
            return ["receipt has an invalid output hash set"]
        failures = [f"hash mismatch: {name}" for name in sorted(DATA_FILES)
                    if hashes[name] != digest((output / name).read_bytes())]
        if failures:
            return failures
        if replay:
            computed = build_bundle(receipt["phase"])
            failures.extend(f"replay mismatch: {name}" for name in sorted(OUTPUT_FILES)
                            if (output / name).read_bytes() != computed[name])
        return failures
    except (OSError, ValueError, TypeError, KeyError) as exc:
        return [f"invalid experiment bundle: {exc}"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run")
    run.add_argument("--out", type=Path, required=True)
    run.add_argument("--phase", choices=("development", "evaluation"), default="evaluation")
    verify = sub.add_parser("verify")
    verify.add_argument("--out", type=Path, required=True)
    verify.add_argument("--replay", action="store_true")
    args = parser.parse_args()
    try:
        if args.command == "run":
            if args.out.exists() or args.out.is_symlink():
                raise FileExistsError(f"output already exists: {args.out}; choose a new path")
            bundle = build_bundle(args.phase)
            publish_new(args.out, bundle)
            print(f"OK: {args.phase} F0 experiment written to {args.out}")
        else:
            failures = verify_bundle(args.out, replay=args.replay)
            if failures:
                for failure in failures:
                    print(f"feasibility verification error: {failure}", file=sys.stderr)
                return 1
            print("OK: feasibility bundle verified" + (" and replayed byte-for-byte" if args.replay else ""))
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(f"feasibility error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
