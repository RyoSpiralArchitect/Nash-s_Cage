import copy
import gzip
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import run


class PublicationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        # Resolve macOS /var -> /private/var before applying the no-symlink policy.
        self.root = Path(self.temp.name).resolve()
        self.plan = run.decode(run.read(run.HERE / "plan.json"))

    def tearDown(self):
        self.temp.cleanup()

    def bundle(self):
        freeze_dir, output = self.root / "freeze", self.root / "out"
        run.freeze(freeze_dir)
        run.run(freeze_dir / "registration.json", "smoke", output, 1)
        return output

    def test_freeze_and_replay(self):
        out = self.bundle()
        self.assertEqual({p.name for p in out.iterdir()}, run.OUTPUTS)
        self.assertTrue(run.verify(out, replay=True)["replayed"])

    def test_parallel_payload_parity(self):
        serial = run.compute(self.plan, "smoke", 1)
        parallel = run.compute(self.plan, "smoke", 2)
        self.assertEqual(serial, parallel)

    def test_complete_denominators_and_witnesses(self):
        output = run.compute(self.plan, "smoke")
        summary = run.decode(output["summary.json"])
        self.assertEqual(summary["world_count"], 12)
        self.assertEqual(summary["arm_world_count"], 48)
        classes = [run.decode(line) for line in gzip.decompress(output["classes.jsonl.gz"]).splitlines()]
        for report in summary["reports"]:
            selected = [r for r in classes if r["view"] == report["view"] and r["contrast"] == report["contrast"]]
            self.assertEqual(sum(r["world_count"] for r in selected), 12)
            self.assertEqual(len(selected), report["class_denominator"])
            self.assertEqual(sum(report["optimistic_label_confusions"].values()), 12)
            self.assertEqual(sum(report[k] for k in ("MODEL_ALL_PASS", "MODEL_ALL_FAIL", "UNIDENTIFIED_WITHIN_CATALOGUE")), len(selected))
            if report["view"] == "full_model_inputs":
                self.assertEqual(report["worlds_in_unidentified_classes"], 0)
                self.assertEqual(report["optimistic_false_positive_worlds"], 0)
                self.assertEqual(report["optimistic_missed_qualifying_worlds"], 0)
        for witness in run.decode(output["witnesses.json"]):
            for key, value in witness["observed"].items():
                self.assertEqual(witness["pass_world"]["world"][key], value)
                self.assertEqual(witness["fail_world"]["world"][key], value)
            self.assertTrue(witness["pass_world"]["qualifies"][witness["contrast"]])
            self.assertFalse(witness["fail_world"]["qualifies"][witness["contrast"]])

    def test_no_overwrite(self):
        out = self.bundle()
        before = {p.name: p.read_bytes() for p in out.iterdir()}
        with self.assertRaises(FileExistsError):
            run.run(self.root / "freeze/registration.json", "smoke", out, 1)
        self.assertEqual(before, {p.name: p.read_bytes() for p in out.iterdir()})
        with self.assertRaises(FileExistsError):
            run.freeze(self.root / "freeze")

    def test_missing_extra_and_corrupted_output_fail(self):
        out = self.bundle()
        target = out / "summary.json"
        original = target.read_bytes()
        target.write_bytes(original + b" ")
        with self.assertRaises(ValueError):
            run.verify(out)
        target.write_bytes(original)
        extra = out / "extra.json"
        extra.write_bytes(b"{}")
        with self.assertRaises(ValueError):
            run.verify(out)
        extra.unlink()
        target.unlink()
        with self.assertRaises(ValueError):
            run.verify(out)

    def test_incomplete_computation_has_no_success_receipt(self):
        run.freeze(self.root / "freeze")
        with patch.object(run, "compute", side_effect=RuntimeError("injected interruption")):
            with self.assertRaises(RuntimeError):
                run.run(self.root / "freeze/registration.json", "smoke", self.root / "partial", 1)
        self.assertFalse((self.root / "partial/receipt.json").exists())
        with self.assertRaises(ValueError):
            run.verify(self.root / "partial")

    def test_source_drift_rejected(self):
        registration = run.freeze(self.root / "freeze")
        mutated = copy.deepcopy(registration["inputs"])
        mutated["model.py"] = "0" * 64
        with patch.object(run, "source_hashes", return_value=mutated):
            with self.assertRaises(ValueError):
                run.validate_registration(registration)

    def test_honest_boundary_and_utc_required(self):
        registration = run.freeze(self.root / "freeze")
        for key, value in (("claim_level", "EMPIRICAL"), ("scope", "external preregistration"),
                           ("created_utc", "2026-10-29T00:00:00")):
            with self.assertRaises(ValueError):
                run.validate_registration(registration | {key: value})

    def test_symlink_rejected(self):
        target = self.root / "file"
        target.write_bytes(b"{}")
        link = self.root / "link"
        try:
            link.symlink_to(target)
        except OSError:
            self.skipTest("symlink creation unavailable on this host")
        with self.assertRaises(ValueError):
            run.read(link)

    def test_json_rejects_nonfinite_and_duplicate(self):
        for blob in (b'{"a":1,"a":2}', b'{"a":NaN}', b'{"a":Infinity}', b'{"a":[1e999]}'):
            with self.assertRaises(ValueError):
                run.decode(blob)

    def test_rehash_is_not_a_substitute_for_replay(self):
        out = self.bundle()
        target = out / "witnesses.json"
        target.write_bytes(b"[]\n")
        receipt_path = out / "receipt.json"
        receipt = run.decode(receipt_path.read_bytes())
        receipt["outputs"]["witnesses.json"] = run.digest(target.read_bytes())
        receipt_path.write_bytes(run.encode(receipt))
        self.assertTrue(run.verify(out)["verified"])  # Internal hashes alone are insufficient.
        with self.assertRaises(ValueError):
            run.verify(out, replay=True)

    def test_receipt_runtime_types_rejected(self):
        out = self.bundle()
        path = out / "receipt.json"
        original = run.decode(path.read_bytes())
        for key, value in (("processes", True), ("elapsed_seconds", -1), ("python", "unknown")):
            receipt = copy.deepcopy(original)
            receipt["runtime"][key] = value
            path.write_bytes(run.encode(receipt))
            with self.assertRaises(ValueError):
                run.verify(out)


if __name__ == "__main__":
    unittest.main()
