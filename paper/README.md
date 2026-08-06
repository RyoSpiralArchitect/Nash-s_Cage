# Manuscript

This directory preserves the uploaded v0.1 manuscript and the v0.2 executability revision.

## Files

- `nashs_cage_rvcim_v0_1.tex` and `.pdf`: original uploaded source and reproducible rendering, dated 30 July 2026.
- `nashs_cage_rvcim_v0_2.tex` and `.pdf`: revision dated 7 August 2026.
- `references.bib`: complete bibliography required by both TeX sources.

Version 0.2 adds an executable-companion box, an F0 to F3 feasibility ladder, a paper-to-code map, the one-command reference experiment, and a reference implementation contract. The central conceptual claims and the non-validation boundary are preserved.

## Build

Requirements:

- a LaTeX distribution containing `newtx`, `biblatex`, `biber`, `tikz`, `tcolorbox`, and the other packages declared in the source
- `latexmk`
- `biber`

From the repository root:

```bash
make paper
```

Or directly:

```bash
cd paper
latexmk -pdf -interaction=nonstopmode -halt-on-error nashs_cage_rvcim_v0_2.tex
```

Clean intermediate files:

```bash
make paper-clean
```

The committed PDFs are provided so reading the manuscript does not require a TeX installation.
