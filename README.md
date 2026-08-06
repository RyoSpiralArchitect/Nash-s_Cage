# Nash's Cage / RVCIM

**Robust Viability-Constrained Payoff-Inversion Governance under Unknown Irreversible Boundaries**

Nash's Cage describes governance systems in which individually rational best responses, externalization, short horizons, partial observation, and institutional capture can jointly stabilize collective degradation. RVCIM is the companion architecture: preserve viability and justice as constraints, estimate remaining braking capacity, alter the payoff field, and model capture inside the control loop rather than as atmospheric background noise.

The repository now places the manuscript beside a deliberately small executable reference model. The code is an **F0 structural toy**. It is not a climate forecast, an integrated assessment model, empirical validation, or a policy recommendation.

## Start in one minute

Requirements: Python 3.10 or newer. The simulator has no third-party runtime dependencies.

```bash
git clone https://github.com/RyoSpiralArchitect/Nash-s_Cage.git
cd Nash-s_Cage
make verify
```

`make verify` compile-checks the package, runs deterministic standard-library tests, executes a four-arm smoke experiment, and verifies its SHA-256 receipt.

The simulator is directly runnable from the checked-in, hash-verified source payload. To expand the ordinary Python, TeX, and bibliography files for inspection or editing:

```bash
make materialize
```

## Restore the exact manuscript package

The repository history also contains the complete verified release archive, including the exact uploaded v0.1 PDF and TeX source, the feasibility-focused v0.2 revision, bibliography, full simulator source, and reference artifacts.

Restore all of them into the working tree with one command:

```bash
make restore-release
```

The restorer uses only Python and Git. It fetches eight archive chunks from this repository, verifies the archive SHA-256, rejects unsafe archive paths, restores the expected files, and verifies the uploaded inputs:

- `nashs_cage_rvcim_v0_1.pdf`: `4ded46a5fee179182f40f671ab1345453dceda8e534b713eee775d628cf65d2e`
- `nashs_cage_rvcim_v0_1.tex`: `6f0d0d7f47df6bdb38ff41bca32b5b5108d7254f07825b069349e53f2c3ad5b7`

This path does not depend on GitHub Actions or a TeX installation.

## Run the complete experiment

```bash
make experiment
```

Equivalent direct invocation:

```bash
python3 -m simulation run \
  --config simulation/configs/minimal.json \
  --episodes 64 --seed 7 \
  --out artifacts/reference_run --overwrite
```

A run writes:

- `summary.csv`: arm-level aggregate metrics
- `episodes.csv`: episode-level outcomes
- `trace.csv`: step traces for the configured number of episodes
- `comparison.md`: compact human-readable comparison
- `resolved_config.json`: the exact configuration after CLI overrides
- `receipt.json`: command, claim boundary, environment metadata, and SHA-256 hashes

Verify a run without rerunning it:

```bash
python3 -m simulation verify --receipt artifacts/reference_run/receipt.json
```

Inspect the claim boundary and paper-to-code map first:

```bash
python3 -m simulation explain
```

## What is executable

The reference model compares four governance arms under common episode seeds and random draws:

1. **Weak coupling**: monitoring with little transmission into incentives.
2. **Nominal trigger**: pressure-threshold response with limited capture defense.
3. **Robust reserve**: ambiguity-aware controllability-reserve triggers.
4. **Full RVCIM**: reserve triggers plus justice buffers, stronger audit, anti-capture separation, faster response, and release rules.

Each run contains heterogeneous actors, noisy and manipulable observation, an unknown realized boundary, a finite model ensemble, endogenous response delay, payoff-sensitive action, institutional degradation, justice and backlash dynamics, and explicit trigger-error accounting.

The verified 64-episode package is a smokeable baseline, not evidence. Under its declared normalized parameters, it produces this mechanism gradient:

| Arm | Irreversible entry | Min hidden CR | Capture absorption | Justice stability | Defective action | False-negative trigger |
|---|---:|---:|---:|---:|---:|---:|
| Weak coupling | 1.000 | -16.171 | 0.212 | 0.246 | 0.767 | 0.816 |
| Nominal trigger | 1.000 | -17.190 | 0.391 | 0.145 | 0.689 | 0.056 |
| Robust reserve | 0.875 | -8.809 | 0.703 | 0.395 | 0.413 | 0.000 |
| Full RVCIM | 0.625 | 2.674 | 0.777 | 0.535 | 0.366 | 0.000 |

These values show only what the current toy assumptions produce. They do not estimate real risk or policy effect.

## Claim boundary and feasibility ladder

| Level | Object | Admissible claim |
|---|---|---|
| F0 | Executable structural toy | The formal pieces compose into a coherent, inspectable, reproducible loop. |
| F1 | Stylized calibrated model | A narrow mechanism reproduces selected regularities under documented assumptions and validation tests. |
| F2 | Sectoral or jurisdictional shadow model | The system may support bounded, non-actuating decision analysis with explicit legal and data scope. |
| F3 | Reversible institutional pilot | A specific mechanism is operationally feasible under declared authority, appeal, release, compensation, and rollback conditions. |

This repository is currently at **F0**. Cleaner execution makes assumptions easier to inspect and attack. It does not make those assumptions true.

## Repository map

```text
simulation/
  rvcim_sim.py                   transparent zero-dependency loader / materialized source
  configs/minimal.json           declared normalized reference configuration
  tests/test_rvcim_sim.py        deterministic standard-library tests
tools/
  restore_release.py             checksum-verified exact release restorer
paper/                            ordinary files appear after make materialize/restore-release
  nashs_cage_rvcim_v0_1.tex     exact uploaded source
  nashs_cage_rvcim_v0_1.pdf     exact uploaded PDF
  nashs_cage_rvcim_v0_2.tex     feasibility and executability revision
  nashs_cage_rvcim_v0_2.pdf
  references.bib
artifacts/reference_run/          restored or regenerated reference package
rvcim / rvcim.cmd                no-install POSIX and Windows launchers
.github/workflows/verify.yml      portable verification workflow
```

## Paper revision

Version 0.2 preserves the conceptual architecture and adds:

- an explicit F0 to F3 feasibility ladder
- a paper-to-code correspondence table
- a one-command reference experiment
- an implementation contract for seeds, outputs, trigger errors, and receipts
- a stronger boundary between executability and validation

After `make materialize`, build it when `latexmk`, Biber, and the required TeX packages are installed:

```bash
make paper
```

`make restore-release` is the faster route when the prebuilt PDFs are sufficient.

## No-install launchers

```bash
./rvcim explain                 # macOS / Linux
rvcim.cmd explain               # Windows Command Prompt
```

They delegate directly to `python -m simulation`; the Python module remains the portable source of truth.

## Development commands

```bash
make help
make verify
make experiment
make materialize
make restore-release
make explain
make compile
make test
make smoke
make verify-artifact
make paper
make clean
```

See [`simulation/README.md`](simulation/README.md) for mechanics and metric definitions, [`paper/README.md`](paper/README.md) for manuscript builds, and [`CONTRIBUTING.md`](CONTRIBUTING.md) for the claim-boundary discipline used for changes.

---

**日本語クイックスタート:** Python 3.10+ だけで `make verify` が動きます。完全な原稿・PDF・reference artifact は `make restore-release`、四つの統治アームの再実験は `make experiment` です。現段階は F0 の構造実験であり、現実の気候予測や政策効果の推定ではありません。
