#!/usr/bin/env python3
"""Run and replay the fixed, failure-first sustained v0.4 F0 experiment."""

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

import simulation as simulation_package
from simulation import feasibility
from simulation import rvcim_sim as legacy
from simulation import sustained

PLAN_PATH = "simulation/configs/sustained_stress_plan.json"
CONFIG_PATH = "simulation/configs/sustained_v04.json"
V03_RECEIPT_PATH = "artifacts/feasibility_v03/receipt.json"
INPUT_FILES = (
    "simulation/__init__.py",
    "simulation/rvcim_sim.py",
    "simulation/configs/minimal.json",
    "simulation/feasibility.py",
    "simulation/configs/feasibility_v03.json",
    V03_RECEIPT_PATH,
    "simulation/sustained.py",
    CONFIG_PATH,
    PLAN_PATH,
    "docs/SUSTAINED_V04_CONTRACT.md",
    "tools/run_sustained.py",
)
DATA_FILES = frozenset({
    "episodes.csv", "summary.json", "trace.csv", "resolved_plan.json", "comparison.md"
})
OUTPUT_FILES = DATA_FILES | {"receipt.json"}
FORMAT = "nash-sustained-experiment/v1"
CLAIM = (
    "F0 synthetic experiment; not an empirical digital twin, deployment controller, "
    "safety certificate, or authority to act."
)
NUMERIC_DECIMALS = 9
NUMERIC_ENCODING = "finite floats rounded to 9 decimal places; missing values preserved"
PRIMARY_COHORT = "primary"
REGRESSION_COHORT = "prior_failure_regression"
V03_CONTROLLERS = ("threshold", "threshold_hysteresis", "reserve")
V04_ONLY_METRICS = (
    "assessment_plan_found_steps",
    "assessment_no_candidate_steps",
    "assessment_insufficient_evidence_steps",
    "no_candidate_boundary_steps",
    "no_candidate_braking_steps",
    "no_candidate_budget_steps",
    "selected_plan_normal_steps",
    "selected_plan_precaution_steps",
    "selected_plan_emergency_steps",
    "public_forecast_checked_steps",
    "public_forecast_miss_steps",
    "max_public_forecast_overshoot",
    "min_projected_boundary_margin",
    "min_projected_final_budget",
    "final_assessment_status",
    "final_selected_plan_mode",
)


def canonical_numbers(value: Any) -> Any:
    """Round exports only; preserve missing values and reject nonfinite evidence."""
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
    return (
        json.dumps(canonical_numbers(value), sort_keys=True, indent=2, allow_nan=False) + "\n"
    ).encode("utf-8")


def digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


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


def _sha256_text(value: Any, label: str) -> None:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"{label} must be a lowercase SHA-256 digest")


def _nonnegative_int(value: Any, label: str, *, positive: bool = False) -> None:
    minimum = 1 if positive else 0
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"{label}: invalid integer")


def _finite_override_mapping(
    value: Any, allowed: set[str], label: str
) -> Mapping[str, int | float]:
    if not isinstance(value, dict) or not set(value) <= allowed:
        raise ValueError(f"unknown {label} override")
    for item in value.values():
        if isinstance(item, bool) or not isinstance(item, (int, float)) or not math.isfinite(item):
            raise ValueError(f"{label} overrides must be finite numbers")
    return value


def validate_plan(plan: Mapping[str, Any]) -> None:
    required = {
        "format",
        "study_id",
        "claim_level",
        "registration_status",
        "legacy_source_sha256",
        "legacy_config_sha256",
        "v03_feasibility_source_sha256",
        "v03_feasibility_config_sha256",
        "v03_feasibility_receipt_sha256",
        "phases",
        "controllers",
        "trace_episodes_per_seed",
        "scenarios",
        "prior_failure_cases",
    }
    if not isinstance(plan, dict) or set(plan) != required:
        raise ValueError("plan must contain exactly the declared fields")
    if plan["format"] != "nash-sustained-stress-plan/v1" or plan["claim_level"] != "F0":
        raise ValueError("invalid plan format or claim level")
    if plan["controllers"] != ["reserve", "sustained_reserve"]:
        raise ValueError("controller order must be reserve, sustained_reserve")
    for key in ("study_id", "registration_status"):
        if not isinstance(plan[key], str) or not plan[key]:
            raise ValueError(f"{key} must be a nonempty string")
    for key in (
        "legacy_source_sha256",
        "legacy_config_sha256",
        "v03_feasibility_source_sha256",
        "v03_feasibility_config_sha256",
        "v03_feasibility_receipt_sha256",
    ):
        _sha256_text(plan[key], key)

    _nonnegative_int(plan["trace_episodes_per_seed"], "trace_episodes_per_seed", positive=True)
    if not isinstance(plan["phases"], dict) or set(plan["phases"]) != {
        "development", "evaluation"
    }:
        raise ValueError("both development and evaluation phases are required")
    used_seeds: set[int] = set()
    for phase in plan["phases"].values():
        if not isinstance(phase, dict) or set(phase) != {"master_seeds", "episodes_per_seed"}:
            raise ValueError("invalid phase fields")
        _nonnegative_int(phase["episodes_per_seed"], "episodes_per_seed", positive=True)
        seeds = phase["master_seeds"]
        if not isinstance(seeds, list) or not seeds:
            raise ValueError("master_seeds must be a nonempty list")
        for seed in seeds:
            _nonnegative_int(seed, "master_seed")
            if seed in used_seeds:
                raise ValueError("master seeds must be unique across both phases")
            used_seeds.add(seed)
        if plan["trace_episodes_per_seed"] > phase["episodes_per_seed"]:
            raise ValueError("trace episode count exceeds phase episode count")

    scenarios = plan["scenarios"]
    if not isinstance(scenarios, list) or len(scenarios) != 10:
        raise ValueError("the ten declared scenarios are required")
    feasibility_fields = {
        field.name for field in dataclasses.fields(feasibility.FeasibilityConfig)
    } - {"base", "schema_version"}
    sustained_fields = {
        field.name for field in dataclasses.fields(sustained.SustainedConfig)
    } - {"base", "schema_version"}
    environment_fields = {
        "true_boundary_scale", "model_boundary_shift", "observation_bias_shift"
    }
    scenario_ids: set[str] = set()
    for scenario in scenarios:
        if not isinstance(scenario, dict) or set(scenario) != {
            "id", "feasibility_overrides", "sustained_overrides", "environment_overrides"
        }:
            raise ValueError("invalid scenario fields")
        scenario_id = scenario["id"]
        if not isinstance(scenario_id, str) or not scenario_id or scenario_id in scenario_ids:
            raise ValueError("scenario ids must be unique nonempty strings")
        scenario_ids.add(scenario_id)
        _finite_override_mapping(
            scenario["feasibility_overrides"], feasibility_fields, "feasibility"
        )
        _finite_override_mapping(
            scenario["sustained_overrides"], sustained_fields, "sustained"
        )
        environment_overrides = _finite_override_mapping(
            scenario["environment_overrides"], environment_fields, "environment"
        )
        if environment_overrides.get("true_boundary_scale", 1.0) <= 0:
            raise ValueError("true_boundary_scale must be positive")

    cases = plan["prior_failure_cases"]
    if not isinstance(cases, list) or len(cases) != 11:
        raise ValueError("the eleven declared prior failure cases are required")
    identities: set[tuple[str, int, int]] = set()
    for case in cases:
        if not isinstance(case, dict) or set(case) != {
            "scenario", "master_seed", "episode", "comparator"
        }:
            raise ValueError("invalid prior failure case fields")
        if case["scenario"] not in scenario_ids:
            raise ValueError("prior failure case references an unknown scenario")
        if case["comparator"] not in {"threshold", "threshold_hysteresis"}:
            raise ValueError("prior failure comparator is invalid")
        _nonnegative_int(case["master_seed"], "prior failure master_seed")
        _nonnegative_int(case["episode"], "prior failure episode")
        identity = (case["scenario"], case["master_seed"], case["episode"])
        if identity in identities:
            raise ValueError("prior failure cases must be unique")
        identities.add(identity)


def _validate_frozen_identities(plan: Mapping[str, Any]) -> None:
    identities = (
        ("simulation/rvcim_sim.py", "legacy_source_sha256"),
        ("simulation/configs/minimal.json", "legacy_config_sha256"),
        ("simulation/feasibility.py", "v03_feasibility_source_sha256"),
        ("simulation/configs/feasibility_v03.json", "v03_feasibility_config_sha256"),
        (V03_RECEIPT_PATH, "v03_feasibility_receipt_sha256"),
    )
    for path, field in identities:
        if digest((ROOT / path).read_bytes()) != plan[field]:
            raise ValueError(f"frozen input identity mismatch: {path}")
    receipt = json.loads((ROOT / V03_RECEIPT_PATH).read_text(encoding="utf-8"))
    try:
        anchored = receipt["input_sha256"]
        if (
            receipt["format"] != "nash-feasibility-experiment/v1"
            or receipt["phase"] != "evaluation"
            or anchored["simulation/rvcim_sim.py"] != plan["legacy_source_sha256"]
            or anchored["simulation/configs/minimal.json"] != plan["legacy_config_sha256"]
            or anchored["simulation/feasibility.py"] != plan["v03_feasibility_source_sha256"]
            or anchored["simulation/configs/feasibility_v03.json"]
            != plan["v03_feasibility_config_sha256"]
        ):
            raise ValueError("v0.3 receipt does not anchor the declared frozen inputs")
    except (KeyError, TypeError) as exc:
        raise ValueError("v0.3 receipt is malformed") from exc


def load_inputs() -> tuple[sustained.SustainedConfig, dict[str, Any]]:
    plan = json.loads((ROOT / PLAN_PATH).read_text(encoding="utf-8"))
    validate_plan(plan)
    _validate_frozen_identities(plan)
    config = sustained.load_config(ROOT / CONFIG_PATH)
    config.validate()
    return config, plan


def transform_environment(
    environment: legacy.Environment, patch: Mapping[str, float]
) -> legacy.Environment:
    """Change only the three declared evaluator/environment stress fields."""
    return dataclasses.replace(
        environment,
        true_boundary=environment.true_boundary * patch.get("true_boundary_scale", 1.0),
        model_boundaries=tuple(
            value + patch.get("model_boundary_shift", 0.0)
            for value in environment.model_boundaries
        ),
        observation_bias=(
            environment.observation_bias + patch.get("observation_bias_shift", 0.0)
        ),
    )


def resolve_scenario(
    config: sustained.SustainedConfig, scenario: Mapping[str, Any]
) -> tuple[feasibility.FeasibilityConfig, sustained.SustainedConfig]:
    feasibility_config = dataclasses.replace(
        config.base, **scenario["feasibility_overrides"]
    )
    feasibility_config.validate()
    sustained_config = dataclasses.replace(
        config, base=feasibility_config, **scenario["sustained_overrides"]
    )
    sustained_config.validate()
    return feasibility_config, sustained_config


def _environment_for(
    feasibility_config: feasibility.FeasibilityConfig,
    scenario: Mapping[str, Any],
    master_seed: int,
    episode: int,
) -> legacy.Environment:
    environment_seed = legacy.stable_seed(master_seed, "environment", episode)
    environment = legacy.sample_environment(
        feasibility_config.base, environment_seed, episode
    )
    return transform_environment(environment, scenario["environment_overrides"])


def _normalize_episode_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not rows:
        raise ValueError("experiment produced no episode rows")
    fields: set[str] = set()
    for row in rows:
        fields.update(row)
        if row["controller"] == "sustained_reserve":
            missing = set(V04_ONLY_METRICS) - set(row)
            if missing:
                raise ValueError(f"sustained metrics missing: {', '.join(sorted(missing))}")
    normalized = []
    for row in rows:
        item = {field: row.get(field) for field in fields}
        if row["controller"] != "sustained_reserve":
            for field in V04_ONLY_METRICS:
                item[field] = None
        normalized.append(item)
    return normalized


def _mean(rows: list[Mapping[str, Any]], key: str) -> float | None:
    values = [row[key] for row in rows if row.get(key) is not None]
    return fmean(values) if values else None


def summarize(
    episodes: list[dict[str, Any]], plan: Mapping[str, Any], phase: str
) -> dict[str, Any]:
    primary = [row for row in episodes if row["cohort"] == PRIMARY_COHORT]
    regression = [row for row in episodes if row["cohort"] == REGRESSION_COHORT]
    groups: list[dict[str, Any]] = []
    paired: list[dict[str, Any]] = []
    for scenario in plan["scenarios"]:
        scenario_id = scenario["id"]
        selected = [row for row in primary if row["scenario"] == scenario_id]
        by_controller: dict[str, dict[tuple[int, int], dict[str, Any]]] = {}
        for controller in plan["controllers"]:
            rows = [row for row in selected if row["controller"] == controller]
            by_controller[controller] = {
                (row["master_seed"], row["episode"]): row for row in rows
            }
            record: dict[str, Any] = {
                "scenario": scenario_id,
                "controller": controller,
                "episodes": len(rows),
                "irreversible_entry_count": sum(row["irreversible_entry"] for row in rows),
                "justice_floor_violation_count": sum(
                    row["justice_floor_violation"] for row in rows
                ),
            }
            for key in (
                "total_cost",
                "remaining_budget",
                "unknown_steps",
                "active_emergency_steps",
                "effective_emergency_steps",
                "requested_emergency_steps",
                "assessment_plan_found_steps",
                "assessment_no_candidate_steps",
                "assessment_insufficient_evidence_steps",
                "no_candidate_boundary_steps",
                "no_candidate_braking_steps",
                "no_candidate_budget_steps",
                "selected_plan_normal_steps",
                "selected_plan_precaution_steps",
                "selected_plan_emergency_steps",
                "public_forecast_checked_steps",
                "public_forecast_miss_steps",
                "max_public_forecast_overshoot",
                "min_projected_boundary_margin",
                "min_projected_final_budget",
            ):
                record[key + "_mean"] = _mean(rows, key)
            statuses = [row["final_assessment_status"] for row in rows if row.get("final_assessment_status")]
            modes = [row["final_selected_plan_mode"] for row in rows if row.get("final_selected_plan_mode") is not None]
            record["final_assessment_status_counts"] = (
                {status: statuses.count(status) for status in sorted(set(statuses))}
                if statuses else None
            )
            record["final_selected_plan_mode_counts"] = (
                {str(mode): modes.count(mode) for mode in sorted(set(modes))} if modes else None
            )
            groups.append(record)

        reserve = by_controller["reserve"]
        sustained_rows = by_controller["sustained_reserve"]
        if set(reserve) != set(sustained_rows):
            raise ValueError("unpaired primary outcomes")
        counts = {
            "sustained_only_success": 0,
            "reserve_only_success": 0,
            "both_success": 0,
            "both_failure": 0,
        }
        cost_deltas: list[float] = []
        for identity, reserve_row in reserve.items():
            sustained_row = sustained_rows[identity]
            if reserve_row["environment_seed"] != sustained_row["environment_seed"]:
                raise ValueError("paired environment seed mismatch")
            reserve_failed = bool(reserve_row["irreversible_entry"])
            sustained_failed = bool(sustained_row["irreversible_entry"])
            if reserve_failed == sustained_failed:
                label = "both_failure" if reserve_failed else "both_success"
            else:
                label = "sustained_only_success" if reserve_failed else "reserve_only_success"
            counts[label] += 1
            cost_deltas.append(sustained_row["total_cost"] - reserve_row["total_cost"])
        paired.append({
            "scenario": scenario_id,
            "pairs": len(reserve),
            **counts,
            "sustained_minus_reserve_cost_mean": fmean(cost_deltas),
        })

    regression_table: list[dict[str, Any]] = []
    for case in plan["prior_failure_cases"]:
        matches = [
            row
            for row in regression
            if row["scenario"] == case["scenario"]
            and row["master_seed"] == case["master_seed"]
            and row["episode"] == case["episode"]
        ]
        by_controller = {row["controller"]: row for row in matches}
        if set(by_controller) != {*V03_CONTROLLERS, "sustained_reserve"}:
            raise ValueError("incomplete prior failure regression case")
        environment_seeds = {row["environment_seed"] for row in matches}
        if len(environment_seeds) != 1:
            raise ValueError("regression environment seed mismatch")
        results = {
            controller: {
                "irreversible_entry": by_controller[controller]["irreversible_entry"],
                "justice_floor_violation": by_controller[controller]["justice_floor_violation"],
                "total_cost": by_controller[controller]["total_cost"],
            }
            for controller in (*V03_CONTROLLERS, "sustained_reserve")
        }
        comparator_succeeded = not bool(results[case["comparator"]]["irreversible_entry"])
        reserve_failed = bool(results["reserve"]["irreversible_entry"])
        sustained_failed = bool(results["sustained_reserve"]["irreversible_entry"])
        regression_table.append({
            **case,
            "environment_seed": next(iter(environment_seeds)),
            "results": results,
            "original_comparator_success": comparator_succeeded,
            "reserve_failure": reserve_failed,
            "original_relation_preserved": comparator_succeeded and reserve_failed,
            "sustained_success": not sustained_failed,
            "sustained_failure": sustained_failed,
        })

    return {
        "format": FORMAT,
        "model_version": sustained.VERSION,
        "baseline_model_version": feasibility.VERSION,
        "claim_level": "F0",
        "claim_boundary": CLAIM,
        "study_id": plan["study_id"],
        "phase": phase,
        "cohort_scope": {
            "primary": "Fixed phase scenarios; paired reserve and sustained_reserve only.",
            "prior_failure_regression": (
                "Eleven post-hoc v0.3 losing cases; all four controllers retained and not "
                "mixed into primary groups."
            ),
        },
        "comparison_scope": (
            "Identical sampled environment and feasibility resources within each pair; "
            "realized actions and spending may differ."
        ),
        "statistical_scope": (
            "Descriptive synthetic paired outcomes by scenario; no pooled universal winner "
            "or empirical causal claim."
        ),
        "trace_scope": (
            "Primary sustained_reserve only; first declared episodes per scenario/master seed. "
            "The prior regression lot is not traced."
        ),
        "groups": groups,
        "paired_comparisons": paired,
        "prior_failure_regression": regression_table,
    }


def _display(value: Any, decimals: int = 3) -> str:
    return "n/a" if value is None else f"{value:.{decimals}f}"


def render_comparison(summary: Mapping[str, Any]) -> bytes:
    lines = [
        "# Sustained-plan failure-first experiment",
        "",
        "> " + CLAIM,
        "",
        f"Phase: {summary['phase']}; sustained model: {sustained.VERSION}; baseline: {feasibility.VERSION}.",
        "",
        "## Primary paired cohort",
        "",
        "| Scenario | Controller | Irreversible / episodes | Justice violations | Mean cost | Mean emergency-active steps | Mean plan-found steps | Mean no-candidate steps | Mean boundary / braking / budget rejection steps |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary["groups"]:
        lines.append(
            f"| {row['scenario']} | {row['controller']} | "
            f"{row['irreversible_entry_count']} / {row['episodes']} | "
            f"{row['justice_floor_violation_count']} | {_display(row['total_cost_mean'], 6)} | "
            f"{_display(row['active_emergency_steps_mean'])} | "
            f"{_display(row['assessment_plan_found_steps_mean'])} | "
            f"{_display(row['assessment_no_candidate_steps_mean'])} | "
            f"{_display(row['no_candidate_boundary_steps_mean'])} / "
            f"{_display(row['no_candidate_braking_steps_mean'])} / "
            f"{_display(row['no_candidate_budget_steps_mean'])} |"
        )

    lines.extend([
        "",
        "## Scenario-local paired outcomes",
        "",
        "| Scenario | Pairs | Sustained only succeeds | Reserve only succeeds | Both succeed | Both fail | Mean cost delta (sustained - reserve) |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ])
    for row in summary["paired_comparisons"]:
        lines.append(
            f"| {row['scenario']} | {row['pairs']} | {row['sustained_only_success']} | "
            f"{row['reserve_only_success']} | {row['both_success']} | {row['both_failure']} | "
            f"{_display(row['sustained_minus_reserve_cost_mean'], 6)} |"
        )

    lines.extend([
        "",
        "## Prior v0.3 failure regression lot (post-hoc)",
        "",
        "| Scenario | Seed | Episode | Declared comparator | Threshold | Threshold + hysteresis | Reserve | Sustained reserve | Original relation preserved |",
        "|---|---:|---:|---|---|---|---|---|---|",
    ])
    for case in summary["prior_failure_regression"]:
        outcome = {
            controller: (
                "failure" if case["results"][controller]["irreversible_entry"] else "success"
            )
            for controller in (*V03_CONTROLLERS, "sustained_reserve")
        }
        lines.append(
            f"| {case['scenario']} | {case['master_seed']} | {case['episode']} | "
            f"{case['comparator']} | {outcome['threshold']} | "
            f"{outcome['threshold_hysteresis']} | {outcome['reserve']} | "
            f"{outcome['sustained_reserve']} | "
            f"{'yes' if case['original_relation_preserved'] else 'no'} |"
        )

    lines.extend([
        "",
        "The regression lot is reported separately and is not independent evidence.",
        "No pooled universal winner is computed. A missing candidate means only that the finite declared plan set did not pass.",
        "Projection assumptions, public model boundaries, and synthetic outcomes are not physical or institutional validation.",
        "",
    ])
    return "\n".join(lines).encode("utf-8")


def compute_data(
    config: sustained.SustainedConfig, plan: dict[str, Any], phase: str
) -> dict[str, bytes]:
    validate_plan(plan)
    if phase not in plan["phases"]:
        raise ValueError("unknown phase")
    sample = plan["phases"][phase]
    scenarios = {scenario["id"]: scenario for scenario in plan["scenarios"]}
    resolved: list[dict[str, Any]] = []
    resolved_configs: dict[
        str, tuple[feasibility.FeasibilityConfig, sustained.SustainedConfig]
    ] = {}
    for scenario in plan["scenarios"]:
        feasibility_config, sustained_config = resolve_scenario(config, scenario)
        resolved_configs[scenario["id"]] = feasibility_config, sustained_config
        resolved.append({
            "scenario": scenario["id"],
            "feasibility_config": feasibility_config.to_mapping(),
            "sustained_config": sustained_config.to_mapping(),
            "environment_overrides": scenario["environment_overrides"],
        })

    episodes: list[dict[str, Any]] = []
    traces: list[dict[str, Any]] = []
    for scenario in plan["scenarios"]:
        scenario_id = scenario["id"]
        feasibility_config, sustained_config = resolved_configs[scenario_id]
        for master_seed in sample["master_seeds"]:
            for episode in range(sample["episodes_per_seed"]):
                environment = _environment_for(
                    feasibility_config, scenario, master_seed, episode
                )
                reserve_metrics, _ = feasibility.run_episode(
                    feasibility_config, "reserve", environment, collect_trace=False
                )
                sustained_metrics, trace = sustained.run_episode(
                    sustained_config,
                    environment,
                    collect_trace=episode < plan["trace_episodes_per_seed"],
                )
                if (
                    reserve_metrics["environment_seed"]
                    != sustained_metrics["environment_seed"]
                    or reserve_metrics["episode"] != sustained_metrics["episode"]
                    or reserve_metrics["true_boundary"] != sustained_metrics["true_boundary"]
                ):
                    raise ValueError("primary controllers did not receive the same environment")
                common = {
                    "cohort": PRIMARY_COHORT,
                    "scenario": scenario_id,
                    "master_seed": master_seed,
                    "phase": phase,
                    "case_comparator": None,
                }
                episodes.append({**reserve_metrics, **common, "controller": "reserve"})
                episodes.append({
                    **sustained_metrics, **common, "controller": "sustained_reserve"
                })
                trace_labels = {
                    **common,
                    "controller": "sustained_reserve",
                    "environment_seed": environment.seed,
                }
                traces.extend({**row, **trace_labels} for row in trace)

    for case in plan["prior_failure_cases"]:
        scenario = scenarios[case["scenario"]]
        feasibility_config, sustained_config = resolved_configs[case["scenario"]]
        environment = _environment_for(
            feasibility_config, scenario, case["master_seed"], case["episode"]
        )
        common = {
            "cohort": REGRESSION_COHORT,
            "scenario": case["scenario"],
            "master_seed": case["master_seed"],
            "phase": phase,
            "case_comparator": case["comparator"],
        }
        case_rows = []
        for controller in V03_CONTROLLERS:
            metrics, _ = feasibility.run_episode(
                feasibility_config, controller, environment, collect_trace=False
            )
            case_rows.append({**metrics, **common, "controller": controller})
        metrics, _ = sustained.run_episode(
            sustained_config, environment, collect_trace=False
        )
        case_rows.append({**metrics, **common, "controller": "sustained_reserve"})
        if (
            len({row["environment_seed"] for row in case_rows}) != 1
            or len({row["episode"] for row in case_rows}) != 1
            or len({row["true_boundary"] for row in case_rows}) != 1
        ):
            raise ValueError("regression controllers did not receive the same environment")
        episodes.extend(case_rows)

    episodes = _normalize_episode_rows(episodes)
    summary = summarize(episodes, plan, phase)
    resolved_plan = {
        "plan": plan,
        "phase": phase,
        "scenarios": resolved,
        "trace_scope": summary["trace_scope"],
        "cohort_separation": summary["cohort_scope"],
    }
    return {
        "episodes.csv": csv_bytes(episodes),
        "trace.csv": csv_bytes(traces),
        "summary.json": json_bytes(summary),
        "comparison.md": render_comparison(summary),
        "resolved_plan.json": json_bytes(resolved_plan),
    }


_IMPORTED_SOURCE_PATHS = {
    "simulation/__init__.py": Path(simulation_package.__file__).resolve(),
    "simulation/rvcim_sim.py": Path(legacy.__file__).resolve(),
    "simulation/feasibility.py": Path(feasibility.__file__).resolve(),
    "simulation/sustained.py": Path(sustained.__file__).resolve(),
    "tools/run_sustained.py": Path(__file__).resolve(),
}
LOADED_SOURCE_HASHES = {
    name: digest((ROOT / name).read_bytes()) for name in _IMPORTED_SOURCE_PATHS
}


def source_hashes() -> dict[str, str]:
    hashes: dict[str, str] = {}
    for name in INPUT_FILES:
        current = ROOT
        for part in Path(name).parts:
            current = current / part
            if current.is_symlink():
                raise ValueError(f"input symlink is not allowed: {name}")
        if not current.is_file():
            raise ValueError(f"input must be a regular file: {name}")
        hashes[name] = digest(current.read_bytes())
    for name, imported_path in _IMPORTED_SOURCE_PATHS.items():
        if imported_path != (ROOT / name).resolve():
            raise ValueError(f"loaded Python module path mismatch: {name}")
    if any(hashes[name] != expected for name, expected in LOADED_SOURCE_HASHES.items()):
        raise ValueError("loaded Python sources changed; start a fresh process")
    return hashes


def build_bundle(phase: str) -> dict[str, bytes]:
    before = source_hashes()
    config, plan = load_inputs()
    data = compute_data(config, plan, phase)
    if before != source_hashes():
        raise ValueError("inputs changed during computation")
    receipt = {
        "format": FORMAT,
        "model_version": sustained.VERSION,
        "baseline_model_version": feasibility.VERSION,
        "claim_level": "F0",
        "claim_boundary": CLAIM,
        "study_id": plan["study_id"],
        "phase": phase,
        "numeric_encoding": NUMERIC_ENCODING,
        "input_sha256": before,
        "output_sha256": {name: digest(data[name]) for name in sorted(data)},
        "trust_model": (
            "internal consistency only; no external attestation, empirical validity, "
            "or authorization"
        ),
    }
    return {**data, "receipt.json": json_bytes(receipt)}


def publish_new(output: Path, bundle: Mapping[str, bytes]) -> None:
    if set(bundle) != OUTPUT_FILES:
        raise ValueError("incomplete bundle")
    if output.exists() or output.is_symlink():
        raise FileExistsError(f"output already exists; choose a new path: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.mkdir()
    for name in sorted(DATA_FILES) + ["receipt.json"]:
        with (output / name).open("xb") as handle:
            handle.write(bundle[name])


def verify_bundle(output: Path, *, replay: bool = False) -> list[str]:
    if output.is_symlink() or not output.is_dir():
        return ["output must be a regular directory, not a symlink"]
    entries = list(output.iterdir())
    if {entry.name for entry in entries} != OUTPUT_FILES:
        return ["output must contain exactly the six declared files"]
    if any(entry.is_symlink() or not entry.is_file() for entry in entries):
        return ["output contains nonregular files or symlinks"]
    try:
        receipt = json.loads((output / "receipt.json").read_text(encoding="utf-8"))
        if not isinstance(receipt, dict):
            return ["receipt must be an object"]
        _config, plan = load_inputs()
        expected = {
            "format": FORMAT,
            "model_version": sustained.VERSION,
            "baseline_model_version": feasibility.VERSION,
            "claim_level": "F0",
            "claim_boundary": CLAIM,
            "study_id": plan["study_id"],
            "phase": receipt.get("phase"),
            "numeric_encoding": NUMERIC_ENCODING,
            "input_sha256": source_hashes(),
            "output_sha256": receipt.get("output_sha256"),
            "trust_model": (
                "internal consistency only; no external attestation, empirical validity, "
                "or authorization"
            ),
        }
        if receipt != expected or receipt.get("phase") not in plan["phases"]:
            return ["receipt metadata or current input hashes do not match"]
        hashes = receipt.get("output_sha256")
        if not isinstance(hashes, dict) or set(hashes) != DATA_FILES:
            return ["receipt has an invalid output hash set"]
        failures = [
            f"hash mismatch: {name}"
            for name in sorted(DATA_FILES)
            if hashes[name] != digest((output / name).read_bytes())
        ]
        if failures:
            return failures
        if replay:
            computed = build_bundle(receipt["phase"])
            failures.extend(
                f"replay mismatch: {name}"
                for name in sorted(OUTPUT_FILES)
                if (output / name).read_bytes() != computed[name]
            )
        return failures
    except (OSError, ValueError, TypeError, KeyError) as exc:
        return [f"invalid experiment bundle: {exc}"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    run = subparsers.add_parser("run")
    run.add_argument("--out", type=Path, required=True)
    run.add_argument(
        "--phase", choices=("development", "evaluation"), default="evaluation"
    )
    verify = subparsers.add_parser("verify")
    verify.add_argument("--out", type=Path, required=True)
    verify.add_argument("--replay", action="store_true")
    args = parser.parse_args()
    try:
        if args.command == "run":
            if args.out.exists() or args.out.is_symlink():
                raise FileExistsError(f"output already exists: {args.out}; choose a new path")
            bundle = build_bundle(args.phase)
            publish_new(args.out, bundle)
            print(f"OK: {args.phase} sustained F0 experiment written to {args.out}")
        else:
            failures = verify_bundle(args.out, replay=args.replay)
            if failures:
                for failure in failures:
                    print(f"sustained verification error: {failure}", file=sys.stderr)
                return 1
            print(
                "OK: sustained bundle verified"
                + (" and replayed byte-for-byte" if args.replay else "")
            )
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(f"sustained error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
