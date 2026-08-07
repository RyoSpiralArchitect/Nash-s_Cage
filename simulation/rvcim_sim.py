#!/usr/bin/env python3
"""Executable F0 reference model for Nash's Cage / RVCIM.

The model is deliberately dependency-free and compact enough to audit. It is a
structural simulation of the paper's causal chain, not a climate forecast, an
integrated assessment model, empirical validation, or policy advice.
"""

from __future__ import annotations

import argparse
import csv
import dataclasses
import hashlib
import json
import math
import os
import platform
import random
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from statistics import fmean, pstdev
from typing import Any, Iterable, Mapping, MutableMapping, Sequence

VERSION = "0.2.0"
SCHEMA_VERSION = 1
RECEIPT_VERSION = 2
CLAIM_LEVEL = "F0"
CLAIM_BOUNDARY = (
    "Structural toy only; not calibrated, predictive, empirically validating, "
    "or a policy recommendation."
)
OUTPUT_HASH_FILES = frozenset(
    {
        "episodes.csv",
        "summary.csv",
        "trace.csv",
        "comparison.md",
        "resolved_config.json",
    }
)
OUTPUT_DIRECTORY_FILES = OUTPUT_HASH_FILES | {"receipt.json"}
DEFAULT_ARMS = (
    "weak_coupling",
    "nominal_trigger",
    "robust_reserve",
    "full_rvcim",
)
MODE_NAMES = {
    0: "adaptive_normal",
    1: "precaution",
    2: "emergency_braking",
    3: "loss_minimization",
}


class ConfigError(ValueError):
    """Raised when a configuration is incomplete or internally inconsistent."""


@dataclass(frozen=True)
class ModelConfig:
    schema_version: int
    horizon: int
    actors: int
    trace_episodes: int
    pressure_initial: float
    biosphere_initial: float
    institution_initial: float
    trust_initial: float
    justice_initial: float
    boundary_mean: float
    boundary_spread: float
    model_boundary_offsets: tuple[float, ...]
    common_mode_boundary_bias_std: float
    common_mode_observation_bias_std: float
    base_pressure_growth: float
    pressure_growth_noise_std: float
    sink_strength: float
    biosphere_damage_rate: float
    restoration_rate: float
    observation_noise_std: float
    manipulation_scale: float
    policy_base_delay: float
    biophysical_response_lag: float
    policy_adjustment_rate: float
    policy_decay: float
    precaution_margin: float
    release_margin: float
    nominal_trigger_level: float
    nominal_emergency_level: float
    actor_baseline_pressure: float
    abatement_effect: float
    policy_effect: float
    damage_payoff_scale: float
    cooperation_temperature: float
    institution_friction: float
    institution_capture_damage: float
    institution_policy_gain: float
    trust_gap_damage: float
    trust_backlash_damage: float
    justice_burden_damage: float
    justice_recovery_rate: float
    irreversible_biosphere_floor: float
    irreversible_institution_floor: float
    irreversible_justice_floor: float
    institutional_irreversibility_pressure_fraction: float
    performative_gap_kappa: float

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "ModelConfig":
        allowed = {item.name for item in dataclasses.fields(cls)}
        unknown = sorted(set(payload) - allowed)
        missing = sorted(allowed - set(payload))
        if unknown:
            raise ConfigError(f"unknown configuration keys: {', '.join(unknown)}")
        if missing:
            raise ConfigError(f"missing configuration keys: {', '.join(missing)}")
        normalized = dict(payload)
        integer_fields = {"schema_version", "horizon", "actors", "trace_episodes"}
        for name in integer_fields:
            value = normalized[name]
            if isinstance(value, bool) or not isinstance(value, int):
                raise ConfigError(f"{name} must be an integer")

        float_fields = allowed - integer_fields - {"model_boundary_offsets"}
        for name in float_fields:
            value = normalized[name]
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ConfigError(f"{name} must be a finite number")
            normalized[name] = float(value)
            if not math.isfinite(normalized[name]):
                raise ConfigError(f"{name} must be a finite number")

        offsets = normalized.get("model_boundary_offsets")
        if not isinstance(offsets, list) or not offsets:
            raise ConfigError("model_boundary_offsets must be a non-empty JSON array")
        if any(
            isinstance(value, bool) or not isinstance(value, (int, float))
            for value in offsets
        ):
            raise ConfigError("model_boundary_offsets must contain finite numbers")
        normalized_offsets = tuple(float(value) for value in offsets)
        if any(not math.isfinite(value) for value in normalized_offsets):
            raise ConfigError("model_boundary_offsets must contain finite numbers")
        normalized["model_boundary_offsets"] = normalized_offsets
        try:
            config = cls(**normalized)
        except TypeError as exc:
            raise ConfigError(str(exc)) from exc
        try:
            config.validate()
        except ConfigError:
            raise
        except (TypeError, ValueError) as exc:
            raise ConfigError(f"invalid configuration value: {exc}") from exc
        return config

    def validate(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise ConfigError(
                f"unsupported schema_version={self.schema_version}; expected {SCHEMA_VERSION}"
            )
        if self.horizon < 8:
            raise ConfigError("horizon must be at least 8")
        if self.actors < 2:
            raise ConfigError("actors must be at least 2")
        if self.trace_episodes < 0:
            raise ConfigError("trace_episodes cannot be negative")
        if self.boundary_spread <= 0:
            raise ConfigError("boundary_spread must be positive")
        if self.cooperation_temperature <= 0:
            raise ConfigError("cooperation_temperature must be positive")
        if not 0 < self.nominal_trigger_level < self.nominal_emergency_level:
            raise ConfigError(
                "nominal_trigger_level must be positive and below nominal_emergency_level"
            )
        for name in (
            "pressure_initial",
            "biosphere_initial",
            "institution_initial",
            "trust_initial",
            "justice_initial",
            "policy_adjustment_rate",
            "policy_decay",
            "institutional_irreversibility_pressure_fraction",
        ):
            value = float(getattr(self, name))
            if not 0.0 <= value <= 1.0:
                raise ConfigError(f"{name} must lie in [0, 1]")

    def to_mapping(self) -> dict[str, Any]:
        payload = dataclasses.asdict(self)
        payload["model_boundary_offsets"] = list(self.model_boundary_offsets)
        return payload


@dataclass(frozen=True)
class ArmSpec:
    key: str
    label: str
    trigger: str
    coupling: float
    monitoring: float
    audit: float
    anti_capture: float
    justice_buffer: float
    function_separation: float
    response_delay_multiplier: float
    response_speed: float
    model_count: int
    structural_allowance: float
    release_rule: bool
    policy_targets: tuple[float, float, float, float]
    support_targets: tuple[float, float, float, float]


ARM_SPECS: dict[str, ArmSpec] = {
    "weak_coupling": ArmSpec(
        key="weak_coupling",
        label="Weak coupling",
        trigger="none",
        coupling=0.08,
        monitoring=0.62,
        audit=0.06,
        anti_capture=0.03,
        justice_buffer=0.06,
        function_separation=0.03,
        response_delay_multiplier=1.30,
        response_speed=0.08,
        model_count=1,
        structural_allowance=0.00,
        release_rule=True,
        policy_targets=(0.05, 0.14, 0.20, 0.24),
        support_targets=(0.07, 0.12, 0.16, 0.20),
    ),
    "nominal_trigger": ArmSpec(
        key="nominal_trigger",
        label="Nominal trigger",
        trigger="threshold",
        coupling=0.58,
        monitoring=0.72,
        audit=0.12,
        anti_capture=0.08,
        justice_buffer=0.16,
        function_separation=0.10,
        response_delay_multiplier=1.10,
        response_speed=0.24,
        model_count=1,
        structural_allowance=0.00,
        release_rule=False,
        policy_targets=(0.08, 0.54, 0.78, 0.82),
        support_targets=(0.10, 0.30, 0.42, 0.48),
    ),
    "robust_reserve": ArmSpec(
        key="robust_reserve",
        label="Robust reserve",
        trigger="reserve",
        coupling=0.83,
        monitoring=0.84,
        audit=0.46,
        anti_capture=0.55,
        justice_buffer=0.60,
        function_separation=0.52,
        response_delay_multiplier=0.76,
        response_speed=0.62,
        model_count=3,
        structural_allowance=0.025,
        release_rule=True,
        policy_targets=(0.13, 0.64, 0.90, 0.94),
        support_targets=(0.17, 0.56, 0.78, 0.88),
    ),
    "full_rvcim": ArmSpec(
        key="full_rvcim",
        label="Full RVCIM",
        trigger="reserve",
        coupling=0.91,
        monitoring=0.90,
        audit=0.68,
        anti_capture=0.86,
        justice_buffer=0.82,
        function_separation=0.82,
        response_delay_multiplier=0.68,
        response_speed=0.72,
        model_count=3,
        structural_allowance=0.050,
        release_rule=True,
        policy_targets=(0.14, 0.65, 0.91, 0.96),
        support_targets=(0.18, 0.56, 0.82, 0.94),
    ),
}


@dataclass(frozen=True)
class ActorProfile:
    power: float
    dependence: float
    exposure: float
    externalization: float
    horizon: float
    transition_cost: float
    capture_ability: float
    greenwash_ability: float


@dataclass(frozen=True)
class Environment:
    episode: int
    seed: int
    true_boundary: float
    model_boundaries: tuple[float, ...]
    observation_bias: float
    actors: tuple[ActorProfile, ...]
    pressure_noise: tuple[float, ...]
    observation_noise: tuple[float, ...]
    social_noise: tuple[float, ...]
    choice_draws: tuple[tuple[float, ...], ...]


@dataclass
class WorldState:
    pressure: float
    biosphere: float
    institution: float
    trust: float
    justice: float
    policy: float
    support: float
    audit: float
    mode: int = 0
    pending_mode: int | None = None
    pending_delay: int = 0
    release_streak: int = 0
    irreversible: bool = False
    irreversible_step: int | None = None


@dataclass
class EpisodeAccumulator:
    min_hidden_cr: float = math.inf
    min_estimated_cr: float = math.inf
    performative_gap: float = 0.0
    attempted_capture: float = 0.0
    effective_capture: float = 0.0
    justice_sum: float = 0.0
    backlash_sum: float = 0.0
    defective_sum: float = 0.0
    false_positive: int = 0
    false_negative: int = 0
    emergency_steps: int = 0
    response_delays: list[int] = field(default_factory=list)
    estimation_error: float = 0.0
    steps: int = 0


@dataclass(frozen=True)
class EpisodeResult:
    arm: str
    episode: int
    environment_seed: int
    true_boundary: float
    irreversible_entry: int
    first_irreversible_step: int
    final_pressure: float
    final_biosphere: float
    final_institution: float
    final_trust: float
    final_justice: float
    min_hidden_cr: float
    min_estimated_cr: float
    cumulative_performative_gap: float
    capture_absorption: float
    justice_stability: float
    defective_action_rate: float
    false_positive_rate: float
    false_negative_rate: float
    emergency_trigger_rate: float
    mean_response_delay: float
    mean_estimation_error: float
    final_mode: int

    def as_row(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


@dataclass(frozen=True)
class StepTrace:
    arm: str
    episode: int
    t: int
    true_boundary: float
    pressure: float
    observed_pressure: float
    biosphere: float
    institution: float
    trust: float
    justice: float
    policy: float
    support: float
    audit: float
    mode: int
    mode_name: str
    estimated_cr: float
    hidden_cr: float
    attempted_capture: float
    effective_capture: float
    cooperation_rate: float
    defective_rate: float
    performative_gap: float
    backlash: float
    irreversible: int

    def as_row(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def logistic(value: float) -> float:
    if value >= 0:
        z = math.exp(-value)
        return 1.0 / (1.0 + z)
    z = math.exp(value)
    return z / (1.0 + z)


def percentile(values: Sequence[float], q: float) -> float:
    if not values:
        raise ValueError("percentile requires at least one value")
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = clamp(q) * (len(ordered) - 1)
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction


def stable_seed(base_seed: int, channel: str, episode: int) -> int:
    payload = f"nash-cage:{base_seed}:{channel}:{episode}".encode("utf-8")
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def parse_override(raw: str) -> tuple[str, Any]:
    if "=" not in raw:
        raise ConfigError(f"override must use key=value syntax: {raw!r}")
    key, text = raw.split("=", 1)
    key = key.strip()
    if not key:
        raise ConfigError("override key cannot be empty")
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        value = text
    return key, value


def load_config(path: Path, overrides: Sequence[str] = ()) -> ModelConfig:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigError(f"configuration not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ConfigError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(payload, MutableMapping):
        raise ConfigError("configuration root must be a JSON object")
    for raw in overrides:
        key, value = parse_override(raw)
        payload[key] = value
    return ModelConfig.from_mapping(payload)


def sample_actors(count: int, rng: random.Random) -> tuple[ActorProfile, ...]:
    profiles: list[ActorProfile] = []
    raw_powers: list[float] = []
    for _ in range(count):
        dependence = rng.betavariate(2.2, 2.0)
        externalization = clamp(0.22 + 0.58 * dependence + rng.gauss(0.0, 0.10))
        exposure = clamp(rng.betavariate(1.8, 2.3) - 0.16 * externalization)
        horizon = clamp(rng.betavariate(2.0, 2.1))
        transition_cost = clamp(0.20 + 0.62 * dependence + rng.gauss(0.0, 0.09))
        capture_ability = clamp(rng.betavariate(1.8, 2.7) + 0.22 * dependence)
        greenwash_ability = clamp(rng.betavariate(2.0, 2.0) + 0.14 * capture_ability)
        raw_power = max(0.01, rng.paretovariate(2.5) - 1.0)
        raw_powers.append(raw_power)
        profiles.append(
            ActorProfile(
                power=raw_power,
                dependence=dependence,
                exposure=exposure,
                externalization=externalization,
                horizon=horizon,
                transition_cost=transition_cost,
                capture_ability=capture_ability,
                greenwash_ability=greenwash_ability,
            )
        )
    total = sum(raw_powers)
    return tuple(dataclasses.replace(profile, power=profile.power / total) for profile in profiles)


def sample_environment(config: ModelConfig, seed: int, episode: int = 0) -> Environment:
    rng = random.Random(seed)
    boundary = rng.uniform(
        config.boundary_mean - config.boundary_spread,
        config.boundary_mean + config.boundary_spread,
    )
    common_boundary_bias = rng.gauss(0.0, config.common_mode_boundary_bias_std)
    model_boundaries = tuple(
        config.boundary_mean + offset + common_boundary_bias
        for offset in config.model_boundary_offsets
    )
    observation_bias = rng.gauss(0.0, config.common_mode_observation_bias_std)
    actors = sample_actors(config.actors, rng)
    pressure_noise = tuple(
        rng.gauss(0.0, config.pressure_growth_noise_std) for _ in range(config.horizon)
    )
    observation_noise = tuple(
        rng.gauss(0.0, config.observation_noise_std) for _ in range(config.horizon)
    )
    social_noise = tuple(rng.gauss(0.0, 0.006) for _ in range(config.horizon))
    choice_draws = tuple(
        tuple(rng.random() for _ in range(config.actors))
        for _ in range(config.horizon)
    )
    return Environment(
        episode=episode,
        seed=seed,
        true_boundary=boundary,
        model_boundaries=model_boundaries,
        observation_bias=observation_bias,
        actors=actors,
        pressure_noise=pressure_noise,
        observation_noise=observation_noise,
        social_noise=social_noise,
        choice_draws=choice_draws,
    )


def initial_state(config: ModelConfig, arm: ArmSpec) -> WorldState:
    return WorldState(
        pressure=config.pressure_initial,
        biosphere=config.biosphere_initial,
        institution=config.institution_initial,
        trust=config.trust_initial,
        justice=config.justice_initial,
        policy=arm.policy_targets[0],
        support=arm.support_targets[0],
        audit=arm.audit,
    )


def selected_boundaries(environment: Environment, arm: ArmSpec) -> tuple[float, ...]:
    ordered = sorted(environment.model_boundaries)
    count = min(max(1, arm.model_count), len(ordered))
    if count == 1:
        return (ordered[len(ordered) // 2],)
    if count == len(ordered):
        return tuple(ordered)
    start = (len(ordered) - count) // 2
    return tuple(ordered[start : start + count])


def estimate_response_time(
    state: WorldState,
    arm: ArmSpec,
    effective_capture: float,
    backlash: float,
    config: ModelConfig,
    robust: bool,
) -> float:
    delay = (
        config.policy_base_delay * arm.response_delay_multiplier
        + config.biophysical_response_lag
        + 3.8 * effective_capture
        + 2.2 * backlash
        + 2.4 * (1.0 - state.institution)
        - 1.8 * arm.response_speed
    )
    if robust:
        delay *= 1.12
    return max(0.5, delay)


def estimate_reserve(
    observed_pressure: float,
    observed_trend: float,
    environment: Environment,
    state: WorldState,
    arm: ArmSpec,
    effective_capture: float,
    backlash: float,
    config: ModelConfig,
) -> tuple[float, float, float]:
    boundaries = selected_boundaries(environment, arm)
    drift = max(0.0035, observed_trend)
    exit_times = [
        max(0.0, (boundary - arm.structural_allowance - observed_pressure) / drift)
        for boundary in boundaries
    ]
    exit_estimate = min(exit_times) if arm.trigger == "reserve" else percentile(exit_times, 0.50)
    response = estimate_response_time(
        state, arm, effective_capture, backlash, config, robust=arm.trigger == "reserve"
    )
    reserve = exit_estimate - response
    recoverability = logistic((reserve + 0.25 * exit_estimate) / 4.5)
    return reserve, response, recoverability


def hidden_reserve(
    state: WorldState,
    environment: Environment,
    hidden_trend: float,
    arm: ArmSpec,
    effective_capture: float,
    backlash: float,
    config: ModelConfig,
) -> float:
    drift = max(0.0035, hidden_trend)
    exit_time = max(0.0, (environment.true_boundary - state.pressure) / drift)
    response = estimate_response_time(
        state, arm, effective_capture, backlash, config, robust=True
    )
    return exit_time - response


def select_mode(
    arm: ArmSpec,
    observed_pressure: float,
    estimated_cr: float,
    recoverability: float,
    boundary_uncertainty: float,
    config: ModelConfig,
) -> int:
    if arm.trigger == "none":
        return 0
    if arm.trigger == "threshold":
        if observed_pressure >= config.nominal_emergency_level:
            return 2
        if observed_pressure >= config.nominal_trigger_level:
            return 1
        return 0
    if recoverability < 0.10:
        return 3
    if estimated_cr <= 0.0:
        return 2
    if estimated_cr <= config.precaution_margin or boundary_uncertainty >= 0.18:
        return 1
    return 0


def truth_mode(hidden_cr: float, state: WorldState, config: ModelConfig) -> int:
    if state.irreversible:
        return 3
    if hidden_cr <= 0.0:
        return 2
    if hidden_cr <= config.precaution_margin:
        return 1
    return 0


def effective_capture_value(
    attempted: float,
    state: WorldState,
    arm: ArmSpec,
) -> float:
    defense = (
        arm.anti_capture
        + 1.30 * state.audit
        + arm.function_separation
        + arm.justice_buffer * state.justice
        + 0.35 * state.policy * state.audit
    )
    return attempted / (1.0 + defense)


def actor_actions(
    state: WorldState,
    arm: ArmSpec,
    environment: Environment,
    t: int,
    config: ModelConfig,
) -> dict[str, float]:
    choices: list[tuple[ActorProfile, bool]] = []
    for actor, draw in zip(environment.actors, environment.choice_draws[t]):
        cooperation_gain = (
            1.05 * state.support * (1.0 - 0.35 * actor.transition_cost)
            + 0.42 * state.trust * actor.horizon
            + config.damage_payoff_scale * 0.35 * actor.exposure * state.pressure
            + 1.10 * state.policy * arm.coupling * (0.35 + 0.65 * state.audit)
        )
        burden = (
            0.82
            * state.policy
            * actor.transition_cost
            * actor.dependence
            * (1.0 - 0.72 * state.support)
        )
        defection_gain = (
            0.72 * actor.dependence
            + 0.55 * actor.externalization
            + 0.32 * (1.0 - actor.horizon)
            + 0.24
            * actor.greenwash_ability
            * arm.monitoring
            * (1.0 - state.audit)
        )
        justice_legitimacy = 0.24 * state.justice * (1.0 - actor.dependence)
        delta = cooperation_gain + justice_legitimacy - burden - defection_gain
        cooperate = draw < logistic(delta / config.cooperation_temperature)
        choices.append((actor, cooperate))

    defective = sum(actor.power for actor, cooperate in choices if not cooperate)
    cooperation = 1.0 - defective
    emission_load = sum(
        actor.power * (0.50 + 0.80 * actor.dependence)
        for actor, cooperate in choices
        if not cooperate
    )
    abatement = sum(
        actor.power * (0.55 + 0.45 * (1.0 - actor.transition_cost))
        for actor, cooperate in choices
        if cooperate
    )
    restoration = sum(
        actor.power * (0.20 + 0.40 * actor.exposure)
        for actor, cooperate in choices
        if cooperate
    )
    attempted_capture = sum(
        actor.power
        * actor.capture_ability
        * (0.45 + actor.dependence)
        * (0.45 + state.policy)
        * (0.55 + actor.power * len(environment.actors))
        for actor, cooperate in choices
        if not cooperate
    )
    symbolic = sum(
        actor.power
        * (
            0.12
            if cooperate
            else 0.22
            + 0.78 * actor.greenwash_ability * arm.monitoring * (1.0 - state.audit)
        )
        for actor, cooperate in choices
    )
    burdens = [
        state.policy
        * actor.dependence
        * actor.transition_cost
        * (1.0 - 0.78 * state.support)
        for actor, _ in choices
    ]
    burden_concentration = max(0.0, percentile(burdens, 0.90) - percentile(burdens, 0.20))
    return {
        "defective_rate": clamp(defective),
        "cooperation_rate": clamp(cooperation),
        "emission_load": emission_load,
        "abatement": abatement,
        "restoration": restoration,
        "attempted_capture": attempted_capture,
        "symbolic": symbolic,
        "burden_concentration": burden_concentration,
    }


def schedule_policy(
    state: WorldState,
    selected_mode: int,
    estimated_cr: float,
    effective_capture: float,
    backlash: float,
    arm: ArmSpec,
    config: ModelConfig,
    delays: list[int],
) -> None:
    if selected_mode < state.mode:
        if not arm.release_rule:
            selected_mode = state.mode
        elif estimated_cr >= config.release_margin:
            state.release_streak += 1
            if state.release_streak < 3:
                selected_mode = state.mode
        else:
            state.release_streak = 0
            selected_mode = state.mode
    else:
        state.release_streak = 0

    requested = state.pending_mode if state.pending_mode is not None else state.mode
    if selected_mode == requested:
        return
    delay = (
        config.policy_base_delay * arm.response_delay_multiplier
        + 3.5 * effective_capture
        + 2.0 * backlash
        + 1.6 * (1.0 - state.institution)
        - 1.8 * arm.response_speed
    )
    if selected_mode >= 2:
        delay -= 0.8
    delay_steps = max(0, int(round(delay)))
    state.pending_mode = selected_mode
    state.pending_delay = delay_steps
    delays.append(delay_steps)


def advance_policy(
    state: WorldState,
    arm: ArmSpec,
    effective_capture: float,
    backlash: float,
    config: ModelConfig,
) -> None:
    if state.pending_mode is not None:
        if state.pending_delay > 0:
            state.pending_delay -= 1
        else:
            state.mode = state.pending_mode
            state.pending_mode = None
    target_policy = arm.policy_targets[state.mode]
    target_support = arm.support_targets[state.mode]
    target_audit = clamp(arm.audit + (0.10, 0.18, 0.28, 0.34)[state.mode])
    rate = clamp(
        config.policy_adjustment_rate
        * (0.35 + 0.65 * state.institution)
        * (0.50 + arm.response_speed)
        * (1.0 - 0.35 * effective_capture)
        * (1.0 - 0.25 * backlash),
        0.02,
        0.80,
    )
    state.policy += rate * (target_policy - state.policy)
    state.support += rate * (target_support - state.support)
    state.audit += rate * (target_audit - state.audit)
    if state.mode == 0:
        state.policy *= 1.0 - config.policy_decay
    state.policy = clamp(state.policy)
    state.support = clamp(state.support)
    state.audit = clamp(state.audit)


def update_world(
    state: WorldState,
    actions: Mapping[str, float],
    environment: Environment,
    t: int,
    config: ModelConfig,
) -> tuple[float, float]:
    old_pressure = state.pressure
    old_biosphere = state.biosphere
    sink = config.sink_strength * state.biosphere * max(0.12, 1.0 - 0.55 * state.pressure)
    emissions = (
        config.base_pressure_growth
        + config.actor_baseline_pressure * actions["emission_load"]
        + environment.pressure_noise[t]
    )
    abatement = (
        config.abatement_effect * actions["abatement"] * (0.30 + 0.70 * state.policy)
        + config.policy_effect * state.policy * state.institution
    )
    restoration = config.restoration_rate * actions["restoration"] * (0.25 + state.support)
    hysteresis = 0.020 if state.irreversible else 0.0
    net = emissions - sink - abatement - 0.30 * restoration + hysteresis
    state.pressure = max(0.0, state.pressure + net)
    state.biosphere = clamp(
        state.biosphere
        - config.biosphere_damage_rate * state.pressure
        - 0.004 * actions["defective_rate"]
        + restoration
        + 0.20 * environment.social_noise[t]
    )
    pressure_fraction = state.pressure / environment.true_boundary
    institutional_failure = (
        pressure_fraction >= config.institutional_irreversibility_pressure_fraction
        and (
            state.institution <= config.irreversible_institution_floor
            or state.justice <= config.irreversible_justice_floor
        )
    )
    if (
        state.pressure >= environment.true_boundary
        or state.biosphere <= config.irreversible_biosphere_floor
        or institutional_failure
    ):
        state.irreversible = True
        if state.irreversible_step is None:
            state.irreversible_step = t
    verified_improvement = max(0.0, old_pressure - state.pressure) + 0.45 * max(
        0.0, state.biosphere - old_biosphere
    )
    return net, verified_improvement


def update_social(
    state: WorldState,
    effective_capture: float,
    performative_gap: float,
    burden_concentration: float,
    backlash: float,
    false_positive: bool,
    false_negative: bool,
    arm: ArmSpec,
    config: ModelConfig,
    noise: float,
) -> None:
    fairness = state.support * (0.35 + 0.65 * arm.justice_buffer)
    state.justice = clamp(
        state.justice
        + config.justice_recovery_rate * fairness
        - config.justice_burden_damage * burden_concentration
        - 0.020 * effective_capture
        - 0.018 * backlash
        + 0.15 * noise
    )
    trust_change = (
        0.022 * fairness
        - config.trust_gap_damage * max(0.0, performative_gap)
        - config.trust_backlash_damage * backlash
        - 0.022 * effective_capture
        + 0.10 * noise
    )
    if false_positive:
        trust_change -= 0.014
    if false_negative:
        trust_change -= 0.022
    state.trust = clamp(state.trust + trust_change)
    state.institution = clamp(
        state.institution
        + config.institution_policy_gain * state.audit * (state.trust - 0.30)
        - config.institution_friction
        - config.institution_capture_damage * effective_capture
        - 0.030 * backlash
        + 0.08 * noise
    )


def observe_pressure(
    state: WorldState,
    environment: Environment,
    t: int,
    effective_capture: float,
    arm: ArmSpec,
    config: ModelConfig,
) -> float:
    manipulation = (
        config.manipulation_scale
        * effective_capture
        * (1.0 - state.audit)
        * (1.0 - 0.45 * arm.monitoring)
    )
    correction = manipulation * state.audit * (0.45 + 0.45 * arm.function_separation)
    return max(
        0.0,
        state.pressure
        + environment.observation_bias
        + environment.observation_noise[t]
        - manipulation
        + correction,
    )


def run_episode(
    config: ModelConfig,
    arm: ArmSpec,
    environment: Environment,
    collect_trace: bool = False,
) -> tuple[EpisodeResult, list[StepTrace]]:
    state = initial_state(config, arm)
    acc = EpisodeAccumulator()
    traces: list[StepTrace] = []
    previous_observed = state.pressure
    smoothed_trend = max(0.0035, config.base_pressure_growth * 0.50)
    hidden_trend = smoothed_trend
    previous_effective_capture = 0.0
    previous_backlash = 0.0
    boundary_uncertainty = max(environment.model_boundaries) - min(environment.model_boundaries)

    for t in range(config.horizon):
        advance_policy(
            state,
            arm,
            previous_effective_capture,
            previous_backlash,
            config,
        )
        actions = actor_actions(state, arm, environment, t, config)
        attempted_capture = actions["attempted_capture"]
        effective_capture = effective_capture_value(attempted_capture, state, arm)
        net_drift, verified_improvement = update_world(state, actions, environment, t, config)
        observed_pressure = observe_pressure(
            state, environment, t, effective_capture, arm, config
        )
        observed_delta = observed_pressure - previous_observed
        smoothed_trend = 0.70 * smoothed_trend + 0.30 * observed_delta
        hidden_trend = 0.70 * hidden_trend + 0.30 * net_drift

        provisional_backlash = clamp(
            actions["burden_concentration"] * (1.0 - 0.55 * arm.justice_buffer)
            + 0.20 * max(0.0, state.policy - state.support)
            + (0.10 if state.mode >= 2 else 0.0) * (1.0 - state.justice)
        )
        estimated_cr, _, recoverability = estimate_reserve(
            observed_pressure,
            smoothed_trend,
            environment,
            state,
            arm,
            effective_capture,
            provisional_backlash,
            config,
        )
        hidden_cr = hidden_reserve(
            state,
            environment,
            hidden_trend,
            arm,
            effective_capture,
            provisional_backlash,
            config,
        )
        selected_mode = select_mode(
            arm,
            observed_pressure,
            estimated_cr,
            recoverability,
            boundary_uncertainty,
            config,
        )
        true_mode = truth_mode(hidden_cr, state, config)
        false_positive = selected_mode > 0 and true_mode == 0
        false_negative = selected_mode == 0 and true_mode > 0
        backlash = clamp(
            provisional_backlash
            + (0.10 if false_positive else 0.0)
            + (0.07 if false_negative else 0.0)
            - 0.18 * state.support * arm.justice_buffer
        )
        performative_gap = actions["symbolic"] - config.performative_gap_kappa * verified_improvement
        update_social(
            state,
            effective_capture,
            performative_gap,
            actions["burden_concentration"],
            backlash,
            false_positive,
            false_negative,
            arm,
            config,
            environment.social_noise[t],
        )
        schedule_policy(
            state,
            selected_mode,
            estimated_cr,
            effective_capture,
            backlash,
            arm,
            config,
            acc.response_delays,
        )

        acc.min_hidden_cr = min(acc.min_hidden_cr, hidden_cr)
        acc.min_estimated_cr = min(acc.min_estimated_cr, estimated_cr)
        acc.performative_gap += performative_gap
        acc.attempted_capture += attempted_capture
        acc.effective_capture += effective_capture
        acc.justice_sum += state.justice
        acc.backlash_sum += backlash
        acc.defective_sum += actions["defective_rate"]
        acc.false_positive += int(false_positive)
        acc.false_negative += int(false_negative)
        acc.emergency_steps += int(selected_mode >= 2)
        acc.estimation_error += abs(estimated_cr - hidden_cr)
        acc.steps += 1

        if collect_trace:
            traces.append(
                StepTrace(
                    arm=arm.key,
                    episode=environment.episode,
                    t=t,
                    true_boundary=environment.true_boundary,
                    pressure=state.pressure,
                    observed_pressure=observed_pressure,
                    biosphere=state.biosphere,
                    institution=state.institution,
                    trust=state.trust,
                    justice=state.justice,
                    policy=state.policy,
                    support=state.support,
                    audit=state.audit,
                    mode=selected_mode,
                    mode_name=MODE_NAMES[selected_mode],
                    estimated_cr=estimated_cr,
                    hidden_cr=hidden_cr,
                    attempted_capture=attempted_capture,
                    effective_capture=effective_capture,
                    cooperation_rate=actions["cooperation_rate"],
                    defective_rate=actions["defective_rate"],
                    performative_gap=performative_gap,
                    backlash=backlash,
                    irreversible=int(state.irreversible),
                )
            )

        previous_observed = observed_pressure
        previous_effective_capture = effective_capture
        previous_backlash = backlash

    attempted_total = acc.attempted_capture
    absorption = (
        1.0
        if attempted_total <= 1e-12
        else 1.0 - acc.effective_capture / attempted_total
    )
    entry_step = state.irreversible_step if state.irreversible_step is not None else config.horizon
    result = EpisodeResult(
        arm=arm.key,
        episode=environment.episode,
        environment_seed=environment.seed,
        true_boundary=environment.true_boundary,
        irreversible_entry=int(state.irreversible),
        first_irreversible_step=entry_step,
        final_pressure=state.pressure,
        final_biosphere=state.biosphere,
        final_institution=state.institution,
        final_trust=state.trust,
        final_justice=state.justice,
        min_hidden_cr=acc.min_hidden_cr,
        min_estimated_cr=acc.min_estimated_cr,
        cumulative_performative_gap=acc.performative_gap,
        capture_absorption=clamp(absorption),
        justice_stability=(acc.justice_sum - acc.backlash_sum) / acc.steps,
        defective_action_rate=acc.defective_sum / acc.steps,
        false_positive_rate=acc.false_positive / acc.steps,
        false_negative_rate=acc.false_negative / acc.steps,
        emergency_trigger_rate=acc.emergency_steps / acc.steps,
        mean_response_delay=fmean(acc.response_delays) if acc.response_delays else 0.0,
        mean_estimation_error=acc.estimation_error / acc.steps,
        final_mode=state.mode,
    )
    return result, traces


EPISODE_FIELDS = [item.name for item in dataclasses.fields(EpisodeResult)]
TRACE_FIELDS = [item.name for item in dataclasses.fields(StepTrace)]
BASE_SUMMARY_METRICS = (
    "irreversible_entry",
    "first_irreversible_step",
    "final_pressure",
    "final_biosphere",
    "final_institution",
    "final_trust",
    "final_justice",
    "min_hidden_cr",
    "min_estimated_cr",
    "cumulative_performative_gap",
    "capture_absorption",
    "justice_stability",
    "defective_action_rate",
    "false_positive_rate",
    "false_negative_rate",
    "emergency_trigger_rate",
    "mean_response_delay",
    "mean_estimation_error",
)
SUMMARY_FIELDS = ["arm", "episodes"] + [
    f"{metric}_{stat}"
    for metric in BASE_SUMMARY_METRICS
    for stat in ("mean", "sd", "p05", "p95")
]


def normalized_row(row: Mapping[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for key, value in row.items():
        if isinstance(value, float):
            normalized[key] = f"{value:.10f}"
        else:
            normalized[key] = value
    return normalized


def write_csv(path: Path, fieldnames: Sequence[str], rows: Iterable[Mapping[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
            extrasaction="ignore",
            lineterminator="\n",
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(normalized_row(row))


def summarize(results: Sequence[EpisodeResult]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for arm_key in DEFAULT_ARMS:
        group = [result for result in results if result.arm == arm_key]
        if not group:
            continue
        row: dict[str, Any] = {"arm": arm_key, "episodes": len(group)}
        for metric in BASE_SUMMARY_METRICS:
            values = [float(getattr(result, metric)) for result in group]
            row[f"{metric}_mean"] = fmean(values)
            row[f"{metric}_sd"] = pstdev(values) if len(values) > 1 else 0.0
            row[f"{metric}_p05"] = percentile(values, 0.05)
            row[f"{metric}_p95"] = percentile(values, 0.95)
        rows.append(row)
    return rows


def render_comparison(summary_rows: Sequence[Mapping[str, Any]]) -> str:
    lines = [
        "# Reference comparison",
        "",
        "> F0 structural output only. Values reflect declared normalized assumptions, not calibrated forecasts.",
        "",
        "| Arm | Irreversible entry | Min hidden CR | Capture absorption | Justice stability | Defective action | FN trigger |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary_rows:
        lines.append(
            "| {arm} | {irr:.3f} | {cr:.3f} | {ca:.3f} | {js:.3f} | {da:.3f} | {fn:.3f} |".format(
                arm=row["arm"],
                irr=float(row["irreversible_entry_mean"]),
                cr=float(row["min_hidden_cr_mean"]),
                ca=float(row["capture_absorption_mean"]),
                js=float(row["justice_stability_mean"]),
                da=float(row["defective_action_rate_mean"]),
                fn=float(row["false_negative_rate_mean"]),
            )
        )
    lines.extend(
        [
            "",
            "The four arms share episode environments and random draws. Differences are therefore paired inside the toy, but they remain model-conditional.",
            "",
        ]
    )
    return "\n".join(lines)


def _has_rvcim_receipt(path: Path) -> bool:
    receipt_path = path / "receipt.json"
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    hashes = receipt.get("sha256") if isinstance(receipt, Mapping) else None
    return (
        isinstance(receipt, Mapping)
        and receipt.get("claim_level") == CLAIM_LEVEL
        and isinstance(hashes, Mapping)
        and OUTPUT_HASH_FILES <= set(hashes)
    )


def prepare_output(path: Path, overwrite: bool) -> None:
    if path.is_symlink():
        raise FileExistsError(f"refusing symlink output directory: {path}")
    resolved = path.resolve()
    protected = {
        Path(resolved.anchor),
        Path.home().resolve(),
        Path.cwd().resolve(),
        Path(__file__).resolve().parents[1],
    }
    if resolved in protected:
        raise FileExistsError(f"refusing protected output directory: {path}")

    if resolved.exists():
        if not overwrite:
            raise FileExistsError(f"output directory exists: {path}; pass --overwrite")
        if not resolved.is_dir():
            raise FileExistsError(f"refusing non-directory output path: {path}")
        entries = list(resolved.iterdir())
        unexpected = [
            entry.name
            for entry in entries
            if entry.is_symlink()
            or not entry.is_file()
            or entry.name not in OUTPUT_DIRECTORY_FILES
        ]
        if unexpected:
            raise FileExistsError(
                "refusing to overwrite directory with unexpected entries: "
                + ", ".join(sorted(unexpected))
            )
        if entries and not _has_rvcim_receipt(resolved):
            raise FileExistsError(
                f"refusing unmarked non-empty output directory: {path}"
            )
        for entry in entries:
            entry.unlink()
    else:
        resolved.mkdir(parents=True, exist_ok=False)


def run_experiment(
    cfg_path: Path,
    episodes: int,
    seed: int,
    out_dir: Path,
    arms: Sequence[str] = DEFAULT_ARMS,
    overwrite: bool = False,
    overrides: Sequence[str] = (),
) -> tuple[list[EpisodeResult], list[dict[str, Any]], dict[str, Any]]:
    if episodes <= 0:
        raise ConfigError("episodes must be positive")
    unknown_arms = [arm for arm in arms if arm not in ARM_SPECS]
    if unknown_arms:
        raise ConfigError(f"unknown arms: {', '.join(unknown_arms)}")
    config = load_config(cfg_path, overrides)
    prepare_output(out_dir, overwrite)
    results: list[EpisodeResult] = []
    traces: list[StepTrace] = []
    for episode in range(episodes):
        environment_seed = stable_seed(seed, "environment", episode)
        environment = sample_environment(config, environment_seed, episode)
        for arm_key in arms:
            result, arm_trace = run_episode(
                config,
                ARM_SPECS[arm_key],
                environment,
                collect_trace=episode < config.trace_episodes,
            )
            results.append(result)
            traces.extend(arm_trace)

    summary_rows = summarize(results)
    episodes_path = out_dir / "episodes.csv"
    summary_path = out_dir / "summary.csv"
    trace_path = out_dir / "trace.csv"
    comparison_path = out_dir / "comparison.md"
    write_csv(episodes_path, EPISODE_FIELDS, (result.as_row() for result in results))
    write_csv(summary_path, SUMMARY_FIELDS, summary_rows)
    write_csv(trace_path, TRACE_FIELDS, (trace.as_row() for trace in traces))
    comparison_path.write_text(render_comparison(summary_rows), encoding="utf-8")

    source_path = Path(__file__).resolve()
    config_path = cfg_path.resolve()
    resolved_config_path = out_dir / "resolved_config.json"
    resolved_config_path.write_text(
        json.dumps(config.to_mapping(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    input_paths = {
        "config": os.path.relpath(config_path, out_dir.resolve()),
        "source": os.path.relpath(source_path, out_dir.resolve()),
    }
    receipt = {
        "receipt_version": RECEIPT_VERSION,
        "claim_level": CLAIM_LEVEL,
        "claim_boundary": CLAIM_BOUNDARY,
        "model_version": VERSION,
        "schema_version": SCHEMA_VERSION,
        "command": {
            "episodes": episodes,
            "seed": seed,
            "arms": list(arms),
            "overrides": list(overrides),
        },
        "environment": {
            "python": platform.python_version(),
            "implementation": platform.python_implementation(),
            "platform": platform.platform(),
        },
        "inputs": input_paths,
        "sha256": {
            "episodes.csv": sha256_file(episodes_path),
            "summary.csv": sha256_file(summary_path),
            "trace.csv": sha256_file(trace_path),
            "comparison.md": sha256_file(comparison_path),
            "resolved_config.json": sha256_file(resolved_config_path),
            input_paths["config"]: sha256_file(config_path),
            input_paths["source"]: sha256_file(source_path),
        },
    }
    (out_dir / "receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return results, summary_rows, receipt


def verify_receipt(receipt_path: Path) -> list[str]:
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    except OSError as exc:
        return [f"cannot read receipt: {receipt_path}: {exc}"]
    except json.JSONDecodeError as exc:
        return [f"invalid receipt JSON: {exc}"]

    if not isinstance(receipt, Mapping):
        return ["receipt root must be an object"]

    failures: list[str] = []
    if receipt.get("receipt_version") != RECEIPT_VERSION:
        failures.append(
            f"receipt_version must be {RECEIPT_VERSION}, got {receipt.get('receipt_version')!r}"
        )
    if receipt.get("claim_level") != CLAIM_LEVEL:
        failures.append(f"claim_level must be {CLAIM_LEVEL}")
    if receipt.get("claim_boundary") != CLAIM_BOUNDARY:
        failures.append("claim_boundary does not match the executable contract")
    if receipt.get("schema_version") != SCHEMA_VERSION:
        failures.append(f"schema_version must be {SCHEMA_VERSION}")
    if receipt.get("model_version") != VERSION:
        failures.append(f"model_version must be {VERSION}")

    command = receipt.get("command")
    if not isinstance(command, Mapping):
        failures.append("command must be an object")
    else:
        episodes = command.get("episodes")
        seed = command.get("seed")
        arms = command.get("arms")
        overrides = command.get("overrides")
        if isinstance(episodes, bool) or not isinstance(episodes, int) or episodes <= 0:
            failures.append("command.episodes must be a positive integer")
        if isinstance(seed, bool) or not isinstance(seed, int):
            failures.append("command.seed must be an integer")
        if (
            not isinstance(arms, list)
            or not arms
            or any(arm not in ARM_SPECS for arm in arms)
        ):
            failures.append("command.arms must be a non-empty list of known arms")
        if not isinstance(overrides, list) or any(
            not isinstance(value, str) for value in overrides
        ):
            failures.append("command.overrides must be a list of strings")

    environment = receipt.get("environment")
    if not isinstance(environment, Mapping) or any(
        not isinstance(environment.get(key), str) or not environment.get(key)
        for key in ("python", "implementation", "platform")
    ):
        failures.append(
            "environment must record non-empty python, implementation, and platform"
        )

    inputs = receipt.get("inputs")
    input_paths: set[str] = set()
    if not isinstance(inputs, Mapping) or set(inputs) != {"config", "source"}:
        failures.append("inputs must contain exactly config and source")
    elif any(not isinstance(value, str) or not value for value in inputs.values()):
        failures.append("input paths must be non-empty strings")
    else:
        input_paths = set(inputs.values())
        if len(input_paths) != 2:
            failures.append("config and source input paths must be distinct")
        if input_paths & OUTPUT_HASH_FILES:
            failures.append("input paths must not alias generated output files")
        recorded_source = (receipt_path.parent / str(inputs["source"])).resolve()
        if recorded_source != Path(__file__).resolve():
            failures.append("inputs.source does not resolve to this executable source")
        recorded_config = (receipt_path.parent / str(inputs["config"])).resolve()
        if receipt_path.parent.resolve() in recorded_config.parents:
            failures.append("inputs.config must be outside the output directory")
        elif recorded_config.is_file():
            try:
                load_config(recorded_config)
            except (ConfigError, OSError, ValueError, TypeError) as exc:
                failures.append(f"inputs.config is not a valid model config: {exc}")

    hashes = receipt.get("sha256")
    if not isinstance(hashes, Mapping):
        return failures + ["receipt.sha256 must be an object"]

    expected_hash_keys = OUTPUT_HASH_FILES | input_paths
    actual_hash_keys = set(hashes)
    if actual_hash_keys != expected_hash_keys:
        missing = sorted(expected_hash_keys - actual_hash_keys)
        extra = sorted(actual_hash_keys - expected_hash_keys)
        if missing:
            failures.append("receipt.sha256 missing keys: " + ", ".join(missing))
        if extra:
            failures.append("receipt.sha256 unexpected keys: " + ", ".join(extra))

    for relative, expected in hashes.items():
        if not isinstance(relative, str) or not relative:
            failures.append("receipt.sha256 keys must be non-empty strings")
            continue
        if (
            not isinstance(expected, str)
            or len(expected) != 64
            or any(character not in "0123456789abcdef" for character in expected)
        ):
            failures.append(f"invalid SHA-256 for {relative}")
            continue
        target = (receipt_path.parent / str(relative)).resolve()
        if not target.is_file():
            failures.append(f"missing regular file: {relative}")
            continue
        actual = sha256_file(target)
        if actual != expected:
            failures.append(
                f"hash mismatch: {relative} expected={expected} actual={actual}"
            )
    return failures


def format_summary(rows: Sequence[Mapping[str, Any]]) -> str:
    columns = (
        ("arm", "arm"),
        ("irreversible_entry_mean", "R_irr"),
        ("min_hidden_cr_mean", "min_CR"),
        ("capture_absorption_mean", "capture_abs"),
        ("justice_stability_mean", "justice"),
        ("defective_action_rate_mean", "defect"),
        ("false_negative_rate_mean", "FN"),
    )
    display: list[dict[str, str]] = []
    widths: dict[str, int] = {}
    for row in rows:
        item: dict[str, str] = {}
        for key, label in columns:
            value = row[key]
            text = f"{value:.3f}" if isinstance(value, float) else str(value)
            item[key] = text
            widths[key] = max(widths.get(key, 0), len(label), len(text))
        display.append(item)
    header = "  ".join(label.ljust(widths[key]) for key, label in columns)
    separator = "  ".join("-" * widths[key] for key, _ in columns)
    body = [
        "  ".join(item[key].ljust(widths[key]) for key, _ in columns)
        for item in display
    ]
    return "\n".join([header, separator, *body])


def explain_text() -> str:
    return f"""Nash's Cage / RVCIM executable reference model v{VERSION}

STATUS
  {CLAIM_LEVEL} structural toy. It is not a climate forecast, an integrated
  assessment model, empirical validation, or a policy recommendation.

PAPER -> CODE
  x_t / s_t       WorldState: pressure, biosphere, institution, trust, justice.
  a_i,t           actor_actions(): cooperation, defection, capture, symbolism.
  y_t / k_t       observe_pressure(): noisy and manipulable observation.
  Theta_t         Environment.model_boundaries plus structural allowance.
  CR_t            estimate_reserve(): conservative exit time minus response time.
  Gamma           select_mode(), schedule_policy(), advance_policy().
  Delta_i         actor payoff differential inside actor_actions().
  c_eff           effective_capture_value(): attempted capture after defenses.
  R^J / JS        state.justice and the justice_stability output metric.
  PG_t            symbolic action minus verified physical improvement.

FOUR ARMS
  weak_coupling   observation with little transmission into incentives.
  nominal_trigger pressure thresholds with limited capture defense.
  robust_reserve  ambiguity-aware controllability-reserve triggers.
  full_rvcim      reserve triggers plus audit, anti-capture separation,
                  justice buffers, faster response, and release rules.

RUN
  python -m simulation run --episodes 64 --seed 7 --out artifacts/reference_run

INTERPRETATION
  Arm differences are generated by declared normalized assumptions under common
  episode environments. They can probe implementation logic inside this toy;
  they cannot establish a real-world causal or policy claim.
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="rvcim",
        description="Zero-dependency F0 simulator for Nash's Cage / RVCIM.",
    )
    parser.add_argument("--version", action="version", version=VERSION)
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="run one or more governance arms")
    run_parser.add_argument(
        "--config",
        type=Path,
        default=Path(__file__).parent / "configs" / "minimal.json",
    )
    run_parser.add_argument("--episodes", type=int, default=64)
    run_parser.add_argument("--seed", type=int, default=7)
    run_parser.add_argument("--out", type=Path, default=Path("artifacts/reference_run"))
    run_parser.add_argument(
        "--arm", action="append", choices=DEFAULT_ARMS, dest="arms"
    )
    run_parser.add_argument(
        "--set", action="append", default=[], dest="overrides", metavar="KEY=VALUE"
    )
    run_parser.add_argument("--overwrite", action="store_true")

    smoke_parser = subparsers.add_parser("smoke", help="run a fast four-arm smoke test")
    smoke_parser.add_argument(
        "--config",
        type=Path,
        default=Path(__file__).parent / "configs" / "minimal.json",
    )
    smoke_parser.add_argument("--episodes", type=int, default=4)
    smoke_parser.add_argument("--seed", type=int, default=101)
    smoke_parser.add_argument("--out", type=Path, default=Path(".tmp/smoke"))
    smoke_parser.add_argument("--overwrite", action="store_true", default=True)

    for name in ("verify", "verify-receipt"):
        verify_parser = subparsers.add_parser(name, help="verify hashes in a receipt")
        verify_parser.add_argument("--receipt", type=Path, required=True)

    subparsers.add_parser("explain", help="print claim boundary and paper-to-code map")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "explain":
            print(explain_text())
            return 0
        if args.command in ("verify", "verify-receipt"):
            failures = verify_receipt(args.receipt)
            if failures:
                for failure in failures:
                    print(f"verification error: {failure}", file=sys.stderr)
                return 1
            print(f"OK: verified {args.receipt}")
            return 0
        if args.command == "smoke":
            _, rows, receipt = run_experiment(
                cfg_path=args.config,
                episodes=args.episodes,
                seed=args.seed,
                out_dir=args.out,
                arms=DEFAULT_ARMS,
                overwrite=True,
            )
        else:
            arms = tuple(args.arms) if args.arms else DEFAULT_ARMS
            _, rows, receipt = run_experiment(
                cfg_path=args.config,
                episodes=args.episodes,
                seed=args.seed,
                out_dir=args.out,
                arms=arms,
                overwrite=args.overwrite,
                overrides=args.overrides,
            )
        print("Nash's Cage / RVCIM executable reference model (F0)")
        print(format_summary(rows))
        print(f"\nmodel_version: {receipt['model_version']}")
        print(f"outputs: {args.out}")
        return 0
    except (ConfigError, FileExistsError, OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
