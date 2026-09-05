# Pre-merge review and execution record

2026-09-05. Scope: accumulated experimental v0.3/v0.4 work and the first
Japan FY2024 fuel-carbon input, against base commit
`1ac0349baedde12c0ea97c16379322660b109b15`.

## Fresh reviewer output

A read-only reviewer was started without the parent conversation. The
project-local context freeze found zero files; the temporary lock was removed
immediately after each review. This is best-effort fresh review, not erasure of
host-injected instructions. The initial reviewer reported:

> One actionable finding; no other merge-blocking defects found in the bounded review.
>
> [P2] Reject nonfinite controller history before making a request.
>
> Controller-state validation checks only its DTO type and authorized mode, then
> consumes `smoothed_trend` unchecked. With otherwise valid inputs, `-inf` changes
> the default precaution request into `sufficient_evidence /
> plan_found_within_declared_model / mode 0`; every candidate passes despite
> `-inf` projected pressures. `NaN` instead produces a new emergency request,
> not the promised insufficient-evidence hold. Validate numerical history before
> the v0.3 decision/projection, including previous pressure used to update the trend.

The reviewer ran 110 accounting, sustained-engine, sustained-runner and
release-verifier tests, reproduced the extract from both pinned workbooks, and
inspected units, scope gates, actuator mechanics, receipt paths and CI wiring.
They did not run the full experiment matrix or Windows CI.

## Stateful annotation and repair

The finding was accepted as a public-API validation defect. It is not evidence
that a committed evaluation episode actually encountered corrupt history.

- The v0.4 decision now validates numerical controller history before calling
  v0.3. Nonfinite, boolean or string history holds the prior authorized request,
  clears release evidence, increments unknown counters and produces no plan.
- Corrupt numerical history is not replaced by invented observations. The
  caller must supply valid history before decisions resume. Invalid counters
  or timestamps raise before decision-making.
- Direct projection rejects invalid numerical history; arithmetic overflow from
  finite inputs cannot produce a passing projection.
- Four regression tests cover these boundaries. No v0.3 source/configuration or
  earlier fixture was edited.
- The operator also added loaded-source and during-computation input-identity
  checks to the accounting receipt builder, with two regression tests.

The narrow read-only re-review reported:

> The P2 is resolved. No new blocker found in the narrow repairs.
>
> Original `-inf`/`NaN` reproducer now returns `insufficient_evidence`, holds the
> prior request, and emits no projections. Thirty additional corrupt-history
> combinations were rejected before reaching the v0.3 decision. All 56 targeted
> tests passed. Simulated loaded-code mismatch and changes to either code or
> data during accounting computation were rejected.

## Operator execution evidence

- Final `make verify` passed on macOS / Python 3.13.13: 208 explicit tests,
  61-file release closure, legacy smoke/receipt verification, legacy five-output
  replay, full v0.3/v0.4 fixture replay, and fuel-carbon replay.
- A clean working-tree export passed the same full command on Furnace / Linux /
  Python 3.14.4. This was CPU execution in an isolated scratch directory, not a
  GPU benchmark or use of another job's checkout.
- The v0.3 evaluation comprises 5,184 runs; v0.4 comprises 960 primary and 44
  post-hoc regression runs. Replaying them does not create new independent
  scientific observations.
- Final `verify-sources` also passed on Furnace using the two original pinned
  workbooks. Local independent `openpyxl` reading agreed on all 21 selected fuel
  labels, energy/carbon values and mapped coefficient values. `openpyxl` is not
  a runtime or CI dependency of the shipped tool.
- After repair, all five v0.4 data files and all three accounting data files were
  byte-identical to the pre-review results. Only their source-binding receipts
  changed. The model parameters, cohorts, seeds and scientific conclusions did not.
- Legacy engine/configuration, entrypoints/tests, manuscript files and the
  v0.2 reference fixture remain byte-identical to the base commit (17 files).

Final receipts:

- [Sustained v0.4](../artifacts/sustained_v04/receipt.json):
  `71574770dfefe79e1c58d29af5cc6200c2fe18afb1aa291958e38c87dec4d3f5`
- [Fuel-carbon accounting](../artifacts/power_jp_fy2024/receipt.json):
  `476b2388a92e70de99724b81cb2f8cf5f7f703fc4512e3715d14591dc86793d5`

An initial Mac archive added AppleDouble sidecars on Linux. Exact-file-set replay
correctly rejected that transferred fixture even though raw extraction and the
fresh Linux run passed. Re-exporting without Mac metadata resolved transport
packaging; no scientific input or result was changed to make it pass.

This record precedes publication. GitHub PR/Actions state is the evidence for
remote CI and merge, not this local report. Passing replay establishes the named
software/accounting contracts, not real-world feasibility, policy effect,
resource availability, or authorization to act.
