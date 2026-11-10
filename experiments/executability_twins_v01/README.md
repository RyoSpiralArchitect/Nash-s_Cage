# Executability twins v0.1 — input-contract counterexamples

**F0**, synthetic and uncalibrated. Read [CONTRACT.ja.md](CONTRACT.ja.md) first.
This is a finite accounting/observation assay, not a real-world digital twin,
causal effect estimate, policy recommender, equilibrium solver, or clinical tool.

The question is whether the same pre-intervention record permits worlds with
different diagnostics for early payment. Unknown credit, physical constraints,
performance assurance, incentives, shared capacity, payer obligations, and
continuation are distinct inputs. No observed results are used to classify worlds.

## Local qualification (repository root)

Python 3.10+, standard library only. No packages, GPU, model, private records,
or data-service credentials are needed.

```sh
python3 -B -m unittest discover -s experiments/executability_twins_v01 -p 'test_*.py' -v
python3 -B experiments/executability_twins_v01/run.py freeze --out .tmp/twins-v01-freeze
python3 -B experiments/executability_twins_v01/run.py run --registration .tmp/twins-v01-freeze/registration.json --phase smoke --out .tmp/twins-v01-smoke --processes 2
python3 -B experiments/executability_twins_v01/run.py verify --out .tmp/twins-v01-smoke --replay --processes 1
```

Smoke is 12 authored engineering cases, 48 arm-worlds. It is **not** the full
36,864-world catalogue and cannot estimate that catalogue's ambiguity counts.
Tests inspect full-catalogue inputs/counts but do not evaluate that campaign.

## Prospective enumeration (separate execution decision)

```sh
python3 -B experiments/executability_twins_v01/run.py run --registration .tmp/twins-v01-freeze/registration.json --phase enumeration --out .tmp/twins-v01-enumeration --processes 2 --acknowledge-f0-enumeration
python3 -B experiments/executability_twins_v01/run.py verify --out .tmp/twins-v01-enumeration --replay --processes 1
```

The flag is an accidental-launch guard, not user authorization. Full enumeration
has 147,456 arm-worlds, no random sampling or repeated seeds, and no weighted
population interpretation. For Furnace, use `spiral`, inspect availability and
contention, transfer only this seven-file lane to a fresh isolated location,
and retain exact source identities and receipts. Do not change managed runtimes.

Every run requires a fresh output name. There is no overwrite/resume/retry mode.
Partial outputs remain incomplete and must be retained. Changing any of the
seven inputs requires a new freeze and explanation, not rewriting old evidence.
Do not silently run full enumeration after smoke or tune the plan after viewing
its output. Registration is local and self-reported, not third-party preregistration.

## Evidence

- `worlds.jsonl.gz`: every declared world, pre-action label, all four outcomes,
  integer ledgers and event clocks, all three contrasts, diagnostic conjunctions.
- `classes.jsonl.gz`: **every** observation equivalence class and contrast;
  possible C/U/ineligible labels, componentwise bounds, counts, diagnostic status,
  first pass/fail witness IDs, and the deliberately optimistic-fill comparison.
- `witnesses.json`: the first contrasting pair per view/contrast, in fixed catalogue
  order. These are illustrations, not a selected sample for estimating prevalence.
- `summary.json`: full denominators and point-fill errors/misses; no p-values,
  winner, real-world confidence interval, or empirically estimated effect.
- `registration.json`, `plan.json`, `receipt.json`: input identity, self-reported
  runtime, and exact output closure.

`verify` checks internal hashes/metadata only. **Use `verify --replay`** to
recompute the evidence. Gzip payloads are compared after decompression to avoid
confusing compression-library differences with scientific discrepancies.
The receipt still hashes actual compressed bytes. Neither check authenticates
history or proves the catalogue contains the real world. Full-input decidability
is built into this deterministic model, not evidence for the theory.

This independent lane is not included in the historical release manifest,
root `make verify`, or CI. Run its tests explicitly; also keep predecessor
verification green. No previous model, source, manuscript, or receipt is replaced.

See [derivation and sources](../../docs/research/2026-10-29-executability-twins/README.ja.md)
and [execution handoff](../../docs/research/2026-10-29-executability-twins/HANDOFF.ja.md).
