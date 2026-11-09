"""Read-only recount of the retained enumeration, without importing its simulator.

Usage: python3 audit.py BUNDLE [--save NEW_JSON]. Does not generate any worlds.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import gzip
import hashlib
import json
from math import prod
from pathlib import Path


RECEIPT = "1f81e90467f6ab2dbe8f179e64073a0b34f2a13d63347d8efe80cb0562235f4c"
FREEZE = "b4f0e4f69ab2743d06b86f04898507b219f7531976937a4670a06237e7ca45d6"
PAIRS = {"timing": "early", "assurance": "assured", "combined": "early_assured"}
DEBT = ("grant_unpaid", "credit_unpaid", "maintenance_unpaid", "credit_arrears_t2")
METRICS = ("target_completed", "other_completed", "target_continued", *DEBT,
           "public_outflow", "real_service_spending")
STATUSES = ("MODEL_ALL_PASS", "MODEL_ALL_FAIL", "UNIDENTIFIED_WITHIN_CATALOGUE")


def check(ok, tag):
    if not ok:
        raise ValueError(f"recount discrepancy: {tag}")


def readout(bundle):
    def load(name):
        return json.loads((bundle / name).read_bytes())

    def sha(name):
        return hashlib.sha256((bundle / name).read_bytes()).hexdigest()

    check(sha("receipt.json") == RECEIPT and sha("registration.json") == FREEZE, "identity")
    receipt, plan, summary = (load(name) for name in ("receipt.json", "plan.json", "summary.json"))
    check(receipt["phase"] == summary["phase"] == "enumeration", "phase")
    for name, digest in receipt["outputs"].items():
        check(sha(name) == digest, name)
    fields = tuple(sorted(plan["domains"]))
    view_fields = {v["name"]: v["fields"] for v in plan["views"]}
    groups = {name: defaultdict(list) for name in view_fields}
    expected_n = prod(len(values) for values in plan["domains"].values())
    ids, by_input, rows, labels = set(), {}, [], Counter()
    counts = {k: Counter() for k in PAIRS}
    timing_partition = Counter()
    timing_by_label = defaultdict(Counter)
    witnesses = load("witnesses.json")
    witness_rows = {w[key]["world_id"]: w[key] for w in witnesses for key in ("pass_world", "fail_world")}
    matched_witnesses = set()
    with gzip.open(bundle / "worlds.jsonl.gz", "rt", encoding="utf8") as records:
        for i, line in enumerate(records):
            r = json.loads(line)
            w, outcomes, ident = r["world"], r["outcomes"], r["world_id"]
            full_key = tuple(w[k] for k in fields)
            check(set(w) == set(fields) and all(w[k] in plan["domains"][k] for k in fields), "domains")
            check(ident == f"w{i:06d}" and ident not in ids and full_key not in by_input, "unique grid")
            check(set(outcomes) == set(plan["arms"]), "all arms")
            if ident in witness_rows:
                check(witness_rows[ident] == r, "witness agrees with raw world")
                matched_witnesses.add(ident)
            label = ("INELIGIBLE_AUTHORITY_OR_PHYSICAL" if not w["authority"] or not w["capacity"]
                     else "C" if w["cash"] + w["credit"] < plan["constants"]["service_cost"] else "U")
            check(label == r["pre_action_label"], "pre-action label")
            labels[label] += 1
            for o in outcomes.values():
                check(o["protected_floor"] == 1 and o["target_completed"] + o["other_completed"] <= w["capacity"],
                      "floor/capacity")
                check(w["payer_cash"] + w["payer_replenishment"] == o["payer_closing"] + o["grant_received"]
                      + o["other_completed"] + o["assurance_paid"], "payer balance")
                check(w["cash"] + w["continuation_income"] + o["grant_received"] + o["borrowed"]
                      == o["recipient_closing"] + o["target_completed"] + o["credit_repaid"]
                      + o["maintenance_paid"], "recipient balance")
                check(o["grant_received_t0"] + o["grant_received_t2"] == o["grant_received"] == 1 - o["grant_unpaid"],
                      "grant clocks")
                due = o["borrowed"] * (1 + w["credit_fee"])
                t2_paid = sum(e["amount"] for e in o["trace"] if e["clock"] == 2 and e["event"] == "credit_repaid")
                check(due - o["credit_repaid"] == o["credit_unpaid"] and due - t2_paid == o["credit_arrears_t2"],
                      "credit clocks")
                check(o["target_completed"] * w["continuation_due"] - o["maintenance_paid"] == o["maintenance_unpaid"]
                      and o["target_continued"] == int(o["target_completed"] and not o["maintenance_unpaid"]),
                      "continuation")
            deltas, flags = {}, {}
            for name, arm in PAIRS.items():
                t, u = outcomes[arm], outcomes["usual"]
                d = {k: t[k] - u[k] for k in METRICS}
                gain = d["target_completed"] > 0
                reasons = [k for k, condition in (
                    ("other_lost", d["other_completed"] < 0),
                    ("not_continued", not t["target_continued"]),
                    ("worse_obligation", any(d[x] > 0 for x in DEBT))) if condition]
                flag = gain and not reasons
                check(d == r["contrasts"][name] and flag == r["qualifies"][name], "contrast/diagnostic")
                counts[name].update(worlds=1, target_gains=int(gain), target_losses=int(d["target_completed"] < 0),
                                    other_losses=int(d["other_completed"] < 0), qualifying=int(flag))
                if name == "timing":
                    timing_by_label[label].update(worlds=1, target_gains=int(gain), qualifying=int(flag))
                    if gain:
                        timing_partition["+".join(reasons) if reasons else "qualifies"] += 1
                deltas[name], flags[name] = tuple(d[m] for m in METRICS), flag
            by_input[full_key] = (label, flags)
            ids.add(ident)
            rows.append((ident, label, flags, deltas, w["guarantee_credit"]))
            for name, visible in view_fields.items():
                groups[name][tuple(w[k] for k in visible)].append(i)
    check(len(rows) == expected_n == summary["world_count"] and 4 * expected_n == summary["arm_world_count"], "grid")
    check(dict(labels) == summary["pre_action_label_counts"] and matched_witnesses == set(witness_rows), "labels/witnesses")

    seen, aggregate, confusions = set(), defaultdict(Counter), defaultdict(Counter)
    with gzip.open(bundle / "classes.jsonl.gz", "rt", encoding="utf8") as records:
        for line in records:
            c = json.loads(line)
            view, contrast, obs = c["view"], c["contrast"], c["observed"]
            check(set(obs) == set(view_fields[view]), "pre-action fields")
            key = tuple(obs[k] for k in view_fields[view])
            signature = (view, contrast, key)
            check(signature not in seen and key in groups[view], "class membership")
            seen.add(signature)
            members = [rows[i] for i in groups[view][key]]
            n, hits = len(members), sum(row[2][contrast] for row in members)
            status = STATUSES[0] if hits == n else STATUSES[1] if hits == 0 else STATUSES[2]
            label_set = sorted({row[1] for row in members})
            label = label_set[0] if len(label_set) == 1 else "UNKNOWN"
            span = {k: [min(vals), max(vals)] for k, vals in
                    zip(METRICS, zip(*(row[3][contrast] for row in members)))}
            check((n, hits, status, label, label_set, span) == (c["world_count"], c["qualifying_worlds"],
                  c["status"], c["liquidity_label"], c["possible_labels"], c["bounds"]), "class count/status/bounds")
            check(sorted({row[4] for row in members}) == c["guarantee_credit_values"], "guarantee flags")
            for value, field in ((True, "first_pass"), (False, "first_fail")):
                check(next((x[0] for x in members if x[2][contrast] == value), None) == c[field], "witness ID")
            fill = plan["optimistic_fill"] | obs
            point_label, point_flags = by_input[tuple(fill[k] for k in fields)]
            point = point_flags[contrast]
            check(point == c["optimistic_positive"], "fill lookup")
            summary_key = (view, contrast)
            a = aggregate[summary_key]
            a[status] += 1
            a.update(class_denominator=1, world_denominator=n,
                     worlds_in_unidentified_classes=n if 0 < hits < n else 0,
                     worlds_with_unknown_liquidity_label=n if label == "UNKNOWN" else 0,
                     optimistic_positive_worlds=n if point else 0,
                     optimistic_false_positive_worlds=n - hits if point else 0,
                     optimistic_missed_qualifying_worlds=0 if point else hits)
            confusions[summary_key].update(x[1] + " -> " + point_label for x in members)
    check(len(seen) == len(PAIRS) * sum(map(len, groups.values())), "all equivalence classes")
    check(len(summary["reports"]) == len(aggregate) == len(view_fields) * len(PAIRS), "summary rows")
    readouts = {}
    for r in summary["reports"]:
        key = r["view"], r["contrast"]
        check(key not in readouts and key in aggregate, "unique summary identity")
        a = aggregate[key]
        for k in set(a) | set(STATUSES):
            check(r[k] == a[k], "summary " + k)
        check(dict(confusions[key]) == r["optimistic_label_confusions"], "classification confusion")
        readouts[key] = {k: a[k] for k in ("class_denominator", *STATUSES, "worlds_in_unidentified_classes",
                        "worlds_with_unknown_liquidity_label", "optimistic_positive_worlds",
                        "optimistic_false_positive_worlds", "optimistic_missed_qualifying_worlds")}
    for witness in witnesses:
        v, c, obs = witness["view"], witness["contrast"], witness["observed"]
        check(set(obs) == set(view_fields[v]), "witness visibility")
        for tag, truth in (("pass_world", True), ("fail_world", False)):
            r = witness[tag]
            check(witness_rows[r["world_id"]] == r and all(r["world"][k] == v for k, v in obs.items())
                  and r["qualifies"][c] == truth, "witness readout")
    return {"status": "RECOUNT_MATCH", "scope": "Recomputed from retained outcomes, not independent simulation.",
            "receipt_sha256": RECEIPT, "worlds": len(rows), "arm_worlds": 4 * len(rows),
            "class_contrast_rows": len(seen), "summary_rows": len(readouts), "witness_pairs": len(witnesses),
            "contrasts": counts, "timing_by_pre_action_label": timing_by_label,
            "timing_gain_partition_disjoint": timing_partition,
            "views": {v: {c: readouts[v, c] for c in PAIRS} for v in view_fields}}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--save", type=Path, help="optional new recount file; never overwrite")
    args = parser.parse_args()
    result = json.dumps(readout(args.bundle), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.save:
        with args.save.open("x", encoding="utf8", newline="\n") as f:
            f.write(result)
    print(result, end="")
