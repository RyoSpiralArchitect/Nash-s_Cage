# Nash's Cage / RVCIM

**Robust Viability-Constrained Payoff-Inversion Governance under Unknown Irreversible Boundaries**

Nash's Cage describes governance systems in which individually rational best responses, externalization, short horizons, partial observation, and institutional capture can jointly stabilize collective degradation. RVCIM is the companion architecture: preserve viability and justice as constraints, estimate remaining braking capacity, alter the payoff field, and model capture inside the control loop rather than as atmospheric background noise.

The repository now places the manuscript beside a deliberately small executable reference model. The code is an **F0 structural toy**. It is not a climate forecast, an integrated assessment model, empirical validation, or a policy recommendation.

## Research notes and prior work

The [Japanese research index](docs/research/README.ja.md) connects the theory proposals,
bounded real-data audits, and a growing [prior-work catalogue](docs/research/prior-work/README.ja.md).
The catalogue distinguishes prior contributions, study limitations, what we actually read,
and this project's interpretations. It includes existing institutional practices and critical
literature, not only supporting papers. Adding sources does not advance the F0 claim level.

The current [manuscript v0.3](paper/nashs_cage_rvcim_v0_3.pdf)
integrates joint executability, financial timing, shared-resource burdens, and
recipient-level revisability. Its [source](paper/nashs_cage_rvcim_v0_3.tex),
[revision and build record](docs/research/2026-10-28-manuscript-v03/README.ja.md),
and [additional source checks](docs/research/2026-10-28-manuscript-v03/SOURCE_NOTES.ja.md)
separate prior contributions from this project's prospective hypotheses.

## Start in one minute

Requirements: Python 3.10 or newer and Make. The simulator and verification tools have no third-party Python runtime dependencies.

```bash
git clone https://github.com/RyoSpiralArchitect/Nash-s_Cage.git
cd Nash-s_Cage
make verify
```

`make verify` checks the full executable closure against `RELEASE_MANIFEST.json`, compile-checks the package, runs deterministic standard-library tests, executes and verifies a four-arm smoke experiment, verifies the committed reference receipt, and replays the declared 64-episode reference command for byte comparison of its five deterministic outputs. It also verifies and replays the separate experimental v0.3 feasibility, v0.4 sustained-plan, and FY2024 fuel-carbon accounting bundles. The closure includes both launchers, package entrypoints, configurations, simulators, verifiers, tests, Makefile, CI workflow, checkout policy, papers, reference outputs, and fixed experiment inputs/outputs. Missing files, symlinks, CRLF-normalized tracked text, and replay mismatches are failures; there is no assembly or download step. CI is configured to run this contract on Linux and Windows with read-only permissions.

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

## Failure-first feasibility experiment (v0.3 experimental)

The preserved v0.2 run below is not a clean trigger comparison: capabilities vary
between arms, and hidden-state evaluation feeds part of its feedback loop. The
separate v0.3 engine removes that feedback path and compares three triggers with
matched capability parameters, measurement mechanisms, exogenous draws and initial
budget. It adds actual actuation/effect delays, capacity and command-slew bounds,
paid delivery, and explicit missing-evidence behavior. It does not establish a
recovery probability or sustained ability to brake.

```bash
make feasibility
make verify-feasibility
```

The first command creates a **new** `.tmp/feasibility` directory; an existing output
is never overwritten. For another run, choose a new path:

```bash
python3 tools/run_feasibility.py run --out .tmp/feasibility-second-run
python3 tools/run_feasibility.py verify --out .tmp/feasibility-second-run --replay
```

The fixed plan contains nine scenarios, three controllers, and 192 evaluation
episodes per scenario/controller (5,184 runs). All losses are retained. For example,
under common optimistic observation/model bias, there are ten paired cases where
the hysteretic threshold avoids irreversible entry and reserve does not. Average
performance does not erase these counterexamples. Zero budget, zero actuator
capacity, and entirely missing pressure observations each fail in every evaluation
episode for all three controllers under the declared fallback.

Read the [experimental contract](docs/FEASIBILITY_V03_CONTRACT.md),
[Japanese results and failure cases](docs/FEASIBILITY_V03_RESULTS.ja.md), and
[full comparison](artifacts/feasibility_v03/comparison.md). This remains F0: no live
data, real-world digital twin, intervention authority, or safety certificate.
The v0.2 simulator, configuration, manuscripts and reference artifacts are unchanged.

## Sustained-plan screen (v0.4 experimental)

The next separate experiment asks what v0.3 still could not: whether delayed
delivery can remain below a public model boundary, produce six terminal braking
steps, and preserve a terminal budget across a 24-step projection. It carries the
complete public actuator queues forward and returns only the first request of a
receding-horizon screen. `no candidate` means none of three constant-mode plans
passed this declared projection—not physical infeasibility.

```bash
make sustained
make verify-sustained
```

In the fixed synthetic evaluation, the sustained screen reduced baseline
irreversible entries from 17/48 to 7/48 and avoided all eleven post-hoc v0.3 losing
cases. But it kept emergency active for a mean 66.958 of 72 steps, spent the entire
baseline budget, and found no passing candidate for a mean 66.938 steps. Under an
optimistic policy-gain assumption it released earlier and introduced one additional
failure relative to the screen's baseline assumptions. Protection, sustainable
operation, and justified release therefore remain separate problems.

Read the [v0.4 contract](docs/SUSTAINED_V04_CONTRACT.md),
[Japanese results and missing pieces](docs/SUSTAINED_V04_RESULTS.ja.md), and
[full comparison](artifacts/sustained_v04/comparison.md). These are F0 outcomes,
not estimates of real risk or institutional feasibility.

## First real-data input: Japan FY2024 fuel-carbon accounting

```bash
make power-accounting
make verify-power
```

The separate standard-library accounting CLI joins 21 nonzero fossil-family fuel
leaves within one published annual business-generation scope. Seventeen reconcile,
diesel retains a coefficient mismatch, and three remain unmapped. Oil is the next
selected entry point, specifically power-generation C fuel oil; this is not a
finding that oil is currently scarcer than other fuels.

Read the [Japanese results and oil input contract](docs/POWER_ACCOUNTING_RESULTS.ja.md)
and [source/extraction contract](data/power_jp_fy2024/README.md). The frozen factual
extract can be independently reproduced from two hash-pinned public workbooks.
Default offline replay does not download or re-open those workbooks. Carbon-input
closure is not independent emissions validation, a net-MWh intensity, an avoided
emissions estimate, current inventory, or an authorized dispatch decision. It does
not calibrate the synthetic RVCIM model or advance its F0 claim level.

## Preserved v0.2 executable

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

These values show only what the preserved toy assumptions produce. They do not estimate real risk or policy effect, and the unequal capabilities and truth-fed feedback make this table unsuitable for isolating trigger quality. See the separate v0.3 experiment above.

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
  feasibility.py                separate public-input, paid-delivery experiment
  sustained.py                  finite queue/resource/braking plan screen
  configs/minimal.json           declared normalized reference configuration
  configs/feasibility_v03.json    declared experimental resource/delay settings
  configs/feasibility_stress_plan.json  fixed scenarios and evaluation seeds
  configs/sustained_v04.json     declared finite-projection assumptions
  configs/sustained_stress_plan.json  fixed primary and prior-failure cohorts
  tests/test_rvcim_sim.py        deterministic standard-library tests
tools/
  verify_release.py              fail-closed release-manifest verifier
  verify_reference_replay.py     64-episode deterministic replay verifier
  run_feasibility.py             new-only experiment runner and replay verifier
  run_sustained.py               sustained experiment runner and replay verifier
  run_power_accounting.py        bounded fuel-carbon extractor and replay runner
data/power_jp_fy2024/              source-linked factual extract and raw recheck instructions
paper/
  nashs_cage_rvcim_v0_1.tex     operator-attested preserved source
  nashs_cage_rvcim_v0_1.pdf     operator-attested preserved PDF
  nashs_cage_rvcim_v0_2.tex     operator-attested regenerated revision
  nashs_cage_rvcim_v0_2.pdf
  references.bib                 preserved v0.1/v0.2 bibliography
  nashs_cage_rvcim_v0_3.tex     joint-executability research revision
  nashs_cage_rvcim_v0_3.pdf
  references_v0_3.bib           separate expanded bibliography
docs/research/                   dated research notes and prior-work catalogue
experiments/cross_domain_audit_v01/  frozen public-data descriptive audit
artifacts/cross_domain_audit_v01/    source-specific attribution and replay inputs
artifacts/reference_run/          committed reproducibility fixture
artifacts/feasibility_v03/        failure-first experimental fixture
artifacts/sustained_v04/           finite-plan experimental fixture
artifacts/power_jp_fy2024/          empirical accounting rows with explicit unknowns
rvcim / rvcim.cmd                no-install POSIX and Windows launchers
.github/workflows/verify.yml      portable verification workflow
.gitattributes                    LF checkout policy for deterministic hashes
RELEASE_MANIFEST.json             hashes, sizes, and provenance boundary
```

The [2026-09-05 pre-merge review record](docs/PREMERGE_REVIEW_20260905.md)
separates fresh-review findings, repairs, and local/Furnace execution evidence.

## Paper revision

Version 0.3 (28 October 2026) preserves v0.1/v0.2 and their bibliography. It adds
prior contributions and critical literature, an actor/time/resource execution
contract, a prospective payment-timing hypothesis, explicit distinctions among
liquidity, scarcity, performance uncertainty and incentive conflict, and
recipient-level correction and release requirements. Existing synthetic losses
and frozen administrative descriptions remain distinct from causal evidence.
This is a manuscript revision, not a new simulator release or an F0 promotion;
the historical release metadata remains unchanged.

Build the current manuscript when `latexmk`, XeLaTeX, BibTeX, and the required TeX packages are installed:

```bash
make paper
```

Use `make paper-v02` for the preserved v0.2 source. Builds go to `.tmp/paper/` and
never overwrite committed PDFs. The manifest identifies the committed rendering
for same-tree consistency, not independent source-to-PDF attestation. Builds are
not expected to be byte-identical across engines, packages, fonts, or metadata.
The [revision record](docs/research/2026-10-28-manuscript-v03/README.ja.md)
states the toolchain actually exercised locally; Python CI alone is not a TeX build.

The frozen cross-domain snapshot has its own receipts and separate CI replay;
it is not included in the 64-file release/manuscript manifest. See its
[attribution and verification boundary](artifacts/cross_domain_audit_v01/README.md).

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
make feasibility
make verify-feasibility
make sustained
make verify-sustained
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
