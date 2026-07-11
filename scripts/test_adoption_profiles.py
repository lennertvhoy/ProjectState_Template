#!/usr/bin/env python3
"""Regression tests for adoption profiles and the bootstrap wizard.

Stays stdlib-only.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    from statedd_validate_schema import parse_yaml_text
except ModuleNotFoundError:  # pragma: no cover - pytest package import path
    from scripts.statedd_validate_schema import parse_yaml_text


ROOT = Path(__file__).resolve().parents[1]
INIT_SCRIPT = ROOT / "scripts" / "init_template.py"
WIZARD_SCRIPT = ROOT / "scripts" / "statedd_bootstrap_wizard.py"
STARTUP_FILES = (
    "AGENTS.md",
    "STATUS.md",
    "PROJECT_STATE.yaml",
    "PROJECT_DNA.yaml",
    "NEXT_ACTIONS.md",
)


def run_init(args: list[str], *, expect_success: bool) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        [sys.executable, str(INIT_SCRIPT), *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if expect_success and completed.returncode != 0:
        raise AssertionError(
            f"Expected success for {args}, got {completed.returncode}\n"
            f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )
    if not expect_success and completed.returncode == 0:
        raise AssertionError(f"Expected failure for {args}, got success\nstdout:\n{completed.stdout}")
    return completed


def run_wizard(args: list[str], *, expect_success: bool) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        [sys.executable, str(WIZARD_SCRIPT), *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if expect_success and completed.returncode != 0:
        raise AssertionError(
            f"Expected success for {args}, got {completed.returncode}\n"
            f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )
    if not expect_success and completed.returncode == 0:
        raise AssertionError(f"Expected failure for {args}, got success\nstdout:\n{completed.stdout}")
    return completed


def validate_repo(repo: Path) -> None:
    manifest = json.loads((repo / "STATEDD_ASSETS.json").read_text(encoding="utf-8"))
    required_gate_level = manifest.get("required_gate_level", 1)
    for command in (
        [sys.executable, str(repo / "scripts" / "statedd_validate_schema.py"), str(repo)],
        [sys.executable, str(repo / "scripts" / "check_state_docs.py"), str(repo)],
        [
            sys.executable,
            str(repo / "scripts" / "statedd_quality_gate.py"),
            "--root",
            str(repo),
            "--gate-level",
            str(required_gate_level),
            "--conformance",
        ],
    ):
        completed = subprocess.run(command, cwd=repo, capture_output=True, text=True, check=False)
        if completed.returncode != 0:
            raise AssertionError(
                f"Validation failed for {repo}\ncommand: {command}\n"
                f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
            )


def test_new_profile_minimal() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "minimal"
        run_init(["new", "--name", "Minimal Demo", "--target", str(target), "--profile", "minimal"], expect_success=True)
        validate_repo(target)
        if (target / "fixtures").exists():
            raise AssertionError("minimal profile should remove fixtures/")
        if (target / "docs" / "BOOTSTRAP_QUALITY.md").exists():
            raise AssertionError("minimal profile should remove docs/BOOTSTRAP_QUALITY.md")
        if (target / "docs" / "WORKFLOW_FOR_BEGINNERS.md").exists():
            raise AssertionError("minimal profile should remove docs/WORKFLOW_FOR_BEGINNERS.md")
        state = (target / "PROJECT_STATE.yaml").read_text(encoding="utf-8")
        if "profile: minimal" not in state:
            raise AssertionError("PROJECT_STATE.yaml should record profile minimal")


def test_new_profile_solo() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "solo"
        run_init(["new", "--name", "Solo Demo", "--target", str(target), "--profile", "solo"], expect_success=True)
        validate_repo(target)
        state = (target / "PROJECT_STATE.yaml").read_text(encoding="utf-8")
        if "profile: solo" not in state:
            raise AssertionError("PROJECT_STATE.yaml should record profile solo")


def test_new_profile_team() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "team"
        run_init(["new", "--name", "Team Demo", "--target", str(target), "--profile", "team"], expect_success=True)
        validate_repo(target)
        agents = (target / "AGENTS.md").read_text(encoding="utf-8")
        if "`team`:" not in agents:
            raise AssertionError("AGENTS.md should mention team profile")


def test_new_profile_regulated() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "regulated"
        run_init(["new", "--name", "Regulated Demo", "--target", str(target), "--profile", "regulated"], expect_success=True)
        validate_repo(target)
        agents = (target / "AGENTS.md").read_text(encoding="utf-8")
        if "`regulated`:" not in agents:
            raise AssertionError("AGENTS.md should mention regulated profile")
        if "requires runtime identity" not in agents:
            raise AssertionError("AGENTS.md should emphasize runtime proof for regulated")


def test_legacy_minimal_flag_maps_to_profile() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "legacy"
        run_init(["--name", "Legacy Minimal", "--target", str(target), "--minimal"], expect_success=True)
        validate_repo(target)
        if (target / "fixtures").exists():
            raise AssertionError("legacy --minimal should remove fixtures/")


def test_profile_footprints_are_bounded_and_minimal_is_smallest() -> None:
    budget = parse_yaml_text((ROOT / "EFFICIENCY_BUDGET.yaml").read_text(encoding="utf-8"))
    profile_budgets = budget["context_budgets"]["profiles"]
    limits = {
        profile: (limits["max_footprint_files"], limits["max_footprint_bytes"])
        for profile, limits in profile_budgets.items()
        if profile in {"minimal", "solo", "team", "regulated"}
    }
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        measured: dict[str, tuple[int, int, int]] = {}
        for index, (profile, (max_files, max_bytes)) in enumerate(limits.items()):
            # Keep project names and target-path lengths identical so the
            # profile comparison measures policy payload, not fixture wording.
            target = root / f"p{index}"
            run_init(
                ["new", "--name", "Profile footprint", "--target", str(target), "--profile", profile],
                expect_success=True,
            )
            files = [path for path in target.rglob("*") if path.is_file() and ".git" not in path.parts]
            file_count = len(files)
            byte_count = sum(path.stat().st_size for path in files)
            startup_bytes = sum((target / path).stat().st_size for path in STARTUP_FILES)
            measured[profile] = (file_count, byte_count, startup_bytes)
            if file_count > max_files or byte_count > max_bytes:
                raise AssertionError(
                    f"{profile} footprint exceeds budget: files={file_count}/{max_files}, "
                    f"bytes={byte_count}/{max_bytes}"
                )

        minimal_files, minimal_bytes, minimal_startup_bytes = measured["minimal"]
        solo_files, solo_bytes, _ = measured["solo"]
        if minimal_files >= solo_files or minimal_bytes >= solo_bytes:
            raise AssertionError(f"minimal is not the smallest usable profile: {measured}")
        other_startup_bytes = [values[2] for profile, values in measured.items() if profile != "minimal"]
        if minimal_startup_bytes >= min(other_startup_bytes):
            raise AssertionError(f"minimal startup context is not the smallest profile payload: {measured}")


def test_adopt_with_profile_preserves_readme() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "adopted"
        target.mkdir()
        (target / "README.md").write_text("# Existing Project\n", encoding="utf-8")
        run_init(["adopt", "--name", "Adopted Demo", "--target", str(target), "--profile", "team"], expect_success=True)
        validate_repo(target)
        if (target / "README.md").read_text(encoding="utf-8") != "# Existing Project\n":
            raise AssertionError("adopt --profile should preserve existing README")
        state = (target / "PROJECT_STATE.yaml").read_text(encoding="utf-8")
        if "profile: team" not in state:
            raise AssertionError("adopt should record profile team")


def test_wizard_answers_generates_files() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "wizard"
        answers = Path(tmp) / "answers.json"
        answers.write_text(
            json.dumps(
                {
                    "project_name": "Wizard Demo",
                    "repo_role": "downstream_project",
                    "profile": "solo",
                    "first_milestone": "Build first feature",
                    "runtime_required": "false",
                    "evidence_strictness": "standard",
                }
            ),
            encoding="utf-8",
        )
        run_wizard(["--target", str(target), "--answers", str(answers)], expect_success=True)
        if not (target / "AGENTS.md").exists():
            raise AssertionError("Wizard did not generate AGENTS.md")
        if not (target / "docs" / "bootstrap_wizard_notes.md").exists():
            raise AssertionError("Wizard did not write bootstrap notes")


def test_wizard_dry_run_writes_nothing() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "wizard"
        answers = Path(tmp) / "answers.json"
        answers.write_text(
            json.dumps(
                {
                    "project_name": "Dry Run Demo",
                    "profile": "minimal",
                }
            ),
            encoding="utf-8",
        )
        run_wizard(["--target", str(target), "--answers", str(answers), "--dry-run"], expect_success=True)
        if target.exists() and any(target.iterdir()):
            raise AssertionError("Dry run wrote files unexpectedly")


def main() -> int:
    tests = [
        test_new_profile_minimal,
        test_new_profile_solo,
        test_new_profile_team,
        test_new_profile_regulated,
        test_legacy_minimal_flag_maps_to_profile,
        test_profile_footprints_are_bounded_and_minimal_is_smallest,
        test_adopt_with_profile_preserves_readme,
        test_wizard_answers_generates_files,
        test_wizard_dry_run_writes_nothing,
    ]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
