#!/usr/bin/env python3
"""Fast StateDD health summary for humans and the CTO lane.

Run this at the start of a session, before a handoff, or whenever you need a
shared snapshot of repo truth. It is read-only.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNTIME_IDENTITY_FILE = "runtime_identity.json"
RUNTIME_IDENTITY_SCHEMA = "statedd.runtime_identity.v1"


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


def git_value(repo: Path, args: list[str], fallback: str = "not proven") -> str:
    code, stdout, stderr = run_command(["git", *args], repo)
    if code != 0:
        return stderr or fallback
    return stdout or fallback


def read_optional(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8") if path.exists() else ""
    except UnicodeDecodeError:
        return ""


def extract_scalar(text: str, key: str) -> str | None:
    match = re.search(rf'^\s*{re.escape(key)}:\s*"?([^"\n#]+)"?\s*$', text, re.MULTILINE)
    return match.group(1).strip() if match else None


def repo_context(repo: Path) -> tuple[str, str]:
    project_state = read_optional(repo / "PROJECT_STATE.yaml")
    agents = read_optional(repo / "AGENTS.md")
    role = extract_scalar(project_state, "repo_role") or extract_scalar(agents, "repo_role") or "not proven"
    mode = (
        extract_scalar(project_state, "statedd_mode")
        or extract_scalar(agents, "statedd_mode")
        or extract_scalar(project_state, "repo_mode")
        or extract_scalar(agents, "repo_mode")
        or "not proven"
    )
    return role, mode


def latest_evidence_folder(repo: Path) -> Path | None:
    evidence_root = repo / "docs" / "evidence"
    try:
        if not evidence_root.exists():
            return None
        candidates = [
            entry
            for entry in evidence_root.iterdir()
            if entry.is_dir() and not entry.name.startswith(".")
        ]
    except OSError:
        return None
    if not candidates:
        return None
    try:
        return max(candidates, key=lambda p: p.stat().st_mtime)
    except OSError:
        return None


def worktree_status(repo: Path) -> str:
    code, status, _ = run_command(["git", "status", "--short"], repo)
    if code != 0:
        return "not a git repo"
    return "clean" if not status.strip() else "dirty"


def state_docs_updated(repo: Path) -> str:
    now = dt.datetime.now(dt.timezone.utc)
    stale_threshold = dt.timedelta(days=14)
    files = ["STATUS.md", "PROJECT_STATE.yaml", "NEXT_ACTIONS.md", "BACKLOG.md", "AGENTS.md"]
    stale: list[str] = []
    for relpath in files:
        path = repo / relpath
        try:
            if not path.exists():
                stale.append(f"{relpath} missing")
                continue
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            stale.append(f"{relpath} unreadable ({exc})")
            continue
        match = re.search(r"(?:updated_at|last_updated):\s*(\d{4}-\d{2}-\d{2})", text) or re.search(
            r"Updated At:\**\s*\*?(\d{4}-\d{2}-\d{2})\*?", text
        )
        if not match:
            stale.append(f"{relpath} no date")
            continue
        try:
            updated = dt.datetime.strptime(match.group(1), "%Y-%m-%d").replace(tzinfo=dt.timezone.utc)
        except ValueError:
            stale.append(f"{relpath} bad date")
            continue
        if now - updated > stale_threshold:
            stale.append(f"{relpath} stale ({(now - updated).days}d)")
    return "yes" if not stale else f"no ({'; '.join(stale)})"


def tests_recorded(repo: Path) -> str:
    folder = latest_evidence_folder(repo)
    if folder is None:
        return "no evidence folder"
    readme = folder / "README.md"
    try:
        if not readme.exists():
            return "no evidence README"
        text = readme.read_text(encoding="utf-8").lower()
    except (OSError, UnicodeDecodeError) as exc:
        return f"unreadable ({exc})"
    if "test" in text or "lint" in text or "build" in text:
        return "yes"
    return "no test/build/lint markers in README"


def browser_proof(repo: Path) -> str:
    folder = latest_evidence_folder(repo)
    if folder is None:
        return "no evidence folder"
    image_exts = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
    browser_exts = {".html", ".har", ".json"}
    try:
        files = [p for p in folder.rglob("*") if p.is_file()]
    except OSError as exc:
        return f"unreadable ({exc})"
    if any(p.suffix.lower() in image_exts for p in files):
        return "yes (image)"
    if any(p.suffix.lower() in browser_exts and p.name != RUNTIME_IDENTITY_FILE for p in files):
        return "yes (browser artifact)"
    return "no screenshot/browser artifacts"


def runtime_identity_status(repo: Path) -> str:
    folder = latest_evidence_folder(repo)
    if folder is None:
        return "no evidence folder"
    artifact = folder / RUNTIME_IDENTITY_FILE
    if not artifact.exists():
        readme = folder / "README.md"
        text = read_optional(readme).lower() if readme.exists() else ""
        if "runtime identity" in text or "runtime proof" in text or RUNTIME_IDENTITY_FILE in text:
            return "missing (claimed in evidence README)"
        return "not present"
    try:
        data = json.loads(artifact.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return f"malformed ({exc})"
    if not isinstance(data, dict):
        return "malformed (top-level JSON is not an object)"
    if data.get("schema") != RUNTIME_IDENTITY_SCHEMA:
        return f"schema mismatch ({data.get('schema') or 'missing'})"
    runtime = data.get("runtime")
    if not isinstance(runtime, dict):
        return "malformed (missing runtime object)"
    if runtime.get("required") is False:
        return "not required"
    checks = data.get("checks")
    endpoint = checks.get("endpoint_reachable") if isinstance(checks, dict) else "not recorded"
    process = runtime.get("process")
    if isinstance(process, dict) and process.get("detected") is True:
        process_status = "process proven"
    elif isinstance(process, dict) and "not applicable" in str(process.get("reason", "")).lower():
        process_status = "process not applicable"
    else:
        process_status = "process not proven"
    return f"required, endpoint_reachable={endpoint}, {process_status}"


def schema_validation_status(repo: Path) -> str:
    script = repo / "scripts" / "statedd_validate_schema.py"
    if not script.exists():
        return "missing validator"
    code, stdout, stderr = run_command([sys.executable, str(script), str(repo), "--quiet"], repo)
    if code == 0:
        return "pass"
    combined = f"{stdout}\n{stderr}".strip()
    first_line = combined.splitlines()[0] if combined else f"exit {code}"
    return f"fail ({first_line[:120]})"


def evidence_manifest_status(repo: Path) -> str:
    folder = latest_evidence_folder(repo)
    if folder is None:
        return "no evidence folder"
    manifest = folder / "manifest.json"
    if not manifest.exists():
        return "not present"
    script = repo / "scripts" / "statedd_evidence_pack.py"
    if not script.exists():
        return "manifest present, helper missing"
    code, stdout, stderr = run_command(
        [sys.executable, str(script), "check", str(folder)], repo
    )
    if code == 0:
        return "valid"
    combined = f"{stdout}\n{stderr}".strip()
    first_line = combined.splitlines()[0] if combined else f"exit {code}"
    return f"invalid ({first_line[:120]})"


def open_blockers(repo: Path) -> str:
    next_actions = repo / "NEXT_ACTIONS.md"
    try:
        if not next_actions.exists():
            return "unknown"
        text = next_actions.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return f"unreadable ({exc})"
    active = [line.strip() for line in text.splitlines() if line.startswith("### ")]
    return str(len(active))


def next_recommended_slice(repo: Path) -> str:
    next_actions = repo / "NEXT_ACTIONS.md"
    try:
        if not next_actions.exists():
            return "unknown"
        text = next_actions.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return f"unreadable ({exc})"
    for line in text.splitlines():
        if line.startswith("### "):
            return line.replace("### ", "").strip()
    return "none"


def closure_grade(repo: Path) -> str:
    audit_script = repo / "scripts" / "statedd_audit.py"
    if not audit_script.exists():
        return "unknown (no audit script)"
    code, _, _ = run_command([sys.executable, str(audit_script)], repo)
    return "pass" if code == 0 else "fail"


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fast StateDD health summary")
    parser.add_argument("root", nargs="?", default=str(ROOT), help="Repo root to inspect")
    return parser.parse_args(argv[1:])


def git_head(repo: Path) -> str:
    code, stdout, _ = run_command(["git", "rev-parse", "HEAD"], repo)
    if code != 0:
        return "not a git repo"
    return stdout


def git_branch(repo: Path) -> str:
    code, stdout, _ = run_command(["git", "rev-parse", "--abbrev-ref", "HEAD"], repo)
    if code != 0:
        return "not a git repo"
    return stdout


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv)
    repo = Path(args.root).resolve()

    head = git_head(repo)
    branch = git_branch(repo)
    role, mode = repo_context(repo)
    folder = latest_evidence_folder(repo)
    folder_name = folder.relative_to(repo).as_posix() if folder else "none"

    print("StateDD Health")
    print()
    print(f"Current HEAD: {head}")
    print(f"Branch: {branch}")
    print(f"Repo role: {role}")
    print(f"StateDD mode: {mode}")
    print(f"Worktree: {worktree_status(repo)}")
    print(f"Latest evidence: {folder_name}")
    print(f"State docs updated: {state_docs_updated(repo)}")
    print(f"Tests recorded: {tests_recorded(repo)}")
    print(f"Browser proof: {browser_proof(repo)}")
    print(f"Runtime identity: {runtime_identity_status(repo)}")
    print(f"Schema validation: {schema_validation_status(repo)}")
    print(f"Evidence manifest: {evidence_manifest_status(repo)}")
    print(f"Open blockers: {open_blockers(repo)}")
    print(f"Next recommended slice: {next_recommended_slice(repo)}")
    print(f"Closure grade: {closure_grade(repo)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
