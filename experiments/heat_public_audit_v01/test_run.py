import tempfile
import unittest
from pathlib import Path

import run


def exact(at="2025-07-01T12:00:00+09:00"):
    return {"status": "EXACT", "at": at, "evidence": "SYNTHETIC_TEST_LOG"}


def transaction(key="a", payer="client", payee="contractor", amount=100, stage="PAID"):
    return {"id": key, "item": "SYNTHETIC_TEST_ITEM", "payer": payer, "payee": payee,
            "amount_jpy": amount, "stage": stage,
            "paid_at": "2025-07-01T12:00:00+09:00" if stage == "PAID" else None,
            "evidence": "SYNTHETIC_TEST_RECEIPT"}


class CoverageTests(unittest.TestCase):
    def test_unknown_is_not_zero(self):
        self.assertEqual(run.coverage_bounds(None, 0, 0, 0)["status"], "UNKNOWN")

    def test_bounds_retain_missing_people(self):
        result = run.coverage_bounds(10, 6, 1, 3)
        self.assertEqual((result["lower"], result["upper"]), (.6, .9))
        self.assertEqual(result["unknown_fraction"], .3)

    def test_zero_denominator_rejected(self):
        with self.assertRaises(ValueError):
            run.coverage_bounds(0, 0, 0, 0)

    def test_bad_partition_rejected(self):
        with self.assertRaises(ValueError):
            run.coverage_bounds(10, 6, 1, 1)

    def test_bad_counts_rejected(self):
        for value in (True, -1, 1.5, float("nan"), float("inf")):
            with self.subTest(value=value), self.assertRaises(ValueError):
                run.coverage_bounds(10, value, 0, 0)


class TimeTests(unittest.TestCase):
    def test_timezone_conversion(self):
        result = run.elapsed_seconds(exact(), exact("2025-07-01T03:02:00Z"))
        self.assertEqual((result["lower_seconds"], result["upper_seconds"]), (120, 120))

    def test_no_timezone_rejected(self):
        with self.assertRaises(ValueError):
            run.elapsed_seconds(exact("2025-07-01T12:00:00"), exact())

    def test_approximation_not_point_imputed(self):
        end = {"status": "APPROXIMATE", "text": "約15分後", "evidence": "TEST"}
        self.assertEqual(run.elapsed_seconds(exact(), end)["status"], "UNKNOWN")

    def test_unknown_not_censored(self):
        self.assertEqual(run.elapsed_seconds(exact(), {"status": "UNKNOWN", "reason": "not published"})["status"], "UNKNOWN")

    def test_censor_requires_observed_cutoff(self):
        end = {"status": "NOT_DONE_BY_CUTOFF", "cutoff": "2025-07-01T12:15:00+09:00", "evidence": "TEST_OBSERVATION"}
        result = run.elapsed_seconds(exact(), end)
        self.assertEqual(result["lower_seconds"], 900)
        self.assertIsNone(result["upper_seconds"])

    def test_censor_without_evidence_rejected(self):
        with self.assertRaises(ValueError):
            run.elapsed_seconds(exact(), {"status": "NOT_DONE_BY_CUTOFF", "cutoff": "2025-07-01T12:15:00+09:00", "evidence": ""})

    def test_reverse_clock_rejected(self):
        with self.assertRaises(ValueError):
            run.elapsed_seconds(exact(), exact("2025-07-01T11:59:00+09:00"))

    def test_interval_kept_as_interval(self):
        end = {"status": "INTERVAL", "earliest": "2025-07-01T12:02:00+09:00", "latest": "2025-07-01T12:05:00+09:00", "evidence": "TEST_INTERVAL_LOG"}
        result = run.elapsed_seconds(exact(), end)
        self.assertEqual((result["lower_seconds"], result["upper_seconds"]), (120, 300))

    def test_invalid_status_rejected(self):
        with self.assertRaises(ValueError):
            run.elapsed_seconds(exact(), {"status": "probably_fine"})


class CashTests(unittest.TestCase):
    def test_missing_ledger_is_not_zero_cost(self):
        result = run.net_paid_cash([])
        self.assertEqual(result["status"], "UNKNOWN_EMPTY_LEDGER")
        self.assertIsNone(result["net_received_jpy"])

    def test_transfers_not_double_counted_cost(self):
        result = run.net_paid_cash([transaction(), transaction("b", "contractor", "worker")])
        self.assertEqual(result["net_received_jpy"], {"client": -100, "contractor": 0, "worker": 100})
        self.assertEqual(result["resource_cost"], "UNKNOWN")

    def test_approval_is_not_payment(self):
        result = run.net_paid_cash([transaction(stage="APPROVED")])
        self.assertEqual(result["net_received_jpy"], {})
        self.assertEqual(result["non_paid_rows"], 1)

    def test_duplicate_payment_rejected(self):
        with self.assertRaises(ValueError):
            run.net_paid_cash([transaction(), transaction()])

    def test_non_integer_cash_rejected(self):
        for amount in (-1, True, 1.5, float("nan")):
            with self.subTest(amount=amount), self.assertRaises(ValueError):
                run.net_paid_cash([transaction(amount=amount)])

    def test_paid_requires_date(self):
        row = transaction()
        row["paid_at"] = None
        with self.assertRaises(ValueError):
            run.net_paid_cash([row])

    def test_source_and_stage_required(self):
        for key, value in (("stage", "PENDING"), ("evidence", ""), ("payee", "client")):
            row = transaction()
            row[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                run.net_paid_cash([row])


class PublicAuditTests(unittest.TestCase):
    def setUp(self):
        self.evidence = run.read_json(run.HERE / "evidence.json")

    def test_public_descriptive_audit(self):
        result = run.analyze(self.evidence)
        self.assertEqual(result["national_change"]["casualties"], 546)
        self.assertEqual(result["national_change"]["deaths"], -12)
        self.assertEqual(result["exact_clock_pair_completeness"]["numerator"], 0)
        self.assertEqual(result["exact_clock_pair_completeness"]["denominator"], 19)
        self.assertEqual(result["unidentified"]["status"], "BLOCKED")

    def test_source_closure_and_hashes(self):
        run.verify_sources(self.evidence)

    def test_rounded_ratio_cannot_be_exact_count(self):
        self.evidence["measurements"][0]["numerator"] = 16048
        with self.assertRaises(ValueError):
            run.analyze(self.evidence)

    def test_different_denominators_rejected(self):
        self.evidence["rest_frequency"][0]["denominator"] = 1100
        with self.assertRaises(ValueError):
            run.analyze(self.evidence)

    def test_missing_or_duplicate_case_rejected(self):
        self.evidence["timing_case_audit"]["cases"][-1]["case_id"] = 1
        with self.assertRaises(ValueError):
            run.analyze(self.evidence)

    def test_unrelated_interval_not_latency(self):
        self.evidence["timing_case_audit"]["cases"][5]["reported_interval"]["is_initial_response_latency"] = True
        with self.assertRaises(ValueError):
            run.analyze(self.evidence)

    def test_descriptive_data_cannot_admit_model(self):
        self.evidence["calibration_gate"]["status"] = "READY"
        with self.assertRaises(ValueError):
            run.analyze(self.evidence)

    def test_forged_source_hash_rejected(self):
        self.evidence["sources"][0]["sha256"] = "0" * 64
        with self.assertRaises(ValueError):
            run.verify_sources(self.evidence)

    def test_source_directory_rejects_extras(self):
        with tempfile.TemporaryDirectory() as folder:
            evidence = {"sources": [{"file": "a", "id": "a", "sha256": "irrelevant"}]}
            (Path(folder) / "unexpected").write_text("fixture", encoding="utf-8")
            with self.assertRaises(ValueError):
                run.verify_sources(evidence, folder)

    def test_parser_rejects_nan_and_duplicate_keys(self):
        for text in ('{"x":NaN}', '{"x":1,"x":2}'):
            with tempfile.TemporaryDirectory() as folder:
                path = Path(folder) / "bad.json"
                path.write_text(text, encoding="utf-8")
                with self.assertRaises(ValueError):
                    run.read_json(path)

    def test_notebook_runs_and_keeps_gates(self):
        nb = run.notebook(self.evidence, run.analyze(self.evidence))
        code_cells = [c for c in nb["cells"] if c["cell_type"] == "code"]
        self.assertEqual([c["execution_count"] for c in code_cells], [1, 2, 3])
        self.assertTrue(any("BLOCKED" in "".join(o["text"]) for o in code_cells[-1]["outputs"]))


if __name__ == "__main__":
    unittest.main()
