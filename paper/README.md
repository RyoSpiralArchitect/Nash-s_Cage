# Manuscript

This directory contains an operator-attested preserved v0.1 manuscript and an operator-attested regenerated v0.2 executability revision. The repository distinguishes those attestations from identities independently anchored in repository history.

## Files

- `nashs_cage_rvcim_v0_1.tex`: operator-attested exact preserved upload, dated 30 July 2026; its hash is also present in earlier repository payload history.
- `nashs_cage_rvcim_v0_1.pdf`: operator-attested exact preserved upload, dated 30 July 2026; no earlier in-repository historical anchor for this PDF is available.
- `nashs_cage_rvcim_v0_2.tex` and `.pdf`: operator-attested regenerated revision dated 7 August 2026.
- `references.bib`: complete bibliography required by both TeX sources.

Version 0.2 adds an executable-companion box, an F0 to F3 feasibility ladder, a paper-to-code map, the one-command reference experiment, and a reference implementation contract. The central conceptual claims and the non-validation boundary are preserved.

The operator attests that the v0.2 files were regenerated from the preserved v0.1 source and the checked-in executable contract after an earlier bootstrap representation proved incomplete. Historical v0.2 bytes are unavailable, and byte identity with any earlier v0.2 build is not claimed.

`../RELEASE_MANIFEST.json` records current file hashes, sizes, and the declared provenance boundary. Because the manifest and verifier are committed in the same tree, they establish internal consistency only: they do not independently prove upload identity, source-to-PDF derivation, historical lineage, or authenticity. A separately reviewed Git commit hash, signed tag, or release signature can serve as an external anchor when distributed through an independent channel. Until such an anchor or an independent build receipt is available, the unanchored provenance statements above remain operator attestations.

## Build

Requirements:

- a LaTeX distribution containing `newtx`, `biblatex`, `tikz`, `tcolorbox`, and the other packages declared in the source
- `latexmk`
- XeLaTeX
- BibTeX

From the repository root:

```bash
make paper
```

Or directly:

```bash
cd paper
mkdir -p ../.tmp/paper
latexmk -xelatex -interaction=nonstopmode -halt-on-error \
  -outdir=../.tmp/paper nashs_cage_rvcim_v0_2.tex
```

Clean intermediate files:

```bash
make paper-clean
```

The result is written under `.tmp/paper/`; the committed PDFs are not overwritten. The manifest hash identifies the current committed v0.2 rendering for same-tree consistency; it does not prove that the PDF was built from the checked-in TeX. A local rebuild checks buildability and may differ byte-for-byte because of TeX engine, package, font, or creation-metadata differences. The committed PDFs are provided so reading the manuscript does not require a TeX installation.
