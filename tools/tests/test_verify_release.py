from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from tools import verify_reference_replay, verify_release


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

    def refresh_manifest_record(
        self, root: Path, manifest_path: Path, relative: str
    ) -> None:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        target = root / relative
        manifest["files"][relative]["bytes"] = target.stat().st_size
        manifest["files"][relative]["sha256"] = verify_release.sha256_file(target)
        self.write_manifest(manifest_path, manifest)

    def replace_with_symlink(self, path: Path, target: Path) -> None:
        path.unlink()
        try:
            path.symlink_to(target)
        except OSError as exc:
            self.skipTest(f"symlinks unavailable on this platform: {exc}")

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

    def test_symlink_file_fails_even_when_bytes_match(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = self.copy_release(root)
            path = root / "artifacts/reference_run/summary.csv"
            real_path = root / "summary-copy.csv"
            shutil.copy2(path, real_path)
            self.replace_with_symlink(path, real_path)
            failures = verify_release.verify(root, manifest)
            self.assertTrue(any("symlink" in failure for failure in failures), failures)

    def test_symlink_directory_component_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = self.copy_release(root)
            path = root / "artifacts/reference_run"
            real_path = root / "reference-run-copy"
            path.rename(real_path)
            try:
                path.symlink_to(real_path, target_is_directory=True)
            except OSError as exc:
                self.skipTest(f"symlinks unavailable on this platform: {exc}")
            failures = verify_release.verify(root, manifest)
            self.assertTrue(any("symlink" in failure for failure in failures), failures)

    def test_manifest_symlink_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = self.copy_release(root)
            real_manifest = root / "manifest-copy.json"
            manifest.rename(real_manifest)
            try:
                manifest.symlink_to(real_manifest)
            except OSError as exc:
                self.skipTest(f"symlinks unavailable on this platform: {exc}")
            failures = verify_release.verify(root, manifest)
            self.assertTrue(any("symlink" in failure for failure in failures), failures)

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

    def test_missing_executable_closure_record_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = self.copy_release(root)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            del manifest["files"]["tools/verify_reference_replay.py"]
            self.write_manifest(manifest_path, manifest)
            failures = verify_release.verify(root, manifest_path)
            self.assertTrue(
                any("tools/verify_reference_replay.py" in failure for failure in failures),
                failures,
            )

    def test_unmanifested_executable_surface_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = self.copy_release(root)
            extra_test = root / "tools/tests/test_zz_unmanifested.py"
            extra_test.parent.mkdir(parents=True, exist_ok=True)
            extra_test.write_text(
                "raise RuntimeError('must never be auto-executed')\n",
                encoding="utf-8",
                newline="\n",
            )
            extra_workflow = root / ".github/workflows/unmanifested.yml"
            extra_workflow.write_text(
                "name: unmanifested\n",
                encoding="utf-8",
                newline="\n",
            )
            failures = verify_release.verify(root, manifest_path)
            self.assertTrue(
                any("unmanifested executable files" in failure for failure in failures),
                failures,
            )

    def test_auto_discovered_test_recipe_fails_even_with_updated_hash(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = self.copy_release(root)
            makefile = root / "Makefile"
            text = makefile.read_text(encoding="utf-8").replace(
                "$(PYTHON) -m unittest -v simulation.tests.test_rvcim_sim",
                "$(PYTHON) -m unittest discover -s simulation/tests -v",
                1,
            )
            makefile.write_text(text, encoding="utf-8", newline="\n")
            self.refresh_manifest_record(root, manifest_path, "Makefile")
            failures = verify_release.verify(root, manifest_path)
            self.assertTrue(
                any("must not auto-discover" in failure for failure in failures),
                failures,
            )

    def test_changed_file_role_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = self.copy_release(root)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["files"]["rvcim"]["role"] = "unreviewed wrapper"
            self.write_manifest(manifest_path, manifest)
            failures = verify_release.verify(root, manifest_path)
            self.assertTrue(any("rvcim: role must be" in failure for failure in failures))

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

    def test_missing_external_trust_model_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = self.copy_release(root)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["provenance"]["trust_model"] = "self-authenticating"
            self.write_manifest(manifest_path, manifest)
            failures = verify_release.verify(root, manifest_path)
            self.assertTrue(any("trust_model" in failure for failure in failures))

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

    def test_checkout_policy_semantics_fail_even_with_updated_hash(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = self.copy_release(root)
            attributes = root / ".gitattributes"
            attributes.write_text("* text=auto\n\n*.pdf -text\n", encoding="utf-8")
            self.refresh_manifest_record(root, manifest_path, ".gitattributes")
            failures = verify_release.verify(root, manifest_path)
            self.assertTrue(any("pin automatic text checkout" in failure for failure in failures))

    def test_crlf_checkout_fails_even_with_updated_hash(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = self.copy_release(root)
            launcher = root / "rvcim.cmd"
            launcher.write_bytes(launcher.read_bytes().replace(b"\n", b"\r\n"))
            self.refresh_manifest_record(root, manifest_path, "rvcim.cmd")
            failures = verify_release.verify(root, manifest_path)
            self.assertTrue(any("LF without CR bytes" in failure for failure in failures))

    def test_write_enabled_workflow_fails_even_with_updated_hash(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = self.copy_release(root)
            workflow = root / ".github/workflows/verify.yml"
            text = workflow.read_text(encoding="utf-8").replace(
                "contents: read", "contents: write", 1
            )
            workflow.write_text(text, encoding="utf-8")
            self.refresh_manifest_record(
                root, manifest_path, ".github/workflows/verify.yml"
            )
            failures = verify_release.verify(root, manifest_path)
            self.assertTrue(any("contents: write" in failure for failure in failures))

    def test_normal_experiment_cannot_target_committed_fixture(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = self.copy_release(root)
            makefile = root / "Makefile"
            text = makefile.read_text(encoding="utf-8").replace(
                "--out .tmp/experiment",
                "--out artifacts/reference_run",
                1,
            )
            makefile.write_text(text, encoding="utf-8")
            self.refresh_manifest_record(root, manifest_path, "Makefile")
            failures = verify_release.verify(root, manifest_path)
            self.assertTrue(
                any("must not write the committed fixture" in failure for failure in failures),
                failures,
            )

    def test_reference_replay_rejects_symlink_input(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.copy_release(root)
            config = root / "simulation/configs/minimal.json"
            real_config = root / "minimal-copy.json"
            shutil.copy2(config, real_config)
            self.replace_with_symlink(config, real_config)
            failures = verify_reference_replay.verify_replay(
                root, root / "artifacts/reference_run"
            )
            self.assertTrue(any("symlink" in failure for failure in failures), failures)


if __name__ == "__main__":
    unittest.main()
