"""F0 sustained-braking experiment built on the v0.3 public control boundary.

The controller in this module is an uncalibrated receding-horizon toy.  It is
not an empirical model, a forecast of a real system, a recovery probability, a
safety or feasibility certificate, or a policy recommendation.  Its declared
projection uses only the current public observation, the public controller
history, and the complete public actuator ledger (including both queues).
Hidden plant state, the sampled true boundary, and evaluator outcomes are not
inputs to :func:`project_constant_mode` or :func:`sustained_decide`.

At every sufficient observation the v0.3 reserve controller is evaluated
first.  Three constant requested modes are then projected through the exact
v0.3 actuator transition, slew, delay, capacity, and paid-delivery mechanics.
Only the first request is issued; the entire assessment is recomputed after the
next observation.  A failure to find a candidate is therefore a bounded result
inside the declared synthetic model, not a conclusion about the real world.
"""

from __future__ import annotations

import dataclasses
import json
import math
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Mapping

from . import feasibility
from . import rvcim_sim as legacy

VERSION = "0.4.0-experimental"
SCHEMA_VERSION = 1
CLAIM_LEVEL = "F0"
CLAIM_BOUNDARY = (
    "Uncalibrated structural projection only; no empirical validation, real-world "
    "prediction, recovery probability, safety certificate, or policy recommendation."
)
TRIGGER = "sustained_reserve"
DEFAULT_BASE_CONFIG = Path(__file__).resolve().parent / "configs" / "feasibility_v03.json"
ConfigError = legacy.ConfigError

STATUS_PLAN_FOUND = "plan_found_within_declared_model"
STATUS_NO_CANDIDATE = "no_candidate_plan_within_declared_model"
STATUS_INSUFFICIENT_EVIDENCE = "insufficient_evidence"
ASSESSMENT_STATUSES = (
    STATUS_PLAN_FOUND,
    STATUS_NO_CANDIDATE,
    STATUS_INSUFFICIENT_EVIDENCE,
)
EXECUTION_SEMANTICS = "receding_horizon_first_request_only_reassess_each_observation"
ASSUMPTION_LABELS = (
    "public_observation_controller_history_and_full_actuator_ledger_only",
    "uncalibrated_constant_policy_gain_bounds",
    "observed_trend_debiased_by_current_delivered_policy",
    "constant_candidate_request_over_declared_forecast_horizon",
    "v03_actuator_queues_delays_slew_capacity_and_paid_delivery",
    "strict_declared_model_boundary_and_terminal_braking_tests",
    EXECUTION_SEMANTICS,
    "f0_not_empirical_not_probability_not_certificate_not_recommendation",
)
CANDIDATE_MODES = (0, 1, 2)


def _finite_number(value: Any) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(value)
    )


def _integer(value: Any, minimum: int = 0) -> bool:
    return not isinstance(value, bool) and isinstance(value, int) and value >= minimum


def _valid_mode(value: Any) -> bool:
    return _integer(value) and value in legacy.MODE_NAMES


@dataclass(frozen=True)
class SustainedConfig:
    """Declared v0.4 projection assumptions wrapped around a resolved v0.3 config."""

    base: feasibility.FeasibilityConfig
    schema_version: int = SCHEMA_VERSION
    forecast_steps: int = 24
    required_braking_steps: int = 6
    max_projected_pressure_change: float = 0.0
    drift_margin: float = 0.008
    policy_gain_lower: float = 0.03
    policy_gain_upper: float = 0.05
    pressure_error_bound: float = 0.04
    model_boundary_margin: float = 0.02
    terminal_budget_reserve: float = 0.20

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        if not isinstance(self.base, feasibility.FeasibilityConfig):
            raise ConfigError("base must be a FeasibilityConfig")
        self.base.validate()
        if not _integer(self.schema_version) or self.schema_version != SCHEMA_VERSION:
            raise ConfigError(f"schema_version must equal {SCHEMA_VERSION}")
        if not _integer(self.forecast_steps, 1):
            raise ConfigError("forecast_steps must be a positive integer")
        if not _integer(self.required_braking_steps, 1):
            raise ConfigError("required_braking_steps must be a positive integer")
        if self.required_braking_steps > self.forecast_steps:
            raise ConfigError("required_braking_steps cannot exceed forecast_steps")
        numeric_fields = (
            "max_projected_pressure_change",
            "drift_margin",
            "policy_gain_lower",
            "policy_gain_upper",
            "pressure_error_bound",
            "model_boundary_margin",
            "terminal_budget_reserve",
        )
        for name in numeric_fields:
            if not _finite_number(getattr(self, name)):
                raise ConfigError(f"{name} must be a finite number")
        for name in numeric_fields[1:]:
            if getattr(self, name) < 0.0:
                raise ConfigError(f"{name} must be nonnegative")
        if self.max_projected_pressure_change > 0.0:
            raise ConfigError(
                "max_projected_pressure_change must be nonpositive for braking"
            )
        if self.policy_gain_upper < self.policy_gain_lower:
            raise ConfigError("policy_gain_upper must be at least policy_gain_lower")

    @classmethod
    def from_mapping(
        cls,
        payload: Mapping[str, Any],
        base: feasibility.FeasibilityConfig | None = None,
    ) -> "SustainedConfig":
        if not isinstance(payload, Mapping):
            raise ConfigError("configuration root must be a JSON object")
        values = dict(payload)
        if "base" in values:
            if base is not None:
                raise ConfigError("provide inline base or base_path, not both")
            nested = values.pop("base")
            if not isinstance(nested, Mapping):
                raise ConfigError("base must be a JSON object")
            base = feasibility.FeasibilityConfig.from_mapping(nested)
        if base is None:
            raise ConfigError("base configuration must be supplied")
        required = {item.name for item in dataclasses.fields(cls)} - {"base"}
        unknown = sorted(set(values) - required)
        missing = sorted(required - set(values))
        if unknown:
            raise ConfigError(f"unknown sustained configuration keys: {', '.join(unknown)}")
        if missing:
            raise ConfigError(f"missing sustained configuration keys: {', '.join(missing)}")
        try:
            return cls(base=base, **values)
        except TypeError as exc:
            raise ConfigError(str(exc)) from exc

    def to_mapping(self) -> dict[str, Any]:
        """Return a self-contained mapping including v0.3 and legacy assumptions."""
        result = dataclasses.asdict(self)
        result["base"] = self.base.to_mapping()
        return result


def _unique_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ConfigError(f"duplicate JSON configuration key: {key}")
        result[key] = value
    return result


def load_config(path: Path, base_path: Path | None = None) -> SustainedConfig:
    """Load a strict wrapper, resolving its v0.3 base from a module-relative path."""
    try:
        payload = json.loads(
            Path(path).read_text(encoding="utf-8"),
            object_pairs_hook=_unique_json_object,
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ConfigError(f"cannot read sustained configuration {path}: {exc}") from exc
    if not isinstance(payload, Mapping):
        raise ConfigError("configuration root must be a JSON object")
    if "base" in payload:
        if base_path is not None:
            raise ConfigError("provide inline base or base_path, not both")
        return SustainedConfig.from_mapping(payload)
    resolved_base = feasibility.load_config(
        Path(base_path) if base_path is not None else DEFAULT_BASE_CONFIG
    )
    return SustainedConfig.from_mapping(payload, base=resolved_base)


@dataclass(frozen=True)
class Projection:
    """One constant-mode projection under the explicitly declared assumptions."""

    mode: int
    max_pressure: float
    boundary_margin: float
    final_budget: float
    total_cost: float
    braking_steps_met: int
    passes: bool
    first_violation_step: int | None
    reasons: tuple[str, ...]
    projected_next_pressure_upper: float
    projected_pressures: tuple[float, ...]
    projected_pressure_changes: tuple[float, ...]
    projected_effective_policies: tuple[float, ...]


@dataclass(frozen=True)
class SustainedAssessment:
    """The complete per-mode assessment returned at one public observation."""

    status: str
    selected_plan_mode: int | None
    projections: tuple[Projection, ...]
    assumption_labels: tuple[str, ...] = ASSUMPTION_LABELS


@dataclass(frozen=True)
class SustainedDecision:
    """One receding-horizon request; it is not a commitment to the full projection."""

    evidence_status: str
    requested_mode: int
    status: str
    reason: str
    base_decision: feasibility.Decision
    assessment: SustainedAssessment
    execution_semantics: str = EXECUTION_SEMANTICS


def _actuator_state_error(
    observation: feasibility.Observation,
    state: feasibility.ActuatorState,
    config: SustainedConfig,
) -> str | None:
    """Check that the complete actuator ledger is valid and synchronized."""
    if not isinstance(state, feasibility.ActuatorState):
        return "invalid_actuator_state_dto"
    if (
        isinstance(state.last_step, bool)
        or not isinstance(state.last_step, int)
        or state.last_step < -1
        or state.last_step != observation.step - 1
    ):
        return "actuator_step_not_synchronized"
    for name in ("requested_mode", "active_mode", "effective_mode"):
        if not _valid_mode(getattr(state, name)):
            return f"invalid_actuator_{name}"
    numeric_fields = (
        "command_policy", "command_support", "command_audit",
        "effective_policy", "effective_support", "effective_audit",
    )
    for name in numeric_fields:
        value = getattr(state, name)
        if not _finite_number(value) or not 0.0 <= value <= 1.0:
            return f"invalid_actuator_{name}"
    capacities = (
        config.base.policy_capacity,
        config.base.support_capacity,
        config.base.audit_capacity,
    )
    for value, capacity in zip(
        (state.command_policy, state.command_support, state.command_audit), capacities
    ):
        if value > capacity:
            return "actuator_command_exceeds_capacity"
    for value, capacity in zip(
        (state.effective_policy, state.effective_support, state.effective_audit), capacities
    ):
        if value > capacity:
            return "actuator_delivery_exceeds_capacity"
    if not isinstance(state.transitions, tuple) or not isinstance(state.effects, tuple):
        return "actuator_queues_must_be_tuples"
    previous_due = state.last_step
    previous_request = -1
    for transition in state.transitions:
        if not isinstance(transition, feasibility.ModeTransition):
            return "invalid_transition_record"
        if (
            not _integer(transition.requested_at_step)
            or not _integer(transition.due_step)
            or not _valid_mode(transition.mode)
            or transition.requested_at_step > state.last_step
            or transition.due_step != transition.requested_at_step + config.base.actuation_delay_steps
            or transition.due_step <= state.last_step
            or transition.due_step < previous_due
            or transition.requested_at_step <= previous_request
        ):
            return "invalid_transition_queue"
        previous_due = transition.due_step
        previous_request = transition.requested_at_step
    previous_due = state.last_step
    previous_issue = -1
    for command in state.effects:
        if not isinstance(command, feasibility.EffectCommand):
            return "invalid_effect_record"
        if (
            not _integer(command.issued_at_step)
            or not _integer(command.due_step)
            or not _valid_mode(command.mode)
            or command.issued_at_step > state.last_step
            or command.due_step != command.issued_at_step + config.base.physical_effect_delay_steps
            or command.due_step <= state.last_step
            or command.due_step < previous_due
            or command.issued_at_step <= previous_issue
        ):
            return "invalid_effect_queue"
        if any(
            not _finite_number(value) or not 0.0 <= value <= 1.0
            for value in (command.policy, command.support, command.audit)
        ):
            return "invalid_effect_levels"
        previous_due = command.due_step
        previous_issue = command.issued_at_step
    if state.transitions:
        if state.requested_mode != state.transitions[-1].mode:
            return "requested_mode_does_not_match_transition_queue"
    elif state.requested_mode != state.active_mode:
        return "requested_mode_without_pending_transition"
    exact_pairs = (
        (observation.active_mode, state.active_mode),
        (observation.pending_mode, state.pending_mode),
        (observation.effective_policy, state.effective_policy),
        (observation.effective_support, state.effective_support),
        (observation.effective_audit, state.effective_audit),
    )
    if any(public != ledger for public, ledger in exact_pairs):
        return "observation_actuator_ledger_mismatch"
    return None


def _projection_observation_error(
    observation: feasibility.Observation,
    controller_state: feasibility.ControllerState,
    config: SustainedConfig,
) -> str | None:
    if not isinstance(controller_state, feasibility.ControllerState):
        return "invalid_controller_state_dto"
    if not _valid_mode(controller_state.authorized_mode):
        return "invalid_authorized_mode"
    history_error = _controller_history_error(controller_state)
    if history_error is not None:
        return history_error
    # A fresh history validates the current public DTO without incorrectly
    # treating an already-updated controller state as a replay.
    fresh = feasibility.ControllerState(authorized_mode=controller_state.authorized_mode)
    return feasibility._observation_error(observation, fresh, config.base)


def _controller_history_error(state: feasibility.ControllerState) -> str | None:
    """Corrupt history cannot contribute evidence or qualify a release."""
    for name in ("smoothed_trend", "previous_observed_pressure"):
        value = getattr(state, name)
        if value is not None and not _finite_number(value):
            return f"invalid_controller_{name}"
    if state.previous_observed_pressure is not None and state.previous_observed_pressure < 0:
        return "invalid_controller_previous_observed_pressure"
    return None


def _projection_trend(
    observation: feasibility.Observation,
    controller_state: feasibility.ControllerState,
    config: SustainedConfig,
) -> float:
    trend = controller_state.smoothed_trend
    if trend is None:
        trend = max(0.0035, config.base.base.base_pressure_growth * 0.50)
    # v0.3 owns the observation-history update before normal controller use.
    # The helper treats the supplied smoothed trend as the public state of
    # record; applying the current observation again would double-update it.
    return trend


def project_constant_mode(
    observation: feasibility.Observation,
    controller_state: feasibility.ControllerState,
    actuator_state: feasibility.ActuatorState,
    config: SustainedConfig,
    candidate_mode: int,
) -> Projection:
    """Project a constant request through an exact copy of the public ledger.

    The observed net trend is converted to a declared uncontrolled upper drift
    once, using the policy being delivered at the observation.  Every future
    pressure change subtracts only the configured lower policy gain.  No plant
    state or evaluator value is accepted by this API.
    """
    if not isinstance(config, SustainedConfig):
        raise TypeError("config must be a SustainedConfig")
    config.validate()
    if candidate_mode not in CANDIDATE_MODES or isinstance(candidate_mode, bool):
        raise ValueError("candidate_mode must be one of 0, 1, or 2")
    error = _projection_observation_error(observation, controller_state, config)
    if error is not None:
        raise ValueError(f"projection requires sufficient public evidence: {error}")
    actuator_error = _actuator_state_error(observation, actuator_state, config)
    if actuator_error is not None:
        raise ValueError(f"projection requires a valid full actuator ledger: {actuator_error}")

    trend = _projection_trend(observation, controller_state, config)
    uncontrolled_upper = (
        trend
        + config.policy_gain_upper * actuator_state.effective_policy
        + config.drift_margin
    )
    boundary = (
        min(observation.model_boundaries)
        - feasibility.MATCHED_ARM.structural_allowance
        - config.model_boundary_margin
    )
    pressure = observation.observed_pressure + config.pressure_error_bound
    if not all(_finite_number(value) for value in (uncontrolled_upper, boundary, pressure)):
        raise ValueError("nonfinite projection arithmetic")
    start_pressure = pressure
    balance = observation.remaining_budget
    projected_actuators = actuator_state
    projected_pressures: list[float] = []
    projected_changes: list[float] = []
    projected_policies: list[float] = []
    total_cost = 0.0
    first_pressure_violation: int | None = (
        observation.step if not pressure < boundary else None
    )

    for offset in range(config.forecast_steps):
        step = observation.step + offset
        projected_actuators = feasibility.request_mode(
            projected_actuators, candidate_mode, step, config.base
        )
        projected_actuators, ledger = feasibility.advance_actuators(
            projected_actuators, step, config.base, balance
        )
        balance = ledger.remaining_budget
        total_cost += ledger.step_cost
        delta = uncontrolled_upper - (
            config.policy_gain_lower * projected_actuators.effective_policy
        )
        pressure += delta
        if not all(_finite_number(value) for value in (delta, pressure, balance, total_cost)):
            raise ValueError("nonfinite projection arithmetic")
        projected_changes.append(delta)
        projected_pressures.append(pressure)
        projected_policies.append(projected_actuators.effective_policy)
        if first_pressure_violation is None and not pressure < boundary:
            first_pressure_violation = step

    final_window = projected_changes[-config.required_braking_steps :]
    braking_steps_met = sum(
        change <= config.max_projected_pressure_change for change in final_window
    )
    max_pressure = max((start_pressure, *projected_pressures))
    boundary_margin = boundary - max_pressure
    reasons: list[str] = []
    violation_steps: list[int] = []
    if first_pressure_violation is not None:
        reasons.append("pressure_not_strictly_below_declared_boundary")
        violation_steps.append(first_pressure_violation)
    if braking_steps_met != config.required_braking_steps:
        reasons.append("final_braking_window_not_met")
        violation_steps.append(
            observation.step + config.forecast_steps - config.required_braking_steps
        )
    if balance < config.terminal_budget_reserve:
        reasons.append("terminal_budget_reserve_not_met")
        violation_steps.append(observation.step + config.forecast_steps - 1)
    return Projection(
        mode=candidate_mode,
        max_pressure=max_pressure,
        boundary_margin=boundary_margin,
        final_budget=balance,
        total_cost=total_cost,
        braking_steps_met=braking_steps_met,
        passes=not reasons,
        first_violation_step=min(violation_steps) if violation_steps else None,
        reasons=tuple(reasons),
        projected_next_pressure_upper=projected_pressures[0],
        projected_pressures=tuple(projected_pressures),
        projected_pressure_changes=tuple(projected_changes),
        projected_effective_policies=tuple(projected_policies),
    )


def _insufficient_decision(
    base_decision: feasibility.Decision,
    requested_mode: int,
    reason: str,
) -> SustainedDecision:
    assessment = SustainedAssessment(
        status=STATUS_INSUFFICIENT_EVIDENCE,
        selected_plan_mode=None,
        projections=(),
    )
    return SustainedDecision(
        evidence_status=STATUS_INSUFFICIENT_EVIDENCE,
        requested_mode=requested_mode,
        status=STATUS_INSUFFICIENT_EVIDENCE,
        reason=reason,
        base_decision=base_decision,
        assessment=assessment,
    )


def sustained_decide(
    observation: feasibility.Observation,
    controller_state: feasibility.ControllerState,
    actuator_state: feasibility.ActuatorState,
    config: SustainedConfig,
) -> tuple[SustainedDecision, feasibility.ControllerState]:
    """Return one public-only receding-horizon request and updated v0.3 history."""
    if not isinstance(config, SustainedConfig):
        raise TypeError("config must be a SustainedConfig")
    config.validate()
    if not isinstance(controller_state, feasibility.ControllerState):
        raise TypeError("controller_state must be a ControllerState")
    if not _valid_mode(controller_state.authorized_mode):
        raise ValueError("invalid prior authorized mode")
    # Reject malformed structural history instead of coercing it into counters
    # or timestamps. -1 is permitted for the pre-first-observation test state.
    for name in ("release_streak", "normal_release_streak", "precaution_release_streak",
                 "unknown_steps", "unknown_streak"):
        if not _integer(getattr(controller_state, name)):
            raise ValueError(f"invalid controller history: {name}")
    for name in ("previous_observed_step", "last_decision_step"):
        value = getattr(controller_state, name)
        if value is not None and not _integer(value, -1):
            raise ValueError(f"invalid controller history: {name}")
    history_error = _controller_history_error(controller_state)
    if history_error is not None:
        # Do not overwrite corrupt numerical history with invented observations.
        # The caller must supply a valid history before decisions can resume.
        reason = f"hold_prior_authorization:{history_error}"
        base_decision = feasibility.Decision(
            evidence_status=STATUS_INSUFFICIENT_EVIDENCE,
            requested_mode=controller_state.authorized_mode,
            estimated_cr=None,
            response_status=STATUS_INSUFFICIENT_EVIDENCE,
            reason=reason,
        )
        held_state = replace(
            controller_state, release_streak=0, normal_release_streak=0,
            precaution_release_streak=0, unknown_steps=controller_state.unknown_steps + 1,
            unknown_streak=controller_state.unknown_streak + 1,
        )
        return (_insufficient_decision(base_decision, controller_state.authorized_mode, reason),
                held_state)
    # This call owns evidence validation, trend/history updates, and the v0.3
    # reserve floor.  Projection never replaces or weakens that base request.
    base_decision, base_state = feasibility.decide(
        observation, controller_state, config.base, "reserve"
    )
    if base_decision.evidence_status != "sufficient_evidence":
        return (
            _insufficient_decision(
                base_decision,
                base_decision.requested_mode,
                base_decision.reason,
            ),
            base_state,
        )

    actuator_error = _actuator_state_error(observation, actuator_state, config)
    if actuator_error is not None:
        # The pressure observation is consumed as public history, but an invalid
        # ledger cannot authorize a new request.  Restore the prior authorization
        # and mark the tick unknown rather than using a reconstructed queue.
        held_state = replace(
            base_state,
            authorized_mode=controller_state.authorized_mode,
            release_streak=0,
            normal_release_streak=0,
            precaution_release_streak=0,
            unknown_steps=base_state.unknown_steps + 1,
            unknown_streak=controller_state.unknown_streak + 1,
        )
        return (
            _insufficient_decision(
                base_decision,
                controller_state.authorized_mode,
                f"hold_prior_authorization:{actuator_error}",
            ),
            held_state,
        )

    projections = tuple(
        project_constant_mode(observation, base_state, actuator_state, config, mode)
        for mode in CANDIDATE_MODES
    )
    passing = [
        projection.mode
        for projection in projections
        if projection.passes and projection.mode >= base_decision.requested_mode
    ]
    if passing:
        selected = min(passing)
        status = STATUS_PLAN_FOUND
        final_request = selected
        reason = "lowest_passing_constant_mode_with_v03_reserve_floor"
    else:
        selected = None
        status = STATUS_NO_CANDIDATE
        final_request = max(base_decision.requested_mode, 2)
        reason = "loss_limiting_emergency_request_no_candidate_within_declared_model"

    if final_request > base_state.authorized_mode:
        base_state = replace(
            base_state,
            authorized_mode=final_request,
            release_streak=0,
            normal_release_streak=0,
            precaution_release_streak=0,
        )
    assessment = SustainedAssessment(
        status=status,
        selected_plan_mode=selected,
        projections=projections,
    )
    return SustainedDecision(
        evidence_status="sufficient_evidence",
        requested_mode=final_request,
        status=status,
        reason=reason,
        base_decision=base_decision,
        assessment=assessment,
    ), base_state


def _validate_environment(config: SustainedConfig, environment: legacy.Environment) -> None:
    if not isinstance(environment, legacy.Environment):
        raise TypeError("environment must be a legacy Environment")
    if len(environment.actors) != config.base.base.actors:
        raise ValueError("environment actor count does not match configuration")
    for name in ("pressure_noise", "observation_noise", "social_noise", "choice_draws"):
        if len(getattr(environment, name)) != config.base.base.horizon:
            raise ValueError(f"environment {name} length does not match horizon")
    if not _finite_number(environment.true_boundary) or environment.true_boundary <= 0.0:
        raise ValueError("true_boundary must be positive and finite")


def _projection_for_request(decision: SustainedDecision) -> Projection | None:
    for projection in decision.assessment.projections:
        if projection.mode == decision.requested_mode:
            return projection
    return None


def run_episode(
    config: SustainedConfig,
    environment: legacy.Environment,
    collect_trace: bool = False,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Run the sustained controller; hidden state is evaluator/plant-only."""
    if not isinstance(config, SustainedConfig):
        raise TypeError("config must be a SustainedConfig")
    config.validate()
    _validate_environment(config, environment)
    base_config = config.base
    model_boundaries = legacy.selected_boundaries(environment, feasibility.MATCHED_ARM)
    plant = feasibility.initial_plant(base_config)
    actuators = feasibility.ActuatorState()
    controller = feasibility.ControllerState()
    balance = base_config.initial_budget
    previous_capture = 0.0
    total_cost = 0.0
    min_justice = plant.justice
    finite_cr: list[float] = []
    projected_margins: list[float] = []
    projected_budgets: list[float] = []
    traces: list[dict[str, Any]] = []
    previous_projected_next_upper: float | None = None
    final_decision: SustainedDecision | None = None
    counts = {
        "budget_exhausted_steps": 0,
        "active_emergency_steps": 0,
        "effective_emergency_steps": 0,
        "requested_emergency_steps": 0,
        "requested_normal_steps": 0,
        "requested_precaution_steps": 0,
        "unknown_steps": 0,
        "max_unknown_streak": 0,
        "assessment_plan_found_steps": 0,
        "assessment_no_candidate_steps": 0,
        "assessment_insufficient_evidence_steps": 0,
        "no_candidate_boundary_steps": 0,
        "no_candidate_braking_steps": 0,
        "no_candidate_budget_steps": 0,
        "selected_plan_normal_steps": 0,
        "selected_plan_precaution_steps": 0,
        "selected_plan_emergency_steps": 0,
        "public_forecast_checked_steps": 0,
        "public_forecast_miss_steps": 0,
    }
    max_public_forecast_overshoot = 0.0

    for step in range(base_config.base.horizon):
        observation = feasibility._sensor_observation(
            plant,
            actuators,
            model_boundaries,
            environment.observation_bias,
            environment.observation_noise[step],
            previous_capture,
            balance,
            step,
            base_config,
        )
        forecast_checked = (
            previous_projected_next_upper is not None
            and _finite_number(observation.observed_pressure)
        )
        forecast_overshoot = (
            max(0.0, observation.observed_pressure - previous_projected_next_upper)
            if forecast_checked
            else 0.0
        )
        forecast_miss = forecast_checked and forecast_overshoot > 0.0
        counts["public_forecast_checked_steps"] += int(forecast_checked)
        counts["public_forecast_miss_steps"] += int(forecast_miss)
        max_public_forecast_overshoot = max(
            max_public_forecast_overshoot, forecast_overshoot
        )

        previous_observed = controller.previous_observed_pressure
        decision, controller = sustained_decide(
            observation, controller, actuators, config
        )
        final_decision = decision
        actuators = feasibility.request_mode(
            actuators, decision.requested_mode, step, base_config
        )
        actuators, ledger = feasibility.advance_actuators(
            actuators, step, base_config, balance
        )
        balance = ledger.remaining_budget
        public = replace(
            observation,
            remaining_budget=balance,
            active_mode=actuators.active_mode,
            pending_mode=actuators.pending_mode,
            effective_policy=actuators.effective_policy,
            effective_support=actuators.effective_support,
            effective_audit=actuators.effective_audit,
        )
        actions = feasibility.public_actor_actions(
            public,
            environment.actors,
            environment.choice_draws[step],
            base_config,
            previous_observed,
        )
        social = feasibility.public_social_update(
            public,
            actions,
            previous_observed,
            base_config,
            environment.social_noise[step],
        )
        pressure_before = plant.pressure
        plant = replace(
            plant,
            institution=social["institution"],
            trust=social["trust"],
            justice=social["justice"],
        )
        plant = feasibility.advance_plant(
            plant,
            actions,
            actuators,
            environment.true_boundary,
            environment.pressure_noise[step],
            environment.social_noise[step],
            step,
            base_config,
        )
        previous_capture = social["effective_capture"]
        total_cost += ledger.step_cost
        min_justice = min(min_justice, plant.justice)
        if decision.base_decision.estimated_cr is not None:
            finite_cr.append(decision.base_decision.estimated_cr)

        counts["budget_exhausted_steps"] += int(ledger.budget_exhausted)
        counts["active_emergency_steps"] += int(actuators.active_mode >= 2)
        counts["effective_emergency_steps"] += int(
            actuators.effective_mode >= 2
            and (
                actuators.effective_policy > 0.0
                or actuators.effective_support > 0.0
                or actuators.effective_audit > 0.0
            )
        )
        counts["requested_emergency_steps"] += int(decision.requested_mode >= 2)
        counts["requested_normal_steps"] += int(decision.requested_mode == 0)
        counts["requested_precaution_steps"] += int(decision.requested_mode == 1)
        counts["unknown_steps"] += int(decision.evidence_status == STATUS_INSUFFICIENT_EVIDENCE)
        counts["max_unknown_streak"] = max(
            counts["max_unknown_streak"], controller.unknown_streak
        )
        counts["assessment_plan_found_steps"] += int(decision.status == STATUS_PLAN_FOUND)
        counts["assessment_no_candidate_steps"] += int(decision.status == STATUS_NO_CANDIDATE)
        counts["assessment_insufficient_evidence_steps"] += int(
            decision.status == STATUS_INSUFFICIENT_EVIDENCE
        )
        if decision.assessment.selected_plan_mode is not None:
            selected_key = (
                "selected_plan_normal_steps",
                "selected_plan_precaution_steps",
                "selected_plan_emergency_steps",
            )[decision.assessment.selected_plan_mode]
            counts[selected_key] += 1

        if decision.status == STATUS_NO_CANDIDATE:
            emergency_projection = next(
                (
                    projection
                    for projection in decision.assessment.projections
                    if projection.mode == 2
                ),
                None,
            )
            if emergency_projection is not None:
                rejection_reasons = set(emergency_projection.reasons)
                counts["no_candidate_boundary_steps"] += int(
                    "pressure_not_strictly_below_declared_boundary" in rejection_reasons
                )
                counts["no_candidate_braking_steps"] += int(
                    "final_braking_window_not_met" in rejection_reasons
                )
                counts["no_candidate_budget_steps"] += int(
                    "terminal_budget_reserve_not_met" in rejection_reasons
                )

        request_projection = _projection_for_request(decision)
        if request_projection is not None:
            projected_margins.append(request_projection.boundary_margin)
            projected_budgets.append(request_projection.final_budget)
            previous_projected_next_upper = request_projection.projected_next_pressure_upper
        else:
            previous_projected_next_upper = None

        if collect_trace:
            traces.append({
                "t": step,
                "trigger": TRIGGER,
                "episode": environment.episode,
                "true_boundary": environment.true_boundary,
                "pressure_before": pressure_before,
                "pressure": plant.pressure,
                "observed_pressure": observation.observed_pressure,
                "observed_at_step": observation.observed_at_step,
                "evidence_status": decision.evidence_status,
                "reason": decision.reason,
                "response_status": decision.base_decision.response_status,
                "estimated_cr": decision.base_decision.estimated_cr,
                "estimated_response_steps": decision.base_decision.estimated_response_steps,
                "boundary_uncertainty": decision.base_decision.boundary_uncertainty,
                "observed_trend": decision.base_decision.observed_trend,
                "assessment_status": decision.status,
                "selected_plan_mode": decision.assessment.selected_plan_mode,
                "execution_semantics": decision.execution_semantics,
                "projection_mode": request_projection.mode if request_projection else None,
                "projected_max_pressure": (
                    request_projection.max_pressure if request_projection else None
                ),
                "projected_boundary_margin": (
                    request_projection.boundary_margin if request_projection else None
                ),
                "projected_final_budget": (
                    request_projection.final_budget if request_projection else None
                ),
                "projected_total_cost": (
                    request_projection.total_cost if request_projection else None
                ),
                "projected_braking_steps_met": (
                    request_projection.braking_steps_met if request_projection else None
                ),
                "projection_passes": (
                    int(request_projection.passes) if request_projection else None
                ),
                "projection_reasons": (
                    "|".join(request_projection.reasons) if request_projection else None
                ),
                "projected_next_pressure_upper": (
                    request_projection.projected_next_pressure_upper
                    if request_projection else None
                ),
                "public_forecast_checked": int(forecast_checked),
                "public_forecast_miss": int(forecast_miss),
                "public_forecast_overshoot": forecast_overshoot,
                "requested_mode": decision.requested_mode,
                "pending_mode": actuators.pending_mode,
                "pending_due_step": actuators.pending_due_step,
                "pending_transition_count": len(actuators.transitions),
                "active_mode": actuators.active_mode,
                "effective_mode": actuators.effective_mode,
                "command_policy": actuators.command_policy,
                "command_support": actuators.command_support,
                "command_audit": actuators.command_audit,
                "effective_policy": actuators.effective_policy,
                "effective_support": actuators.effective_support,
                "effective_audit": actuators.effective_audit,
                "pending_effect_count": len(actuators.effects),
                "remaining_budget": balance,
                "step_cost": ledger.step_cost,
                "nominal_cost": ledger.nominal_cost,
                "curtailment_factor": ledger.curtailment_factor,
                "budget_exhausted": int(ledger.budget_exhausted),
                "irreversible": int(plant.irreversible),
                "biosphere": plant.biosphere,
                "institution": plant.institution,
                "trust": plant.trust,
                "justice": plant.justice,
                "release_streak": controller.release_streak,
                "normal_release_streak": controller.normal_release_streak,
                "precaution_release_streak": controller.precaution_release_streak,
                "unknown_streak": controller.unknown_streak,
                "attempted_capture": actions["attempted_capture"],
                "effective_capture": social["effective_capture"],
                "cooperation_rate": actions["cooperation_rate"],
                "defective_rate": actions["defective_rate"],
                "backlash": social["backlash"],
                "performative_gap": social["performative_gap"],
                "perceived_improvement": social["perceived_improvement"],
            })

    assert final_decision is not None  # legacy validation guarantees a positive horizon
    metrics = {
        "trigger": TRIGGER,
        "episode": environment.episode,
        "environment_seed": environment.seed,
        "true_boundary": environment.true_boundary,
        "irreversible_entry": int(plant.irreversible),
        "justice_floor_violation": int(
            min_justice <= base_config.base.irreversible_justice_floor
        ),
        "first_irreversible_step": (
            plant.irreversible_step if plant.irreversible_step is not None else -1
        ),
        "final_pressure": plant.pressure,
        "final_biosphere": plant.biosphere,
        "final_institution": plant.institution,
        "final_trust": plant.trust,
        "final_justice": plant.justice,
        "total_cost": total_cost,
        "remaining_budget": balance,
        "min_justice": min_justice,
        "min_estimated_cr": min(finite_cr) if finite_cr else None,
        "final_active_mode": actuators.active_mode,
        "final_effective_mode": actuators.effective_mode,
        "min_projected_boundary_margin": (
            min(projected_margins) if projected_margins else None
        ),
        "min_projected_final_budget": (
            min(projected_budgets) if projected_budgets else None
        ),
        "max_public_forecast_overshoot": max_public_forecast_overshoot,
        "final_assessment_status": final_decision.status,
        "final_selected_plan_mode": final_decision.assessment.selected_plan_mode,
        **counts,
    }
    return metrics, traces
