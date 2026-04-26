#!/usr/bin/env python3
"""Regression tests for the StateDD initializer.

These tests intentionally stay stdlib-only so template maintainers and
downstream repos can run them without installing a test framework.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INIT_SCRIPT = ROOT / "scripts" / "init_template.py"


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


def assert_no_external_files(path: Path) -> None:
    leaked = sorted(item.relative_to(path) for item in path.rglob("*") if item.is_file())
    if leaked:
        raise AssertionError(f"Initializer wrote outside the target repo: {leaked}")


def assert_mentions_symlink(completed: subprocess.CompletedProcess[str]) -> None:
    output = f"{completed.stdout}\n{completed.stderr}".lower()
    if "symlink" not in output:
        raise AssertionError(f"Expected symlink refusal message, got:\n{output}")


def test_adopt_rejects_symlinked_managed_directory() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        repo = root / "repo"
        outside = root / "outside"
        repo.mkdir()
        outside.mkdir()
        os.symlink(outside, repo / "docs")

        completed = run_init(["adopt", "--name", "Audit Demo", "--target", str(repo)], expect_success=False)

        assert_mentions_symlink(completed)
        assert_no_external_files(outside)


def test_new_rejects_symlinked_existing_directory() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        repo = root / "repo"
        outside = root / "outside"
        repo.mkdir()
        outside.mkdir()
        os.symlink(outside, repo / "docs")

        completed = run_init(
            [
                "new",
                "--name",
                "Audit Demo",
                "--target",
                str(repo),
                "--overwrite",
                "--force-overwrite",
            ],
            expect_success=False,
        )

        assert_mentions_symlink(completed)
        assert_no_external_files(outside)


def test_readme_link_rejects_symlinked_readme_before_writes() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        repo = root / "repo"
        outside = root / "outside"
        repo.mkdir()
        outside.mkdir()
        (outside / "README.md").write_text("# External\n", encoding="utf-8")
        os.symlink(outside / "README.md", repo / "README.md")

        completed = run_init(
            ["adopt", "--name", "Audit Demo", "--target", str(repo), "--readme-link"],
            expect_success=False,
        )

        assert_mentions_symlink(completed)
        if any(item.name in {"AGENTS.md", "PROJECT_STATE.yaml", "prompts"} for item in repo.iterdir()):
            raise AssertionError("README symlink preflight failed after writing workflow files")
        if (outside / "README.md").read_text(encoding="utf-8") != "# External\n":
            raise AssertionError("Initializer modified the external README target")


def test_top_level_help_shows_subcommands() -> None:
    completed = run_init(["--help"], expect_success=True)
    help_text = completed.stdout
    if "new" not in help_text or "adopt" not in help_text:
        raise AssertionError(f"Top-level help does not advertise both subcommands:\n{help_text}")


def test_legacy_new_invocation_still_works() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "legacy"
        run_init(["--name", "Legacy Demo", "--target", str(target)], expect_success=True)
        if not (target / "AGENTS.md").exists():
            raise AssertionError("Legacy initializer invocation did not create AGENTS.md")


def test_new_copies_curated_template_surface_only() -> None:
    sentinel = ROOT / "LOCAL_UNTRACKED_SENTINEL_FOR_TEST.md"
    if sentinel.exists():
        raise AssertionError(f"Unexpected pre-existing test sentinel: {sentinel}")

    try:
        sentinel.write_text("local maintenance artifact\n", encoding="utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "demo"
            run_init(["new", "--name", "Audit Demo", "--target", str(target)], expect_success=True)
            if (target / sentinel.name).exists():
                raise AssertionError("Initializer copied an untracked root-level maintenance artifact")
    finally:
        sentinel.unlink(missing_ok=True)


def main() -> int:
    tests = [
        test_adopt_rejects_symlinked_managed_directory,
        test_new_rejects_symlinked_existing_directory,
        test_readme_link_rejects_symlinked_readme_before_writes,
        test_top_level_help_shows_subcommands,
        test_legacy_new_invocation_still_works,
        test_new_copies_curated_template_surface_only,
    ]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
