#!/usr/bin/env python3
"""Regression tests for scripts/statedd_worktree_guard.py."""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GUARD = ROOT / "scripts" / "statedd_worktree_guard.py"


def run(args: list[str], *, cwd: Path, expect_code: int | None = None) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        [sys.executable, str(GUARD), *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    if expect_code is not None and completed.returncode != expect_code:
        raise AssertionError(
            f"Expected exit {expect_code} for {args}, got {completed.returncode}\n"
            f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )
    return completed


def git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise AssertionError(f"git {' '.join(args)} failed\nstdout:\n{completed.stdout}\nstderr:\n{completed.stderr}")
    return completed.stdout.strip()


def init_repo(root: Path, *, with_origin: bool = True) -> Path:
    repo = root / "repo"
    repo.mkdir()
    git(repo, "init", "-b", "main")
    git(repo, "config", "user.email", "statedd@example.invalid")
    git(repo, "config", "user.name", "StateDD Test")
    (repo / "README.md").write_text("# Demo\n", encoding="utf-8")
    git(repo, "add", "README.md")
    git(repo, "commit", "-m", "initial")
    if with_origin:
        origin = root / "origin.git"
        git(root, "init", "--bare", str(origin))
        git(repo, "remote", "add", "origin", str(origin))
        git(repo, "push", "-u", "origin", "main")
        git(repo, "remote", "set-head", "origin", "main")
    return repo


def assert_contains(output: str, expected: str) -> None:
    if expected not in output:
        raise AssertionError(f"Expected output to contain {expected!r}, got:\n{output}")


def test_clean_repo_passes_start_slice() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        repo = init_repo(Path(tmp))
        completed = run(["--repo", str(repo), "--mode", "start-slice"], cwd=repo, expect_code=0)
        assert_contains(completed.stdout, "safe to start: yes")
        assert_contains(completed.stdout, "dirty file count: 0")
        assert_contains(completed.stdout, "origin remote URL:")


def test_dirty_repo_fails_start_slice_without_classification() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        repo = init_repo(Path(tmp))
        (repo / "local.txt").write_text("dirty\n", encoding="utf-8")
        completed = run(["--repo", str(repo), "--mode", "start-slice"], cwd=repo, expect_code=1)
        assert_contains(completed.stdout, "safe to start: no")
        assert_contains(completed.stdout, "Dirty files are not fully classified")


def test_dirty_repo_can_warn_only_for_diagnostics() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        repo = init_repo(Path(tmp))
        (repo / "local.txt").write_text("dirty\n", encoding="utf-8")
        completed = run(["--repo", str(repo), "--mode", "start-slice", "--warn-only"], cwd=repo, expect_code=0)
        assert_contains(completed.stdout, "safe to start: no")


def test_dirty_repo_with_classification_reports_classified_state() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        repo = init_repo(Path(tmp))
        (repo / "local.txt").write_text("dirty\n", encoding="utf-8")
        evidence = repo / "docs" / "evidence" / "slice" / "README.md"
        evidence.parent.mkdir(parents=True)
        evidence.write_text(
            """# Evidence

## Worktree Dirty File Classification

| status | path | category | owner/notes |
| --- | --- | --- | --- |
| ?? | `local.txt` | intended_slice_work | test owns this file |
| ?? | `docs/evidence/slice/README.md` | intended_slice_work | classification evidence |
""",
            encoding="utf-8",
        )
        completed = run(
            ["--repo", str(repo), "--mode", "start-slice", "--classification-file", str(evidence)],
            cwd=repo,
            expect_code=0,
        )
        assert_contains(completed.stdout, "safe to start: yes")
        assert_contains(completed.stdout, "dirty files classified: yes")
        assert_contains(completed.stdout, "local.txt [intended_slice_work]")


def test_closure_mode_fails_dirty_worktree() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        repo = init_repo(Path(tmp))
        (repo / "local.txt").write_text("dirty\n", encoding="utf-8")
        completed = run(["--repo", str(repo), "--mode", "closure"], cwd=repo, expect_code=1)
        assert_contains(completed.stdout, "Closure mode requires a clean worktree")


def test_detached_head_and_missing_origin_are_reported_not_proven() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        repo = init_repo(Path(tmp), with_origin=False)
        head = git(repo, "rev-parse", "HEAD")
        git(repo, "checkout", "--detach", head)
        completed = run(["--repo", str(repo), "--mode", "start-slice"], cwd=repo, expect_code=1)
        assert_contains(completed.stdout, "detached HEAD")
        assert_contains(completed.stdout, "origin remote URL: not proven")
        assert_contains(completed.stdout, "current branch is shared/default branch: not proven")


def test_classify_dirty_prints_template_table() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        repo = init_repo(Path(tmp))
        (repo / "local.txt").write_text("dirty\n", encoding="utf-8")
        completed = run(["--repo", str(repo), "--mode", "classify-dirty"], cwd=repo, expect_code=0)
        assert_contains(completed.stdout, "## Worktree Dirty File Classification")
        assert_contains(completed.stdout, "unknown_do_not_touch")
        assert_contains(completed.stdout, "local.txt")


def test_linked_worktrees_are_printed() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        repo = init_repo(root)
        linked = root / "linked"
        git(repo, "worktree", "add", "-b", "linked-branch", str(linked))
        completed = run(["--repo", str(repo), "--mode", "start-slice"], cwd=repo, expect_code=0)
        assert_contains(completed.stdout, "linked worktrees:")
        assert_contains(completed.stdout, str(linked))


def test_unknown_do_not_touch_blocks_start() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        repo = init_repo(Path(tmp))
        (repo / "local.txt").write_text("dirty\n", encoding="utf-8")
        evidence = repo / "docs" / "evidence" / "slice" / "README.md"
        evidence.parent.mkdir(parents=True)
        evidence.write_text(
            """# Evidence

## Worktree Dirty File Classification

| status | path | category | owner/notes |
| --- | --- | --- | --- |
| ?? | `local.txt` | unknown_do_not_touch | dangerous legacy file |
| ?? | `docs/evidence/slice/README.md` | intended_slice_work | classification evidence |
""",
            encoding="utf-8",
        )
        completed = run(
            ["--repo", str(repo), "--mode", "start-slice", "--classification-file", str(evidence)],
            cwd=repo,
            expect_code=1,
        )
        assert_contains(completed.stdout, "safe to start: no")
        assert_contains(completed.stdout, "do-not-touch")


def test_feature_branch_is_not_shared_default() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        repo = init_repo(Path(tmp))
        git(repo, "checkout", "-b", "feature-x")
        git(repo, "push", "-u", "origin", "feature-x")
        (repo / "local.txt").write_text("dirty\n", encoding="utf-8")
        completed = run(["--repo", str(repo), "--mode", "start-slice"], cwd=repo, expect_code=1)
        assert_contains(completed.stdout, "current branch is shared/default branch: no")


def test_unstaged_hidden_path_preserves_porcelain_columns() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        repo = init_repo(Path(tmp))
        hidden = repo / ".github" / "workflow.yml"
        hidden.parent.mkdir()
        hidden.write_text("before\n", encoding="utf-8")
        git(repo, "add", ".github/workflow.yml")
        git(repo, "commit", "-m", "add hidden path")
        hidden.write_text("after\n", encoding="utf-8")

        evidence = repo / "evidence.md"
        evidence.write_text(
            """## Worktree Dirty File Classification

| status | path | category | owner/notes |
| --- | --- | --- | --- |
| M | `.github/workflow.yml` | intended_slice_work | hidden path under test |
| ?? | `evidence.md` | generated_artifact | classification file |
""",
            encoding="utf-8",
        )
        completed = run(
            ["--repo", str(repo), "--mode", "start-slice", "--classification-file", str(evidence)],
            cwd=repo,
            expect_code=0,
        )
        assert_contains(completed.stdout, "dirty files classified: yes")
        assert_contains(completed.stdout, ".github/workflow.yml [intended_slice_work]")


def main() -> int:
    tests = [
        test_clean_repo_passes_start_slice,
        test_dirty_repo_fails_start_slice_without_classification,
        test_dirty_repo_can_warn_only_for_diagnostics,
        test_dirty_repo_with_classification_reports_classified_state,
        test_closure_mode_fails_dirty_worktree,
        test_detached_head_and_missing_origin_are_reported_not_proven,
        test_classify_dirty_prints_template_table,
        test_linked_worktrees_are_printed,
        test_unknown_do_not_touch_blocks_start,
        test_feature_branch_is_not_shared_default,
        test_unstaged_hidden_path_preserves_porcelain_columns,
    ]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
