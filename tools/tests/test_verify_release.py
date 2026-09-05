from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from tools import verify_reference_replay, verify_release


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SUSTAINED_REQUIRED_FILES = (
    "simulation/sustained.py",
    "simulation/tests/test_sustained.py",
    "simulation/configs/sustained_v04.json",
    "simulation/configs/sustained_stress_plan.json",
    "docs/SUSTAINED_V04_CONTRACT.md",
    "tools/run_sustained.py",
    "tools/tests/test_sustained_runner.py",
    "artifacts/sustained_v04/episodes.csv",
    "artifacts/sustained_v04/summary.json",
    "artifacts/sustained_v04/trace.csv",
    "artifacts/sustained_v04/resolved_plan.json",
    "artifacts/sustained_v04/receipt.json",
    "artifacts/sustained_v04/comparison.md",
)


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

    def test_release_closure_has_exactly_sixty_one_records(self) -> None:
        self.assertEqual(61, len(verify_release.REQUIRED_FILES))
        self.assertEqual(
            verify_release.REQUIRED_FILES,
            frozenset(verify_release.EXPECTED_ROLES),
        )
        self.assertEqual(
            set(SUSTAINED_REQUIRED_FILES),
            verify_release.REQUIRED_FILES
            - {
                relative
                for relative in verify_release.REQUIRED_FILES
                if "sustained" not in relative.lower()
            },
        )

    def test_modified_file_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = self.copy_release(root)
            with (root / "artifacts/reference_run/summary.csv").open("ab") as handle:
                handle.write(b"tamper")
            failures = verify_release.verify(root, manifest)
            self.assertTrue(any("hash mismatch" in failure for failure in failures))

    def test_each_empirical_file_is_required(self) -> None:
        for relative in verify_release.POWER_ROLES:
            with self.subTest(relative=relative), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                manifest = self.copy_release(root)
                (root / relative).unlink()
                self.assertTrue(verify_release.verify(root, manifest))

    def test_empirical_make_safety_and_verify_dependencies(self) -> None:
        for old, new, message in (
            ("--out .tmp/power-accounting", "--out artifacts/power_jp_fy2024", "new-only output"),
            ("--out .tmp/power-accounting", "--out .tmp/power-accounting --overwrite", "new-only output"),
            ("verify-sustained verify-power\n", "verify-sustained\n", "all legacy and experimental checks"),
            ("verify --out artifacts/power_jp_fy2024 --replay", "verify --out artifacts/power_jp_fy2024", "make verify-power"),
        ):
            with self.subTest(new=new), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                manifest = self.copy_release(root)
                path = root / "Makefile"
                original = path.read_text(encoding="utf-8")
                self.assertIn(old, original)
                path.write_text(original.replace(old, new, 1), encoding="utf-8")
                self.refresh_manifest_record(root, manifest, "Makefile")
                failures = verify_release.verify(root, manifest)
                self.assertTrue(any(message in f for f in failures), failures)

    def test_missing_file_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = self.copy_release(root)
            (root / "artifacts/reference_run/receipt.json").unlink()
            failures = verify_release.verify(root, manifest)
            self.assertTrue(any("missing regular file" in failure for failure in failures))

    def test_missing_experimental_file_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = self.copy_release(root)
            relative = "artifacts/feasibility_v03/receipt.json"
            (root / relative).unlink()
            failures = verify_release.verify(root, manifest)
            self.assertIn(f"{relative}: missing regular file", failures)

    def test_each_sustained_file_removal_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = self.copy_release(root)
            for relative in SUSTAINED_REQUIRED_FILES:
                with self.subTest(relative=relative):
                    target = root / relative
                    target.unlink()
                    failures = verify_release.verify(root, manifest)
                    self.assertIn(f"{relative}: missing regular file", failures)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(REPOSITORY_ROOT / relative, target)

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

    def test_missing_experimental_manifest_record_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = self.copy_release(root)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            relative = "simulation/feasibility.py"
            del manifest["files"][relative]
            self.write_manifest(manifest_path, manifest)
            failures = verify_release.verify(root, manifest_path)
            self.assertTrue(
                any(
                    "missing required records" in failure and relative in failure
                    for failure in failures
                ),
                failures,
            )

    def test_each_sustained_manifest_record_removal_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = self.copy_release(root)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            for relative in SUSTAINED_REQUIRED_FILES:
                with self.subTest(relative=relative):
                    removed = manifest["files"].pop(relative)
                    self.write_manifest(manifest_path, manifest)
                    failures = verify_release.verify(root, manifest_path)
                    self.assertTrue(
                        any(
                            "missing required records" in failure
                            and relative in failure
                            for failure in failures
                        ),
                        failures,
                    )
                    manifest["files"][relative] = removed

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

    def test_unmanifested_feasibility_test_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = self.copy_release(root)
            relative = "simulation/tests/test_feasibility_unreviewed.py"
            (root / relative).write_text(
                "raise RuntimeError('must never be auto-executed')\n",
                encoding="utf-8",
                newline="\n",
            )
            failures = verify_release.verify(root, manifest_path)
            self.assertTrue(
                any(
                    "unmanifested executable files" in failure and relative in failure
                    for failure in failures
                ),
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

    def test_removed_windows_exit_check_fails_even_with_updated_hash(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = self.copy_release(root)
            workflow = root / ".github/workflows/verify.yml"
            text = workflow.read_text(encoding="utf-8")
            native_command = (
                "python tools/verify_release.py --root . --manifest RELEASE_MANIFEST.json"
            )
            protected = native_command + "\n          " + verify_release.WINDOWS_EXIT_CHECK
            self.assertIn(protected, text)
            workflow.write_text(
                text.replace(protected, native_command, 1),
                encoding="utf-8",
                newline="\n",
            )
            self.refresh_manifest_record(root, manifest_path, ".github/workflows/verify.yml")
            failures = verify_release.verify(root, manifest_path)
            self.assertTrue(
                any("must immediately check LASTEXITCODE" in failure for failure in failures),
                failures,
            )

    def test_each_windows_native_exit_check_is_required(self) -> None:
        workflow = (REPOSITORY_ROOT / ".github/workflows/verify.yml").read_text(
            encoding="utf-8"
        )
        self.assertEqual([], verify_release.verify_windows_workflow(workflow))
        lines = workflow.splitlines()
        check_indexes = [
            index for index, line in enumerate(lines)
            if line.strip() == verify_release.WINDOWS_EXIT_CHECK
        ]
        self.assertEqual(
            len(verify_release.WINDOWS_REQUIRED_NATIVE_COMMANDS),
            len(check_indexes),
        )
        for index in check_indexes:
            with self.subTest(native_command=lines[index - 1].strip()):
                modified = "\n".join(lines[:index] + lines[index + 1 :])
                failures = verify_release.verify_windows_workflow(modified)
                self.assertTrue(
                    any(
                        "must immediately check LASTEXITCODE" in failure
                        for failure in failures
                    ),
                    failures,
                )

    def test_each_windows_native_command_is_required(self) -> None:
        workflow = (REPOSITORY_ROOT / ".github/workflows/verify.yml").read_text(
            encoding="utf-8"
        )
        lines = workflow.splitlines()
        for command in verify_release.WINDOWS_REQUIRED_NATIVE_COMMANDS:
            with self.subTest(native_command=command):
                indexes = [
                    index for index, line in enumerate(lines) if line.strip() == command
                ]
                self.assertEqual(1, len(indexes))
                index = indexes[0]
                self.assertEqual(
                    verify_release.WINDOWS_EXIT_CHECK,
                    lines[index + 1].strip(),
                )
                modified = "\n".join(lines[:index] + lines[index + 2 :])
                failures = verify_release.verify_windows_workflow(modified)
                self.assertTrue(
                    any(
                        "missing required native commands" in failure
                        and command in failure
                        for failure in failures
                    ),
                    failures,
                )

    def test_missing_windows_experimental_replay_is_rejected(self) -> None:
        workflow = (REPOSITORY_ROOT / ".github/workflows/verify.yml").read_text(
            encoding="utf-8"
        )
        command = (
            "python tools/run_feasibility.py verify "
            "--out artifacts/feasibility_v03 --replay"
        )
        self.assertIn(command, workflow)
        failures = verify_release.verify_windows_workflow(workflow.replace(command, "# removed"))
        self.assertIn(
            "Windows verification must replay the experimental feasibility fixture", failures
        )

    def test_missing_windows_sustained_replay_is_rejected(self) -> None:
        workflow = (REPOSITORY_ROOT / ".github/workflows/verify.yml").read_text(
            encoding="utf-8"
        )
        command = (
            "python tools/run_sustained.py verify "
            "--out artifacts/sustained_v04 --replay"
        )
        self.assertIn(command, workflow)
        failures = verify_release.verify_windows_workflow(
            workflow.replace(command, "# removed")
        )
        self.assertIn(
            "Windows verification must replay the experimental sustained fixture",
            failures,
        )

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

    def test_feasibility_cannot_target_committed_fixture_or_overwrite(self) -> None:
        for replacement in (
            "--out artifacts/feasibility_v03",
            "--out .tmp/feasibility --overwrite",
        ):
            with self.subTest(replacement=replacement), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                manifest_path = self.copy_release(root)
                makefile = root / "Makefile"
                text = makefile.read_text(encoding="utf-8")
                self.assertIn("--out .tmp/feasibility", text)
                makefile.write_text(
                    text.replace("--out .tmp/feasibility", replacement, 1),
                    encoding="utf-8",
                    newline="\n",
                )
                self.refresh_manifest_record(root, manifest_path, "Makefile")
                failures = verify_release.verify(root, manifest_path)
                self.assertIn(
                    "make feasibility must create new-only output at fixed .tmp/feasibility",
                    failures,
                )

    def test_sustained_cannot_target_committed_fixture_or_overwrite(self) -> None:
        for replacement in (
            "--out artifacts/sustained_v04",
            "--out .tmp/sustained --overwrite",
        ):
            with self.subTest(replacement=replacement), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                manifest_path = self.copy_release(root)
                makefile = root / "Makefile"
                text = makefile.read_text(encoding="utf-8")
                self.assertIn("--out .tmp/sustained", text)
                makefile.write_text(
                    text.replace("--out .tmp/sustained", replacement, 1),
                    encoding="utf-8",
                    newline="\n",
                )
                self.refresh_manifest_record(root, manifest_path, "Makefile")
                failures = verify_release.verify(root, manifest_path)
                self.assertIn(
                    "make sustained must create new-only output at fixed .tmp/sustained",
                    failures,
                )

    def test_missing_experimental_verify_dependency_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = self.copy_release(root)
            makefile = root / "Makefile"
            text = makefile.read_text(encoding="utf-8")
            old = "verify: verify-release compile test smoke verify-artifact verify-reference-replay verify-feasibility"
            self.assertIn(old, text)
            makefile.write_text(
                text.replace(old, old.removesuffix(" verify-feasibility"), 1),
                encoding="utf-8",
                newline="\n",
            )
            self.refresh_manifest_record(root, manifest_path, "Makefile")
            failures = verify_release.verify(root, manifest_path)
            self.assertIn(
                "make verify must include all legacy and experimental checks", failures
            )

    def test_missing_sustained_verify_dependency_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = self.copy_release(root)
            makefile = root / "Makefile"
            text = makefile.read_text(encoding="utf-8")
            dependency = " verify-sustained"
            verify_line = next(
                line for line in text.splitlines() if line.startswith("verify:")
            )
            self.assertIn(dependency, verify_line)
            makefile.write_text(
                text.replace(verify_line, verify_line.replace(dependency, ""), 1),
                encoding="utf-8",
                newline="\n",
            )
            self.refresh_manifest_record(root, manifest_path, "Makefile")
            failures = verify_release.verify(root, manifest_path)
            self.assertIn(
                "make verify must include all legacy and experimental checks", failures
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
