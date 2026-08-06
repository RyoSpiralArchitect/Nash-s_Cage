from __future__ import annotations

import dataclasses
import json
import tempfile
import unittest
from pathlib import Path

from simulation import rvcim_sim as sim


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "simulation" / "configs" / "minimal.json"


class ConfigTests(unittest.TestCase):
    def test_reference_config_is_valid(self) -> None:
        config = sim.load_config(CONFIG)
        self.assertEqual(config.schema_version, sim.SCHEMA_VERSION)
        self.assertGreaterEqual(config.horizon, 8)
        self.assertGreaterEqual(config.actors, 2)
        self.assertEqual(len(config.model_boundary_offsets), 3)

    def test_unknown_configuration_key_is_rejected(self) -> None:
        payload = json.loads(CONFIG.read_text(encoding="utf-8"))
        payload["silent_extra"] = 1
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(sim.ConfigError):
                sim.load_config(path)

    def test_override_is_recorded_in_resolved_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "run"
            sim.run_experiment(
                CONFIG,
                episodes=1,
                seed=3,
                out_dir=out,
                overwrite=True,
                overrides=("horizon=12", "actors=6"),
            )
            resolved = json.loads((out / "resolved_config.json").read_text())
            self.assertEqual(resolved["horizon"], 12)
            self.assertEqual(resolved["actors"], 6)


class MechanismTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = sim.load_config(CONFIG)

    def test_declared_defenses_increase_across_arms(self) -> None:
        arms = [sim.ARM_SPECS[key] for key in sim.DEFAULT_ARMS]
        for field in ("coupling", "audit", "anti_capture", "justice_buffer"):
            values = [getattr(arm, field) for arm in arms]
            self.assertEqual(values, sorted(values), field)
            self.assertEqual(len(values), len(set(values)), field)

    def test_negative_reserve_requests_emergency_mode(self) -> None:
        arm = sim.ARM_SPECS["robust_reserve"]
        selected = sim.select_mode(
            arm,
            observed_pressure=0.45,
            estimated_cr=-0.01,
            recoverability=0.50,
            boundary_uncertainty=0.10,
            config=self.config,
        )
        self.assertEqual(selected, 2)

    def test_full_rvcim_absorbs_more_capture_than_nominal(self) -> None:
        state = sim.WorldState(
            pressure=0.50,
            biosphere=0.70,
            institution=0.60,
            trust=0.60,
            justice=0.65,
            policy=0.55,
            support=0.45,
            audit=0.55,
        )
        attempted = 0.8
        nominal = sim.effective_capture_value(
            attempted, state, sim.ARM_SPECS["nominal_trigger"]
        )
        full = sim.effective_capture_value(
            attempted, state, sim.ARM_SPECS["full_rvcim"]
        )
        self.assertLess(full, nominal)

    def test_environment_sampling_is_deterministic(self) -> None:
        seed = sim.stable_seed(11, "environment", 2)
        left = sim.sample_environment(self.config, seed, episode=2)
        right = sim.sample_environment(self.config, seed, episode=2)
        self.assertEqual(left, right)


class ExperimentTests(unittest.TestCase):
    @staticmethod
    def _run(out: Path) -> tuple[list[sim.EpisodeResult], list[dict[str, object]], dict[str, object]]:
        return sim.run_experiment(
            CONFIG,
            episodes=3,
            seed=19,
            out_dir=out,
            overwrite=True,
            overrides=("horizon=12", "actors=6", "trace_episodes=1"),
        )

    def test_four_arms_share_each_episode_environment(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            results, _, _ = self._run(Path(tmp) / "run")
            self.assertEqual(len(results), 3 * len(sim.DEFAULT_ARMS))
            for episode in range(3):
                group = [row for row in results if row.episode == episode]
                self.assertEqual({row.arm for row in group}, set(sim.DEFAULT_ARMS))
                self.assertEqual(len({row.environment_seed for row in group}), 1)
                self.assertEqual(len({row.true_boundary for row in group}), 1)

    def test_repeated_runs_are_byte_reproducible(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            left = root / "left"
            right = root / "right"
            self._run(left)
            self._run(right)
            for name in (
                "summary.csv",
                "episodes.csv",
                "trace.csv",
                "comparison.md",
                "resolved_config.json",
            ):
                self.assertEqual((left / name).read_bytes(), (right / name).read_bytes(), name)

    def test_receipt_verifies_and_detects_tampering(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "run"
            _, _, receipt = self._run(out)
            receipt_path = out / "receipt.json"
            self.assertEqual(receipt["claim_level"], "F0")
            self.assertEqual(sim.verify_receipt(receipt_path), [])
            with (out / "episodes.csv").open("a", encoding="utf-8") as handle:
                handle.write("tamper\n")
            failures = sim.verify_receipt(receipt_path)
            self.assertTrue(any("episodes.csv" in failure for failure in failures))

    def test_result_rows_are_dataclass_serializable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            results, _, _ = self._run(Path(tmp) / "run")
            payload = dataclasses.asdict(results[0])
            self.assertEqual(payload["arm"], results[0].arm)
            self.assertIn("min_hidden_cr", payload)


if __name__ == "__main__":
    unittest.main()
