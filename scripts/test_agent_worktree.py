#!/usr/bin/env python3
"""Regression tests for the ProjectState strong-isolation orchestrator."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ORCHESTRATOR = ROOT / "scripts" / "projectstate_agent_worktree.py"

# Integration subprocesses must never inherit ambient machine session state:
# a stale read-only latch in the shared default Git-safety state root otherwise
# fails these regressions spuriously. The legacy variable points at a decoy
# root holding an ambient latch so a precedence regression fails loudly here.
GIT_SAFETY_STATE_ENV: dict[str, str] = {}


def isolate_git_safety_state(root: Path) -> tuple[Path, Path]:
    isolated = root / "git-safety-state"
    decoy = root / "ambient-git-safety-state"
    decoy.mkdir(mode=0o700)
    decoy_latch = decoy / "global.latch.json"
    payload = {
        "schema": "projectstate.git_safety_latch.v1",
        "blockers": ["ambient decoy latch from a concurrent session"],
        "restart_required": True,
    }
    decoy_latch.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    GIT_SAFETY_STATE_ENV.clear()
    GIT_SAFETY_STATE_ENV.update(
        {
            "PROJECTSTATE_GIT_SAFETY_STATE_ROOT": str(isolated),
            "STATEDD_GIT_SAFETY_STATE_ROOT": str(decoy),
        }
    )
    return isolated, decoy


if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from projectstate_workspace_inventory import normalize_remote  # noqa: E402
from projectstate_validate_schema import validate_json_schema  # noqa: E402


def run(args: list[str], *, cwd: Path, expect_code: int | None = None) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment.update(GIT_SAFETY_STATE_ENV)
    environment.setdefault(
        "STATEDD_WORKSPACE_ROOT",
        str(cwd.parent / ".projectstate-test-workspaces"),
    )
    completed = subprocess.run(
        [sys.executable, str(ORCHESTRATOR), *args],
        cwd=cwd,
        env=environment,
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
    isolate_git_safety_state(root)
    repo = root / "repo"
    repo.mkdir()
    git(repo, "init", "-b", "main")
    git(repo, "config", "user.email", "projectstate@example.invalid")
    git(repo, "config", "user.name", "ProjectState Test")
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
        context = json.loads((clone / ".projectstate" / "agent.context").read_text(encoding="utf-8"))
        assert context["schema"] == "projectstate.agent_context.v2"
        assert context["isolation_mode"] == "clone"
        assert context["reservation_ref"] == ""
        assert context["branch"].startswith(agent_branch_prefix("BL-TEST-001", agent_id))
        assert context["git_safety"]["mutation_permitted"] is True
        source_common = Path(git(repo, "rev-parse", "--git-common-dir")).resolve()
        clone_common_raw = Path(git(clone, "rev-parse", "--git-common-dir"))
        clone_common = clone_common_raw if clone_common_raw.is_absolute() else (clone / clone_common_raw).resolve()
        assert clone_common != source_common
        assert ".projectstate-test-workspaces" in clone.parts
        assert clone.parent.name == "active"
        alternates = clone_common / "objects" / "info" / "alternates"
        assert not alternates.exists() or not alternates.read_text(encoding="utf-8").strip()


def test_resume_clones_existing_remote_branch_at_exact_head() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        repo = init_repo(Path(tmp))
        branch = "agent/bl-006-feedback-policy-v2"
        git(repo, "switch", "-c", branch)
        (repo / "resume.txt").write_text("resume me\n", encoding="utf-8")
        git(repo, "add", "resume.txt")
        git(repo, "commit", "-m", "resume branch")
        expected_head = git(repo, "rev-parse", "HEAD")
        git(repo, "push", "-u", "origin", branch)
        git(repo, "switch", "main")

        completed = run(
            [
                "--repo",
                str(repo),
                "start",
                "--slice-id",
                "BL-RESUME-001",
                "--agent-id",
                "agent-a1b2",
                "--resume",
                "--branch",
                branch,
                "--expected-head",
                expected_head,
            ],
            cwd=repo,
            expect_code=0,
        )
        clone = Path(next(line.split(":", 1)[1].strip() for line in completed.stdout.splitlines() if line.startswith("Agent clone ready:")))
        context = json.loads((clone / ".projectstate" / "agent.context").read_text(encoding="utf-8"))
        assert context["branch"] == branch
        assert context["base_branch"] == "origin/main"
        assert git(clone, "rev-parse", "HEAD") == expected_head
        assert (clone / "resume.txt").read_text(encoding="utf-8") == "resume me\n"
        assert "Resumed remote branch head: " + expected_head in completed.stdout
        assert git(repo, "branch", "--show-current") == "main"


def test_resume_head_mismatch_fails_before_creating_managed_clone() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        repo = init_repo(Path(tmp))
        branch = "agent/resume-mismatch"
        git(repo, "switch", "-c", branch)
        (repo / "resume.txt").write_text("remote\n", encoding="utf-8")
        git(repo, "add", "resume.txt")
        git(repo, "commit", "-m", "resume branch")
        git(repo, "push", "-u", "origin", branch)
        git(repo, "switch", "main")

        completed = run(
            [
                "--repo",
                str(repo),
                "start",
                "--slice-id",
                "BL-RESUME-002",
                "--agent-id",
                "agent-a1b2",
                "--resume",
                "--branch",
                branch,
                "--expected-head",
                "0" * 40,
            ],
            cwd=repo,
            expect_code=1,
        )
        assert "expected head" in completed.stderr
        assert not (Path(tmp) / ".projectstate-test-workspaces").exists()


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
        context = json.loads((worktree / ".projectstate" / "agent.context").read_text(encoding="utf-8"))
        assert context["isolation_mode"] == "worktree"
        assert context["reservation_ref"].startswith("refs/projectstate/reservations/")
        assert git(repo, "rev-parse", context["reservation_ref"])
        assert git(worktree, "check-ignore", ".projectstate/agent.context") == ".projectstate/agent.context"


def test_duplicate_worktree_reservation_fails_without_cleanup() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        repo = init_repo(Path(tmp))
        worktree = start_worktree(repo, "BL-TEST-004", "agent-a1b2")
        context = json.loads((worktree / ".projectstate" / "agent.context").read_text(encoding="utf-8"))
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
        assert_contains(completed.stdout, "# ProjectState Handoff Snapshot")
        assert_contains(completed.stdout, "agent_id: agent-a1b2")
        assert_contains(completed.stdout, "slice_id: BL-TEST-007")


def test_close_dry_run_retains_clone() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        repo = init_repo(Path(tmp))
        clone = start_clone(repo, "BL-TEST-008", "agent-a1b2")
        context_before = (clone / ".projectstate" / "agent.context").read_bytes()
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
        assert (clone / ".projectstate" / "agent.context").read_bytes() == context_before


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
        context = json.loads((worktree / ".projectstate" / "agent.context").read_text(encoding="utf-8"))
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
                    "schema": "projectstate.evidence_manifest.v1",
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
                str(ROOT / "scripts" / "projectstate_audit.py"),
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


def test_forged_context_unknown_field_is_rejected() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        repo = init_repo(Path(tmp))
        clone = start_clone(repo, "BL-TEST-012", "agent-a1b2")
        context_path = clone / ".projectstate" / "agent.context"
        context = json.loads(context_path.read_text(encoding="utf-8"))
        context["forged"] = True
        context_path.write_text(json.dumps(context), encoding="utf-8")
        completed = run(["--repo", str(repo), "guard", "--worktree", str(clone)], cwd=repo, expect_code=2)
        assert_contains(completed.stderr, "closed-world")


def test_copied_context_from_another_clone_is_rejected() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        repo = init_repo(Path(tmp))
        first = start_clone(repo, "BL-TEST-013", "agent-a1b2")
        second = start_clone(repo, "BL-TEST-014", "agent-c3d4")
        source_context = (first / ".projectstate" / "agent.context").read_text(encoding="utf-8")
        (second / ".projectstate" / "agent.context").write_text(source_context, encoding="utf-8")
        completed = run(["--repo", str(repo), "guard", "--worktree", str(second)], cwd=repo, expect_code=1)
        assert_contains(completed.stderr, "worktree_path")


def test_symlinked_context_path_is_rejected() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        repo = init_repo(Path(tmp))
        clone = start_clone(repo, "BL-TEST-015", "agent-a1b2")
        link = Path(tmp) / "clone-link"
        link.symlink_to(clone, target_is_directory=True)
        completed = run(["--repo", str(repo), "guard", "--worktree", str(link)], cwd=repo, expect_code=2)
        assert_contains(completed.stderr, "symlink")


def test_close_requires_explicit_remote_mutation_authorization() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        repo = init_repo(Path(tmp))
        clone = start_clone(repo, "BL-TEST-016", "agent-a1b2")
        completed = run(["--repo", str(repo), "close", "--worktree", str(clone), "--pr", "1"], cwd=repo, expect_code=1)
        assert_contains(completed.stderr, "Remote push is disabled by default")
        assert clone.exists()


def test_dirty_close_cannot_reach_push_path() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        repo = init_repo(Path(tmp))
        clone = start_clone(repo, "BL-TEST-017", "agent-a1b2")
        (clone / "dirty.txt").write_text("preserve\n", encoding="utf-8")
        completed = run(
            [
                "--repo", str(repo), "close", "--worktree", str(clone), "--pr", "1",
                "--remote-mutation", "--operator-authorized",
            ],
            cwd=repo,
            expect_code=1,
        )
        assert "clean worktree" in completed.stderr.lower() or "write probes" in completed.stderr.lower()
        assert clone.exists()
        assert (clone / "dirty.txt").exists()


def test_nested_clone_provisioning_is_blocked() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        repo = init_repo(Path(tmp))
        clone = start_clone(repo, "BL-TEST-018", "agent-a1b2")
        completed = run(
            ["--repo", str(clone), "start", "--slice-id", "BL-NESTED-001"],
            cwd=clone,
            expect_code=1,
        )
        assert_contains(completed.stderr, "Nested agent isolation is forbidden")


def test_arbitrary_sibling_clone_target_is_blocked() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        repo = init_repo(Path(tmp))
        target = repo.parent / "surprise-copy"
        completed = run(
            [
                "--repo",
                str(repo),
                "start",
                "--slice-id",
                "BL-TEST-019",
                "--target",
                str(target),
            ],
            cwd=repo,
            expect_code=1,
        )
        assert_contains(completed.stderr, "Arbitrary clone targets are forbidden")
        assert not target.exists()


def test_unmanaged_same_origin_sibling_blocks_start_and_handoff() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        repo = init_repo(Path(tmp))
        sibling = repo.parent / "manual-copy"
        git(repo.parent, "clone", str(repo.parent / "origin.git"), str(sibling))
        start = run(
            ["--repo", str(repo), "start", "--slice-id", "BL-TEST-020"],
            cwd=repo,
            expect_code=1,
        )
        assert_contains(start.stderr, "unmanaged same-origin sibling clone")
        handoff = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "projectstate_handoff.py"), "--repo", str(repo), "--no-include-listeners"],
            cwd=repo,
            env={**os.environ, **GIT_SAFETY_STATE_ENV, "STATEDD_WORKSPACE_ROOT": str(repo.parent / ".projectstate-test-workspaces")},
            capture_output=True,
            text=True,
            check=False,
        )
        assert handoff.returncode == 1, handoff.stdout + handoff.stderr
        assert_contains(handoff.stdout, str(sibling))
        assert_contains(handoff.stdout, "handoff is refused")


def test_clean_clone_release_quarantines_and_proves_original_absent() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        repo = init_repo(Path(tmp))
        clone = start_clone(repo, "BL-TEST-021", "agent-a1b2")
        completed = run(
            [
                "--repo",
                str(repo),
                "release",
                "--worktree",
                str(clone),
                "--validated",
                "--format",
                "json",
            ],
            cwd=repo,
            expect_code=0,
        )
        receipt = json.loads(completed.stdout)
        schema = json.loads(
            (ROOT / "schemas" / "isolation_release.schema.json").read_text(encoding="utf-8")
        )
        assert validate_json_schema(receipt, schema) == []
        assert receipt["released"] is True
        assert receipt["disposition"] == "quarantined"
        assert receipt["original_path"] == str(clone)
        assert receipt["original_path_absent"] is True
        assert receipt["recoverable_state_retained"] is True
        assert not clone.exists()
        assert Path(receipt["quarantine_path"]).is_dir()
        listed = run(["--repo", str(repo), "list"], cwd=repo, expect_code=0)
        assert_contains(listed.stdout, receipt["quarantine_path"])


def test_dirty_clone_release_is_fail_closed_and_retained() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        repo = init_repo(Path(tmp))
        clone = start_clone(repo, "BL-TEST-022", "agent-a1b2")
        (clone / "dirty.txt").write_text("preserve\n", encoding="utf-8")
        completed = run(
            ["--repo", str(repo), "release", "--worktree", str(clone), "--validated"],
            cwd=repo,
            expect_code=1,
        )
        assert_contains(completed.stderr, "release requires a clean worktree")
        assert clone.exists()
        assert (clone / "dirty.txt").read_text(encoding="utf-8") == "preserve\n"


def test_clean_failed_clone_can_be_explicitly_abandoned_to_quarantine() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        repo = init_repo(Path(tmp))
        clone = start_clone(repo, "BL-TEST-024", "agent-a1b2")
        completed = run(
            [
                "--repo",
                str(repo),
                "abandon",
                "--worktree",
                str(clone),
                "--reason",
                "failed_preflight",
                "--format",
                "json",
            ],
            cwd=repo,
            expect_code=0,
        )
        receipt = json.loads(completed.stdout)
        schema = json.loads(
            (ROOT / "schemas" / "isolation_release.schema.json").read_text(encoding="utf-8")
        )
        assert validate_json_schema(receipt, schema) == []
        assert receipt["release_reason"] == "failed_preflight"
        assert receipt["disposition"] == "quarantined"
        assert receipt["original_path_absent"] is True
        assert receipt["recoverable_state_retained"] is True
        assert not clone.exists()
        assert Path(receipt["quarantine_path"]).is_dir()


def test_dirty_clone_abandon_is_fail_closed_and_retained() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        repo = init_repo(Path(tmp))
        clone = start_clone(repo, "BL-TEST-025", "agent-a1b2")
        (clone / "dirty.txt").write_text("preserve\n", encoding="utf-8")
        completed = run(
            [
                "--repo",
                str(repo),
                "abandon",
                "--worktree",
                str(clone),
                "--reason",
                "failed_preflight",
            ],
            cwd=repo,
            expect_code=1,
        )
        assert_contains(completed.stderr, "abandon requires a clean worktree")
        assert clone.exists()
        assert (clone / "dirty.txt").read_text(encoding="utf-8") == "preserve\n"


def test_clean_worktree_release_removes_path_and_reservation_without_force() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        repo = init_repo(Path(tmp))
        worktree = start_worktree(repo, "BL-TEST-023", "agent-a1b2")
        context = json.loads((worktree / ".projectstate" / "agent.context").read_text(encoding="utf-8"))
        completed = run(
            [
                "--repo",
                str(repo),
                "release",
                "--worktree",
                str(worktree),
                "--validated",
                "--format",
                "json",
            ],
            cwd=repo,
            expect_code=0,
        )
        receipt = json.loads(completed.stdout)
        assert receipt["disposition"] == "removed"
        assert receipt["original_path_absent"] is True
        assert receipt["reservation_absent"] is True
        assert not worktree.exists()
        assert context["reservation_ref"] not in git(repo, "show-ref")


def test_remote_identity_normalizes_transport_and_credentials() -> None:
    repo = Path("/tmp/example-repo")
    expected = "remote:github.com/example/ProjectState_Template"
    assert normalize_remote(
        "git@github.com:example/ProjectState_Template.git", repo=repo
    ) == expected
    assert normalize_remote(
        "ssh://git@github.com/example/ProjectState_Template.git", repo=repo
    ) == expected
    assert normalize_remote(
        "https://secret-token@github.com/example/ProjectState_Template.git", repo=repo
    ) == expected


def test_local_remote_identity_resolves_relative_to_repository() -> None:
    repo = Path("/tmp/example/repo")
    assert normalize_remote("../origin.git", repo=repo) == "local:/tmp/example/origin"


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
        test_forged_context_unknown_field_is_rejected,
        test_copied_context_from_another_clone_is_rejected,
        test_symlinked_context_path_is_rejected,
        test_close_requires_explicit_remote_mutation_authorization,
        test_dirty_close_cannot_reach_push_path,
        test_nested_clone_provisioning_is_blocked,
        test_arbitrary_sibling_clone_target_is_blocked,
        test_unmanaged_same_origin_sibling_blocks_start_and_handoff,
        test_clean_clone_release_quarantines_and_proves_original_absent,
        test_dirty_clone_release_is_fail_closed_and_retained,
        test_clean_failed_clone_can_be_explicitly_abandoned_to_quarantine,
        test_dirty_clone_abandon_is_fail_closed_and_retained,
        test_clean_worktree_release_removes_path_and_reservation_without_force,
        test_remote_identity_normalizes_transport_and_credentials,
        test_local_remote_identity_resolves_relative_to_repository,
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
