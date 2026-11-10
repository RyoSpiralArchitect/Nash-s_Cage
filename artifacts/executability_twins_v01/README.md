# Executability twins — full enumeration and retained engineering qualification

2026-11-04 JST. The frozen full catalogue has now run once on Furnace. The
[enumeration](enumeration_20261104/) retains the seven original files, separate
from qualification. A one-process replay matched the two-process run. See the
[results, limitations and independent recount](../../docs/research/2026-11-04-executability-twins/RESULTS.ja.md).

## Historical smoke checkpoint

2026-10-29 JST. F0. The `qualification_20261029/` folder contains a **smoke-only**
checkpoint: 12 authored worlds, 48 arm-worlds. Full enumeration had not run at this checkpoint.
No real people, private conversations, institutional records, or API data are here.

- `freeze/registration.json`: seven source hashes fixed before the retained runs.
  Engineering tests had already exercised these authored cases; this is not a
  blind test, public preregistration, or authenticated historical timestamp.
- `local-smoke/`: retained Mac output, one CPU process.
- `furnace-smoke/`: retained Furnace output, two CPU processes.
- `source.tar.gz`: the exact seven input files, repository-relative paths,
  with extended attributes excluded. An archive, not a new supported entrypoint.
- `qualification.json`: operator-recorded validation and identity summary.

The six non-receipt files in the two runs are byte-identical. Runtime receipts
correctly differ. Source hashes match on both machines. The source archive's
seven member contents were independently compared to those hashes (not an
independent implementation of the model). Both hosts passed the 27 lane tests.

## Reproduce with the current exact source

From the repository root:

```sh
python3 -B -m unittest discover -s experiments/executability_twins_v01 -p 'test_*.py' -v
python3 -B experiments/executability_twins_v01/run.py verify --out artifacts/executability_twins_v01/qualification_20261029/local-smoke --replay --processes 2
python3 -B experiments/executability_twins_v01/run.py verify --out artifacts/executability_twins_v01/qualification_20261029/furnace-smoke --replay --processes 1
```

If future code changes, retain this checkpoint and its input archive. Verification
against changed current source must fail. Inspect and restore the archive only
into a fresh isolated directory if historical replay is needed; do not overwrite
the active source or an older result. No automatic archive execution is provided.

See the [contract](../../experiments/executability_twins_v01/CONTRACT.ja.md)
and [handoff](../../docs/research/2026-10-29-executability-twins/HANDOFF.ja.md).
These receipts are internal consistency records, not signatures, empirical
validation, external review, CI, a published release, or proof of model coverage.
