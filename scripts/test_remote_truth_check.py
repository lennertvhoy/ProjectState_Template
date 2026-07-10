#!/usr/bin/env python3
"""Focused regressions for scripts/statedd_remote_truth_check.py."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import statedd_remote_truth_check as remote_truth  # noqa: E402


HEAD = "1111111111111111111111111111111111111111"
OTHER_HEAD = "2222222222222222222222222222222222222222"
BRANCH = "feature/closure"
UPSTREAM = f"origin/{BRANCH}"


def fake_commands(
    *,
    status: str = "",
    branch: str = BRANCH,
    upstream: str | None = UPSTREAM,
    upstream_head: str = HEAD,
    remote_head: str = HEAD,
):
    def run(cmd: list[str]) -> tuple[int, str, str]:
        if cmd == ["pwd"]:
            return 0, "/tmp/repo", ""
        if cmd == ["git", "remote", "-v"]:
            return 0, "origin\thttps://github.com/statedd/template.git (fetch)", ""
        if cmd in (
            ["git", "branch", "--show-current"],
            ["git", "symbolic-ref", "--quiet", "--short", "HEAD"],
        ):
            return 0, branch, ""
        if cmd in (
            ["git", "status", "--short"],
            ["git", "status", "--porcelain=v1", "--untracked-files=all"],
        ):
            return 0, status, ""
        if cmd == ["git", "log", "--oneline", "-8"]:
            return 0, f"{HEAD[:7]} test", ""
        if cmd == ["git", "rev-parse", "HEAD"]:
            return 0, HEAD, ""
        if cmd == ["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}"]:
            if upstream is None:
                return 128, "", "no upstream configured"
            return 0, upstream, ""
        if cmd == ["git", "rev-parse", "@{upstream}"]:
            if upstream is None:
                return 128, "", "no upstream configured"
            return 0, upstream_head, ""
        if cmd[:4] == ["git", "ls-remote", "--heads", "origin"]:
            ref = cmd[4] if len(cmd) > 4 else ""
            return 0, f"{remote_head}\t{ref}", ""
        if cmd[:3] == ["git", "ls-remote", "origin"]:
            ref = cmd[3] if len(cmd) > 3 else ""
            if ref == "HEAD":
                return 0, f"{remote_head}\tHEAD", ""
            return 0, f"{remote_head}\trefs/heads/{BRANCH}", ""
        if cmd == ["git", "remote", "get-url", "origin"]:
            return 0, "https://github.com/statedd/template.git", ""
        return 127, "", f"unexpected command: {' '.join(cmd)}"

    return run


def run_checker(**kwargs) -> remote_truth.RemoteTruthCheck:
    temp = tempfile.TemporaryDirectory()
    checker = remote_truth.RemoteTruthCheck(Path(temp.name))
    checker._test_tempdir = temp  # type: ignore[attr-defined]
    checker.run_cmd = fake_commands(**kwargs)  # type: ignore[method-assign]
    checker.exit_code = checker.run()  # type: ignore[attr-defined]
    return checker


def test_clean_exact_heads_pass_as_pushed_only() -> None:
    checker = run_checker()
    assert checker.exit_code == 0
    assert checker.closure_label == "pushed"


def test_staged_change_fails() -> None:
    checker = run_checker(status="M  tracked.py")
    assert checker.exit_code == 1
    assert any("dirty" in failure.lower() for failure in checker.failures)


def test_unstaged_change_fails() -> None:
    checker = run_checker(status=" M tracked.py")
    assert checker.exit_code == 1
    assert any("dirty" in failure.lower() for failure in checker.failures)


def test_untracked_file_fails() -> None:
    checker = run_checker(status="?? untracked.py")
    assert checker.exit_code == 1
    assert any("dirty" in failure.lower() for failure in checker.failures)


def test_missing_upstream_fails() -> None:
    checker = run_checker(upstream=None)
    assert checker.exit_code == 1
    assert any("upstream" in failure.lower() for failure in checker.failures)


def test_stale_upstream_tracking_ref_fails() -> None:
    checker = run_checker(upstream_head=OTHER_HEAD)
    assert checker.exit_code == 1
    assert any("upstream" in failure.lower() for failure in checker.failures)


def test_remote_head_mismatch_fails() -> None:
    checker = run_checker(remote_head=OTHER_HEAD)
    assert checker.exit_code == 1
    assert any("remote" in failure.lower() for failure in checker.failures)


def test_detached_head_fails_without_crashing() -> None:
    checker = run_checker(branch="")
    assert checker.exit_code == 1
    assert any("branch" in failure.lower() for failure in checker.failures)


def main() -> int:
    tests = [
        test_clean_exact_heads_pass_as_pushed_only,
        test_staged_change_fails,
        test_unstaged_change_fails,
        test_untracked_file_fails,
        test_missing_upstream_fails,
        test_stale_upstream_tracking_ref_fails,
        test_remote_head_mismatch_fails,
        test_detached_head_fails_without_crashing,
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
