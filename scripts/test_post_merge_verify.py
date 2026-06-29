#!/usr/bin/env python3
"""Regression tests for scripts/statedd_post_merge_verify.py."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERIFY_SCRIPT = ROOT / "scripts" / "statedd_post_merge_verify.py"


def run_verify(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(VERIFY_SCRIPT), *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_help_runs() -> None:
    completed = run_verify(["--help"])
    assert completed.returncode == 0, completed.stderr
    assert "pr-number" in completed.stdout


def test_missing_pr_number_fails() -> None:
    completed = run_verify([])
    assert completed.returncode == 2, completed.stderr


if __name__ == "__main__":
    tests = [test_help_runs, test_missing_pr_number_fails]
    for t in tests:
        t()
        print(f"PASS {t.__name__}")
