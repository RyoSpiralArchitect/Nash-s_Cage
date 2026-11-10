#!/usr/bin/env python3
"""Freeze, bounded execution, and replay for the independent F0 twins assay."""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone
import gzip
import hashlib
import io
import json
import math
from pathlib import Path
import platform
import re
import sys
import time

from model import (ARMS, CLAIM, CONTRASTS, FIELDS, bound_group, catalogue, evaluate,
                   integer, record_key, validate_plan, METRICS)

HERE = Path(__file__).resolve().parent
INPUTS = frozenset({"model.py", "run.py", "test_model.py", "test_run.py", "plan.json",
                    "CONTRACT.ja.md", "README.md", "audit.py"})
DATA = frozenset({"worlds.jsonl.gz", "classes.jsonl.gz", "summary.json", "witnesses.json"})
OUTPUTS = DATA | {"plan.json", "registration.json", "receipt.json"}
SCOPE = "Local pre-execution freeze; not third-party preregistration."
TRUST = "Internal consistency and optional replay; not authenticity or empirical validity."


def encode(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2,
                       allow_nan=False) + "\n").encode()


def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def decode(data):
    def invalid(value):
        raise ValueError(f"nonfinite JSON: {value}")
    def finite(value):
        if isinstance(value, float) and not math.isfinite(value):
            invalid(value)
        if isinstance(value, dict):
            for child in value.values():
                finite(child)
        elif isinstance(value, list):
            for child in value:
                finite(child)
    value = json.loads(data, object_pairs_hook=unique_pairs, parse_constant=invalid)
    finite(value)
    return value


def digest(data):
    return hashlib.sha256(data).hexdigest()


def plain_path(path):
    path = Path(path).absolute()
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError("symlink paths are not supported")
    return path


def read(path):
    path = plain_path(path)
    if not path.is_file():
        raise ValueError(f"not a regular file: {path}")
    return path.read_bytes()


def write(path, data):
    path = plain_path(path)
    with path.open("xb") as handle:
        handle.write(data)


def source_hashes():
    return {name: digest(read(HERE / name)) for name in sorted(INPUTS)}


def utc_valid(value):
    if not isinstance(value, str):
        raise ValueError("invalid UTC timestamp")
    stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if stamp.tzinfo is None or stamp.utcoffset() != timezone.utc.utcoffset(None):
        raise ValueError("UTC offset required")


def validate_registration(registration):
    if not isinstance(registration, dict) or set(registration) != {
            "format", "claim_level", "scope", "trust", "created_utc", "inputs"}:
        raise ValueError("invalid registration schema")
    if (registration["format"] != "waiting-contestability-freeze/v1"
            or registration["claim_level"] != CLAIM or registration["scope"] != SCOPE
            or registration["trust"] != TRUST):
        raise ValueError("invalid registration boundary")
    utc_valid(registration["created_utc"])
    if registration["inputs"] != source_hashes():
        raise ValueError("source changed; create a new freeze and output directory")


def freeze(out):
    plan = decode(read(HERE / "plan.json"))
    validate_plan(plan)
    before = source_hashes()
    registration = {"format": "waiting-contestability-freeze/v1", "claim_level": CLAIM,
                    "scope": SCOPE, "trust": TRUST,
                    "created_utc": datetime.now(timezone.utc).isoformat(), "inputs": before}
    out = plain_path(out)
    out.mkdir(parents=True, exist_ok=False)
    write(out / "registration.json", encode(registration))
    if before != source_hashes():
        raise ValueError("source changed during freeze; preserve partial output")
    return registration


def jsonl_gzip(rows):
    payload = b"".join((json.dumps(r, ensure_ascii=False, sort_keys=True,
                                  separators=(",", ":"), allow_nan=False) + "\n").encode()
                       for r in rows)
    buffer = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=buffer, mtime=0) as stream:
        stream.write(payload)
    return buffer.getvalue()


def compute(plan, phase, processes=1):
    integer(processes, 1, plan["max_processes"])
    items = catalogue(plan, phase)
    if processes == 1:
        rows = [evaluate(item) for item in items]
    else:
        with ProcessPoolExecutor(max_workers=processes) as pool:
            rows = list(pool.map(evaluate, items, chunksize=128))
    classes, reports, witnesses = [], [], []
    totals = {}
    for name in CONTRASTS:
        totals[name] = {}
        for metric in METRICS:
            vals = [r["contrasts"][name][metric] for r in rows]
            totals[name][metric] = {label: sum(test(v) for v in vals)
                for label, test in {
                    "positive": lambda v: v is not None and v > 0,
                    "negative": lambda v: v is not None and v < 0,
                    "zero": lambda v: v == 0,
                    "undefined": lambda v: v is None}.items()}
    for view in plan["views"]:
        groups = {}
        for row in rows:
            groups.setdefault(record_key(row["world"], view["fields"]), []).append(row)
        for name in CONTRASTS:
            mixed = {k: 0 for k in METRICS}
            mixed_worlds = {k: 0 for k in METRICS}
            first = {}
            for key, group in groups.items():
                bound = bound_group(group, name)
                observed = dict(zip(view["fields"], key))
                classes.append({"view": view["name"], "contrast": name,
                                "observed": observed, **bound})
                for metric, limits in bound["bounds"].items():
                    ambiguity = (limits["min"] != limits["max"]
                                 or 0 < limits["undefined"] < len(group))
                    if ambiguity:
                        mixed[metric] += 1
                        mixed_worlds[metric] += len(group)
                        if metric not in first:
                            lhs = group[0]
                            rhs = next(r for r in group if r["contrasts"][name][metric]
                                       != lhs["contrasts"][name][metric])
                            first[metric] = {"view": view["name"], "contrast": name,
                                "metric": metric, "observed": observed,
                                "world_ids": [lhs["world_id"], rhs["world_id"]],
                                "values": [lhs["contrasts"][name][metric], rhs["contrasts"][name][metric]]}
            reports.append({"view": view["name"], "contrast": name,
                            "world_denominator": len(rows), "class_denominator": len(groups),
                            "mixed_classes": mixed, "worlds_in_mixed_classes": mixed_worlds})
            witnesses.extend(first.values())
    summary = {
        "format": "waiting-contestability-summary/v1", "claim_level": CLAIM, "phase": phase,
        "world_count": len(rows), "arm_world_count": len(rows)*len(ARMS),
        "counts_are": "Designed catalogue counts, not population frequencies or causal estimates.",
        "scope": "Engineering cases only" if phase == "smoke" else "Full declared finite catalogue",
        "full_input_decidability_is": "By construction; evaluator-only view is not an operational guarantee.",
        "bounds_are": "Componentwise; delivery-time differences undefined if either service never arrives.",
        "totals": totals, "reports": reports}
    return {"worlds.jsonl.gz": jsonl_gzip(rows), "classes.jsonl.gz": jsonl_gzip(classes),
            "summary.json": encode(summary), "witnesses.json": encode(witnesses)}


def run(registration_path, phase, out, processes):
    registration_bytes = read(registration_path)
    registration = decode(registration_bytes)
    validate_registration(registration)
    before = source_hashes()
    plan_bytes = read(HERE / "plan.json")
    plan = decode(plan_bytes)
    validate_plan(plan)
    integer(processes, 1, plan["max_processes"])
    if phase not in ("smoke", "enumeration"):
        raise ValueError("unknown phase")
    out = plain_path(out)
    out.mkdir(parents=True, exist_ok=False)
    write(out / "registration.json", registration_bytes)
    write(out / "plan.json", plan_bytes)
    started = datetime.now(timezone.utc).isoformat()
    begin = time.monotonic()
    outputs = compute(plan, phase, processes)
    for name, payload in outputs.items():
        write(out / name, payload)
    if before != source_hashes():
        raise ValueError("source changed during computation; preserve partial output")
    receipt = {
        "format": "waiting-contestability-receipt/v1", "claim_level": CLAIM,
        "trust": TRUST, "phase": phase, "started_utc": started, "inputs": before,
        "runtime": {"python": platform.python_version(), "system": platform.system(),
                    "machine": platform.machine(), "processes": processes,
                    "elapsed_seconds": round(time.monotonic() - begin, 6)},
        "outputs": {n: digest(read(out / n)) for n in sorted(OUTPUTS - {"receipt.json"})},
    }
    write(out / "receipt.json", encode(receipt))
    verify(out)
    return receipt


def verify(out, replay=False, processes=1):
    before = source_hashes()
    out = plain_path(out)
    if not out.is_dir() or {p.name for p in out.iterdir()} != OUTPUTS:
        raise ValueError("incomplete or unexpected output closure")
    blobs = {n: read(out / n) for n in OUTPUTS}
    receipt = decode(blobs["receipt.json"])
    expected = {"format", "claim_level", "trust", "phase", "started_utc", "inputs", "runtime", "outputs"}
    if not isinstance(receipt, dict) or set(receipt) != expected:
        raise ValueError("invalid receipt schema")
    if (receipt["format"] != "waiting-contestability-receipt/v1"
            or receipt["claim_level"] != CLAIM or receipt["trust"] != TRUST
            or receipt["phase"] not in ("smoke", "enumeration") or receipt["inputs"] != before):
        raise ValueError("invalid receipt identity")
    utc_valid(receipt["started_utc"])
    runtime = receipt["runtime"]
    if not isinstance(runtime, dict) or set(runtime) != {"python", "system", "machine", "processes", "elapsed_seconds"}:
        raise ValueError("invalid runtime schema")
    if not isinstance(runtime["python"], str) or re.fullmatch(r"\d+\.\d+\.\d+(?:(?:a|b|rc)\d+)?", runtime["python"]) is None:
        raise ValueError("invalid Python version")
    if any(not isinstance(runtime[k], str) or not runtime[k] for k in ("system", "machine")):
        raise ValueError("invalid runtime identity")
    elapsed = runtime["elapsed_seconds"]
    if isinstance(elapsed, bool) or not isinstance(elapsed, (int, float)) or not math.isfinite(elapsed) or elapsed < 0:
        raise ValueError("invalid elapsed time")
    plan = decode(blobs["plan.json"])
    validate_plan(plan)
    integer(runtime["processes"], 1, plan["max_processes"])
    integer(processes, 1, plan["max_processes"])
    validate_registration(decode(blobs["registration.json"]))
    if digest(blobs["plan.json"]) != before["plan.json"]:
        raise ValueError("plan mismatch")
    hashes = {n: digest(b) for n, b in blobs.items() if n != "receipt.json"}
    if hashes != receipt["outputs"]:
        raise ValueError("output hash mismatch")
    summary = decode(blobs["summary.json"])
    expected_count = len(catalogue(plan, receipt["phase"]))
    if (summary.get("phase") != receipt["phase"] or summary.get("claim_level") != CLAIM
            or summary.get("world_count") != expected_count
            or summary.get("arm_world_count") != expected_count * len(ARMS)):
        raise ValueError("summary phase/denominator mismatch")
    if replay:
        regenerated = compute(plan, receipt["phase"], processes)
        for name in DATA:
            a, b = blobs[name], regenerated[name]
            # Gzip implementation versions may differ; compare the exact JSONL payload.
            if name.endswith(".gz"):
                a, b = gzip.decompress(a), gzip.decompress(b)
            if a != b:
                raise ValueError(f"deterministic replay mismatch: {name}")
    if (before != source_hashes() or {p.name for p in out.iterdir()} != OUTPUTS
            or any(read(out / n) != b for n, b in blobs.items())):
        raise ValueError("input/output changed during verification")
    return {"verified": True, "replayed": replay, "phase": receipt["phase"], "claim_level": CLAIM}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    f = sub.add_parser("freeze")
    f.add_argument("--out", type=Path, required=True)
    r = sub.add_parser("run")
    r.add_argument("--registration", type=Path, required=True)
    r.add_argument("--phase", choices=("smoke", "enumeration"), required=True)
    r.add_argument("--out", type=Path, required=True)
    r.add_argument("--processes", type=int, default=1)
    r.add_argument("--acknowledge-f0-enumeration", action="store_true")
    v = sub.add_parser("verify")
    v.add_argument("--out", type=Path, required=True)
    v.add_argument("--replay", action="store_true")
    v.add_argument("--processes", type=int, default=1)
    args = parser.parse_args()
    try:
        if args.command == "freeze":
            result = freeze(args.out)
        elif args.command == "run":
            if args.phase == "enumeration" and not args.acknowledge_f0_enumeration:
                raise ValueError("enumeration needs --acknowledge-f0-enumeration; smoke is separate")
            result = run(args.registration, args.phase, args.out, args.processes)
        else:
            result = verify(args.out, args.replay, args.processes)
        print(encode(result).decode(), end="")
    except (ValueError, OSError, TypeError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
