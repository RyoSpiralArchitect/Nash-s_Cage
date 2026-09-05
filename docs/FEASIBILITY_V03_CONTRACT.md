# Feasibility v0.3: first-path experimental contract

Status: F0 experimental extension, not an empirical digital twin or deployment controller.
This file specifies the first comparison before measuring its results.
It is a local pre-execution specification, not an independently preregistered study.
The legacy v0.2 executable, config, manuscript and reference outputs stay byte-identical.

## Question and falsification target

With identical observation mechanisms, actor profiles, actuator capability parameters,
initial budget, and exogenous episode draws, where does a reserve trigger outperform,
tie, or underperform simple threshold and hysteretic-threshold triggers?
Realized observations can diverge after different interventions change the plant.

A result that favors a simpler trigger is retained. There is no requirement that
RVCIM win. Fixed capability parameters are not a claim of equal realized cost.
The same ex ante budget is available to each controller; actual spending, shortages,
duration of intervention, and harmful outcomes are separately reported.

## Model interfaces

- Hidden plant state and true irreversible boundaries belong only to the world
  dynamics and evaluator, not to the decision API.
- Decisions consume a public Observation, controller memory, and explicit config.
  Pressure is noisy; institutional/justice/resource/actuator telemetry is assumed
  exact and available in this toy. That simplifying assumption is disclosed.
- Actor and social response may consume public observations; evaluator FP/FN and
  hidden-boundary-derived classifications do not feed the live loop.
- Missing/stale/non-finite observations produce insufficient_evidence. There is no
  new escalation from missing evidence alone. Existing authorized commands may
  continue; that fallback is an assumption to stress, not a safety certificate.
  Replayed samples cannot advance release: the hold requires distinct timestamps.
  Normal-mode targets may still run and cost resources under this fallback.
- requested, pending, active command, and effective intervention are different.
  Configured actuation delay and physical effect delay have real queues.
  Repeating an unchanged request must not indefinitely postpone activation.
- Policy/support/audit commands have capacity and slew bounds. Delivered output
  can shut down faster than command down-slew when funding is exhausted: this
  explicit forced-curtailment exception prevents unfunded residual operation.
  A finite ledger funds actual delivery, not a command that may never act.
  Curtailment is explicit; no overspending or free positive
  paid actuator. Costs are synthetic normalized quantities, not currency.
- The former recoverability logistic is not a probability certificate. The new
  experiment does not solve a robust viability kernel or establish recovery probability.
- Hysteresis and release are tested, including a case in which model ambiguity
  prevents normal requests. Time spent stuck in a state must remain visible.

## Fixed initial design

The new wrapper config uses the preserved minimal.json for legacy physical/actor
parameters. The v0.3 initial values are: actuation delay 3 steps; physical effect
delay 4; policy/support/audit capacity 1; maximum slew .12 each; initial budget 4;
policy/support/audit costs .06/.03/.02; uncertainty limit .30; release margin 11;
release hold 3 observations; maximum observation age 1; missing-observation
schedule disabled by default. These are declared toy assumptions, not estimates.
All controllers share the legacy full_rvcim capability coefficients.

Plain threshold releases using pressure thresholds immediately. Threshold with
hysteresis uses a declared pressure release margin .05 and the 3-observation hold.
Each lower target has its own qualifying streak; a precaution-release observation
cannot count as normal-release evidence. The lowest independently qualified lower
target is eligible, so lower pressure cannot prevent an otherwise qualified downshift.
Reserve uses the CR margin and ambiguity condition for release. Threshold
comparators do not depend on CR for their transitions. An unavailable response
estimate has a separate capacity/slew/budget status; it is not zero or certified safe.
The response proxy checks the emergency policy target and funding for one operating
tick, not sustained affordability or whether that target can reverse physical drift.
Unavailable response can still request a declared loss-limiting emergency; this is
a heuristic, not proof of feasible protection.

The uncertainty threshold differs from legacy .18. This is a versioned design
choice to permit testing return-to-normal behavior; .18 remains an explicit stress
case. It is not tuned against the new evaluation outcomes.

## Sampling and comparison

The machine-readable plan is simulation/configs/feasibility_stress_plan.json.

- Development: master seed 7, 16 episodes. For debugging only.
- Evaluation: master seeds 101, 211, 307; 64 episodes each.
- Controllers: threshold, threshold_hysteresis, reserve.
- Nine scenarios: baseline, long delays, low policy capacity, zero budget, closer
  hidden boundary, correlated optimistic model/observation bias, persistent
  ambiguity, every observation missing, and zero actuator capacities.
- Environment draws use stable_seed(master_seed, "environment", episode).
  Each scenario applies the same declared environment transform for every controller.
- No threshold selection or scenario removal after seeing evaluation results.
  Bug fixes require rerunning the whole fixed plan and retaining their explanation.
- Record all episode-level outcomes, per-scenario summaries, and the first
  episode's step trace for every seed/controller/scenario.
- Comparisons are paired by scenario/master_seed/episode. Never pool scenarios
  into a universal winner. Unused random seeds are not empirical validation.

## Required outputs

- episodes.csv: outcomes and resource/intervention metrics for every run.
- summary.json: per-scenario/controller aggregates and paired win/loss/tie counts.
- trace.csv: observation and requested/pending/active/effective/resource history.
- resolved_plan.json: complete plan and resolved per-scenario model configs.
- receipt.json: phase, model version, source/config/plan hashes and output hashes.
- comparison.md: human-readable results and claim limitations.

All numeric JSON must be finite; absent estimates are null, not zero.
Exported floating-point values are canonically rounded to nine decimal places in
CSV and JSON (negative zero becomes zero); internal calculations are not rounded.
Replay compares these declared-precision exports, not raw binary floating states.
Text is UTF-8/LF and sorted deterministically where ordering is not semantic.
New output directories only: no overwrite option. Publication exclusively creates
the destination and writes its receipt last; incomplete publication is invalid
and is not claimed atomic. It leaves partial output for inspection, never removes
an existing directory to recover. A verifier checks the exact
output set and hashes against the current source/config/plan and can replay all
deterministic outputs. This is internal consistency, not authenticity.

## Outcomes and gates

Primary descriptive outcome: any irreversible entry within the declared horizon.
Also report justice-floor violations, actual cost and remaining budget, shortage
duration, active/effective emergency duration where defined, unknown duration,
normal requests, and terminal physical condition.

Engineering acceptance does not require favorable outcomes. It requires:
information-boundary noninterference; exact delay boundaries; finite nonnegative
resource accounting; capacity/slew enforcement; visible missing evidence;
deterministic matched runs; valid release behavior; legacy-byte preservation;
tamper detection and full replay. A failed invariant blocks acceptance.
A numerically unfavorable controller result does not.

## What remains outside this first path

No live data ingestion, real authority, actuation, new emergency powers, compensation
scheme, democratic legitimacy, calibrated effect estimate, climate forecast,
equilibrium incentive compatibility, or learned/adaptive capture adversary is
established. Public telemetry accuracy and actor payoffs remain modeling assumptions.
Work on unknown-evidence rules and adoption incentives continues at the theory level.
This extension is the test apparatus that later, narrowly scoped empirical models
may replace, not a proof that those models already exist.

## Specification history

The plan and numerical configuration were fixed before any v0.3 outcomes. After
the development run, wording was clarified to distinguish matched observation
mechanisms from identical realized observations, and to describe replayed-sample
handling, normal-mode costs and the one-tick response proxy. No thresholds,
parameters, scenarios or evaluation seeds were changed from development results.

Fresh review after the first evaluation found two bugs: hysteresis transferred
release evidence between destinations and could block an otherwise justified
emergency downshift; raw floats broke replay between Python 3.10 and 3.13. The
superseded first evaluation was kept locally, both bugs were repaired, and the
entire fixed plan was rerun without changing numerical parameters or seeds.
