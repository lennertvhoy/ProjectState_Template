#!/usr/bin/env python3
"""End-to-end regression for the agent-operated downstream golden path."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run(args: list[str], cwd: Path, *, expected: int = 0) -> str:
    completed = subprocess.run(args, cwd=cwd, capture_output=True, text=True, check=False)
    if completed.returncode != expected:
        raise AssertionError(
            f"Command failed: {' '.join(args)}\n"
            f"expected={expected} actual={completed.returncode}\n"
            f"stdout:\n{completed.stdout}\n"
            f"stderr:\n{completed.stderr}"
        )
    return completed.stdout.strip()


def git(repo: Path, *args: str, expected: int = 0) -> str:
    return run(["git", *args], repo, expected=expected)


def commit(repo: Path, message: str) -> str:
    git(repo, "add", "-A")
    git(repo, "commit", "-m", message)
    return git(repo, "rev-parse", "HEAD")


def start_agent(repo: Path, slice_id: str, agent_id: str) -> tuple[Path, str]:
    output = run(
        [
            sys.executable,
            str(repo / "scripts" / "statedd_agent_worktree.py"),
            "--repo",
            str(repo),
            "start",
            "--slice-id",
            slice_id,
            "--agent-id",
            agent_id,
        ],
        repo,
    )
    line = next(line for line in output.splitlines() if line.startswith("Agent clone ready:"))
    clone = Path(line.split(":", 1)[1].strip())
    context = json.loads((clone / ".statedd" / "agent.context").read_text(encoding="utf-8"))
    git(clone, "config", "user.email", f"{agent_id}@example.invalid")
    git(clone, "config", "user.name", f"StateSpec {agent_id}")
    return clone, context["branch"]


def test_golden_path() -> None:
    with tempfile.TemporaryDirectory(prefix="statedd-golden-path-") as tmp:
        root = Path(tmp)
        template_clone = root / "template-source"
        downstream = root / "downstream"
        remote = root / "downstream.git"

        # Exercise the public materialization shape: a temporary template clone
        # is the source, and the downstream target starts without Git metadata.
        run(["git", "clone", "--no-local", str(ROOT), str(template_clone)], root)
        # Keep the regression runnable before the maintainer commits the slice:
        # a real public clone is clean, while this local test may contain the
        # candidate changes that the clone must exercise.
        changed = set(git(ROOT, "diff", "--name-only", "HEAD").splitlines())
        changed.update(git(ROOT, "ls-files", "--others", "--exclude-standard").splitlines())
        for relpath in changed:
            source = ROOT / relpath
            destination = template_clone / relpath
            if source.is_file():
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, destination)
        source_head = git(template_clone, "rev-parse", "HEAD")
        run(
            [
                sys.executable,
                str(template_clone / "scripts" / "init_template.py"),
                "new",
                "--name",
                "Golden Path Demo",
                "--profile",
                "team",
                "--target",
                str(downstream),
            ],
            template_clone,
        )

        if not (downstream / ".git").is_dir():
            raise AssertionError("new-project materialization did not initialize Git metadata")
        if git(downstream, "branch", "--show-current") != "main":
            raise AssertionError("new-project materialization did not initialize main")
        inherited = subprocess.run(
            ["git", "cat-file", "-e", f"{source_head}^{{commit}}"],
            cwd=downstream,
            capture_output=True,
            text=True,
            check=False,
        )
        if inherited.returncode == 0:
            raise AssertionError("downstream repository inherited template Git history")
        for forbidden in (
            "scripts/test_init_template.py",
            "fixtures",
            "docs/evidence",
            "docs/incidents/20260711-141533-git-object-ownership-permission.md",
        ):
            candidate = downstream / forbidden
            leaked = candidate.is_file() or (
                candidate.is_dir()
                and any(path.is_file() and path.name != ".gitkeep" for path in candidate.rglob("*"))
            )
            if leaked:
                raise AssertionError(f"template-maintenance payload leaked: {forbidden}")

        run([sys.executable, str(downstream / "scripts" / "statedd_validate_schema.py"), str(downstream)], downstream)
        run([sys.executable, str(downstream / "scripts" / "check_state_docs.py"), str(downstream)], downstream)

        git(downstream, "config", "user.email", "statedd-golden@example.invalid")
        git(downstream, "config", "user.name", "StateSpec Golden Path")
        git(root, "init", "--bare", str(remote))
        git(downstream, "remote", "add", "origin", str(remote))
        commit(downstream, "bootstrap: establish golden-path baseline")
        git(downstream, "push", "-u", "origin", "main")
        git(remote, "symbolic-ref", "HEAD", "refs/heads/main")
        git(downstream, "remote", "set-head", "origin", "main")

        agent_a, branch_a = start_agent(downstream, "BL-GOLDEN-PATH-001", "agent-a111")
        agent_b, branch_b = start_agent(downstream, "BL-GOLDEN-PATH-001", "agent-b222")
        (agent_a / "subagent-a.txt").write_text("independent package A\n", encoding="utf-8")
        (agent_b / "subagent-b.txt").write_text("independent package B\n", encoding="utf-8")
        commit_a = commit(agent_a, "feat: integrate package A")
        commit_b = commit(agent_b, "feat: integrate package B")
        git(agent_a, "push", "origin", f"HEAD:refs/heads/{branch_a}")
        git(agent_b, "push", "origin", f"HEAD:refs/heads/{branch_b}")

        integration_branch = "bl-golden-path-001-integration"
        git(downstream, "switch", "-c", integration_branch)
        git(downstream, "fetch", "origin", branch_a, branch_b)
        git(downstream, "merge", "--no-ff", "--no-edit", f"origin/{branch_a}")
        git(downstream, "merge", "--no-ff", "--no-edit", f"origin/{branch_b}")
        state = (downstream / "PROJECT_STATE.yaml").read_text(encoding="utf-8")
        state = state.replace("status: proposed_default", "status: confirmed", 1)
        state = state.replace("confirmation: pending_during_bootstrap", "confirmation: human_confirmed", 1)
        (downstream / "PROJECT_STATE.yaml").write_text(state, encoding="utf-8")
        integration_head = commit(downstream, "chore: record integrated delivery policy")
        git(downstream, "push", "-u", "origin", f"HEAD:refs/heads/{integration_branch}")

        remote_head = git(remote, "show-ref", "--hash", f"refs/heads/{integration_branch}")
        if remote_head != integration_head:
            raise AssertionError("final remote integration branch does not contain exact local HEAD")
        if commit_a not in git(downstream, "log", "--all", "--format=%H"):
            raise AssertionError("integration branch does not contain subagent A commit")
        if commit_b not in git(downstream, "log", "--all", "--format=%H"):
            raise AssertionError("integration branch does not contain subagent B commit")
        if git(downstream, "status", "--short"):
            raise AssertionError("golden-path integration worktree is not clean")

        handoff = run(
            [
                sys.executable,
                str(downstream / "scripts" / "statedd_handoff.py"),
                "--repo",
                str(downstream),
                "--no-include-listeners",
            ],
            downstream,
        )
        for phrase in (
            "## Remote-First Status",
            f"- exact local HEAD: {integration_head}",
            f"- remote branch HEAD: {integration_head}",
            "- remote contains exact local HEAD: yes",
            "- delivery status: pushed",
        ):
            if phrase not in handoff:
                raise AssertionError(f"handoff is missing remote proof: {phrase}")


if __name__ == "__main__":
    test_golden_path()
    print("PASS test_golden_path")
