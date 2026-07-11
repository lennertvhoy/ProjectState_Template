#!/usr/bin/env python3
"""Regression tests for the StateDD strong-isolation orchestrator."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


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
    completed = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        raise AssertionError(
            f"git {' '.join(args)} failed\nstdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )
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
    git(origin, "symbolic-ref", "HEAD", "refs/heads/main")
    git(repo, "remote", "set-head", "origin", "main")
    return repo


def assert_contains(output: str, expected: str) -> None:
    if expected not in output:
        raise AssertionError(f"Expected output to contain {expected!r}, got:\n{output}")


def agent_branch_prefix(slice_id: str, agent_id: str) -> str:
    clean_slice = "".join(char if char.isalnum() else "-" for char in slice_id.lower()).strip("-")
    return f"bl-{clean_slice}-{agent_id[:4].lower()}-"


def start_clone(repo: Path, slice_id: str, agent_id: str) -> Path:
    completed = run(
        ["--repo", str(repo), "start", "--slice-id", slice_id, "--agent-id", agent_id],
        cwd=repo,
        expect_code=0,
    )
    line = next(line for line in completed.stdout.splitlines() if line.startswith("Agent clone ready:"))
    return Path(line.split(":", 1)[1].strip())


def start_worktree(repo: Path, slice_id: str, agent_id: str) -> Path:
    completed = run(
        [
            "--repo",
            str(repo),
            "start",
            "--slice-id",
            slice_id,
            "--agent-id",
            agent_id,
            "--isolation-mode",
            "worktree",
            "--worktree-opt-in",
            "--trusted-local-machine",
        ],
        cwd=repo,
        expect_code=0,
    )
    line = next(line for line in completed.stdout.splitlines() if line.startswith("Agent worktree ready:"))
    return Path(line.split(":", 1)[1].strip())


def test_default_start_creates_independent_clone() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        repo = init_repo(Path(tmp))
        agent_id = "agent-a1b2"
        clone = start_clone(repo, "BL-TEST-001", agent_id)
        context = json.loads((clone / ".statedd" / "agent.context").read_text(encoding="utf-8"))
        assert context["schema"] == "statedd.agent_context.v2"
        assert context["isolation_mode"] == "clone"
        assert context["reservation_ref"] == ""
        assert context["branch"].startswith(agent_branch_prefix("BL-TEST-001", agent_id))
        assert context["git_safety"]["mutation_permitted"] is True
        source_common = Path(git(repo, "rev-parse", "--git-common-dir")).resolve()
        clone_common_raw = Path(git(clone, "rev-parse", "--git-common-dir"))
        clone_common = clone_common_raw if clone_common_raw.is_absolute() else (clone / clone_common_raw).resolve()
        assert clone_common != source_common
        alternates = clone_common / "objects" / "info" / "alternates"
        assert not alternates.exists() or not alternates.read_text(encoding="utf-8").strip()


def test_worktree_creation_is_blocked_without_explicit_opt_in() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        repo = init_repo(Path(tmp))
        completed = run(
            [
                "--repo",
                str(repo),
                "start",
                "--slice-id",
                "BL-TEST-002",
                "--isolation-mode",
                "worktree",
            ],
            cwd=repo,
            expect_code=1,
        )
        assert_contains(completed.stderr, "disabled by default")
        assert ".worktrees" not in git(repo, "status", "--short", "--untracked-files=all")


def test_explicit_same_user_worktree_creates_reservation() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        repo = init_repo(Path(tmp))
        agent_id = "agent-a1b2"
        worktree = start_worktree(repo, "BL-TEST-003", agent_id)
        context = json.loads((worktree / ".statedd" / "agent.context").read_text(encoding="utf-8"))
        assert context["isolation_mode"] == "worktree"
        assert context["reservation_ref"].startswith("refs/statedd/reservations/")
        assert git(repo, "rev-parse", context["reservation_ref"])
        assert git(worktree, "check-ignore", ".statedd/agent.context") == ".statedd/agent.context"


def test_duplicate_worktree_reservation_fails_without_cleanup() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        repo = init_repo(Path(tmp))
        worktree = start_worktree(repo, "BL-TEST-004", "agent-a1b2")
        context = json.loads((worktree / ".statedd" / "agent.context").read_text(encoding="utf-8"))
        completed = run(
            [
                "--repo",
                str(repo),
                "start",
                "--slice-id",
                "BL-TEST-004",
                "--agent-id",
                "agent-a1b2",
                "--branch",
                context["branch"],
                "--isolation-mode",
                "worktree",
                "--worktree-opt-in",
                "--trusted-local-machine",
            ],
            cwd=repo,
            expect_code=1,
        )
        assert_contains(completed.stderr, "Reservation ref already exists")
        assert worktree.exists()
        assert git(repo, "rev-parse", context["reservation_ref"])


def test_dry_run_does_not_create_isolation_path() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        repo = init_repo(Path(tmp))
        before = git(repo, "worktree", "list", "--porcelain")
        completed = run(
            [
                "--repo",
                str(repo),
                "--dry-run",
                "start",
                "--slice-id",
                "CI-SMOKE-001",
                "--agent-id",
                "agent-a1b2",
            ],
            cwd=repo,
            expect_code=0,
        )
        assert_contains(completed.stdout, "no Git or filesystem mutation performed")
        assert git(repo, "worktree", "list", "--porcelain") == before


def test_guard_passes_in_independent_clone_with_dirty_slice_files() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        repo = init_repo(Path(tmp))
        clone = start_clone(repo, "BL-TEST-005", "agent-a1b2")
        (clone / "feature.txt").write_text("new\n", encoding="utf-8")
        completed = run(
            ["--repo", str(repo), "guard", "--worktree", str(clone), "--mode", "start-slice"],
            cwd=repo,
            expect_code=0,
        )
        assert_contains(completed.stdout, "Isolation mode: clone")
        assert_contains(completed.stdout, "Git safety mutation permit: True")
        assert_contains(completed.stdout, "feature.txt")


def test_lock_detection_blocks_opt_in_worktree_without_wait_or_cleanup() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        repo = init_repo(Path(tmp))
        common_raw = Path(git(repo, "rev-parse", "--git-common-dir"))
        common = common_raw if common_raw.is_absolute() else (repo / common_raw).resolve()
        lock = common / "index.lock"
        lock.write_text("", encoding="utf-8")
        try:
            completed = run(
                [
                    "--repo",
                    str(repo),
                    "start",
                    "--slice-id",
                    "BL-TEST-006",
                    "--isolation-mode",
                    "worktree",
                    "--worktree-opt-in",
                    "--trusted-local-machine",
                ],
                cwd=repo,
                expect_code=1,
            )
            assert_contains(completed.stderr, "Another git operation holds")
            assert lock.exists()
        finally:
            lock.unlink()


def test_handoff_includes_clone_agent_context() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        repo = init_repo(Path(tmp))
        clone = start_clone(repo, "BL-TEST-007", "agent-a1b2")
        completed = run(
            ["--repo", str(repo), "handoff", "--worktree", str(clone)],
            cwd=repo,
            expect_code=0,
        )
        assert_contains(completed.stdout, "# StateDD Handoff Snapshot")
        assert_contains(completed.stdout, "agent_id: agent-a1b2")
        assert_contains(completed.stdout, "slice_id: BL-TEST-007")


def test_close_dry_run_retains_clone() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        repo = init_repo(Path(tmp))
        clone = start_clone(repo, "BL-TEST-008", "agent-a1b2")
        context_before = (clone / ".statedd" / "agent.context").read_bytes()
        completed = run(
            [
                "--repo",
                str(repo),
                "--dry-run",
                "close",
                "--worktree",
                str(clone),
                "--pr",
                "1",
            ],
            cwd=repo,
            expect_code=0,
        )
        assert_contains(completed.stdout, "No worktree, clone, branch, or reservation cleanup")
        assert clone.exists()
        assert (clone / ".statedd" / "agent.context").read_bytes() == context_before


def test_cleanup_is_report_only_for_stale_and_dirty_worktrees() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        repo = init_repo(Path(tmp))
        worktree = start_worktree(repo, "BL-TEST-009", "agent-a1b2")
        (worktree / "dirty.txt").write_text("preserve\n", encoding="utf-8")
        topology_before = git(repo, "worktree", "list", "--porcelain")
        completed = run(["--repo", str(repo), "cleanup"], cwd=repo, expect_code=0)
        assert_contains(completed.stdout, "non-mutating")
        assert_contains(completed.stdout, "No automatic deletion")
        assert worktree.exists()
        assert (worktree / "dirty.txt").exists()
        assert git(repo, "worktree", "list", "--porcelain") == topology_before


def test_missing_worktree_is_reported_not_pruned() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        repo = init_repo(Path(tmp))
        worktree = start_worktree(repo, "BL-TEST-010", "agent-a1b2")
        context = json.loads((worktree / ".statedd" / "agent.context").read_text(encoding="utf-8"))
        shutil.rmtree(worktree)
        topology_before = git(repo, "worktree", "list", "--porcelain")
        completed = run(["--repo", str(repo), "cleanup"], cwd=repo, expect_code=0)
        assert_contains(completed.stdout, context["branch"])
        assert git(repo, "worktree", "list", "--porcelain") == topology_before


def test_existing_audit_does_not_treat_clone_context_dirt_as_shared_worktree_dirt() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        repo = init_repo(Path(tmp))
        clone = start_clone(repo, "BL-TEST-011", "agent-a1b2")
        evidence_dir = clone / "docs" / "evidence" / "bl-test-011"
        evidence_dir.mkdir(parents=True)
        (evidence_dir / "README.md").write_text(
            """# Evidence

branch: placeholder
head: placeholder
Claims: isolated clone

## Worktree Dirty File Classification

| status | path | category | owner/notes |
| --- | --- | --- | --- |
| ?? | `feature.txt` | intended_slice_work | test |
""",
            encoding="utf-8",
        )
        (evidence_dir / "manifest.json").write_text(
            json.dumps(
                {
                    "schema": "statedd.evidence_manifest.v1",
                    "slice_id": "BL-TEST-011",
                    "manifest_status": "complete",
                    "created_at": "2026-07-11T00:00:00+00:00",
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
        (clone / "feature.txt").write_text("new\n", encoding="utf-8")
        completed = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "statedd_audit.py"),
                str(clone),
                "--agent-context",
                str(clone),
            ],
            cwd=clone,
            capture_output=True,
            text=True,
            check=False,
        )
        assert "Worktree is dirty" not in completed.stdout, completed.stdout


def main() -> int:
    tests = [
        test_default_start_creates_independent_clone,
        test_worktree_creation_is_blocked_without_explicit_opt_in,
        test_explicit_same_user_worktree_creates_reservation,
        test_duplicate_worktree_reservation_fails_without_cleanup,
        test_dry_run_does_not_create_isolation_path,
        test_guard_passes_in_independent_clone_with_dirty_slice_files,
        test_lock_detection_blocks_opt_in_worktree_without_wait_or_cleanup,
        test_handoff_includes_clone_agent_context,
        test_close_dry_run_retains_clone,
        test_cleanup_is_report_only_for_stale_and_dirty_worktrees,
        test_missing_worktree_is_reported_not_pruned,
        test_existing_audit_does_not_treat_clone_context_dirt_as_shared_worktree_dirt,
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
