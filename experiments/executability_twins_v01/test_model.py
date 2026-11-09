import copy
import json
from pathlib import Path
import unittest

import model


class ModelTests(unittest.TestCase):
    def setUp(self):
        self.plan = json.loads((Path(__file__).parent / "plan.json").read_text())
        self.base = self.plan["smoke_base"]

    def row(self, **changes):
        return model.evaluate(("case", self.base | changes))

    def test_declared_catalogue_budget_and_disjoint_ids(self):
        full = model.catalogue(self.plan, "enumeration")  # Inputs only, no evaluation.
        self.assertEqual(len(full), 36864)
        self.assertEqual(len({name for name, _ in full}), len(full))
        smoke = model.catalogue(self.plan, "smoke")
        self.assertEqual(len(smoke), 12)

    def test_timing_ledger_by_hand(self):
        row = self.row()
        ordinary, early = row["outcomes"]["usual"], row["outcomes"]["early"]
        self.assertEqual([ordinary[k] for k in ("target_completed", "other_completed",
                         "payer_closing", "recipient_closing", "grant_received_t2")], [0, 1, 1, 2, 1])
        self.assertEqual([early[k] for k in ("target_completed", "other_completed",
                         "target_continued", "payer_closing", "recipient_closing")], [1, 1, 1, 1, 0])
        self.assertTrue(row["qualifies"]["timing"])
        self.assertEqual(early["real_service_spending"], 3)
        self.assertEqual(early["public_outflow"], 2)

    def test_hidden_credit_changes_pre_action_label_not_observed_cash(self):
        constrained, unconstrained = self.row(), self.row(credit=1)
        self.assertEqual(constrained["pre_action_label"], "C")
        self.assertEqual(unconstrained["pre_action_label"], "U")
        self.assertEqual(constrained["world"]["cash"], unconstrained["world"]["cash"])
        self.assertFalse(unconstrained["qualifies"]["timing"])
        bound = model.bound_group([constrained, unconstrained], "timing")
        self.assertEqual(bound["liquidity_label"], "UNKNOWN")
        self.assertEqual(bound["bounds"]["target_completed"], [0, 1])

    def test_four_distinct_failures_are_not_renamed(self):
        for changes, label in (({"capacity": 0}, "INELIGIBLE_AUTHORITY_OR_PHYSICAL"),
                               ({"authority": 0}, "INELIGIBLE_AUTHORITY_OR_PHYSICAL"),
                               ({"credible": 0}, "C"), ({"incentive": 0}, "C")):
            row = self.row(**changes)
            self.assertEqual(row["pre_action_label"], label)
            self.assertEqual(row["outcomes"]["early"]["target_completed"], 0)
            self.assertFalse(row["qualifies"]["timing"])

    def test_assurance_does_not_create_physical_capacity_or_change_incentives(self):
        for changes in ({"capacity": 0}, {"incentive": 0}, {"authority": 0}):
            row = self.row(**changes)
            self.assertTrue(all(o["target_completed"] == 0 for o in row["outcomes"].values()))

    def test_payer_displacement_is_not_erased_by_target_gain(self):
        row = self.row(payer_cash=1)
        self.assertEqual(row["contrasts"]["timing"]["target_completed"], 1)
        self.assertEqual(row["contrasts"]["timing"]["other_completed"], -1)
        self.assertFalse(row["qualifies"]["timing"])

    def test_shared_capacity_and_priority(self):
        target_first = self.row(capacity=1)
        other_first = self.row(capacity=1, priority="other_first")
        self.assertEqual(target_first["contrasts"]["timing"]["other_completed"], -1)
        self.assertEqual(other_first["contrasts"]["timing"]["target_completed"], 0)

    def test_continuation_debt_and_disbursement_clocks(self):
        row = self.row(continuation_due=2, continuation_income=0)
        early = row["outcomes"]["early"]
        self.assertEqual(early["target_completed"], 1)
        self.assertEqual(early["target_continued"], 0)
        self.assertEqual(early["maintenance_unpaid"], 2)
        self.assertFalse(row["qualifies"]["timing"])
        row = self.row(payer_cash=1, payer_replenishment=0, credit=1)
        self.assertEqual(row["outcomes"]["usual"]["grant_unpaid"], 1)
        self.assertEqual(row["outcomes"]["usual"]["credit_arrears_t2"], 1)

    def test_guarantee_credit_channel_is_explicit(self):
        pure = self.row(credible=0)
        bundle = self.row(credible=0, guarantee_credit=1)
        self.assertEqual(pure["outcomes"]["assured"]["target_completed"], 0)
        self.assertEqual(bundle["outcomes"]["assured"]["target_completed"], 1)
        self.assertEqual(bundle["outcomes"]["assured"]["borrowed"], 1)

    def test_setup_cost_can_prevent_early_receipt(self):
        o = self.row(payer_cash=1, assurance_cost=1)["outcomes"]["early_assured"]
        self.assertEqual(o["assurance_paid"], 1)
        self.assertEqual(o["grant_received_t0"], 0)
        self.assertEqual(o["grant_received_t2"], 1)
        self.assertEqual(o["target_completed"], 0)

    def test_frozen_floor_and_accounts_across_smoke(self):
        for item in model.catalogue(self.plan, "smoke"):
            row = model.evaluate(item)
            for outcome in row["outcomes"].values():
                self.assertEqual(outcome["protected_floor"], 1)
                model.check_accounts(row["world"], outcome)
                mutated = copy.deepcopy(outcome)
                mutated["recipient_closing"] += 1
                with self.assertRaises(ValueError):
                    model.check_accounts(row["world"], mutated)

    def test_observation_filter_is_pre_action_and_fail_closed(self):
        rows = [self.row(), self.row(credit=1)]
        self.assertEqual(len(model.compatible(rows, {"credit": None})), 2)
        self.assertEqual(len(model.compatible(rows, {"credit": 0})), 1)
        for observation in ({"target_completed": 1}, {"credit": True}, {"capacity": 9}, {"cash": 1}):
            with self.assertRaises(ValueError):
                model.compatible(rows, observation)
        with self.assertRaises(ValueError):
            model.bound_group([], "timing")
        with self.assertRaises(ValueError):
            model.record_key(self.base, ["target_completed"])

    def test_added_observations_can_only_narrow_finite_bounds(self):
        rows = [model.evaluate(item) for item in model.catalogue(self.plan, "smoke")]
        for row in rows:
            old = None
            for view in self.plan["views"]:
                observed = {f: row["world"][f] for f in view["fields"]}
                bounds = model.bound_group(model.compatible(rows, observed), "timing")["bounds"]
                for metric, (lo, hi) in bounds.items():
                    self.assertLessEqual(lo, row["contrasts"]["timing"][metric])
                    self.assertGreaterEqual(hi, row["contrasts"]["timing"][metric])
                    if old:
                        self.assertGreaterEqual(lo, old[metric][0])
                        self.assertLessEqual(hi, old[metric][1])
                old = bounds
            self.assertTrue(all(lo == hi for lo, hi in old.values()))

    def test_strict_plan_contract(self):
        for mutation in (
            lambda p: p.update(unrecognized=True),
            lambda p: p["constants"].update(grant=True),
            lambda p: p["domains"].update(cash=[0, 0]),
            lambda p: p["domains"].update(credit=[False, 1]),
            lambda p: p["views"][0]["fields"].append("target_completed"),
            lambda p: p["views"][-1]["fields"].remove("credit"),
            lambda p: p["smoke_cases"].append(p["smoke_cases"][0]),
        ):
            plan = copy.deepcopy(self.plan)
            mutation(plan)
            with self.assertRaises(ValueError):
                model.validate_plan(plan)

    def test_no_randomness_or_arm_order_dependence(self):
        row = self.row(credit=1, credit_fee=1)
        for arm in reversed(model.ARMS):
            self.assertEqual(model.simulate(self.base | {"credit": 1, "credit_fee": 1}, arm), row["outcomes"][arm])


if __name__ == "__main__":
    unittest.main()
