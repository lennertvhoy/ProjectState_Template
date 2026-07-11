#!/usr/bin/env python3
"""StateDD Parallel-Agent Worktree Orchestrator.

Creates, guards, hands off, and closes isolated git worktrees for concurrent
agent slices. Each agent gets its own branch and worktree under
<repo-root>/.worktrees/, tracked by a reservation ref under
refs/statedd/reservations/ and a .statedd/agent.context file inside the
worktree.

Subcommands:
  start   Create a branch, worktree, reservation ref, and agent.context.
  guard   Run worktree-guard checks in agent context.
  handoff Run statedd_handoff.py from inside the agent worktree.
  close   Push branch, run remote closure finalizer, then remove worktree.
  cleanup Remove stale or explicitly-forced agent worktrees and reservations.
  list    Show active agent worktrees, branches, reservations, and lock files.

Exit codes:
  0 = success / guard passed
  1 = guard/runtime failure (recoverable, usually user-facing)
  2 = unexpected runtime error
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

try:
    from statedd_contracts import (
        ContractError,
        reject_symlink_components,
        safe_root_path,
        strict_json_loads,
    )
except ModuleNotFoundError:  # pragma: no cover - pytest package import path
    from scripts.statedd_contracts import (
        ContractError,
        reject_symlink_components,
        safe_root_path,
        strict_json_loads,
    )


ROOT = Path(__file__).resolve().parents[1]

VALID_SLICE_CATEGORIES = {"intended_slice_work", "generated_artifact"}
AGENT_CONTEXT_SCHEMA = "statedd.agent_context.v1"
RESERVATION_REF_PREFIX = "refs/statedd/reservations/"
WORKTREE_DIR = ".worktrees"
LOCK_FILES = ("index.lock", "config.lock")
AGENT_CONTEXT_FIELDS = {
    "schema",
    "agent_id",
    "slice_id",
    "reservation_ref",
    "worktree_path",
    "branch",
    "base_branch",
    "created_at",
}


def run_command(args: list[str], cwd: Path) -> tuple[int, str, str]:
    """Run a subprocess command and return (code, stdout, stderr)."""
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
    code, stdout, _ = run_command(["git", *args], repo)
    if code != 0:
        return fallback
    return stdout or fallback


def resolve_repo(path: Path) -> tuple[int, Path, str]:
    code, stdout, stderr = run_command(["git", "rev-parse", "--show-toplevel"], path)
    if code != 0:
        return 2, path.resolve(), stderr or "not a git repository"
    return 0, Path(stdout).resolve(), ""


def git_common_dir(repo: Path) -> Path | None:
    code, stdout, _ = run_command(["git", "rev-parse", "--git-common-dir"], repo)
    if code != 0 or not stdout:
        return None
    return (repo / stdout).resolve() if not os.path.isabs(stdout) else Path(stdout).resolve()


def detect_git_locks(repo: Path) -> list[Path]:
    """Return list of existing git lock files in the common git directory."""
    locks: list[Path] = []
    common = git_common_dir(repo)
    if not common:
        return locks
    for name in LOCK_FILES:
        lock = common / name
        if lock.exists():
            locks.append(lock)
    return locks


def wait_for_git_locks(repo: Path, max_seconds: float = 10.0) -> list[Path]:
    """Poll until git locks are released or timeout expires."""
    deadline = time.time() + max_seconds
    interval = 0.2
    while time.time() < deadline:
        locks = detect_git_locks(repo)
        if not locks:
            return []
        time.sleep(interval)
    return detect_git_locks(repo)


def base36_encode(value: int, width: int = 5) -> str:
    """Encode a non-negative integer as zero-padded base36 lowercase."""
    if value < 0:
        raise ValueError("value must be non-negative")
    chars = []
    while value or not chars:
        value, remainder = divmod(value, 36)
        chars.append("0123456789abcdefghijklmnopqrstuvwxyz"[remainder])
    return "".join(reversed(chars)).zfill(width)


def generate_agent_id() -> tuple[str, str]:
    """Return (agent_id, agent_short_id)."""
    env_id = os.environ.get("STATEDD_AGENT_ID", "").strip()
    if env_id:
        short = env_id[:4].lower()
        return env_id, short
    short = uuid.uuid4().hex[:4].lower()
    return f"agent-{short}", short


def compute_branch_name(slice_id: str, agent_short_id: str) -> str:
    """Compute deterministic branch name with a timestamp nonce."""
    # Use a fragment of the current timestamp so simultaneous starts for the
    # same slice by the same agent still collide rarely.
    nonce_value = int(time.time() * 1000) % (36 ** 5)
    nonce = base36_encode(nonce_value, 5)
    clean_slice = "".join(c if c.isalnum() else "-" for c in slice_id.lower()).strip("-")
    return f"bl-{clean_slice}-{agent_short_id}-{nonce}"


def worktree_path_for_branch(repo: Path, branch: str) -> Path:
    return (repo / WORKTREE_DIR / branch).resolve()


def reservation_ref(branch: str) -> str:
    return f"{RESERVATION_REF_PREFIX}{branch}"


def load_agent_context(path: Path) -> tuple[int, dict, str]:
    """Load a closed-world agent.context JSON contract without following links."""
    if path.is_dir():
        context_path = path / ".statedd" / "agent.context"
    else:
        context_path = path
    try:
        reject_symlink_components(context_path, label="agent context")
        if not context_path.is_file():
            return 2, {}, f"agent context is not a regular file: {context_path}"
        data = strict_json_loads(context_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return 2, {}, f"agent context not found: {context_path}"
    except (ContractError, OSError, UnicodeDecodeError) as exc:
        return 2, {}, f"invalid agent context JSON: {exc}"
    if not isinstance(data, dict):
        return 2, {}, "agent context must be a JSON object"
    missing = AGENT_CONTEXT_FIELDS - set(data)
    unknown = set(data) - AGENT_CONTEXT_FIELDS
    if missing or unknown:
        return 2, {}, f"agent context fields are invalid (missing={sorted(missing)}, unknown={sorted(unknown)})"
    if data.get("schema") != AGENT_CONTEXT_SCHEMA:
        return 2, {}, f"unexpected agent context schema: {data.get('schema')}"
    for field in AGENT_CONTEXT_FIELDS - {"schema"}:
        if not isinstance(data.get(field), str) or not data[field].strip():
            return 2, {}, f"agent context field {field!r} must be a non-empty string"
    branch = data["branch"]
    if data["reservation_ref"] != reservation_ref(branch):
        return 2, {}, "agent context reservation_ref does not match its branch"
    if not Path(data["worktree_path"]).is_absolute():
        return 2, {}, "agent context worktree_path must be absolute"
    return 0, data, ""


def atomic_write_context(path: Path, context: dict) -> None:
    """Write context atomically so interruption cannot leave a partial contract."""
    payload = json.dumps(context, indent=2, sort_keys=True) + "\n"
    descriptor, tmp_name = tempfile.mkstemp(prefix=".agent.context.", dir=path.parent)
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(tmp_path, 0o600)
        os.replace(tmp_path, path)
    finally:
        tmp_path.unlink(missing_ok=True)


def _strict_context_message(text: str) -> dict | None:
    try:
        payload = strict_json_loads(text)
    except ContractError:
        return None
    return payload if isinstance(payload, dict) else None


def verify_agent_ownership(worktree: Path, context: dict) -> tuple[int, Path, str]:
    """Bind a context to its exact registered worktree, branch, and reservation."""
    try:
        requested = safe_root_path(worktree, must_exist=True)
        declared = safe_root_path(context["worktree_path"], must_exist=True)
    except (ContractError, OSError) as exc:
        return 2, worktree, str(exc)
    code, repo, error = resolve_repo(requested)
    if code != 0:
        return code, repo, error
    if requested != repo or declared != repo:
        return 2, repo, (
            f"agent context worktree mismatch: requested={requested}, "
            f"declared={declared}, git_root={repo}"
        )

    branch = current_branch(repo)
    declared_branch = context["branch"]
    if branch != declared_branch:
        return 2, repo, (
            f"agent context branch {declared_branch!r} does not match current branch {branch!r}"
        )

    repo_root = main_worktree_root(repo)
    worktrees = list_worktrees(repo_root)
    record = worktrees.get(f"refs/heads/{declared_branch}")
    if not isinstance(record, dict):
        return 2, repo, f"branch {declared_branch!r} is not registered to a worktree"
    try:
        registered = safe_root_path(record.get("path", ""), must_exist=True)
    except (ContractError, OSError) as exc:
        return 2, repo, f"registered worktree path is unsafe: {exc}"
    if registered != repo:
        return 2, repo, (
            f"branch {declared_branch!r} is registered at {registered}, not {repo}"
        )

    ref = context["reservation_ref"]
    if ref != reservation_ref(declared_branch):
        return 2, repo, "reservation ref does not match the current branch"
    code, _, stderr = run_command(["git", "rev-parse", "--verify", ref], repo_root)
    if code != 0:
        return 2, repo, f"reservation ref is missing: {ref}: {stderr}"
    code, message, stderr = run_command(
        ["git", "log", "-g", "-1", "--format=%gs", ref], repo_root
    )
    if code != 0:
        return 2, repo, f"reservation reflog is unavailable for {ref}: {stderr}"
    reserved_context = _strict_context_message(message)
    if reserved_context != context:
        return 2, repo, "agent context does not match the reservation reflog payload"
    return 0, repo, ""


def load_and_verify_agent(worktree: Path) -> tuple[int, dict, Path, str]:
    code, context, error = load_agent_context(worktree)
    if code != 0:
        return code, {}, worktree, error
    code, repo, error = verify_agent_ownership(worktree, context)
    return code, context, repo, error


def normalize_cell(cell: str) -> str:
    return cell.strip().strip("`").strip()


def parse_classification_file(path: Path) -> dict[str, str]:
    """Parse a markdown classification table into {path: category}."""
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return {}
    classifications: dict[str, str] = {}
    for raw in text.splitlines():
        stripped = raw.strip()
        if not stripped.startswith("|"):
            continue
        cells = [normalize_cell(cell) for cell in stripped.strip("|").split("|")]
        if not cells or set(cells[0]) <= {"-", ":"}:
            continue
        lower = [cell.lower() for cell in cells]
        if "path" in lower and "category" in lower:
            continue
        file_path = ""
        category = ""
        if len(cells) >= 3 and cells[2] in {
            "intended_slice_work",
            "pre_existing_unrelated",
            "generated_artifact",
            "unknown_do_not_touch",
            "safe_to_discard_after_proof",
        }:
            file_path = cells[1]
            category = cells[2]
        elif len(cells) >= 2 and cells[1] in {
            "intended_slice_work",
            "pre_existing_unrelated",
            "generated_artifact",
            "unknown_do_not_touch",
            "safe_to_discard_after_proof",
        }:
            file_path = cells[0]
            category = cells[1]
        if file_path and category:
            classifications[file_path] = category
    return classifications


def with_agent_classifications(classifications: dict[str, str]) -> dict[str, str]:
    """Return a copy that classifies orchestrator-managed files as generated artifacts."""
    result = dict(classifications)
    result.setdefault(".statedd/", "generated_artifact")
    result.setdefault(".statedd/agent.context", "generated_artifact")
    return result


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


def current_branch(repo: Path) -> str:
    branch = git_value(repo, ["branch", "show-current"], fallback="")
    if branch:
        return branch
    return git_value(repo, ["rev-parse", "--abbrev-ref", "HEAD"], fallback="not proven")


def origin_default_branch(repo: Path) -> str:
    ref = git_value(repo, ["symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD"], fallback="")
    if ref.startswith("origin/"):
        return ref.removeprefix("origin/")
    return ""


def resolve_base_ref(repo: Path, explicit_base: str | None) -> tuple[str, str]:
    """Resolve the base ref for a new agent worktree.

    Fresh CI checkouts often contain only the checked-out branch, so a hard-coded
    local ``main`` default is not reliable. Explicit --base remains strict; the
    implicit default tries default-branch refs first, then the current branch,
    then HEAD as a last resort.
    """
    if explicit_base:
        base = explicit_base.strip()
        return base, git_value(repo, ["rev-parse", base], fallback="")

    candidates: list[str] = []
    default_branch = origin_default_branch(repo)
    if default_branch:
        candidates.extend([default_branch, f"origin/{default_branch}"])
    candidates.extend(["main", "origin/main", "master", "origin/master"])
    branch = current_branch(repo)
    if branch and branch != "not proven":
        candidates.append(branch)
    candidates.append("HEAD")

    seen: set[str] = set()
    for candidate in candidates:
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        commit = git_value(repo, ["rev-parse", candidate], fallback="")
        if commit:
            return candidate, commit
    return "", ""


def dirty_files(repo: Path) -> list[str]:
    status = git_value(repo, ["status", "--short"], fallback="")
    paths: list[str] = []
    for line in status.splitlines():
        if not line.strip():
            continue
        path = line[3:] if len(line) > 3 else line
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        paths.append(path)
    return paths


def linked_worktree_paths(repo: Path) -> list[str]:
    code, stdout, _ = run_command(["git", "worktree", "list", "--porcelain"], repo)
    if code != 0:
        return []
    current = repo.resolve()
    linked: list[str] = []
    for line in stdout.splitlines():
        if not line.startswith("worktree "):
            continue
        path = line.removeprefix("worktree ").strip()
        if path and Path(path).resolve() != current:
            linked.append(path)
    return linked


def main_worktree_root(repo: Path) -> Path:
    """Return the main worktree root (first entry from git worktree list)."""
    code, stdout, _ = run_command(["git", "worktree", "list", "--porcelain"], repo)
    if code == 0:
        for line in stdout.splitlines():
            if line.startswith("worktree "):
                return Path(line.removeprefix("worktree ").strip()).resolve()
    return repo.resolve()


def origin_default_branch(repo: Path) -> str:
    ref = git_value(repo, ["symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD"], fallback="")
    if ref.startswith("origin/"):
        return ref.removeprefix("origin/")
    return "main"


def check_locks_or_fail(repo: Path, wait: bool = False) -> int:
    locks = wait_for_git_locks(repo) if wait else detect_git_locks(repo)
    if locks:
        for lock in locks:
            print(f"Another git operation holds {lock}; use --wait or retry.", file=sys.stderr)
        return 1
    return 0


def rollback_started_worktree(repo: Path, worktree: Path, branch: str, ref: str) -> list[str]:
    """Best-effort reverse-order rollback for a failed start transaction."""
    errors: list[str] = []
    code, _, stderr = run_command(["git", "update-ref", "-d", ref], repo)
    if code != 0:
        errors.append(f"reservation cleanup failed: {stderr}")
    registered = list_worktrees(repo).get(f"refs/heads/{branch}")
    if registered:
        try:
            remove_worktree_safe(repo, worktree)
        except RuntimeError as exc:
            errors.append(str(exc))
    code, _, stderr = run_command(["git", "branch", "-D", branch], repo)
    if code != 0:
        errors.append(f"branch cleanup failed: {stderr}")
    return errors


def cmd_start(args: argparse.Namespace) -> int:
    repo = Path(args.repo).resolve()
    code, repo, error = resolve_repo(repo)
    if code != 0:
        print(f"StateDD Agent Worktree Orchestrator\n\nBlocking problems\n- {error}", file=sys.stderr)
        return 2

    # Operate from the main worktree so .worktrees/ is created in a predictable
    # location relative to the repository root.
    repo = main_worktree_root(repo)

    slice_id = (args.slice_id or "").strip()
    if not slice_id:
        print("--slice-id is required for start", file=sys.stderr)
        return 1

    agent_id, agent_short_id = generate_agent_id()
    if args.agent_id:
        agent_id = args.agent_id.strip()
        agent_short_id = agent_id[:4].lower()

    branch = args.branch if args.branch else compute_branch_name(slice_id, agent_short_id)
    wt_path = (repo / WORKTREE_DIR / branch).resolve()
    ref = reservation_ref(branch)
    # Verify git is available and base exists.
    base, base_commit = resolve_base_ref(repo, args.base)
    if not base_commit:
        requested = args.base if args.base else "auto"
        print(f"Base branch/ref '{requested}' could not be resolved", file=sys.stderr)
        return 1

    # Fail fast if reservation already exists.
    existing_ref = git_value(repo, ["rev-parse", "--quiet", ref], fallback="")
    if existing_ref:
        print(f"Reservation ref already exists: {ref}", file=sys.stderr)
        return 1

    # Fail fast if branch or worktree path already exists.
    if (repo / ".git" / "refs" / "heads" / branch).exists() or git_value(repo, ["rev-parse", "--quiet", branch], fallback=""):
        print(f"Branch already exists: {branch}", file=sys.stderr)
        return 1
    if wt_path.exists():
        print(f"Worktree path already exists: {wt_path}", file=sys.stderr)
        return 1

    lock_code = check_locks_or_fail(repo, wait=args.wait)
    if lock_code != 0:
        return lock_code

    if args.dry_run:
        print("DRY RUN: would create branch, worktree, agent.context, and reservation ref")
        print(f"  branch: {branch}")
        print(f"  worktree: {wt_path}")
        print(f"  base: {base} ({base_commit})")
        print(f"  reservation: {ref}")
        print(f"  agent_id: {agent_id}")
        return 0

    # Create branch.
    code, _, stderr = run_command(["git", "branch", branch, base], repo)
    if code != 0:
        print(f"Failed to create branch '{branch}': {stderr}", file=sys.stderr)
        return 2

    # Create worktree (use absolute path so it is registered consistently).
    code, _, stderr = run_command(["git", "worktree", "add", str(wt_path), branch], repo)
    if code != 0:
        # Roll back branch if worktree creation failed.
        run_command(["git", "branch", "-D", branch], repo)
        print(f"Failed to create worktree '{wt_path}': {stderr}", file=sys.stderr)
        return 2

    try:
        # Ensure .statedd directory exists inside worktree.
        statedd_dir = wt_path / ".statedd"
        statedd_dir.mkdir(parents=True, exist_ok=True)

        created_at = dt.datetime.now(dt.timezone.utc).astimezone().isoformat(timespec="seconds")
        context = {
            "schema": AGENT_CONTEXT_SCHEMA,
            "agent_id": agent_id,
            "slice_id": slice_id,
            "reservation_ref": ref,
            "worktree_path": str(wt_path),
            "branch": branch,
            "base_branch": base,
            "created_at": created_at,
        }
        context_path = statedd_dir / "agent.context"
        atomic_write_context(context_path, context)

        # Create reservation ref with context JSON as reflog message.
        # --create-reflog is required so custom refs under refs/statedd/ keep a
        # reflog that `git log -g` can later retrieve.
        context_json = json.dumps(context, sort_keys=True)
        code, _, stderr = run_command(
            ["git", "update-ref", "--create-reflog", "-m", context_json, ref, base_commit],
            repo,
        )
        if code != 0:
            raise RuntimeError(f"Failed to create reservation ref '{ref}': {stderr}")
    except (OSError, RuntimeError) as exc:
        cleanup_errors = rollback_started_worktree(repo, wt_path, branch, ref)
        suffix = f"; rollback errors: {cleanup_errors}" if cleanup_errors else ""
        print(f"Failed to complete worktree start: {exc}{suffix}", file=sys.stderr)
        return 2

    print(f"Agent worktree ready: {wt_path}")
    print(f"Branch: {branch}")
    return 0


def cmd_guard(args: argparse.Namespace) -> int:
    worktree = Path(args.worktree).absolute() if args.worktree else Path.cwd().absolute()
    code, context, repo, error = load_and_verify_agent(worktree)
    if code != 0:
        print(f"StateDD Agent Worktree Guard\n\nBlocking problems\n- {error}", file=sys.stderr)
        return 2

    env = os.environ.copy()
    env["GIT_OPTIONAL_LOCKS"] = "0"

    branch = current_branch(repo)
    local_head = git_value(repo, ["rev-parse", "HEAD"])
    origin_url = git_value(repo, ["remote", "get-url", "origin"])
    upstream_branch = git_value(repo, ["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"])
    upstream_head = "not proven"
    if upstream_branch != "not proven":
        upstream_head = git_value(repo, ["rev-parse", "@{u}"])
    default_branch = origin_default_branch(repo)
    changed = dirty_files(repo)
    linked = linked_worktree_paths(repo)

    source = latest_evidence_readme(repo)
    classifications = with_agent_classifications(parse_classification_file(source) if source else {})
    classified = all(path in classifications for path in changed) if changed else True

    warnings: list[str] = []
    problems: list[str] = []

    if args.mode == "closure":
        if changed:
            problems.append("Closure mode requires a clean worktree.")
    else:
        if changed and not classified:
            missing = [p for p in changed if p not in classifications]
            warnings.append(
                f"Dirty files are not classified; record a classification table in evidence: {', '.join(missing)}"
            )
        elif changed:
            warnings.append("Dirty files are classified as expected slice work.")

    if origin_url == "not proven":
        warnings.append("origin remote URL is not proven; remote visibility cannot be checked yet.")
    if upstream_branch == "not proven":
        warnings.append("upstream branch is not proven; local HEAD versus upstream is not comparable yet.")

    safe = not problems

    print("StateDD Agent Worktree Guard")
    print(f"Mode: {args.mode}")
    print(f"Agent context: {context.get('agent_id')} / {context.get('slice_id')}")
    print()
    print("Repo truth")
    print(f"- repo root: {repo}")
    print(f"- current branch: {branch}")
    print(f"- local HEAD: {local_head}")
    print(f"- origin remote URL: {origin_url}")
    print(f"- upstream branch: {upstream_branch}")
    print(f"- upstream HEAD: {upstream_head}")
    print(f"- default branch: {default_branch}")
    print(f"- agent branch is private: yes")
    print(f"- local HEAD equals upstream: {'yes' if local_head == upstream_head else 'no' if upstream_head != 'not proven' else 'not proven'}")
    print(f"- safe to start: {'yes' if safe else 'no'}")
    print()
    print("Worktree topology")
    print("- worktree topology captured: yes")
    print(f"- current worktree path: {repo}")
    if linked:
        print("- linked worktrees:")
        for path in linked:
            print(f"  - {path}")
    else:
        print("- linked worktrees: none")
    print()
    print("Dirty state")
    print(f"- dirty files classified: {'yes' if classified else 'no'}")
    print(f"- classification file: {source if source else 'not found'}")
    print(f"- dirty file count: {len(changed)}")
    print("- dirty files:")
    if changed:
        for path in changed:
            category = classifications.get(path, "not classified")
            print(f"  - {path} [{category}]")
    else:
        print("  - none")
    print()
    print("Warnings")
    if warnings:
        for warning in warnings:
            print(f"- {warning}")
    else:
        print("- none")
    print()
    print("Blocking problems")
    if problems:
        for problem in problems:
            print(f"- {problem}")
    else:
        print("- none")

    return 0 if safe else 1


def cmd_handoff(args: argparse.Namespace) -> int:
    worktree = Path(args.worktree).absolute() if args.worktree else Path.cwd().absolute()
    code, context, repo, error = load_and_verify_agent(worktree)
    if code != 0:
        print(f"StateDD Agent Worktree Handoff\n\nBlocking problems\n- {error}", file=sys.stderr)
        return 2
    worktree = repo

    handoff_script = ROOT / "scripts" / "statedd_handoff.py"
    if not handoff_script.exists():
        print(f"Handoff script not found: {handoff_script}", file=sys.stderr)
        return 2

    code, output, stderr = run_command([sys.executable, str(handoff_script), "--repo", str(worktree)], worktree)
    print(output)
    if stderr:
        print(stderr, file=sys.stderr)
    if code != 0:
        return code

    changed = dirty_files(worktree)
    if changed:
        source = latest_evidence_readme(worktree)
        classifications = with_agent_classifications(parse_classification_file(source) if source else {})
        unclassified = [p for p in changed if p not in classifications]
        if unclassified:
            print()
            print("Warnings")
            print(f"- Unclassified dirty files (expected intended_slice_work or generated_artifact): {', '.join(unclassified)}")
        else:
            miscategorized = [
                p for p in changed
                if classifications.get(p) not in VALID_SLICE_CATEGORIES
            ]
            if miscategorized:
                print()
                print("Warnings")
                cats = [classifications.get(p, "not classified") for p in miscategorized]
                print(f"- Dirty files not classified as intended_slice_work or generated_artifact: {', '.join(f'{p}[{c}]' for p, c in zip(miscategorized, cats))}")

    if args.release:
        ref = context.get("reservation_ref", "")
        if ref:
            repo_root = main_worktree_root(worktree)
            delete_code, _, delete_error = run_command(["git", "update-ref", "-d", ref], repo_root)
            if delete_code != 0:
                print(f"Failed to release reservation {ref}: {delete_error}", file=sys.stderr)
                return 1
            print(f"Released reservation: {ref}")

    return 0


def cmd_close(args: argparse.Namespace) -> int:
    worktree = Path(args.worktree).absolute() if args.worktree else Path.cwd().absolute()
    code, context, repo, error = load_and_verify_agent(worktree)
    if code != 0:
        print(f"StateDD Agent Worktree Close\n\nBlocking problems\n- {error}", file=sys.stderr)
        return 2
    worktree = repo

    pr_number = args.pr
    if not pr_number or pr_number <= 0:
        print("--pr is required and must be a positive integer", file=sys.stderr)
        return 1

    branch = context.get("branch", "")
    ref = context.get("reservation_ref", "")
    repo_root = main_worktree_root(worktree)

    if args.dry_run:
        print("DRY RUN: would push branch and run remote closure finalizer")
        print(f"  branch: {branch}")
        print(f"  worktree: {worktree}")
        print(f"  reservation: {ref}")
        return 0

    lock_code = check_locks_or_fail(repo_root, wait=args.wait)
    if lock_code != 0:
        return lock_code

    # Push branch.
    code, _, stderr = run_command(
        ["git", "push", "origin", f"HEAD:refs/heads/{branch}"], worktree
    )
    if code != 0:
        print(f"Failed to push branch '{branch}': {stderr}", file=sys.stderr)
        print(f"Worktree left intact for debugging: {worktree}")
        return 1

    # Run remote closure finalizer from inside the worktree.
    finalizer_script = ROOT / "scripts" / "statedd_remote_closure_finalizer.py"
    if not finalizer_script.exists():
        print(f"Remote closure finalizer not found: {finalizer_script}", file=sys.stderr)
        print(f"Worktree left intact for debugging: {worktree}")
        return 2

    code, output, stderr = run_command(
        [sys.executable, str(finalizer_script), "--root", str(worktree), "--pr-number", str(pr_number)],
        worktree,
    )
    print(output)
    if stderr:
        print(stderr, file=sys.stderr)
    if code != 0:
        print(f"\nRemote closure finalizer failed; worktree left intact: {worktree}", file=sys.stderr)
        return code

    # Remove the verified worktree first. Keep the reservation if removal fails
    # so cleanup remains attributable and retryable.
    cleanup_code, cleanup_error = remove_worktree_then_reservation(repo_root, worktree, ref)
    if cleanup_code != 0:
        print(cleanup_error, file=sys.stderr)
        return 1
    print(f"Closed agent worktree: {worktree}")
    return 0


def remove_worktree_safe(repo_root: Path, worktree_path: Path) -> None:
    """Remove a worktree after verifying it lives under repo-root/.worktrees/."""
    resolved = worktree_path.resolve()
    allowed_root = (repo_root / WORKTREE_DIR).resolve()
    if not str(resolved).startswith(str(allowed_root) + os.sep) and resolved != allowed_root:
        raise RuntimeError(f"Refusing to remove path outside {allowed_root}: {resolved}")

    code, _, stderr = run_command(["git", "worktree", "remove", "--force", str(resolved)], repo_root)
    if code != 0:
        raise RuntimeError(f"Failed to remove worktree {resolved}: {stderr}")

    # Prune leftover registration.
    run_command(["git", "worktree", "prune"], repo_root)


def remove_worktree_then_reservation(repo_root: Path, worktree: Path, ref: str) -> tuple[int, str]:
    """Close local ownership without discarding attribution on removal failure."""
    try:
        remove_worktree_safe(repo_root, worktree)
    except RuntimeError as exc:
        return 1, f"{exc}; reservation retained: {ref}"
    code, _, error = run_command(["git", "update-ref", "-d", ref], repo_root)
    if code != 0:
        return 1, f"Worktree removed but reservation cleanup failed for {ref}: {error}"
    return 0, ""


def list_reservations(repo: Path) -> list[tuple[str, str, dict]]:
    """Return list of (branch, sha, context) for reservation refs.

    Reservation context is stored as the reflog message of the ref and
    retrieved with git log -g.
    """
    code, stdout, _ = run_command(
        ["git", "for-each-ref", "--format=%(refname) %(objectname)", RESERVATION_REF_PREFIX],
        repo,
    )
    if code != 0:
        return []
    results: list[tuple[str, str, dict]] = []
    for line in stdout.splitlines():
        parts = line.split(" ", 1)
        if len(parts) < 2:
            continue
        refname, sha = parts[0], parts[1]
        branch = refname.removeprefix(RESERVATION_REF_PREFIX)
        context_text = git_value(repo, ["log", "-g", "-1", "--format=%gs", refname], fallback="{}")
        try:
            context = json.loads(context_text)
        except json.JSONDecodeError:
            context = {}
        results.append((branch, sha, context))
    return results


def list_worktrees(repo: Path) -> dict[str, dict]:
    """Return {branch: {path, head, bare}} from git worktree list --porcelain."""
    code, stdout, _ = run_command(["git", "worktree", "list", "--porcelain"], repo)
    if code != 0:
        return {}
    worktrees: dict[str, dict] = {}
    current: dict = {}
    for line in stdout.splitlines():
        if not line:
            if current.get("branch"):
                worktrees[current["branch"]] = current
            current = {}
            continue
        if line.startswith("worktree "):
            current["path"] = line.removeprefix("worktree ").strip()
        elif line.startswith("HEAD "):
            current["head"] = line.removeprefix("HEAD ").strip()
        elif line.startswith("branch "):
            current["branch"] = line.removeprefix("branch ").strip()
        elif line == "bare":
            current["bare"] = True
    if current.get("branch"):
        worktrees[current["branch"]] = current
    return worktrees


def is_merged(repo: Path, branch: str, default_branch: str) -> bool:
    code, _, _ = run_command(["git", "merge-base", "--is-ancestor", branch, default_branch], repo)
    return code == 0


def cmd_cleanup(args: argparse.Namespace) -> int:
    repo = Path(args.repo).resolve()
    code, repo, error = resolve_repo(repo)
    if code != 0:
        print(f"StateDD Agent Worktree Cleanup\n\nBlocking problems\n- {error}", file=sys.stderr)
        return 2

    default_branch = origin_default_branch(repo)
    reservations = list_reservations(repo)
    worktrees = list_worktrees(repo)

    if args.force:
        branch = args.force.strip()
        ref = reservation_ref(branch)
        wt_path = worktree_path_for_branch(repo, branch)
        if args.dry_run:
            print(f"DRY RUN: would remove worktree and reservation for {branch}")
            return 0
        if f"refs/heads/{branch}" in worktrees:
            try:
                remove_worktree_safe(repo, wt_path)
            except RuntimeError as exc:
                print(str(exc), file=sys.stderr)
                return 1
        run_command(["git", "update-ref", "-d", ref], repo)
        run_command(["git", "branch", "-D", branch], repo)
        print(f"Removed reservation and branch: {branch}")
        return 0

    stale: list[tuple[str, Path | None, str]] = []
    for branch, sha, context in reservations:
        wt_path = worktree_path_for_branch(repo, branch)
        info = worktrees.get(f"refs/heads/{branch}")
        if info is None:
            stale.append((branch, None, "no linked worktree"))
        elif is_merged(repo, branch, default_branch):
            stale.append((branch, Path(info["path"]), f"merged to {default_branch}"))

    if args.stale_only:
        print("StateDD Agent Worktree Cleanup (stale-only listing)")
        if not stale:
            print("No stale reservations found.")
            return 0
        print("The following reservations would be removed with --force <branch>:")
        for branch, wt_path, reason in stale:
            print(f"- {branch}: {reason} ({wt_path or 'no worktree'})")
        return 0

    # Default cleanup without flags: show status and exit.
    print("StateDD Agent Worktree Cleanup")
    print("Use --stale-only to list stale entries or --force <branch> to remove one.")
    print()
    print(f"Reservations found: {len(reservations)}")
    for branch, sha, context in reservations:
        agent_id = context.get("agent_id", "unknown")
        slice_id = context.get("slice_id", "unknown")
        print(f"- {branch} (agent={agent_id}, slice={slice_id})")
    print()
    print(f"Stale reservations: {len(stale)}")
    for branch, wt_path, reason in stale:
        print(f"- {branch}: {reason}")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    repo = Path(args.repo).resolve()
    code, repo, error = resolve_repo(repo)
    if code != 0:
        print(f"StateDD Agent Worktree List\n\nBlocking problems\n- {error}", file=sys.stderr)
        return 2

    reservations = list_reservations(repo)
    worktrees = list_worktrees(repo)
    locks = detect_git_locks(repo)

    print("StateDD Agent Worktrees")
    print()
    print("Reservations")
    if reservations:
        for branch, sha, context in reservations:
            agent_id = context.get("agent_id", "unknown")
            slice_id = context.get("slice_id", "unknown")
            created = context.get("created_at", "unknown")
            print(f"- {branch}")
            print(f"  agent_id: {agent_id}")
            print(f"  slice_id: {slice_id}")
            print(f"  base_sha: {sha}")
            print(f"  created_at: {created}")
    else:
        print("- none")
    print()
    print("Worktrees")
    if worktrees:
        for branch, info in worktrees.items():
            print(f"- {branch}: {info.get('path')} (HEAD {info.get('head', 'unknown')})")
    else:
        print("- none")
    print()
    print("Git lock files")
    if locks:
        for lock in locks:
            print(f"- {lock}")
    else:
        print("- none")
    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="StateDD Parallel-Agent Worktree Orchestrator")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without executing git mutations")
    parser.add_argument("--repo", default=str(ROOT), help="Repo root (default: repository containing this script)")

    subparsers = parser.add_subparsers(dest="command", required=True)

    start = subparsers.add_parser("start", help="Create a new agent worktree")
    start.add_argument("--slice-id", required=True, help="Backlog slice identifier")
    start.add_argument("--agent-id", help="Agent identifier (default: env STATEDD_AGENT_ID or uuid4 fragment)")
    start.add_argument("--base", help="Base branch/ref (default: repo default branch, then current branch)")
    start.add_argument("--branch", help="Override computed branch name")
    start.add_argument("--wait", action="store_true", help="Wait briefly if git locks are held")

    guard = subparsers.add_parser("guard", help="Run worktree guard in agent context")
    guard.add_argument("--mode", choices=("start-slice", "closure"), default="start-slice", help="Guard mode")
    guard.add_argument("--worktree", help="Agent worktree path (default: current directory)")

    handoff = subparsers.add_parser("handoff", help="Generate handoff snapshot in agent context")
    handoff.add_argument("--worktree", help="Agent worktree path (default: current directory)")
    handoff.add_argument("--release", action="store_true", help="Also release the reservation ref")

    close = subparsers.add_parser("close", help="Push branch and finalize remote closure")
    close.add_argument("--pr", type=int, required=True, help="Pull request number")
    close.add_argument("--worktree", help="Agent worktree path (default: current directory)")
    close.add_argument("--wait", action="store_true", help="Wait briefly if git locks are held")

    cleanup = subparsers.add_parser("cleanup", help="Remove stale or forced agent worktrees")
    cleanup.add_argument("--stale-only", action="store_true", help="List stale reservations without removing")
    cleanup.add_argument("--force", help="Remove reservation and worktree for this branch")

    list_cmd = subparsers.add_parser("list", help="List active agent worktrees and reservations")

    return parser.parse_args(argv[1:])


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv)
    try:
        if args.command == "start":
            return cmd_start(args)
        if args.command == "guard":
            return cmd_guard(args)
        if args.command == "handoff":
            return cmd_handoff(args)
        if args.command == "close":
            return cmd_close(args)
        if args.command == "cleanup":
            return cmd_cleanup(args)
        if args.command == "list":
            return cmd_list(args)
        print(f"Unknown command: {args.command}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"Unexpected error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
