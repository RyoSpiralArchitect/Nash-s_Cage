# Heat public evidence audit v0.1

2026-09-09, public official documents only. **Descriptive evidence, not an empirical
digital twin, policy-effect estimate, legal judgment, clinical safety test, or
authorization to intervene.** No private conversation or worker records were imported.

## Current entry points

- `report.html`: self-contained report, checked on 2026-09-09; no hosted site.
- `analysis-r02/audit.json`: descriptive results and three unresolved calibration gates.
- `analysis-r02/audit.ipynb`: inspectable companion notebook. Three code cells executed
  sequentially through Python's standard `exec` in a shared namespace; Jupyter kernel
  execution is not claimed (nbformat/nbclient were unavailable in checked runtimes).
- `analysis-r02/artifact.json`: canonical source for the HTML report.
- `analysis-r02/receipt.json`: source, input, output hashes; replay with the lane CLI.
- `VALIDATION.json`: technical checks, claim ceilings and HTML delivery receipt.
- `sources/`: eight public source snapshots; expected closure and SHA-256 values are
  in `experiments/heat_public_audit_v01/evidence.json`.
- `qa/`: rendered PDF pages used to inspect denominators, footnotes and case sequences.

The Japanese empirical input contract is
`experiments/heat_public_audit_v01/CONTRACT.ja.md`. The executable provides a public
evidence audit plus small, tested coverage-bound, timing and realized-cash helpers.
It is not a full private-record intake/authorization pipeline.

## Verification

From the repository root:

```sh
python3 -m unittest discover -s experiments/heat_public_audit_v01 -v
python3 experiments/heat_public_audit_v01/run.py --out artifacts/heat_public_audit_v01/analysis-r02 --verify
```

To generate another snapshot, omit `--verify` and use a new output directory. To
package its canonical report, use the installed Data Analytics portable builder:

```sh
node "$DATA_ANALYTICS_PLUGIN_ROOT/skills/build-report/scripts/deliver_portable_artifact.mjs" --input artifacts/heat_public_audit_v01/analysis-r02/artifact.json --output NEW_REPORT.html
```

Set `DATA_ANALYTICS_PLUGIN_ROOT` to the installed Data Analytics plugin directory
(the delivered snapshot used version `0.2.10-13ceeea1f599`). Use a new output file;
do not replace the frozen delivered report. The builder is an installed local
dependency, not vendored into Nash's Cage. The
delivered HTML needs no such dependency, server, external scripts or data sidecars.
The chart/table are generated from manually transcribed public JSON by the exact
SQLite queries stored in their source metadata. SQL execution does not establish
the correctness of the manual source reading; relevant source pages were also inspected.

## Analysis validation

Assessment: **Share with caveats**, as a bounded research audit only.

- Coverage: institutional reach is not a national implementation denominator.
  The construction questionnaire describes accident-involved member establishments;
  its precise membership scope comes from the final committee report, not inference.
- Timing: zero of the 19 published fatal-case summaries supplies both exact clock
  anchors under the chosen recognition/initial-cooling definition. This is a document
  completeness measure, never a zero-response finding. Three other approximate event
  intervals are retained with distinct anchors and never averaged as response latency.
- Costs: estimation, approval, paid transfers, resources used and ultimate economic
  incidence are separate. The 2026 cost rule supersedes the 2025 rule in its stated
  scope; its 100% cap is not 100% income protection.
- National outcomes: use the same 2026 final publication for both 2024 and 2025.
  Deaths are included in casualties. No causal estimate is calculated from the change.
- Missing inputs: exposed-worker/protection-opportunity denominator, representative
  event records and linked contract/payment/payroll evidence. All remain UNKNOWN.

No material transcription or calculation discrepancy remained after the checks.
At the 2026-09-09 checkpoint, no independent adversarial review, new Furnace run,
new Windows CI, commit, push, PR creation or merge was performed for this lane.
See `docs/HEAT_RESEARCH_RELEASE.ja.md` for the later PR/CI integration boundary.
It is separate from the historical
61-file release manifest; passing root `make verify` is predecessor regression
evidence, not admission of these new files to that release.

## Preserved packaging failure

`analysis/` is the first descriptive draft. Its HTML packaging failed because the
report renderer required an executable SQL source for the chart/table. Its exact
four authored inputs are retained in `history/r01_inputs/`. This draft is not the
delivered report. The r02 revision adds genuinely executed, self-contained SQLite
transcription queries; it does not change the public measurements or turn them into
empirical simulation coefficients. Final packaging and responsive checks passed.

No source data or preceding heat simulation input/result was deleted or replaced.
