#!/usr/bin/env python3
"""Frozen FY2024 fuel-carbon accounting, not dispatch or a calibrated RVCIM model.

Standard library only. Excel formula caches are read, never executed. Normal runs
use a small factual extract; verify-sources independently reproduces that extract
from the two hash-pinned, locally supplied public workbooks.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import posixpath
import sys
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter
from decimal import Decimal, InvalidOperation, localcontext
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOADED_CODE_SHA256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
DATA = "data/power_jp_fy2024/observations.json"
FORMAT = "nashs-cage-power-carbon-extract/v1"
SCOPE = "JP/FY2024/#241000/business-generation-excluding-pumped-storage"
ENERGY_SHEET = "（詳細表）ｴﾈﾙｷﾞｰ単位表（本表）"
CARBON_SHEET = "（詳細表）炭素単位表"
SOURCES = {
    "energy_balance": {
        "filename": "nash-energybalance-2024-detail.xlsx",
        "sha256": "fa243caf7ecfccb0c091aaaa45415aee804553d28fbbb6f5cd53ec24403376b8",
        "publisher": "METI / Agency for Natural Resources and Energy / e-Stat",
        "release_date": "2026-04-14",
        "landing_url": "https://www.enecho.meti.go.jp/statistics/total_energy/results.html",
        "download_url": "https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040445052&fileKind=0",
    },
    "nid_coefficients": {
        "filename": "nash-nid-ch3-2026.xlsx",
        "sha256": "67db62abf7e09388705a1cf88565779daa0c4bbf2f037a421c06ebae0600f5c4",
        "publisher": "NIES / Greenhouse Gas Inventory Office of Japan (GIO)",
        "release_date": "2026-05-29",
        "landing_url": "https://www.nies.go.jp/gio/archive/nirdata/2026.html",
        "download_url": "https://www.nies.go.jp/gio/archive/nirdata/qu9bd600001b3pi9-att/L5-NID-Ch3-Energy-2026_web.xlsx",
    },
}
# Non-overlapping nonzero leaves in the fossil fuel families $0100 through $0600.
# No implicit parent-to-child coefficient inheritance. Missing mappings stay open.
# (fuel code, detailed-table column, CEF row or None, descriptive family)
CELLS = (
    ("$0123", "N", 12, "coal"),
    ("$0211", "T", 16, "coal_product"),
    ("$0221", "X", 19, "coal_product"),
    ("$0224", "AA", None, "coal_product"),
    ("$0225", "AB", 21, "coal_product"),
    ("$0320", "AH", 27, "oil"),
    ("$0321", "AI", 28, "oil"),
    ("$0332", "AL", 31, "oil"),
    ("$0421", "BA", 36, "oil_product"),
    ("$0433", "BE", 41, "oil_product"),
    ("$0434", "BF", 42, "oil_product"),
    ("$0436", "BH", 44, "oil_product"),
    ("$0440", "BL", 47, "oil_product"),
    ("$0453", "BP", None, "oil_product"),
    ("$0454", "BQ", None, "oil_product"),
    ("$0455", "BR", 51, "oil_product"),
    ("$0457", "BT", 53, "oil_product"),
    ("$0458", "BU", 54, "oil_product"),
    ("$0510", "BY", 57, "natural_gas"),
    ("$0521", "CA", 59, "natural_gas"),
    ("$0610", "CE", 63, "city_gas"),
)
PARENTS = (("$0100", "G"), ("$0200", "R"), ("$0300", "AD"),
           ("$0400", "AO"), ("$0500", "BX"), ("$0600", "CD"))
UNITS = {"input": "TJ-HHV", "carbon": "10^3 tC", "coefficient": "tC/TJ-HHV"}
GATES = {
    "fuel_specific_net_generation_mwh": None,
    "tco2_per_net_mwh": None,
    "same_service_avoided_tco2": None,
    "deliverable_oil_stock_tj": None,
    "oil_stockout_date": None,
    "power_sector_carbon_budget_tco2": None,
    "action_status": "ACTION_EFFECT_UNIDENTIFIED",
    "resource_status": "RESOURCE_AVAILABILITY_UNKNOWN",
    "service_status": "TIME_RESOLVED_SERVICE_UNVERIFIED",
    "ndc_allocation_status": "SECTOR_BUDGET_UNSPECIFIED",
    "dispatch_authority": "NOT_AUTHORIZED",
}
BOUNDARY = (
    "Fuel-carbon accounting consistency only. Reported carbon is not independent "
    "stack measurement. Full-carbon CO2 equivalents are not avoided emissions, "
    "electricity-service-preserving effects, or evidence of present fuel scarcity. "
    "RVCIM remains an uncalibrated F0 structural toy."
)
NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


def digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def json_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True,
                       allow_nan=False) + "\n").encode("utf-8")


def require(ok: bool, message: str) -> None:
    if not ok:
        raise ValueError(message)


def regular_bytes(path: Path) -> bytes:
    require(not any(p.is_symlink() for p in (path, *path.parents)),
            f"symlink input/output rejected: {path}")
    require(path.is_file(), f"missing regular file: {path}")
    return path.read_bytes()


def number(value: object) -> Decimal:
    require(isinstance(value, str), "numeric values must be explicit decimal strings")
    try:
        result = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError("invalid decimal value") from exc
    require(result.is_finite(), "nonfinite value rejected")
    require(abs(result) < Decimal("1e15"), "value outside bounded accounting range")
    return result


def decimal_text(value: Decimal) -> str:
    rounded = value.quantize(Decimal("0.000000001"))
    return format(abs(rounded) if not rounded else rounded, "f")


def excel_text(element: ET.Element) -> str:
    """Visible rich text only: OOXML rPh phonetic guides are not cell text."""
    return "".join((child.text or "") if child.tag == NS + "t" else
                   "".join(t.text or "" for t in child.findall(NS + "t"))
                   if child.tag == NS + "r" else "" for child in element)


def xlsx_cells(payload: bytes, sheet: str, addresses: set[str]) -> dict[str, str | None]:
    """Read only requested cached cells of a hash-pinned OOXML workbook."""
    with zipfile.ZipFile(io.BytesIO(payload)) as book:
        require(sum(z.file_size for z in book.infolist()) < 256 * 1024**2,
                "workbook expands beyond limit")
        strings = []
        if "xl/sharedStrings.xml" in book.namelist():
            tree = ET.fromstring(book.read("xl/sharedStrings.xml"))
            strings = [excel_text(si) for si in tree]
        links = {r.attrib["Id"]: r.attrib["Target"] for r in
                 ET.fromstring(book.read("xl/_rels/workbook.xml.rels"))}
        workbook = ET.fromstring(book.read("xl/workbook.xml"))
        entries = [s for s in workbook.find(NS + "sheets") if s.attrib["name"] == sheet]
        require(len(entries) == 1, f"missing/duplicate sheet: {sheet}")
        rel = entries[0].attrib[
            "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"]
        target = links[rel]
        target = target.lstrip("/") if target.startswith("/") else posixpath.normpath("xl/" + target)
        require(target.startswith("xl/"), "invalid sheet relationship")
        result: dict[str, str | None] = {}
        with book.open(target) as handle:
            for _, element in ET.iterparse(handle, events=("end",)):
                if element.tag == NS + "c":
                    addr = element.attrib["r"]
                    if addr in addresses:
                        require(addr not in result, "duplicate cell")
                        value = element.find(NS + "v")
                        raw = value.text if value is not None else None
                        kind = element.attrib.get("t")
                        if kind == "s" and raw is not None:
                            raw = strings[int(raw)]
                        elif kind == "inlineStr":
                            raw = excel_text(element.find(NS + "is"))
                        elif kind in ("e", "b"):
                            raise ValueError(f"unsupported selected cell type: {addr}")
                        result[addr] = raw
                    element.clear()
                elif element.tag == NS + "row":
                    element.clear()
        return {addr: result.get(addr) for addr in sorted(addresses)}


def extract(source_dir: Path) -> dict:
    sources = {key: regular_bytes(source_dir / spec["filename"])
               for key, spec in SOURCES.items()}
    for key, payload in sources.items():
        require(digest(payload) == SOURCES[key]["sha256"], f"raw source hash mismatch: {key}")
    columns = [v[1] for v in CELLS] + [v[1] for v in PARENTS]
    addresses = {f"{col}{row}" for col in columns for row in (1, 13, 14, 58)}
    addresses.update({"A1", "B11", "A58", "D58"})
    energy = xlsx_cells(sources["energy_balance"], ENERGY_SHEET, addresses)
    carbon = xlsx_cells(sources["energy_balance"], CARBON_SHEET, addresses)
    cef_rows = [v[2] for v in CELLS if v[2] is not None]
    cef_addresses = {f"{col}{row}" for col in ("I", "AR") for row in cef_rows}
    cef_addresses.update({"AR4", "D3", "AR43", "G43"})
    cef = xlsx_cells(sources["nid_coefficients"], "CEF", cef_addresses)
    require(cef["AR4"] == "2024", "CEF fiscal year mismatch")
    require("t-C/TJ" in (cef["D3"] or "") and "高位" in cef["D3"], "CEF unit/basis mismatch")
    for sheet in (energy, carbon):
        require((sheet["A1"] or "").strip() == "2024FY", "balance fiscal year mismatch")
        require(sheet["A58"] == "#241000", "balance population mismatch")
    require("High Calorific" in (energy["B11"] or ""), "balance heat basis mismatch")
    rows = []
    for code, col, cef_row, family in CELLS:
        for sheet, unit in ((energy, "TJ"), (carbon, "10^3 tC")):
            require(sheet[col + "1"] == code, f"balance fuel code mismatch: {code}")
            require(sheet[col + "14"] == unit, f"balance unit mismatch: {code}")
        if cef_row is not None:
            require(cef[f"I{cef_row}"] == code, f"CEF fuel code mismatch: {code}")
        rows.append({
            "fuel_code": code, "name_ja": energy[col + "13"], "family": family,
            "balance_cell": col + "58", "cef_cell": f"AR{cef_row}" if cef_row else None,
            "input_tj_signed": energy[col + "58"],
            "carbon_ktc_signed": carbon[col + "58"],
            "coefficient_tc_per_tj_hhv": cef[f"AR{cef_row}"] if cef_row else None,
        })
    parents = []
    for code, col in PARENTS:
        for sheet, unit in ((energy, "TJ"), (carbon, "10^3 tC")):
            require(sheet[col + "1"] == code and sheet[col + "14"] == unit,
                    "parent code/unit mismatch")
        parents.append({"fuel_code": code, "balance_cell": col + "58",
                        "input_tj_signed": energy[col + "58"],
                        "carbon_ktc_signed": carbon[col + "58"]})
    return {"format": FORMAT, "scope": SCOPE, "units": UNITS, "sources": SOURCES,
            "sheets": {"energy": ENERGY_SHEET, "carbon": CARBON_SHEET, "coefficient": "CEF"},
            "rows": rows, "parent_totals": parents,
            "diesel_biomass_diagnostic": {"cell": "CEF!AR43", "code": None,
                                          "coefficient_tc_per_tj_hhv": cef["AR43"]}}


def evaluate(data: dict) -> tuple[list[dict], dict]:
    for key, expected in (("format", FORMAT), ("scope", SCOPE), ("units", UNITS),
                          ("sources", SOURCES),
                          ("sheets", {"energy": ENERGY_SHEET, "carbon": CARBON_SHEET, "coefficient": "CEF"})):
        require(data.get(key) == expected, f"extract contract mismatch: {key}")
    require(isinstance(data.get("rows"), list) and len(data["rows"]) == len(CELLS),
            "wrong fuel row denominator")
    result = []
    with localcontext() as ctx:
        ctx.prec = 40
        for raw, (code, col, cef_row, family) in zip(data["rows"], CELLS):
            require(raw.get("fuel_code") == code and raw.get("balance_cell") == col + "58"
                    and raw.get("family") == family, "fuel code/order/locator mismatch")
            require(raw.get("cef_cell") == (f"AR{cef_row}" if cef_row else None), "coefficient locator mismatch")
            h_signed = number(raw["input_tj_signed"])
            c_signed = number(raw["carbon_ktc_signed"])
            require(h_signed < 0 and c_signed < 0, "selected fuel must have negative transformation input")
            h, carbon = -h_signed, -c_signed * 1000
            factor_raw = raw["coefficient_tc_per_tj_hhv"]
            reconstructed = residual = per_tj = None
            if cef_row is None:
                require(factor_raw is None, "unapproved aggregate-to-leaf coefficient mapping")
                status = "COEFFICIENT_MAPPING_UNKNOWN"
            else:
                factor = number(factor_raw)
                require(0 < factor < 100, "coefficient outside carbon-accounting range")
                reconstructed = h * factor
                residual = reconstructed - carbon
                # Numerical closure tolerance, not measurement/model uncertainty.
                tolerance = max(Decimal("0.001"), carbon * Decimal("1e-9"))
                status = "RECONCILED" if abs(residual) <= tolerance else "REJECT_COEFFICIENT_MISMATCH"
                if status == "RECONCILED":
                    per_tj = factor * Decimal(44) / 12
            result.append({
                "fuel_code": code, "name_ja": raw["name_ja"], "family": family,
                "input_tj_hhv": decimal_text(h),
                "reported_carbon_tc": decimal_text(carbon),
                "reconstructed_carbon_tc": decimal_text(reconstructed) if reconstructed is not None else None,
                "residual_tc": decimal_text(residual) if residual is not None else None,
                "reported_carbon_full_co2_equivalent_tco2": decimal_text(carbon * 44 / 12),
                "one_tj_full_carbon_co2_equivalent_tco2": decimal_text(per_tj) if per_tj is not None else None,
                "status": status, "balance_cell": raw["balance_cell"], "cef_cell": raw["cef_cell"],
            })
        parents = data.get("parent_totals")
        require(isinstance(parents, list) and len(parents) == len(PARENTS), "missing parent totals")
        for raw, (code, col) in zip(parents, PARENTS):
            require(raw["fuel_code"] == code and raw["balance_cell"] == col + "58", "parent locator mismatch")
        for key in ("input_tj_signed", "carbon_ktc_signed"):
            # Aggregate parents are a coverage check only; never included twice.
            leaves = sum(number(r[key]) for r in data["rows"])
            total = sum(number(r[key]) for r in parents)
            require(abs(leaves - total) <= max(Decimal("1e-6"), abs(total) * Decimal("1e-10")),
                    f"leaf/parent coverage mismatch: {key}")
        diagnostic = data["diesel_biomass_diagnostic"]
        require(diagnostic.get("cell") == "CEF!AR43" and diagnostic.get("code") is None,
                "unapproved diesel diagnostic mapping")
        diesel = next(r for r in data["rows"] if r["fuel_code"] == "$0434")
        diagnostic_residual = (-number(diesel["input_tj_signed"]) *
                               number(diagnostic["coefficient_tc_per_tj_hhv"]) +
                               number(diesel["carbon_ktc_signed"]) * 1000)
        summary = {
            "format": "nashs-cage-power-carbon-result/v1", "scope": SCOPE,
            "claim_boundary": BOUNDARY, "row_count": len(result),
            "status_counts": dict(sorted(Counter(r["status"] for r in result).items())),
            "accounting_status": "PARTIAL_RECONCILIATION_WITH_REJECTIONS",
            "coverage": "21 nonzero leaves close six fossil-family parents; not all generation fuels",
            "priority_fuel": "$0440", "priority_reason": "operator-selected oil accounting entry, not an inferred scarcity ranking",
            "diesel_biomass_diagnostic_residual_tc": decimal_text(diagnostic_residual),
            "diesel_diagnostic_status": "DIAGNOSTIC_ONLY_NOT_AN_ACCEPTED_MAPPING",
            "forbidden_join": "REJECT_SCOPE_MISMATCH: NID 1.A.1.a CO2 / national 9911 hundred-million kWh",
            "unknowns_and_gates": GATES,
        }
    return result, summary


def output_payloads(data: dict) -> dict[str, bytes]:
    rows, summary = evaluate(data)
    csv_out = io.StringIO(newline="")
    writer = csv.DictWriter(csv_out, fieldnames=list(rows[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    lines = ["# JP FY2024 fuel-carbon accounting", "", BOUNDARY, "",
             f"Scope: `{SCOPE}`. Full denominator: {len(rows)} nonzero fossil-family leaves.", "",
             "| Fuel | Input TJ-HHV | Reported carbon CO2-equivalent t | Status |",
             "|---|---:|---:|---|"]
    for r in rows:
        lines.append(f"| {r['fuel_code']} {r['name_ja']} | {r['input_tj_hhv']} | "
                     f"{r['reported_carbon_full_co2_equivalent_tco2']} | {r['status']} |")
    lines += ["", "Reconciliation is not independent empirical validation. Unknown/rejected rows remain in the denominator.",
              "No net-MWh intensity, avoided-emissions estimate, stockout forecast, NDC allocation or dispatch authorization is produced.", ""]
    return {"rows.csv": csv_out.getvalue().encode("utf-8"),
            "summary.json": json_bytes(summary), "comparison.md": "\n".join(lines).encode("utf-8")}


def bundle(root: Path = ROOT) -> dict[str, bytes]:
    raw = regular_bytes(root / DATA)
    code = regular_bytes(root / "tools/run_power_accounting.py")
    require(digest(code) == LOADED_CODE_SHA256, "loaded Python source changed; start a fresh process")
    outputs = output_payloads(json.loads(raw))
    require(raw == regular_bytes(root / DATA) and code == regular_bytes(root / "tools/run_power_accounting.py"),
            "inputs changed during computation")
    receipt = {
        "format": "nashs-cage-power-carbon-receipt/v1", "claim_boundary": BOUNDARY,
        "input": {"path": DATA, "sha256": digest(raw)},
        "code": {"path": "tools/run_power_accounting.py", "sha256": digest(code)},
        "source_workbook_sha256": {k: v["sha256"] for k, v in SOURCES.items()},
        "raw_source_verification": "separate verify-sources command; offline replay alone does not re-open workbooks",
        "numeric_encoding": "decimal arithmetic; outputs rounded to 9 fractional digits; null is unknown",
        "outputs": {name: {"sha256": digest(value), "bytes": len(value)} for name, value in outputs.items()},
    }
    return {**outputs, "receipt.json": json_bytes(receipt)}


def write_new(out: Path, payloads: dict[str, bytes]) -> None:
    require(not any(p.is_symlink() for p in (out, *out.parents)), "symlink output rejected")
    # Deliberately no overwrite mode. A partial failed creation cannot verify.
    out.mkdir(parents=True, exist_ok=False)
    for name, value in payloads.items():
        with (out / name).open("xb") as handle:
            handle.write(value)


def verify(out: Path, root: Path = ROOT) -> None:
    expected = bundle(root)
    require(out.is_dir() and not out.is_symlink(), "invalid output directory")
    require({p.name for p in out.iterdir()} == set(expected), "output set mismatch")
    for name, value in expected.items():
        require(regular_bytes(out / name) == value, f"replay mismatch: {name}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("run", "verify"):
        command = commands.add_parser(name)
        command.add_argument("--out", type=Path, required=True)
        if name == "verify":
            command.add_argument("--replay", action="store_true", help="always performed, retained for explicit intent")
    for name in ("extract", "verify-sources"):
        command = commands.add_parser(name)
        command.add_argument("--source-dir", type=Path, required=True)
        if name == "extract":
            command.add_argument("--out", type=Path, required=True, help="new directory receiving observations.json")
    args = parser.parse_args()
    try:
        if args.command in ("extract", "verify-sources"):
            data = extract(args.source_dir)
            evaluate(data)
            payload = json_bytes(data)
            if args.command == "extract":
                write_new(args.out, {"observations.json": payload})
            else:
                require(payload == regular_bytes(ROOT / DATA), "raw source / frozen extract mismatch")
        elif args.command == "run":
            write_new(args.out, bundle())
            verify(args.out)
        else:
            verify(args.out)
    except (OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile, ET.ParseError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print(f"PASS: {args.command}; accounting only; action/resource/service remain unverified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
