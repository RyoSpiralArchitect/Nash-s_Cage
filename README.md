# Nash's Cage / RVCIM

**Robust Viability-Constrained Payoff-Inversion Governance under Unknown Irreversible Boundaries**

Nash's Cage describes governance systems in which individually rational best responses, externalization, short horizons, partial observation, and institutional capture can jointly stabilize collective degradation. RVCIM is the companion architecture: preserve viability and justice as constraints, estimate remaining braking capacity, alter the payoff field, and model capture inside the control loop rather than as atmospheric background noise.

The repository now places the manuscript beside a deliberately small executable reference model. The code is an **F0 structural toy**. It is not a climate forecast, an integrated assessment model, empirical validation, or a policy recommendation.

## Start in one minute

Requirements: Python 3.10 or newer and Make. The simulator and verification tools have no third-party Python runtime dependencies.

```bash
git clone https://github.com/RyoSpiralArchitect/Nash-s_Cage.git
cd Nash-s_Cage
make verify
```

`make verify` checks the full executable closure against `RELEASE_MANIFEST.json`, compile-checks the package, runs deterministic standard-library tests, executes and verifies a four-arm smoke experiment, verifies the committed reference receipt, and replays the declared 64-episode reference command for byte comparison of its five deterministic outputs. The closure includes both launchers, package entrypoints, configuration, simulator, verifiers, tests, Makefile, CI workflow, checkout policy, papers, and reference outputs. Missing files, symlinks, CRLF-normalized tracked text, and replay mismatches are failures; there is no assembly or download step. CI runs this contract on Linux and Windows with read-only permissions.

## Release files and provenance

The readable Python, TeX, bibliography, PDFs, and reference results are ordinary checked-in files. In particular:

- `nashs_cage_rvcim_v0_1.pdf`: `4ded46a5fee179182f40f671ab1345453dceda8e534b713eee775d628cf65d2e`
- `nashs_cage_rvcim_v0_1.tex`: `6f0d0d7f47df6bdb38ff41bca32b5b5108d7254f07825b069349e53f2c3ad5b7`

Those are the current v0.1 file identities. The repository records v0.1 as an **operator-attested preserved upload**: an available history anchor supports the TeX source, while an independent Git-history anchor for the PDF is unavailable. The v0.2 source and PDF in this tree are operator-attested regenerations made on 7 August 2026 from v0.1 and the executable-companion contract after an earlier bootstrap representation proved incomplete. They are deliberately **not** claimed to be byte-identical to an unavailable earlier v0.2 build.

`RELEASE_MANIFEST.json` checks internal consistency of a checkout. Because the manifest, verifier, and files live in the same tree, they do not self-authenticate historical provenance. The external anchor is the reviewed Git commit (and any separately retained signature or archive), not a literal hash repeated inside the same commit.

## Run a disposable complete experiment

```bash
make experiment
```

Equivalent direct invocation:

```bash
python3 -m simulation run \
  --config simulation/configs/minimal.json \
  --episodes 64 --seed 7 \
  --out .tmp/experiment --overwrite
```

A run writes:

- `summary.csv`: arm-level aggregate metrics
- `episodes.csv`: episode-level outcomes
- `trace.csv`: step traces for the configured number of episodes
- `comparison.md`: compact human-readable comparison
- `resolved_config.json`: the exact configuration after CLI overrides
- `receipt.json`: command, claim boundary, declared environment metadata, and SHA-256 hashes

Verify a run without rerunning it:

```bash
python3 -m simulation verify --receipt .tmp/experiment/receipt.json
```

`make experiment` never targets the committed fixture. Maintainers can run the deliberately explicit `make refresh-reference` after a reviewed model or configuration change, then inspect every changed artifact and update the manifest before committing.

Replacing an existing output directory requires an atomic directory-exchange primitive. Linux and macOS use that primitive when the filesystem supports it. On Windows or an unsupported filesystem, `--overwrite` refuses the replacement and leaves the verified target unchanged; choose a new output path instead. Fresh output directories remain fully supported on every declared platform.

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
  rvcim_sim.py                   transparent zero-dependency implementation
  configs/minimal.json           declared normalized reference configuration
  tests/test_rvcim_sim.py        deterministic standard-library tests
tools/
  verify_release.py              fail-closed release-manifest verifier
  verify_reference_replay.py     64-episode deterministic replay verifier
paper/
  nashs_cage_rvcim_v0_1.tex     operator-attested preserved source
  nashs_cage_rvcim_v0_1.pdf     operator-attested preserved PDF
  nashs_cage_rvcim_v0_2.tex     operator-attested regenerated revision
  nashs_cage_rvcim_v0_2.pdf
  references.bib
artifacts/reference_run/          committed reproducibility fixture
rvcim / rvcim.cmd                no-install POSIX and Windows launchers
.github/workflows/verify.yml      portable verification workflow
.gitattributes                    LF checkout policy for deterministic hashes
RELEASE_MANIFEST.json             hashes, sizes, and provenance boundary
```

## Paper revision

Version 0.2 preserves the conceptual architecture and adds:

- an explicit F0 to F3 feasibility ladder
- a paper-to-code correspondence table
- a one-command reference experiment
- an implementation contract for seeds, outputs, trigger errors, and receipts
- a stronger boundary between executability and validation

Build v0.2 when `latexmk`, XeLaTeX, BibTeX, and the required TeX packages are installed:

```bash
make paper
```

The build is written to `.tmp/paper/nashs_cage_rvcim_v0_2.pdf`; it does not overwrite either committed PDF. The manifest hash identifies the current committed rendering for same-tree consistency; it does not independently prove a source-to-PDF derivation. A local rebuild checks source buildability but is not expected to be byte-identical across TeX engines, package sets, fonts, or embedded creation metadata.

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
make refresh-reference            # explicit maintainer operation
make explain
make verify-release
make verify-reference-replay
make compile
make test
make smoke
make verify-artifact
make paper
make clean
```

See [`simulation/README.md`](simulation/README.md) for mechanics and metric definitions, [`paper/README.md`](paper/README.md) for manuscript builds, and [`CONTRIBUTING.md`](CONTRIBUTING.md) for the claim-boundary discipline used for changes.

---

**日本語クイックスタート:** Python 3.10+ と Make で `make verify` が動きます。Python verifier と simulator 自体には third-party package は不要です。原稿・PDF・reference artifact は通常ファイルとして同梱され、四つの統治アームの再実験は `.tmp/experiment` に生成されます。v0.1 は operator-attested な保存版、v0.2 は出自を明示した再生成版で、同一 tree 内の manifest は履歴を自己証明しません。現段階は F0 の構造実験であり、現実の気候予測や政策効果の推定ではありません。
