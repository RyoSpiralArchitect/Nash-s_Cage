"""Fixed-plan, non-overwrite, evidence-integrity and deterministic replay contracts."""

from __future__ import annotations

import copy
import csv
import dataclasses
import io
import json
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools import run_feasibility as runner


class RunnerCase(unittest.TestCase):
    def setUp(self):
        self.config, self.plan = runner.load_inputs()

    def tiny(self):
        plan = copy.deepcopy(self.plan)
        plan["scenarios"] = plan["scenarios"][:1]
        plan["phases"] = {
            "development": {"master_seeds": [7], "episodes_per_seed": 1},
            "evaluation": {"master_seeds": [101], "episodes_per_seed": 1},
        }
        config = dataclasses.replace(self.config, base=dataclasses.replace(self.config.base, horizon=8))
        return config, plan


class PlanTests(RunnerCase):
    def test_committed_plan_valid_and_contains_all_stresses(self):
        runner.validate_plan(self.plan)
        self.assertEqual(len(self.plan["scenarios"]), 9)
        self.assertEqual(self.plan["phases"]["evaluation"]["master_seeds"], [101, 211, 307])

    def test_unknown_or_missing_plan_keys_rejected(self):
        for mutation in (lambda p: p.update(extra=1), lambda p: p.pop("registration_status")):
            plan = copy.deepcopy(self.plan)
            mutation(plan)
            with self.assertRaises(ValueError):
                runner.validate_plan(plan)

    def test_missing_controller_or_duplicate_seed_rejected(self):
        plan = copy.deepcopy(self.plan)
        plan["controllers"].pop()
        with self.assertRaises(ValueError):
            runner.validate_plan(plan)
        plan = copy.deepcopy(self.plan)
        plan["phases"]["evaluation"]["master_seeds"] = [7]
        with self.assertRaises(ValueError):
            runner.validate_plan(plan)

    def test_counts_reject_bool_zero_negative_and_fraction(self):
        for value in (True, 0, -1, 1.5):
            with self.subTest(value=value):
                plan = copy.deepcopy(self.plan)
                plan["phases"]["evaluation"]["episodes_per_seed"] = value
                with self.assertRaises(ValueError):
                    runner.validate_plan(plan)

    def test_scenario_override_names_and_environment_values_checked(self):
        for key, value in (("unlisted", 1), ("true_boundary_scale", 0),
                           ("observation_bias_shift", math.nan), ("model_boundary_shift", True)):
            plan = copy.deepcopy(self.plan)
            plan["scenarios"][0]["environment_overrides"] = {key: value}
            with self.assertRaises(ValueError):
                runner.validate_plan(plan)
        plan = copy.deepcopy(self.plan)
        plan["scenarios"][0]["config_overrides"] = {"base": {}}
        with self.assertRaises(ValueError):
            runner.validate_plan(plan)

    def test_invalid_scenario_config_rejected_before_running(self):
        config, plan = self.tiny()
        plan["scenarios"][0]["config_overrides"] = {"initial_budget": -1}
        with self.assertRaises(ValueError):
            runner.compute_data(config, plan, "evaluation")

    def test_environment_transform_preserves_every_undeclared_draw(self):
        env = runner.legacy.sample_environment(self.config.base, 101, 0)
        changed = runner.transform_environment(env, {"true_boundary_scale": .7, "model_boundary_shift": .12})
        for field in dataclasses.fields(env):
            if field.name not in {"true_boundary", "model_boundaries"}:
                self.assertEqual(getattr(env, field.name), getattr(changed, field.name))
        self.assertEqual(changed.true_boundary, env.true_boundary * .7)


class SerializationTests(RunnerCase):
    def test_declared_numeric_encoding_removes_runtime_last_bit_variation(self):
        values = {"a": 0.07619999999999999, "b": 0.0762, "missing": None, "zero": -0.0}
        exported = json.loads(runner.json_bytes(values))
        self.assertEqual(exported, {"a": .0762, "b": .0762, "missing": None, "zero": 0.0})
        self.assertEqual(runner.csv_bytes([values]), b"a,b,missing,zero\n0.0762,0.0762,,0.0\n")
        self.assertEqual(runner.canonical_numbers(1.1234567894), 1.123456789)
        self.assertEqual(values["a"], 0.07619999999999999)  # never change calculations

    def test_csv_is_stable_lf_and_preserves_unknown_as_empty(self):
        result = runner.csv_bytes([{"z": None, "a": 1}])
        self.assertEqual(result, b"a,z\n1,\n")

    def test_csv_and_json_reject_nonfinite_numbers(self):
        for value in (math.nan, math.inf, -math.inf):
            with self.assertRaises(ValueError):
                runner.csv_bytes([{"value": value}])
            with self.assertRaises(ValueError):
                runner.json_bytes({"value": value})
        with self.assertRaises(ValueError):
            runner.csv_bytes([{"a": 1}, {"b": 2}])

    def test_tiny_experiment_replays_identically_and_pairs_all_controllers(self):
        config, plan = self.tiny()
        first = runner.compute_data(config, plan, "evaluation")
        self.assertEqual(first, runner.compute_data(config, plan, "evaluation"))
        self.assertEqual(set(first), runner.DATA_FILES)
        rows = list(csv.DictReader(io.StringIO(first["episodes.csv"].decode())))
        self.assertEqual(len(rows), 3)
        self.assertEqual(len({r["environment_seed"] for r in rows}), 1)
        self.assertEqual({r["controller"] for r in rows}, set(plan["controllers"]))
        summary = json.loads(first["summary.json"])
        self.assertEqual(summary["claim_level"], "F0")
        for pair in summary["paired_comparisons"]:
            self.assertEqual(pair["pairs"], 1)
            self.assertEqual(sum(pair[k] for k in (
                "reserve_only_success", "baseline_only_success", "both_success", "both_failure")), 1)


class BundleTests(RunnerCase):
    def setUp(self):
        super().setUp()
        self.temp = tempfile.TemporaryDirectory(prefix="feasibility-contract-")
        self.addCleanup(self.temp.cleanup)
        self.parent = Path(self.temp.name)
        config, plan = self.tiny()
        self.inputs = patch.object(runner, "load_inputs", return_value=(config, plan))
        self.inputs.start()
        self.addCleanup(self.inputs.stop)
        self.bundle = runner.build_bundle("evaluation")

    def publish(self):
        output = self.parent / "new-run"
        runner.publish_new(output, self.bundle)
        return output

    def test_receipt_and_replay_accept_unchanged_bundle(self):
        output = self.publish()
        self.assertEqual(runner.verify_bundle(output), [])
        self.assertEqual(runner.verify_bundle(output, replay=True), [])

    def test_existing_directory_is_never_overwritten_even_when_empty(self):
        output = self.parent / "existing"
        output.mkdir()
        with self.assertRaises(FileExistsError):
            runner.publish_new(output, self.bundle)
        marker = output / "keep.txt"
        marker.write_bytes(b"user content")
        with self.assertRaises(FileExistsError):
            runner.publish_new(output, self.bundle)
        self.assertEqual(marker.read_bytes(), b"user content")

    def test_incomplete_bundle_rejected_before_creating_directory(self):
        output = self.parent / "invalid"
        with self.assertRaises(ValueError):
            runner.publish_new(output, {"receipt.json": b"{}"})
        self.assertFalse(output.exists())

    def test_missing_extra_or_tampered_output_rejected(self):
        output = self.publish()
        target = output / "summary.json"
        target.write_bytes(b"{}\n")
        self.assertTrue(runner.verify_bundle(output))
        target.unlink()
        self.assertTrue(runner.verify_bundle(output))
        target.write_bytes(self.bundle["summary.json"])
        (output / "unlisted.txt").write_bytes(b"extra")
        self.assertTrue(runner.verify_bundle(output))

    def test_symlink_directory_or_file_rejected(self):
        output = self.publish()
        alias = self.parent / "alias"
        try:
            alias.symlink_to(output, target_is_directory=True)
        except OSError as exc:
            self.skipTest(f"symlink creation unavailable: {exc}")
        self.assertTrue(runner.verify_bundle(alias))
        with self.assertRaises(FileExistsError):
            runner.publish_new(alias, self.bundle)
        target = output / "summary.json"
        target.unlink()
        target.symlink_to(output / "resolved_plan.json")
        self.assertTrue(runner.verify_bundle(output))

    def test_receipt_cannot_upgrade_claim_or_omit_input_hash(self):
        output = self.publish()
        for change in (lambda r: r.update(claim_level="F1"), lambda r: r["input_sha256"].pop(runner.PLAN_PATH)):
            receipt = json.loads(self.bundle["receipt.json"])
            change(receipt)
            (output / "receipt.json").write_bytes(runner.json_bytes(receipt))
            self.assertTrue(runner.verify_bundle(output))

    def test_rehashing_fabricated_result_is_not_replay_evidence(self):
        output = self.publish()
        payload = b'{"invented": true}\n'
        (output / "summary.json").write_bytes(payload)
        receipt = json.loads(self.bundle["receipt.json"])
        receipt["output_sha256"]["summary.json"] = runner.digest(payload)
        (output / "receipt.json").write_bytes(runner.json_bytes(receipt))
        self.assertEqual(runner.verify_bundle(output), [])  # consistency, not authenticity
        self.assertTrue(runner.verify_bundle(output, replay=True))

    def test_input_change_during_computation_refused(self):
        before = runner.source_hashes()
        changed = {**before, runner.PLAN_PATH: "0" * 64}
        with patch.object(runner, "source_hashes", side_effect=[before, changed]):
            with self.assertRaisesRegex(ValueError, "inputs changed"):
                runner.build_bundle("evaluation")

    def test_loaded_code_identity_must_match_disk(self):
        with patch.dict(runner.LOADED_SOURCE_HASHES, {"simulation/feasibility.py": "0" * 64}):
            with self.assertRaisesRegex(ValueError, "loaded Python"):
                runner.source_hashes()

    def test_input_symlink_component_is_rejected(self):
        try:
            (self.parent / "simulation").symlink_to(runner.ROOT / "simulation", target_is_directory=True)
        except OSError as exc:
            self.skipTest(f"symlink creation unavailable: {exc}")
        with patch.object(runner, "ROOT", self.parent):
            with self.assertRaisesRegex(ValueError, "input symlink"):
                runner.source_hashes()


if __name__ == "__main__":
    unittest.main()
