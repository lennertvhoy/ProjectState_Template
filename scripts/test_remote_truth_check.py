from __future__ import annotations

import subprocess
from pathlib import Path

from statedd_remote_truth_check import RemoteTruthCheck


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def pushed_repo(tmp_path: Path) -> tuple[Path, Path]:
    remote = tmp_path / "remote.git"
    repo = tmp_path / "repo"
    subprocess.run(["git", "init", "--bare", "-q", str(remote)], check=True)
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    git(repo, "config", "user.email", "test@example.invalid")
    git(repo, "config", "user.name", "StateDD Test")
    git(repo, "checkout", "-q", "-b", "slice")
    (repo / "tracked.txt").write_text("one\n", encoding="utf-8")
    git(repo, "add", "tracked.txt")
    git(repo, "commit", "-q", "-m", "initial")
    git(repo, "remote", "add", "origin", str(remote))
    git(repo, "push", "-q", "-u", "origin", "slice")
    return repo, remote


def test_clean_pushed_branch_stops_at_pushed_state(tmp_path: Path) -> None:
    repo, _ = pushed_repo(tmp_path)
    checker = RemoteTruthCheck(repo, claimed_files=["tracked.txt"])

    assert checker.run() == 0
    assert checker.closure_label == "pushed"
    assert {boundary.name for boundary in checker.boundaries}.isdisjoint({"github_visible", "ci"})


def test_dirty_worktree_fails_remote_branch_preflight(tmp_path: Path) -> None:
    repo, _ = pushed_repo(tmp_path)
    (repo / "tracked.txt").write_text("changed\n", encoding="utf-8")
    checker = RemoteTruthCheck(repo)

    assert checker.run() == 1
    assert any("worktree is dirty" in failure for failure in checker.failures)
    assert checker.closure_label == "local-only"


def test_unpushed_commit_fails_remote_branch_preflight(tmp_path: Path) -> None:
    repo, _ = pushed_repo(tmp_path)
    (repo / "tracked.txt").write_text("two\n", encoding="utf-8")
    git(repo, "add", "tracked.txt")
    git(repo, "commit", "-q", "-m", "unpushed")
    checker = RemoteTruthCheck(repo)

    assert checker.run() == 1
    assert any("remote_contains_head" in failure for failure in checker.failures)


def test_untracked_claim_fails(tmp_path: Path) -> None:
    repo, _ = pushed_repo(tmp_path)
    checker = RemoteTruthCheck(repo, claimed_files=["missing.txt"])

    assert checker.run() == 1
    assert any("Claimed file not tracked" in failure for failure in checker.failures)
