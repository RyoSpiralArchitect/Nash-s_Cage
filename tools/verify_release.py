#!/usr/bin/env python3
"""Fail-closed verification for the committed Nash's Cage release tree."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Mapping


MANIFEST_FORMAT = "nashs-cage-release-manifest/v1"
RELEASE = "v0.2.0"
RELEASE_STATUS = "recovery"
RELEASE_DATE = "2026-08-07"
CLAIM_LEVEL = "F0"
CLAIM_BOUNDARY = (
    "Structural toy only; not calibrated, predictive, empirically validating, "
    "or a policy recommendation."
)
TRUST_MODEL = (
    "manifest-checks-internal-consistency; reviewed-git-commit-is-external-anchor"
)
REFERENCE_COMMAND = {
    "arms": [
        "weak_coupling",
        "nominal_trigger",
        "robust_reserve",
        "full_rvcim",
    ],
    "episodes": 64,
    "overrides": [],
    "seed": 7,
}
REFERENCE_INPUTS = {
    "config": "../../simulation/configs/minimal.json",
    "source": "../../simulation/rvcim_sim.py",
}
REQUIRED_FILES = frozenset(
    {
        ".gitattributes",
        ".github/workflows/verify.yml",
        "Makefile",
        "rvcim",
        "rvcim.cmd",
        "paper/nashs_cage_rvcim_v0_1.tex",
        "paper/nashs_cage_rvcim_v0_1.pdf",
        "paper/nashs_cage_rvcim_v0_2.tex",
        "paper/nashs_cage_rvcim_v0_2.pdf",
        "paper/references.bib",
        "simulation/__init__.py",
        "simulation/__main__.py",
        "simulation/rvcim_sim.py",
        "simulation/feasibility.py",
        "simulation/sustained.py",
        "simulation/configs/minimal.json",
        "simulation/configs/feasibility_v03.json",
        "simulation/configs/feasibility_stress_plan.json",
        "simulation/configs/sustained_v04.json",
        "simulation/configs/sustained_stress_plan.json",
        "simulation/tests/test_rvcim_sim.py",
        "simulation/tests/test_feasibility.py",
        "simulation/tests/test_sustained.py",
        "docs/FEASIBILITY_V03_CONTRACT.md",
        "docs/SUSTAINED_V04_CONTRACT.md",
        "artifacts/reference_run/summary.csv",
        "artifacts/reference_run/episodes.csv",
        "artifacts/reference_run/trace.csv",
        "artifacts/reference_run/comparison.md",
        "artifacts/reference_run/resolved_config.json",
        "artifacts/reference_run/receipt.json",
        "artifacts/feasibility_v03/episodes.csv",
        "artifacts/feasibility_v03/summary.json",
        "artifacts/feasibility_v03/trace.csv",
        "artifacts/feasibility_v03/resolved_plan.json",
        "artifacts/feasibility_v03/receipt.json",
        "artifacts/feasibility_v03/comparison.md",
        "artifacts/sustained_v04/episodes.csv",
        "artifacts/sustained_v04/summary.json",
        "artifacts/sustained_v04/trace.csv",
        "artifacts/sustained_v04/resolved_plan.json",
        "artifacts/sustained_v04/receipt.json",
        "artifacts/sustained_v04/comparison.md",
        "tools/verify_release.py",
        "tools/verify_reference_replay.py",
        "tools/run_feasibility.py",
        "tools/run_sustained.py",
        "tools/tests/test_verify_release.py",
        "tools/tests/test_feasibility_runner.py",
        "tools/tests/test_sustained_runner.py",
    }
)
EXPECTED_ROLES = {
    ".gitattributes": "cross-platform LF checkout policy",
    ".github/workflows/verify.yml": "read-only cross-platform verification workflow",
    "Makefile": "verification and experiment orchestration",
    "rvcim": "POSIX no-install launcher",
    "rvcim.cmd": "Windows no-install launcher",
    "paper/nashs_cage_rvcim_v0_1.tex": "preserved manuscript v0.1 TeX",
    "paper/nashs_cage_rvcim_v0_1.pdf": "preserved manuscript v0.1 PDF",
    "paper/nashs_cage_rvcim_v0_2.tex": "regenerated manuscript v0.2 TeX",
    "paper/nashs_cage_rvcim_v0_2.pdf": "regenerated manuscript v0.2 PDF",
    "paper/references.bib": "bibliography for manuscript sources",
    "simulation/__init__.py": "simulation package API entrypoint",
    "simulation/__main__.py": "python -m simulation CLI entrypoint",
    "simulation/rvcim_sim.py": "zero-dependency executable reference source",
    "simulation/feasibility.py": "experimental v0.3 structural feasibility engine",
    "simulation/sustained.py": "experimental v0.4 sustained-response engine",
    "simulation/configs/minimal.json": "declared normalized reference configuration",
    "simulation/configs/feasibility_v03.json": "experimental v0.3 feasibility configuration",
    "simulation/configs/feasibility_stress_plan.json": "fixed experimental feasibility stress plan",
    "simulation/configs/sustained_v04.json": "experimental v0.4 sustained-response configuration",
    "simulation/configs/sustained_stress_plan.json": "fixed experimental sustained-response stress plan",
    "simulation/tests/test_rvcim_sim.py": "deterministic simulator contract tests",
    "simulation/tests/test_feasibility.py": "experimental feasibility engine contract tests",
    "simulation/tests/test_sustained.py": "experimental sustained-response engine contract tests",
    "docs/FEASIBILITY_V03_CONTRACT.md": "experimental v0.3 feasibility contract and claim boundary",
    "docs/SUSTAINED_V04_CONTRACT.md": "experimental v0.4 sustained-response contract and claim boundary",
    "artifacts/reference_run/summary.csv": "arm-level reference summary",
    "artifacts/reference_run/episodes.csv": "episode-level reference outcomes",
    "artifacts/reference_run/trace.csv": "step-level reference trace",
    "artifacts/reference_run/comparison.md": "human-readable reference comparison",
    "artifacts/reference_run/resolved_config.json": "resolved reference configuration",
    "artifacts/reference_run/receipt.json": "reference artifact verification receipt",
    "artifacts/feasibility_v03/episodes.csv": "experimental feasibility episode outcomes",
    "artifacts/feasibility_v03/summary.json": "experimental feasibility aggregate summary",
    "artifacts/feasibility_v03/trace.csv": "experimental feasibility step trace",
    "artifacts/feasibility_v03/resolved_plan.json": "resolved experimental feasibility stress plan",
    "artifacts/feasibility_v03/receipt.json": "experimental feasibility verification receipt",
    "artifacts/feasibility_v03/comparison.md": "human-readable experimental feasibility comparison",
    "artifacts/sustained_v04/episodes.csv": "experimental sustained-response episode outcomes",
    "artifacts/sustained_v04/summary.json": "experimental sustained-response aggregate summary",
    "artifacts/sustained_v04/trace.csv": "experimental sustained-response step trace",
    "artifacts/sustained_v04/resolved_plan.json": "resolved experimental sustained-response stress plan",
    "artifacts/sustained_v04/receipt.json": "experimental sustained-response verification receipt",
    "artifacts/sustained_v04/comparison.md": "human-readable experimental sustained-response comparison",
    "tools/verify_release.py": "fail-closed release-tree verifier",
    "tools/verify_reference_replay.py": "deterministic reference replay verifier",
    "tools/run_feasibility.py": "experimental feasibility runner and replay verifier",
    "tools/run_sustained.py": "experimental sustained-response runner and replay verifier",
    "tools/tests/test_verify_release.py": "release-verifier contract tests",
    "tools/tests/test_feasibility_runner.py": "experimental feasibility runner contract tests",
    "tools/tests/test_sustained_runner.py": "experimental sustained-response runner contract tests",
}
EXPECTED_FILE_PROVENANCE = {
    "paper/nashs_cage_rvcim_v0_1.tex": "operator-attested-preserved-upload",
    "paper/nashs_cage_rvcim_v0_1.pdf": "operator-attested-preserved-upload",
    "paper/nashs_cage_rvcim_v0_2.tex": "operator-attested-regeneration-from-v0.1",
    "paper/nashs_cage_rvcim_v0_2.pdf": "operator-attested-regeneration-from-v0.1",
}
POWER_ROLES = {
    "tools/run_power_accounting.py": "bounded empirical fuel-carbon extractor and replay runner",
    "tools/tests/test_power_accounting.py": "fuel-carbon input and replay contract tests",
    "data/power_jp_fy2024/observations.json": "frozen official fuel-carbon factual extract",
    "data/power_jp_fy2024/README.md": "fuel-carbon source attribution and extraction contract",
    "docs/EMPIRICAL_POWER_INPUT_CONTRACT.ja.md": "initial empirical power-input design contract",
    "docs/empirical_power_case.jp_fy2024.draft.json": "initial empirical power-input draft with unknown gates",
    "docs/POWER_ACCOUNTING_RESULTS.ja.md": "empirical accounting results and oil resource boundary",
    "artifacts/power_jp_fy2024/rows.csv": "all empirical fuel-carbon row outcomes including rejections",
    "artifacts/power_jp_fy2024/summary.json": "empirical fuel-carbon summary and unresolved gates",
    "artifacts/power_jp_fy2024/comparison.md": "human-readable empirical fuel-carbon comparison",
    "artifacts/power_jp_fy2024/receipt.json": "deterministic empirical fuel-carbon replay receipt",
}
REQUIRED_FILES = REQUIRED_FILES | frozenset(POWER_ROLES)
EXPECTED_ROLES.update(POWER_ROLES)
PDF_FILES = frozenset(relative for relative in REQUIRED_FILES if relative.endswith(".pdf"))
TEXT_FILES = REQUIRED_FILES - PDF_FILES
EXECUTABLE_GLOBS = (
    "simulation/**/*.py",
    "tools/**/*.py",
    ".github/workflows/*.yml",
    ".github/workflows/*.yaml",
)
OFFICIAL_ACTION_PATTERN = re.compile(
    r"^\s*-\s+uses:\s+(actions/[A-Za-z0-9_.-]+)@([^\s#]+)",
    re.MULTILINE,
)
TEST_MODULES = (
    "simulation.tests.test_rvcim_sim",
    "simulation.tests.test_feasibility",
    "simulation.tests.test_sustained",
    "tools.tests.test_verify_release",
    "tools.tests.test_feasibility_runner",
    "tools.tests.test_sustained_runner",
    "tools.tests.test_power_accounting",
)
COMPILE_FILES = tuple(
    sorted(relative for relative in REQUIRED_FILES if relative.endswith(".py"))
)
WINDOWS_NATIVE_COMMAND = re.compile(
    r"^(?:run:\s*)?(?:python(?:[0-9.]+)?|\.\\rvcim\.cmd)(?:\s|$)",
    re.IGNORECASE,
)
WINDOWS_EXIT_CHECK = "if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }"
WINDOWS_REQUIRED_NATIVE_COMMANDS = (
    ".\\rvcim.cmd explain",
    "python tools/verify_release.py --root . --manifest RELEASE_MANIFEST.json",
    (
        "python -m py_compile simulation/__init__.py simulation/__main__.py "
        "simulation/rvcim_sim.py simulation/feasibility.py simulation/sustained.py"
    ),
    (
        "python -m py_compile tools/verify_release.py "
        "tools/verify_reference_replay.py tools/run_feasibility.py "
        "tools/run_sustained.py tools/run_power_accounting.py"
    ),
    (
        "python -m py_compile simulation/tests/test_rvcim_sim.py "
        "simulation/tests/test_feasibility.py simulation/tests/test_sustained.py "
        "tools/tests/test_verify_release.py tools/tests/test_feasibility_runner.py "
        "tools/tests/test_sustained_runner.py tools/tests/test_power_accounting.py"
    ),
    "python -m unittest -v simulation.tests.test_rvcim_sim",
    "python -m unittest -v simulation.tests.test_feasibility",
    "python -m unittest -v simulation.tests.test_sustained",
    "python -m unittest -v tools.tests.test_verify_release",
    "python -m unittest -v tools.tests.test_feasibility_runner",
    "python -m unittest -v tools.tests.test_sustained_runner",
    "python -m unittest -v tools.tests.test_power_accounting",
    (
        ".\\rvcim.cmd smoke --config simulation\\configs\\minimal.json "
        "--episodes 4 --seed 101 --out .tmp\\smoke-windows"
    ),
    ".\\rvcim.cmd verify --receipt .tmp\\smoke-windows\\receipt.json",
    "python -m simulation verify --receipt artifacts\\reference_run\\receipt.json",
    (
        "python tools/verify_reference_replay.py --root . "
        "--reference-dir artifacts\\reference_run"
    ),
    (
        "python tools/run_feasibility.py verify "
        "--out artifacts/feasibility_v03 --replay"
    ),
    (
        "python tools/run_sustained.py verify "
        "--out artifacts/sustained_v04 --replay"
    ),
    (
        "python tools/run_power_accounting.py verify "
        "--out artifacts/power_jp_fy2024 --replay"
    ),
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> Mapping[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise ValueError("JSON root must be an object")
    return value


def has_symlink_component(root: Path, relative: str | Path) -> bool:
    """Return true when a path at or below root traverses a symlink."""

    current = root
    for part in Path(relative).parts:
        current = current / part
        if current.is_symlink():
            return True
    return False


def read_required_text(root: Path, relative: str, failures: list[str]) -> str | None:
    path = root / relative
    if has_symlink_component(root, relative):
        return None
    try:
        payload = path.read_bytes()
        text = payload.decode("utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        failures.append(f"{relative}: cannot read UTF-8 text: {exc}")
        return None
    if b"\r" in payload:
        failures.append(f"{relative}: text checkout must use LF without CR bytes")
    return text


def make_recipe(makefile: str, target: str) -> str | None:
    lines = makefile.splitlines()
    header = f"{target}:"
    for index, line in enumerate(lines):
        if line == header or line.startswith(header + " "):
            body: list[str] = []
            for following in lines[index + 1 :]:
                if following.startswith(("\t", " ")) or not following:
                    body.append(following)
                    continue
                break
            return "\n".join(body)
    return None


def workflow_job(workflow: str, job: str) -> str | None:
    """Read a job from the deliberately fixed, two-space workflow layout."""

    lines = workflow.splitlines()
    for index, line in enumerate(lines):
        if line != f"  {job}:":
            continue
        body: list[str] = []
        for following in lines[index + 1 :]:
            if following.strip() and not following.startswith("    "):
                break
            body.append(following)
        return "\n".join(body)
    return None


def verify_windows_workflow(workflow: str) -> list[str]:
    """Require explicit native exit propagation in the locked Windows job."""

    windows = workflow_job(workflow, "windows")
    if windows is None:
        return ["verification workflow must define the windows job"]
    failures: list[str] = []
    if "runs-on: windows-latest" not in windows:
        failures.append("windows verification job must run on windows-latest")
    if "shell: pwsh" not in windows:
        failures.append("windows verification job must explicitly select pwsh")
    statements = [
        line.strip()
        for line in windows.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    native_commands = []
    for index, statement in enumerate(statements):
        if WINDOWS_NATIVE_COMMAND.match(statement) is None:
            continue
        native_commands.append(statement)
        if (
            index + 1 >= len(statements)
            or statements[index + 1] != WINDOWS_EXIT_CHECK
        ):
            failures.append(
                "Windows native command must immediately check LASTEXITCODE: "
                + statement
            )
    if tuple(native_commands) != WINDOWS_REQUIRED_NATIVE_COMMANDS:
        missing = [
            command
            for command in WINDOWS_REQUIRED_NATIVE_COMMANDS
            if command not in native_commands
        ]
        unexpected = [
            command
            for command in native_commands
            if command not in WINDOWS_REQUIRED_NATIVE_COMMANDS
        ]
        if missing:
            failures.append(
                "Windows verification is missing required native commands: "
                + "; ".join(missing)
            )
        if unexpected:
            failures.append(
                "Windows verification has unexpected native commands: "
                + "; ".join(unexpected)
            )
        if not missing and not unexpected:
            failures.append("Windows native commands must use the locked order")
    for module in TEST_MODULES:
        if f"python -m unittest -v {module}" not in native_commands:
            failures.append(f"Windows verification must explicitly run {module}")
    compiled = set()
    for command in native_commands:
        if command.startswith("python -m py_compile "):
            compiled.update(command.split()[3:])
    for relative in COMPILE_FILES:
        if relative not in compiled:
            failures.append(f"Windows verification must explicitly compile {relative}")
    feasibility_verify = (
        "python tools/run_feasibility.py verify "
        "--out artifacts/feasibility_v03 --replay"
    )
    if feasibility_verify not in native_commands:
        failures.append("Windows verification must replay the experimental feasibility fixture")
    sustained_verify = (
        "python tools/run_sustained.py verify "
        "--out artifacts/sustained_v04 --replay"
    )
    if sustained_verify not in native_commands:
        failures.append("Windows verification must replay the experimental sustained fixture")
    return failures


def verify_executable_surface(root: Path) -> list[str]:
    """Reject executable files that are outside the declared release closure."""

    observed: set[str] = set()
    for pattern in EXECUTABLE_GLOBS:
        for path in root.glob(pattern):
            if path.is_file() or path.is_symlink():
                observed.add(path.relative_to(root).as_posix())
    unexpected = sorted(observed - REQUIRED_FILES)
    if unexpected:
        return [
            "unmanifested executable files: " + ", ".join(unexpected)
        ]
    return []


def verify_operational_semantics(root: Path) -> list[str]:
    """Check high-risk operational invariants in addition to manifest hashes."""

    failures: list[str] = []
    texts = {
        relative: read_required_text(root, relative, failures)
        for relative in sorted(TEXT_FILES)
    }

    attributes = texts.get(".gitattributes")
    if attributes is not None:
        rules = {
            line.strip()
            for line in attributes.splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        }
        if "* text=auto eol=lf" not in rules:
            failures.append(".gitattributes: must pin automatic text checkout to LF")
        if "*.pdf -text" not in rules:
            failures.append(".gitattributes: PDFs must be declared binary")
        if "eol=crlf" in attributes.lower():
            failures.append(".gitattributes: CRLF checkout overrides are not allowed")

    workflow = texts.get(".github/workflows/verify.yml")
    if workflow is not None:
        if "permissions:\n  contents: read" not in workflow:
            failures.append("verification workflow must declare contents: read")
        if "runs-on: windows-latest" not in workflow:
            failures.append("verification workflow must cover windows-latest")
        if "./rvcim explain" not in workflow:
            failures.append("verification workflow must exercise the POSIX launcher")
        if ".\\rvcim.cmd explain" not in workflow:
            failures.append("verification workflow must exercise the Windows launcher")
        if workflow.count("timeout-minutes:") < workflow.count("runs-on:"):
            failures.append("every verification workflow job must declare a timeout")
        lowered = workflow.lower()
        for forbidden in (
            "contents: write",
            "permissions: write-all",
            "git push",
            "pull_request_target:",
            "schedule:",
        ):
            if forbidden in lowered:
                failures.append(f"verification workflow contains forbidden token: {forbidden}")
        actions = OFFICIAL_ACTION_PATTERN.findall(workflow)
        action_names = {name for name, _ in actions}
        if not {"actions/checkout", "actions/setup-python"} <= action_names:
            failures.append("verification workflow must use checkout and setup-python")
        for name, revision in actions:
            if not re.fullmatch(r"[0-9a-f]{40}", revision):
                failures.append(f"verification workflow must SHA-pin {name}")
        checkout_count = sum(name == "actions/checkout" for name, _ in actions)
        if workflow.count("persist-credentials: false") < checkout_count:
            failures.append("every checkout step must disable persisted credentials")
        if "unittest discover" in workflow:
            failures.append("verification workflow must not auto-discover tests")
        failures.extend(verify_windows_workflow(workflow))

    makefile = texts.get("Makefile")
    if makefile is not None:
        experiment = make_recipe(makefile, "experiment")
        if experiment is None:
            failures.append("Makefile must define experiment")
        else:
            if "--out .tmp/experiment" not in experiment:
                failures.append("make experiment must write to fixed .tmp/experiment")
            if "artifacts/reference_run" in experiment or "REFERENCE_DIR" in experiment:
                failures.append("make experiment must not write the committed fixture")
        smoke = make_recipe(makefile, "smoke")
        if smoke is None or "--out .tmp/smoke" not in smoke:
            failures.append("make smoke must write to fixed .tmp/smoke")
        elif "artifacts/reference_run" in smoke or "SMOKE_DIR" in smoke:
            failures.append("make smoke must not accept a tracked output destination")
        refresh = make_recipe(makefile, "refresh-reference")
        if refresh is None or "artifacts/reference_run" not in refresh:
            failures.append("Makefile must reserve fixture writes for refresh-reference")
        feasibility = make_recipe(makefile, "feasibility")
        if feasibility is None:
            failures.append("Makefile must define feasibility")
        else:
            expected = "$(PYTHON) tools/run_feasibility.py run --out .tmp/feasibility"
            if feasibility.strip() != expected:
                failures.append(
                    "make feasibility must create new-only output at fixed .tmp/feasibility"
                )
        feasibility_verify = make_recipe(makefile, "verify-feasibility")
        expected = (
            "$(PYTHON) tools/run_feasibility.py verify "
            "--out artifacts/feasibility_v03 --replay"
        )
        if feasibility_verify is None or feasibility_verify.strip() != expected:
            failures.append("make verify-feasibility must replay the experimental fixture")
        sustained = make_recipe(makefile, "sustained")
        if sustained is None:
            failures.append("Makefile must define sustained")
        else:
            expected = "$(PYTHON) tools/run_sustained.py run --out .tmp/sustained"
            if sustained.strip() != expected:
                failures.append(
                    "make sustained must create new-only output at fixed .tmp/sustained"
                )
        sustained_verify = make_recipe(makefile, "verify-sustained")
        expected = (
            "$(PYTHON) tools/run_sustained.py verify "
            "--out artifacts/sustained_v04 --replay"
        )
        if sustained_verify is None or sustained_verify.strip() != expected:
            failures.append("make verify-sustained must replay the experimental sustained fixture")
        power_run = make_recipe(makefile, "power-accounting")
        expected = "$(PYTHON) tools/run_power_accounting.py run --out .tmp/power-accounting"
        if power_run is None or power_run.strip() != expected:
            failures.append("make power-accounting must create new-only output at fixed .tmp/power-accounting")
        power_verify = make_recipe(makefile, "verify-power")
        expected = "$(PYTHON) tools/run_power_accounting.py verify --out artifacts/power_jp_fy2024 --replay"
        if power_verify is None or power_verify.strip() != expected:
            failures.append("make verify-power must replay the empirical accounting fixture")
        verify_headers = [
            line for line in makefile.splitlines() if line.startswith("verify:")
        ]
        required_dependencies = {
            "verify-release", "compile", "test", "smoke", "verify-artifact",
            "verify-reference-replay", "verify-feasibility", "verify-sustained",
            "verify-power",
        }
        if (
            len(verify_headers) != 1
            or not required_dependencies <= set(verify_headers[0].split()[1:])
        ):
            failures.append("make verify must include all legacy and experimental checks")
        compile_recipe = make_recipe(makefile, "compile")
        compiled = set()
        if compile_recipe is not None:
            for line in compile_recipe.splitlines():
                command = line.strip()
                if command.startswith("$(PYTHON) -m py_compile "):
                    compiled.update(command.split()[3:])
        for relative in COMPILE_FILES:
            if relative not in compiled:
                failures.append(f"make compile must explicitly compile {relative}")
        tests = make_recipe(makefile, "test")
        if tests is None:
            failures.append("Makefile must define test")
        else:
            for module in TEST_MODULES:
                if f"-m unittest -v {module}" not in tests:
                    failures.append(f"make test must explicitly run {module}")
            if "discover" in tests:
                failures.append("make test must not auto-discover unmanifested tests")

    posix_launcher = texts.get("rvcim")
    if posix_launcher is not None:
        if not posix_launcher.startswith("#!/usr/bin/env sh\nset -eu\n"):
            failures.append("rvcim: launcher must use fail-fast POSIX sh")
        if 'exec "${PYTHON:-python3}" -m simulation "$@"' not in posix_launcher:
            failures.append("rvcim: launcher must delegate to python -m simulation")

    windows_launcher = texts.get("rvcim.cmd")
    if windows_launcher is not None and "python -m simulation %*" not in windows_launcher:
        failures.append("rvcim.cmd: launcher must delegate to python -m simulation")

    module_entrypoint = texts.get("simulation/__main__.py")
    if module_entrypoint is not None:
        if "from .rvcim_sim import main" not in module_entrypoint:
            failures.append("simulation/__main__.py must import the simulator main")
        if "raise SystemExit(main())" not in module_entrypoint:
            failures.append("simulation/__main__.py must propagate the CLI exit status")

    return failures


def verify(root: Path, manifest_path: Path) -> list[str]:
    failures: list[str] = []
    lexical_root = root.absolute()
    root = root.resolve()
    if manifest_path.is_absolute():
        manifest_absolute = manifest_path.absolute()
        manifest_relative: Path | None = None
        for candidate_root in (lexical_root, root):
            try:
                manifest_relative = manifest_absolute.relative_to(candidate_root)
                break
            except ValueError:
                continue
        if manifest_relative is None or ".." in manifest_relative.parts:
            return ["manifest path escapes repository root"]
    else:
        manifest_relative = manifest_path
        if ".." in manifest_relative.parts:
            return ["manifest path escapes repository root"]
    manifest_path = root / manifest_relative
    if has_symlink_component(root, manifest_relative):
        return ["manifest path must not contain symlinks"]
    try:
        manifest = load_json(manifest_path)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        return [f"cannot read manifest: {exc}"]

    if manifest.get("format") != MANIFEST_FORMAT:
        failures.append(
            f"unsupported format: {manifest.get('format')!r}; expected {MANIFEST_FORMAT!r}"
        )
    for field, expected in (
        ("release", RELEASE),
        ("release_status", RELEASE_STATUS),
        ("release_date", RELEASE_DATE),
        ("claim_level", CLAIM_LEVEL),
        ("claim_boundary", CLAIM_BOUNDARY),
    ):
        if manifest.get(field) != expected:
            failures.append(f"{field} must be {expected!r}")

    provenance = manifest.get("provenance")
    if not isinstance(provenance, Mapping):
        failures.append("provenance must be an object")
    else:
        if provenance.get("v0_1") != "operator-attested-preserved-upload":
            failures.append(
                "provenance.v0_1 must be operator-attested-preserved-upload"
            )
        if provenance.get("v0_2") != "operator-attested-regeneration-from-v0.1":
            failures.append(
                "provenance.v0_2 must be operator-attested-regeneration-from-v0.1"
            )
        if provenance.get("historical_v0_2_byte_identity") != "not-claimed":
            failures.append(
                "provenance.historical_v0_2_byte_identity must be not-claimed"
            )
        if provenance.get("trust_model") != TRUST_MODEL:
            failures.append(f"provenance.trust_model must be {TRUST_MODEL!r}")
        if provenance.get("v0_1_tex_history_anchor") != "present":
            failures.append("provenance.v0_1_tex_history_anchor must be present")
        if provenance.get("v0_1_pdf_history_anchor") != "unavailable":
            failures.append("provenance.v0_1_pdf_history_anchor must be unavailable")
        if not isinstance(provenance.get("note"), str) or not provenance.get(
            "note"
        ):
            failures.append("provenance.note must be a non-empty string")

    files = manifest.get("files")
    if not isinstance(files, Mapping):
        return failures + ["files must be an object"]

    recorded = set(files)
    missing_records = sorted(REQUIRED_FILES - recorded)
    extra_records = sorted(recorded - REQUIRED_FILES)
    if missing_records:
        failures.append("manifest missing required records: " + ", ".join(missing_records))
    if extra_records:
        failures.append("manifest has unexpected records: " + ", ".join(extra_records))

    for relative in sorted(REQUIRED_FILES & recorded):
        entry = files[relative]
        if not isinstance(entry, Mapping):
            failures.append(f"{relative}: record must be an object")
            continue
        if has_symlink_component(root, relative):
            failures.append(f"{relative}: path must not contain symlinks")
            continue
        target = root / relative
        resolved_target = target.resolve()
        try:
            resolved_target.relative_to(root)
        except ValueError:
            failures.append(f"{relative}: path escapes repository root")
            continue
        if not target.is_file():
            failures.append(f"{relative}: missing regular file")
            continue
        expected_bytes = entry.get("bytes")
        expected_sha = entry.get("sha256")
        if (
            isinstance(expected_bytes, bool)
            or not isinstance(expected_bytes, int)
            or expected_bytes < 0
        ):
            failures.append(f"{relative}: bytes must be a non-negative integer")
        if (
            not isinstance(expected_sha, str)
            or len(expected_sha) != 64
            or any(character not in "0123456789abcdef" for character in expected_sha)
        ):
            failures.append(f"{relative}: sha256 must be lowercase hexadecimal")
        expected_role = EXPECTED_ROLES[relative]
        if entry.get("role") != expected_role:
            failures.append(f"{relative}: role must be {expected_role!r}")
        actual_bytes = target.stat().st_size
        actual_sha = sha256_file(target)
        if expected_bytes != actual_bytes:
            failures.append(
                f"{relative}: size mismatch expected={expected_bytes} actual={actual_bytes}"
            )
        if expected_sha != actual_sha:
            failures.append(
                f"{relative}: hash mismatch expected={expected_sha} actual={actual_sha}"
            )

    for relative, expected in EXPECTED_FILE_PROVENANCE.items():
        entry = files.get(relative)
        if isinstance(entry, Mapping) and entry.get("provenance") != expected:
            failures.append(f"{relative}: provenance must be {expected}")

    receipt_relative = "artifacts/reference_run/receipt.json"
    receipt_path = root / receipt_relative
    receipt: Mapping[str, Any] | None = None
    if has_symlink_component(root, receipt_relative):
        failures.append("cannot inspect reference receipt through a symlink")
    else:
        try:
            receipt = load_json(receipt_path)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            failures.append(f"cannot inspect reference receipt: {exc}")
            receipt = None
    if receipt is not None:
        if receipt.get("receipt_version") != 2:
            failures.append("reference receipt_version must be 2")
        if receipt.get("model_version") != "0.2.0":
            failures.append("reference model_version must be 0.2.0")
        if receipt.get("schema_version") != 1:
            failures.append("reference schema_version must be 1")
        if receipt.get("claim_level") != CLAIM_LEVEL:
            failures.append("reference claim_level must be F0")
        if receipt.get("claim_boundary") != CLAIM_BOUNDARY:
            failures.append("reference claim_boundary does not match release")
        if receipt.get("command") != REFERENCE_COMMAND:
            failures.append("reference command does not match the release contract")
        if receipt.get("inputs") != REFERENCE_INPUTS:
            failures.append("reference inputs do not match the release contract")

    failures.extend(verify_executable_surface(root))
    failures.extend(verify_operational_semantics(root))

    return failures


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--manifest", type=Path, default=Path("RELEASE_MANIFEST.json"))
    return parser


def main() -> int:
    args = build_parser().parse_args()
    root = args.root.resolve()
    manifest = args.manifest
    if not manifest.is_absolute():
        manifest = root / manifest
    failures = verify(root, manifest)
    if failures:
        for failure in failures:
            print(f"release verification error: {failure}", file=sys.stderr)
        return 1
    print(
        "OK: verified internal consistency and operational semantics for "
        f"{len(REQUIRED_FILES)} committed release files; external provenance "
        "depends on the reviewed Git commit"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
