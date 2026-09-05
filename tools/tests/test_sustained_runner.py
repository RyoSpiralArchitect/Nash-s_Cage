"""Fixed-plan, cohort-separation, evidence-integrity and replay contracts."""

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

from tools import run_sustained as runner


class RunnerCase(unittest.TestCase):
    def setUp(self):
        self.config, self.plan = runner.load_inputs()

    def tiny(self):
        plan = copy.deepcopy(self.plan)
        plan["phases"] = {
            "development": {"master_seeds": [17], "episodes_per_seed": 1},
            "evaluation": {"master_seeds": [401], "episodes_per_seed": 1},
        }
        base = dataclasses.replace(self.config.base.base, horizon=8)
        feasibility_config = dataclasses.replace(self.config.base, base=base)
        config = dataclasses.replace(self.config, base=feasibility_config)
        return config, plan


class PlanTests(RunnerCase):
    def test_committed_plan_is_fixed_and_contains_both_cohorts(self):
        runner.validate_plan(self.plan)
        self.assertEqual(len(self.plan["scenarios"]), 10)
        self.assertEqual(len(self.plan["prior_failure_cases"]), 11)
        self.assertEqual(self.plan["controllers"], ["reserve", "sustained_reserve"])
        self.assertEqual(
            self.plan["phases"]["evaluation"]["master_seeds"], [401, 503, 607]
        )

    def test_unknown_or_missing_top_level_fields_are_rejected(self):
        for mutation in (
            lambda value: value.update(extra=True),
            lambda value: value.pop("registration_status"),
        ):
            plan = copy.deepcopy(self.plan)
            mutation(plan)
            with self.assertRaises(ValueError):
                runner.validate_plan(plan)

    def test_controller_order_counts_and_unique_phase_seeds_are_enforced(self):
        plan = copy.deepcopy(self.plan)
        plan["controllers"].reverse()
        with self.assertRaises(ValueError):
            runner.validate_plan(plan)
        for value in (True, 0, -1, 1.5):
            with self.subTest(value=value):
                plan = copy.deepcopy(self.plan)
                plan["phases"]["evaluation"]["episodes_per_seed"] = value
                with self.assertRaises(ValueError):
                    runner.validate_plan(plan)
        plan = copy.deepcopy(self.plan)
        plan["phases"]["evaluation"]["master_seeds"] = [17]
        with self.assertRaises(ValueError):
            runner.validate_plan(plan)

    def test_scenario_shape_override_names_and_values_are_strict(self):
        mutations = (
            lambda scenario: scenario.update(extra={}),
            lambda scenario: scenario["feasibility_overrides"].update(base=1),
            lambda scenario: scenario["sustained_overrides"].update(unknown=1),
            lambda scenario: scenario["environment_overrides"].update(unknown=1),
            lambda scenario: scenario["environment_overrides"].update(
                observation_bias_shift=math.nan
            ),
            lambda scenario: scenario["environment_overrides"].update(
                true_boundary_scale=0
            ),
        )
        for mutation in mutations:
            plan = copy.deepcopy(self.plan)
            mutation(plan["scenarios"][0])
            with self.subTest(plan=plan["scenarios"][0]):
                with self.assertRaises(ValueError):
                    runner.validate_plan(plan)

    def test_prior_failure_case_shape_comparator_reference_and_uniqueness_are_strict(self):
        mutations = (
            lambda case: case.update(extra=1),
            lambda case: case.update(comparator="reserve"),
            lambda case: case.update(scenario="absent"),
            lambda case: case.update(episode=True),
        )
        for mutation in mutations:
            plan = copy.deepcopy(self.plan)
            mutation(plan["prior_failure_cases"][0])
            with self.assertRaises(ValueError):
                runner.validate_plan(plan)
        plan = copy.deepcopy(self.plan)
        plan["prior_failure_cases"][1] = copy.deepcopy(plan["prior_failure_cases"][0])
        with self.assertRaises(ValueError):
            runner.validate_plan(plan)

    def test_invalid_feasibility_or_sustained_configuration_is_rejected_before_run(self):
        config, plan = self.tiny()
        plan["scenarios"][0]["feasibility_overrides"] = {"initial_budget": -1}
        with self.assertRaises(ValueError):
            runner.compute_data(config, plan, "evaluation")
        config, plan = self.tiny()
        plan["scenarios"][0]["sustained_overrides"] = {"forecast_steps": 0}
        with self.assertRaises(ValueError):
            runner.compute_data(config, plan, "evaluation")

    def test_frozen_v02_v03_and_fixture_identities_are_checked(self):
        plan = copy.deepcopy(self.plan)
        plan["v03_feasibility_receipt_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "frozen input identity"):
            runner._validate_frozen_identities(plan)

    def test_environment_transform_changes_only_declared_fields(self):
        environment = runner.legacy.sample_environment(self.config.base.base, 101, 0)
        changed = runner.transform_environment(
            environment,
            {
                "true_boundary_scale": 0.7,
                "model_boundary_shift": 0.12,
                "observation_bias_shift": -0.08,
            },
        )
        for field in dataclasses.fields(environment):
            if field.name not in {"true_boundary", "model_boundaries", "observation_bias"}:
                self.assertEqual(getattr(environment, field.name), getattr(changed, field.name))
        self.assertEqual(changed.true_boundary, environment.true_boundary * 0.7)


class SerializationAndComputationTests(RunnerCase):
    def test_numeric_export_is_canonical_and_nonfinite_is_rejected(self):
        values = {"a": 0.07619999999999999, "b": 0.0762, "missing": None, "zero": -0.0}
        self.assertEqual(
            json.loads(runner.json_bytes(values)),
            {"a": 0.0762, "b": 0.0762, "missing": None, "zero": 0.0},
        )
        self.assertEqual(
            runner.csv_bytes([values]), b"a,b,missing,zero\n0.0762,0.0762,,0.0\n"
        )
        for value in (math.nan, math.inf, -math.inf):
            with self.assertRaises(ValueError):
                runner.json_bytes({"value": value})
            with self.assertRaises(ValueError):
                runner.csv_bytes([{"value": value}])

    def test_tiny_run_is_deterministic_paired_and_keeps_cohorts_separate(self):
        config, plan = self.tiny()
        first = runner.compute_data(config, plan, "evaluation")
        self.assertEqual(first, runner.compute_data(config, plan, "evaluation"))
        self.assertEqual(set(first), runner.DATA_FILES)
        rows = list(csv.DictReader(io.StringIO(first["episodes.csv"].decode())))
        primary = [row for row in rows if row["cohort"] == runner.PRIMARY_COHORT]
        regression = [
            row for row in rows if row["cohort"] == runner.REGRESSION_COHORT
        ]
        self.assertEqual(len(primary), 10 * 2)
        self.assertEqual(len(regression), 11 * 4)
        for scenario in plan["scenarios"]:
            pair = [row for row in primary if row["scenario"] == scenario["id"]]
            self.assertEqual({row["controller"] for row in pair}, set(plan["controllers"]))
            self.assertEqual(len({row["environment_seed"] for row in pair}), 1)

        summary = json.loads(first["summary.json"])
        self.assertEqual(len(summary["groups"]), 10 * 2)
        self.assertEqual(len(summary["paired_comparisons"]), 10)
        self.assertEqual(len(summary["prior_failure_regression"]), 11)
        self.assertIn("no pooled universal winner", summary["statistical_scope"])
        self.assertIn(b"No pooled universal winner", first["comparison.md"])

    def test_v03_rows_have_explicit_missing_v04_metrics(self):
        config, plan = self.tiny()
        data = runner.compute_data(config, plan, "development")
        rows = list(csv.DictReader(io.StringIO(data["episodes.csv"].decode())))
        reserve = next(row for row in rows if row["controller"] == "reserve")
        sustained = next(
            row for row in rows if row["controller"] == "sustained_reserve"
        )
        for field in runner.V04_ONLY_METRICS:
            self.assertEqual(reserve[field], "")
        self.assertNotEqual(sustained["assessment_plan_found_steps"], "")
        summary = json.loads(data["summary.json"])
        reserve_group = next(
            row for row in summary["groups"] if row["controller"] == "reserve"
        )
        self.assertIsNone(reserve_group["assessment_plan_found_steps_mean"])
        self.assertIsNone(reserve_group["assessment_no_candidate_steps_mean"])

    def test_every_fixed_regression_case_has_all_four_controllers_and_relation_record(self):
        config, plan = self.tiny()
        summary = json.loads(runner.compute_data(config, plan, "development")["summary.json"])
        expected = {
            (case["scenario"], case["master_seed"], case["episode"], case["comparator"])
            for case in plan["prior_failure_cases"]
        }
        actual = {
            (case["scenario"], case["master_seed"], case["episode"], case["comparator"])
            for case in summary["prior_failure_regression"]
        }
        self.assertEqual(actual, expected)
        for case in summary["prior_failure_regression"]:
            self.assertEqual(
                set(case["results"]),
                {"threshold", "threshold_hysteresis", "reserve", "sustained_reserve"},
            )
            self.assertIsInstance(case["original_relation_preserved"], bool)
            self.assertEqual(case["sustained_success"], not case["sustained_failure"])

    def test_trace_is_primary_sustained_only(self):
        config, plan = self.tiny()
        data = runner.compute_data(config, plan, "development")
        rows = list(csv.DictReader(io.StringIO(data["trace.csv"].decode())))
        self.assertTrue(rows)
        self.assertEqual({row["cohort"] for row in rows}, {runner.PRIMARY_COHORT})
        self.assertEqual({row["controller"] for row in rows}, {"sustained_reserve"})


class BundleTests(RunnerCase):
    def setUp(self):
        super().setUp()
        self.temp = tempfile.TemporaryDirectory(prefix="sustained-contract-")
        self.addCleanup(self.temp.cleanup)
        self.parent = Path(self.temp.name)
        config, plan = self.tiny()
        self.inputs = patch.object(runner, "load_inputs", return_value=(config, plan))
        self.inputs.start()
        self.addCleanup(self.inputs.stop)
        self.bundle = runner.build_bundle("evaluation")

    def publish(self, name="new-run"):
        output = self.parent / name
        runner.publish_new(output, self.bundle)
        return output

    def test_receipt_and_replay_accept_unchanged_bundle(self):
        output = self.publish()
        self.assertEqual(runner.verify_bundle(output), [])
        self.assertEqual(runner.verify_bundle(output, replay=True), [])

    def test_existing_output_is_never_overwritten(self):
        output = self.parent / "existing"
        output.mkdir()
        with self.assertRaises(FileExistsError):
            runner.publish_new(output, self.bundle)
        marker = output / "keep.txt"
        marker.write_bytes(b"user content")
        with self.assertRaises(FileExistsError):
            runner.publish_new(output, self.bundle)
        self.assertEqual(marker.read_bytes(), b"user content")

    def test_incomplete_bundle_is_rejected_before_directory_creation(self):
        output = self.parent / "invalid"
        with self.assertRaises(ValueError):
            runner.publish_new(output, {"receipt.json": b"{}"})
        self.assertFalse(output.exists())

    def test_missing_extra_tampered_and_symlink_outputs_are_rejected(self):
        output = self.publish()
        target = output / "summary.json"
        target.write_bytes(b"{}\n")
        self.assertTrue(runner.verify_bundle(output))
        target.unlink()
        self.assertTrue(runner.verify_bundle(output))
        target.write_bytes(self.bundle["summary.json"])
        extra = output / "extra.txt"
        extra.write_bytes(b"extra")
        self.assertTrue(runner.verify_bundle(output))
        extra.unlink()
        target.unlink()
        try:
            target.symlink_to(output / "resolved_plan.json")
        except OSError as exc:
            self.skipTest(f"symlink creation unavailable: {exc}")
        self.assertTrue(runner.verify_bundle(output))

    def test_symlink_output_directory_is_rejected_for_run_and_verify(self):
        output = self.publish()
        alias = self.parent / "alias"
        try:
            alias.symlink_to(output, target_is_directory=True)
        except OSError as exc:
            self.skipTest(f"symlink creation unavailable: {exc}")
        with self.assertRaises(FileExistsError):
            runner.publish_new(alias, self.bundle)
        self.assertTrue(runner.verify_bundle(alias))

    def test_receipt_cannot_upgrade_claim_or_omit_input_identity(self):
        output = self.publish()
        receipt = json.loads(self.bundle["receipt.json"])
        receipt["claim_level"] = "F1"
        (output / "receipt.json").write_bytes(runner.json_bytes(receipt))
        self.assertTrue(runner.verify_bundle(output))

        output = self.publish("second")
        receipt = json.loads(self.bundle["receipt.json"])
        receipt["input_sha256"].pop(runner.PLAN_PATH)
        (output / "receipt.json").write_bytes(runner.json_bytes(receipt))
        self.assertTrue(runner.verify_bundle(output))

    def test_rehashed_fabrication_fails_deterministic_replay(self):
        output = self.publish()
        payload = b'{"invented": true}\n'
        (output / "summary.json").write_bytes(payload)
        receipt = json.loads(self.bundle["receipt.json"])
        receipt["output_sha256"]["summary.json"] = runner.digest(payload)
        (output / "receipt.json").write_bytes(runner.json_bytes(receipt))
        self.assertEqual(runner.verify_bundle(output), [])
        self.assertTrue(runner.verify_bundle(output, replay=True))

    def test_input_change_during_computation_is_refused(self):
        before = runner.source_hashes()
        changed = {**before, runner.PLAN_PATH: "0" * 64}
        with patch.object(runner, "source_hashes", side_effect=[before, changed]):
            with self.assertRaisesRegex(ValueError, "inputs changed"):
                runner.build_bundle("evaluation")

    def test_loaded_code_identity_must_match_disk(self):
        with patch.dict(
            runner.LOADED_SOURCE_HASHES, {"simulation/sustained.py": "0" * 64}
        ):
            with self.assertRaisesRegex(ValueError, "loaded Python"):
                runner.source_hashes()

    def test_input_symlink_component_is_rejected(self):
        try:
            (self.parent / "simulation").symlink_to(
                runner.ROOT / "simulation", target_is_directory=True
            )
        except OSError as exc:
            self.skipTest(f"symlink creation unavailable: {exc}")
        with patch.object(runner, "ROOT", self.parent):
            with self.assertRaisesRegex(ValueError, "input symlink"):
                runner.source_hashes()


if __name__ == "__main__":
    unittest.main()
