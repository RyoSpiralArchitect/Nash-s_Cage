# Artifacts

`reference_run/` contains the committed F0 baseline for this reviewed tree. Its declared command is:

```bash
python3 -m simulation run \
  --config simulation/configs/minimal.json \
  --episodes 64 --seed 7 \
  --out artifacts/reference_run --overwrite
```

Verify it from the repository root:

```bash
make verify-artifact
```

Regenerate the declared run in a temporary directory and byte-compare all five deterministic outputs:

```bash
make verify-reference-replay
```

The artifact is a reproducibility fixture and an example of the output contract. It is also covered by `RELEASE_MANIFEST.json`. It is not a calibrated result, benchmark score, or empirical policy comparison.

For an ordinary experiment, write only to disposable scratch space:

```bash
make experiment
```

That target writes `.tmp/experiment` and cannot overwrite this committed fixture. After an intentional, reviewed model or configuration change, a maintainer may explicitly refresh the fixture with:

```bash
make refresh-reference
```

Review the changed `summary.csv`, `episodes.csv`, `trace.csv`, `comparison.md`, `resolved_config.json`, and `receipt.json`, then update `RELEASE_MANIFEST.json`, before committing. A source change invalidates the previous receipt even when numeric CSV outputs happen to remain unchanged.
