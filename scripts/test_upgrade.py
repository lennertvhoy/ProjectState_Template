#!/usr/bin/env python3
"""Regression tests for statedd_upgrade.py.

Stays stdlib-only.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
UPGRADE_SCRIPT = ROOT / "scripts" / "statedd_upgrade.py"
INIT_SCRIPT = ROOT / "scripts" / "init_template.py"


def run_upgrade(args: list[str], *, expect_success: bool) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        [sys.executable, str(UPGRADE_SCRIPT), *args],
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
        raise AssertionError(
            f"Expected failure for {args}, got success\nstdout:\n{completed.stdout}"
        )
    return completed


def run_init(args: list[str]) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        [sys.executable, str(INIT_SCRIPT), *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise AssertionError(
            f"init failed: {completed.returncode}\nstdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )
    return completed


def test_dry_run_on_current_repo_refuses_template_root() -> None:
    run_upgrade([str(ROOT)], expect_success=False)


def test_dry_run_on_generated_repo_is_no_op_or_safe() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "demo"
        run_init(["new", "--name", "Upgrade Demo", "--target", str(target)])
        completed = run_upgrade([str(target)], expect_success=True)
        output = completed.stdout
        if "Will add:" not in output:
            raise AssertionError("Upgrade plan missing 'Will add' section")
        if "Will modify:" not in output:
            raise AssertionError("Upgrade plan missing 'Will modify' section")


def test_dry_run_on_older_fixture_reports_missing_assets() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "older"
        run_init(["new", "--name", "Older Demo", "--target", str(target)])
        # Simulate an older repo by removing newer assets.
        (target / "scripts" / "statedd_evidence_pack.py").unlink(missing_ok=True)
        (target / "schemas" / "evidence_manifest.schema.json").unlink(missing_ok=True)
        (target / "scripts" / "test_evidence_pack.py").unlink(missing_ok=True)
        (target / "scripts" / "statedd_worktree_guard.py").unlink(missing_ok=True)
        (target / "ANTI_BRITTLENESS_GUARD.md").unlink(missing_ok=True)

        completed = run_upgrade([str(target)], expect_success=True)
        output = completed.stdout
        if "statedd_evidence_pack.py" not in output:
            raise AssertionError("Missing evidence pack script not reported")
        if "evidence_manifest.schema.json" not in output:
            raise AssertionError("Missing evidence manifest schema not reported")
        if "statedd_worktree_guard.py" not in output:
            raise AssertionError("Missing worktree guard script not reported")
        if "ANTI_BRITTLENESS_GUARD.md" not in output:
            raise AssertionError("Missing anti-brittleness guard doc not reported")


def test_apply_adds_safe_missing_assets() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "older"
        run_init(["new", "--name", "Older Demo", "--target", str(target)])
        (target / "scripts" / "statedd_evidence_pack.py").unlink(missing_ok=True)
        (target / "schemas" / "evidence_manifest.schema.json").unlink(missing_ok=True)
        (target / "QUALITY_FIREWALL.md").unlink(missing_ok=True)
        (target / "docs" / "quality_gates" / "README.md").unlink(missing_ok=True)
        (target / "scripts" / "statedd_worktree_guard.py").unlink(missing_ok=True)
        (target / "docs" / "quality_gates" / "ANTI_BRITTLENESS_GATE.md").unlink(missing_ok=True)

        run_upgrade([str(target), "--apply"], expect_success=True)
        if not (target / "scripts" / "statedd_evidence_pack.py").exists():
            raise AssertionError("Apply did not add missing script")
        if not (target / "schemas" / "evidence_manifest.schema.json").exists():
            raise AssertionError("Apply did not add missing schema")
        if not (target / "QUALITY_FIREWALL.md").exists():
            raise AssertionError("Apply did not add missing quality firewall")
        if not (target / "docs" / "quality_gates" / "README.md").exists():
            raise AssertionError("Apply did not add missing quality gates README")
        if not (target / "scripts" / "statedd_worktree_guard.py").exists():
            raise AssertionError("Apply did not add missing worktree guard")
        if not (target / "docs" / "quality_gates" / "ANTI_BRITTLENESS_GATE.md").exists():
            raise AssertionError("Apply did not add missing anti-brittleness gate")


def test_apply_preserves_readme_and_project_truth() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "older"
        run_init(["new", "--name", "Older Demo", "--target", str(target)])
        original_readme = (target / "README.md").read_text(encoding="utf-8")
        original_state = (target / "PROJECT_STATE.yaml").read_text(encoding="utf-8")

        run_upgrade([str(target), "--apply"], expect_success=True)

        if (target / "README.md").read_text(encoding="utf-8") != original_readme:
            raise AssertionError("Apply unexpectedly changed README.md")
        if (target / "PROJECT_STATE.yaml").read_text(encoding="utf-8") != original_state:
            raise AssertionError("Apply unexpectedly changed PROJECT_STATE.yaml")


def test_conflict_fixture_refuses_unsafe_overwrite() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "older"
        run_init(["new", "--name", "Older Demo", "--target", str(target)])
        # Modify a safe managed asset locally so it differs from template.
        script = target / "scripts" / "statedd_evidence_pack.py"
        script.write_text("# locally modified\n", encoding="utf-8")

        completed = run_upgrade([str(target)], expect_success=True)
        if "Conflicts" not in completed.stdout:
            raise AssertionError("Expected conflict section in dry-run output")
        if "statedd_evidence_pack.py" not in completed.stdout:
            raise AssertionError("Expected modified script to be reported as conflict")

        # Apply without --force-managed should refuse.
        run_upgrade([str(target), "--apply"], expect_success=False)


def test_force_managed_replaces_outdated_safe_asset() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "older"
        run_init(["new", "--name", "Older Demo", "--target", str(target)])
        script = target / "scripts" / "statedd_evidence_pack.py"
        script.write_text("# locally modified\n", encoding="utf-8")

        run_upgrade([str(target), "--apply", "--force-managed"], expect_success=True)
        if "# locally modified" in script.read_text(encoding="utf-8"):
            raise AssertionError("--force-managed did not replace outdated safe asset")


def test_force_managed_never_overwrites_truth_files() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "older"
        run_init(["new", "--name", "Older Demo", "--target", str(target)])
        state = target / "PROJECT_STATE.yaml"
        state.write_text("# locally modified state\n", encoding="utf-8")

        run_upgrade([str(target), "--apply", "--force-managed"], expect_success=True)
        if "# locally modified state" not in state.read_text(encoding="utf-8"):
            raise AssertionError("--force-managed unexpectedly overwrote a project-truth file")


def test_upgrade_never_installs_template_tests_or_history() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "legacy-downstream"
        target.mkdir()
        run_upgrade([str(target), "--apply"], expect_success=True)
        leaked = [
            path.relative_to(target).as_posix()
            for path in target.rglob("*")
            if path.is_file()
            and (
                path.name.startswith("test_")
                or path.name == "init_template.py"
                or "fixtures" in path.parts
                or "evidence" in path.parts
                or path.name == "CHANGELOG.md"
            )
        ]
        if leaked:
            raise AssertionError(f"Upgrade installed template-only payload: {sorted(leaked)}")


def test_report_writes_json() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "older"
        report = Path(tmp) / "report.json"
        run_init(["new", "--name", "Older Demo", "--target", str(target)])
        run_upgrade([str(target), "--report", str(report)], expect_success=True)
        if not report.exists():
            raise AssertionError("Report file was not written")
        data = json.loads(report.read_text(encoding="utf-8"))
        if data.get("schema") != "statedd.upgrade_report.v1":
            raise AssertionError("Report has unexpected schema")


def test_report_reflects_dry_run_value() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "older"
        dry_report = Path(tmp) / "dry_report.json"
        applied_report = Path(tmp) / "applied_report.json"
        run_init(["new", "--name", "Older Demo", "--target", str(target)])

        run_upgrade([str(target), "--report", str(dry_report)], expect_success=True)
        dry_data = json.loads(dry_report.read_text(encoding="utf-8"))
        if dry_data.get("dry_run") is not True:
            raise AssertionError("Dry-run report should state dry_run: true")

        run_upgrade([str(target), "--apply", "--report", str(applied_report)], expect_success=True)
        applied_data = json.loads(applied_report.read_text(encoding="utf-8"))
        if applied_data.get("dry_run") is not False:
            raise AssertionError("Applied upgrade report should state dry_run: false")


def main() -> int:
    tests = [
        test_dry_run_on_current_repo_refuses_template_root,
        test_dry_run_on_generated_repo_is_no_op_or_safe,
        test_dry_run_on_older_fixture_reports_missing_assets,
        test_apply_adds_safe_missing_assets,
        test_apply_preserves_readme_and_project_truth,
        test_conflict_fixture_refuses_unsafe_overwrite,
        test_force_managed_replaces_outdated_safe_asset,
        test_force_managed_never_overwrites_truth_files,
        test_upgrade_never_installs_template_tests_or_history,
        test_report_writes_json,
        test_report_reflects_dry_run_value,
    ]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
