#!/usr/bin/env python3
"""Regression tests for repository-role-driven StateDD version checks.

These tests intentionally stay stdlib-only.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION_CHECK = ROOT / "scripts" / "statedd_version_check.py"
VERSION = "statedd-template-v5"


def run_version_check(root: Path, *, expect_success: bool) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        [sys.executable, str(VERSION_CHECK), str(root)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if expect_success and completed.returncode != 0:
        raise AssertionError(
            f"Expected version check success, got {completed.returncode}\n"
            f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )
    if not expect_success and completed.returncode == 0:
        raise AssertionError(
            f"Expected version check failure, got success\nstdout:\n{completed.stdout}"
        )
    return completed


def write_base_repo(root: Path, *, role: str, readme_heading: str) -> None:
    (root / "scripts").mkdir(parents=True)
    (root / "VERSION").write_text(f"{VERSION}\n", encoding="utf-8")
    (root / "AGENTS.md").write_text(
        "---\n"
        f'repo_role: "{role}"\n'
        f'statedd_version: "{VERSION}"\n'
        "---\n\n"
        "# Agent Contract\n",
        encoding="utf-8",
    )
    (root / "PROJECT_STATE.yaml").write_text(
        "metadata:\n"
        f'  version: "{VERSION}"\n'
        "workflow:\n"
        f"  repo_role: {role}\n",
        encoding="utf-8",
    )
    (root / "PROJECT_DNA.yaml").write_text(f'version: "{VERSION}"\n', encoding="utf-8")
    (root / "PROJECT_ADAPTER.yaml").write_text(f'version: "{VERSION}"\n', encoding="utf-8")
    (root / "scripts" / "init_template.py").write_text(
        f'TEMPLATE_VERSION = "{VERSION}"\n',
        encoding="utf-8",
    )
    (root / "README.md").write_text(
        f"# {readme_heading}\n\nCurrent version: `{VERSION}`\n",
        encoding="utf-8",
    )


def test_template_role_requires_current_template_assets_with_any_readme_heading() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_base_repo(root, role="template_repository", readme_heading="Renamed Template Home")
        (root / "docs").mkdir()
        (root / "docs" / "UPGRADING.md").write_text(
            f"Current version: `{VERSION}`\n",
            encoding="utf-8",
        )

        completed = run_version_check(root, expect_success=False)
        if "CHANGELOG.md" not in completed.stdout:
            raise AssertionError(
                "Template role did not make CHANGELOG.md a required current asset:\n"
                f"{completed.stdout}"
            )


def test_downstream_role_ignores_obsolete_template_readme_heading() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_base_repo(
            root,
            role="downstream_project",
            readme_heading="State Driven Development Template",
        )

        run_version_check(root, expect_success=True)


def main() -> int:
    tests = [
        test_template_role_requires_current_template_assets_with_any_readme_heading,
        test_downstream_role_ignores_obsolete_template_readme_heading,
    ]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
