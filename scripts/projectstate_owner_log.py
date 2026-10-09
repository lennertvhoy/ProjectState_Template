#!/usr/bin/env python3
"""Keep the owner's own words across sessions, without relying on the agent to write them down.

    python3 scripts/projectstate_owner_log.py install [--root DIR] [--dry-run]
    python3 scripts/projectstate_owner_log.py show [--root DIR]
    python3 scripts/projectstate_owner_log.py record      # Claude Code UserPromptSubmit hook (reads JSON on stdin)
    python3 scripts/projectstate_owner_log.py inject      # Claude Code SessionStart hook (prints context)

What an owner says in conversation (a constraint, a decision, "do it this way") exists nowhere in the repository
unless an agent chooses to write it down, and measured agents mostly do not. This tool captures it mechanically.
``record`` appends each owner prompt, verbatim, to ``.projectstate/owner-log.md``. ``inject`` prints the most recent
entries when a session starts, resumes or is compacted, so the next session starts with the owner's words in context
whether or not anything was written elsewhere.

The log is local: ``.projectstate/`` ignores itself in Git, because prompts can hold private data. Obvious secrets
(private keys, ``sk-``/``ghp_``/``AKIA``/``xox`` tokens, ``password=...`` pairs) are redacted on a best-effort basis;
that is not a guarantee. The hooks never block or fail a session: any problem is reported on stderr and the exit code
stays 0. Only ``install`` edits a file you did not create, and it merges into ``.claude/settings.json`` without
removing anything. Other agent hosts need their own equivalent of the two hooks; the log format is plain Markdown.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
import tempfile
from pathlib import Path

LOG_DIR = ".projectstate"
LOG_NAME = "owner-log.md"
MAX_ENTRY_CHARS = 8000
MAX_LOG_BYTES = 64 * 1024
INJECT_CHARS = 3500
INJECT_ENTRY_CHARS = 1500
MIN_PROMPT_CHARS = 3
HOOK_MARK = "projectstate_owner_log.py"
ENTRY_HEAD = re.compile(r"^## (\d{4}-\d{2}-\d{2}T[\d:]+Z) \(session ([^)]*)\)\s*$", re.MULTILINE)
REDACTIONS = (
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.DOTALL), "[redacted private key]"),
    (re.compile(r"\b(?:sk-[A-Za-z0-9_-]{16,}|gh[pousr]_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|xox[baprs]-[A-Za-z0-9-]{10,})\b"), "[redacted token]"),
    (re.compile(r"(?i)\b(password|passwd|secret|token|api[_-]?key)(\s*[:=]\s*)\S+"), r"\1\2[redacted]"),
)
HOOKS = {
    "SessionStart": f'python3 "$CLAUDE_PROJECT_DIR"/scripts/{HOOK_MARK} inject',
    "UserPromptSubmit": f'python3 "$CLAUDE_PROJECT_DIR"/scripts/{HOOK_MARK} record',
}


def find_root(start: Path) -> Path:
    """The nearest ancestor holding STATE.yaml or .git; otherwise ``start`` itself."""
    for candidate in (start, *start.parents):
        if (candidate / "STATE.yaml").is_file() or (candidate / ".git").exists():
            return candidate
    return start


def redact(text: str) -> str:
    for pattern, replacement in REDACTIONS:
        text = pattern.sub(replacement, text)
    return text


def log_path(root: Path) -> Path:
    return root / LOG_DIR / LOG_NAME


def write_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    tmp_path = Path(name)
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
        os.replace(tmp_path, path)
    except BaseException:
        tmp_path.unlink(missing_ok=True)
        raise


def entries_of(text: str) -> list[tuple[str, str, str]]:
    """(timestamp, session, body) for each entry, oldest first."""
    heads = list(ENTRY_HEAD.finditer(text))
    found = []
    for index, head in enumerate(heads):
        end = heads[index + 1].start() if index + 1 < len(heads) else len(text)
        found.append((head.group(1), head.group(2), text[head.end():end].strip()))
    return found


def render_entry(stamp: str, session: str, body: str) -> str:
    return f"## {stamp} (session {session})\n\n{body}\n\n"


def append_entry(root: Path, prompt: str, session: str, now: dt.datetime | None = None) -> bool:
    """Append one owner prompt; return False when it is too short, repeated or the log cannot be written safely."""
    body = redact(prompt.strip())
    if len(body) < MIN_PROMPT_CHARS:
        return False
    if len(body) > MAX_ENTRY_CHARS:
        body = body[:MAX_ENTRY_CHARS] + "\n[truncated]"
    directory = root / LOG_DIR
    if directory.is_symlink() or log_path(root).is_symlink():
        return False
    path = log_path(root)
    existing = path.read_text(encoding="utf-8") if path.is_file() else ""
    found = entries_of(existing)
    if found and found[-1][1] == session and found[-1][2] == body:
        return False
    stamp = (now or dt.datetime.now(dt.timezone.utc)).strftime("%Y-%m-%dT%H:%M:%SZ")
    kept = found + [(stamp, session, body)]
    text = "# Owner log\n\nThe owner's words, verbatim and oldest first. Recorded by scripts/projectstate_owner_log.py.\n\n"
    rendered = [render_entry(*entry) for entry in kept]
    while len(rendered) > 1 and len((text + "".join(rendered)).encode("utf-8")) > MAX_LOG_BYTES:
        rendered.pop(0)  # keep the newest entries when the log outgrows its cap
    directory.mkdir(parents=True, exist_ok=True)
    gitignore = directory / ".gitignore"
    if not gitignore.exists():
        gitignore.write_text("*\n", encoding="utf-8")
    write_atomic(path, text + "".join(rendered))
    return True


def inject_text(root: Path) -> str:
    path = log_path(root)
    if path.is_symlink() or not path.is_file():
        return ""
    found = entries_of(path.read_text(encoding="utf-8"))
    if not found:
        return ""
    blocks: list[str] = []
    used = 0
    for stamp, session, body in reversed(found):
        shown = body if len(body) <= INJECT_ENTRY_CHARS else body[:INJECT_ENTRY_CHARS] + " [...]"
        block = f"[{stamp}] {shown}"
        if blocks and used + len(block) > INJECT_CHARS:
            break
        blocks.append(block)
        used += len(block)
    header = (
        "Owner's words from earlier sessions in this project (verbatim, oldest first). Treat constraints and "
        "decisions in them as binding unless the owner changes them, and carry them into your plans and records:"
    )
    return header + "\n" + "\n---\n".join(reversed(blocks)) + "\n"


def hook_input() -> dict:
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except (ValueError, OSError):
        return {}
    return payload if isinstance(payload, dict) else {}


def hook_root(payload: dict) -> Path:
    return find_root(Path(str(payload.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())).resolve())


def merge_settings(existing: dict) -> tuple[dict, list[str]]:
    """Add the two hooks to a Claude Code settings mapping, keeping everything already there."""
    merged = json.loads(json.dumps(existing))
    hooks = merged.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        raise ValueError("'hooks' in .claude/settings.json is not an object")
    added = []
    for event, command in HOOKS.items():
        groups = hooks.setdefault(event, [])
        if not isinstance(groups, list):
            raise ValueError(f"hooks.{event} in .claude/settings.json is not a list")
        present = any(HOOK_MARK in str(hook.get("command", "")) for group in groups if isinstance(group, dict)
                      for hook in group.get("hooks", []) if isinstance(hook, dict))
        if not present:
            groups.append({"hooks": [{"type": "command", "command": command}]})
            added.append(event)
    return merged, added


def install(root: Path, dry_run: bool) -> int:
    settings = root / ".claude" / "settings.json"
    tool = root / "scripts" / HOOK_MARK
    if settings.is_symlink() or (root / ".claude").is_symlink():
        print("refused: .claude/settings.json is reached through a symlink", file=sys.stderr)
        return 2
    try:
        existing = json.loads(settings.read_text(encoding="utf-8")) if settings.is_file() else {}
        if not isinstance(existing, dict):
            raise ValueError("it is not a JSON object")
        merged, added = merge_settings(existing)
    except (ValueError, OSError) as error:
        print(f"refused: cannot merge into {settings}: {error}", file=sys.stderr)
        return 2
    if not tool.is_file():
        print(f"warning: {tool} does not exist, so the hooks would fail; copy this script to scripts/ first", file=sys.stderr)
    if not added:
        print("already installed: both hooks are present in .claude/settings.json")
        return 0
    print(f"{'would add' if dry_run else 'adding'} hooks for: {', '.join(added)} in {settings}")
    if not dry_run:
        write_atomic(settings, json.dumps(merged, indent=2) + "\n")
        print("done. Restart Claude Code in this project; owner prompts are now recorded to .projectstate/owner-log.md")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Keep the owner's own words across sessions")
    parser.add_argument("command", choices=("install", "show", "record", "inject"))
    parser.add_argument("--root", default=".", help="Repository root (install and show; default: current directory)")
    parser.add_argument("--dry-run", action="store_true", help="install: print what would change and write nothing")
    args = parser.parse_args(argv)
    try:
        if args.command == "install":
            return install(Path(args.root).resolve(), args.dry_run)
        if args.command == "show":
            print(log_path(find_root(Path(args.root).resolve())).read_text(encoding="utf-8"), end="")
            return 0
        payload = hook_input()
        root = hook_root(payload)
        if args.command == "record":
            append_entry(root, str(payload.get("prompt") or ""), str(payload.get("session_id") or "unknown")[:8])
        else:
            sys.stdout.write(inject_text(root))
    except Exception as error:  # noqa: BLE001 - a hook must never break the owner's session
        if args.command in ("install", "show"):
            print(f"error: {error}", file=sys.stderr)
            return 2
        print(f"projectstate_owner_log: {args.command} skipped: {error}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
