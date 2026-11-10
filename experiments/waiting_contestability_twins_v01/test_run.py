import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import run
from model import validate_plan


class RunnerTests(unittest.TestCase):
    def fixture(self, root):
        run.freeze(root/"freeze")
        run.run(root/"freeze/registration.json", "smoke", root/"output", 1)
        return root/"output"

    def test_freeze_run_replay_and_closure(self):
        with tempfile.TemporaryDirectory() as d:
            out=self.fixture(Path(d).resolve())
            self.assertTrue(run.verify(out, True)["replayed"])
            self.assertEqual({p.name for p in out.iterdir()},run.OUTPUTS)

    def test_no_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d).resolve(); out=self.fixture(root)
            with self.assertRaises(FileExistsError): run.freeze(root/"freeze")
            with self.assertRaises(FileExistsError): run.run(root/"freeze/registration.json", "smoke", out,1)

    def test_corrupt_output(self):
        with tempfile.TemporaryDirectory() as d:
            out=self.fixture(Path(d).resolve()); (out/"summary.json").write_bytes(b"{}")
            with self.assertRaises(ValueError): run.verify(out)

    def test_extra_and_missing_output(self):
        with tempfile.TemporaryDirectory() as d:
            out=self.fixture(Path(d).resolve()); (out/"unexpected").touch()
            with self.assertRaises(ValueError): run.verify(out)
            (out/"unexpected").unlink(); (out/"summary.json").unlink()
            with self.assertRaises(ValueError): run.verify(out)

    def test_replay_detects_rehashed_payload(self):
        with tempfile.TemporaryDirectory() as d:
            out=self.fixture(Path(d).resolve()); (out/"witnesses.json").write_bytes(b"[]\n")
            receipt=run.decode((out/"receipt.json").read_bytes())
            receipt["outputs"]["witnesses.json"]=run.digest(b"[]\n")
            (out/"receipt.json").write_bytes(run.encode(receipt))
            self.assertTrue(run.verify(out)["verified"])
            with self.assertRaises(ValueError): run.verify(out,True)

    def test_bad_json_and_plan(self):
        for data in ['{"x":1,"x":2}','{"x":NaN}','{"x":1e999}']:
            with self.assertRaises(ValueError):run.decode(data)
        p=run.decode(run.read(run.HERE/"plan.json"));p["world_count"]=1
        with self.assertRaises(ValueError):validate_plan(p)

    def test_source_drift(self):
        with tempfile.TemporaryDirectory() as d:
            reg=run.freeze(Path(d).resolve()/"freeze")
            with patch.object(run,"source_hashes",return_value={}):
                with self.assertRaises(ValueError):run.validate_registration(reg)

    def test_runtime_and_process_cap(self):
        p=run.decode(run.read(run.HERE/"plan.json"))
        with self.assertRaises(ValueError):run.compute(p,"smoke",2)
        with tempfile.TemporaryDirectory() as d:
            out=self.fixture(Path(d).resolve());r=run.decode((out/"receipt.json").read_bytes())
            r["runtime"]["elapsed_seconds"]=-1
            (out/"receipt.json").write_bytes(run.encode(r))
            with self.assertRaises(ValueError):run.verify(out)

    def test_symlink_denied(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d).resolve();(root/"file").write_text("x");(root/"alias").symlink_to(root/"file")
            with self.assertRaises(ValueError):run.read(root/"alias")

    def test_full_input_view_no_mixture_in_smoke(self):
        p=run.decode(run.read(run.HERE/"plan.json"));s=run.decode(run.compute(p,"smoke")["summary.json"])
        for r in s["reports"]:
            if r["view"]=="full_model_evaluator_only":self.assertFalse(any(r["mixed_classes"].values()))
        for stats in s["totals"]["nominal"].values():
            self.assertEqual(stats["positive"]+stats["negative"],0)

if __name__ == "__main__":unittest.main()
