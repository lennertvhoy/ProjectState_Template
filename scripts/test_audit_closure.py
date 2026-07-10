#!/usr/bin/env python3
"""Closure-boundary regressions for scripts/statedd_audit.py."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import statedd_audit as audit  # noqa: E402


HEAD = "1111111111111111111111111111111111111111"
STALE_HEAD = "2222222222222222222222222222222222222222"
BRANCH = "feature/closure"


def test_uninspectable_git_status_is_failure() -> None:
    original = audit.run_command
    audit.run_command = lambda args, cwd: (128, "", "not a git repository")  # type: ignore[assignment]
    try:
        result = audit.AuditResult()
        audit.check_worktree_clean(Path("/tmp/not-a-repo"), result)
        assert result.has_failures()
    finally:
        audit.run_command = original


def test_porcelain_dirty_categories_all_fail() -> None:
    original = audit.run_command
    try:
        for status in ("M  staged.py", " M unstaged.py", "?? untracked.py"):
            audit.run_command = lambda args, cwd, value=status: (0, value, "")  # type: ignore[assignment]
            result = audit.AuditResult()
            audit.check_worktree_clean(Path("/tmp/repo"), result)
            assert result.has_failures(), status
    finally:
        audit.run_command = original


def test_unrelated_evidence_sha_does_not_count_as_recorded_head() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        evidence = root / "docs" / "evidence" / "slice"
        evidence.mkdir(parents=True)
        (evidence / "README.md").write_text(
            f"# Evidence\n\nBranch: {BRANCH}\nHEAD: {STALE_HEAD}\n",
            encoding="utf-8",
        )

        original_branch_head = audit.git_branch_and_head
        original_run = audit.run_command
        audit.git_branch_and_head = lambda repo: (BRANCH, HEAD)  # type: ignore[assignment]
        audit.run_command = lambda args, cwd: (0, HEAD, "")  # type: ignore[assignment]
        try:
            result = audit.AuditResult()
            audit.check_branch_head_recorded(root, result)
            assert result.has_failures()
        finally:
            audit.git_branch_and_head = original_branch_head
            audit.run_command = original_run


def main() -> int:
    tests = [
        test_uninspectable_git_status_is_failure,
        test_porcelain_dirty_categories_all_fail,
        test_unrelated_evidence_sha_does_not_count_as_recorded_head,
    ]
    failures = 0
    for test in tests:
        try:
            test()
            print(f"PASS {test.__name__}")
        except Exception as exc:
            failures += 1
            print(f"FAIL {test.__name__}: {exc}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
