"""Publication checks outside the four frozen r02 analysis inputs."""
import contextlib
import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import run


class PublicationTests(unittest.TestCase):
    def setUp(self):
        self.artifacts = run.ROOT / "artifacts/heat_public_audit_v01"

    def test_delivered_html_and_analysis_receipt_keep_checkpoint_hashes(self):
        validation = run.read_json(self.artifacts / "VALIDATION.json")
        self.assertEqual("2026-09-09", validation["checked_on"])
        self.assertEqual(validation["html_delivery"]["sha256"],
                         run.digest(self.artifacts / "report.html"))
        self.assertEqual(validation["analysis_receipt_sha256"],
                         run.digest(self.artifacts / "analysis-r02/receipt.json"))

    def test_failed_packaging_draft_retains_its_inputs_and_outputs(self):
        receipt = run.read_json(self.artifacts / "analysis/receipt.json")
        inputs = self.artifacts / "history/r01_inputs"
        self.assertEqual(set(run.ARCHIVED_INPUTS), set(receipt["input_sha256"]))
        self.assertEqual(set(run.ARCHIVED_INPUTS), {p.name for p in inputs.iterdir()})
        for name, sha in receipt["input_sha256"].items():
            self.assertEqual(sha, run.digest(inputs / name), name)
        for name, sha in receipt["output_sha256"].items():
            self.assertEqual(sha, run.digest(self.artifacts / "analysis" / name), name)

    def test_raw_source_bytes_are_not_git_text_normalized(self):
        rules = (self.artifacts / ".gitattributes").read_text(encoding="utf-8")
        self.assertIn("sources/* -text", rules.splitlines())
        # This snapshot actually has CRLF. A clean checkout must retain the
        # original source digest, not silently rewrite evidence on publication.
        raw = (self.artifacts / "sources/wage_faq.html").read_bytes()
        self.assertIn(b"\r\n", raw)
        run.verify_sources(run.read_json(run.HERE / "evidence.json"))

    def test_r02_frozen_inputs_and_outputs_replay_without_legacy_execution(self):
        out = self.artifacts / "analysis-r02"
        inputs = run.input_snapshot(run.R02_INPUT_DIR, run.ARCHIVED_INPUTS)
        self.assertEqual(set(inputs), {p.name for p in run.R02_INPUT_DIR.iterdir()})
        self.assertEqual(run.R02_RECEIPT_SHA256, run.digest(out / "receipt.json"))
        run.verify_output(out, run.read_json(run.R02_INPUT_DIR / "evidence.json"),
                          inputs, run.R02_INPUT_DIR, run.ARCHIVED_INPUTS)


class PublicationSafetyTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="heat-public-tests-")
        self.addCleanup(self.temporary.cleanup)
        self.folder = Path(self.temporary.name).resolve()
        self.out = self.folder / "new-output"
        self.evidence = run.read_json(run.HERE / "evidence.json")

    def invoke(self, *args):
        with mock.patch.object(sys, "argv", ["run.py", *map(str, args)]), contextlib.redirect_stdout(io.StringIO()):
            run.main()

    def generate(self):
        self.invoke("--out", self.out)

    def verify(self):
        run.verify_output(self.out, self.evidence, run.input_snapshot())

    def symlink(self, link, target, directory=False):
        try:
            link.symlink_to(target, target_is_directory=directory)
        except OSError as exc:
            self.skipTest(f"symlinks unavailable: {exc}")

    def test_new_bundle_generates_and_replays(self):
        self.generate()
        self.invoke("--out", self.out, "--verify")
        self.assertEqual(set(run.OUTPUTS), {p.name for p in self.out.iterdir()})
        self.assertEqual(set(run.INPUTS), set(run.read_json(self.out / "receipt.json")["input_sha256"]))
        self.assertNotIn(b"\r\n", (self.out / "receipt.json").read_bytes())

    def test_existing_bundle_is_not_overwritten_even_with_same_inputs(self):
        self.generate()
        before = {p.name: p.read_bytes() for p in self.out.iterdir()}
        with self.assertRaisesRegex(ValueError, "output exists"):
            self.generate()
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.out.iterdir()})

    def test_existing_empty_directory_is_not_reused(self):
        self.out.mkdir()
        with self.assertRaisesRegex(ValueError, "output exists"):
            self.generate()
        self.assertEqual([], list(self.out.iterdir()))

    def test_existing_output_file_link_cannot_overwrite_a_sentinel(self):
        self.generate()
        sentinel = self.folder / "sentinel"
        sentinel.write_bytes(b"DO_NOT_REPLACE")
        (self.out / "audit.json").unlink()
        self.symlink(self.out / "audit.json", sentinel)
        with self.assertRaises(ValueError):
            self.generate()
        self.assertEqual(b"DO_NOT_REPLACE", sentinel.read_bytes())
        with self.assertRaises(ValueError):
            self.verify()

    def test_symlinked_output_ancestor_is_rejected_before_creation(self):
        target = self.folder / "real"
        target.mkdir()
        alias = self.folder / "alias"
        self.symlink(alias, target, directory=True)
        with self.assertRaisesRegex(ValueError, "symlink"):
            self.invoke("--out", alias / "new")
        self.assertFalse((target / "new").exists())

    def test_symlinked_output_ancestor_is_rejected_on_verification(self):
        self.generate()
        alias = self.folder / "alias"
        self.symlink(alias, self.folder, directory=True)
        with self.assertRaisesRegex(ValueError, "symlink"):
            self.invoke("--out", alias / self.out.name, "--verify")

    def test_symlinked_source_ancestor_is_rejected(self):
        alias = self.folder / "alias"
        self.symlink(alias, run.SOURCE_DIR.parent, directory=True)
        with self.assertRaisesRegex(ValueError, "symlink"):
            run.verify_sources(self.evidence, alias / "sources")

    def test_exclusive_json_writer_refuses_existing_files(self):
        sentinel = self.folder / "sentinel"
        sentinel.write_bytes(b"DO_NOT_REPLACE")
        with self.assertRaises(FileExistsError):
            run.write_json(sentinel, {})
        self.assertEqual(b"DO_NOT_REPLACE", sentinel.read_bytes())

    def test_receipt_metadata_tampering_fails_closed(self):
        self.generate()
        original = run.read_json(self.out / "receipt.json")
        for key, value in (("format", "other/v1"), ("calibration", "READY"),
                           ("source_closure", "NOT_CHECKED"), ("notebook_cells_executed", True),
                           ("notebook_cells_executed", 4), ("notebook_engine", "Jupyter"),
                           ("generated_at", "2026-09-09T10:00:00"), ("extra", "unrecognized")):
            with self.subTest(key=key, value=value):
                receipt = dict(original)
                receipt[key] = value
                (self.out / "receipt.json").write_text(json.dumps(receipt), encoding="utf-8")
                with self.assertRaises(ValueError):
                    self.verify()

    def test_each_missing_changed_or_extra_output_is_rejected(self):
        self.generate()
        for name in run.OUTPUTS:
            path = self.out / name
            original = path.read_bytes()
            with self.subTest(name=name, kind="missing"):
                path.unlink()
                with self.assertRaises(ValueError):
                    self.verify()
            path.write_bytes(original + b"tamper")
            with self.subTest(name=name, kind="changed"), self.assertRaises(ValueError):
                self.verify()
            path.write_bytes(original)
        (self.out / "extra").write_bytes(b"extra")
        with self.assertRaises(ValueError):
            self.verify()

    def test_overflow_json_number_rejected_recursively(self):
        path = self.folder / "overflow.json"
        for text in ('{"x":1e999}', '{"x":[{"y":-1e999}]}'):
            path.write_text(text, encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "nonfinite"):
                run.read_json(path)

    def test_transcription_queries_close_their_database_connections(self):
        connections = []
        original = run.sqlite3.connect
        def track(*args, **kwargs):
            connection = original(*args, **kwargs)
            connections.append(connection)
            return connection
        with mock.patch.object(run.sqlite3, "connect", side_effect=track):
            run.report_artifact(self.evidence, run.analyze(self.evidence), "2026-09-09T13:13:49Z")
        self.assertEqual(2, len(connections))
        for connection in connections:
            with self.assertRaises(run.sqlite3.ProgrammingError):
                connection.execute("SELECT 1")

    def test_legacy_inputs_are_read_only(self):
        with self.assertRaisesRegex(ValueError, "verification-only"):
            self.invoke("--out", self.out, "--input-revision", "r02")
        self.assertFalse(self.out.exists())

    def test_legacy_replay_rejects_receipt_claim_escalation(self):
        shutil.copytree(run.ROOT / "artifacts/heat_public_audit_v01/analysis-r02", self.out)
        receipt = run.read_json(self.out / "receipt.json")
        receipt["calibration"] = "READY"
        (self.out / "receipt.json").write_text(json.dumps(receipt), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "pinned r02 receipt"):
            self.invoke("--out", self.out, "--verify", "--input-revision", "r02")

    def test_changed_inputs_abort_before_publication(self):
        original = run.notebook
        def change_identity(*args):
            value = original(*args)
            run.LOADED_SOURCE_SHA256 = "0" * 64
            return value
        with mock.patch.object(run, "LOADED_SOURCE_SHA256", run.LOADED_SOURCE_SHA256):
            with mock.patch.object(run, "notebook", side_effect=change_identity):
                with self.assertRaisesRegex(ValueError, "loaded source changed"):
                    self.generate()
        self.assertFalse(self.out.exists())


if __name__ == "__main__":
    unittest.main()
