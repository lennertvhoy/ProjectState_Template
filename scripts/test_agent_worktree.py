#!/usr/bin/env python3
"""Regression tests for scripts/statedd_agent_worktree.py."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import statedd_agent_worktree as orchestrator


ROOT = Path(__file__).resolve().parents[1]
ORCHESTRATOR = ROOT / "scripts" / "statedd_agent_worktree.py"


def run(args: list[str], *, cwd: Path, expect_code: int | None = None) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        [sys.executable, str(ORCHESTRATOR), *args],
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


def init_repo(root: Path) -> Path:
    repo = root / "repo"
    repo.mkdir()
    git(repo, "init", "-b", "main")
    git(repo, "config", "user.email", "statedd@example.invalid")
    git(repo, "config", "user.name", "StateDD Test")
    (repo / "README.md").write_text("# Demo\n", encoding="utf-8")
    (repo / ".gitignore").write_text((ROOT / ".gitignore").read_text(encoding="utf-8"), encoding="utf-8")
    git(repo, "add", "README.md", ".gitignore")
    git(repo, "commit", "-m", "initial")
    origin = root / "origin.git"
    git(root, "init", "--bare", str(origin))
    git(repo, "remote", "add", "origin", str(origin))
    git(repo, "push", "-u", "origin", "main")
    git(repo, "remote", "set-head", "origin", "main")
    return repo


def assert_contains(output: str, expected: str) -> None:
    if expected not in output:
        raise AssertionError(f"Expected output to contain {expected!r}, got:\n{output}")


def agent_branch_prefix(slice_id: str, agent_id: str) -> str:
    """Return the expected branch prefix given the orchestrator's naming rules."""
    clean_slice = "".join(c if c.isalnum() else "-" for c in slice_id.lower()).strip("-")
    short = agent_id[:4].lower()
    return f"bl-{clean_slice}-{short}-"


def test_start_creates_worktree_and_reservation() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        repo = init_repo(Path(tmp))
        agent_id = "agent-a1b2"
        completed = run(
            ["--repo", str(repo), "start", "--slice-id", "BL-TEST-001", "--agent-id", agent_id],
            cwd=repo,
            expect_code=0,
        )
        assert_contains(completed.stdout, "Agent worktree ready:")
        assert_contains(completed.stdout, f"Branch: {agent_branch_prefix('BL-TEST-001', agent_id)}")

        # Find the created worktree path from output.
        worktree_line = [line for line in completed.stdout.splitlines() if line.startswith("Agent worktree ready:")][0]
        worktree = Path(worktree_line.split("Agent worktree ready:", 1)[1].strip())

        assert worktree.exists()
        context_path = worktree / ".statedd" / "agent.context"
        assert context_path.exists()
        context = json.loads(context_path.read_text(encoding="utf-8"))
        assert context["schema"] == "statedd.agent_context.v1"
        assert context["agent_id"] == agent_id
        assert context["slice_id"] == "BL-TEST-001"
        assert context["branch"].startswith(agent_branch_prefix("BL-TEST-001", agent_id))
        assert context["worktree_path"] == str(worktree)

        # The orchestrator's own context must not make closure-grade worktrees
        # appear dirty. Generated repositories inherit this ignore contract.
        assert git(worktree, "check-ignore", ".statedd/agent.context") == ".statedd/agent.context"
        assert ".statedd/" not in git(worktree, "status", "--short", "--untracked-files=all")

        # Reservation ref should exist and point to base commit.
        ref = context["reservation_ref"]
        assert ref.startswith("refs/statedd/reservations/")
        sha = git(repo, "rev-parse", ref)
        base_sha = git(repo, "rev-parse", "main")
        assert sha == base_sha


def test_double_reserve_same_branch_fails() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        repo = init_repo(Path(tmp))
        agent_id = "agent-a1b2"
        completed = run(
            ["--repo", str(repo), "start", "--slice-id", "BL-TEST-002", "--agent-id", agent_id],
            cwd=repo,
            expect_code=0,
        )
        worktree_line = [line for line in completed.stdout.splitlines() if line.startswith("Agent worktree ready:")][0]
        worktree = Path(worktree_line.split("Agent worktree ready:", 1)[1].strip())
        context = json.loads((worktree / ".statedd" / "agent.context").read_text(encoding="utf-8"))

        # Second start with explicit same branch must fail.
        completed = run(
            ["--repo", str(repo), "start", "--slice-id", "BL-TEST-002", "--agent-id", agent_id, "--branch", context["branch"]],
            cwd=repo,
            expect_code=1,
        )
        assert_contains(completed.stderr, "Reservation ref already exists")


def test_start_auto_base_uses_current_branch_when_main_is_absent() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        repo = init_repo(Path(tmp))
        git(repo, "checkout", "-b", "feature-ci-checkout")
        git(repo, "branch", "-D", "main")
        git(repo, "remote", "set-head", "origin", "-d")
        git(repo, "update-ref", "-d", "refs/remotes/origin/main")

        completed = run(
            ["--repo", str(repo), "--dry-run", "start", "--slice-id", "CI-SMOKE-001", "--agent-id", "agent-a1b2"],
            cwd=repo,
            expect_code=0,
        )
        assert_contains(completed.stdout, "DRY RUN: would create branch")
        assert_contains(completed.stdout, "base: feature-ci-checkout")


def test_guard_passes_in_agent_worktree_with_dirty_files() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        repo = init_repo(Path(tmp))
        agent_id = "agent-a1b2"
        run(
            ["--repo", str(repo), "start", "--slice-id", "BL-TEST-003", "--agent-id", agent_id],
            cwd=repo,
            expect_code=0,
        )
        worktree = list(repo.joinpath(".worktrees").glob(f"{agent_branch_prefix('BL-TEST-003', agent_id)}*"))[0]

        (worktree / "feature.txt").write_text("new\n", encoding="utf-8")
        completed = run(["--repo", str(repo), "guard", "--worktree", str(worktree), "--mode", "start-slice"], cwd=repo, expect_code=0)
        assert_contains(completed.stdout, f"Agent context: {agent_id} / BL-TEST-003")
        assert_contains(completed.stdout, "agent branch is private: yes")
        assert_contains(completed.stdout, "feature.txt")


def test_lock_detection_reports_concurrent_git_operation() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        repo = init_repo(Path(tmp))
        common = Path(git(repo, "rev-parse", "--git-common-dir"))
        if not common.is_absolute():
            common = repo / common
        lock = common / "index.lock"
        lock.write_text("", encoding="utf-8")
        try:
            completed = run(
                ["--repo", str(repo), "start", "--slice-id", "BL-TEST-004", "--agent-id", "agent-a1b2"],
                cwd=repo,
                expect_code=1,
            )
            assert_contains(completed.stderr, "Another git operation holds")
            assert_contains(completed.stderr, "index.lock")
        finally:
            lock.unlink(missing_ok=True)


def test_handoff_includes_agent_context() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        repo = init_repo(Path(tmp))
        agent_id = "agent-a1b2"
        run(
            ["--repo", str(repo), "start", "--slice-id", "BL-TEST-005", "--agent-id", agent_id],
            cwd=repo,
            expect_code=0,
        )
        worktree = list(repo.joinpath(".worktrees").glob(f"{agent_branch_prefix('BL-TEST-005', agent_id)}*"))[0]

        completed = run(["--repo", str(repo), "handoff", "--worktree", str(worktree)], cwd=repo, expect_code=0)
        assert_contains(completed.stdout, "# StateDD Handoff Snapshot")
        assert_contains(completed.stdout, f"agent_id: {agent_id}")
        assert_contains(completed.stdout, "slice_id: BL-TEST-005")


def test_close_removes_worktree_and_reservation() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        repo = init_repo(Path(tmp))
        agent_id = "agent-a1b2"
        run(
            ["--repo", str(repo), "start", "--slice-id", "BL-TEST-006", "--agent-id", agent_id],
            cwd=repo,
            expect_code=0,
        )
        worktree = list(repo.joinpath(".worktrees").glob(f"{agent_branch_prefix('BL-TEST-006', agent_id)}*"))[0]
        context = json.loads((worktree / ".statedd" / "agent.context").read_text(encoding="utf-8"))
        branch = context["branch"]

        # Make a commit in the worktree so the branch can be pushed.
        (worktree / "feature.txt").write_text("new\n", encoding="utf-8")
        git(worktree, "add", "feature.txt")
        git(worktree, "commit", "-m", "slice commit")

        # Use --dry-run because we cannot actually open a PR in the bare repo.
        completed = run(
            ["--repo", str(repo), "--dry-run", "close", "--worktree", str(worktree), "--pr", "1"],
            cwd=repo,
            expect_code=0,
        )
        assert_contains(completed.stdout, "DRY RUN: would push branch and run remote closure finalizer")

        # Now actually run cleanup to verify removal works.
        completed = run(["--repo", str(repo), "cleanup", "--force", branch], cwd=repo, expect_code=0)
        assert_contains(completed.stdout, "Removed reservation and branch")
        assert not worktree.exists()


def test_close_rejects_context_from_another_worktree_before_push() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        repo = init_repo(Path(tmp))
        for slice_id, agent_id in (("BL-TEST-A", "agent-a111"), ("BL-TEST-B", "agent-b222")):
            run(
                ["--repo", str(repo), "start", "--slice-id", slice_id, "--agent-id", agent_id],
                cwd=repo,
                expect_code=0,
            )
        worktree_a = next(repo.joinpath(".worktrees").glob(f"{agent_branch_prefix('BL-TEST-A', 'agent-a111')}*"))
        worktree_b = next(repo.joinpath(".worktrees").glob(f"{agent_branch_prefix('BL-TEST-B', 'agent-b222')}*"))
        context_a_path = worktree_a / ".statedd" / "agent.context"
        context_b_path = worktree_b / ".statedd" / "agent.context"
        context_a = json.loads(context_a_path.read_text(encoding="utf-8"))
        context_b = json.loads(context_b_path.read_text(encoding="utf-8"))
        before_a = git(repo, "ls-remote", "origin", context_a["branch"])
        before_b = git(repo, "ls-remote", "origin", context_b["branch"])

        context_a_path.write_bytes(context_b_path.read_bytes())
        completed = run(
            ["--repo", str(repo), "close", "--worktree", str(worktree_a), "--pr", "1"],
            cwd=repo,
            expect_code=2,
        )

        assert_contains(completed.stderr, "worktree mismatch")
        assert git(repo, "ls-remote", "origin", context_a["branch"]) == before_a
        assert git(repo, "ls-remote", "origin", context_b["branch"]) == before_b


def test_start_rolls_back_when_reservation_creation_fails() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        repo = init_repo(Path(tmp))
        branch = "bl-rollback-test"
        real_run = orchestrator.run_command

        def fail_reservation(args: list[str], cwd: Path) -> tuple[int, str, str]:
            if args[:4] == ["git", "update-ref", "--create-reflog", "-m"]:
                return 1, "", "injected reservation failure"
            return real_run(args, cwd)

        args = SimpleNamespace(
            repo=str(repo),
            slice_id="BL-ROLLBACK",
            agent_id="agent-rb01",
            branch=branch,
            base="main",
            wait=False,
            dry_run=False,
        )
        with mock.patch.object(orchestrator, "run_command", side_effect=fail_reservation):
            assert orchestrator.cmd_start(args) == 2

        assert git(repo, "branch", "--list", branch) == ""
        assert not (repo / ".worktrees" / branch).exists()
        assert git(repo, "for-each-ref", "--format=%(refname)", orchestrator.reservation_ref(branch)) == ""


def test_close_preserves_reservation_when_worktree_removal_fails() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        repo = init_repo(Path(tmp))
        run(
            ["--repo", str(repo), "start", "--slice-id", "BL-REMOVE", "--agent-id", "agent-rm01"],
            cwd=repo,
            expect_code=0,
        )
        worktree = next(repo.joinpath(".worktrees").glob(f"{agent_branch_prefix('BL-REMOVE', 'agent-rm01')}*"))
        context = json.loads((worktree / ".statedd" / "agent.context").read_text(encoding="utf-8"))
        ref = context["reservation_ref"]
        with mock.patch.object(
            orchestrator,
            "remove_worktree_safe",
            side_effect=RuntimeError("injected removal failure"),
        ):
            code, error = orchestrator.remove_worktree_then_reservation(repo, worktree, ref)
        assert code == 1
        assert "reservation retained" in error
        assert git(repo, "rev-parse", "--verify", ref)


def test_cleanup_removes_stale_worktree() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        repo = init_repo(Path(tmp))
        agent_id = "agent-a1b2"
        run(
            ["--repo", str(repo), "start", "--slice-id", "BL-TEST-007", "--agent-id", agent_id],
            cwd=repo,
            expect_code=0,
        )
        worktree = list(repo.joinpath(".worktrees").glob(f"{agent_branch_prefix('BL-TEST-007', agent_id)}*"))[0]
        context = json.loads((worktree / ".statedd" / "agent.context").read_text(encoding="utf-8"))
        branch = context["branch"]

        # Merge the agent branch to main so it becomes stale.
        git(repo, "merge", "--no-ff", branch, "-m", "merge agent branch")

        completed = run(["--repo", str(repo), "cleanup", "--stale-only"], cwd=repo, expect_code=0)
        assert_contains(completed.stdout, branch)
        assert_contains(completed.stdout, "merged to main")

        completed = run(["--repo", str(repo), "cleanup", "--force", branch], cwd=repo, expect_code=0)
        assert_contains(completed.stdout, "Removed reservation and branch")


def test_existing_audit_passes_in_agent_context() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        repo = init_repo(Path(tmp))
        agent_id = "agent-a1b2"
        run(
            ["--repo", str(repo), "start", "--slice-id", "BL-TEST-008", "--agent-id", agent_id],
            cwd=repo,
            expect_code=0,
        )
        worktree = list(repo.joinpath(".worktrees").glob(f"{agent_branch_prefix('BL-TEST-008', agent_id)}*"))[0]

        # Create evidence folder matching slice_id and a classification table.
        evidence_dir = worktree / "docs" / "evidence" / "bl-test-008"
        evidence_dir.mkdir(parents=True)
        readme = evidence_dir / "README.md"
        readme.write_text(
            """# Evidence

branch: placeholder
head: placeholder
Claims: agent worktree

## Worktree Dirty File Classification

| status | path | category | owner/notes |
| --- | --- | --- | --- |
| ?? | `feature.txt` | intended_slice_work | test |
""",
            encoding="utf-8",
        )
        manifest = evidence_dir / "manifest.json"
        manifest.write_text(
            json.dumps(
                {
                    "schema": "statedd.evidence_manifest.v1",
                    "slice_id": "BL-TEST-008",
                    "manifest_status": "complete",
                    "created_at": "2026-07-07T00:00:00+00:00",
                    "repo": {"branch": "main", "head": "HEAD"},
                    "runtime_identity": {"required": False},
                    "claims": [],
                    "artifacts": [],
                    "redaction": {"status": "checked"},
                },
                indent=2,
            ),
            encoding="utf-8",
        )

        (worktree / "feature.txt").write_text("new\n", encoding="utf-8")
        audit_script = ROOT / "scripts" / "statedd_audit.py"
        completed = subprocess.run(
            [sys.executable, str(audit_script), str(worktree), "--agent-context", str(worktree)],
            cwd=worktree,
            capture_output=True,
            text=True,
            check=False,
        )
        # Audit may warn/fail about state files because this is a temp repo, but it
        # should not fail on worktree_clean when agent context classifies the dirt.
        assert "Worktree is dirty" not in completed.stdout, completed.stdout


def main() -> int:
    tests = [
        test_start_creates_worktree_and_reservation,
        test_double_reserve_same_branch_fails,
        test_start_auto_base_uses_current_branch_when_main_is_absent,
        test_guard_passes_in_agent_worktree_with_dirty_files,
        test_lock_detection_reports_concurrent_git_operation,
        test_handoff_includes_agent_context,
        test_close_removes_worktree_and_reservation,
        test_close_rejects_context_from_another_worktree_before_push,
        test_start_rolls_back_when_reservation_creation_fails,
        test_close_preserves_reservation_when_worktree_removal_fails,
        test_cleanup_removes_stale_worktree,
        test_existing_audit_passes_in_agent_context,
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
