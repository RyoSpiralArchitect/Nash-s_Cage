# Waiting-contestability twins v0.1

F0 finite input-contract assay, not an empirical effect, equilibrium solver or real digital twin.
Read [the frozen contract](CONTRACT.ja.md). This lane is independent of the prior timing assay.

Python 3.10+, standard library only. CPU **one process**, no GPU, models, credentials or data acquisition.

```sh
python3 -B -m unittest discover -s experiments/waiting_contestability_twins_v01 -p 'test_*.py' -v
python3 -B experiments/waiting_contestability_twins_v01/run.py freeze --out .tmp/waiting-freeze
python3 -B experiments/waiting_contestability_twins_v01/run.py run --registration .tmp/waiting-freeze/registration.json --phase smoke --out .tmp/waiting-smoke
python3 -B experiments/waiting_contestability_twins_v01/run.py verify --out .tmp/waiting-smoke --replay
```

Full enumeration is a separate authorized step, with a fresh output directory:

```sh
python3 -B experiments/waiting_contestability_twins_v01/run.py run --registration .tmp/waiting-freeze/registration.json --phase enumeration --out .tmp/waiting-enumeration --acknowledge-f0-enumeration
python3 -B experiments/waiting_contestability_twins_v01/run.py verify --out .tmp/waiting-enumeration --replay
python3 -B experiments/waiting_contestability_twins_v01/audit.py .tmp/waiting-enumeration
```

Eight source files are hashed before execution, including the independent output audit.
No overwrite, automatic retry or parameter tuning after the enumeration is allowed.
Receipts and hashes establish same-tree consistency, not authenticated timestamps or empirical validity.
`verify` checks closure/hashes; `--replay` additionally regenerates results. Gzip replay compares decompressed JSONL.
`audit.py` independently recounts saved events/classes without importing the simulator; it is not another world generator.
Every class and every world is retained. Undefined time differences remain null, not zero.
The full-input view includes evaluator-only state and is not an implementable observation guarantee.

Furnace: inspect `spiral status`, transfer the eight files to a fresh isolated scratch directory,
test there, run once with `nice -n 19`, verify, and return exact artifacts. Preserve other workloads.
This new lane is not part of historical release closure, root `make verify`, or CI.
The paper, prior experiments and receipts are not modified by running it.
