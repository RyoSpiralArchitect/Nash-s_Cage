"""Publication checks outside the four frozen r02 analysis inputs."""
import unittest
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
        self.assertEqual(set(run.INPUTS), set(receipt["input_sha256"]))
        self.assertEqual(set(run.INPUTS), {p.name for p in inputs.iterdir()})
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


if __name__ == "__main__":
    unittest.main()
