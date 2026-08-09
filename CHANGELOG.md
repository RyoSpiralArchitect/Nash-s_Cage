# Changelog

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
