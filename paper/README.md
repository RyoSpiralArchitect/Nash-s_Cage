# Manuscript

This directory preserves the exact uploaded v0.1 manuscript and a provenance-marked regenerated v0.2 executability revision.

## Files

- `nashs_cage_rvcim_v0_1.tex` and `.pdf`: exact preserved uploaded files, dated 30 July 2026.
- `nashs_cage_rvcim_v0_2.tex` and `.pdf`: regenerated revision dated 7 August 2026.
- `references.bib`: complete bibliography required by both TeX sources.

Version 0.2 adds an executable-companion box, an F0 to F3 feasibility ladder, a paper-to-code map, the one-command reference experiment, and a reference implementation contract. The central conceptual claims and the non-validation boundary are preserved.

The v0.2 files were regenerated from the preserved v0.1 manuscript and the checked-in executable contract after an earlier bootstrap representation proved incomplete. They are not claimed to be byte-identical to an unavailable historical v0.2 build. `../RELEASE_MANIFEST.json` records file hashes, sizes, and this provenance boundary.

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

The result is written under `.tmp/paper/`; the committed PDFs are not overwritten. The committed v0.2 hash identifies the qualified rendering, while a local rebuild checks buildability and may differ byte-for-byte because of TeX engine, package, font, or creation-metadata differences. The committed PDFs are provided so reading the manuscript does not require a TeX installation.
