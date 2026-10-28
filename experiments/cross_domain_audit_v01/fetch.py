"""Fetch bounded public snapshots; refuse to overwrite an existing snapshot."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode

HERE = Path(__file__).resolve().parent
FEMA_FILTER = ("declarationType eq 'DR' and declarationDate ge '2000-01-01T00:00:00.000Z' "
               "and declarationDate lt '2025-01-01T00:00:00.000Z'")
FEMA_FIELDS = [
    "id", "femaDeclarationString", "disasterNumber", "state", "declarationType",
    "declarationDate", "declarationRequestDate", "incidentBeginDate", "incidentEndDate",
    "incidentType", "declarationTitle", "tribalRequest", "placeCode", "incidentId", "lastRefresh",
]
INDICATORS = ["DT.TDS.DECT.EX.ZS", "DT.TDS.DPPG.XP.ZS"]


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    entries = []

    def get(name: str, base: str, params: dict) -> object:
        url = base + "?" + urlencode(params)
        began = datetime.now(timezone.utc).isoformat()
        raw = subprocess.run(
            ["curl", "--fail", "--silent", "--show-error", "--max-time", "45", url],
            capture_output=True, check=True, timeout=55,
        ).stdout
        data = json.loads(raw)
        compressed = gzip.compress(raw, mtime=0)
        with (args.out / (name + ".json.gz")).open("xb") as fh:
            fh.write(compressed)
        entry = {"file": name + ".json.gz", "url": url, "started_at": began,
                 "completed_at": datetime.now(timezone.utc).isoformat(),
                 "raw_bytes": len(raw), "raw_sha256": digest(raw),
                 "gzip_bytes": len(compressed), "gzip_sha256": digest(compressed)}
        entries.append(entry)
        print(json.dumps({"fetched": name, "raw_bytes": len(raw)}), flush=True)
        return data

    get("fema_fields", "https://www.fema.gov/api/open/v1/OpenFemaDataSetFields",
        {"$filter": "openFemaDataSet eq 'DisasterDeclarationsSummaries'", "$top": 1000})
    get("fema_dataset", "https://www.fema.gov/api/open/v1/OpenFemaDataSets",
        {"$filter": "name eq 'DisasterDeclarationsSummaries'", "$top": 100})
    expected = None
    ids = set()
    for page in range(30):  # bound accidental queries to 300,000 rows
        data = get(f"fema_page_{page:03d}", "https://www.fema.gov/api/open/v2/DisasterDeclarationsSummaries",
                   {"$filter": FEMA_FILTER, "$select": ",".join(FEMA_FIELDS),
                    "$orderby": "id", "$top": 10000, "$skip": page * 10000, "$count": "true"})
        count = data["metadata"]["count"]
        if expected is None:
            expected = count
        if count != expected:
            raise ValueError("FEMA count changed during pagination; no completed manifest")
        rows = data["DisasterDeclarationsSummaries"]
        wanted = min(10000, expected - page * 10000)
        if len(rows) != wanted:
            raise ValueError("Incomplete FEMA page")
        for row in rows:
            if row["id"] in ids:
                raise ValueError("Duplicate FEMA id across pages")
            ids.add(row["id"])
        if len(ids) == expected:
            break
    else:
        raise ValueError("FEMA pagination limit reached")
    for indicator in INDICATORS:
        get("wb_meta_" + indicator, "https://api.worldbank.org/v2/indicator/" + indicator,
            {"format": "json"})
        data = get("wb_data_" + indicator,
                   "https://api.worldbank.org/v2/country/BGD;KEN/indicator/" + indicator,
                   {"format": "json", "date": "2000:2024", "per_page": 1000, "source": 2})
        if data[0]["pages"] != 1 or data[0]["total"] != len(data[1]) or len(data[1]) != 50:
            raise ValueError("Incomplete World Bank country-year grid")
    manifest = {"schema_version": 1, "fema_expected_rows": expected, "sources": entries,
                "contract_sha256": digest((HERE / "CONTRACT.ja.md").read_bytes()),
                "fetch_sha256": digest(Path(__file__).read_bytes()),
                "note": "Read-only public API capture, not an atomic cross-page snapshot."}
    with (args.out / "manifest.json").open("x") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    print(json.dumps({"complete": True, "fema_rows": expected, "files": len(entries)}))


if __name__ == "__main__":
    main()
