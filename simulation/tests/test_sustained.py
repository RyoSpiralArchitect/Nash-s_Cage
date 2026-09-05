"""Adversarial contracts for the public-only sustained v0.4 screen.

The assertions in this module are mechanism checks.  They do not assert that a
controller wins, that a rejected finite plan is physically infeasible, or that
the reduced-form projection is calibrated to a real system.
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

from simulation import feasibility
from simulation import rvcim_sim as legacy
from simulation import sustained as sim


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "simulation" / "configs" / "sustained_v04.json"


class SustainedCase(unittest.TestCase):
    def setUp(self) -> None:
        self.config = sim.load_config(CONFIG)

    def config_with(
        self,
        *,
        feasibility_changes: dict[str, object] | None = None,
        legacy_changes: dict[str, object] | None = None,
        **changes: object,
    ) -> sim.SustainedConfig:
        base = self.config.base
        if legacy_changes:
            base = dataclasses.replace(
                base, base=dataclasses.replace(base.base, **legacy_changes)
            )
        if feasibility_changes:
            base = dataclasses.replace(base, **feasibility_changes)
        return dataclasses.replace(self.config, base=base, **changes)

    def observation(self, step: int = 0, **changes: object) -> feasibility.Observation:
        fields: dict[str, object] = {
            "step": step,
            "observed_at_step": step,
            "observed_pressure": 0.40,
            "model_boundaries": (0.95, 1.00, 1.05),
            "institution": 0.80,
            "trust": 0.80,
            "justice": 0.80,
            "remaining_budget": self.config.base.initial_budget,
            "active_mode": 0,
            "pending_mode": None,
            "effective_policy": 0.0,
            "effective_support": 0.0,
            "effective_audit": 0.0,
        }
        fields.update(changes)
        return feasibility.Observation(**fields)

    def controller(self, step: int = 0, **changes: object) -> feasibility.ControllerState:
        fields: dict[str, object] = {
            "previous_observed_pressure": 0.39,
            "previous_observed_step": step - 1,
            "smoothed_trend": 0.01,
            "last_decision_step": step - 1,
        }
        fields.update(changes)
        return feasibility.ControllerState(**fields)

    def actuator(self, step: int = 0, **changes: object) -> feasibility.ActuatorState:
        fields: dict[str, object] = {"last_step": step - 1}
        fields.update(changes)
        return feasibility.ActuatorState(**fields)

    def environment(
        self, config: sim.SustainedConfig | None = None, episode: int = 3
    ) -> legacy.Environment:
        config = config or self.config
        return legacy.sample_environment(
            config.base.base,
            legacy.stable_seed(29, "sustained-environment", episode),
            episode=episode,
        )

    @staticmethod
    def fake_base_decision(mode: int) -> feasibility.Decision:
        return feasibility.Decision(
            evidence_status="sufficient_evidence",
            requested_mode=mode,
            estimated_cr=1.0,
            response_status="available",
            reason="test_base_decision",
        )

    @staticmethod
    def fake_projection(mode: int, passes: bool) -> sim.Projection:
        reasons = () if passes else ("final_braking_window_not_met",)
        return sim.Projection(
            mode=mode,
            max_pressure=0.50,
            boundary_margin=0.30,
            final_budget=3.0,
            total_cost=1.0,
            braking_steps_met=6 if passes else 0,
            passes=passes,
            first_violation_step=None,
            reasons=reasons,
            projected_next_pressure_upper=0.50,
            projected_pressures=(0.50,),
            projected_pressure_changes=(0.0,),
            projected_effective_policies=(0.5,),
        )


class ConfigContractTests(SustainedCase):
    def test_resolved_configuration_is_separate_and_strict(self) -> None:
        self.config.validate()
        self.assertEqual(sim.VERSION, "0.4.0-experimental")
        self.assertIsInstance(self.config.base, feasibility.FeasibilityConfig)
        self.assertEqual(self.config.base.schema_version, feasibility.SCHEMA_VERSION)
        self.assertIn("base", self.config.to_mapping())
        self.assertIn("base", self.config.to_mapping()["base"])

    def test_corrupt_numeric_history_holds_prior_authorization(self) -> None:
        for field in ("smoothed_trend", "previous_observed_pressure"):
            for value in (math.nan, math.inf, -math.inf, True, "0.1"):
                for mode in (0, 1, 2):
                    with self.subTest(field=field, value=value, mode=mode):
                        state = self.controller(**{field: value}, authorized_mode=mode,
                                                release_streak=2, normal_release_streak=2,
                                                precaution_release_streak=2)
                        decision, updated = sim.sustained_decide(
                            self.observation(), state, self.actuator(), self.config)
                        self.assertEqual("insufficient_evidence", decision.evidence_status)
                        self.assertEqual(mode, decision.requested_mode)
                        self.assertEqual((), decision.assessment.projections)
                        self.assertIsNone(decision.assessment.selected_plan_mode)
                        self.assertEqual(0, updated.release_streak)
                        self.assertEqual(0, updated.normal_release_streak)
                        self.assertEqual(0, updated.precaution_release_streak)
                        self.assertEqual(state.unknown_steps + 1, updated.unknown_steps)

    def test_direct_projection_rejects_corrupt_numeric_history(self) -> None:
        for field in ("smoothed_trend", "previous_observed_pressure"):
            for value in (math.nan, math.inf, -math.inf, True, "0.1"):
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    sim.project_constant_mode(self.observation(), self.controller(**{field: value}),
                                              self.actuator(), self.config, 0)

    def test_finite_inputs_cannot_overflow_into_passing_projection(self) -> None:
        with self.assertRaisesRegex(ValueError, "nonfinite projection arithmetic"):
            sim.project_constant_mode(self.observation(), self.controller(smoothed_trend=-1e308),
                                      self.actuator(), self.config, 0)

    def test_malformed_history_counters_and_timestamps_are_rejected(self) -> None:
        for field in ("release_streak", "unknown_steps", "previous_observed_step", "last_decision_step"):
            for value in (True, math.nan, math.inf, "0", -2):
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    sim.sustained_decide(self.observation(), self.controller(**{field: value}),
                                         self.actuator(), self.config)

    def test_unknown_and_missing_keys_are_rejected(self) -> None:
        payload = json.loads(CONFIG.read_text(encoding="utf-8"))
        variants = []
        with_extra = dict(payload)
        with_extra["silent_extra"] = 1
        variants.append(with_extra)
        missing = dict(payload)
        missing.pop("forecast_steps")
        variants.append(missing)
        for index, variant in enumerate(variants):
            with self.subTest(index=index), tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "invalid.json"
                path.write_text(json.dumps(variant), encoding="utf-8")
                with self.assertRaises(legacy.ConfigError):
                    sim.load_config(path)

    def test_nonfinite_and_negative_assumptions_are_rejected(self) -> None:
        nonnegative = (
            "drift_margin",
            "policy_gain_lower",
            "policy_gain_upper",
            "pressure_error_bound",
            "model_boundary_margin",
            "terminal_budget_reserve",
        )
        for name in nonnegative:
            for value in (-0.01, math.nan, math.inf, -math.inf):
                with self.subTest(field=name, value=value):
                    with self.assertRaises(legacy.ConfigError):
                        dataclasses.replace(self.config, **{name: value}).validate()
        for value in (math.nan, math.inf, -math.inf):
            with self.subTest(field="max_projected_pressure_change", value=value):
                with self.assertRaises(legacy.ConfigError):
                    dataclasses.replace(
                        self.config, max_projected_pressure_change=value
                    ).validate()

    def test_horizon_fields_require_real_positive_integers(self) -> None:
        for name in ("forecast_steps", "required_braking_steps"):
            for value in (0, -1, 1.5, True, math.nan):
                with self.subTest(field=name, value=value):
                    with self.assertRaises(legacy.ConfigError):
                        dataclasses.replace(self.config, **{name: value}).validate()

    def test_braking_window_cannot_exceed_projection_horizon(self) -> None:
        with self.assertRaises(legacy.ConfigError):
            dataclasses.replace(
                self.config,
                forecast_steps=3,
                required_braking_steps=4,
            ).validate()

    def test_policy_gain_bounds_must_form_an_interval(self) -> None:
        with self.assertRaises(legacy.ConfigError):
            dataclasses.replace(
                self.config,
                policy_gain_lower=0.11,
                policy_gain_upper=0.10,
            ).validate()

    def test_braking_threshold_cannot_admit_positive_final_drift(self) -> None:
        with self.assertRaises(legacy.ConfigError):
            dataclasses.replace(
                self.config, max_projected_pressure_change=1e-9
            ).validate()

    def test_boolean_and_string_numeric_values_are_not_accepted(self) -> None:
        for name in (
            "drift_margin",
            "policy_gain_lower",
            "policy_gain_upper",
            "pressure_error_bound",
            "model_boundary_margin",
            "terminal_budget_reserve",
            "max_projected_pressure_change",
        ):
            for value in (True, "0.1"):
                with self.subTest(field=name, value=value):
                    with self.assertRaises(legacy.ConfigError):
                        dataclasses.replace(self.config, **{name: value}).validate()


class InformationBoundaryTests(SustainedCase):
    def test_public_projection_and_decision_signatures_are_exact(self) -> None:
        self.assertEqual(
            tuple(inspect.signature(sim.project_constant_mode).parameters),
            (
                "observation",
                "controller_state",
                "actuator_state",
                "config",
                "candidate_mode",
            ),
        )
        self.assertEqual(
            tuple(inspect.signature(sim.sustained_decide).parameters),
            ("observation", "controller_state", "actuator_state", "config"),
        )
        forbidden = {
            "environment",
            "world",
            "world_state",
            "plant",
            "true_boundary",
            "hidden_cr",
            "truth_mode",
            "irreversible",
            "forecast_error",
        }
        for record in (
            sim.Projection,
            sim.SustainedAssessment,
            sim.SustainedDecision,
            feasibility.ControllerState,
        ):
            with self.subTest(record=record.__name__):
                self.assertFalse(
                    forbidden & {field.name for field in dataclasses.fields(record)}
                )

    def test_identical_public_inputs_give_identical_projection_and_decision(self) -> None:
        observation = self.observation()
        controller = self.controller()
        actuator = self.actuator()
        # These hidden worlds intentionally differ, but cannot be supplied to
        # either public function.
        left_world = dataclasses.replace(self.environment(), true_boundary=10.0)
        right_world = dataclasses.replace(self.environment(), true_boundary=20.0)
        self.assertNotEqual(left_world.true_boundary, right_world.true_boundary)
        left_projection = sim.project_constant_mode(
            observation, controller, actuator, self.config, 2
        )
        right_projection = sim.project_constant_mode(
            dataclasses.replace(observation),
            dataclasses.replace(controller),
            dataclasses.replace(actuator),
            self.config,
            2,
        )
        self.assertEqual(left_projection, right_projection)
        self.assertEqual(
            sim.sustained_decide(observation, controller, actuator, self.config),
            sim.sustained_decide(
                dataclasses.replace(observation),
                dataclasses.replace(controller),
                dataclasses.replace(actuator),
                self.config,
            ),
        )

    def test_projection_and_decision_never_call_truth_helpers(self) -> None:
        with mock.patch.object(
            legacy, "hidden_reserve", side_effect=AssertionError("truth leak")
        ), mock.patch.object(
            legacy, "truth_mode", side_effect=AssertionError("truth leak")
        ), mock.patch.object(
            feasibility, "advance_plant", side_effect=AssertionError("truth leak")
        ):
            sim.project_constant_mode(
                self.observation(), self.controller(), self.actuator(), self.config, 2
            )
            sim.sustained_decide(
                self.observation(), self.controller(), self.actuator(), self.config
            )

    def test_full_pending_transition_changes_projection_and_is_not_postponed(self) -> None:
        config = self.config_with(
            feasibility_changes={
                "actuation_delay_steps": 2,
                "physical_effect_delay_steps": 0,
                "max_policy_slew": 1.0,
                "initial_budget": 100.0,
            },
            forecast_steps=5,
            required_braking_steps=1,
            terminal_budget_reserve=0.0,
        )
        observation = self.observation(step=5, remaining_budget=100.0)
        observation = dataclasses.replace(observation, pending_mode=2)
        controller = self.controller(step=5)
        already_pending = self.actuator(
            step=5,
            requested_mode=2,
            transitions=(feasibility.ModeTransition(3, 5, 2),),
        )
        later_pending = self.actuator(
            step=5,
            requested_mode=2,
            transitions=(feasibility.ModeTransition(4, 6, 2),),
        )
        pending_projection = sim.project_constant_mode(
            observation, controller, already_pending, config, 2
        )
        later_projection = sim.project_constant_mode(
            observation, controller, later_pending, config, 2
        )
        self.assertNotEqual(
            pending_projection.projected_effective_policies,
            later_projection.projected_effective_policies,
        )
        pending_first = next(
            index
            for index, value in enumerate(
                pending_projection.projected_effective_policies
            )
            if value > 0.50
        )
        later_first = next(
            index
            for index, value in enumerate(later_projection.projected_effective_policies)
            if value > 0.50
        )
        self.assertLess(pending_first, later_first)

    def test_full_pending_effect_queue_changes_the_projected_delivery(self) -> None:
        config = self.config_with(
            feasibility_changes={
                "actuation_delay_steps": 0,
                "physical_effect_delay_steps": 3,
                "max_policy_slew": 0.0,
                "initial_budget": 100.0,
            },
            forecast_steps=4,
            required_braking_steps=1,
            terminal_budget_reserve=0.0,
        )
        observation = self.observation(step=5, remaining_budget=100.0)
        controller = self.controller(step=5)
        queued = self.actuator(
            step=5,
            effects=(feasibility.EffectCommand(2, 5, 2, 0.91, 0.82, 0.96),),
        )
        empty = self.actuator(step=5)
        queued_projection = sim.project_constant_mode(
            observation, controller, queued, config, 0
        )
        empty_projection = sim.project_constant_mode(
            observation, controller, empty, config, 0
        )
        self.assertGreater(queued_projection.projected_effective_policies[0], 0.0)
        self.assertEqual(empty_projection.projected_effective_policies[0], 0.0)
        self.assertNotEqual(queued_projection, empty_projection)

    def test_asymmetric_capacities_are_checked_against_the_matching_channel(self) -> None:
        config = self.config_with(
            feasibility_changes={
                "policy_capacity": 0.90,
                "support_capacity": 0.20,
                "audit_capacity": 0.10,
                "initial_budget": 100.0,
            },
            forecast_steps=1,
            required_braking_steps=1,
            terminal_budget_reserve=0.0,
        )
        observation = self.observation(
            remaining_budget=100.0,
            effective_policy=0.90,
            effective_support=0.20,
            effective_audit=0.10,
        )
        valid = self.actuator(
            command_policy=0.90,
            command_support=0.20,
            command_audit=0.10,
            effective_policy=0.90,
            effective_support=0.20,
            effective_audit=0.10,
        )
        sim.project_constant_mode(
            observation, self.controller(), valid, config, 0
        )
        for channel, excess in (
            ("policy", 0.91),
            ("support", 0.21),
            ("audit", 0.11),
        ):
            for kind in ("command", "effective"):
                with self.subTest(channel=channel, kind=kind):
                    changes = {f"{kind}_{channel}": excess}
                    invalid = dataclasses.replace(valid, **changes)
                    invalid_observation = observation
                    if kind == "effective":
                        invalid_observation = dataclasses.replace(
                            observation, **{f"effective_{channel}": excess}
                        )
                    with self.assertRaisesRegex(
                        ValueError, "valid full actuator ledger"
                    ):
                        sim.project_constant_mode(
                            invalid_observation,
                            self.controller(),
                            invalid,
                            config,
                            0,
                        )


class ProjectionArithmeticTests(SustainedCase):
    def test_controlled_trend_is_reconstructed_without_double_counting(self) -> None:
        config = self.config_with(
            feasibility_changes={
                "max_policy_slew": 0.0,
                "physical_effect_delay_steps": 0,
                "initial_budget": 100.0,
            },
            forecast_steps=1,
            required_braking_steps=1,
            drift_margin=0.008,
            policy_gain_lower=0.03,
            policy_gain_upper=0.05,
            pressure_error_bound=0.04,
            model_boundary_margin=0.0,
            terminal_budget_reserve=0.0,
        )
        observation = self.observation(
            observed_pressure=0.40,
            model_boundaries=(2.0,),
            remaining_budget=100.0,
            effective_policy=0.20,
        )
        controller = self.controller(smoothed_trend=0.01)
        actuator = self.actuator(
            command_policy=0.20,
            effective_policy=0.20,
        )
        projection = sim.project_constant_mode(
            observation, controller, actuator, config, 0
        )
        expected_change = 0.01 + 0.05 * 0.20 + 0.008 - 0.03 * 0.20
        self.assertAlmostEqual(
            projection.projected_pressure_changes[0], expected_change, places=12
        )
        self.assertAlmostEqual(
            projection.projected_pressures[0], 0.40 + 0.04 + expected_change, places=12
        )

    def test_boundary_condition_is_strict_not_nonstrict(self) -> None:
        config = self.config_with(
            feasibility_changes={"max_policy_slew": 0.0, "initial_budget": 100.0},
            forecast_steps=1,
            required_braking_steps=1,
            drift_margin=0.0,
            pressure_error_bound=0.0,
            model_boundary_margin=0.02,
            terminal_budget_reserve=0.0,
        )
        controller = self.controller(
            previous_observed_pressure=0.40,
            previous_observed_step=0,
            smoothed_trend=0.0,
            last_decision_step=0,
        )
        actuator = self.actuator()
        exact_boundary = 0.40 + feasibility.MATCHED_ARM.structural_allowance + 0.02
        exact = sim.project_constant_mode(
            self.observation(model_boundaries=(exact_boundary,), remaining_budget=100.0),
            controller,
            actuator,
            config,
            0,
        )
        outside = sim.project_constant_mode(
            self.observation(
                model_boundaries=(exact_boundary + 1e-9,), remaining_budget=100.0
            ),
            controller,
            actuator,
            config,
            0,
        )
        self.assertEqual(exact.boundary_margin, 0.0)
        self.assertFalse(exact.passes)
        self.assertIn("pressure_not_strictly_below_declared_boundary", exact.reasons)
        self.assertGreater(outside.boundary_margin, 0.0)
        self.assertTrue(outside.passes)

    def test_candidate_requires_the_complete_final_braking_window(self) -> None:
        config = self.config_with(
            feasibility_changes={"max_policy_slew": 0.0, "initial_budget": 100.0},
            forecast_steps=4,
            required_braking_steps=2,
            drift_margin=0.0,
            pressure_error_bound=0.0,
            model_boundary_margin=0.0,
            terminal_budget_reserve=0.0,
            max_projected_pressure_change=0.0,
        )
        projection = sim.project_constant_mode(
            self.observation(model_boundaries=(10.0,), remaining_budget=100.0),
            self.controller(smoothed_trend=0.01),
            self.actuator(),
            config,
            0,
        )
        self.assertEqual(len(projection.projected_pressure_changes), 4)
        self.assertEqual(projection.braking_steps_met, 0)
        self.assertFalse(projection.passes)
        self.assertIn("final_braking_window_not_met", projection.reasons)

    def test_terminal_budget_threshold_is_inclusive(self) -> None:
        config = self.config_with(
            feasibility_changes={"max_policy_slew": 0.0},
            forecast_steps=1,
            required_braking_steps=1,
            drift_margin=0.0,
            pressure_error_bound=0.0,
            model_boundary_margin=0.0,
            terminal_budget_reserve=1.0,
        )
        controller = self.controller(
            previous_observed_pressure=0.40,
            previous_observed_step=0,
            smoothed_trend=0.0,
            last_decision_step=0,
        )
        exact = sim.project_constant_mode(
            self.observation(model_boundaries=(10.0,), remaining_budget=1.0),
            controller,
            self.actuator(),
            config,
            0,
        )
        short = sim.project_constant_mode(
            self.observation(model_boundaries=(10.0,), remaining_budget=0.99),
            controller,
            self.actuator(),
            config,
            0,
        )
        self.assertTrue(exact.passes)
        self.assertFalse(short.passes)
        self.assertIn("terminal_budget_reserve_not_met", short.reasons)

    def test_a_plan_whose_effect_arrives_only_after_the_horizon_cannot_pass(self) -> None:
        base_changes = {
            "actuation_delay_steps": 2,
            "physical_effect_delay_steps": 5,
            "max_policy_slew": 1.0,
            "initial_budget": 100.0,
        }
        common = {
            "required_braking_steps": 2,
            "drift_margin": 0.0,
            "pressure_error_bound": 0.0,
            "model_boundary_margin": 0.0,
            "terminal_budget_reserve": 0.0,
            "max_projected_pressure_change": 0.0,
        }
        short = self.config_with(
            feasibility_changes=base_changes, forecast_steps=4, **common
        )
        long = self.config_with(
            feasibility_changes=base_changes, forecast_steps=12, **common
        )
        observation = self.observation(
            model_boundaries=(10.0,), remaining_budget=100.0
        )
        controller = self.controller(smoothed_trend=0.01)
        short_projection = sim.project_constant_mode(
            observation, controller, self.actuator(), short, 2
        )
        long_projection = sim.project_constant_mode(
            observation, controller, self.actuator(), long, 2
        )
        self.assertFalse(short_projection.passes)
        self.assertIn("final_braking_window_not_met", short_projection.reasons)
        short_decision, _ = sim.sustained_decide(
            observation, controller, self.actuator(), short
        )
        self.assertEqual(
            short_decision.status, "no_candidate_plan_within_declared_model"
        )
        self.assertTrue(
            all(
                projection.total_cost == 0.0
                for projection in short_decision.assessment.projections
            )
        )
        self.assertTrue(long_projection.passes)

    def test_zero_budget_and_zero_capacity_have_no_paid_projected_effects(self) -> None:
        hostile = {
            "forecast_steps": 4,
            "required_braking_steps": 2,
            "drift_margin": 0.0,
            "pressure_error_bound": 0.0,
            "model_boundary_margin": 0.0,
            "max_projected_pressure_change": 0.0,
        }
        cases = (
            self.config_with(
                feasibility_changes={"initial_budget": 0.0},
                terminal_budget_reserve=0.2,
                **hostile,
            ),
            self.config_with(
                feasibility_changes={
                    "initial_budget": 100.0,
                    "policy_capacity": 0.0,
                    "support_capacity": 0.0,
                    "audit_capacity": 0.0,
                },
                terminal_budget_reserve=0.0,
                **hostile,
            ),
        )
        for index, config in enumerate(cases):
            budget = config.base.initial_budget
            observation = self.observation(
                model_boundaries=(10.0,), remaining_budget=budget
            )
            with self.subTest(case=index):
                decision, _ = sim.sustained_decide(
                    observation, self.controller(), self.actuator(), config
                )
                self.assertEqual(
                    decision.status, "no_candidate_plan_within_declared_model"
                )
                self.assertIsNone(decision.assessment.selected_plan_mode)
                for projection in decision.assessment.projections:
                    self.assertEqual(projection.total_cost, 0.0)
                    self.assertTrue(
                        all(value == 0.0 for value in projection.projected_effective_policies)
                    )


class DecisionContractTests(SustainedCase):
    def test_missing_stale_and_replayed_evidence_hold_without_projection(self) -> None:
        cases = (
            self.observation(step=1, observed_pressure=None),
            self.observation(
                step=4,
                observed_at_step=4 - self.config.base.max_observation_age_steps - 1,
            ),
            self.observation(step=1, observed_at_step=0),
        )
        for index, observation in enumerate(cases):
            prior = self.controller(
                step=1 if index != 1 else 4,
                authorized_mode=1,
                previous_observed_step=0,
                last_decision_step=0,
            )
            actuator = self.actuator(step=observation.step)
            with self.subTest(case=index), mock.patch.object(
                sim,
                "project_constant_mode",
                side_effect=AssertionError("projection must not run"),
            ):
                decision, updated = sim.sustained_decide(
                    observation, prior, actuator, self.config
                )
                self.assertEqual(decision.evidence_status, "insufficient_evidence")
                self.assertEqual(decision.status, "insufficient_evidence")
                self.assertEqual(decision.requested_mode, 1)
                self.assertEqual(updated.authorized_mode, 1)
                self.assertEqual(decision.assessment.projections, ())

    def test_lowest_passing_plan_at_or_above_base_reserve_is_selected(self) -> None:
        base_decision = self.fake_base_decision(1)

        def projection(
            observation: feasibility.Observation,
            controller_state: feasibility.ControllerState,
            actuator_state: feasibility.ActuatorState,
            config: sim.SustainedConfig,
            candidate_mode: int,
        ) -> sim.Projection:
            del observation, controller_state, actuator_state, config
            return self.fake_projection(candidate_mode, passes=True)

        with mock.patch.object(
            feasibility, "decide", return_value=(base_decision, self.controller())
        ), mock.patch.object(sim, "project_constant_mode", side_effect=projection) as project:
            decision, _ = sim.sustained_decide(
                self.observation(), self.controller(), self.actuator(), self.config
            )
        self.assertEqual(tuple(item.mode for item in decision.assessment.projections), (0, 1, 2))
        self.assertEqual(project.call_count, 3)
        self.assertEqual(decision.assessment.selected_plan_mode, 1)
        self.assertEqual(decision.requested_mode, 1)
        self.assertEqual(decision.status, "plan_found_within_declared_model")

    def test_no_candidate_uses_emergency_only_as_a_loss_limiting_request(self) -> None:
        base_decision = self.fake_base_decision(1)

        def rejection(*args: object) -> sim.Projection:
            return self.fake_projection(int(args[-1]), passes=False)

        with mock.patch.object(
            feasibility, "decide", return_value=(base_decision, self.controller())
        ), mock.patch.object(sim, "project_constant_mode", side_effect=rejection):
            decision, _ = sim.sustained_decide(
                self.observation(), self.controller(), self.actuator(), self.config
            )
        self.assertEqual(decision.status, "no_candidate_plan_within_declared_model")
        self.assertIsNone(decision.assessment.selected_plan_mode)
        self.assertEqual(decision.requested_mode, 2)
        self.assertIn("loss_limiting", decision.reason)
        self.assertNotIn("physically_infeasible", decision.status.lower())
        self.assertNotIn("physically_infeasible", decision.reason.lower())

    def test_decision_exposes_only_the_first_receding_horizon_request(self) -> None:
        decision, _ = sim.sustained_decide(
            self.observation(), self.controller(), self.actuator(), self.config
        )
        self.assertIn("first_request", decision.execution_semantics)
        self.assertIn("receding_horizon", decision.execution_semantics)
        self.assertFalse(
            {"planned_requests", "committed_tail", "future_requests"}
            & {field.name for field in dataclasses.fields(decision)}
        )
        if decision.assessment.selected_plan_mode is not None:
            self.assertEqual(
                decision.requested_mode, decision.assessment.selected_plan_mode
            )

    def test_status_vocabulary_never_claims_physical_infeasibility(self) -> None:
        allowed = {
            "plan_found_within_declared_model",
            "no_candidate_plan_within_declared_model",
            "insufficient_evidence",
        }
        observations = (
            self.observation(),
            self.observation(observed_pressure=None),
            self.observation(observed_pressure=0.94),
        )
        for observation in observations:
            controller = self.controller()
            decision, _ = sim.sustained_decide(
                observation, controller, self.actuator(), self.config
            )
            self.assertIn(decision.status, allowed)
            self.assertIn(decision.assessment.status, allowed)


class MonotonicFixtureTests(SustainedCase):
    def test_more_budget_cannot_hurt_an_otherwise_identical_projection(self) -> None:
        config = self.config_with(
            feasibility_changes={"max_policy_slew": 0.0},
            forecast_steps=1,
            required_braking_steps=1,
            drift_margin=0.0,
            pressure_error_bound=0.0,
            model_boundary_margin=0.0,
            terminal_budget_reserve=1.0,
        )
        controller = self.controller(
            previous_observed_pressure=0.40,
            previous_observed_step=0,
            smoothed_trend=0.0,
            last_decision_step=0,
        )
        low = sim.project_constant_mode(
            self.observation(model_boundaries=(10.0,), remaining_budget=0.5),
            controller,
            self.actuator(),
            config,
            0,
        )
        high = sim.project_constant_mode(
            self.observation(model_boundaries=(10.0,), remaining_budget=2.0),
            controller,
            self.actuator(),
            config,
            0,
        )
        self.assertFalse(low.passes)
        self.assertTrue(high.passes)
        self.assertGreater(high.final_budget, low.final_budget)

    def test_stronger_mode_cannot_worsen_pressure_in_an_isolated_fixture(self) -> None:
        config = self.config_with(
            feasibility_changes={
                "actuation_delay_steps": 0,
                "physical_effect_delay_steps": 0,
                "max_policy_slew": 1.0,
                "initial_budget": 100.0,
            },
            forecast_steps=4,
            required_braking_steps=2,
            drift_margin=0.0,
            pressure_error_bound=0.0,
            model_boundary_margin=0.0,
            terminal_budget_reserve=0.0,
            max_projected_pressure_change=0.0,
        )
        observation = self.observation(
            model_boundaries=(10.0,), remaining_budget=100.0
        )
        controller = self.controller(smoothed_trend=0.03)
        precaution = sim.project_constant_mode(
            observation, controller, self.actuator(), config, 1
        )
        emergency = sim.project_constant_mode(
            observation, controller, self.actuator(), config, 2
        )
        self.assertLessEqual(emergency.max_pressure, precaution.max_pressure)
        self.assertGreaterEqual(
            emergency.braking_steps_met, precaution.braking_steps_met
        )
        if precaution.passes:
            self.assertTrue(emergency.passes)


class EpisodeBoundaryTests(SustainedCase):
    def test_no_candidate_reason_counts_match_the_visible_emergency_projection(self) -> None:
        metrics, trace = sim.run_episode(
            self.config, self.environment(), collect_trace=True
        )
        reason_metrics = {
            "pressure_not_strictly_below_declared_boundary": (
                "no_candidate_boundary_steps"
            ),
            "final_braking_window_not_met": "no_candidate_braking_steps",
            "terminal_budget_reserve_not_met": "no_candidate_budget_steps",
        }
        for reason, metric in reason_metrics.items():
            expected = sum(
                row["assessment_status"]
                == "no_candidate_plan_within_declared_model"
                and reason in (row["projection_reasons"] or "").split("|")
                for row in trace
            )
            with self.subTest(reason=reason):
                self.assertEqual(metrics[metric], expected)
                self.assertLessEqual(
                    metrics[metric], metrics["assessment_no_candidate_steps"]
                )
        self.assertTrue(any(metrics[name] > 0 for name in reason_metrics.values()))

    def test_far_hidden_boundaries_cannot_change_the_public_episode_trace(self) -> None:
        environment = self.environment()
        left = dataclasses.replace(environment, true_boundary=10.0)
        right = dataclasses.replace(environment, true_boundary=20.0)
        left_metrics, left_trace = sim.run_episode(
            self.config, left, collect_trace=True
        )
        right_metrics, right_trace = sim.run_episode(
            self.config, right, collect_trace=True
        )
        self.assertEqual(len(left_trace), len(right_trace))
        truth_trace_fields = {"true_boundary", "irreversible"}
        for step, (left_row, right_row) in enumerate(zip(left_trace, right_trace)):
            with self.subTest(step=step):
                self.assertEqual(
                    {k: v for k, v in left_row.items() if k not in truth_trace_fields},
                    {k: v for k, v in right_row.items() if k not in truth_trace_fields},
                )
        truth_metric_fields = {
            "true_boundary",
            "irreversible_entry",
            "first_irreversible_step",
        }
        self.assertEqual(
            {k: v for k, v in left_metrics.items() if k not in truth_metric_fields},
            {k: v for k, v in right_metrics.items() if k not in truth_metric_fields},
        )
        self.assertNotEqual(left_metrics["true_boundary"], right_metrics["true_boundary"])

    def test_forecast_error_is_diagnostic_only_not_controller_memory(self) -> None:
        forbidden = {"forecast_error", "projection_error", "realized_error"}
        self.assertFalse(
            forbidden
            & {field.name for field in dataclasses.fields(feasibility.ControllerState)}
        )
        self.assertNotIn(
            "forecast_error", inspect.signature(sim.sustained_decide).parameters
        )
        _, trace = sim.run_episode(
            self.config, self.environment(), collect_trace=True
        )
        # Diagnostics may be emitted after realization, but no later decision
        # can receive them through the fixed public signature or memory DTO.
        if trace and "forecast_error" in trace[0]:
            self.assertTrue(
                all(
                    row["forecast_error"] is None
                    or isinstance(row["forecast_error"], (int, float))
                    for row in trace
                )
            )

    def test_paired_episode_replay_is_deterministic(self) -> None:
        environment = self.environment(episode=7)
        first = sim.run_episode(self.config, environment, collect_trace=True)
        second = sim.run_episode(self.config, environment, collect_trace=True)
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
