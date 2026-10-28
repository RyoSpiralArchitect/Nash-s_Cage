# Frozen cross-domain descriptive audit

The snapshot was acquired on 2026-10-24 at 21:55 UTC (2026-10-25 JST).
It contains public administrative declaration records and national annual debt
indicators, not personal records, private conversations, or authentication data.
The [input contract](../../experiments/cross_domain_audit_v01/CONTRACT.ja.md),
[analysis and limitations](../../docs/research/2026-10-25-cross-domain-executability/ANALYSIS.ja.md),
and [reproduction instructions](../../docs/research/2026-10-25-cross-domain-executability/REPRODUCIBILITY.ja.md)
define the selected populations, units, missingness rules, and claim ceiling.

## Sources, attribution, and reuse

### FEMA

Source: Federal Emergency Management Agency, OpenFEMA Disaster Declarations
Summaries v2, including its dataset and field metadata. The complete query URLs,
UTC access times, and original response hashes are in
[`snapshot_20261025/manifest.json`](snapshot_20261025/manifest.json).

- [Official dataset description](https://www.fema.gov/openfema-data-page/disaster-declarations-summaries-v2)
- [Official API](https://www.fema.gov/api/open/v2/DisasterDeclarationsSummaries)
- [Federal data catalog entry](https://catalog.data.gov/dataset/disaster-declarations-summaries)
- [OpenFEMA terms and citation requirements](https://www.fema.gov/about/openfema/terms-conditions)

The federal catalog identifies this dataset as public, links its v2 API, and
provides a U.S. government-works reuse reference. This is source-specific
attribution, not a claim that all material on federal websites is unrestricted
worldwide. The terms page returned HTTP 403 during the 2026-10-28 verification;
the catalog and the citation reference in the frozen dataset metadata were
available. No agency logo or seal is redistributed here.

This product uses the Federal Emergency Management Agency's OpenFEMA API, but
is not endorsed by FEMA. The Federal Government or FEMA cannot vouch for the
data or analyses derived from these data after the data have been retrieved
from the Agency's website(s).

### World Bank

Source: World Bank, World Development Indicators / International Debt Statistics:

- [`DT.TDS.DECT.EX.ZS`: total external debt service / exports](https://data.worldbank.org/indicator/DT.TDS.DECT.EX.ZS)
- [`DT.TDS.DPPG.XP.ZS`: public and publicly guaranteed debt service / exports](https://data.worldbank.org/indicator/DT.TDS.DPPG.XP.ZS)

Both indicator pages explicitly identify the license as
[Creative Commons Attribution 4.0 International](https://creativecommons.org/licenses/by/4.0/).
See also the World Bank's [summary terms of use](https://data.worldbank.org/summary-terms-of-use),
including its additional terms. Attribution and those underlying terms continue
to apply to the World Bank data; no endorsement by the World Bank is implied.
The API responses report a last-update date of 2026-10-08, distinct from our
acquisition date. The selection is Bangladesh and Kenya, 2000--2024, two
indicators (100 country-year-indicator cells).

### Transformations and project license boundary

Original API response bytes are stored losslessly with gzip compression.
The two frozen analysis CSVs retain their original CRLF bytes through narrowly
scoped `-text` attributes; Git must not normalize them and invalidate the receipt.
Derived CSV/JSON files deduplicate FEMA's designated-area rows to declaration
records, compute UTC calendar-date differences and descriptive distributions,
and report World Bank values and specified five-year mean ratios. Missing and
negative date differences are retained. Display payloads contain a labeled
subset of those descriptive results. The analysis does not correct source
records, join the two populations, impute missing values, or estimate causal
effects. These are project transformations, not agency-published conclusions.

The repository has not selected a general software or manuscript license.
These source-specific notices do not relicense the repository, extend data
licenses to project code, or grant rights over separately linked publications.

## Verification boundary

`RELEASE_MANIFEST.json` covers the separately declared executable release and
versioned manuscripts. This research snapshot is **not** part of that manifest;
its input and output identities are recorded in the snapshot manifest and
[`analysis_20261025/receipt.json`](analysis_20261025/receipt.json).
The independent `cross-domain` CI job runs the bounded Python tests, recomputes
from these frozen responses without fetching data, and byte-compares the three
descriptive outputs. A green release check alone does not verify this snapshot.

The Ruby check is an additional independent arithmetic implementation, not a
replacement for Python's input-integrity, cohort, duplicate, and within-declaration
consistency checks. Its date arithmetic is applicable to the UTC `Z` timestamps
in this frozen snapshot. The recorded 1,578 matching values do not independently
validate the source dates, causal mechanisms, recipient payments, protection
outcomes, or government daily liquidity. Same-tree hashes establish consistency;
the reviewed Git commit supplies the external version anchor.

Replaying an existing snapshot is a reproducibility check, not a new experiment.
Do not refresh the snapshot or overwrite its receipts as part of manuscript or
CI maintenance. A later acquisition must use a new output directory and retain
its own acquisition date and provenance.
