# Heat institution v0.1 — independent experimental lane

Read `CONTRACT.ja.md` before interpreting results. This is an **uncalibrated F0
synthetic mechanism screen**, not a model of Japan's actual institutional performance.
Existing institutions are present in every arm, including the active ordinary
comparator. No private conversation, worker records, or observed clinical outcomes
are shipped to the compute node.

## Run from the repository root

Python standard library only, Python 3.10+. No GPU or dependencies required.

```sh
python3 -m unittest discover -s experiments/heat_institution_v01 -p test_run.py -v
python3 experiments/heat_institution_v01/run.py freeze --out .tmp/heat-freeze-v01
python3 experiments/heat_institution_v01/run.py run --registration .tmp/heat-freeze-v01/registration.json --phase development --out .tmp/heat-development-v01 --processes 2
python3 experiments/heat_institution_v01/run.py run --registration .tmp/heat-freeze-v01/registration.json --phase evaluation --out .tmp/heat-evaluation-v01 --processes 2
python3 experiments/heat_institution_v01/run.py verify --out .tmp/heat-evaluation-v01 --replay --processes 2
```

Use new output names for another run. There is no overwrite option. Failed
publication can leave a partial directory, which verification rejects; preserve
it and use a new output name. Source/plan changes invalidate the local registration
and require a new freeze. The six inputs are hashed before and after computation;
the seven output files are checked for exact closure before and after verification.
The registration is not an external timestamp authority. Hash consistency is
distinct from deterministic replay (`--replay`) and neither proves model validity.

## Evidence

- `episodes.csv`: all arm-seasons, with constrained-group outcomes and resource ledger.
- `trace.csv`: all days of the first seed in each scenario/arm; hidden hazard fields
  are evaluator-only. This is not a randomly selected sample of worker histories.
- `summary.json`: all four arms, paired contrasts and the factorial interaction,
  separate by condition, with season-level descriptive standard errors.
- `comparison.md`: compact all-condition table, not a selected winner table.
- `registration.json`, `resolved_plan.json`, `receipt.json`: identity and replay anchors.

Development and evaluation seeds are disjoint. Parameters are frozen before either
set; inspecting development results is allowed but changing them is a new version,
not a silent update. Evaluation is a fresh seed set, not independent real-world
validation. All scenarios share the seed stream to support controlled contrasts;
do not treat different scenarios as independent geographic observations.

## Integration boundary

This folder has its own tests and verifier. It is **not yet part of the historical
61-file release manifest or the root `make verify` target**. Existing release tests
must still pass without changing any predecessor source or receipt. Local execution
and Furnace replay do not imply Windows CI, independent review, push, or merge.

## Mechanism limitations

The synthetic baseline floor is a guaranteed service allocation, not a simulation
of how a statute produces compliance. Legal rules have not been numerically encoded.
Information reduces random error only; linkage reduces assumed delay and increases
the privately anticipated availability of an already budgeted transfer. Every added
action receives the same nominal transfer in every arm. These are modeling
assumptions, not learned behavioral estimates. The model has no equilibrium solver,
strategic capture, mortality equation, service-delivery outcome, or national
standard-revision process. See the empirical input gates in the contract.
