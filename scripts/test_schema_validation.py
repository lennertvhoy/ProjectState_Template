#!/usr/bin/env python3
"""Regression tests for StateSpec schema-backed validation."""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts" / "statedd_validate_schema.py"
INIT_SCRIPT = ROOT / "scripts" / "init_template.py"


def run(args: list[str], *, cwd: Path = ROOT, expect_success: bool) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        [sys.executable, *args],
        cwd=cwd,
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


def run_init(args: list[str]) -> subprocess.CompletedProcess[str]:
    return run([str(INIT_SCRIPT), *args], expect_success=True)


def assert_output_contains(completed: subprocess.CompletedProcess[str], expected: str) -> None:
    output = f"{completed.stdout}\n{completed.stderr}"
    if expected not in output:
        raise AssertionError(f"Expected output to contain {expected!r}, got:\n{output}")


def test_root_schema_validation_passes() -> None:
    run([str(VALIDATOR)], expect_success=True)


def test_invalid_project_state_fails_with_actionable_message() -> None:
    completed = run(
        [
            str(VALIDATOR),
            "--file",
            str(ROOT / "fixtures" / "schema_validation" / "invalid_project_state" / "PROJECT_STATE.yaml"),
            "--schema",
            str(ROOT / "schemas" / "project_state.schema.json"),
        ],
        expect_success=False,
    )
    assert_output_contains(completed, "template_repository")
    assert_output_contains(completed, "template-maintenance")


def test_invalid_evidence_readme_fails_contract() -> None:
    completed = run(
        [
            str(VALIDATOR),
            "--file",
            str(ROOT / "fixtures" / "schema_validation" / "invalid_evidence_readme" / "README.md"),
            "--schema",
            str(ROOT / "schemas" / "evidence_readme_contract.json"),
        ],
        expect_success=False,
    )
    assert_output_contains(completed, "missing required heading")


def test_runtime_not_applicable_fixture_passes() -> None:
    run(
        [
            str(VALIDATOR),
            "--file",
            str(ROOT / "fixtures" / "schema_validation" / "runtime-not-applicable" / "runtime_identity.json"),
            "--schema",
            str(ROOT / "schemas" / "runtime_identity.schema.json"),
        ],
        expect_success=True,
    )


def test_runtime_required_unreachable_fixture_fails() -> None:
    completed = run(
        [
            str(VALIDATOR),
            "--file",
            str(ROOT / "fixtures" / "schema_validation" / "runtime-required-unreachable" / "runtime_identity.json"),
            "--schema",
            str(ROOT / "schemas" / "runtime_identity.schema.json"),
        ],
        expect_success=False,
    )
    assert_output_contains(completed, "runtime.required is true")
    assert_output_contains(completed, "endpoint_reachable must be true")


def test_duplicate_root_yaml_key_fails() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "duplicate-root"
        run_init(["new", "--name", "Duplicate Root", "--target", str(target), "--profile", "minimal"])
        dna = target / "PROJECT_DNA.yaml"
        dna.write_text(dna.read_text(encoding="utf-8") + "\ninvariants:\n  - duplicate\n", encoding="utf-8")
        completed = run(
            [str(target / "scripts" / "statedd_validate_schema.py"), str(target)],
            cwd=target,
            expect_success=False,
        )
        assert_output_contains(completed, "duplicate mapping key 'invariants'")


def test_duplicate_nested_yaml_key_fails() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "duplicate-nested"
        run_init(["new", "--name", "Duplicate Nested", "--target", str(target), "--profile", "minimal"])
        state = target / "PROJECT_STATE.yaml"
        text = state.read_text(encoding="utf-8")
        text = text.replace(
            "  repo_role: downstream_project\n",
            "  repo_role: downstream_project\n  repo_role: downstream_project\n",
            1,
        )
        state.write_text(text, encoding="utf-8")
        completed = run(
            [str(target / "scripts" / "statedd_validate_schema.py"), str(target)],
            cwd=target,
            expect_success=False,
        )
        assert_output_contains(completed, "duplicate mapping key 'repo_role'")


def assert_schema_assets_exist(root: Path) -> None:
    required = [
        root / "schemas" / "project_state.schema.json",
        root / "schemas" / "project_dna.schema.json",
        root / "schemas" / "project_adapter.schema.json",
        root / "schemas" / "statedd_assets.schema.json",
        root / "schemas" / "runtime_identity.schema.json",
        root / "schemas" / "evidence_readme_contract.json",
        root / "schemas" / "final_handoff_contract.json",
        root / "schemas" / "git_safety_report.schema.json",
        root / "scripts" / "statedd_git_safety_check.py",
        root / "scripts" / "statedd_validate_schema.py",
    ]
    missing = [str(path.relative_to(root)) for path in required if not path.exists()]
    if missing:
        raise AssertionError(f"Missing schema validation assets: {missing}")


def test_generated_new_repo_includes_schema_validation_assets_and_passes() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "generated-new"
        run_init(["new", "--name", "Schema Demo", "--target", str(target)])
        assert_schema_assets_exist(target)
        run([str(target / "scripts" / "statedd_validate_schema.py"), str(target)], cwd=target, expect_success=True)


def test_adopted_repo_includes_schema_validation_assets_and_passes() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "adopted"
        target.mkdir()
        (target / "README.md").write_text("# Existing Project\n", encoding="utf-8")
        run_init(["adopt", "--name", "Schema Adopted", "--target", str(target)])
        assert_schema_assets_exist(target)
        run([str(target / "scripts" / "statedd_validate_schema.py"), str(target)], cwd=target, expect_success=True)


def main() -> int:
    tests = [
        test_root_schema_validation_passes,
        test_invalid_project_state_fails_with_actionable_message,
        test_invalid_evidence_readme_fails_contract,
        test_runtime_not_applicable_fixture_passes,
        test_runtime_required_unreachable_fixture_fails,
        test_duplicate_root_yaml_key_fails,
        test_duplicate_nested_yaml_key_fails,
        test_generated_new_repo_includes_schema_validation_assets_and_passes,
        test_adopted_repo_includes_schema_validation_assets_and_passes,
    ]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
