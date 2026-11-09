"""Finite, integer-valued accounting worlds; not an empirical policy model."""
from __future__ import annotations

from itertools import product
import math

FIELDS = (
    "cash", "credit", "credit_fee", "authority", "capacity", "credible",
    "incentive", "payer_cash", "payer_replenishment", "priority",
    "continuation_due", "continuation_income", "assurance_cost", "guarantee_credit",
)
ARMS = ("usual", "early", "assured", "early_assured")
CONSTANTS = ("grant", "service_cost", "other_service_cost", "protected_floor",
             "assurance_credit_increment")
CONTRASTS = {"timing": ("early", "usual"),
             "assurance": ("assured", "usual"),
             "combined": ("early_assured", "usual")}
METRICS = ("target_completed", "other_completed", "target_continued",
           "grant_unpaid", "credit_unpaid", "maintenance_unpaid",
           "credit_arrears_t2", "public_outflow", "real_service_spending")
CLAIM = "F0_INPUT_CONTRACT_ASSAY"


def integer(value, lo, hi):
    if type(value) is not int or not lo <= value <= hi:
        raise ValueError(f"expected integer in [{lo}, {hi}]")


def validate_world(w):
    if not isinstance(w, dict) or set(w) != set(FIELDS):
        raise ValueError("unknown or missing world field")
    for key in FIELDS:
        if key == "priority":
            if w[key] not in ("target_first", "other_first"):
                raise ValueError("invalid priority")
        else:
            integer(w[key], 1 if key == "payer_cash" else 0,
                    2 if key in ("capacity", "payer_cash", "continuation_due") else 1)


def validate_plan(p):
    keys = {"format", "claim_level", "base_commit", "max_processes", "arms",
            "constants", "domains", "views", "optimistic_fill", "smoke_base", "smoke_cases"}
    if not isinstance(p, dict) or set(p) != keys:
        raise ValueError("unknown or missing plan field")
    if (p["format"] != "executability-twins-plan/v1" or p["claim_level"] != CLAIM
            or p["arms"] != list(ARMS)
            or p["base_commit"] != "222976a2c7a0a3e622e380fcc280ddaad7733bf4"):
        raise ValueError("invalid study boundary")
    integer(p["max_processes"], 1, 2)
    if not isinstance(p["constants"], dict) or set(p["constants"]) != set(CONSTANTS):
        raise ValueError("invalid constants")
    for value in p["constants"].values():
        integer(value, 1, 1)
    validate_world(p["smoke_base"])
    validate_world(p["optimistic_fill"])
    if not isinstance(p["domains"], dict) or set(p["domains"]) != set(FIELDS):
        raise ValueError("invalid domains")
    for key, values in p["domains"].items():
        if not isinstance(values, list) or not values:
            raise ValueError("empty domain")
        for value in values:
            validate_world(p["smoke_base"] | {key: value})
        if len(set(values)) != len(values):
            raise ValueError("duplicate domain")
        for name in ("smoke_base", "optimistic_fill"):
            if p[name][key] not in values:
                raise ValueError("base/fill outside domain")
    if math.prod(len(v) for v in p["domains"].values()) > 100_000:
        raise ValueError("world budget exceeded")
    if not isinstance(p["views"], list) or not p["views"]:
        raise ValueError("empty views")
    seen, previous = set(), set()
    for view in p["views"]:
        if not isinstance(view, dict) or set(view) != {"name", "fields"}:
            raise ValueError("invalid view")
        if not isinstance(view["name"], str) or not view["name"] or view["name"] in seen:
            raise ValueError("invalid view name")
        fields = view["fields"]
        if (not isinstance(fields, list) or not all(isinstance(f, str) for f in fields)
                or len(fields) != len(set(fields)) or not previous <= set(fields) <= set(FIELDS)):
            raise ValueError("views must be nested pre-action fields")
        seen.add(view["name"])
        previous = set(fields)
    if previous != set(FIELDS):
        raise ValueError("last view must expose all declared inputs")
    if not isinstance(p["smoke_cases"], list) or not 1 <= len(p["smoke_cases"]) <= 32:
        raise ValueError("invalid smoke cases")
    names = set()
    worlds = set()
    for case in p["smoke_cases"]:
        if not isinstance(case, dict) or set(case) != {"name", "changes"}:
            raise ValueError("invalid smoke case")
        if not isinstance(case["name"], str) or not case["name"] or case["name"] in names:
            raise ValueError("duplicate/invalid smoke name")
        if not isinstance(case["changes"], dict) or not set(case["changes"]) <= set(FIELDS):
            raise ValueError("invalid smoke changes")
        w = p["smoke_base"] | case["changes"]
        validate_world(w)
        if any(w[k] not in p["domains"][k] for k in FIELDS):
            raise ValueError("smoke outside domain")
        key = tuple(w[k] for k in FIELDS)
        if key in worlds:
            raise ValueError("duplicate smoke world")
        names.add(case["name"])
        worlds.add(key)


def catalogue(plan, phase):
    validate_plan(plan)
    if phase == "smoke":
        return [(c["name"], plan["smoke_base"] | c["changes"]) for c in plan["smoke_cases"]]
    if phase != "enumeration":
        raise ValueError("unknown phase")
    return [(f"w{i:06d}", dict(zip(FIELDS, values)))
            for i, values in enumerate(product(*(plan["domains"][k] for k in FIELDS)))]


def liquidity_label(w):
    """Pre-action finance label; beliefs, incentives, spillovers stay separate."""
    if not w["authority"] or w["capacity"] == 0:
        return "INELIGIBLE_AUTHORITY_OR_PHYSICAL"
    return "C" if w["cash"] + w["credit"] < 1 else "U"


def simulate(w, arm):
    validate_world(w)
    if arm not in ARMS:
        raise ValueError("unknown arm")
    early = arm in ("early", "early_assured")
    assured = arm in ("assured", "early_assured")
    payer, cash = w["payer_cash"], w["cash"]
    trace = []

    def event(clock, name, amount):
        trace.append({"clock": clock, "event": name, "amount": amount})

    # t0: implementation cost precedes transfer. Unpaid transfers are retried at t2.
    assurance_paid = w["assurance_cost"] if assured and payer >= w["assurance_cost"] else 0
    assurance_active = int(assured and payer >= w["assurance_cost"])
    payer -= assurance_paid
    event(0, "assurance_cost", assurance_paid)
    grant = int(early and payer >= 1)
    payer -= grant
    cash += grant
    event(0, "grant_received", grant)
    credit = w["credit"] + assurance_active * w["guarantee_credit"]
    ready = bool(w["authority"] and w["incentive"]
                 and (w["credible"] or assurance_active) and cash + credit >= 1)
    capacity = w["capacity"]
    target, other, borrowed = 0, 0, 0
    order = ("target", "other") if w["priority"] == "target_first" else ("other", "target")
    # t1: one operational deadline, two competing added-service opportunities.
    for actor in order:
        if capacity == 0:
            continue
        if actor == "target" and ready:
            borrowed = max(0, 1 - cash)
            cash += borrowed - 1
            capacity -= 1
            target = 1
            event(1, "credit_drawn", borrowed)
            event(1, "target_service_paid", 1)
        elif actor == "other" and payer >= 1:
            payer -= 1
            capacity -= 1
            other = 1
            event(1, "other_service_paid", 1)
    # t2: committed replenishment, outstanding grant, then credit settlement.
    payer += w["payer_replenishment"]
    event(2, "payer_replenishment", w["payer_replenishment"])
    late_grant = int(not grant and payer >= 1)
    payer -= late_grant
    cash += late_grant
    grant += late_grant
    event(2, "grant_received", late_grant)
    debt = borrowed * (1 + w["credit_fee"])
    debt_paid = min(cash, debt)
    cash -= debt_paid
    arrears_t2 = debt - debt_paid
    event(2, "credit_repaid", debt_paid)
    # t3: committed continuation income, late debt recovery, then maintenance.
    cash += w["continuation_income"]
    event(3, "continuation_income", w["continuation_income"])
    late_debt_paid = min(cash, arrears_t2)
    debt_paid += late_debt_paid
    cash -= late_debt_paid
    event(3, "credit_repaid", late_debt_paid)
    due = target * w["continuation_due"]
    maintenance_paid = min(cash, due)
    cash -= maintenance_paid
    event(3, "maintenance_paid", maintenance_paid)
    result = {
        "target_completed": target, "other_completed": other,
        "target_continued": int(target and maintenance_paid == due),
        "protected_floor": 1, "assurance_active": assurance_active,
        "assurance_paid": assurance_paid, "grant_received": grant,
        "grant_received_t0": int(early and grant - late_grant == 1),
        "grant_received_t2": late_grant, "grant_unpaid": 1 - grant,
        "borrowed": borrowed, "credit_repaid": debt_paid,
        "credit_arrears_t2": arrears_t2, "credit_unpaid": debt - debt_paid,
        "maintenance_paid": maintenance_paid, "maintenance_unpaid": due - maintenance_paid,
        "payer_closing": payer, "recipient_closing": cash,
        "lender_net": debt_paid - borrowed,
        "public_outflow": grant + other + assurance_paid,
        "real_service_spending": target + other + maintenance_paid + assurance_paid,
        "trace": trace,
    }
    check_accounts(w, result)
    return result


def check_accounts(w, o):
    """Closed integer ledgers, with grant/credit transfers not counted as output."""
    recipient = (w["cash"] + o["grant_received"] + o["borrowed"]
                 + w["continuation_income"] - o["target_completed"]
                 - o["credit_repaid"] - o["maintenance_paid"])
    payer = w["payer_cash"] + w["payer_replenishment"] - o["public_outflow"]
    total = w["cash"] + w["payer_cash"] + w["payer_replenishment"] + w["continuation_income"]
    if (recipient != o["recipient_closing"] or payer != o["payer_closing"]
            or min(recipient, payer) < 0
            or total != recipient + payer + o["lender_net"] + o["real_service_spending"]
            or o["target_completed"] + o["other_completed"] > w["capacity"]
            or o["protected_floor"] != 1):
        raise ValueError("accounting/capacity/floor invariant failed")


def contrast(outcomes, name):
    treated, control = (outcomes[a] for a in CONTRASTS[name])
    return {m: treated[m] - control[m] for m in METRICS}


def qualifies(outcomes, name):
    """A declared diagnostic conjunction, NOT a justice or welfare criterion."""
    delta = contrast(outcomes, name)
    treated = outcomes[CONTRASTS[name][0]]
    return bool(delta["target_completed"] > 0 and delta["other_completed"] >= 0
                and treated["target_continued"] == 1
                and all(delta[k] <= 0 for k in ("grant_unpaid", "credit_unpaid",
                                               "maintenance_unpaid", "credit_arrears_t2")))


def evaluate(item):
    name, world = item
    outcomes = {arm: simulate(world, arm) for arm in ARMS}
    return {"world_id": name, "world": world, "pre_action_label": liquidity_label(world),
            "outcomes": outcomes,
            "contrasts": {k: contrast(outcomes, k) for k in CONTRASTS},
            "qualifies": {k: qualifies(outcomes, k) for k in CONTRASTS}}


def record_key(world, fields):
    if not set(fields) <= set(FIELDS):
        raise ValueError("post-action or unknown field requested")
    return tuple(world[k] for k in fields)


def compatible(rows, observed):
    """Explicit None means unobserved, never zero; no vacuous certification."""
    if not isinstance(observed, dict) or not set(observed) <= set(FIELDS):
        raise ValueError("post-action or unknown observation")
    for key, value in observed.items():
        if value is not None:
            probe = {k: ("target_first" if k == "priority" else 1) for k in FIELDS}
            validate_world(probe | {key: value})
    matches = [r for r in rows if all(value is None or r["world"][key] == value
                                    for key, value in observed.items())]
    if not matches:
        raise ValueError("OUT_OF_CATALOGUE: no compatible world")
    return matches


def bound_group(rows, name):
    if not rows:
        raise ValueError("empty identification set")
    flags = [r["qualifies"][name] for r in rows]
    labels = sorted({r["pre_action_label"] for r in rows})
    return {
        "world_count": len(rows),
        "liquidity_label": labels[0] if len(labels) == 1 else "UNKNOWN",
        "possible_labels": labels,
        "status": ("MODEL_ALL_PASS" if all(flags) else
                   "MODEL_ALL_FAIL" if not any(flags) else "UNIDENTIFIED_WITHIN_CATALOGUE"),
        "qualifying_worlds": sum(flags),
        "bounds": {m: [min(r["contrasts"][name][m] for r in rows),
                        max(r["contrasts"][name][m] for r in rows)] for m in METRICS},
        "first_pass": next((r["world_id"] for r in rows if r["qualifies"][name]), None),
        "first_fail": next((r["world_id"] for r in rows if not r["qualifies"][name]), None),
        "guarantee_credit_values": sorted({r["world"]["guarantee_credit"] for r in rows}),
    }
