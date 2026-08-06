# Nash's Cage / RVCIM

[![Verify](https://github.com/RyoSpiralArchitect/Nash-s_Cage/actions/workflows/verify.yml/badge.svg)](https://github.com/RyoSpiralArchitect/Nash-s_Cage/actions/workflows/verify.yml)

**Robust Viability-Constrained Payoff-Inversion Governance under Unknown Irreversible Boundaries**

Nash's Cage is a conceptual model of governance systems in which local best responses, externalization, short horizons, partial observation, and institutional capture can jointly stabilize collective degradation. RVCIM is the companion architecture: preserve viability and justice as hard constraints, estimate remaining braking capacity, change the payoff field, and treat capture as part of the dynamic system rather than as background noise.

This repository keeps the manuscript beside a deliberately small executable reference model. The code is an **F0 structural toy**, not a climate forecast, an integrated assessment model, empirical validation, or a policy recommendation.

## Start in one minute

Requirements: Python 3.10 or newer. The simulator has no third-party runtime dependencies.

```bash
git clone https://github.com/RyoSpiralArchitect/Nash-s_Cage.git
cd Nash-s_Cage
make verify
```

Run the complete four-arm reference experiment:

```bash
make experiment
```

The direct Python form is equally valid:

```bash
python3 -m simulation run \
  --config simulation/configs/minimal.json \
  --episodes 64 --seed 7 \
  --out artifacts/reference_run --overwrite
```

The run writes:

- `summary.csv`: arm-level aggregate metrics
- `episodes.csv`: episode-level outcomes
- `trace.csv`: step traces for the configured number of episodes
- `comparison.md`: compact human-readable comparison
- `resolved_config.json`: the exact configuration after CLI overrides
- `receipt.json`: command, claim boundary, environment metadata, and SHA-256 hashes

Verify any run without rerunning it:

```bash
python3 -m simulation verify --receipt artifacts/reference_run/receipt.json
```

To see the model boundary before interpreting an output:

```bash
python3 -m simulation explain
```

## What is executable

The reference model instantiates four comparison arms using common episode seeds and random draws:

1. **Weak coupling**: monitoring with little transmission into incentives.
2. **Nominal trigger**: pressure-threshold response with limited capture defense.
3. **Robust reserve**: ambiguity-aware controllability-reserve triggers.
4. **Full RVCIM**: reserve triggers plus justice buffers, stronger audit, anti-capture separation, faster response, and release rules.

Each run contains heterogeneous actors, noisy and manipulable observation, an unknown realized boundary, a finite model ensemble, endogenous response delay, payoff-sensitive action, institutional degradation, justice and backlash dynamics, and explicit trigger-error accounting.

The committed 64-episode reference run is designed as a smokeable baseline, not as evidence. Under the declared normalized parameters, the arms form a visible mechanism gradient:

| Arm | Irreversible entry | Min hidden CR | Capture absorption | Justice stability | Defective action | False-negative trigger |
|---|---:|---:|---:|---:|---:|---:|
| Weak coupling | 1.000 | -16.171 | 0.212 | 0.246 | 0.767 | 0.816 |
| Nominal trigger | 1.000 | -17.190 | 0.391 | 0.145 | 0.689 | 0.056 |
| Robust reserve | 0.875 | -8.809 | 0.703 | 0.395 | 0.413 | 0.000 |
| Full RVCIM | 0.625 | 2.674 | 0.777 | 0.535 | 0.366 | 0.000 |

These values only show what the current toy assumptions produce. They do not estimate real risk or policy effect.

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
paper/
  nashs_cage_rvcim_v0_1.tex     original uploaded draft
  nashs_cage_rvcim_v0_1.pdf     reproducible v0.1 rendering
  nashs_cage_rvcim_v0_2.tex     feasibility and executability revision
  nashs_cage_rvcim_v0_2.pdf
  references.bib                 complete reproducible bibliography
simulation/
  rvcim_sim.py                   zero-dependency executable reference model
  configs/minimal.json           declared normalized reference configuration
  tests/test_rvcim_sim.py        deterministic standard-library tests
rvcim / rvcim.cmd                no-install POSIX and Windows launchers
artifacts/reference_run/
  summary.csv
  episodes.csv
  trace.csv
  comparison.md
  resolved_config.json
  receipt.json
.github/workflows/verify.yml      Python verification on push and pull request
```

## Paper

The current working manuscript is [`paper/nashs_cage_rvcim_v0_2.pdf`](paper/nashs_cage_rvcim_v0_2.pdf). Version 0.2 preserves the conceptual architecture and adds:

- an explicit F0 to F3 feasibility ladder
- a paper-to-code correspondence table
- a one-command reference experiment
- an implementation contract for seeds, outputs, trigger errors, and receipts
- a stronger boundary between executability and validation

Build it when `latexmk`, Biber, and the required TeX packages are installed:

```bash
make paper
```

## No-install launchers

The repository includes thin launchers that add no dependency or installation step:

```bash
./rvcim explain                 # macOS / Linux
rvcim.cmd explain               # Windows Command Prompt
```

They delegate directly to `python -m simulation`; the Python module remains the portable source of truth.

## Development commands

```bash
make help
make explain
make compile
make test
make smoke
make verify
make verify-artifact
make experiment
make paper
make clean
```

See [`simulation/README.md`](simulation/README.md) for mechanics and metric definitions, [`paper/README.md`](paper/README.md) for manuscript builds, and [`CONTRIBUTING.md`](CONTRIBUTING.md) for the claim-boundary discipline used for changes.

---

**日本語クイックスタート:** Python 3.10+ で `make verify`、四つの統治アームの比較は `make experiment` です。CSV、ステップトレース、解決済み設定、SHA-256 receipt が生成されます。現段階は F0 の構造実験であり、現実の気候予測や政策効果の推定ではありません。
