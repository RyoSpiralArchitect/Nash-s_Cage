# Sustained v0.4: finite-plan admission contract

Status: F0 experimental extension. This is neither an empirical digital twin nor
a deployment controller, safety certificate, recovery probability, robust
viability kernel, or authority to act. v0.2 and v0.3 sources, configurations and
fixtures are frozen inputs and remain byte-identical.

## The missing gate

v0.3 asks approximately whether an emergency policy target can be reached and
funded for one operating tick. That leaves four distinct questions unanswered:

1. Does the plant stay below a public model boundary while delayed effects arrive?
2. Is delivered policy strong enough to stop the declared upper pressure drift?
3. Can the full projected intervention and a terminal resource reserve be funded?
4. Would a requested downshift preserve non-increasing pressure for several steps?

v0.4 adds a queue-aware, finite candidate-plan screen. Failure means only that no
tested constant-mode plan was demonstrated within this declared projection and
horizon. It never means physical or institutional infeasibility in general.

## Information and authority boundary

The screen receives a v0.3 public observation, controller memory, the complete
public actuator state (including all transition/effect queues), and configuration.
It cannot receive the plant state, true boundary, environment or evaluator labels.
Hidden outcomes may be accumulated after a decision for evaluation, but never feed
later control or social dynamics.

The v0.3 reserve decision remains the minimum requested mode. The new screen tests
constant normal, precaution and emergency targets and may raise that request or
delay a release. It returns only the first request of a receding-horizon procedure;
the projected tail is not a binding commitment and is reassessed on every distinct
valid observation. Missing, stale, replayed or nonfinite evidence preserves the
v0.3 hold behavior and runs no new projection or escalation.

## Declared reduced-form projection

The screen clones the full actuator state, submits a candidate mode, and advances
the real v0.3 queues, slew/capacity limits, delivery ledger and affordability
curtailment for each projected step. Repeating a candidate cannot move its due date.

The pressure projection is deliberately small and inspectable. Starting pressure
is the observed pressure plus a declared error bound. It reconstructs upper
uncontrolled drift from the observed trend plus the upper policy-gain assumption
times current delivered policy and a drift margin. Each future increment subtracts
the lower gain assumption times projected delivered policy. This avoids subtracting
new policy effects twice from an already controlled trend.

A candidate passes only if every projected pressure is strictly below the lowest
public model boundary after structural and model margins, its final required
braking window has no increment above the configured maximum, and its terminal
budget meets the configured reserve. A pass is conditional on these declared
reduced-form bounds. Gaussian sensor noise, omitted plant/social dynamics and
misspecified gain are not magically bounded by the configuration.

Initial assumptions, fixed before development results: projection horizon 24;
required braking tail 6; maximum tail pressure increment 0; drift margin .008;
policy gain interval [.03,.05]; pressure error bound .04; model-boundary margin
.02; terminal budget reserve .20. These normalized values are not estimates.

## Fixed comparison

The machine plan is `simulation/configs/sustained_stress_plan.json`.

- Development: seed 17, 8 episodes per scenario. Evaluation: seeds 401, 503 and
  607, 16 episodes each (48 per scenario/controller).
- Paired controllers: unchanged v0.3 reserve and v0.4 sustained-reserve. They use
  the same plant, actors, capabilities, initial resources and exogenous draws.
- Ten scenarios retain favorable and hostile cases: baseline, long delays, low
  policy capacity, tight/zero budgets, closer hidden boundary, common optimistic
  model/observation bias, optimistic policy-gain assumption, intermittent
  observations and zero actuator capacity.
- Eleven exact v0.3 cases in which a threshold comparator succeeded and reserve
  failed are a named post-hoc regression lot. They are not new independent evidence.
- No scenario, seed, numerical threshold or losing case is removed after outcomes.
  Implementation bugs require a documented full rerun.

## Outcomes and limits

Report irreversible entry, justice-floor entry, costs/resources, projected-plan
availability, selected plan, boundary/braking/budget rejection reasons, unknown
observations, intervention duration and terminal condition. Compare paired outcomes
within each scenario; do not pool them into a universal winner.

Passing tests establishes information separation and arithmetic contracts only.
Even a favorable synthetic result cannot establish policy effectiveness. Actual
system identification, calibrated observation/error bounds, nonstationary/adaptive
actors, legal authority, compensation, appeal, legitimacy and incentives to adopt
the institution remain outside this implementation.
