"""Contract, information-boundary, resource, and tamper tests for this lane."""
import copy
from dataclasses import fields, replace
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

import run as h


class ModelTests(unittest.TestCase):
    def setUp(self):
        self.plan = h.decode((h.HERE / "plan.json").read_bytes())
        self.p = self.plan["defaults"].copy()

    def case(self, overrides=None, seed=11):
        p = self.p | (overrides or {})
        s = {"id": "test", "cohort": "control", "params": p}
        people, days = h.world(self.plan, p, seed)
        return [h.episode(self.plan, s, seed, a, people, days, True) for a in h.ARMS]

    def test_plan_counts_and_phase_separation(self):
        h.validate_plan(self.plan)
        self.assertEqual(len(h.scenarios(self.plan)), 80)
        self.assertEqual(80 * len(self.plan["evaluation_seeds"]) * 4, 10240)
        self.assertFalse(set(self.plan["development_seeds"]) & set(self.plan["evaluation_seeds"]))

    def test_existing_institution_cannot_be_abolished(self):
        for value in (False, 0, 1, "true"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                h.validate_plan(self.plan | {"institution_exists": value})

    def test_nonfinite_and_boolean_parameters_refused(self):
        for key in h.PARAMS:
            for value in (float("nan"), float("inf"), float("-inf"), True):
                with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                    h.validate_params(self.p | {key: value})

    def test_unknown_parameters_refused(self):
        with self.assertRaises(ValueError):
            h.validate_params(self.p | {"new_gain": 10})
        with self.assertRaises(ValueError):
            h.validate_plan(self.plan | {"new_gain": 10})

    def test_probability_and_money_bounds(self):
        for p in ({"existing_coverage": -0.1}, {"existing_coverage": 1.01},
                  {"worker_transfer": 1.01}, {"action_cost": 0}, {"budget_per_worker": -1}):
            with self.subTest(p=p), self.assertRaises(ValueError):
                h.validate_params(self.p | p)

    def test_duplicate_and_overlapping_seeds(self):
        for field, seeds in (("development_seeds", [11, 11]), ("evaluation_seeds", [11])):
            with self.assertRaises(ValueError):
                h.validate_plan(self.plan | {field: seeds})

    def test_claim_gate_cannot_be_removed(self):
        with self.assertRaises(ValueError):
            h.validate_plan(self.plan | {"unknown_gates": []})
        with self.assertRaises(ValueError):
            h.validate_plan(self.plan | {"claim_level": "EMPIRICALLY_VALIDATED"})

    def test_world_deterministic(self):
        self.assertEqual(h.world(self.plan, self.p, 7), h.world(self.plan, self.p, 7))
        self.assertNotEqual(h.world(self.plan, self.p, 7), h.world(self.plan, self.p, 8))

    def test_policy_interface_has_no_hidden_state(self):
        self.assertEqual({f.name for f in fields(h.PublicFrame)},
                         {"observation", "baseline_ids", "slots", "people", "day"})
        people, _ = h.world(self.plan, self.p, 7)
        frame = h.PublicFrame(3.0, (), 6, people, 0)
        a = h.choose(frame, self.p, 24.0, True)
        self.assertEqual(a, h.choose(frame, self.p, 24.0, True))
        self.assertEqual(h.choose(replace(frame, observation=0), self.p, 24.0, True)[0], ())
        with self.assertRaises(ValueError):
            h.choose(replace(frame, observation=float("nan")), self.p, 24.0, True)

    def test_future_outcomes_cannot_change_prefix(self):
        people, days = h.world(self.plan, self.p, 11)
        s = {"id": "test", "cohort": "control", "params": self.p}
        changed = days[:4] + tuple(replace(d, hazard=0.0, delivery_jitter=(0.0,) * len(people)) for d in days[4:])
        for arm in h.ARMS:
            _, a = h.episode(self.plan, s, 11, arm, people, days, True)
            _, b = h.episode(self.plan, s, 11, arm, people, changed, True)
            self.assertEqual(a[:4], b[:4])

    def test_existing_floor_identical_in_all_arms(self):
        for coverage in (0.25, 0.6, 1.0):
            outcomes = self.case({"existing_coverage": coverage})
            self.assertEqual(len({r["baseline_protected_person_days"] for r, _ in outcomes}), 1)
            for day in range(self.plan["days"]):
                self.assertEqual(len({t[day]["baseline_protected"] for _, t in outcomes}), 1)

    def test_full_existing_protection_null(self):
        results = self.case({"existing_coverage": 1.0})
        for r, _ in results:
            self.assertEqual(r["residual_exposure"], 0)
            self.assertEqual(r["additional_actions"], 0)
            self.assertEqual(r["discretionary_spent"], 0)
        for key in h.METRICS:
            self.assertEqual(len({r[key] for r, _ in results}), 1)

    def test_zero_budget_preserves_floor(self):
        results = self.case({"budget_per_worker": 0.0})
        for r, _ in results:
            self.assertEqual(r["additional_actions"], 0)
            self.assertEqual(r["discretionary_spent"], 0)
            self.assertGreater(r["baseline_protected_person_days"], 0)
            self.assertGreater(r["total_public_cost"], 0)
        self.assertEqual(len({r["residual_exposure"] for r, _ in results}), 1)

    def test_zero_capacity(self):
        for r, _ in self.case({"additional_capacity_fraction": 0.0}):
            self.assertEqual(r["additional_actions"], 0)
            self.assertEqual(r["discretionary_spent"], 0)

    def test_no_hazard_exposure_zero_not_cost_zero(self):
        for r, _ in self.case({"hot_day_probability": 0.0}):
            self.assertEqual(r["residual_exposure"], 0)
            self.assertGreater(r["total_public_cost"], 0)

    def test_information_null_identity(self):
        results = self.case({"information_noise_multiplier": 1, "information_setup_per_worker": 0})
        for a, b in ((0, 1), (2, 3)):
            for key in h.METRICS:
                self.assertEqual(results[a][0][key], results[b][0][key])

    def test_link_null_identity(self):
        results = self.case({"link_effect": 0, "link_setup_per_worker": 0})
        for a, b in ((0, 2), (1, 3)):
            for key in h.METRICS:
                self.assertEqual(results[a][0][key], results[b][0][key])

    def test_resource_and_population_denominators(self):
        for budget in (0.1, 0.8, 3.0):
            for r, t in self.case({"budget_per_worker": budget}):
                self.assertAlmostEqual(r["discretionary_spent"] + r["budget_remaining"], budget * 24)
                self.assertLessEqual(r["discretionary_spent"], budget * 24 + h.EPS)
                self.assertGreaterEqual(r["budget_remaining"], 0)
                self.assertAlmostEqual(r["residual_exposure"], (r["constrained_exposure"] + r["other_exposure"]) / 2)
                self.assertTrue(all(x["actions"] <= 18 and x["budget_remaining"] >= 0 for x in t))

    def test_ordinary_is_an_active_comparator(self):
        r, _ = self.case({"friction": 0, "hot_day_probability": 1.0})[0]
        self.assertGreater(r["additional_actions"], 0)
        self.assertGreater(r["baseline_protected_person_days"], 0)

    def test_common_bias_is_not_removed_by_clearer_information(self):
        p = self.p | {"signal_noise": 0, "signal_bias": 0.7}
        people, days = h.world(self.plan, p, 11)
        s = {"id": "test", "cohort": "control", "params": p}
        for a in h.ARMS:
            _, t = h.episode(self.plan, s, 11, a, people, days, True)
            self.assertAlmostEqual(t[0]["policy_observation"] - t[0]["evaluator_true_hazard"], 0.7)

    def test_late_delivery_is_retained(self):
        plan = self.plan | {"days": 1}
        people, _ = h.world(plan, self.p, 11)
        day = h.WorldDay(3.0, 0.0, (), (0.5,) * 24)
        s = {"id": "test", "cohort": "control", "params": self.p}
        r, _ = h.episode(plan, s, 11, "ordinary", people, (day,), True)
        self.assertGreater(r["additional_actions"], 0)
        self.assertEqual(r["late_actions"], r["additional_actions"])


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        self.source = self.root / "source"
        self.source.mkdir()
        for name in h.INPUT_NAMES:
            shutil.copyfile(h.HERE / name, self.source / name)
        p = h.decode((self.source / "plan.json").read_bytes())
        p.update(workers=4, days=3, development_seeds=[11], evaluation_seeds=[1000, 1001])
        p["factors"] = {k: [p["defaults"][k]] for k in h.FACTORS}
        (self.source / "plan.json").write_bytes(h.encode(p))
        self.here_patch = patch.object(h, "HERE", self.source)
        self.here_patch.start()
        self.reg = self.root / "freeze" / "registration.json"
        self.out = self.root / "out"
        h.freeze(self.reg.parent)

    def tearDown(self):
        self.here_patch.stop()
        self.temp.cleanup()

    def make_run(self):
        return h.run(self.reg, "evaluation", self.out, 1)

    def test_full_replay(self):
        result = self.make_run()
        self.assertEqual(result["arm_seasons"], 9 * 2 * 4)
        self.assertEqual(result["winner"], "none")
        self.assertEqual(result["unknown_gates"], h.GATES)
        self.assertTrue(h.verify(self.out, True)["replayed"])

    def test_registration_source_drift_refused(self):
        with (self.source / "README.md").open("a") as f:
            f.write("changed")
        with self.assertRaises(ValueError):
            self.make_run()
        self.assertFalse(self.out.exists())

    def test_source_drift_during_computation_refused(self):
        original = h.compute
        def changed(*args):
            result = original(*args)
            (self.source / "README.md").write_text("changed")
            return result
        with patch.object(h, "compute", side_effect=changed), self.assertRaises(ValueError):
            self.make_run()
        self.assertFalse(self.out.exists())

    def test_existing_output_never_overwritten(self):
        self.make_run()
        before = h.output_snapshot(self.out)
        with self.assertRaises(ValueError):
            self.make_run()
        self.assertEqual(before, h.output_snapshot(self.out))

    def test_existing_empty_directory_never_overwritten(self):
        target = self.root / "existing"
        target.mkdir()
        with self.assertRaises(ValueError):
            h.publish(target, {"evidence": b"hello"})
        self.assertEqual(list(target.iterdir()), [])

    def test_duplicate_and_nonfinite_json_refused(self):
        for b in (b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":Infinity}', b'{"x":-Infinity}'):
            with self.subTest(b=b), self.assertRaises(ValueError):
                h.decode(b)

    def test_artifact_tampering_detected(self):
        self.make_run()
        (self.out / "episodes.csv").write_text("changed")
        with self.assertRaises(ValueError):
            h.verify(self.out)

    def test_extra_file_and_directory_rejected(self):
        self.make_run()
        (self.out / "unexpected").mkdir()
        with self.assertRaises(ValueError):
            h.verify(self.out)

    def test_rehashed_wrong_results_fail_replay(self):
        self.make_run()
        target = self.out / "episodes.csv"
        target.write_bytes(target.read_bytes() + b"bogus\n")
        receipt = h.decode((self.out / "receipt.json").read_bytes())
        receipt["outputs"]["episodes.csv"] = h.digest(target.read_bytes())
        (self.out / "receipt.json").write_bytes(h.encode(receipt))
        self.assertTrue(h.verify(self.out, False)["verified"])
        with self.assertRaises(ValueError):
            h.verify(self.out, True)

    def test_claim_promotion_rejected_even_if_rehashed(self):
        self.make_run()
        target = self.out / "summary.json"
        summary = h.decode(target.read_bytes())
        summary["winner"] = "information_linked"
        target.write_bytes(h.encode(summary))
        receipt = h.decode((self.out / "receipt.json").read_bytes())
        receipt["outputs"]["summary.json"] = h.digest(target.read_bytes())
        (self.out / "receipt.json").write_bytes(h.encode(receipt))
        with self.assertRaises(ValueError):
            h.verify(self.out)

    def test_path_traversal_in_receipt_rejected(self):
        self.make_run()
        receipt = h.decode((self.out / "receipt.json").read_bytes())
        receipt["outputs"]["../elsewhere"] = "0" * 64
        (self.out / "receipt.json").write_bytes(h.encode(receipt))
        with self.assertRaises(ValueError):
            h.verify(self.out)

    def test_receipt_trust_claim_cannot_be_promoted(self):
        self.make_run()
        path = self.out / "receipt.json"
        receipt = h.decode(path.read_bytes())
        receipt["trust_model"] = "Externally authenticated and empirically validated."
        path.write_bytes(h.encode(receipt))
        for replay in (False, True):
            with self.subTest(replay=replay), self.assertRaises(ValueError):
                h.verify(self.out, replay)

    def test_runtime_schema_is_validated(self):
        self.make_run()
        path = self.out / "receipt.json"
        receipt = h.decode(path.read_bytes())
        runtime = receipt["runtime"]
        invalid = [None, "authenticated", {}, runtime | {"extra": "claim"}]
        invalid += [runtime | {key: value} for key, value in (
            ("python", None), ("python", ""), ("python", "externally authenticated"),
            ("system", True), ("system", ""), ("machine", []),
            ("processes", True), ("processes", 0), ("processes", 3),
            ("elapsed_seconds", -1), ("elapsed_seconds", True), ("elapsed_seconds", "1"))]
        for value in invalid:
            path.write_bytes(h.encode(receipt | {"runtime": value}))
            for replay in (False, True):
                with self.subTest(runtime=value, replay=replay), self.assertRaises(ValueError):
                    h.verify(self.out, replay)

    def rewrite_registration(self, record):
        path = self.out / "registration.json"
        path.write_bytes(h.encode(record))
        receipt_path = self.out / "receipt.json"
        receipt = h.decode(receipt_path.read_bytes())
        receipt["outputs"]["registration.json"] = h.digest(path.read_bytes())
        receipt_path.write_bytes(h.encode(receipt))

    def test_registration_scope_cannot_be_promoted_even_if_rehashed(self):
        self.make_run()
        reg = h.decode((self.out / "registration.json").read_bytes())
        reg["scope"] = "Independent third-party preregistration."
        self.rewrite_registration(reg)
        for replay in (False, True):
            with self.subTest(replay=replay), self.assertRaises(ValueError):
                h.verify(self.out, replay)

    def test_invalid_registration_timestamp_rejected_even_if_rehashed(self):
        self.make_run()
        reg = h.decode((self.out / "registration.json").read_bytes())
        for value in (None, True, 0, "", "not a timestamp", "2026-02-30T00:00:00Z",
                      "2026-09-09T11:17:32", "2026-09-09T11:17:32+09:00"):
            self.rewrite_registration(reg | {"created_utc": value})
            for replay in (False, True):
                with self.subTest(timestamp=value, replay=replay), self.assertRaises(ValueError):
                    h.verify(self.out, replay)

    def test_invalid_registration_refused_before_generation(self):
        reg = h.decode(self.reg.read_bytes())
        for field, value in (("scope", "Externally registered"), ("created_utc", "not a timestamp")):
            self.reg.write_bytes(h.encode(reg | {field: value}))
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.make_run()
            self.assertFalse(self.out.exists())

    def test_registration_accepts_explicit_utc_not_external_authentication(self):
        reg = h.decode(self.reg.read_bytes())
        for value in ("2026-09-09T11:17:32.090207+00:00", "2026-09-09T11:17:32Z"):
            self.reg.write_bytes(h.encode(reg | {"created_utc": value}))
            _, checked = h.registration(self.reg)
            self.assertEqual(checked["scope"], h.REGISTRATION_SCOPE)

    def test_runtime_is_self_reported_not_compared_to_verifier_platform(self):
        self.make_run()
        path = self.out / "receipt.json"
        receipt = h.decode(path.read_bytes())
        receipt["runtime"].update(python="3.14.4", system="Linux", machine="x86_64")
        path.write_bytes(h.encode(receipt))
        self.assertTrue(h.verify(self.out, True)["replayed"])

    def test_symlink_input_and_output_rejected(self):
        alias = self.root / "alias"
        try:
            alias.symlink_to(self.reg)
        except OSError:
            self.skipTest("symlinks unavailable on this platform")
        with self.assertRaises(ValueError):
            h.registration(alias)
        alias_dir = self.root / "alias_dir"
        alias_dir.symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(ValueError):
            h.publish(alias_dir / "output", {"a": b"b"})

    def test_unknown_phase_and_excess_processes_rejected(self):
        for phase, processes in (("bad", 1), ("evaluation", 0), ("evaluation", 3)):
            with self.assertRaises(ValueError):
                h.run(self.reg, phase, self.out, processes)

    def test_inputs_and_outputs_rechecked_after_replay(self):
        self.make_run()
        original = h.compute
        def changed(*args):
            result = original(*args)
            (self.out / "surprise").write_text("new")
            return result
        with patch.object(h, "compute", side_effect=changed), self.assertRaises(ValueError):
            h.verify(self.out, True)


class ArchivedEvidenceTests(unittest.TestCase):
    def test_original_inputs_and_receipts_are_preserved(self):
        base = h.HERE.parents[1] / "artifacts/heat_institution_v01"
        frozen = h.input_hashes(h.R01_INPUT_DIR)
        self.assertEqual(h.INPUT_NAMES, {p.name for p in h.R01_INPUT_DIR.iterdir()})
        for phase in ("development", "evaluation"):
            receipt_bytes = h.read_plain(base / phase / "receipt.json")
            self.assertEqual(h.R01_RECEIPT_SHA256[phase], h.digest(receipt_bytes))
            self.assertEqual(frozen, h.decode(receipt_bytes)["inputs"])
            self.assertTrue(h.verify(base / phase, input_revision="r01")["verified"])

    def test_archived_mode_rejects_rehashed_registration_tampering(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp).resolve() / "out"
            base = h.HERE.parents[1] / "artifacts/heat_institution_v01/development"
            shutil.copytree(base, out)
            path = out / "registration.json"
            record = h.decode(path.read_bytes())
            record["created_utc"] = "2000-01-01T00:00:00Z"
            path.write_bytes(h.encode(record))
            receipt_path = out / "receipt.json"
            receipt = h.decode(receipt_path.read_bytes())
            receipt["outputs"]["registration.json"] = h.digest(path.read_bytes())
            receipt_path.write_bytes(h.encode(receipt))
            with self.assertRaisesRegex(ValueError, "pinned r01 receipt"):
                h.verify(out, True, input_revision="r01")

    def test_archived_input_closure_is_exact(self):
        with tempfile.TemporaryDirectory() as tmp:
            inputs = Path(tmp).resolve() / "inputs"
            shutil.copytree(h.R01_INPUT_DIR, inputs)
            (inputs / "extra").write_text("unexpected", encoding="utf-8")
            with patch.object(h, "R01_INPUT_DIR", inputs):
                with self.assertRaisesRegex(ValueError, "archived input closure"):
                    h.verify(h.HERE.parents[1] / "artifacts/heat_institution_v01/development",
                             input_revision="r01")


if __name__ == "__main__":
    unittest.main()
