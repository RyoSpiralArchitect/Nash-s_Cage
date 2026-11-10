import copy
import json
from pathlib import Path
import unittest
from model import (ARMS, AXES, actor_information, catalogue, evaluate, simulate,
                   validate_plan, validate_world, wants_review)

PLAN = json.loads((Path(__file__).parent / "plan.json").read_text())
BASE = PLAN["smoke"][0]


class ModelTests(unittest.TestCase):
    def world(self, **kw):
        return BASE | kw

    def test_catalogue_inputs_only(self):
        rows = catalogue(PLAN, "enumeration")
        self.assertEqual(len(rows), 18432)
        self.assertEqual(len({i for i, w in rows}), 18432)
        for i, w in rows: validate_world(w)

    def test_engineering_negative_control(self):
        for w in PLAN["smoke"]:
            self.assertEqual(simulate(w, "B"), simulate(w, "N"))

    def test_hand_computed_gain_without_displacement(self):
        r = evaluate(("x", BASE))
        self.assertEqual(r["arms"]["E"]["metrics"]["target_time"], 1)
        self.assertEqual(r["arms"]["B"]["metrics"]["target_time"], 4)
        self.assertEqual(r["contrasts"]["effective"]["target_on_time"], 1)
        self.assertEqual(r["contrasts"]["effective"]["other_completed"], 0)

    def test_payer_displacement_not_erased(self):
        r = evaluate(("x", self.world(payer_cash=2)))
        self.assertEqual(r["contrasts"]["effective"]["target_on_time"], 1)
        self.assertEqual(r["contrasts"]["effective"]["other_completed"], -1)

    def test_cost_can_harm_target(self):
        r = evaluate(("x", self.world(schedule="early", payer_cash=2, review_cost=1)))
        self.assertEqual(r["contrasts"]["effective"]["target_on_time"], -1)

    def test_shared_capacity_can_nullify_gain(self):
        r = evaluate(("x", self.world(capacity=1)))
        self.assertEqual(r["contrasts"]["effective"]["target_on_time"], 0)

    def test_unsafe_alternative_never_delivered(self):
        for w in PLAN["smoke"]:
            for a in ARMS:
                r = simulate(w | {"alternative": "unsafe"}, a)
                self.assertNotEqual(r["route"], "alternative")

    def test_hidden_safety_does_not_change_pre_review_actions(self):
        for a in ARMS:
            safe = simulate(self.world(review_delay=2, wrong_info=1), a)
            unsafe = simulate(self.world(review_delay=2, wrong_info=1, alternative="unsafe"), a)
            self.assertEqual([e for e in safe["events"] if e["t"] < 3],
                             [e for e in unsafe["events"] if e["t"] < 3])

    def test_guidance_not_true_future_controls_policy(self):
        i = actor_information(self.world(review_delay=2, wrong_info=1, alternative="absent"))
        self.assertTrue(wants_review(i))
        self.assertNotIn("safe", i)

    def test_eligibility_restores_next_tick_not_immediately(self):
        r = simulate(self.world(schedule="early", review_delay=2, wrong_info=1,
                     existing_access=1, eligibility_penalty=1, alternative="unsafe"), "B")
        states = {e["t"]:e for e in r["events"] if e["kind"]=="state"}
        self.assertTrue(states[0]["eligible"])
        self.assertFalse(states[2]["eligible"])
        self.assertFalse(states[3]["eligible"])
        self.assertTrue(states[4]["eligible"])
        self.assertIsNone(r["metrics"]["target_time"])

    def test_continuation_debt_is_separate(self):
        r = simulate(self.world(payer_cash=2, maintenance=1), "E")
        self.assertEqual(r["metrics"]["target_on_time"], 1)
        self.assertEqual(r["metrics"]["continued"], 0)
        self.assertEqual(r["metrics"]["unpaid"], 1)

    def test_can_request_is_not_success(self):
        r = simulate(self.world(alternative="unsafe", payer_cash=2, review_cost=1), "E")
        self.assertEqual(r["metrics"]["can_request"], 1)
        self.assertEqual(r["metrics"]["target_on_time"], 0)

    def test_ledger_time_and_floor(self):
        for w in PLAN["smoke"]:
            for a in ARMS:
                r=simulate(w,a)
                self.assertEqual([e["t"] for e in r["events"]], sorted(e["t"] for e in r["events"]))
                for e in r["events"]:
                    if e["kind"]=="state":
                        self.assertEqual(e["payer"]+e["recipient"]+e["spent"], w["payer_cash"]+w["recipient_cash"])
                        self.assertEqual(e["protected_floor"],1)

    def test_strict_types_and_shapes(self):
        for w in [BASE | {"capacity": True}, BASE | {"typo":1}, BASE | {"capacity":0}]:
            with self.assertRaises(ValueError): validate_world(w)
        p=copy.deepcopy(PLAN); p["axes"]["capacity"][0]=True
        with self.assertRaises(ValueError): validate_plan(p)

    def test_no_delivery_time_is_not_zero(self):
        r=evaluate(("x",self.world(schedule="early",payer_cash=2,review_cost=1)))
        self.assertIsNone(r["contrasts"]["effective"]["target_time"])

    def test_existing_route_is_not_removed_from_baseline(self):
        r=simulate(self.world(existing_access=1), "B")
        self.assertEqual(r["route"],"alternative")
        self.assertEqual(r["metrics"]["target_on_time"],1)

if __name__ == "__main__": unittest.main()
