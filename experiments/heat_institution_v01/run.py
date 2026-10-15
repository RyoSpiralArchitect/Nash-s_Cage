#!/usr/bin/env python3
"""Standalone, institution-preserving synthetic screen. No real-world controller."""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
import csv
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import io
from itertools import product
import json
import math
import os
from pathlib import Path
import platform
import random
import statistics
import sys
import tempfile
import time

HERE = Path(__file__).resolve().parent
INPUT_NAMES = frozenset({"run.py", "test_run.py", "plan.json", "CONTRACT.ja.md",
                         "policy_inventory.json", "README.md"})
OUTPUT_NAMES = frozenset({"episodes.csv", "trace.csv", "summary.json", "resolved_plan.json",
                          "registration.json", "comparison.md", "receipt.json"})
ARMS = ("ordinary", "information", "linked", "information_linked")
FACTORS = ("existing_coverage", "friction", "additional_capacity_fraction",
           "budget_per_worker", "hot_day_probability")
PARAMS = frozenset(FACTORS) | {"signal_noise", "signal_bias", "information_noise_multiplier",
    "link_effect", "information_setup_per_worker", "link_setup_per_worker",
    "baseline_cost_per_worker_day", "action_cost", "worker_transfer"}
GATES = ["EMPIRICAL_INSTITUTION_COVERAGE_UNKNOWN", "EMPIRICAL_PRIVATE_PAYOFFS_UNKNOWN",
         "EMPIRICAL_RESPONSE_DELAYS_UNKNOWN", "CLINICAL_EXPOSURE_RESPONSE_UNIDENTIFIED",
         "NATIONAL_POLICY_TRANSMISSION_UNVERIFIED", "NASH_EQUILIBRIUM_NOT_ESTIMATED",
         "CAPTURE_NOT_MODELLED", "SERVICE_PRESERVATION_UNVERIFIED",
         "REAL_WORLD_ACTION_NOT_AUTHORIZED"]
METRICS = ("residual_exposure", "constrained_exposure", "other_exposure", "income_loss",
           "constrained_income_loss", "discretionary_spent", "total_public_cost",
           "budget_remaining", "false_alarm_actions", "late_actions", "additional_actions",
           "denied_budget", "denied_capacity", "baseline_protected_person_days")
CONTRASTS = (("information", "ordinary"), ("linked", "ordinary"),
             ("information_linked", "ordinary"), ("information_linked", "information"),
             ("information_linked", "linked"))
EPS = 1e-9


def finite_tree(x):
    if isinstance(x, float) and not math.isfinite(x):
        raise ValueError("nonfinite evidence")
    if isinstance(x, dict):
        for y in x.values():
            finite_tree(y)
    if isinstance(x, (list, tuple)):
        for y in x:
            finite_tree(y)


def rounded(x):
    finite_tree(x)
    if isinstance(x, float):
        return round(x, 9) + 0.0
    if isinstance(x, dict):
        return {k: rounded(v) for k, v in x.items()}
    if isinstance(x, (tuple, list)):
        return [rounded(v) for v in x]
    return x


def encode(x):
    return (json.dumps(rounded(x), ensure_ascii=False, indent=2, sort_keys=True,
                       allow_nan=False) + "\n").encode()


def digest(b):
    return hashlib.sha256(b).hexdigest()


def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def decode(b):
    x = json.loads(b, object_pairs_hook=unique_pairs)
    finite_tree(x)
    return x


def no_links(path):
    path = Path(path).absolute()
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError("symlink paths are not accepted")
    return path


def read_plain(path):
    p = no_links(path)
    if not p.is_file():
        raise ValueError(f"not a regular file: {p}")
    return p.read_bytes()


def input_hashes():
    return {n: digest(read_plain(HERE / n)) for n in sorted(INPUT_NAMES)}


def number(x, lo=0.0, hi=100.0):
    if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x):
        raise ValueError("expected a finite number, not a boolean")
    if not lo <= x <= hi:
        raise ValueError("number outside declared bounds")


def integer(x, lo, hi):
    if type(x) is not int or not lo <= x <= hi:
        raise ValueError("integer outside declared bounds")


def validate_params(p):
    if not isinstance(p, dict) or set(p) != PARAMS:
        raise ValueError("unknown or missing parameter")
    for k, v in p.items():
        number(v, -3.0 if k == "signal_bias" else 0.0, 100.0)
    for k in ("existing_coverage", "additional_capacity_fraction", "hot_day_probability",
              "information_noise_multiplier", "link_effect"):
        number(p[k], 0, 1)
    number(p["action_cost"], 0.01, 100)
    number(p["worker_transfer"], 0, p["action_cost"])


def validate_plan(p):
    keys = {"format", "study_id", "claim_level", "institution_exists", "base_commit",
            "workers", "days", "max_processes", "development_seeds", "evaluation_seeds",
            "arms", "factors", "defaults", "controls", "unknown_gates"}
    if not isinstance(p, dict) or set(p) != keys:
        raise ValueError("unknown or missing plan field")
    if (p["format"] != "heat-institution-plan/v1" or p["study_id"] != "heat-institution-v01"
            or p["claim_level"] != "F0_SYNTHETIC_MECHANISM_SCREEN"
            or p["institution_exists"] is not True or p["arms"] != list(ARMS)
            or p["unknown_gates"] != GATES):
        raise ValueError("claim boundary / institution / arms / unknown gates changed")
    if p["base_commit"] != "c0031acceda44c13f32be1c51eb2125167e89ed1":
        raise ValueError("wrong predecessor anchor")
    integer(p["workers"], 2, 100)
    if p["workers"] % 2:
        raise ValueError("two equal-sized groups required")
    integer(p["days"], 1, 366)
    integer(p["max_processes"], 1, 2)
    used = set()
    for phase in ("development", "evaluation"):
        seeds = p[phase + "_seeds"]
        if not isinstance(seeds, list) or not seeds or len(seeds) > 256:
            raise ValueError("invalid seeds")
        for seed in seeds:
            integer(seed, 0, 2**32 - 1)
            if seed in used:
                raise ValueError("seeds overlap or repeat")
            used.add(seed)
    validate_params(p["defaults"])
    if not isinstance(p["factors"], dict) or set(p["factors"]) != set(FACTORS):
        raise ValueError("wrong factor axes")
    size = 1
    for k, values in p["factors"].items():
        if not isinstance(values, list) or not values or len(values) > 8:
            raise ValueError("invalid axis")
        if len(set(values)) != len(values):
            raise ValueError("duplicate axis value")
        size *= len(values)
        for v in values:
            validate_params(p["defaults"] | {k: v})
    if size > 512:
        raise ValueError("matrix too large")
    if not isinstance(p["controls"], list) or not 1 <= len(p["controls"]) <= 32:
        raise ValueError("invalid controls")
    ids = set()
    for c in p["controls"]:
        if not isinstance(c, dict) or set(c) != {"id", "overrides"}:
            raise ValueError("invalid control")
        label = c["id"]
        if (not isinstance(label, str) or not label or label in ids
                or any(ch not in "abcdefghijklmnopqrstuvwxyz0123456789_" for ch in label)):
            raise ValueError("invalid control id")
        ids.add(label)
        if not isinstance(c["overrides"], dict) or not set(c["overrides"]) <= PARAMS:
            raise ValueError("unknown override")
        validate_params(p["defaults"] | c["overrides"])


def scenarios(plan):
    result = []
    for i, values in enumerate(product(*(plan["factors"][k] for k in FACTORS))):
        result.append({"id": f"matrix_{i:03d}", "cohort": "factorial",
                       "params": plan["defaults"] | dict(zip(FACTORS, values))})
    result.extend({"id": c["id"], "cohort": "control",
                   "params": plan["defaults"] | c["overrides"]} for c in plan["controls"])
    return result


@dataclass(frozen=True)
class Person:
    constrained: bool
    vulnerability: float
    wage_loss_if_stopped: float


@dataclass(frozen=True)
class WorldDay:
    # Only the evaluator receives hazard and delivery_jitter.
    hazard: float
    signal_error: float
    baseline_ids: tuple[int, ...]
    delivery_jitter: tuple[float, ...]


@dataclass(frozen=True)
class PublicFrame:
    observation: float
    baseline_ids: tuple[int, ...]
    slots: int
    people: tuple[Person, ...]
    day: int


def world(plan, p, seed):
    rng = random.Random(seed)
    n = plan["workers"]
    people = tuple(Person(i < n // 2, 1.2 if i < n // 2 else 0.9,
                          1.15 if i < n // 2 else 0.8) for i in range(n))
    days = []
    for _ in range(plan["days"]):
        hot, magnitude, error = rng.random(), rng.random(), rng.random()
        hazard = 1.1 + 1.4 * magnitude if hot < p["hot_day_probability"] else 0.6 * magnitude
        roster = sorted(range(n), key=lambda _: rng.random())
        base = tuple(sorted(roster[:math.floor(n * p["existing_coverage"])]))
        jitter = tuple(rng.random() - 0.5 for _ in range(n))
        days.append(WorldDay(hazard, p["signal_noise"] * (2 * error - 1), base, jitter))
    return people, tuple(days)


def choose(frame, p, budget, linked):
    """No true hazard, future weather, outcome labels, or service jitter are accepted."""
    number(frame.observation, 0, 200)
    number(budget, 0, 1e9)
    delay = p["friction"] * (1 - p["link_effect"] if linked else 1)
    expected_gain = max(0.0, 1 - delay)
    observed_excess = max(0.0, frame.observation - 1)
    worker_support = p["worker_transfer"] / (1 + delay)
    employer_support = (p["action_cost"] - p["worker_transfer"]) / (1 + delay)
    actions, denied_budget, denied_capacity, declined = [], 0, 0, 0
    baseline = set(frame.baseline_ids)
    order = sorted(range(len(frame.people)), key=lambda i:
                   (-frame.people[i].vulnerability, (i + frame.day) % len(frame.people)))
    for i in order:
        if i in baseline:
            continue
        person = frame.people[i]
        private_worker = (1.3 * observed_excess * person.vulnerability * expected_gain
                          - max(0.0, person.wage_loss_if_stopped - worker_support))
        private_employer = (0.8 * observed_excess * expected_gain + employer_support
                            - 0.35 - 0.2 * delay)
        if observed_excess <= 0 or private_worker < 0 or private_employer < 0:
            declined += 1
        elif len(actions) >= frame.slots:
            denied_capacity += 1
        elif budget + EPS < p["action_cost"]:
            denied_budget += 1
        else:
            actions.append(i)
            budget = max(0.0, budget - p["action_cost"])
    return tuple(actions), budget, denied_budget, denied_capacity, declined


def episode(plan, scenario, seed, arm, people, days, traced=False):
    p = scenario["params"]
    n, horizon = plan["workers"], plan["days"]
    budget_start = n * p["budget_per_worker"]
    budget = budget_start
    capacity = math.floor(n * p["additional_capacity_fraction"])
    uncovered = n - math.floor(n * p["existing_coverage"])
    setup = (n * p["information_setup_per_worker"] if "information" in arm else 0)
    setup += n * p["link_setup_per_worker"] if "linked" in arm else 0
    admitted = capacity > 0 and uncovered > 0 and budget + EPS >= setup
    info = "information" in arm and admitted
    linked = "linked" in arm and admitted
    setup_paid = setup if admitted else 0
    budget = max(0.0, budget - setup_paid)
    delay = p["friction"] * (1 - p["link_effect"] if linked else 1)
    metrics = {k: 0.0 for k in METRICS}
    rows = []
    for day_index, d in enumerate(days):
        observation = max(0.0, d.hazard + p["signal_bias"] + d.signal_error *
                          (p["information_noise_multiplier"] if info else 1))
        frame = PublicFrame(observation, d.baseline_ids, min(capacity, uncovered), people, day_index)
        actions, budget, denied_budget, denied_capacity, declined = choose(frame, p, budget, linked)
        base_set, action_set = set(d.baseline_ids), set(actions)
        excess = max(0.0, d.hazard - 1)
        exposure, constrained, other, losses, constrained_losses = 0.0, 0.0, 0.0, 0.0, 0.0
        false_alarms, late = 0, 0
        for i, person in enumerate(people):
            protection, loss = (1.0 if i in base_set else 0.0), 0.0
            if i in action_set:
                realized_delay = max(0.0, delay + d.delivery_jitter[i])
                protection = max(0.0, 1 - realized_delay)
                loss = max(0.0, person.wage_loss_if_stopped - p["worker_transfer"])
                false_alarms += excess == 0
                late += realized_delay >= 1
            residual = excess * person.vulnerability * (1 - protection)
            exposure += residual
            losses += loss
            if person.constrained:
                constrained += residual
                constrained_losses += loss
            else:
                other += residual
        metrics["residual_exposure"] += exposure / (n * horizon)
        metrics["constrained_exposure"] += constrained / (n / 2 * horizon)
        metrics["other_exposure"] += other / (n / 2 * horizon)
        metrics["income_loss"] += losses / (n * horizon)
        metrics["constrained_income_loss"] += constrained_losses / (n / 2 * horizon)
        metrics["false_alarm_actions"] += false_alarms
        metrics["late_actions"] += late
        metrics["additional_actions"] += len(actions)
        metrics["denied_budget"] += denied_budget
        metrics["denied_capacity"] += denied_capacity
        metrics["baseline_protected_person_days"] += len(base_set)
        if traced:
            rows.append({"scenario": scenario["id"], "cohort": scenario["cohort"], "seed": seed,
                         "arm": arm, "day": day_index, "policy_observation": observation,
                         "evaluator_true_hazard": d.hazard, "baseline_protected": len(base_set),
                         "actions": len(actions), "budget_remaining": budget,
                         "residual_exposure_sum": exposure, "income_loss_sum": losses,
                         "false_alarms": false_alarms, "late_actions": late,
                         "denied_budget": denied_budget, "denied_capacity": denied_capacity,
                         "declined_by_actor": declined})
    metrics["budget_remaining"] = budget
    metrics["discretionary_spent"] = budget_start - budget
    metrics["total_public_cost"] = (metrics["discretionary_spent"] +
        metrics["baseline_protected_person_days"] * p["baseline_cost_per_worker_day"])
    expected_spend = setup_paid + metrics["additional_actions"] * p["action_cost"]
    if (abs(expected_spend - metrics["discretionary_spent"]) > EPS
            or metrics["discretionary_spent"] > budget_start + EPS
            or metrics["additional_actions"] > capacity * horizon):
        raise ValueError("resource conservation violated")
    result = {"scenario": scenario["id"], "cohort": scenario["cohort"], "seed": seed,
              "arm": arm, "information_active": info, "link_active": linked,
              "setup_paid": setup_paid} | metrics
    finite_tree(result)
    return result, rows


def paired_job(job):
    plan, scenario, seed, traced = job
    people, days = world(plan, scenario["params"], seed)
    results, traces = [], []
    for arm in ARMS:
        r, t = episode(plan, scenario, seed, arm, people, days, traced)
        results.append(r)
        traces.extend(t)
    if len({r["baseline_protected_person_days"] for r in results}) != 1:
        raise ValueError("existing institution floor differs across arms")
    return results, traces


def describe(values):
    return {"n_paired_seasons": len(values), "mean": statistics.fmean(values),
            "standard_error": statistics.stdev(values) / math.sqrt(len(values)) if len(values) > 1 else None,
            "lower_count": sum(x < -EPS for x in values), "higher_count": sum(x > EPS for x in values),
            "tie_count": sum(abs(x) <= EPS for x in values)}


def summarize(plan, phase, rows):
    cells = []
    for scenario in scenarios(plan):
        subset = [r for r in rows if r["scenario"] == scenario["id"]]
        by_arm = {a: {r["seed"]: r for r in subset if r["arm"] == a} for a in ARMS}
        seeds = plan[phase + "_seeds"]
        if any(set(r) != set(seeds) for r in by_arm.values()):
            raise ValueError("missing paired seasons")
        means = {a: {m: statistics.fmean(by_arm[a][s][m] for s in seeds) for m in METRICS} for a in ARMS}
        contrasts = {}
        for a, b in CONTRASTS:
            contrasts[a + "-" + b] = {m: describe([by_arm[a][s][m] - by_arm[b][s][m]
                                                    for s in seeds]) for m in METRICS}
        contrasts["interaction"] = {m: describe([by_arm["information_linked"][s][m]
            - by_arm["information"][s][m] - by_arm["linked"][s][m]
            + by_arm["ordinary"][s][m] for s in seeds]) for m in METRICS}
        cells.append(scenario | {"arm_means": means, "paired_contrasts": contrasts})
    control_checks(plan, rows)
    return {"format": "heat-institution-summary/v1", "phase": phase,
            "claim_level": plan["claim_level"], "arm_seasons": len(rows),
            "paired_worlds": len(rows) // 4, "scenario_count": len(cells),
            "winner": "none", "reason": "Uncalibrated mechanism screen with multiple nonfungible outcomes.",
            "unknown_gates": plan["unknown_gates"], "invariants": "PASS", "cells": cells}


def control_checks(plan, rows):
    for seed in plan["development_seeds"] + plan["evaluation_seeds"]:
        group = {name: {r["arm"]: r for r in rows if r["scenario"] == name and r["seed"] == seed}
                 for name in (c["id"] for c in plan["controls"])}
        for name in ("full_existing_protection", "no_additional_capacity", "no_additional_budget"):
            if name not in group or not group[name]:
                continue
            g = group[name]
            if any(r["additional_actions"] != 0 for r in g.values()):
                raise ValueError(f"negative control failed: {name}")
            if len({round(r["residual_exposure"], 12) for r in g.values()}) != 1:
                raise ValueError("physical null arms differ")
            if name == "full_existing_protection" and any(r["residual_exposure"] != 0 for r in g.values()):
                raise ValueError("full existing protection failed")
        if any(r["residual_exposure"] != 0 for r in group.get("no_hazard", {}).values()):
            raise ValueError("no hazard control failed")
        for name, pairs in (("information_effect_null", (("ordinary", "information"),
                                                         ("linked", "information_linked"))),
                            ("link_effect_null", (("ordinary", "linked"),
                                                  ("information", "information_linked")))):
            if name in group and group[name]:
                for a, b in pairs:
                    if any(group[name][a][m] != group[name][b][m] for m in METRICS):
                        raise ValueError(f"mechanism identity control failed: {name}")


def csv_bytes(rows):
    if not rows:
        raise ValueError("empty evidence table")
    out = io.StringIO(newline="")
    fields = sorted(rows[0])
    writer = csv.DictWriter(out, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for r in rows:
        if set(r) != set(fields):
            raise ValueError("inconsistent row schema")
        writer.writerow(rounded(r))
    return out.getvalue().encode()


def comparison(summary):
    lines = ["# 暑熱・制度接続: 合成実験の全条件", "",
             f"{summary['phase']}: {summary['scenario_count']} 条件 / {summary['arm_seasons']} arm-season。",
             "", "F0 合成機構スクリーニング。実際の日本の制度効果・死傷者・安全性の推定ではない。",
             "winner: none。既存の保護は全 arm で保持。主行列と対照は別 cohort。",
             "資源上限は同じだが実支出は同じとは限らない。以下の曝露は無次元の人工指標。",
             "差は information_linked - ordinary。負の曝露差は追加保護側が小さいことを示す。",
             "費用・所得損失・空振りは別に評価し、死亡回避へ換算しない。全 arm と全対比較は summary.json。",
             "", "| 条件 | cohort | ordinary 曝露 | 両方 曝露 | 曝露差 | 所得損失差 | 追加支出差 |",
             "|---|---|---:|---:|---:|---:|---:|"]
    for c in summary["cells"]:
        a = c["arm_means"]
        d = c["paired_contrasts"]["information_linked-ordinary"]
        lines.append(f"| {c['id']} | {c['cohort']} | {a['ordinary']['residual_exposure']:.6f} | "
                     f"{a['information_linked']['residual_exposure']:.6f} | "
                     f"{d['residual_exposure']['mean']:+.6f} | {d['income_loss']['mean']:+.6f} | "
                     f"{d['discretionary_spent']['mean']:+.3f} |")
    lines += ["", "## 未同定のゲート", ""] + ["- " + g for g in summary["unknown_gates"]]
    return ("\n".join(lines) + "\n").encode()


def compute(plan, phase, processes):
    jobs = [(plan, s, seed, seed == plan[phase + "_seeds"][0])
            for s in scenarios(plan) for seed in plan[phase + "_seeds"]]
    rows, traces = [], []
    if processes == 1:
        results = map(paired_job, jobs)
        for r, t in results:
            rows.extend(r)
            traces.extend(t)
    else:
        with ProcessPoolExecutor(max_workers=processes) as pool:
            for r, t in pool.map(paired_job, jobs, chunksize=8):
                rows.extend(r)
                traces.extend(t)
    summary = summarize(plan, phase, rows)
    return {"episodes.csv": csv_bytes(rows), "trace.csv": csv_bytes(traces),
            "summary.json": encode(summary), "resolved_plan.json": encode(plan),
            "comparison.md": comparison(summary)}


def publish(out, blobs):
    out = no_links(out)
    if out.exists():
        raise ValueError("output exists; no overwrite permitted")
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="heat-stage-", dir=out.parent) as tmp:
        stage = Path(tmp) / "bundle"
        stage.mkdir()
        for name, data in blobs.items():
            if Path(name).name != name:
                raise ValueError("invalid output name")
            (stage / name).write_bytes(data)
        # Refuse another writer's output, including an empty directory.
        out.mkdir()
        for name in blobs:
            os.replace(stage / name, out / name)


def freeze(out):
    before = input_hashes()
    p = decode(read_plain(HERE / "plan.json"))
    validate_plan(p)
    if input_hashes() != before:
        raise ValueError("inputs changed during freeze")
    record = {"format": "heat-local-registration/v1", "created_utc": datetime.now(timezone.utc).isoformat(),
              "scope": "Local pre-execution freeze; not third-party preregistration.",
              "inputs": before, "plan": p}
    publish(out, {"registration.json": encode(record)})
    return record


def registration(path):
    raw = read_plain(path)
    record = decode(raw)
    if (not isinstance(record, dict) or set(record) != {"format", "created_utc", "scope", "inputs", "plan"}
            or record["format"] != "heat-local-registration/v1" or record["inputs"] != input_hashes()):
        raise ValueError("registration or source identity mismatch")
    validate_plan(record["plan"])
    if encode(record["plan"]) != encode(decode(read_plain(HERE / "plan.json"))):
        raise ValueError("registered plan differs from current plan")
    return raw, record


def run(reg_path, phase, out, processes):
    raw, reg = registration(reg_path)
    integer(processes, 1, reg["plan"]["max_processes"])
    if phase not in ("development", "evaluation"):
        raise ValueError("invalid phase")
    if no_links(out).exists():
        raise ValueError("output exists")
    started = time.monotonic()
    blobs = compute(reg["plan"], phase, processes)
    if registration(reg_path)[0] != raw:
        raise ValueError("registration changed during computation")
    blobs["registration.json"] = raw
    receipt = {"format": "heat-institution-receipt/v1", "phase": phase,
               "claim_level": reg["plan"]["claim_level"], "inputs": reg["inputs"],
               "outputs": {n: digest(b) for n, b in sorted(blobs.items())},
               "runtime": {"python": platform.python_version(), "system": platform.system(),
                           "machine": platform.machine(), "processes": processes,
                           "elapsed_seconds": time.monotonic() - started},
               "trust_model": "Internal consistency; not authenticity, calibration, or external registration."}
    blobs["receipt.json"] = encode(receipt)
    publish(out, blobs)
    return decode(blobs["summary.json"])


def output_snapshot(out):
    out = no_links(out)
    if not out.is_dir() or {p.name for p in out.iterdir()} != OUTPUT_NAMES:
        raise ValueError("output file closure mismatch")
    return {n: read_plain(out / n) for n in sorted(OUTPUT_NAMES)}


def verify(out, replay=False, processes=1):
    snapshot = output_snapshot(out)
    receipt = decode(snapshot["receipt.json"])
    keys = {"format", "phase", "claim_level", "inputs", "outputs", "runtime", "trust_model"}
    if (not isinstance(receipt, dict) or set(receipt) != keys
            or receipt["format"] != "heat-institution-receipt/v1"
            or receipt["phase"] not in ("development", "evaluation")
            or receipt["inputs"] != input_hashes()
            or set(receipt["outputs"]) != OUTPUT_NAMES - {"receipt.json"}):
        raise ValueError("invalid receipt")
    for n, h in receipt["outputs"].items():
        if digest(snapshot[n]) != h:
            raise ValueError(f"artifact hash mismatch: {n}")
    raw, reg = registration(Path(out) / "registration.json")
    if raw != snapshot["registration.json"] or receipt["claim_level"] != reg["plan"]["claim_level"]:
        raise ValueError("claim/registration mismatch")
    if snapshot["resolved_plan.json"] != encode(reg["plan"]):
        raise ValueError("resolved plan mismatch")
    summary = decode(snapshot["summary.json"])
    if (summary["unknown_gates"] != GATES or summary["winner"] != "none"
            or summary["claim_level"] != reg["plan"]["claim_level"]):
        raise ValueError("summary claim boundary mismatch")
    integer(processes, 1, reg["plan"]["max_processes"])
    if replay:
        fresh = compute(reg["plan"], receipt["phase"], processes)
        if any(snapshot[n] != b for n, b in fresh.items()):
            raise ValueError("deterministic replay mismatch")
    if output_snapshot(out) != snapshot or input_hashes() != receipt["inputs"]:
        raise ValueError("inputs or artifacts changed during verification")
    return {"verified": True, "replayed": replay, "phase": receipt["phase"],
            "arm_seasons": summary["arm_seasons"], "unknown_gates": GATES}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    subs = ap.add_subparsers(dest="command", required=True)
    f = subs.add_parser("freeze")
    f.add_argument("--out", required=True, type=Path)
    r = subs.add_parser("run")
    r.add_argument("--registration", required=True, type=Path)
    r.add_argument("--phase", choices=["development", "evaluation"], required=True)
    r.add_argument("--out", required=True, type=Path)
    r.add_argument("--processes", type=int, default=1)
    v = subs.add_parser("verify")
    v.add_argument("--out", required=True, type=Path)
    v.add_argument("--replay", action="store_true")
    v.add_argument("--processes", type=int, default=1)
    args = ap.parse_args()
    try:
        if args.command == "freeze":
            x = freeze(args.out)
            print(encode({"frozen": True, "created_utc": x["created_utc"], "inputs": x["inputs"]}).decode())
        elif args.command == "run":
            x = run(args.registration, args.phase, args.out, args.processes)
            print(encode({k: x[k] for k in ("phase", "arm_seasons", "paired_worlds", "winner", "invariants")}).decode())
        else:
            print(encode(verify(args.out, args.replay, args.processes)).decode())
        return 0
    except (ValueError, OSError, KeyError, TypeError) as e:
        print(f"REFUSED: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
