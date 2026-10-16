# Heat institution v0.1 artifacts

Independent F0 synthetic lane; not part of the historical 61-file release closure.

- `development/`: 1,280 arm-seasons, generated on Mac, separate development seeds.
- `evaluation/`: 10,240 arm-seasons, generated on Furnace, replayed on Furnace and Mac.
- Both carry the same pre-execution local registration and exact input hashes.
- The 80 conditions are 72 factorial cells and eight named controls; see each
  row's cohort. No global winner or real-world effect is claimed.

From the repository root:

```sh
python3 experiments/heat_institution_v01/run.py verify --out artifacts/heat_institution_v01/development --replay --input-revision r01
python3 experiments/heat_institution_v01/run.py verify --out artifacts/heat_institution_v01/evaluation --replay --processes 2 --input-revision r01
```

See `docs/HEAT_INSTITUTION_V01_RESULTS.ja.md` for post-run interpretation and
`experiments/heat_institution_v01/CONTRACT.ja.md` for the pre-execution contract.
Interpretation is outside the frozen numerical input set and must not be confused
with preregistered findings. No historical receipt has been replaced.

The original six inputs are preserved in `history/r01_inputs/`. The current runner
adds strict checks for receipt trust claims, runtime schema, local-registration
scope and UTC timestamp. `--input-revision r01` is available only for verification:
it pins the original development/evaluation receipts and reconstructs numerical
outputs with the current code without executing archived code. New experiments
require a new freeze of the current inputs. Runtime and registration times remain
self-reported; schema checks do not authenticate them or imply empirical validity.
