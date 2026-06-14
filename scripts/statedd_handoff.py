#!/usr/bin/env python3
"""Print a read-only StateDD handoff snapshot."""

from __future__ import annotations

import argparse
import datetime as dt
import shlex
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


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
        return stderr or fallback
    return stdout or fallback


def git_changed_files(repo: Path) -> list[str]:
    status = git_value(repo, ["status", "--short"], fallback="")
    return [line.strip() for line in status.splitlines() if line.strip()]


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

    branch = git_value(repo, ["rev-parse", "--abbrev-ref", "HEAD"])
    head = git_value(repo, ["rev-parse", "HEAD"])
    short_status = git_value(repo, ["status", "--short"], fallback="")
    worktree = "clean" if not short_status.strip() else "dirty"
    changed_files = git_changed_files(repo)

    print("# StateDD Handoff Snapshot")
    print()
    print(f"Generated: {now}")
    print()
    print("## Repo Identity")
    print()
    print(f"- repo path: {repo}")
    print(f"- branch: {branch}")
    print(f"- head: {head}")
    print(f"- worktree: {worktree}")
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
        else:
            print("- scripts/statedd_audit.py not found")

    print()
    print("## Handoff Reminder")
    print()
    print("- Use prompts/FINAL_HANDOFF_TEMPLATE.md for the final human-facing handoff.")
    print("- Attach evidence refs from docs/EVIDENCE_LOG.md when user-facing behavior was verified.")
    print("- Keep unresolved searches as `not found`, `not currently locatable`, or `not proven`.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
