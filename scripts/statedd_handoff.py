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

try:
    from statedd_contracts import ContractError, UnsafePathError, load_json_file, safe_root_path
except ModuleNotFoundError:  # pragma: no cover - pytest package import path
    from scripts.statedd_contracts import ContractError, UnsafePathError, load_json_file, safe_root_path


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
    if not evidence_root.is_dir() or evidence_root.is_symlink():
        return None
    candidates = [
        entry / "README.md"
        for entry in evidence_root.iterdir()
        if entry.is_dir()
        and not entry.is_symlink()
        and not entry.name.startswith(".")
        and (entry / "README.md").is_file()
        and not (entry / "README.md").is_symlink()
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


def load_agent_context(path: Path) -> dict:
    data = load_json_file(path)
    if not isinstance(data, dict):
        raise ContractError("agent context root must be an object")
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
        raise ContractError("agent context is missing required fields")
    if data.get("schema") != AGENT_CONTEXT_SCHEMA:
        raise ContractError("agent context has an unsupported schema")
    for key in required_keys - {"schema"}:
        if not isinstance(data.get(key), str) or not data[key]:
            raise ContractError(f"agent context field {key!r} must be a non-empty string")
    return data


def find_agent_contexts(repo: Path) -> tuple[dict | None, list[dict]]:
    """Return (current_worktree_context, sibling_worktree_contexts)."""
    current_path = default_agent_context_path(repo)
    current = load_agent_context(current_path) if current_path.exists() else None
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
        sibling_path = wt_path / AGENT_CONTEXT_PATH
        if not sibling_path.exists():
            continue
        try:
            siblings.append(load_agent_context(sibling_path))
        except ContractError:
            # Sibling corruption must not hide current-worktree truth. Its owner
            # will fail when handing off from that worktree.
            continue
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


def remote_branch_head(repo: Path, branch: str) -> str:
    if branch == "not proven":
        return "not proven"
    code, stdout, _ = run_command(
        ["git", "ls-remote", "origin", f"refs/heads/{branch}"], repo
    )
    if code != 0 or not stdout:
        return "not proven"
    rows = [line.split("\t", 1) for line in stdout.splitlines() if "\t" in line]
    matches = [sha for sha, ref in rows if ref == f"refs/heads/{branch}"]
    return matches[0] if len(matches) == 1 else "not proven"


def selected_evidence(repo: Path, agent_context: dict | None) -> Path | None:
    if not agent_context:
        return None
    evidence_root = repo / "docs" / "evidence"
    if not evidence_root.is_dir() or evidence_root.is_symlink():
        return None
    matches: list[Path] = []
    for entry in evidence_root.iterdir():
        manifest = entry / "manifest.json"
        if entry.is_symlink() or not entry.is_dir() or manifest.is_symlink() or not manifest.is_file():
            continue
        try:
            payload = load_json_file(manifest)
        except ContractError:
            continue
        if isinstance(payload, dict) and payload.get("slice_id") == agent_context.get("slice_id"):
            matches.append(entry)
    return matches[0] if len(matches) == 1 else None


def first_next_action(repo: Path) -> str:
    path = repo / "NEXT_ACTIONS.md"
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return "not proven"
    for line in text.splitlines():
        if line.startswith("### "):
            return line.removeprefix("### ").strip()
    return "not found"


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
    try:
        repo = safe_root_path(args.repo, must_exist=True)
    except UnsafePathError as exc:
        print(f"Handoff refused: {exc}")
        return 1
    now = dt.datetime.now(dt.timezone.utc).astimezone().isoformat(timespec="seconds")

    branch = git_value(repo, ["rev-parse", "--abbrev-ref", "HEAD"])
    head = git_value(repo, ["rev-parse", "HEAD"])
    origin_url = git_value(repo, ["remote", "get-url", "origin"])
    upstream_branch = git_value(repo, ["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"])
    upstream_head = "not proven"
    if upstream_branch != "not proven":
        upstream_head = git_value(repo, ["rev-parse", "@{u}"])
    local_equals_tracking_ref = head_equals_upstream(head, upstream_head)
    direct_remote_head = remote_branch_head(repo, branch)
    local_equals_remote = head_equals_upstream(head, direct_remote_head)
    verification_failed = False
    short_status = git_value(repo, ["status", "--short"], fallback="")
    worktree = "clean" if not short_status.strip() else "dirty"
    changed_files = git_changed_files(repo)
    context_error: str | None = None
    try:
        agent_context, sibling_contexts = find_agent_contexts(repo)
    except ContractError as exc:
        agent_context, sibling_contexts = None, []
        context_error = str(exc)
        verification_failed = True
    topology_captured, topology_raw, linked_worktrees = worktree_topology(repo)
    dirty_classified = dirty_classification_status(repo, changed_files)
    evidence = selected_evidence(repo, agent_context)
    next_action = first_next_action(repo)
    if changed_files or local_equals_remote == "no":
        local_only_claimed = "yes"
    elif local_equals_remote == "yes":
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
    print(f"- local remote-tracking ref parity: {local_equals_tracking_ref}")
    print(f"- direct remote branch HEAD: {direct_remote_head}")
    print(f"- local HEAD equals direct remote branch: {local_equals_remote}")
    print(f"- worktree: {worktree}")
    print(f"- dirty files classified: {dirty_classified}")
    print("- GitHub-visible deliverables: not proven by this helper; use the remote closure finalizer")
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
    elif context_error:
        print()
        print("## Agent Context")
        print()
        print(f"- invalid active context: {context_error}")
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
    print("## Evidence and Continuation")
    print()
    if evidence:
        print(f"- selected evidence ref: {evidence.relative_to(repo)}")
        print(f"- selected evidence absolute path: {evidence.resolve()}")
    else:
        print("- selected evidence ref: not proven")
        print("- selected evidence absolute path: not proven")
    print(f"- next action: {next_action}")
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
        for command in args.test_command:
            code, output = run_shell_command(command, repo)
            verification_failed = verification_failed or code != 0
            print(f"- command: {shlex.quote(command)}")
            print(f"  exit: {code}")
            if output:
                print("  output:")
                for line in trim_lines(output, args.max_output_lines):
                    print(f"    {line}")
            else:
                print("  output: none")
        if verification_failed:
            print()
            print("At least one verification command failed.")

    if args.run_audit:
        print()
        print("## StateDD Audit")
        print()
        audit_script = repo / "scripts" / "statedd_audit.py"
        if audit_script.exists():
            code, output, _ = run_command([sys.executable, str(audit_script)], repo)
            verification_failed = verification_failed or code != 0
            print(f"- audit exit code: {code}")
            for line in trim_lines(output, args.max_output_lines):
                print(f"  {line}")
        else:
            print("- scripts/statedd_audit.py not found")
            verification_failed = True

    print()
    print("## Handoff Reminder")
    print()
    print("- Use prompts/FINAL_HANDOFF_TEMPLATE.md for the final human-facing handoff.")
    print("- Attach evidence refs from docs/EVIDENCE_LOG.md when user-facing behavior was verified.")
    print("- Keep unresolved searches as `not found`, `not currently locatable`, or `not proven`.")
    print()
    print("## Residual / Partial Risks")
    print()
    if changed_files:
        print("- worktree is dirty; changes are local worktree truth only")
    if local_equals_remote != "yes":
        print("- exact local-to-remote branch parity is not proven")
    print("- PR, CI, runtime, and human acceptance are not proven by this helper")
    if context_error:
        print(f"- active agent context is invalid: {context_error}")
    print()
    print("## CTO-Pasteable Handoff")
    print()
    boundary = "pushed" if not changed_files and local_equals_remote == "yes" else "local-only or unverified"
    print(
        f"Repo {repo} on {branch} at {head}: boundary={boundary}; "
        f"worktree={worktree}; evidence={evidence.relative_to(repo) if evidence else 'not proven'}; "
        f"next={next_action}; PR/CI/runtime/acceptance remain separately unproven."
    )

    return 1 if verification_failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
