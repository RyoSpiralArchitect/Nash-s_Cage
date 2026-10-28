"""Offline descriptive audit of public snapshots; no causal estimation."""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import math
import statistics
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
INDICATORS = ("DT.TDS.DECT.EX.ZS", "DT.TDS.DPPG.XP.ZS")
CONSTANT_FIELDS = ("disasterNumber", "state", "declarationType", "declarationDate",
                   "declarationRequestDate", "incidentBeginDate", "incidentType", "tribalRequest")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def date(value):
    if value is None:
        return None
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError("Timezone missing")
    return dt.astimezone(timezone.utc).date()


def days(start, end):
    return None if start is None or end is None else (date(end) - date(start)).days


def quantile(values, p):
    ordered = sorted(values)
    if not ordered:
        return None
    index = (len(ordered) - 1) * p
    lo, hi = math.floor(index), math.ceil(index)
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (index - lo)


def stats(values):
    observed = [v for v in values if v is not None]
    return {"n_total": len(values), "n_observed": len(observed),
            "n_missing": len(values) - len(observed),
            "n_negative": sum(v < 0 for v in observed), "n_zero": sum(v == 0 for v in observed),
            "min": min(observed) if observed else None,
            "q25": quantile(observed, .25), "median": quantile(observed, .5),
            "q75": quantile(observed, .75), "q90": quantile(observed, .9),
            "max": max(observed) if observed else None}


def collapse_fema(rows):
    groups = defaultdict(list)
    ids = [row["id"] for row in rows]
    if len(set(ids)) != len(ids):
        raise ValueError("Duplicate source IDs")
    for row in rows:
        if row["declarationType"] != "DR" or not date("2000-01-01T00:00:00Z") <= date(row["declarationDate"]) < date("2025-01-01T00:00:00Z"):
            raise ValueError("Out-of-cohort FEMA record")
        if not row["femaDeclarationString"]:
            raise ValueError("Missing declaration key")
        groups[row["femaDeclarationString"]].append(row)
    declarations = []
    for key, group in sorted(groups.items()):
        for field in CONSTANT_FIELDS:
            if len({r[field] for r in group}) != 1:
                raise ValueError(f"Within-declaration conflict: {key}/{field}")
        row = group[0]
        entry = {"declaration": key, **{k: row[k] for k in CONSTANT_FIELDS},
                 "year": date(row["declarationDate"]).year, "designated_area_rows": len(group),
                 "begin_to_declaration_days": days(row["incidentBeginDate"], row["declarationDate"]),
                 "begin_to_request_days": days(row["incidentBeginDate"], row["declarationRequestDate"]),
                 "request_to_declaration_days": days(row["declarationRequestDate"], row["declarationDate"])}
        if entry["begin_to_request_days"] is not None and entry["begin_to_declaration_days"] is not None:
            if entry["begin_to_declaration_days"] != entry["begin_to_request_days"] + entry["request_to_declaration_days"]:
                raise ValueError("Individual timeline does not reconcile")
        declarations.append(entry)
    return declarations


def fema_summary(records):
    fields = ("begin_to_declaration_days", "begin_to_request_days", "request_to_declaration_days")
    result = []
    for dimension in ("all", "incidentType", "year"):
        groups = defaultdict(list)
        for row in records:
            groups["all" if dimension == "all" else row[dimension]].append(row)
        for label, group in sorted(groups.items()):
            result.append({"dimension": dimension, "group": label,
                           **{field: stats([r[field] for r in group]) for field in fields}})
    return result


def world_bank(data_by_indicator):
    cells = []
    summaries = []
    for indicator in INDICATORS:
        data = data_by_indicator[indicator]
        if data[0]["pages"] != 1 or data[0]["total"] != len(data[1]):
            raise ValueError("Incomplete World Bank response")
        seen = set()
        for row in data[1]:
            key = (row["countryiso3code"], int(row["date"]))
            if key in seen or row["indicator"]["id"] != indicator:
                raise ValueError("Duplicate or wrong World Bank cell")
            seen.add(key)
            value = row["value"]
            if value is not None and (not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0):
                raise ValueError("Invalid World Bank ratio")
            cells.append({"country": key[0], "year": key[1], "indicator": indicator, "value_pct": value})
        if seen != {(c, y) for c in ("BGD", "KEN") for y in range(2000, 2025)}:
            raise ValueError("Unexpected country/year grid")
        for country in ("BGD", "KEN"):
            for start, end in ((2000, 2004), (2020, 2024)):
                selected = [r["value_pct"] for r in cells if r["indicator"] == indicator and
                            r["country"] == country and start <= r["year"] <= end]
                observed = [v for v in selected if v is not None]
                summaries.append({"country": country, "indicator": indicator, "start": start, "end": end,
                                  "n_observed": len(observed), "n_expected": 5,
                                  "mean_annual_ratio_pct": statistics.mean(observed) if observed else None})
    return sorted(cells, key=lambda r: (r["country"], r["indicator"], r["year"])), summaries


def write_csv(path, rows):
    with path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    manifest_bytes = (args.snapshot / "manifest.json").read_bytes()
    manifest = json.loads(manifest_bytes)
    if manifest["contract_sha256"] != digest((HERE / "CONTRACT.ja.md").read_bytes()):
        raise ValueError("Contract changed since acquisition")
    data = {}
    for source in manifest["sources"]:
        compressed = (args.snapshot / source["file"]).read_bytes()
        raw = gzip.decompress(compressed)
        if digest(raw) != source["raw_sha256"] or digest(compressed) != source["gzip_sha256"]:
            raise ValueError("Snapshot integrity failure")
        if len(raw) != source["raw_bytes"] or len(compressed) != source["gzip_bytes"]:
            raise ValueError("Snapshot size mismatch")
        data[source["file"]] = json.loads(raw)
    pages = [v for k, v in sorted(data.items()) if k.startswith("fema_page_")]
    rows = [r for page in pages for r in page["DisasterDeclarationsSummaries"]]
    if len(rows) != manifest["fema_expected_rows"] or any(p["metadata"]["count"] != len(rows) for p in pages):
        raise ValueError("FEMA source count mismatch")
    declarations = collapse_fema(rows)
    cells, wb_summary = world_bank({k: data["wb_data_" + k + ".json.gz"] for k in INDICATORS})
    summary = {"fema": {"raw_area_rows": len(rows), "declarations": len(declarations),
                        "unique_disaster_numbers": len({r["disasterNumber"] for r in declarations}),
                        "tribal_request_declarations": sum(r["tribalRequest"] for r in declarations),
                        "duplicate_ids": 0, "within_declaration_conflicts": 0,
                        "raw_area_weighted_begin_to_declaration": stats([days(r["incidentBeginDate"], r["declarationDate"]) for r in rows]),
                        "summaries": fema_summary(declarations)},
               "world_bank": {"expected_cells": 100, "observed_cells": sum(r["value_pct"] is not None for r in cells),
                              "missing_cells": [r for r in cells if r["value_pct"] is None], "window_summaries": wb_summary,
                              "lastupdated": {k: data["wb_data_" + k + ".json.gz"][0].get("lastupdated") for k in INDICATORS}},
               "claim_ceiling": "DESCRIPTIVE_ONLY_NOT_CAUSAL_NOT_LIQUIDITY_CALIBRATION",
               "snapshot_manifest_sha256": digest(manifest_bytes)}
    args.out.mkdir(parents=True, exist_ok=False)
    write_csv(args.out / "fema_declarations.csv", declarations)
    write_csv(args.out / "world_bank_series.csv", cells)
    (args.out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    outputs = {p.name: digest(p.read_bytes()) for p in sorted(args.out.iterdir())}
    receipt = {"schema_version": 1, "analyze_sha256": digest(Path(__file__).read_bytes()),
               "snapshot_manifest_sha256": digest(manifest_bytes), "outputs_sha256": outputs,
               "checks": ["raw and compressed hashes", "FEMA source count", "unique source IDs",
                          "constant declaration fields", "individual date decomposition", "WB full country-year grid",
                          "WB unique finite-or-null values"],
               "not_checked": ["actual recipient payment", "protection outcomes", "causal effects",
                               "government daily liquidity", "cross-page atomicity"]}
    (args.out / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"fema_area_rows": len(rows), "declarations": len(declarations),
                      "world_bank_cells": len(cells), "out": str(args.out)}))


if __name__ == "__main__":
    main()
