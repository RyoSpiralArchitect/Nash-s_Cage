from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from tools import verify_release


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


class ReleaseVerificationTests(unittest.TestCase):
    def copy_release(self, destination: Path) -> Path:
        manifest_source = REPOSITORY_ROOT / "RELEASE_MANIFEST.json"
        manifest = json.loads(manifest_source.read_text(encoding="utf-8"))
        for relative in manifest["files"]:
            source = REPOSITORY_ROOT / relative
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        manifest_target = destination / "RELEASE_MANIFEST.json"
        shutil.copy2(manifest_source, manifest_target)
        return manifest_target

    @staticmethod
    def write_manifest(path: Path, manifest: dict[str, object]) -> None:
        path.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def test_committed_release_verifies(self) -> None:
        failures = verify_release.verify(
            REPOSITORY_ROOT, REPOSITORY_ROOT / "RELEASE_MANIFEST.json"
        )
        self.assertEqual([], failures)

    def test_modified_file_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = self.copy_release(root)
            with (root / "artifacts/reference_run/summary.csv").open("ab") as handle:
                handle.write(b"tamper")
            failures = verify_release.verify(root, manifest)
            self.assertTrue(any("hash mismatch" in failure for failure in failures))

    def test_missing_file_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = self.copy_release(root)
            (root / "artifacts/reference_run/receipt.json").unlink()
            failures = verify_release.verify(root, manifest)
            self.assertTrue(any("missing regular file" in failure for failure in failures))

    def test_unexpected_manifest_record_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = self.copy_release(root)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["files"]["unexpected.bin"] = {
                "bytes": 0,
                "sha256": "0" * 64,
            }
            self.write_manifest(manifest_path, manifest)
            failures = verify_release.verify(root, manifest_path)
            self.assertTrue(
                any("unexpected records" in failure for failure in failures)
            )

    def test_stronger_claim_level_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = self.copy_release(root)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["claim_level"] = "F3"
            manifest["claim_boundary"] = "Production-safe institutional pilot."
            self.write_manifest(manifest_path, manifest)
            failures = verify_release.verify(root, manifest_path)
            self.assertTrue(any("claim_level" in failure for failure in failures))
            self.assertTrue(any("claim_boundary" in failure for failure in failures))

    def test_changed_manuscript_provenance_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = self.copy_release(root)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["files"]["paper/nashs_cage_rvcim_v0_2.pdf"][
                "provenance"
            ] = "historical-byte-identical"
            self.write_manifest(manifest_path, manifest)
            failures = verify_release.verify(root, manifest_path)
            self.assertTrue(
                any(
                    "nashs_cage_rvcim_v0_2.pdf: provenance" in failure
                    for failure in failures
                )
            )

    def test_changed_reference_command_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = self.copy_release(root)
            receipt_path = root / "artifacts/reference_run/receipt.json"
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            receipt["command"]["episodes"] = 1
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            failures = verify_release.verify(root, manifest_path)
            self.assertTrue(
                any("reference command" in failure for failure in failures)
            )


if __name__ == "__main__":
    unittest.main()
