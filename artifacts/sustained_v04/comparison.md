# Sustained-plan failure-first experiment

> F0 synthetic experiment; not an empirical digital twin, deployment controller, safety certificate, or authority to act.

Phase: evaluation; sustained model: 0.4.0-experimental; baseline: 0.3.0-experimental.

## Primary paired cohort

| Scenario | Controller | Irreversible / episodes | Justice violations | Mean cost | Mean emergency-active steps | Mean plan-found steps | Mean no-candidate steps | Mean boundary / braking / budget rejection steps |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| baseline | reserve | 17 / 48 | 0 | 3.979175 | 36.271 | n/a | n/a | n/a / n/a / n/a |
| baseline | sustained_reserve | 7 / 48 | 0 | 4.000000 | 66.958 | 5.062 | 66.938 | 45.438 / 66.500 / 48.000 |
| long_delays | reserve | 33 / 48 | 0 | 3.993179 | 59.854 | n/a | n/a | n/a / n/a / n/a |
| long_delays | sustained_reserve | 26 / 48 | 0 | 4.000000 | 61.979 | 1.104 | 70.896 | 67.375 / 67.854 / 27.979 |
| low_policy_capacity | reserve | 25 / 48 | 0 | 3.808800 | 69.000 | n/a | n/a | n/a / n/a / n/a |
| low_policy_capacity | sustained_reserve | 25 / 48 | 0 | 3.808800 | 69.000 | 1.208 | 70.792 | 63.896 / 70.646 / 24.000 |
| tight_budget | reserve | 48 / 48 | 1 | 1.500000 | 50.708 | n/a | n/a | n/a / n/a / n/a |
| tight_budget | sustained_reserve | 48 / 48 | 0 | 1.500000 | 67.458 | 1.542 | 70.458 | 63.000 / 69.979 / 70.458 |
| zero_budget | reserve | 48 / 48 | 3 | 0.000000 | 69.000 | n/a | n/a | n/a / n/a / n/a |
| zero_budget | sustained_reserve | 48 / 48 | 3 | 0.000000 | 69.000 | 0.000 | 72.000 | 68.479 / 71.812 / 72.000 |
| closer_hidden_boundary | reserve | 43 / 48 | 0 | 3.989737 | 41.542 | n/a | n/a | n/a / n/a / n/a |
| closer_hidden_boundary | sustained_reserve | 14 / 48 | 0 | 4.000000 | 66.958 | 5.062 | 66.938 | 45.458 / 66.500 / 48.000 |
| common_optimistic_bias | reserve | 30 / 48 | 0 | 3.882808 | 28.812 | n/a | n/a | n/a / n/a / n/a |
| common_optimistic_bias | sustained_reserve | 7 / 48 | 0 | 4.000000 | 66.958 | 5.021 | 66.979 | 32.896 / 66.646 / 48.000 |
| optimistic_policy_gain_assumption | reserve | 17 / 48 | 0 | 3.979175 | 36.271 | n/a | n/a | n/a / n/a / n/a |
| optimistic_policy_gain_assumption | sustained_reserve | 8 / 48 | 0 | 4.000000 | 61.854 | 11.667 | 60.333 | 46.583 / 59.812 / 47.479 |
| intermittent_observation | reserve | 15 / 48 | 0 | 3.988392 | 37.479 | n/a | n/a | n/a / n/a / n/a |
| intermittent_observation | sustained_reserve | 8 / 48 | 0 | 4.000000 | 65.958 | 3.312 | 50.688 | 36.167 / 50.312 / 35.979 |
| zero_actuator_capacity | reserve | 48 / 48 | 3 | 0.000000 | 69.000 | n/a | n/a | n/a / n/a / n/a |
| zero_actuator_capacity | sustained_reserve | 48 / 48 | 3 | 0.000000 | 69.000 | 0.188 | 71.812 | 68.479 / 71.812 / 0.000 |

## Scenario-local paired outcomes

| Scenario | Pairs | Sustained only succeeds | Reserve only succeeds | Both succeed | Both fail | Mean cost delta (sustained - reserve) |
|---|---:|---:|---:|---:|---:|---:|
| baseline | 48 | 10 | 0 | 31 | 7 | 0.020825 |
| long_delays | 48 | 7 | 0 | 15 | 26 | 0.006821 |
| low_policy_capacity | 48 | 0 | 0 | 23 | 25 | 0.000000 |
| tight_budget | 48 | 0 | 0 | 0 | 48 | 0.000000 |
| zero_budget | 48 | 0 | 0 | 0 | 48 | 0.000000 |
| closer_hidden_boundary | 48 | 29 | 0 | 5 | 14 | 0.010262 |
| common_optimistic_bias | 48 | 23 | 0 | 18 | 7 | 0.117192 |
| optimistic_policy_gain_assumption | 48 | 9 | 0 | 31 | 8 | 0.020825 |
| intermittent_observation | 48 | 7 | 0 | 33 | 8 | 0.011608 |
| zero_actuator_capacity | 48 | 0 | 0 | 0 | 48 | 0.000000 |

## Prior v0.3 failure regression lot (post-hoc)

| Scenario | Seed | Episode | Declared comparator | Threshold | Threshold + hysteresis | Reserve | Sustained reserve | Original relation preserved |
|---|---:|---:|---|---|---|---|---|---|
| baseline | 307 | 42 | threshold | success | success | failure | success | yes |
| common_optimistic_bias | 101 | 45 | threshold_hysteresis | success | success | failure | success | yes |
| common_optimistic_bias | 101 | 56 | threshold_hysteresis | failure | success | failure | success | yes |
| common_optimistic_bias | 211 | 8 | threshold_hysteresis | failure | success | failure | success | yes |
| common_optimistic_bias | 211 | 28 | threshold_hysteresis | failure | success | failure | success | yes |
| common_optimistic_bias | 211 | 61 | threshold_hysteresis | success | success | failure | success | yes |
| common_optimistic_bias | 307 | 6 | threshold_hysteresis | success | success | failure | success | yes |
| common_optimistic_bias | 307 | 35 | threshold_hysteresis | failure | success | failure | success | yes |
| common_optimistic_bias | 307 | 36 | threshold_hysteresis | success | success | failure | success | yes |
| common_optimistic_bias | 307 | 39 | threshold_hysteresis | success | success | failure | success | yes |
| common_optimistic_bias | 307 | 54 | threshold_hysteresis | failure | success | failure | success | yes |

The regression lot is reported separately and is not independent evidence.
No pooled universal winner is computed. A missing candidate means only that the finite declared plan set did not pass.
Projection assumptions, public model boundaries, and synthetic outcomes are not physical or institutional validation.
