"""Adversarial contracts for the separate, experimental F0 model.

These tests check information and resource boundaries.  They do not require a
particular trigger to outperform another, or establish real-world feasibility.
Run explicitly with ``python -m unittest simulation.tests.test_feasibility``.
"""

from __future__ import annotations

import dataclasses
import inspect
import json
import math
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from simulation import feasibility as sim
from simulation import rvcim_sim as legacy


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "simulation" / "configs" / "feasibility_v03.json"


class FeasibilityCase(unittest.TestCase):
    def setUp(self) -> None:
        self.config = sim.load_config(CONFIG)

    def observation(self, step: int = 0, **changes: object) -> sim.Observation:
        fields = {
            "step": step,
            "observed_at_step": step,
            "observed_pressure": 0.10,
            "model_boundaries": (0.88, 1.00, 1.12),
            "institution": 0.80,
            "trust": 0.80,
            "justice": 0.80,
            "remaining_budget": self.config.initial_budget,
            "active_mode": 0,
            "pending_mode": None,
            "effective_policy": 0.0,
            "effective_support": 0.0,
            "effective_audit": 0.0,
        }
        fields.update(changes)
        return sim.Observation(**fields)

    def environment(self, config: sim.FeasibilityConfig | None = None) -> legacy.Environment:
        config = config or self.config
        return legacy.sample_environment(
            config.base, legacy.stable_seed(7, "environment", 3), episode=3
        )


class ConfigTests(FeasibilityCase):
    def test_experimental_config_is_separate_from_the_legacy_config(self) -> None:
        self.config.validate()
        self.assertIsInstance(self.config.base, legacy.ModelConfig)
        self.assertNotEqual(sim.VERSION, legacy.VERSION)
        self.assertEqual(legacy.VERSION, "0.2.0")

    def test_unknown_configuration_key_is_rejected(self) -> None:
        payload = json.loads(CONFIG.read_text(encoding="utf-8"))
        payload["silent_extra"] = 1
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "invalid.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(legacy.ConfigError):
                sim.load_config(path)

    def test_negative_delays_costs_resources_and_slew_are_rejected(self) -> None:
        for name in (
            "actuation_delay_steps", "physical_effect_delay_steps",
            "policy_cost", "support_cost", "audit_cost", "initial_budget",
            "policy_capacity", "support_capacity", "audit_capacity",
            "max_policy_slew", "max_support_slew", "max_audit_slew",
            "max_observation_age_steps", "observation_missing_every",
        ):
            with self.subTest(field=name):
                with self.assertRaises(legacy.ConfigError):
                    dataclasses.replace(self.config, **{name: -1}).validate()

    def test_nonfinite_configuration_values_are_rejected(self) -> None:
        for name in (
            "policy_cost", "support_cost", "audit_cost", "initial_budget",
            "policy_capacity", "support_capacity", "audit_capacity",
            "max_policy_slew", "max_support_slew", "max_audit_slew",
            "uncertainty_limit", "release_margin",
        ):
            for value in (math.nan, math.inf, -math.inf):
                with self.subTest(field=name, value=value):
                    with self.assertRaises(legacy.ConfigError):
                        dataclasses.replace(self.config, **{name: value}).validate()

    def test_noninteger_or_boolean_step_configuration_is_rejected(self) -> None:
        for name in (
            "actuation_delay_steps", "physical_effect_delay_steps",
            "release_consecutive_steps", "max_observation_age_steps",
            "observation_missing_every",
        ):
            for value in (0.5, True, math.nan):
                with self.subTest(field=name, value=value):
                    with self.assertRaises(legacy.ConfigError):
                        dataclasses.replace(self.config, **{name: value}).validate()

    def test_release_requires_at_least_one_valid_observation(self) -> None:
        with self.assertRaises(legacy.ConfigError):
            dataclasses.replace(self.config, release_consecutive_steps=0).validate()


class InformationBoundaryTests(FeasibilityCase):
    def test_controller_api_has_only_explicit_public_inputs(self) -> None:
        self.assertEqual(
            tuple(inspect.signature(sim.decide).parameters),
            ("observation", "controller_state", "config", "trigger"),
        )
        forbidden = {
            "environment", "world", "world_state", "true_boundary", "hidden_cr",
            "hidden_trend", "irreversible", "truth_mode", "false_positive",
            "false_negative",
        }
        for record in (sim.Observation, sim.ControllerState):
            with self.subTest(record=record.__name__):
                self.assertFalse(forbidden & {field.name for field in dataclasses.fields(record)})

    def test_identical_public_history_produces_identical_decisions(self) -> None:
        history = [
            self.observation(step=step, observed_pressure=pressure)
            for step, pressure in enumerate((0.10, 0.68, 0.81, 0.60, 0.15, 0.15, 0.15))
        ]
        for trigger in ("threshold", "threshold_hysteresis", "reserve"):
            left = sim.ControllerState()
            right = sim.ControllerState()
            for observation in history:
                with self.subTest(trigger=trigger, step=observation.step):
                    left_decision, left = sim.decide(observation, left, self.config, trigger)
                    right_decision, right = sim.decide(
                        dataclasses.replace(observation), right, self.config, trigger
                    )
                    self.assertEqual(left_decision, right_decision)
                    self.assertEqual(left, right)

    def test_controller_never_calls_legacy_truth_evaluators(self) -> None:
        with mock.patch.object(legacy, "hidden_reserve", side_effect=AssertionError("truth leak")):
            with mock.patch.object(legacy, "truth_mode", side_effect=AssertionError("truth leak")):
                for trigger in ("threshold", "threshold_hysteresis", "reserve"):
                    sim.decide(self.observation(), sim.ControllerState(), self.config, trigger)

    def test_mode_label_without_delivery_cannot_change_actor_or_social_outputs(self) -> None:
        environment = self.environment()
        normal = self.observation(active_mode=0)
        announced = dataclasses.replace(normal, active_mode=2)
        normal_actions = sim.public_actor_actions(
            normal, environment.actors, environment.choice_draws[0], self.config
        )
        announced_actions = sim.public_actor_actions(
            announced, environment.actors, environment.choice_draws[0], self.config
        )
        self.assertEqual(normal_actions, announced_actions)
        normal_social = sim.public_social_update(
            normal, normal_actions, 0.10, self.config, environment.social_noise[0]
        )
        announced_social = sim.public_social_update(
            announced, announced_actions, 0.10, self.config, environment.social_noise[0]
        )
        self.assertEqual(normal_social, announced_social)


class EvidenceAndReleaseTests(FeasibilityCase):
    def test_missing_nonfinite_and_stale_evidence_cannot_escalate(self) -> None:
        failures = [
            {"observed_pressure": None},
            {"observed_pressure": math.nan},
            {"observed_pressure": math.inf},
            {"model_boundaries": ()},
            {"model_boundaries": (0.88, math.nan, 1.12)},
            {"observed_at_step": None},
            {"observed_at_step": 10 - self.config.max_observation_age_steps - 1},
            {"observed_at_step": 11},
            {"institution": None},
            {"trust": math.nan},
            {"justice": None},
            {"remaining_budget": None},
            {"remaining_budget": math.nan},
            {"active_mode": None},
            {"effective_policy": None},
            {"effective_support": math.nan},
            {"effective_audit": None},
        ]
        for trigger in ("threshold", "threshold_hysteresis", "reserve"):
            for changes in failures:
                with self.subTest(trigger=trigger, changes=changes):
                    decision, updated = sim.decide(
                        self.observation(10, observed_pressure=0.95, **changes)
                        if "observed_pressure" not in changes
                        else self.observation(10, **changes),
                        sim.ControllerState(), self.config, trigger,
                    )
                    self.assertEqual(decision.evidence_status, "insufficient_evidence")
                    self.assertEqual(decision.requested_mode, 0)
                    self.assertEqual(updated.authorized_mode, 0)
                    self.assertEqual(updated.release_streak, 0)

    def test_observation_at_maximum_age_is_still_usable(self) -> None:
        decision, _ = sim.decide(
            self.observation(
                step=10, observed_at_step=10 - self.config.max_observation_age_steps,
                observed_pressure=0.95,
            ), sim.ControllerState(), self.config, "threshold",
        )
        self.assertNotEqual(decision.evidence_status, "insufficient_evidence")
        self.assertGreater(decision.requested_mode, 0)

    def test_reserve_release_occurs_on_exact_configured_consecutive_observation(self) -> None:
        config = dataclasses.replace(self.config, uncertainty_limit=0.30, release_consecutive_steps=3)
        state = sim.ControllerState(authorized_mode=2)
        for step in range(config.release_consecutive_steps):
            decision, state = sim.decide(
                self.observation(step, active_mode=2), state, config, "reserve"
            )
            self.assertNotEqual(decision.evidence_status, "insufficient_evidence")
            self.assertIsNotNone(decision.estimated_cr)
            self.assertGreater(decision.estimated_cr, config.release_margin)
            if step < config.release_consecutive_steps - 1:
                self.assertGreater(decision.requested_mode, 0)
            else:
                self.assertEqual(decision.requested_mode, 0)

    def test_missing_evidence_resets_release_streak(self) -> None:
        config = dataclasses.replace(self.config, release_consecutive_steps=3)
        state = sim.ControllerState(authorized_mode=2)
        for step in range(2):
            _, state = sim.decide(self.observation(step, active_mode=2), state, config, "reserve")
        decision, state = sim.decide(
            self.observation(2, active_mode=2, observed_pressure=None), state, config, "reserve"
        )
        self.assertEqual(decision.evidence_status, "insufficient_evidence")
        self.assertEqual(state.release_streak, 0)
        for step in range(3, 6):
            decision, state = sim.decide(self.observation(step, active_mode=2), state, config, "reserve")
            self.assertEqual(decision.requested_mode == 0, step == 5)

    def test_replaying_a_still_fresh_sample_cannot_advance_release(self) -> None:
        config = dataclasses.replace(
            self.config, max_observation_age_steps=10, release_consecutive_steps=3
        )
        for trigger in ("threshold_hysteresis", "reserve"):
            state = sim.ControllerState(authorized_mode=2)
            decision, state = sim.decide(self.observation(0, active_mode=2), state, config, trigger)
            self.assertGreater(decision.requested_mode, 0)
            streak_after_first_sample = state.release_streak
            for step in range(1, 6):
                with self.subTest(trigger=trigger, repeated_at_step=step):
                    decision, state = sim.decide(
                        self.observation(step, observed_at_step=0, active_mode=2),
                        state, config, trigger,
                    )
                    self.assertGreater(decision.requested_mode, 0)
                    self.assertLessEqual(state.release_streak, streak_after_first_sample)
            for step in range(6, 6 + config.release_consecutive_steps):
                decision, state = sim.decide(
                    self.observation(step, active_mode=2), state, config, trigger
                )
            self.assertEqual(decision.requested_mode, 0)

    def test_uncertainty_stress_is_visible_as_perpetual_precaution(self) -> None:
        config = dataclasses.replace(self.config, uncertainty_limit=0.18)
        state = sim.ControllerState()
        for step in range(12):
            decision, state = sim.decide(self.observation(step), state, config, "reserve")
            self.assertNotEqual(decision.evidence_status, "insufficient_evidence")
            self.assertEqual(decision.requested_mode, 1)
            self.assertEqual(decision.reason, "model_disagreement")
            self.assertGreaterEqual(decision.boundary_uncertainty, config.uncertainty_limit)
            self.assertEqual(state.release_streak, 0)


    def test_plain_threshold_can_release_without_a_reserve_certificate(self) -> None:
        config = dataclasses.replace(self.config, release_margin=1000000.0, uncertainty_limit=0.001)
        decision, state = sim.decide(
            self.observation(observed_pressure=0.10, active_mode=2),
            sim.ControllerState(authorized_mode=2), config, "threshold",
        )
        self.assertEqual(decision.requested_mode, 0)
        self.assertEqual(state.authorized_mode, 0)

    def test_threshold_hysteresis_uses_pressure_margin_not_reserve_release(self) -> None:
        config = dataclasses.replace(self.config, release_margin=1000000.0, release_consecutive_steps=3)
        release_level = config.base.nominal_trigger_level - config.threshold_release_margin
        state = sim.ControllerState(authorized_mode=1)
        for step in range(3):
            decision, state = sim.decide(
                self.observation(step, observed_pressure=release_level - 0.01, active_mode=1),
                state, config, "threshold_hysteresis",
            )
            self.assertEqual(decision.requested_mode == 0, step == 2)

    def test_threshold_hysteresis_does_not_release_inside_its_pressure_deadband(self) -> None:
        config = self.config
        state = sim.ControllerState(authorized_mode=1)
        pressure = config.base.nominal_trigger_level - config.threshold_release_margin / 2
        for step in range(config.release_consecutive_steps + 2):
            decision, state = sim.decide(
                self.observation(step, observed_pressure=pressure, active_mode=1),
                state, config, "threshold_hysteresis",
            )
            self.assertEqual(decision.requested_mode, 1)

    def hysteresis_sequence(self, pressures: tuple[float, ...]) -> list[tuple[sim.Decision, sim.ControllerState]]:
        config = dataclasses.replace(self.config, release_consecutive_steps=3)
        state = sim.ControllerState(authorized_mode=2)
        records = []
        for step, pressure in enumerate(pressures):
            decision, state = sim.decide(
                self.observation(step, observed_pressure=pressure, active_mode=state.authorized_mode),
                state, config, "threshold_hysteresis",
            )
            records.append((decision, state))
        return records

    def test_hysteresis_emergency_releases_to_precaution_on_third_qualified_sample(self) -> None:
        records = self.hysteresis_sequence((0.70, 0.70, 0.70))
        self.assertEqual([decision.requested_mode for decision, _ in records], [2, 2, 1])

    def test_hysteresis_normal_deadband_does_not_trap_authorized_emergency(self) -> None:
        records = self.hysteresis_sequence((0.65, 0.65, 0.65, 0.65, 0.65))
        self.assertEqual([decision.requested_mode for decision, _ in records], [2, 2, 1, 1, 1])

    def test_hysteresis_cannot_borrow_precaution_evidence_for_normal_release(self) -> None:
        records = self.hysteresis_sequence((0.70, 0.70, 0.62))
        self.assertEqual([decision.requested_mode for decision, _ in records], [2, 2, 1])
        self.assertEqual(records[-1][1].normal_release_streak, 1)

    def test_hysteresis_preserves_normal_evidence_across_precaution_release(self) -> None:
        records = self.hysteresis_sequence((0.70, 0.70, 0.62, 0.62, 0.62))
        self.assertEqual([decision.requested_mode for decision, _ in records], [2, 2, 1, 1, 0])

    def test_hysteresis_can_release_directly_to_normal_after_three_normal_samples(self) -> None:
        records = self.hysteresis_sequence((0.62, 0.62, 0.62))
        self.assertEqual([decision.requested_mode for decision, _ in records], [2, 2, 0])

    def test_hysteresis_missing_or_replayed_evidence_resets_both_target_counters(self) -> None:
        config = dataclasses.replace(self.config, release_consecutive_steps=3)
        for invalid in (
            {"observed_pressure": None},
            {"observed_at_step": 1},
        ):
            with self.subTest(invalid=invalid):
                state = self.hysteresis_sequence((0.62, 0.62))[-1][1]
                self.assertEqual(state.normal_release_streak, 2)
                self.assertEqual(state.precaution_release_streak, 2)
                invalid_record = dataclasses.replace(
                    self.observation(2, observed_pressure=0.62, active_mode=2), **invalid
                )
                decision, state = sim.decide(invalid_record, state, config, "threshold_hysteresis")
                self.assertEqual(decision.evidence_status, "insufficient_evidence")
                self.assertEqual(decision.requested_mode, 2)
                self.assertEqual(state.normal_release_streak, 0)
                self.assertEqual(state.precaution_release_streak, 0)
                after_reset = []
                for step in range(3, 6):
                    decision, state = sim.decide(
                        self.observation(step, observed_pressure=0.62, active_mode=state.authorized_mode),
                        state, config, "threshold_hysteresis",
                    )
                    after_reset.append(decision.requested_mode)
                self.assertEqual(after_reset, [2, 2, 0])

    def test_unattainable_response_is_unknown_not_a_positive_reserve(self) -> None:
        for changes, status in (
            ({"policy_capacity": 0.0}, "insufficient_capacity"),
            ({"max_policy_slew": 0.0}, "insufficient_slew"),
            ({"initial_budget": 0.0}, "insufficient_budget"),
        ):
            with self.subTest(changes=changes):
                config = dataclasses.replace(self.config, **changes)
                decision, _ = sim.decide(
                    self.observation(remaining_budget=config.initial_budget),
                    sim.ControllerState(), config, "reserve",
                )
                self.assertEqual(decision.evidence_status, "sufficient_evidence")
                self.assertEqual(decision.response_status, status)
                self.assertIsNone(decision.estimated_cr)


class ActuationAndBudgetTests(FeasibilityCase):
    CHANNELS = ("policy", "support", "audit")

    def ready_config(self, **changes: object) -> sim.FeasibilityConfig:
        fields = {
            "actuation_delay_steps": 0,
            "physical_effect_delay_steps": 0,
            "initial_budget": 1000.0,
        }
        fields.update(changes)
        return dataclasses.replace(self.config, **fields)

    def test_actuation_delay_has_an_exact_boundary(self) -> None:
        config = self.ready_config(actuation_delay_steps=3)
        state = sim.request_mode(sim.ActuatorState(), 2, 5, config)
        self.assertEqual(state.active_mode, 0)
        self.assertEqual(state.transitions[0].requested_at_step, 5)
        self.assertEqual(state.transitions[0].due_step, 8)
        for step in range(5, 9):
            state, _ = sim.advance_actuators(state, step, config, config.initial_budget)
            self.assertEqual(state.active_mode, 0 if step < 8 else 2)

    def test_zero_actuation_delay_activates_on_the_request_tick(self) -> None:
        config = self.ready_config()
        state = sim.request_mode(sim.ActuatorState(), 2, 5, config)
        state, _ = sim.advance_actuators(state, 5, config, config.initial_budget)
        self.assertEqual(state.active_mode, 2)

    def test_repeated_unchanged_requests_do_not_reset_the_due_step(self) -> None:
        config = self.ready_config(actuation_delay_steps=3)
        state = sim.request_mode(sim.ActuatorState(), 2, 0, config)
        for step in range(4):
            previous = state
            state = sim.request_mode(state, 2, step, config)
            self.assertEqual(state, previous)
            self.assertLessEqual(len(state.transitions), 1)
            state, _ = sim.advance_actuators(state, step, config, config.initial_budget)
        self.assertEqual(state.active_mode, 2)
        self.assertFalse(state.transitions)

    def test_effect_delay_has_an_exact_boundary_and_does_not_charge_pending_targets(self) -> None:
        config = self.ready_config(physical_effect_delay_steps=3)
        state = sim.request_mode(sim.ActuatorState(), 2, 5, config)
        for step in range(5, 9):
            state, cost = sim.advance_actuators(state, step, config, config.initial_budget)
            self.assertEqual(state.active_mode, 2)
            self.assertGreater(state.command_policy, 0.0)
            if step < 8:
                self.assertEqual(state.effective_policy, 0.0)
                self.assertEqual(state.effective_support, 0.0)
                self.assertEqual(state.effective_audit, 0.0)
                self.assertEqual(cost.step_cost, 0.0)
                self.assertEqual(cost.remaining_budget, config.initial_budget)
            else:
                self.assertEqual(state.effective_mode, 2)
                self.assertGreater(state.effective_policy, 0.0)
                self.assertGreater(cost.step_cost, 0.0)

    def test_actuation_and_physical_delay_are_additive(self) -> None:
        config = self.ready_config(actuation_delay_steps=2, physical_effect_delay_steps=3)
        state = sim.request_mode(sim.ActuatorState(), 2, 0, config)
        for step in range(6):
            state, _ = sim.advance_actuators(state, step, config, config.initial_budget)
            self.assertEqual(state.active_mode, 0 if step < 2 else 2)
            self.assertEqual(state.effective_mode, 0 if step < 5 else 2)

    def test_every_channel_respects_capacity_and_command_slew(self) -> None:
        config = self.ready_config(
            policy_capacity=0.25, support_capacity=0.22, audit_capacity=0.19,
            max_policy_slew=0.07, max_support_slew=0.05, max_audit_slew=0.03,
            physical_effect_delay_steps=2,
        )
        state = sim.ActuatorState()
        for step in range(32):
            mode = (2, 0, 1, 2)[step // 8]
            state = sim.request_mode(state, mode, step, config)
            previous = state
            state, cost = sim.advance_actuators(state, step, config, config.initial_budget)
            self.assertEqual(cost.curtailment_factor, 1.0)
            for channel in self.CHANNELS:
                with self.subTest(step=step, channel=channel):
                    command = getattr(state, f"command_{channel}")
                    effective = getattr(state, f"effective_{channel}")
                    capacity = getattr(config, f"{channel}_capacity")
                    self.assertGreaterEqual(command, 0.0)
                    self.assertLessEqual(command, capacity + 1e-12)
                    self.assertGreaterEqual(effective, 0.0)
                    self.assertLessEqual(effective, capacity + 1e-12)
                    self.assertLessEqual(
                        abs(command - getattr(previous, f"command_{channel}")),
                        getattr(config, f"max_{channel}_slew") + 1e-12,
                    )

    def test_zero_capacity_cannot_secretly_deliver_any_output(self) -> None:
        config = self.ready_config(policy_capacity=0.0, support_capacity=0.0, audit_capacity=0.0)
        state = sim.request_mode(sim.ActuatorState(), 2, 0, config)
        for step in range(8):
            state, cost = sim.advance_actuators(state, step, config, config.initial_budget)
            for channel in self.CHANNELS:
                self.assertEqual(getattr(state, f"command_{channel}"), 0.0)
                self.assertEqual(getattr(state, f"effective_{channel}"), 0.0)
            self.assertEqual(cost.step_cost, 0.0)

    def test_zero_slew_cannot_move_a_zero_initial_actuator(self) -> None:
        config = self.ready_config(max_policy_slew=0.0, max_support_slew=0.0, max_audit_slew=0.0)
        state = sim.request_mode(sim.ActuatorState(), 2, 0, config)
        for step in range(8):
            state, cost = sim.advance_actuators(state, step, config, config.initial_budget)
            for channel in self.CHANNELS:
                self.assertEqual(getattr(state, f"command_{channel}"), 0.0)
                self.assertEqual(getattr(state, f"effective_{channel}"), 0.0)
            self.assertEqual(cost.step_cost, 0.0)

    def test_costs_are_actual_delivered_outputs_and_budget_never_goes_negative(self) -> None:
        config = self.ready_config(initial_budget=0.021, physical_effect_delay_steps=2)
        state = sim.request_mode(sim.ActuatorState(), 2, 0, config)
        remaining = config.initial_budget
        total = 0.0
        saw_curtailment = False
        for step in range(20):
            previous_remaining = remaining
            state, cost = sim.advance_actuators(state, step, config, remaining)
            expected_cost = sum(
                getattr(state, f"effective_{channel}") * getattr(config, f"{channel}_cost")
                for channel in self.CHANNELS
            )
            self.assertAlmostEqual(cost.step_cost, expected_cost, places=12)
            self.assertGreaterEqual(cost.remaining_budget, 0.0)
            self.assertLessEqual(cost.step_cost, previous_remaining + 1e-12)
            self.assertAlmostEqual(cost.remaining_budget, previous_remaining - cost.step_cost, places=12)
            self.assertGreaterEqual(cost.curtailment_factor, 0.0)
            self.assertLessEqual(cost.curtailment_factor, 1.0)
            saw_curtailment |= 0.0 < cost.curtailment_factor < 1.0
            total += cost.step_cost
            remaining = cost.remaining_budget
        self.assertTrue(saw_curtailment)
        self.assertAlmostEqual(total, config.initial_budget, places=12)
        self.assertAlmostEqual(remaining, 0.0, places=12)

    def test_zero_budget_prevents_all_paid_outputs_even_after_effects_become_due(self) -> None:
        config = self.ready_config(initial_budget=0.0, physical_effect_delay_steps=2)
        state = sim.request_mode(sim.ActuatorState(), 2, 0, config)
        for step in range(10):
            state, cost = sim.advance_actuators(state, step, config, 0.0)
            for channel in self.CHANNELS:
                self.assertGreater(getattr(config, f"{channel}_cost"), 0.0)
                self.assertEqual(getattr(state, f"effective_{channel}"), 0.0)
            self.assertEqual(cost.remaining_budget, 0.0)
            self.assertEqual(cost.step_cost, 0.0)

    def test_budget_shutdown_may_exceed_downward_delivery_slew_but_not_command_slew(self) -> None:
        config = self.ready_config(max_policy_slew=0.05, max_support_slew=0.05, max_audit_slew=0.05)
        state = sim.request_mode(sim.ActuatorState(), 2, 0, config)
        for step in range(5):
            state, _ = sim.advance_actuators(state, step, config, config.initial_budget)
        previous = state
        state, cost = sim.advance_actuators(state, 5, config, 0.0)
        self.assertGreater(previous.effective_policy, config.max_policy_slew)
        self.assertEqual(state.effective_policy, 0.0)
        self.assertEqual(cost.curtailment_factor, 0.0)
        self.assertEqual(cost.step_cost, 0.0)
        for channel in self.CHANNELS:
            self.assertLessEqual(
                abs(getattr(state, f"command_{channel}") - getattr(previous, f"command_{channel}")),
                getattr(config, f"max_{channel}_slew") + 1e-12,
            )


class ReproducibilityTests(FeasibilityCase):
    PUBLIC_TRACE_FIELDS = (
        "t", "pressure_before", "pressure", "observed_pressure", "observed_at_step",
        "evidence_status", "reason", "estimated_cr", "response_status",
        "requested_mode", "pending_mode", "pending_due_step", "active_mode",
        "effective_mode", "command_policy", "command_support", "command_audit",
        "effective_policy", "effective_support", "effective_audit", "remaining_budget",
        "step_cost", "nominal_cost", "curtailment_factor", "budget_exhausted",
        "biosphere", "institution", "trust", "justice", "release_streak", "unknown_streak",
    )

    def test_environment_sampling_is_deterministic(self) -> None:
        self.assertEqual(self.environment(), self.environment())

    def test_each_trigger_reproduces_its_episode_and_trace(self) -> None:
        environment = self.environment()
        snapshot = dataclasses.asdict(environment)
        for trigger in ("threshold", "threshold_hysteresis", "reserve"):
            with self.subTest(trigger=trigger):
                left = sim.run_episode(self.config, trigger, environment, collect_trace=True)
                right = sim.run_episode(self.config, trigger, environment, collect_trace=True)
                self.assertEqual(left, right)
                self.assertEqual(dataclasses.asdict(environment), snapshot)

    def test_hidden_boundary_cannot_change_public_feedback_before_physical_crossing(self) -> None:
        environment = self.environment()
        for trigger in ("threshold", "threshold_hysteresis", "reserve"):
            traces = []
            for boundary in (0.87, 1.13):
                _, trace = sim.run_episode(
                    self.config, trigger,
                    dataclasses.replace(environment, true_boundary=boundary),
                    collect_trace=True,
                )
                traces.append(trace)
            compared = 0
            for left, right in zip(*traces):
                if left["irreversible"] or right["irreversible"]:
                    break
                with self.subTest(trigger=trigger, step=left["t"]):
                    self.assertLess(left["pressure"], 0.87)
                    self.assertLess(right["pressure"], 1.13)
                    for field in self.PUBLIC_TRACE_FIELDS:
                        self.assertEqual(left[field], right[field], field)
                compared += 1
            self.assertGreaterEqual(compared, 8, "counterfactual needs a nonempty safe prefix")

    def test_far_hidden_boundaries_leave_the_entire_public_trace_unchanged(self) -> None:
        environment = self.environment()
        traces = []
        for boundary in (100.0, 200.0):
            _, trace = sim.run_episode(
                self.config, "reserve", dataclasses.replace(environment, true_boundary=boundary),
                collect_trace=True,
            )
            traces.append(trace)
        self.assertEqual(len(traces[0]), self.config.base.horizon)
        for left, right in zip(*traces):
            for field in self.PUBLIC_TRACE_FIELDS:
                self.assertEqual(left[field], right[field], f"step={left['t']} {field}")

    def test_physical_delay_defers_real_pressure_change_not_only_the_reserve_estimate(self) -> None:
        config = dataclasses.replace(
            self.config, base=dataclasses.replace(self.config.base, horizon=8),
            actuation_delay_steps=0, physical_effect_delay_steps=3, initial_budget=100.0,
            max_policy_slew=1.0, max_support_slew=1.0, max_audit_slew=1.0,
        )
        powerless = dataclasses.replace(config, policy_capacity=0.0, support_capacity=0.0, audit_capacity=0.0)
        environment = self.environment(config)
        original_decide = sim.decide

        def request_emergency(observation, state, cfg, trigger):
            decision, updated = original_decide(observation, state, cfg, trigger)
            return dataclasses.replace(decision, requested_mode=2), dataclasses.replace(updated, authorized_mode=2)

        # Freeze actor choices to isolate the plant's direct, delayed policy term.
        actions = {
            "defective_rate": 0.0, "cooperation_rate": 1.0, "emission_load": 0.0,
            "abatement": 0.0, "restoration": 0.0, "attempted_capture": 0.0,
            "symbolic": 0.0, "burden_concentration": 0.0,
        }
        with mock.patch.object(sim, "decide", side_effect=request_emergency):
            with mock.patch.object(sim, "public_actor_actions", return_value=actions) as actor_choices:
                _, delayed = sim.run_episode(config, "reserve", environment, collect_trace=True)
                _, disabled = sim.run_episode(powerless, "reserve", environment, collect_trace=True)
        self.assertEqual(actor_choices.call_count, 2 * config.base.horizon)
        for step in range(config.physical_effect_delay_steps):
            self.assertGreater(delayed[step]["command_policy"], 0.0)
            self.assertEqual(delayed[step]["effective_policy"], 0.0)
            self.assertEqual(delayed[step]["step_cost"], 0.0)
            self.assertEqual(delayed[step]["pressure"], disabled[step]["pressure"])
        first_effect = config.physical_effect_delay_steps
        self.assertGreater(delayed[first_effect]["effective_policy"], 0.0)
        self.assertLess(delayed[first_effect]["pressure"], disabled[first_effect]["pressure"])

    def test_episode_budget_ledger_matches_every_actual_paid_output(self) -> None:
        config = dataclasses.replace(self.config, initial_budget=0.021)
        _, trace = sim.run_episode(config, "reserve", self.environment(config), collect_trace=True)
        remaining = config.initial_budget
        for row in trace:
            expected_cost = sum(
                row[f"effective_{channel}"] * getattr(config, f"{channel}_cost")
                for channel in ("policy", "support", "audit")
            )
            self.assertAlmostEqual(row["step_cost"], expected_cost, places=12)
            self.assertGreaterEqual(row["remaining_budget"], 0.0)
            self.assertAlmostEqual(remaining - row["step_cost"], row["remaining_budget"], places=12)
            remaining = row["remaining_budget"]
        self.assertAlmostEqual(
            sum(row["step_cost"] for row in trace) + remaining, config.initial_budget, places=12
        )

    def test_zero_capacity_and_zero_budget_never_count_a_paid_emergency_effect(self) -> None:
        for changes in (
            {"initial_budget": 0.0},
            {"policy_capacity": 0.0, "support_capacity": 0.0, "audit_capacity": 0.0},
        ):
            with self.subTest(changes=changes):
                config = dataclasses.replace(self.config, **changes)
                metrics, trace = sim.run_episode(config, "reserve", self.environment(config), collect_trace=True)
                self.assertEqual(metrics["effective_emergency_steps"], 0)
                self.assertTrue(all(row["step_cost"] == 0.0 for row in trace))
                self.assertTrue(all(row["effective_policy"] == 0.0 for row in trace))


if __name__ == "__main__":
    unittest.main()
