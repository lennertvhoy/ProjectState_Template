#!/usr/bin/env python3
"""Capture durable browser evidence with the Playwright CLI.

This is the concrete Playwright provider for the provider-agnostic browser
verification contract.  It deliberately invokes the installed Playwright CLI
instead of importing a project-specific browser library, so downstream repos
can opt in without adding a Python dependency to the ProjectState template.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
BROWSER_VERIFY = ROOT / "scripts" / "projectstate_browser_verify.py"
SCHEMA = "projectstate.runtime_identity.v1"


def utc_now() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def repo_head(repo: Path) -> tuple[str, str, bool]:
    def git(*args: str) -> str:
        result = subprocess.run(
            ["git", *args], cwd=repo, capture_output=True, text=True, check=False
        )
        return result.stdout.strip() if result.returncode == 0 else "not proven"

    branch = git("branch", "--show-current") or "not proven"
    head = git("rev-parse", "HEAD")
    clean = subprocess.run(
        ["git", "diff", "--quiet"], cwd=repo, check=False
    ).returncode == 0
    return branch, head, clean


def ensure_http_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise SystemExit("--url must be an absolute http:// or https:// URL")


def ensure_inside(root: Path, path: Path) -> None:
    resolved_root = root.resolve()
    resolved_path = path.resolve()
    if resolved_path != resolved_root and resolved_root not in resolved_path.parents:
        raise SystemExit(f"Artifact path escapes evidence directory: {path}")


def runtime_identity(evidence_dir: Path, repo: Path, reason: str | None) -> Path:
    path = evidence_dir / "runtime_identity.json"
    if path.exists():
        return path
    if reason is None:
        raise SystemExit(
            "runtime_identity.json is required; use --no-runtime-required with --reason "
            "only for an explicitly non-runtime provider smoke test"
        )
    branch, head, clean = repo_head(repo)
    atomic_write_json(
        path,
        {
            "schema": SCHEMA,
            "captured_at": utc_now(),
            "repo": {
                "path": str(repo.resolve()),
                "branch": branch,
                "head": head,
                "worktree_clean": clean,
            },
            "runtime": {
                "required": False,
                "reason": reason,
            },
            "checks": {},
            "limits": [reason],
        },
    )
    return path


def command_for(args: argparse.Namespace, screenshot: Path, har: Path) -> list[str]:
    configured = args.playwright_command or os.environ.get("PLAYWRIGHT_COMMAND")
    if configured:
        command = shlex.split(configured)
    else:
        executable = shutil.which("playwright")
        if not executable:
            raise SystemExit(
                "Playwright CLI not found; install it or set PLAYWRIGHT_COMMAND"
            )
        command = [executable]
    command.extend(["screenshot", "--browser", args.browser])
    if args.full_page:
        command.append("--full-page")
    if args.wait_for_selector:
        command.extend(["--wait-for-selector", args.wait_for_selector])
    if args.wait_for_timeout is not None:
        command.extend(["--wait-for-timeout", str(args.wait_for_timeout)])
    if args.timeout is not None:
        command.extend(["--timeout", str(args.timeout)])
    command.extend(["--save-har", str(har), args.url, str(screenshot)])
    return command


def capture(args: argparse.Namespace) -> int:
    ensure_http_url(args.url)
    evidence_dir = Path(args.evidence_dir).resolve()
    evidence_dir.mkdir(parents=True, exist_ok=True)
    screenshot = evidence_dir / "playwright" / "page.png"
    har = evidence_dir / "playwright" / "network.har"
    command_log = evidence_dir / "playwright" / "capture_command.txt"
    for path in (screenshot, har, command_log):
        ensure_inside(evidence_dir, path)
    identity = runtime_identity(evidence_dir, Path(args.repo).resolve(), args.reason)
    command = command_for(args, screenshot, har)
    screenshot.parent.mkdir(parents=True, exist_ok=True)
    completed = subprocess.run(
        command,
        cwd=Path(args.repo).resolve(),
        capture_output=True,
        text=True,
        timeout=args.command_timeout,
        check=False,
    )
    command_log.write_text(
        "$ " + shlex.join(command) + "\n\n" + completed.stdout + completed.stderr,
        encoding="utf-8",
    )
    if completed.returncode != 0:
        print("Playwright capture failed:")
        print(completed.stdout, end="")
        print(completed.stderr, end="", file=sys.stderr)
        return completed.returncode or 1
    missing = [str(path) for path in (screenshot, har) if not path.exists()]
    if missing:
        print("Playwright capture did not produce required artifacts: " + ", ".join(missing), file=sys.stderr)
        return 1

    limits = list(args.limit)
    if args.reason:
        limits.append(args.reason)
    if not limits:
        limits.append("Playwright CLI capture records a screenshot and HAR; browser console messages are not captured by this CLI command.")
    artifact_paths = [screenshot, har, command_log]
    data = {
        "schema": "projectstate.browser_verification.v1",
        "captured_at": utc_now(),
        "slice_id": args.slice_id,
        "provider": {
            "kind": "playwright",
            "required": True,
            "available": True,
            "selection_reason": "Playwright CLI provider was explicitly selected and executed.",
            "fallbacks_considered": ["kimi_webbridge", "agent_native_browser", "manual_browser"],
            "tool": "playwright",
            "command": shlex.join(command),
        },
        "runtime_identity": {
            "path": identity.name,
            "head_matches": True,
            "endpoint_matches": None if args.reason else True,
        },
        "checks": [
            {
                "id": "BV-PLAYWRIGHT-001",
                "route": urlparse(args.url).path or "/",
                "claim": "Playwright captured the requested page and network trace.",
                "status": "passed",
                "evidence": [str(path.relative_to(evidence_dir)) for path in artifact_paths],
                "known_limits": limits,
            }
        ],
        "artifacts": [
            {
                "path": str(path.relative_to(evidence_dir)),
                "kind": kind,
                "sha256": sha256_file(path),
                "redaction_status": "manual_required" if kind == "screenshot" else "unchecked",
            }
            for path, kind in (
                (screenshot, "screenshot"),
                (har, "other"),
                (command_log, "test_output"),
            )
        ],
        "limits": limits,
    }
    atomic_write_json(evidence_dir / "browser_verification.json", data)
    result = subprocess.run(
        [sys.executable, str(BROWSER_VERIFY), "check", str(evidence_dir), "--strict"],
        cwd=Path(args.repo).resolve(),
        check=False,
    )
    if result.returncode:
        return result.returncode
    print(f"Playwright evidence captured in {evidence_dir}")
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True)
    parser.add_argument("--evidence-dir", required=True)
    parser.add_argument("--slice-id", default="BL-BROWSER-002")
    parser.add_argument("--repo", default=str(ROOT))
    parser.add_argument("--playwright-command", help="Executable or quoted command to invoke")
    parser.add_argument("--browser", default="chromium")
    parser.add_argument("--wait-for-selector")
    parser.add_argument("--wait-for-timeout", type=int)
    parser.add_argument("--timeout", type=int)
    parser.add_argument("--command-timeout", type=int, default=120)
    parser.add_argument("--full-page", action="store_true")
    parser.add_argument("--no-runtime-required", dest="reason", metavar="REASON")
    parser.add_argument("--limit", action="append", default=[])
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(capture(parse_args()))
