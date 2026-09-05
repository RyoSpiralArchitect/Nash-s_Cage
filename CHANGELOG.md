# Changelog

## Unreleased - v0.3 experimental first path - 2026-09-04

- preserved the v0.2 engine, configuration, manuscripts and reference outputs
- added an independent public-input controller/actor/social loop with no truth-label feedback
- implemented real actuation and effect queues, capacity/command-slew constraints,
  and finite-budget delivery; disclosed affordability shutdown and proxy limitations
- matched threshold, hysteretic threshold and reserve capability parameters and
  initial budgets across nine fixed synthetic stresses and 5,184 evaluation runs
- retained per-case losses, unknown periods, emergency duration and actual spending
- added new-only output publication, source/output hashes and six-file byte replay
- extended release verification and explicit tests; guarded Windows native-command failures
- documented that the current response proxy is not sustained affordability,
  physical controllability, a recovery probability or an empirical digital twin

### v0.4 sustained-plan extension

- added a public-only, receding-horizon screen over the complete v0.3 actuator ledger
- projected three constant-mode candidates through actual delays, slew, capacity,
  paid delivery and forced affordability curtailment for 24 steps
- separated strict model-boundary, six-step braking and terminal-budget tests,
  with explicit rejection counters and no physical-infeasibility claim
- evaluated reserve versus sustained-reserve on ten fixed scenarios and retained
  eleven post-hoc v0.3 losing cases as a separate regression cohort
- exposed chronic emergency duration, full-budget use, model-gain optimism and
  observation-envelope misses rather than interpreting fewer toy failures alone
- added deterministic new-only outputs, receipts, full replay and adversarial tests

### First empirical input — FY2024 fuel-carbon accounting — 2026-09-05

- extracted 21 non-overlapping fuel leaves from hash-pinned official workbooks
- reconciled 17 carbon-input rows, retained one diesel mismatch and three unknown mappings
- selected power-generation C fuel oil as the next stock-and-delivery contract;
  kept oil urgency separate from national annual emissions scale
- added a standard-library extractor, strict unit/year/fuel checks, new-only runs,
  deterministic offline replay, and separate raw-workbook verification
- kept net-MWh intensities, action effects, inventories and NDC sector allocation unknown
- preserved all synthetic fixtures and the F0 claim boundary

## v0.2.0 - 2026-08-07

### Added

- dependency-free Python F0 reference simulator
- four paired governance arms from the manuscript's research program
- normalized reference configuration and CLI overrides
- arm-level, episode-level, and step-level outputs
- resolved configuration and SHA-256 receipt
- deterministic unit tests and GitHub Actions verification
- `Makefile`, no-install launchers, and practical documentation
- complete `references.bib`
- manuscript v0.2 with feasibility ladder, paper-to-code map, runnable command, and implementation contract
- committed 64-episode reference artifact

### Preserved

- operator-attested v0.1 TeX source, with an available Git-history anchor
- operator-attested v0.1 PDF, without an independent earlier in-repository anchor
- the manuscript's explicit boundary between formal proposal and empirical validation

### Recovered

- replaced incomplete encoded bootstrap payloads with ordinary checked-in release files
- regenerated manuscript v0.2 from the operator-attested v0.1 source and executable contract, without claiming historical byte identity
- added a fail-closed release manifest and committed reference receipt
- removed the scheduled self-modifying workflow and archive restorer
- made CI fail when a required source, paper, PDF, reference artifact, or receipt is absent or modified

### Hardened after adversarial review

- expanded the manifest boundary to the complete executable closure, including launchers, entrypoints, verifiers, tests, Makefile, CI, and checkout policy
- rejected unmanifested Python and workflow files on executable surfaces and replaced automatic test discovery with explicit modules
- pinned tracked text to LF across platforms and rejected symlink traversal in release and replay verification
- separated disposable `make experiment` output from the explicit maintainer-only `make refresh-reference` operation
- replaced destructive output cleanup with verified staging and atomic directory exchange; existing-output replacement is refused where atomic exchange is unavailable
- separated requested, pending, and active control modes in the trace and renamed the request-rate metric accordingly
- added read-only Windows CI and exercised both no-install launchers
- SHA-pinned official GitHub Actions to revisions verified from their authoritative tag refs and added job timeouts
- clarified that a same-tree manifest proves internal consistency, while provenance remains operator-attested and externally anchored by a reviewed Git commit
