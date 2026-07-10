#!/usr/bin/env python3
"""Print a read-only StateDD handoff snapshot."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import shlex
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

AGENT_CONTEXT_SCHEMA = "statedd.agent_context.v1"
AGENT_CONTEXT_PATH = ".statedd/agent.context"


def run_command(args: list[str], cwd: Path) -> tuple[int, str, str]:
    try:
        completed = subprocess.run(
            args,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        return 127, "", str(exc)
    return completed.returncode, completed.stdout.strip(), completed.stderr.strip()


def run_shell_command(command: str, cwd: Path) -> tuple[int, str]:
    completed = subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
        shell=True,
        check=False,
    )
    output = "\n".join(part for part in (completed.stdout.strip(), completed.stderr.strip()) if part)
    return completed.returncode, output


def git_value(repo: Path, args: list[str], fallback: str = "not proven") -> str:
    code, stdout, stderr = run_command(["git", *args], repo)
    if code != 0:
        return fallback
    return stdout or fallback


def git_changed_files(repo: Path) -> list[str]:
    status = git_value(repo, ["status", "--short"], fallback="")
    return [line.strip() for line in status.splitlines() if line.strip()]


def latest_evidence_readme(repo: Path) -> Path | None:
    evidence_root = repo / "docs" / "evidence"
    if not evidence_root.exists():
        return None
    candidates = [
        entry / "README.md"
        for entry in evidence_root.iterdir()
        if entry.is_dir() and not entry.name.startswith(".") and (entry / "README.md").exists()
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda path: path.stat().st_mtime)


def worktree_topology(repo: Path) -> tuple[bool, str, list[str]]:
    code, stdout, _ = run_command(["git", "worktree", "list", "--porcelain"], repo)
    if code != 0:
        return False, "", []
    linked: list[str] = []
    for line in stdout.splitlines():
        if not line.startswith("worktree "):
            continue
        path = line.removeprefix("worktree ").strip()
        if path and Path(path).resolve() != repo:
            linked.append(path)
    return True, stdout, linked


def default_agent_context_path(repo: Path) -> Path:
    return repo / AGENT_CONTEXT_PATH


def load_agent_context(path: Path) -> dict | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    required_keys = {
        "schema",
        "agent_id",
        "slice_id",
        "reservation_ref",
        "worktree_path",
        "branch",
        "base_branch",
    }
    if not required_keys.issubset(data.keys()):
        return None
    if data.get("schema") != AGENT_CONTEXT_SCHEMA:
        return None
    return data


def find_agent_contexts(repo: Path) -> tuple[dict | None, list[dict]]:
    """Return (current_worktree_context, sibling_worktree_contexts)."""
    current = load_agent_context(default_agent_context_path(repo))
    siblings: list[dict] = []
    code, stdout, _ = run_command(["git", "worktree", "list", "--porcelain"], repo)
    if code != 0:
        return current, siblings
    for line in stdout.splitlines():
        if not line.startswith("worktree "):
            continue
        wt_path = Path(line.removeprefix("worktree ").strip()).resolve()
        if wt_path == repo:
            continue
        ctx = load_agent_context(wt_path / AGENT_CONTEXT_PATH)
        if ctx:
            siblings.append(ctx)
    return current, siblings


def dirty_classification_status(repo: Path, changed_files: list[str]) -> str:
    if not changed_files:
        return "not applicable"
    readme = latest_evidence_readme(repo)
    if readme is None:
        return "no"
    try:
        text = readme.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return "no"
    return "yes" if "Worktree Dirty File Classification" in text else "no"


def head_equals_upstream(local_head: str, upstream_head: str) -> str:
    if local_head == "not proven" or upstream_head == "not proven":
        return "not proven"
    return "yes" if local_head == upstream_head else "no"


def github_visible_deliverables(local_equals_upstream: str, changed_files: list[str]) -> str:
    if changed_files:
        return "no"
    if local_equals_upstream == "yes":
        return "yes"
    if local_equals_upstream == "no":
        return "no"
    return "not proven"


def active_listeners(repo: Path) -> tuple[str, list[str]]:
    if shutil.which("ss"):
        code, stdout, stderr = run_command(["ss", "-ltnp"], repo)
        if code == 0 and stdout:
            return "ss -ltnp", stdout.splitlines()[:30]
        return "ss -ltnp", [stderr or "not found"]

    if shutil.which("lsof"):
        code, stdout, stderr = run_command(["lsof", "-nP", "-iTCP", "-sTCP:LISTEN"], repo)
        if code == 0 and stdout:
            return "lsof -nP -iTCP -sTCP:LISTEN", stdout.splitlines()[:30]
        return "lsof -nP -iTCP -sTCP:LISTEN", [stderr or "not found"]

    return "listener scan", ["not currently locatable: neither `ss` nor `lsof` is available"]


def trim_lines(text: str, max_lines: int) -> list[str]:
    lines = text.splitlines()
    if len(lines) <= max_lines:
        return lines
    omitted = len(lines) - max_lines
    return [*lines[:max_lines], f"... truncated {omitted} line(s)"]


def print_list(items: list[str], empty: str = "not found") -> None:
    if not items:
        print(f"- {empty}")
        return
    for item in items:
        print(f"- {item}")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Print a read-only StateDD handoff snapshot")
    parser.add_argument("--repo", default=str(ROOT), help="Repo root to inspect")
    parser.add_argument(
        "--test-command",
        action="append",
        default=[],
        help="Command to run and include in the verification section; can be repeated",
    )
    parser.add_argument(
        "--include-listeners",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Include active TCP listener scan when `ss` or `lsof` is available",
    )
    parser.add_argument(
        "--run-audit",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Run scripts/statedd_audit.py and include its output",
    )
    parser.add_argument("--max-output-lines", type=int, default=80, help="Max lines to print per test command")
    return parser.parse_args(argv[1:])


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv)
    repo = Path(args.repo).resolve()
    now = dt.datetime.now(dt.timezone.utc).astimezone().isoformat(timespec="seconds")
    handoff_exit = 0

    branch = git_value(repo, ["rev-parse", "--abbrev-ref", "HEAD"])
    head = git_value(repo, ["rev-parse", "HEAD"])
    origin_url = git_value(repo, ["remote", "get-url", "origin"])
    upstream_branch = git_value(repo, ["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"])
    upstream_head = "not proven"
    if upstream_branch != "not proven":
        upstream_head = git_value(repo, ["rev-parse", "@{u}"])
    local_equals_upstream = head_equals_upstream(head, upstream_head)
    short_status = git_value(repo, ["status", "--short"], fallback="")
    worktree = "clean" if not short_status.strip() else "dirty"
    changed_files = git_changed_files(repo)
    agent_context, sibling_contexts = find_agent_contexts(repo)
    topology_captured, topology_raw, linked_worktrees = worktree_topology(repo)
    dirty_classified = dirty_classification_status(repo, changed_files)
    github_visible = github_visible_deliverables(local_equals_upstream, changed_files)
    if changed_files or local_equals_upstream == "no":
        local_only_claimed = "yes"
    elif local_equals_upstream == "yes":
        local_only_claimed = "no"
    else:
        local_only_claimed = "not proven"

    print("# StateDD Handoff Snapshot")
    print()
    print(f"Generated: {now}")
    print()
    print("## Repo Identity")
    print()
    print(f"- repo path: {repo}")
    print(f"- branch: {branch}")
    print(f"- head: {head}")
    print(f"- origin remote URL: {origin_url}")
    print(f"- upstream branch: {upstream_branch}")
    print(f"- upstream HEAD: {upstream_head}")
    print(f"- local HEAD: {head}")
    print(f"- local HEAD equals upstream: {local_equals_upstream}")
    print(f"- worktree: {worktree}")
    print(f"- dirty files classified: {dirty_classified}")
    print(f"- GitHub-visible deliverables: {github_visible}")
    print(f"- local-only files claimed: {local_only_claimed}")
    if agent_context:
        print()
        print("## Agent Context")
        print()
        print(f"- agent_id: {agent_context['agent_id']}")
        print(f"- slice_id: {agent_context['slice_id']}")
        print(f"- worktree_path: {agent_context.get('worktree_path', 'not proven')}")
        print(f"- reservation_ref: {agent_context.get('reservation_ref', 'not proven')}")
        owner = "self"
        expected_path = agent_context.get("worktree_path")
        if expected_path:
            try:
                if Path(expected_path).resolve() != repo:
                    owner = "other"
            except OSError:
                owner = "other"
        print(f"- worktree_owner: {owner}")
        if sibling_contexts:
            print("- sibling agent worktrees:")
            for ctx in sibling_contexts:
                print(
                    f"  - {ctx.get('worktree_path', 'not proven')} "
                    f"({ctx.get('agent_id', 'unknown')}/{ctx.get('slice_id', 'unknown')})"
                )
    print()
    print("## Worktree Topology")
    print()
    print(f"- worktree topology captured: {'yes' if topology_captured else 'no'}")
    print(f"- current worktree path: {repo}")
    if linked_worktrees:
        print("- linked worktrees:")
        for path in linked_worktrees:
            print(f"  - {path}")
    else:
        print("- linked worktrees: none")
    print("- git worktree list --porcelain:")
    if topology_raw:
        for line in trim_lines(topology_raw, 40):
            print(f"  {line}")
    else:
        print("  not proven")
    print()
    print("## Changed Files")
    print()
    print_list(changed_files, empty="none")
    print()
    print("## Runtime Identity")
    print()
    print("- process/container: not proven by this helper")
    print("- port/base URL: not proven by this helper")
    print("- rebuilt in this slice: not proven by this helper")
    print("- duplicate runtimes checked: not proven by this helper")

    if args.include_listeners:
        command_label, listeners = active_listeners(repo)
        print(f"- active listener source: {command_label}")
        for line in listeners:
            print(f"  - {line}")

    print()
    print("## Direct Verification")
    print()
    if not args.test_command:
        print("- not run by this helper; pass `--test-command` to include command output")
    else:
        failed = False
        for command in args.test_command:
            code, output = run_shell_command(command, repo)
            failed = failed or code != 0
            print(f"- command: {shlex.quote(command)}")
            print(f"  exit: {code}")
            if output:
                print("  output:")
                for line in trim_lines(output, args.max_output_lines):
                    print(f"    {line}")
            else:
                print("  output: none")
        if failed:
            print()
            print("At least one verification command failed.")
            handoff_exit = 1

    if args.run_audit:
        print()
        print("## StateDD Audit")
        print()
        audit_script = repo / "scripts" / "statedd_audit.py"
        if audit_script.exists():
            code, output, _ = run_command([sys.executable, str(audit_script)], repo)
            print(f"- audit exit code: {code}")
            for line in trim_lines(output, args.max_output_lines):
                print(f"  {line}")
            if code != 0:
                handoff_exit = 1
        else:
            print("- scripts/statedd_audit.py not found")
            handoff_exit = 1

    print()
    print("## Handoff Reminder")
    print()
    print("- Use prompts/FINAL_HANDOFF_TEMPLATE.md for the final human-facing handoff.")
    print("- Attach evidence refs from docs/EVIDENCE_LOG.md when user-facing behavior was verified.")
    print("- Keep unresolved searches as `not found`, `not currently locatable`, or `not proven`.")

    return handoff_exit


if __name__ == "__main__":
    raise SystemExit(main())
