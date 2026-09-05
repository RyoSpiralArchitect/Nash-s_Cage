# Failure-first feasibility experiment

> F0 synthetic experiment; not empirical validation, a safety certificate, or authority to act.

Phase: evaluation; model: 0.3.0-experimental.

Same capability parameters and initial budget; realized cost is reported, not forced equal.

| Scenario | Controller | Irreversible / episodes | Justice violations | Mean cost | Mean emergency-active steps | Mean unknown steps |
|---|---|---:|---:|---:|---:|---:|
| baseline | threshold | 98 / 192 | 1 | 3.986969 | 33.604 | 0.000 |
| baseline | threshold_hysteresis | 93 / 192 | 1 | 3.995542 | 36.714 | 0.000 |
| baseline | reserve | 70 / 192 | 1 | 3.977604 | 37.948 | 0.000 |
| long_delays | threshold | 192 / 192 | 2 | 2.866814 | 38.068 | 0.000 |
| long_delays | threshold_hysteresis | 192 / 192 | 2 | 2.918450 | 38.583 | 0.000 |
| long_delays | reserve | 148 / 192 | 1 | 3.988174 | 59.635 | 0.000 |
| low_policy_capacity | threshold | 190 / 192 | 1 | 3.160152 | 41.526 | 0.000 |
| low_policy_capacity | threshold_hysteresis | 187 / 192 | 1 | 3.183534 | 42.375 | 0.000 |
| low_policy_capacity | reserve | 112 / 192 | 0 | 3.808800 | 69.000 | 0.000 |
| zero_budget | threshold | 192 / 192 | 5 | 0.000000 | 45.411 | 0.000 |
| zero_budget | threshold_hysteresis | 192 / 192 | 5 | 0.000000 | 45.849 | 0.000 |
| zero_budget | reserve | 192 / 192 | 5 | 0.000000 | 69.000 | 0.000 |
| closer_hidden_boundary | threshold | 192 / 192 | 1 | 4.000000 | 44.297 | 0.000 |
| closer_hidden_boundary | threshold_hysteresis | 192 / 192 | 1 | 4.000000 | 44.474 | 0.000 |
| closer_hidden_boundary | reserve | 176 / 192 | 1 | 3.985275 | 42.714 | 0.000 |
| common_optimistic_bias | threshold | 135 / 192 | 1 | 3.975619 | 34.115 | 0.000 |
| common_optimistic_bias | threshold_hysteresis | 131 / 192 | 1 | 3.991563 | 35.698 | 0.000 |
| common_optimistic_bias | reserve | 130 / 192 | 1 | 3.914717 | 31.786 | 0.000 |
| persistent_ambiguity | threshold | 98 / 192 | 1 | 3.986969 | 33.604 | 0.000 |
| persistent_ambiguity | threshold_hysteresis | 93 / 192 | 1 | 3.995542 | 36.714 | 0.000 |
| persistent_ambiguity | reserve | 38 / 192 | 1 | 4.000000 | 45.661 | 0.000 |
| missing_every_observation | threshold | 192 / 192 | 3 | 1.953000 | 0.000 | 72.000 |
| missing_every_observation | threshold_hysteresis | 192 / 192 | 3 | 1.953000 | 0.000 | 72.000 |
| missing_every_observation | reserve | 192 / 192 | 3 | 1.953000 | 0.000 | 72.000 |
| zero_actuator_capacity | threshold | 192 / 192 | 5 | 0.000000 | 45.411 | 0.000 |
| zero_actuator_capacity | threshold_hysteresis | 192 / 192 | 5 | 0.000000 | 45.849 | 0.000 |
| zero_actuator_capacity | reserve | 192 / 192 | 5 | 0.000000 | 69.000 | 0.000 |

All scenarios, unfavorable outcomes, and paired comparisons are retained in summary.json.
Requested/active/effective modes and delivered resources are distinct. Positive CR is not a feasibility proof.
Missing evidence is not safety; unknown-period behavior is a declared fallback assumption.
