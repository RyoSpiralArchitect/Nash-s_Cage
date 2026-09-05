"""F0 v0.3 experiment with a public-input controller and paid delayed actuators.

This is an uncalibrated structural toy, not a recovery-probability estimator,
forecast, feasibility certificate, or policy recommendation.  The v0.2 module
is imported only for its immutable configuration, actor/environment types,
sampling, and pure numeric primitives; none of its truth-fed control loop runs.

Within a tick: observe the pre-step plant, decide, enqueue a requested mode,
activate due requests, slew commands, deliver due physical targets subject to
the budget, then advance actors/social state and the physical plant.  A mode
requested at t cannot become active before t+A, and its command cannot affect
the plant before t+A+E.  Queues are FIFO; unchanged requests retain their dates.

Actuator targets are not prepaid effects.  Actual delivered intensity is paid
at each tick, and all channels are proportionally curtailed if funds are short.
Slew limits apply to commands.  Forced affordability shutdown can reduce actual
output faster than the commanded down-slew: no unpaid output is grandfathered.
Initial delivered and command intensities are zero, including audit.

Institution/trust/justice, model boundaries, actuator state, and the budget are
explicitly assumed public exact telemetry.  Pressure is a noisy, potentially
manipulated sensor observation.  True boundary access is confined to the plant
and evaluator; neither controllers nor actor/social feedback receive it.
"""

from __future__ import annotations

import dataclasses
import json
import math
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Mapping, Sequence

from . import rvcim_sim as legacy

VERSION = "0.3.0-experimental"
SCHEMA_VERSION = 1
CLAIM_LEVEL = "F0"
CLAIM_BOUNDARY = (
    "Uncalibrated structural experiment only; no recovery probability, empirical "
    "validation, feasibility certificate, prediction, or policy recommendation."
)
TRIGGERS = ("threshold", "threshold_hysteresis", "reserve")
MATCHED_ARM = legacy.ARM_SPECS["full_rvcim"]
DEFAULT_BASE_CONFIG = Path(__file__).resolve().parent / "configs" / "minimal.json"
ConfigError = legacy.ConfigError


def _finite_number(value: Any) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(value)
    )


def _integer(value: Any, minimum: int = 0) -> bool:
    return not isinstance(value, bool) and isinstance(value, int) and value >= minimum


@dataclass(frozen=True)
class FeasibilityConfig:
    """All added defaults are synthetic assumptions frozen before comparisons."""

    base: legacy.ModelConfig
    schema_version: int = SCHEMA_VERSION
    actuation_delay_steps: int = 3
    physical_effect_delay_steps: int = 4
    policy_capacity: float = 1.0
    support_capacity: float = 1.0
    audit_capacity: float = 1.0
    max_policy_slew: float = 0.12
    max_support_slew: float = 0.12
    max_audit_slew: float = 0.12
    initial_budget: float = 4.0
    policy_cost: float = 0.06
    support_cost: float = 0.03
    audit_cost: float = 0.02
    uncertainty_limit: float = 0.30
    release_margin: float = 11.0
    threshold_release_margin: float = 0.05
    release_consecutive_steps: int = 3
    max_observation_age_steps: int = 1
    observation_missing_every: int = 0

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        if not isinstance(self.base, legacy.ModelConfig):
            raise ConfigError("base must be a legacy ModelConfig")
        # Reparse to enforce strict field/type checks even for dataclass.replace.
        legacy.ModelConfig.from_mapping(self.base.to_mapping())
        integer_fields = (
            "schema_version", "actuation_delay_steps", "physical_effect_delay_steps",
            "release_consecutive_steps", "max_observation_age_steps",
            "observation_missing_every",
        )
        for name in integer_fields:
            if not _integer(getattr(self, name)):
                raise ConfigError(f"{name} must be a nonnegative integer")
        if self.schema_version != SCHEMA_VERSION:
            raise ConfigError(f"schema_version must equal {SCHEMA_VERSION}")
        if self.release_consecutive_steps < 1:
            raise ConfigError("release_consecutive_steps must be at least 1")
        numeric_fields = {
            item.name for item in dataclasses.fields(self)
        } - set(integer_fields) - {"base"}
        for name in numeric_fields:
            value = getattr(self, name)
            if not _finite_number(value) or value < 0.0:
                raise ConfigError(f"{name} must be a finite nonnegative number")
        for name in (
            "policy_capacity", "support_capacity", "audit_capacity",
            "max_policy_slew", "max_support_slew", "max_audit_slew",
        ):
            if getattr(self, name) > 1.0:
                raise ConfigError(f"{name} must lie in [0, 1]")
        for name in ("policy_cost", "support_cost", "audit_cost"):
            if getattr(self, name) <= 0.0:
                raise ConfigError(f"{name} must be positive: nonzero actuators are not free")
        if self.threshold_release_margin >= self.base.nominal_trigger_level:
            raise ConfigError("threshold_release_margin must be below nominal_trigger_level")
        if self.base.boundary_mean <= self.base.boundary_spread:
            raise ConfigError("the sampled true boundary range must be strictly positive")
        for item in dataclasses.fields(self.base):
            name = item.name
            if name.endswith("_std") and getattr(self.base, name) < 0.0:
                raise ConfigError(f"base.{name} cannot be negative")
        for name in (
            "base_pressure_growth", "sink_strength", "biosphere_damage_rate",
            "restoration_rate", "manipulation_scale", "actor_baseline_pressure",
            "abatement_effect", "policy_effect", "damage_payoff_scale",
            "institution_friction", "institution_capture_damage",
            "institution_policy_gain", "trust_gap_damage", "trust_backlash_damage",
            "justice_burden_damage", "justice_recovery_rate", "performative_gap_kappa",
            "precaution_margin",
        ):
            if getattr(self.base, name) < 0.0:
                raise ConfigError(f"base.{name} cannot be negative")

    @classmethod
    def from_mapping(
        cls, payload: Mapping[str, Any], base: legacy.ModelConfig | None = None
    ) -> "FeasibilityConfig":
        if not isinstance(payload, Mapping):
            raise ConfigError("configuration root must be a JSON object")
        values = dict(payload)
        if "base" in values:
            if base is not None:
                raise ConfigError("provide inline base or base_path, not both")
            nested = values.pop("base")
            if not isinstance(nested, Mapping):
                raise ConfigError("base must be a JSON object")
            base = legacy.ModelConfig.from_mapping(nested)
        if base is None:
            raise ConfigError("base configuration must be supplied")
        required = {item.name for item in dataclasses.fields(cls)} - {"base"}
        unknown = sorted(set(values) - required)
        missing = sorted(required - set(values))
        if unknown:
            raise ConfigError(f"unknown feasibility configuration keys: {', '.join(unknown)}")
        if missing:
            raise ConfigError(f"missing feasibility configuration keys: {', '.join(missing)}")
        return cls(base=base, **values)

    def to_mapping(self) -> dict[str, Any]:
        """Return a self-contained resolved mapping, including the legacy base."""
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


def load_config(path: Path, base_path: Path | None = None) -> FeasibilityConfig:
    """Read a strict wrapper, or a self-contained resolved mapping.

    A wrapper's base defaults to the fixed module-relative minimal.json, never
    the caller's working directory.  It may be overridden explicitly by path.
    Paths from untrusted JSON are not evaluated.
    """
    try:
        payload = json.loads(
            Path(path).read_text(encoding="utf-8"), object_pairs_hook=_unique_json_object
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ConfigError(f"cannot read feasibility configuration {path}: {exc}") from exc
    if not isinstance(payload, Mapping):
        raise ConfigError("configuration root must be a JSON object")
    if "base" in payload:
        if base_path is not None:
            raise ConfigError("provide inline base or base_path, not both")
        return FeasibilityConfig.from_mapping(payload)
    base = legacy.load_config(Path(base_path) if base_path is not None else DEFAULT_BASE_CONFIG)
    return FeasibilityConfig.from_mapping(payload, base=base)


@dataclass(frozen=True)
class Observation:
    """Public-input DTO; absent or invalid required telemetry is not safety."""

    step: int
    observed_pressure: float | None
    model_boundaries: tuple[float, ...]
    observed_at_step: int | None = None
    institution: float | None = None
    trust: float | None = None
    justice: float | None = None
    remaining_budget: float | None = None
    active_mode: int | None = None
    pending_mode: int | None = None
    effective_policy: float | None = None
    effective_support: float | None = None
    effective_audit: float | None = None


@dataclass(frozen=True)
class ControllerState:
    authorized_mode: int = 0
    release_streak: int = 0
    normal_release_streak: int = 0
    precaution_release_streak: int = 0
    previous_observed_pressure: float | None = None
    previous_observed_step: int | None = None
    smoothed_trend: float | None = None
    last_decision_step: int | None = None
    unknown_steps: int = 0
    unknown_streak: int = 0


@dataclass(frozen=True)
class Decision:
    evidence_status: str
    requested_mode: int
    estimated_cr: float | None
    response_status: str
    reason: str
    estimated_response_steps: float | None = None
    boundary_uncertainty: float | None = None
    observed_trend: float | None = None


def _valid_mode(mode: Any) -> bool:
    return _integer(mode) and mode in legacy.MODE_NAMES


def _observation_error(
    observation: Observation, state: ControllerState, config: FeasibilityConfig
) -> str | None:
    if not isinstance(observation, Observation):
        return "invalid_observation_dto"
    if not _integer(observation.step):
        return "invalid_step"
    if state.last_decision_step is not None and observation.step <= state.last_decision_step:
        return "nonmonotonic_observation_step"
    if not _integer(observation.observed_at_step):
        return "missing_timestamp"
    age = observation.step - observation.observed_at_step
    if age < 0 or age > config.max_observation_age_steps:
        return "stale_or_future_observation"
    if (
        state.previous_observed_step is not None
        and observation.observed_at_step <= state.previous_observed_step
    ):
        return "replayed_observation"
    if not _finite_number(observation.observed_pressure) or observation.observed_pressure < 0:
        return "missing_or_invalid_pressure"
    if not isinstance(observation.model_boundaries, tuple) or not observation.model_boundaries:
        return "missing_or_invalid_model_boundaries"
    if any(not _finite_number(x) or x <= 0 for x in observation.model_boundaries):
        return "missing_or_invalid_model_boundaries"
    for name in (
        "institution", "trust", "justice", "effective_policy", "effective_support",
        "effective_audit",
    ):
        value = getattr(observation, name)
        if not _finite_number(value) or not 0 <= value <= 1:
            return f"missing_or_invalid_{name}"
    if not _finite_number(observation.remaining_budget) or observation.remaining_budget < 0:
        return "missing_or_invalid_remaining_budget"
    if not _valid_mode(observation.active_mode):
        return "missing_or_invalid_active_mode"
    if observation.pending_mode is not None and not _valid_mode(observation.pending_mode):
        return "invalid_pending_mode"
    return None


def response_proxy(
    observation: Observation, config: FeasibilityConfig
) -> tuple[float | None, str]:
    """Declared latency-to-emergency-command proxy, not time to recovery.

    It checks the emergency policy target against capacity, slew and the funds
    for one emergency operating tick.  It does not establish that the target
    could reverse drift, survive an uncertain boundary, or remain funded.
    """
    target = MATCHED_ARM.policy_targets[2]
    if config.policy_capacity < target:
        return None, "insufficient_capacity"
    distance = max(0.0, target - observation.effective_policy)
    if distance > 0.0 and config.max_policy_slew <= 0.0:
        return None, "insufficient_slew"
    operating_cost = (
        target * config.policy_cost
        + min(config.support_capacity, MATCHED_ARM.support_targets[2]) * config.support_cost
        + min(config.audit_capacity, MATCHED_ARM.audit + 0.28) * config.audit_cost
    )
    if observation.remaining_budget < operating_cost:
        return None, "insufficient_budget"
    ramp_steps = math.ceil(distance / config.max_policy_slew) if distance > 0.0 else 0
    # The first slew increment is issued on the activation tick itself.
    response = config.actuation_delay_steps + config.physical_effect_delay_steps
    response += max(0, ramp_steps - 1)
    return float(response), "available"


def decide(
    observation: Observation,
    controller_state: ControllerState,
    config: FeasibilityConfig,
    trigger: str,
) -> tuple[Decision, ControllerState]:
    """Pure controller: only public observation, public history, model and ledger.

    Missing evidence holds the last authorized request and clears a release
    streak.  It is neither a new escalation nor certification that holding is
    safe.  Plain threshold release is immediate and pressure-only.  Threshold
    hysteresis counts normal- and precaution-qualified observations separately;
    one target cannot borrow another target's streak.  Reserve uses a CR margin
    and uncertainty with its existing release counter.
    """
    if trigger not in TRIGGERS:
        raise ValueError(f"unknown trigger: {trigger!r}")
    if not isinstance(controller_state, ControllerState):
        raise TypeError("controller_state must be a ControllerState")
    if not _valid_mode(controller_state.authorized_mode):
        raise ValueError("invalid prior authorized mode")
    error = _observation_error(observation, controller_state, config)
    if error is not None:
        state = replace(
            controller_state,
            release_streak=0,
            normal_release_streak=0,
            precaution_release_streak=0,
            unknown_steps=controller_state.unknown_steps + 1,
            unknown_streak=controller_state.unknown_streak + 1,
            last_decision_step=(
                max(observation.step, controller_state.last_decision_step or 0)
                if isinstance(observation, Observation) and _integer(observation.step)
                else controller_state.last_decision_step
            ),
        )
        return Decision(
            evidence_status="insufficient_evidence",
            requested_mode=controller_state.authorized_mode,
            estimated_cr=None,
            response_status="insufficient_evidence",
            reason=f"hold_prior_authorization:{error}",
        ), state

    observed = observation.observed_pressure
    previous = controller_state.previous_observed_pressure
    previous_step = controller_state.previous_observed_step
    trend = controller_state.smoothed_trend
    if trend is None:
        trend = max(0.0035, config.base.base_pressure_growth * 0.50)
    if previous is not None and previous_step is not None:
        delta = (observed - previous) / (observation.observed_at_step - previous_step)
        trend = 0.70 * trend + 0.30 * delta
    drift = max(0.0035, trend)
    uncertainty = max(observation.model_boundaries) - min(observation.model_boundaries)
    response, response_status = response_proxy(observation, config)
    exit_time = max(
        0.0,
        (min(observation.model_boundaries) - MATCHED_ARM.structural_allowance - observed)
        / drift,
    )
    reserve = None if response is None else exit_time - response
    if trigger in ("threshold", "threshold_hysteresis"):
        if observed >= config.base.nominal_emergency_level:
            candidate = 2
        elif observed >= config.base.nominal_trigger_level:
            candidate = 1
        else:
            candidate = 0
        reason = "pressure_threshold"
    elif reserve is None:
        candidate = 2
        reason = f"loss_limiting_request:{response_status}"
    elif reserve <= 0.0:
        candidate, reason = 2, "nonpositive_reserve_proxy"
    elif reserve <= config.base.precaution_margin:
        candidate, reason = 1, "small_reserve_proxy"
    elif uncertainty >= config.uncertainty_limit:
        candidate, reason = 1, "model_disagreement"
    else:
        candidate, reason = 0, "reserve_proxy_above_margin"

    authorized = controller_state.authorized_mode
    streak = 0
    normal_streak = 0
    precaution_streak = 0
    if candidate < authorized and trigger == "threshold_hysteresis":
        # Each potential lower target has its own qualifying predicate.  In
        # particular, pressure below the nominal normal threshold may still
        # qualify for precaution release without yet qualifying for normal.
        if observed <= config.base.nominal_trigger_level - config.threshold_release_margin:
            normal_streak = controller_state.normal_release_streak + 1
        if (
            authorized > 1
            and observed <= config.base.nominal_emergency_level - config.threshold_release_margin
        ):
            precaution_streak = controller_state.precaution_release_streak + 1
        qualified = [
            target for target, count in ((0, normal_streak), (1, precaution_streak))
            if target < authorized and count >= config.release_consecutive_steps
        ]
        if qualified:
            candidate = min(qualified)
            reason = "configured_release"
            # Keep independently accumulated normal evidence across 2 -> 1;
            # it still needs N genuinely normal-qualified observations.  Clear
            # counters for targets that are no longer below the authorized mode.
            if candidate == 0:
                normal_streak = 0
            if candidate <= 1:
                precaution_streak = 0
        else:
            candidate = authorized
            reason = (
                "release_pending" if normal_streak or precaution_streak
                else "release_margin_not_met"
            )
        # Compatibility/diagnostic summary only: threshold hysteresis never
        # reads this aggregate to authorize either lower target.
        streak = max(normal_streak, precaution_streak)
    elif candidate < authorized and trigger == "reserve":
        release_ok = (
            reserve is not None and reserve >= config.release_margin
            and uncertainty < config.uncertainty_limit
        )
        streak = controller_state.release_streak + 1 if release_ok else 0
        if streak < config.release_consecutive_steps:
            candidate = authorized
            reason = "release_pending" if release_ok else "release_margin_not_met"
        else:
            reason = "configured_release"
            streak = 0
    state = replace(
        controller_state,
        authorized_mode=candidate,
        release_streak=streak,
        normal_release_streak=normal_streak,
        precaution_release_streak=precaution_streak,
        previous_observed_pressure=observed,
        previous_observed_step=observation.observed_at_step,
        smoothed_trend=trend,
        last_decision_step=observation.step,
        unknown_streak=0,
    )
    return Decision(
        evidence_status="sufficient_evidence",
        requested_mode=candidate,
        estimated_cr=reserve,
        response_status=response_status,
        reason=reason,
        estimated_response_steps=response,
        boundary_uncertainty=uncertainty,
        observed_trend=trend,
    ), state


@dataclass(frozen=True)
class ModeTransition:
    requested_at_step: int
    due_step: int
    mode: int


@dataclass(frozen=True)
class EffectCommand:
    issued_at_step: int
    due_step: int
    mode: int
    policy: float
    support: float
    audit: float


@dataclass(frozen=True)
class ActuatorState:
    requested_mode: int = 0
    active_mode: int = 0
    effective_mode: int = 0
    command_policy: float = 0.0
    command_support: float = 0.0
    command_audit: float = 0.0
    effective_policy: float = 0.0
    effective_support: float = 0.0
    effective_audit: float = 0.0
    transitions: tuple[ModeTransition, ...] = ()
    effects: tuple[EffectCommand, ...] = ()
    last_step: int = -1

    @property
    def pending_mode(self) -> int | None:
        return self.transitions[0].mode if self.transitions else None

    @property
    def pending_due_step(self) -> int | None:
        return self.transitions[0].due_step if self.transitions else None


@dataclass(frozen=True)
class ActuationResult:
    step_cost: float
    nominal_cost: float
    curtailment_factor: float
    remaining_budget: float
    budget_exhausted: bool


def request_mode(
    state: ActuatorState, requested_mode: int, step: int, config: FeasibilityConfig
) -> ActuatorState:
    """Enqueue a changed request; do not reset a matching pending transition."""
    if not _integer(step) or step < state.last_step:
        raise ValueError("request step must be nonnegative and not precede actuator state")
    if not _valid_mode(requested_mode):
        raise ValueError("requested_mode must be a known integer mode")
    if requested_mode == state.requested_mode:
        return state
    transition = ModeTransition(step, step + config.actuation_delay_steps, requested_mode)
    if state.transitions and transition.due_step < state.transitions[-1].due_step:
        raise ValueError("mode transitions must remain FIFO")
    return replace(
        state, requested_mode=requested_mode, transitions=state.transitions + (transition,)
    )


def _slew(previous: float, target: float, maximum: float) -> float:
    return previous + max(-maximum, min(maximum, target - previous))


def advance_actuators(
    state: ActuatorState, step: int, config: FeasibilityConfig, remaining_budget: float
) -> tuple[ActuatorState, ActuationResult]:
    """Advance one tick; costs apply to actual current delivery, not requests."""
    if not _integer(step) or step <= state.last_step:
        raise ValueError("advance step must be nonnegative and strictly increasing")
    if not _finite_number(remaining_budget) or remaining_budget < 0.0:
        raise ValueError("remaining_budget must be finite and nonnegative")
    transitions = list(state.transitions)
    active = state.active_mode
    while transitions and transitions[0].due_step <= step:
        active = transitions.pop(0).mode
    if not _valid_mode(active):
        raise ValueError("invalid active mode")
    policy = _slew(
        state.command_policy, min(config.policy_capacity, MATCHED_ARM.policy_targets[active]),
        config.max_policy_slew,
    )
    support = _slew(
        state.command_support, min(config.support_capacity, MATCHED_ARM.support_targets[active]),
        config.max_support_slew,
    )
    audit = _slew(
        state.command_audit,
        min(config.audit_capacity, MATCHED_ARM.audit + (0.10, 0.18, 0.28, 0.34)[active]),
        config.max_audit_slew,
    )
    effects = list(state.effects)
    command = EffectCommand(
        step, step + config.physical_effect_delay_steps, active, policy, support, audit
    )
    if effects and command.due_step < effects[-1].due_step:
        raise ValueError("physical commands must remain FIFO")
    effects.append(command)
    delivered = (state.effective_policy, state.effective_support, state.effective_audit)
    effective_mode = state.effective_mode
    while effects and effects[0].due_step <= step:
        due = effects.pop(0)
        delivered = (due.policy, due.support, due.audit)
        effective_mode = due.mode
    delivered = tuple(
        max(0.0, min(value, capacity))
        for value, capacity in zip(
            delivered, (config.policy_capacity, config.support_capacity, config.audit_capacity)
        )
    )
    nominal_cost = sum(
        level * cost for level, cost in zip(
            delivered, (config.policy_cost, config.support_cost, config.audit_cost)
        )
    )
    scale = min(1.0, remaining_budget / nominal_cost) if nominal_cost > 0.0 else 1.0
    delivered = tuple(level * scale for level in delivered)
    cost = sum(
        level * unit for level, unit in zip(
            delivered, (config.policy_cost, config.support_cost, config.audit_cost)
        )
    )
    # Bound a possible final-ulp rounding excess without allowing an overdraft.
    cost = min(remaining_budget, cost)
    balance = max(0.0, remaining_budget - cost)
    if scale < 1.0:
        balance = 0.0
        cost = remaining_budget
    next_state = replace(
        state, active_mode=active, effective_mode=effective_mode,
        command_policy=policy, command_support=support, command_audit=audit,
        effective_policy=delivered[0], effective_support=delivered[1],
        effective_audit=delivered[2], transitions=tuple(transitions), effects=tuple(effects),
        last_step=step,
    )
    return next_state, ActuationResult(
        step_cost=cost, nominal_cost=nominal_cost, curtailment_factor=scale,
        remaining_budget=balance, budget_exhausted=balance <= 0.0,
    )


@dataclass(frozen=True)
class PlantState:
    pressure: float
    biosphere: float
    institution: float
    trust: float
    justice: float
    irreversible: bool = False
    irreversible_step: int | None = None


def initial_plant(config: FeasibilityConfig) -> PlantState:
    base = config.base
    return PlantState(
        base.pressure_initial, base.biosphere_initial, base.institution_initial,
        base.trust_initial, base.justice_initial,
    )


def public_actor_actions(
    observation: Observation,
    actors: Sequence[legacy.ActorProfile],
    draws: Sequence[float],
    config: FeasibilityConfig,
    last_observed_pressure: float | None = None,
) -> dict[str, float]:
    """Actor choices use perceived pressure and public telemetry, not plant truth."""
    if len(actors) != len(draws):
        raise ValueError("one choice draw is required for every actor")
    pressure = observation.observed_pressure
    if not _finite_number(pressure):
        pressure = last_observed_pressure if _finite_number(last_observed_pressure) else 0.0
    policy, support, audit = (
        observation.effective_policy, observation.effective_support, observation.effective_audit
    )
    trust, justice = observation.trust, observation.justice
    arm, base = MATCHED_ARM, config.base
    choices = []
    for actor, draw in zip(actors, draws):
        cooperation_gain = (
            1.05 * support * (1.0 - 0.35 * actor.transition_cost)
            + 0.42 * trust * actor.horizon
            + base.damage_payoff_scale * 0.35 * actor.exposure * pressure
            + 1.10 * policy * arm.coupling * (0.35 + 0.65 * audit)
        )
        burden = (
            0.82 * policy * actor.transition_cost * actor.dependence * (1.0 - 0.72 * support)
        )
        defection_gain = (
            0.72 * actor.dependence + 0.55 * actor.externalization
            + 0.32 * (1.0 - actor.horizon)
            + 0.24 * actor.greenwash_ability * arm.monitoring * (1.0 - audit)
        )
        legitimacy = 0.24 * justice * (1.0 - actor.dependence)
        cooperate = draw < legacy.logistic(
            (cooperation_gain + legitimacy - burden - defection_gain)
            / base.cooperation_temperature
        )
        choices.append((actor, cooperate))
    defective = sum(actor.power for actor, cooperate in choices if not cooperate)
    burdens = [
        policy * actor.dependence * actor.transition_cost * (1.0 - 0.78 * support)
        for actor, _ in choices
    ]
    return {
        "defective_rate": legacy.clamp(defective),
        "cooperation_rate": legacy.clamp(1.0 - defective),
        "emission_load": sum(
            actor.power * (0.50 + 0.80 * actor.dependence)
            for actor, cooperate in choices if not cooperate
        ),
        "abatement": sum(
            actor.power * (0.55 + 0.45 * (1.0 - actor.transition_cost))
            for actor, cooperate in choices if cooperate
        ),
        "restoration": sum(
            actor.power * (0.20 + 0.40 * actor.exposure)
            for actor, cooperate in choices if cooperate
        ),
        "attempted_capture": sum(
            actor.power * actor.capture_ability * (0.45 + actor.dependence)
            * (0.45 + policy) * (0.55 + actor.power * len(actors))
            for actor, cooperate in choices if not cooperate
        ),
        "symbolic": sum(
            actor.power * (
                0.12 if cooperate else
                0.22 + 0.78 * actor.greenwash_ability * arm.monitoring * (1.0 - audit)
            ) for actor, cooperate in choices
        ),
        "burden_concentration": max(
            0.0, legacy.percentile(burdens, 0.90) - legacy.percentile(burdens, 0.20)
        ),
    }


def public_social_update(
    observation: Observation,
    actions: Mapping[str, float],
    last_observed_pressure: float | None,
    config: FeasibilityConfig,
    noise: float,
) -> dict[str, float]:
    """No truth-mode labels, false positives/negatives or verified improvement."""
    arm, base = MATCHED_ARM, config.base
    policy, support, audit = (
        observation.effective_policy, observation.effective_support, observation.effective_audit
    )
    defense = (
        arm.anti_capture + 1.30 * audit + arm.function_separation
        + arm.justice_buffer * observation.justice + 0.35 * policy * audit
    )
    capture = actions["attempted_capture"] / (1.0 + defense)
    backlash = legacy.clamp(
        actions["burden_concentration"] * (1.0 - 0.55 * arm.justice_buffer)
        + 0.20 * max(0.0, policy - support)
        + 0.10 * policy * (1.0 - observation.justice)
        - 0.18 * support * arm.justice_buffer
    )
    perceived_improvement = 0.0
    if _finite_number(observation.observed_pressure) and _finite_number(last_observed_pressure):
        perceived_improvement = max(0.0, last_observed_pressure - observation.observed_pressure)
    gap = actions["symbolic"] - base.performative_gap_kappa * perceived_improvement
    fairness = support * (0.35 + 0.65 * arm.justice_buffer)
    justice = legacy.clamp(
        observation.justice + base.justice_recovery_rate * fairness
        - base.justice_burden_damage * actions["burden_concentration"]
        - 0.020 * capture - 0.018 * backlash + 0.15 * noise
    )
    trust = legacy.clamp(
        observation.trust + 0.022 * fairness - base.trust_gap_damage * max(0.0, gap)
        - base.trust_backlash_damage * backlash - 0.022 * capture + 0.10 * noise
    )
    institution = legacy.clamp(
        observation.institution + base.institution_policy_gain * audit * (trust - 0.30)
        - base.institution_friction - base.institution_capture_damage * capture
        - 0.030 * backlash + 0.08 * noise
    )
    return {
        "institution": institution, "trust": trust, "justice": justice,
        "effective_capture": capture, "backlash": backlash,
        "perceived_improvement": perceived_improvement, "performative_gap": gap,
    }


def advance_plant(
    state: PlantState,
    actions: Mapping[str, float],
    actuators: ActuatorState,
    true_boundary: float,
    pressure_noise: float,
    social_noise: float,
    step: int,
    config: FeasibilityConfig,
) -> PlantState:
    """Physical law and irreversible-entry evaluator; hidden boundary lives here."""
    if not _finite_number(true_boundary) or true_boundary <= 0.0:
        raise ValueError("true_boundary must be positive and finite")
    base = config.base
    policy, support = actuators.effective_policy, actuators.effective_support
    sink = base.sink_strength * state.biosphere * max(0.12, 1.0 - 0.55 * state.pressure)
    emissions = base.base_pressure_growth + base.actor_baseline_pressure * actions["emission_load"]
    emissions += pressure_noise
    abatement = (
        base.abatement_effect * actions["abatement"] * (0.30 + 0.70 * policy)
        + base.policy_effect * policy * state.institution
    )
    restoration = base.restoration_rate * actions["restoration"] * (0.25 + support)
    hysteresis = 0.020 if state.irreversible else 0.0
    pressure = max(
        0.0, state.pressure + emissions - sink - abatement - 0.30 * restoration + hysteresis
    )
    biosphere = legacy.clamp(
        state.biosphere - base.biosphere_damage_rate * pressure
        - 0.004 * actions["defective_rate"] + restoration + 0.20 * social_noise
    )
    institutional_failure = (
        pressure / true_boundary >= base.institutional_irreversibility_pressure_fraction
        and (
            state.institution <= base.irreversible_institution_floor
            or state.justice <= base.irreversible_justice_floor
        )
    )
    entered = (
        pressure >= true_boundary or biosphere <= base.irreversible_biosphere_floor
        or institutional_failure
    )
    first = state.irreversible_step
    if entered and first is None:
        first = step
    return replace(
        state, pressure=pressure, biosphere=biosphere,
        irreversible=state.irreversible or entered, irreversible_step=first,
    )


def _sensor_observation(
    plant: PlantState,
    actuators: ActuatorState,
    model_boundaries: tuple[float, ...],
    observation_bias: float,
    observation_noise: float,
    previous_capture: float,
    remaining_budget: float,
    step: int,
    config: FeasibilityConfig,
) -> Observation:
    """The measurement boundary: plant pressure is converted into public signal."""
    arm = MATCHED_ARM
    manipulation = (
        config.base.manipulation_scale * previous_capture
        * (1.0 - actuators.effective_audit) * (1.0 - 0.45 * arm.monitoring)
    )
    correction = manipulation * actuators.effective_audit * (0.45 + 0.45 * arm.function_separation)
    missing = config.observation_missing_every > 0 and step % config.observation_missing_every == 0
    observed = None if missing else max(
        0.0, plant.pressure + observation_bias + observation_noise - manipulation + correction
    )
    return Observation(
        step=step, observed_pressure=observed, model_boundaries=model_boundaries,
        observed_at_step=None if missing else step,
        institution=plant.institution, trust=plant.trust, justice=plant.justice,
        remaining_budget=remaining_budget, active_mode=actuators.active_mode,
        pending_mode=actuators.pending_mode,
        effective_policy=actuators.effective_policy, effective_support=actuators.effective_support,
        effective_audit=actuators.effective_audit,
    )


def run_episode(
    config: FeasibilityConfig,
    trigger: str,
    environment: legacy.Environment,
    collect_trace: bool = False,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Run paired exogenous draws through one trigger and the common capability."""
    config.validate()
    if trigger not in TRIGGERS:
        raise ValueError(f"unknown trigger: {trigger!r}")
    if not isinstance(environment, legacy.Environment):
        raise TypeError("environment must be a legacy Environment")
    if len(environment.actors) != config.base.actors:
        raise ValueError("environment actor count does not match configuration")
    for name in ("pressure_noise", "observation_noise", "social_noise", "choice_draws"):
        if len(getattr(environment, name)) != config.base.horizon:
            raise ValueError(f"environment {name} length does not match horizon")
    if not _finite_number(environment.true_boundary) or environment.true_boundary <= 0.0:
        raise ValueError("true_boundary must be positive and finite")
    model_boundaries = legacy.selected_boundaries(environment, MATCHED_ARM)
    plant = initial_plant(config)
    actuators = ActuatorState()
    controller = ControllerState()
    balance = config.initial_budget
    previous_capture = 0.0
    total_cost = 0.0
    min_justice = plant.justice
    finite_cr: list[float] = []
    traces: list[dict[str, Any]] = []
    counts = {
        "budget_exhausted_steps": 0, "active_emergency_steps": 0,
        "effective_emergency_steps": 0, "requested_emergency_steps": 0,
        "requested_normal_steps": 0, "requested_precaution_steps": 0,
        "unknown_steps": 0, "max_unknown_streak": 0,
    }
    for step in range(config.base.horizon):
        observation = _sensor_observation(
            plant, actuators, model_boundaries, environment.observation_bias,
            environment.observation_noise[step], previous_capture, balance, step, config,
        )
        previous_observed = controller.previous_observed_pressure
        decision, controller = decide(observation, controller, config, trigger)
        actuators = request_mode(actuators, decision.requested_mode, step, config)
        actuators, ledger = advance_actuators(actuators, step, config, balance)
        balance = ledger.remaining_budget
        public = replace(
            observation, remaining_budget=balance, active_mode=actuators.active_mode,
            pending_mode=actuators.pending_mode, effective_policy=actuators.effective_policy,
            effective_support=actuators.effective_support, effective_audit=actuators.effective_audit,
        )
        actions = public_actor_actions(
            public, environment.actors, environment.choice_draws[step], config, previous_observed
        )
        social = public_social_update(
            public, actions, previous_observed, config, environment.social_noise[step]
        )
        pressure_before = plant.pressure
        plant = replace(
            plant, institution=social["institution"], trust=social["trust"], justice=social["justice"]
        )
        plant = advance_plant(
            plant, actions, actuators, environment.true_boundary,
            environment.pressure_noise[step], environment.social_noise[step], step, config,
        )
        previous_capture = social["effective_capture"]
        total_cost += ledger.step_cost
        min_justice = min(min_justice, plant.justice)
        if decision.estimated_cr is not None:
            finite_cr.append(decision.estimated_cr)
        counts["budget_exhausted_steps"] += int(ledger.budget_exhausted)
        counts["active_emergency_steps"] += int(actuators.active_mode >= 2)
        counts["effective_emergency_steps"] += int(
            actuators.effective_mode >= 2 and (
                actuators.effective_policy > 0.0 or actuators.effective_support > 0.0
                or actuators.effective_audit > 0.0
            )
        )
        counts["requested_emergency_steps"] += int(decision.requested_mode >= 2)
        counts["requested_normal_steps"] += int(decision.requested_mode == 0)
        counts["requested_precaution_steps"] += int(decision.requested_mode == 1)
        counts["unknown_steps"] += int(decision.evidence_status == "insufficient_evidence")
        counts["max_unknown_streak"] = max(counts["max_unknown_streak"], controller.unknown_streak)
        if collect_trace:
            traces.append({
                "t": step, "trigger": trigger, "episode": environment.episode,
                "true_boundary": environment.true_boundary, "pressure_before": pressure_before,
                "pressure": plant.pressure, "observed_pressure": observation.observed_pressure,
                "observed_at_step": observation.observed_at_step,
                "evidence_status": decision.evidence_status, "reason": decision.reason,
                "response_status": decision.response_status, "estimated_cr": decision.estimated_cr,
                "estimated_response_steps": decision.estimated_response_steps,
                "boundary_uncertainty": decision.boundary_uncertainty,
                "observed_trend": decision.observed_trend,
                "requested_mode": decision.requested_mode, "pending_mode": actuators.pending_mode,
                "pending_due_step": actuators.pending_due_step,
                "pending_transition_count": len(actuators.transitions),
                "active_mode": actuators.active_mode, "effective_mode": actuators.effective_mode,
                "command_policy": actuators.command_policy, "command_support": actuators.command_support,
                "command_audit": actuators.command_audit, "effective_policy": actuators.effective_policy,
                "effective_support": actuators.effective_support, "effective_audit": actuators.effective_audit,
                "pending_effect_count": len(actuators.effects), "remaining_budget": balance,
                "step_cost": ledger.step_cost, "nominal_cost": ledger.nominal_cost,
                "curtailment_factor": ledger.curtailment_factor,
                "budget_exhausted": int(ledger.budget_exhausted),
                "irreversible": int(plant.irreversible), "biosphere": plant.biosphere,
                "institution": plant.institution, "trust": plant.trust, "justice": plant.justice,
                "release_streak": controller.release_streak, "unknown_streak": controller.unknown_streak,
                "normal_release_streak": controller.normal_release_streak,
                "precaution_release_streak": controller.precaution_release_streak,
                "attempted_capture": actions["attempted_capture"],
                "effective_capture": social["effective_capture"],
                "cooperation_rate": actions["cooperation_rate"], "defective_rate": actions["defective_rate"],
                "backlash": social["backlash"], "performative_gap": social["performative_gap"],
                "perceived_improvement": social["perceived_improvement"],
            })
    metrics = {
        "trigger": trigger, "episode": environment.episode, "environment_seed": environment.seed,
        "true_boundary": environment.true_boundary, "irreversible_entry": int(plant.irreversible),
        "justice_floor_violation": int(min_justice <= config.base.irreversible_justice_floor),
        "first_irreversible_step": plant.irreversible_step if plant.irreversible_step is not None else -1,
        "final_pressure": plant.pressure, "final_biosphere": plant.biosphere,
        "final_institution": plant.institution, "final_trust": plant.trust, "final_justice": plant.justice,
        "total_cost": total_cost, "remaining_budget": balance, "min_justice": min_justice,
        "min_estimated_cr": min(finite_cr) if finite_cr else None,
        "final_active_mode": actuators.active_mode, "final_effective_mode": actuators.effective_mode,
        **counts,
    }
    return metrics, traces
