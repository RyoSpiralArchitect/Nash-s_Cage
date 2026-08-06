# Executable reference model

`simulation/rvcim_sim.py` is a dependency-free F0 implementation of the paper's minimal research program. It is intentionally small enough to read as one auditable file.

## Quick run

From the repository root:

```bash
python3 -m simulation explain
python3 -m simulation smoke --out .tmp/smoke
python3 -m simulation verify --receipt .tmp/smoke/receipt.json
```

A full reference run:

```bash
python3 -m simulation run \
  --config simulation/configs/minimal.json \
  --episodes 64 \
  --seed 7 \
  --out artifacts/reference_run \
  --overwrite
```

Run one arm by repeating `--arm` as needed:

```bash
python3 -m simulation run \
  --arm weak_coupling \
  --arm full_rvcim \
  --episodes 32 --seed 12 \
  --out .tmp/two-arm --overwrite
```

Override a declared parameter without editing the JSON:

```bash
python3 -m simulation run \
  --set observation_noise_std=0.06 \
  --set policy_base_delay=7.0 \
  --out .tmp/noisy-delay --overwrite
```

Overrides use JSON values. Unknown keys are rejected, and the exact effective configuration is saved as `resolved_config.json`.

## Paper-to-code map

| Paper object | Implementation | F0 meaning |
|---|---|---|
| `x_t`, `s_t` | `WorldState` | Pressure, biosphere, institutional, trust, justice, policy, support, and audit state. |
| `a_i,t`, `Delta_i` | `actor_actions()` | Heterogeneous payoff-sensitive cooperation, defection, capture, and symbolic action. |
| `y_t`, `k_t` | `observe_pressure()` | Noisy observation, manipulation, and audit correction. |
| `Theta_t` | `Environment.model_boundaries` | Finite model ensemble with common-mode bias and structural allowance. |
| `CR_t`, `rho_t` | `estimate_reserve()` | Conservative estimated exit time minus endogenous response time. |
| `Gamma` | `select_mode()`, `schedule_policy()`, `advance_policy()` | Trigger selection, delayed activation, and release logic. |
| `c_eff` | `effective_capture_value()` | Attempted capture after audit, function separation, justice, and policy exposure. |
| `PG_t` | trace and episode accumulators | Symbolic action minus scaled verified physical improvement. |

## Comparison arms

The four arms differ only through the declared `ArmSpec` values. Within an episode they receive the same actor profiles, true boundary, model-boundary errors, physical disturbances, observation noise, social noise, and random choice draws.

This paired construction makes internal comparisons less noisy. It does not establish external validity.

## State transition order

At each step the model:

1. advances any pending institutional mode toward its target policy and support levels;
2. samples actor cooperation, defection, symbolic action, restoration, and capture from fixed episode draws and current payoffs;
3. updates the hidden physical state;
4. produces a noisy and manipulable observation;
5. estimates controllability reserve and recoverability;
6. selects a governance mode and records false-positive or false-negative trigger status against the hidden toy state;
7. updates justice, trust, and institutional capacity;
8. schedules delayed policy changes and writes an optional trace row.

The order is explicit because moving even one operation can change the mechanism being tested.

## Metrics

- `irreversible_entry`: whether the toy entered a physical, biosphere, institutional, or justice irreversibility condition.
- `first_irreversible_step`: first entry step; right-censored at the configured horizon when no entry occurs.
- `min_hidden_cr`: minimum controllability reserve using the hidden realized boundary.
- `min_estimated_cr`: minimum reserve available to the controller.
- `cumulative_performative_gap`: symbolic action minus scaled verified physical improvement, summed over time.
- `capture_absorption`: one minus effective capture divided by attempted capture.
- `justice_stability`: mean justice reserve minus mean backlash.
- `defective_action_rate`: power-weighted defective action over time.
- `false_positive_rate`: trigger escalation while the hidden toy state remains in normal mode.
- `false_negative_rate`: no escalation while the hidden toy state warrants precaution or emergency response.
- `emergency_trigger_rate`: fraction of steps selecting emergency or loss-minimization mode.
- `mean_response_delay`: mean scheduled institutional delay.
- `mean_estimation_error`: absolute difference between estimated and hidden controllability reserve.

## Reproducibility receipt

`receipt.json` records:

- model and schema versions
- the F0 claim boundary
- episodes, seed, selected arms, and CLI overrides
- Python implementation and platform metadata
- SHA-256 hashes for results, source, original config, and resolved config

Verification resolves every path relative to the receipt location:

```bash
python3 -m simulation verify --receipt PATH/receipt.json
```

A modified or missing file makes verification fail with a non-zero exit status.

## Tests

```bash
python3 -m unittest discover -s simulation/tests -v
```

The tests cover configuration validation, arm ordering, emergency selection, capture defenses, deterministic environment sampling, common episode environments, byte-reproducible outputs, and receipt tamper detection.

## Claim boundary

The normalized parameters are selected to produce an inspectable mechanism gradient. They do not estimate climate sensitivity, tipping distributions, institutional response, actor preferences, or real intervention effects. A visually ordered table is a property of this configuration, not empirical support for RVCIM.
