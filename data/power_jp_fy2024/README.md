# Frozen factual extract: Japan FY2024 fuel-carbon balance

`observations.json` contains selected numerical facts and labels, not copies of
the source workbooks. It covers 21 nonzero, non-overlapping fuel leaves of the
six fossil-fuel families `$0100`–`$0600`, in row `#241000` (business generation,
excluding pumped storage). Family parent totals are retained only for coverage
checks, never summed again as fuel leaves. This is not all Japanese generation,
not all combustion fuels, and not a power-station or hourly dataset.

Sources, accessed 2026-09-05:

- METI / Agency for Natural Resources and Energy, General Energy Statistics,
  FY2024 final detailed energy balance, published 2026-04-14.
  [Official results](https://www.enecho.meti.go.jp/statistics/total_energy/results.html).
  e-Stat file ID `000040445052`, Excel version. SHA-256:
  `fa243caf7ecfccb0c091aaaa45415aee804553d28fbbb6f5cd53ec24403376b8`.
- NIES / Greenhouse Gas Inventory Office of Japan (GIO), Japan NID 2026,
  Chapter 3 time-series data, published 2026-05-29, `CEF` sheet, FY2024 column AR.
  [Official data landing page](https://www.nies.go.jp/gio/archive/nirdata/2026.html).
  SHA-256: `67db62abf7e09388705a1cf88565779daa0c4bbf2f037a421c06ebae0600f5c4`.
  Original data are supplied through the [GIO archive](https://www.nies.go.jp/gio/archive/index.html)
  and governed by [GIO's terms](https://www.nies.go.jp/gio/copyright/index.html).
  This is our processed factual extract, not a GIO-endorsed product. Source data
  can be revised; the frozen values are not a claim about the latest release.

Machine-readable download addresses, publishers, dates and hashes are inside
the extract. It preserves raw signed decimal cell values, sheet/cell locators,
original fuel codes, units and heat basis. The extraction code pins both source
hashes and checks their year, row, fuel codes and units. Labels exclude Excel's
phonetic guides. No formulas, macros or external links are executed.

To independently reproduce the extract, obtain the two workbooks from their
official sources and save them together under these exact local names:

```text
nash-energybalance-2024-detail.xlsx
nash-nid-ch3-2026.xlsx
```

Then, from the repository root:

```bash
python3 tools/run_power_accounting.py verify-sources --source-dir /absolute/path/to/raw-sources
```

This verifies raw bytes and reproduces the committed extract, without network
access. Any source revision fails closed; do not just replace the expected hash.
For a separate fresh extraction:

```bash
python3 tools/run_power_accounting.py extract --source-dir /absolute/path/to/raw-sources --out .tmp/power-extract
```

Ordinary `make verify-power` replays the committed extract and outputs offline.
It does **not** retrieve or independently authenticate the original workbooks.
The published source and reviewed Git commit remain the external evidence
anchors; self-consistent hashes alone cannot authenticate a modified dataset.

Reconstruction: negate only the declared transformation-input cells, convert
reported `10^3 tC` to `tC`, and compare against `TJ-HHV × tC/TJ-HHV`. The
tolerance is `max(0.001 tC, 1e-9 × reported tC)`, a numerical closure tolerance,
not an uncertainty interval. Decimal arithmetic is used, with final display
rounded to nine fractional digits. Multiplication by `44/12` gives full-carbon
CO2 equivalents, not measured stack emissions or avoided emissions.

No coefficient is inherited from a parent fuel code. `$0224`, `$0453`, `$0454`
therefore remain unresolved. `$0434` fails using the code-matched fossil diesel
coefficient. The separate unnumbered biomass-considered diesel row explains the
arithmetic residual, but is a diagnostic, not an admitted fuel-composition map.
