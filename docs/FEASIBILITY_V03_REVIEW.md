# Fresh review and repair record — feasibility v0.3

Date: 2026-09-04. Scope: the experimental model, matched comparison, exporter,
replay verifier, tests and portable verification wiring. No real-world validity
review or security certification is implied.

## Fresh reviewer output

A read-only reviewer received no parent conversation and inspected the visible
repository. Project-local memory hiding found zero files; the temporary freeze
lock was removed after each review. This is a best-effort fresh view, not a claim
that host-injected instructions or context were erased.

The first review found two actionable defects:

1. **P1 — cross-runtime replay:** raw floating-point export differed between
   Python 3.10.20 and 3.13.13, for example `0.07619999999999999` versus `0.0762`.
   Requiring byte equality while exporting runtime-dependent last bits would
   fail the declared CI matrix.
2. **P2 — mixed release evidence:** hysteretic threshold reused a release streak
   for different destinations. From emergency, pressure `.70,.70,.62` prematurely
   released to normal; `.65` repeated could remain in emergency even though it
   qualified to downshift to precaution.

The reviewer found no additional consequential issue within the bounded review
of hidden-truth separation, physical delay queues, paid delivery and matched
capabilities. The disclosed one-tick response proxy remains a scientific limit.

After repair, the same reviewer reported: both fixes address the defects, with
no remaining blocker or new material issue found in the bounded re-review.
They independently checked nine short scenarios across both Python runtimes and
the 65 engine/runner tests. Full-plan replay was left to the main task and passed.

## Stateful annotation and repairs

Both findings were accepted and fixed, not explained away as toy-model assumptions.

- CSV/JSON now export finite floats rounded to nine decimal places. Missing
  estimates stay null/empty, nonfinite values fail, and negative zero is normalized.
  Computation itself is not rounded. The encoding is declared in the receipt.
- Normal and precaution release have independent qualifying counters. An
  observation cannot donate evidence to a stricter target. A direct emergency to
  normal release still works after three genuinely normal-qualified observations.
- Six regression tests first reproduced the hysteresis failures, then passed
  after repair. Serialization regression tests exercise the cross-runtime example.
- Neither the numerical configuration, nine scenarios, nor evaluation seeds changed.
  The entire evaluation was rerun; aggregate irreversible-entry counts happened to
  remain the same, while some hysteretic-controller durations and costs changed.

The initial, superseded output remains at `.tmp/feasibility-evaluation-01` in the
working checkout; its receipt intentionally no longer matches current source.
It is not the committed fixture and must not be treated as current verified output.
The final six-file fixture is `artifacts/feasibility_v03/`.

## Verification evidence

- `make verify` passed on macOS with Python 3.13.13: all 120 tests, release closure
  of 37 files, legacy smoke/receipt verification, old five-output replay and new
  six-file full-plan replay.
- Python 3.10.20 replayed the same final 5,184-run feasibility fixture byte-for-byte
  at the declared output precision.
- A clean export containing tracked and nonignored new project files, but no Git
  metadata or working scratch outputs, passed the complete `make verify` contract
  under Python 3.10.20 from its own extracted directory. This was a working-tree
  export, not an assertion that these changes had been committed or published.
- Legacy source/config/package entrypoints/tests/manuscript/reference outputs
  remain byte-identical to base commit `1ac0349baedde12c0ea97c16379322660b109b15`.
- Windows CI now checks every native command's exit code, with regression tests
  for removal. No Windows execution or new GitHub Actions run is claimed here.

These checks establish local internal consistency and the named implementation
contracts. They do not establish empirical accuracy, sustainable controllability,
institutional legitimacy, deployment readiness, or authorization to act.
