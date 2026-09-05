from __future__ import annotations

import copy
import json
import tempfile
import unittest
import xml.etree.ElementTree as ET
from decimal import Decimal
from pathlib import Path
from unittest import mock

from tools import run_power_accounting as power


class PowerAccountingTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((power.ROOT / power.DATA).read_text(encoding="utf-8"))

    def test_full_denominator_and_failures_are_retained(self):
        rows, summary = power.evaluate(self.data)
        self.assertEqual(21, len(rows))
        self.assertEqual({"RECONCILED": 17, "COEFFICIENT_MAPPING_UNKNOWN": 3,
                          "REJECT_COEFFICIENT_MISMATCH": 1}, summary["status_counts"])
        self.assertEqual("PARTIAL_RECONCILIATION_WITH_REJECTIONS", summary["accounting_status"])

    def test_oil_coal_lng_one_tj_is_carbon_not_electricity(self):
        rows, summary = power.evaluate(self.data)
        expected = {"$0440": "72.896383438", "$0123": "90.783680883", "$0510": "50.746998913"}
        for row in rows:
            if row["fuel_code"] in expected:
                self.assertEqual(expected[row["fuel_code"]], row["one_tj_full_carbon_co2_equivalent_tco2"])
        self.assertEqual(power.GATES, summary["unknowns_and_gates"])
        for field in ("same_service_avoided_tco2", "tco2_per_net_mwh", "deliverable_oil_stock_tj"):
            self.assertIsNone(summary["unknowns_and_gates"][field])

    def test_diesel_residual_is_not_silently_repaired(self):
        rows, summary = power.evaluate(self.data)
        diesel = next(r for r in rows if r["fuel_code"] == "$0434")
        self.assertEqual("18.816513328", diesel["residual_tc"])
        self.assertIsNone(diesel["one_tj_full_carbon_co2_equivalent_tco2"])
        self.assertEqual("0.000000000", summary["diesel_biomass_diagnostic_residual_tc"])
        self.assertEqual("DIAGNOSTIC_ONLY_NOT_AN_ACCEPTED_MAPPING", summary["diesel_diagnostic_status"])

    def test_all_unknown_coefficients_remain_unknown(self):
        rows, _ = power.evaluate(self.data)
        for row in rows:
            if row["fuel_code"] in ("$0224", "$0453", "$0454"):
                self.assertIsNone(row["reconstructed_carbon_tc"])
                self.assertIsNone(row["one_tj_full_carbon_co2_equivalent_tco2"])

    def test_wrong_scope_units_basis_or_source_rejected(self):
        for field, value in (("scope", "NID/1.A.1.a"), ("units", {**power.UNITS, "input": "TJ-LHV"}),
                             ("sources", {}), ("format", "future/v9")):
            with self.subTest(field=field):
                changed = copy.deepcopy(self.data)
                changed[field] = value
                with self.assertRaises(ValueError):
                    power.evaluate(changed)

    def test_missing_duplicate_and_reordered_fuel_rows_rejected(self):
        for rows in (self.data["rows"][:-1], self.data["rows"] + [self.data["rows"][0]],
                     list(reversed(self.data["rows"]))):
            with self.subTest(rows=len(rows)):
                with self.assertRaises(ValueError):
                    power.evaluate({**self.data, "rows": rows})

    def test_invalid_numeric_inputs_and_wrong_sign_rejected(self):
        for field in ("input_tj_signed", "carbon_ktc_signed", "coefficient_tc_per_tj_hhv"):
            for value in (None, True, 2, "NaN", "Infinity", "n/a", "1e99", "0"):
                with self.subTest(field=field, value=value):
                    changed = copy.deepcopy(self.data)
                    changed["rows"][0][field] = value
                    with self.assertRaises(ValueError):
                        power.evaluate(changed)
        changed = copy.deepcopy(self.data)
        changed["rows"][0]["input_tj_signed"] = "2494789.89582"
        with self.assertRaises(ValueError):
            power.evaluate(changed)

    def test_no_aggregate_coefficient_inheritance(self):
        changed = copy.deepcopy(self.data)
        changed["rows"][3]["coefficient_tc_per_tj_hhv"] = "26.064172490174048"
        with self.assertRaisesRegex(ValueError, "aggregate-to-leaf"):
            power.evaluate(changed)

    def test_wrong_fuel_or_locator_rejected(self):
        for field, value in (("fuel_code", "$0122"), ("cef_cell", "AR11"),
                             ("balance_cell", "N57"), ("family", "oil")):
            changed = copy.deepcopy(self.data)
            changed["rows"][0][field] = value
            with self.assertRaises(ValueError):
                power.evaluate(changed)

    def test_parent_totals_are_coverage_not_double_counted(self):
        changed = copy.deepcopy(self.data)
        changed["parent_totals"][0]["input_tj_signed"] = "-2494780"
        with self.assertRaisesRegex(ValueError, "coverage mismatch"):
            power.evaluate(changed)

    def test_wrong_diesel_diagnostic_locator_rejected(self):
        changed = copy.deepcopy(self.data)
        changed["diesel_biomass_diagnostic"]["code"] = "$0434"
        with self.assertRaises(ValueError):
            power.evaluate(changed)

    def test_rounding_is_explicit_and_normalizes_negative_zero(self):
        self.assertEqual("0.000000000", power.decimal_text(Decimal("-0.00000000001")))
        self.assertEqual("0.076200000", power.decimal_text(Decimal("0.07619999999999999")))

    def test_excel_phonetic_guides_are_not_cell_text(self):
        element = ET.fromstring(f'<si xmlns="{power.NS[1:-1]}"><t>発電用</t>'
                                '<rPh sb="0" eb="3"><t>ハツデンヨウ</t></rPh></si>')
        self.assertEqual("発電用", power.excel_text(element))

    def test_rich_text_runs_are_preserved(self):
        element = ET.fromstring(f'<si xmlns="{power.NS[1:-1]}"><r><t>A</t></r><r><t>重油</t></r></si>')
        self.assertEqual("A重油", power.excel_text(element))

    def test_output_replays_and_is_new_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp).resolve() / "run"
            power.write_new(out, power.bundle())
            power.verify(out)
            original = (out / "receipt.json").read_bytes()
            with self.assertRaises(FileExistsError):
                power.write_new(out, power.bundle())
            self.assertEqual(original, (out / "receipt.json").read_bytes())

    def test_loaded_source_change_is_rejected(self):
        with mock.patch.object(power, "LOADED_CODE_SHA256", "0" * 64):
            with self.assertRaisesRegex(ValueError, "loaded Python source changed"):
                power.bundle()

    def test_input_change_during_computation_is_rejected(self):
        original = power.regular_bytes
        calls = 0
        def changed(path):
            nonlocal calls
            calls += 1
            return original(path) + (b" " if calls == 3 else b"")
        with mock.patch.object(power, "regular_bytes", side_effect=changed):
            with self.assertRaisesRegex(ValueError, "inputs changed during computation"):
                power.bundle()

    def test_every_output_tamper_and_missing_file_rejected(self):
        for name in power.bundle():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                out = Path(tmp).resolve() / "run"
                power.write_new(out, power.bundle())
                (out / name).write_bytes(b"tamper")
                with self.assertRaises(ValueError):
                    power.verify(out)
                (out / name).unlink()
                with self.assertRaises(ValueError):
                    power.verify(out)

    def test_extra_output_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp).resolve() / "run"
            power.write_new(out, power.bundle())
            (out / "extra.txt").write_text("unexpected")
            with self.assertRaisesRegex(ValueError, "output set"):
                power.verify(out)

    def test_missing_and_changed_raw_source_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                power.extract(Path(tmp).resolve())
            for spec in power.SOURCES.values():
                (Path(tmp).resolve() / spec["filename"]).write_bytes(b"not the frozen workbook")
            with self.assertRaisesRegex(ValueError, "raw source hash mismatch"):
                power.extract(Path(tmp).resolve())

    def test_symlink_output_parent_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp).resolve() / "real"
            target.mkdir()
            link = Path(tmp).resolve() / "link"
            try:
                link.symlink_to(target, target_is_directory=True)
            except OSError as exc:
                self.skipTest(str(exc))
            with self.assertRaisesRegex(ValueError, "symlink"):
                power.write_new(link / "run", power.bundle())
            self.assertEqual([], list(target.iterdir()))


if __name__ == "__main__":
    unittest.main()
