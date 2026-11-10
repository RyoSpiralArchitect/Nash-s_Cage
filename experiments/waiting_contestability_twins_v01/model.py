"""Finite F0 waiting-route assay. No real institutions or strategic equilibrium."""
from itertools import product

CLAIM = "F0_INPUT_CONTRACT_ASSAY"
ARMS = ("B", "N", "E")
CONTRASTS = {"effective": ("E", "N"), "nominal": ("N", "B")}
AXES = {
    "schedule": ["early", "late", "patient"],
    "alternative": ["absent", "safe", "unsafe"],
    "expiry": [2, 4], "review_delay": [0, 2], "access_cost": [0, 1],
    "recipient_cash": [0, 1], "eligibility_penalty": [0, 1],
    "capacity": [1, 2], "payer_cash": [2, 3], "review_cost": [0, 1],
    "maintenance": [0, 1], "existing_access": [0, 1], "wrong_info": [0, 1],
}
FIELDS = tuple(AXES)
VIEWS = [
    {"name": "administrative", "fields": ["schedule", "recipient_cash", "payer_cash"]},
    {"name": "authority", "fields": ["schedule", "recipient_cash", "payer_cash", "existing_access"]},
    {"name": "access", "fields": ["schedule", "recipient_cash", "payer_cash", "existing_access", "access_cost", "review_delay", "wrong_info"]},
    {"name": "consequences", "fields": [k for k in FIELDS if k != "alternative"]},
    {"name": "full_model_evaluator_only", "fields": list(FIELDS)},
]
METRICS = ("target_on_time", "other_completed", "continued", "unpaid", "target_time", "total_cost", "unused_safe_alternative", "pending_review", "can_request", "requested", "eligibility_lost", "recipient_cost", "payer_cost")


def integer(x, lo, hi):
    if type(x) is not int or not lo <= x <= hi:
        raise ValueError("invalid integer")


def validate_plan(p):
    expected = {"format", "claim_level", "axes", "views", "max_processes", "world_count", "horizon", "smoke"}
    if set(p) != expected or p["format"] != "waiting-contestability-plan/v1" or p["claim_level"] != CLAIM:
        raise ValueError("invalid plan schema")
    if p["axes"] != AXES or p["views"] != VIEWS:
        raise ValueError("unreviewed catalogue/view change")
    for k, values in p["axes"].items():
        if any(type(v) is not type(AXES[k][0]) for v in values):
            raise ValueError("invalid axis types")
    for k, v in (("max_processes", 1), ("world_count", 18432), ("horizon", 6)):
        integer(p[k], v, v)
    if type(p["smoke"]) is not list or not p["smoke"]:
        raise ValueError("empty smoke")
    for w in p["smoke"]:
        validate_world(w)


def validate_world(w):
    if set(w) != set(FIELDS):
        raise ValueError("unknown/missing world keys")
    for k, v in w.items():
        if type(v) is not type(AXES[k][0]) or v not in AXES[k]:
            raise ValueError("invalid world value: " + k)


def catalogue(plan, phase):
    validate_plan(plan)
    if phase == "smoke":
        return [(f"s{i:03}", w) for i, w in enumerate(plan["smoke"])]
    if phase != "enumeration":
        raise ValueError("unknown phase")
    return [(f"w{i:05}", dict(zip(FIELDS, v)))
            for i, v in enumerate(product(*(AXES[k] for k in FIELDS)))]


def actor_information(w):
    # Safety is deliberately absent: known only after review. Guidance is shared by arms.
    return {"announced_available": w["alternative"] != "absent" or bool(w["wrong_info"]),
            "announced_delay": 0 if w["wrong_info"] else w["review_delay"],
            "usual_time": 2 if w["schedule"] == "early" else 4,
            "deadline": 5 if w["schedule"] == "patient" else 3,
            "expiry": w["expiry"]}


def wants_review(info):
    arrival = 1 + info["announced_delay"]
    return (info["announced_available"] and arrival <= min(info["deadline"], info["expiry"])
            and arrival < info["usual_time"])


def simulate(w, arm):
    validate_world(w)
    if arm not in ARMS:
        raise ValueError("unknown arm")
    payer, recipient, spent = w["payer_cash"], w["recipient_cash"], 0
    initial = payer + recipient
    events = []
    def log(t, kind, **fields):
        events.append({"t": t, "kind": kind, **fields})
    def pay(t, actor, amount, kind):
        nonlocal payer, recipient, spent
        balance = payer if actor == "payer" else recipient
        if balance < amount:
            raise AssertionError("negative cash")
        if actor == "payer": payer -= amount
        else: recipient -= amount
        spent += amount
        log(t, kind, actor=actor, amount=amount)
    enabled = arm == "E"
    if enabled:
        pay(0, "payer", 1, "setup")
    info = actor_information(w)
    access = bool(w["existing_access"] or enabled)
    fee_actor = "payer" if enabled else "recipient"
    funding_ok = (payer >= w["review_cost"] + (w["access_cost"] if enabled else 0)
                  and (enabled or recipient >= w["access_cost"]))
    can_request = bool(access and funding_ok)  # Defined before outcome; not successful protection.
    requested = bool(can_request and wants_review(info))
    penalty = bool(requested and w["eligibility_penalty"] and not enabled)
    review_due = 1 + w["review_delay"] if requested else None
    pending = False
    decision = None
    restore_at = None
    target_time = None
    route = None
    other = False
    unpaid = 0
    continued = False
    for t in range(7):
        slots = w["capacity"]
        if t == 1 and requested:
            pending = True
            pay(t, fee_actor, w["access_cost"], "access")
            pay(t, "payer", w["review_cost"], "review_fee")
        # Fixed order: existing floor (separate); other service; review; target; maintenance.
        if t == 2 and payer >= 1 and slots:
            pay(t, "payer", 1, "other_service")
            slots -= 1
            other = True
        if pending and t >= review_due and slots:
            slots -= 1
            pending = False
            decision = "approve" if w["alternative"] == "safe" else "deny"
            restore_at = t + 1
            log(t, "review", decision=decision)
        eligible = t < 1 or not penalty or (restore_at is not None and t >= restore_at)
        # Ordinary route is a one-time delivery window, not an automatically renewed queue.
        usual_ready = t == info["usual_time"] and eligible
        alt_ready = decision == "approve" and t <= w["expiry"]
        if target_time is None and (alt_ready or usual_ready) and slots and payer >= 1:
            route = "alternative" if alt_ready else "usual"
            pay(t, "payer", 1, "target_service")
            slots -= 1
            target_time = t
            log(t, "delivery", route=route)
        # Every possible delivery by t5 has follow-up inside the declared t0..t6 horizon.
        if target_time is not None and t == target_time + 1:
            due = w["maintenance"]
            paid = min(payer, due)
            pay(t, "payer", paid, "maintenance")
            unpaid = due - paid
            continued = unpaid == 0
        log(t, "state", payer=payer, recipient=recipient, spent=spent,
            capacity_used=w["capacity"]-slots, pending_review=pending,
            eligible=eligible, target_time=target_time, other_completed=other,
            unpaid=unpaid, protected_floor=1)
        assert payer + recipient + spent == initial and 0 <= slots <= w["capacity"]
    assert target_time is None or target_time <= 4
    metrics = {
        "target_on_time": int(target_time is not None and target_time <= info["deadline"]),
        "other_completed": int(other), "continued": int(continued), "unpaid": unpaid,
        "target_time": target_time, "total_cost": spent,
        "unused_safe_alternative": int(w["alternative"] == "safe" and route != "alternative"),
        "pending_review": int(pending), "can_request": int(can_request),
        "requested": int(requested), "eligibility_lost": int(penalty),
        "recipient_cost": w["recipient_cash"]-recipient,
        "payer_cost": w["payer_cash"]-payer,
    }
    return {"metrics": metrics, "route": route, "guidance": info,
            "no_request_reason": (None if requested else "access_or_funding" if not can_request else "prefer_usual_or_no_timely_announced_route"),
            "events": events}


def evaluate(item):
    ident, w = item
    arms = {a: simulate(w, a) for a in ARMS}
    assert arms["B"] == arms["N"], "label-only negative control failed"
    contrasts = {}
    for name, (a, b) in CONTRASTS.items():
        ma, mb = arms[a]["metrics"], arms[b]["metrics"]
        # A missing delivery time is not zero or an invented finite delay.
        contrasts[name] = {k: None if ma[k] is None or mb[k] is None else ma[k]-mb[k] for k in METRICS}
    return {"world_id": ident, "world": w, "arms": arms, "contrasts": contrasts}


def record_key(w, fields):
    return tuple(w[k] for k in fields)


def bound_group(rows, contrast):
    result = {}
    for key in METRICS:
        values = [r["contrasts"][contrast][key] for r in rows]
        defined = [v for v in values if v is not None]
        result[key] = {"min": min(defined) if defined else None,
                       "max": max(defined) if defined else None,
                       "undefined": len(values)-len(defined)}
    return {"worlds": len(rows), "bounds": result}
