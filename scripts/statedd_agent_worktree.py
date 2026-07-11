#!/usr/bin/env python3
"""StateDD strong-isolation orchestrator for independent coding agents.

``start`` defaults to a full clone with an independent object database. Linked
worktrees remain available only through explicit same-machine opt-in after the
central Git safety preflight passes. ``cleanup`` is intentionally report-only:
this tool never force-removes, prunes, resets, or deletes affected Git state.

Exit codes:
  0 = requested diagnostic/operation succeeded
  1 = safety or operational failure; leave repository state intact
  2 = invalid context or unexpected runtime error
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path
from typing import Any

from statedd_git_safety_session import (
    MutationBlocked,
    require_mutation_permit,
    record_required_git_failure,
    sanitized_git_environment,
)


ROOT = Path(__file__).resolve().parents[1]
GIT_SAFETY_SCRIPT = ROOT / "scripts" / "statedd_git_safety_check.py"
AGENT_CONTEXT_SCHEMA = "statedd.agent_context.v2"
RESERVATION_REF_PREFIX = "refs/statedd/reservations/"
WORKTREE_DIR = ".worktrees"
LOCK_FILES = ("index.lock", "config.lock", "packed-refs.lock", "shallow.lock")


def run_command(args: list[str], cwd: Path) -> tuple[int, str, str]:
    try:
        completed = subprocess.run(
            args,
            cwd=cwd,
            env=sanitized_git_environment(),
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        return 127, "", str(exc)
    return completed.returncode, completed.stdout.rstrip(), completed.stderr.rstrip()


def required_command(args: list[str], cwd: Path, label: str) -> str:
    code, stdout, stderr = run_command(args, cwd)
    if code != 0:
        raise RuntimeError(f"{label} failed ({code}): {stderr or stdout or 'no diagnostic'}")
    return stdout


def resolve_repo(path: Path) -> Path:
    output = required_command(["git", "rev-parse", "--show-toplevel"], path, "repository resolution")
    return Path(output).resolve()


def git_path(repo: Path, selector: str) -> Path:
    output = required_command(["git", "rev-parse", selector], repo, f"git {selector}")
    path = Path(output)
    return path.resolve() if path.is_absolute() else (repo / path).resolve()


def git_common_dir(repo: Path) -> Path:
    return git_path(repo, "--git-common-dir")


def detect_git_locks(repo: Path) -> list[Path]:
    common = git_common_dir(repo)
    locks: list[Path] = []
    for name in LOCK_FILES:
        candidate = common / name
        if candidate.exists():
            locks.append(candidate)
    refs = common / "refs"
    if refs.exists():
        locks.extend(path for path in refs.rglob("*.lock") if path.is_file())
    return sorted(set(locks))


def check_locks_or_fail(repo: Path) -> int:
    locks = detect_git_locks(repo)
    if not locks:
        return 0
    for lock in locks:
        print(f"Another git operation holds {lock}; diagnose and retry.", file=sys.stderr)
    return 1


def base36_encode(value: int, width: int = 5) -> str:
    if value < 0:
        raise ValueError("value must be non-negative")
    chars: list[str] = []
    while value or not chars:
        value, remainder = divmod(value, 36)
        chars.append("0123456789abcdefghijklmnopqrstuvwxyz"[remainder])
    return "".join(reversed(chars)).zfill(width)


def generate_agent_id() -> tuple[str, str]:
    env_id = os.environ.get("STATEDD_AGENT_ID", "").strip()
    if env_id:
        return env_id, env_id[:4].lower()
    short = uuid.uuid4().hex[:4].lower()
    return f"agent-{short}", short


def compute_branch_name(slice_id: str, agent_short_id: str) -> str:
    # A UUID-derived nonce avoids timing/sleep-based coordination.
    nonce = base36_encode(int(uuid.uuid4().hex[:8], 16) % (36**5), 5)
    clean_slice = "".join(char if char.isalnum() else "-" for char in slice_id.lower()).strip("-")
    return f"bl-{clean_slice}-{agent_short_id}-{nonce}"


def reservation_ref(branch: str) -> str:
    return f"{RESERVATION_REF_PREFIX}{branch}"


def worktree_path_for_branch(repo: Path, branch: str) -> Path:
    return (repo / WORKTREE_DIR / branch).resolve()


def clone_path_for_branch(repo: Path, branch: str) -> Path:
    return (repo.parent / ".statedd-clones" / repo.name / branch).resolve()


def main_worktree_root(repo: Path) -> Path:
    output = required_command(
        ["git", "worktree", "list", "--porcelain"],
        repo,
        "worktree topology inspection",
    )
    for line in output.splitlines():
        if line.startswith("worktree "):
            return Path(line.removeprefix("worktree ")).resolve()
    raise RuntimeError("worktree topology inspection returned no main worktree")


def current_branch(repo: Path) -> str:
    branch = required_command(["git", "branch", "--show-current"], repo, "current branch inspection")
    if not branch:
        raise RuntimeError("detached HEAD cannot be used for agent isolation")
    return branch


def origin_default_branch(repo: Path) -> str:
    code, stdout, _ = run_command(
        ["git", "symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD"], repo
    )
    if code == 0 and stdout.startswith("origin/"):
        return stdout.removeprefix("origin/")
    for candidate in ("main", "master"):
        code, _, _ = run_command(
            ["git", "show-ref", "--verify", "--quiet", f"refs/remotes/origin/{candidate}"], repo
        )
        if code == 0:
            return candidate
    return ""


def resolve_base_ref(repo: Path, explicit_base: str | None, safety_report: dict[str, Any]) -> tuple[str, str]:
    if explicit_base:
        base = explicit_base.strip()
    else:
        default = safety_report.get("repository", {}).get("default_branch", "")
        base = f"origin/{default}" if default and default != "not proven" else current_branch(repo)
    code, stdout, _ = run_command(["git", "rev-parse", "--verify", base], repo)
    if code != 0 or not stdout:
        raise RuntimeError(f"base ref could not be resolved after mandatory synchronization: {base}")
    return base, stdout


def run_git_safety(
    repo: Path,
    mode: str,
    *,
    source_repo: Path | None = None,
    worktree_opt_in: bool = False,
    trusted_local_machine: bool = False,
    restart_session: bool = False,
    operation_class: str = "local_mutation",
    operator_authorized: bool = False,
    context: dict[str, Any] | None = None,
) -> tuple[int, dict[str, Any], str]:
    command = [
        sys.executable,
        str(GIT_SAFETY_SCRIPT),
        "--repo",
        str(repo),
        "--mode",
        mode,
        "--format",
        "json",
    ]
    if source_repo is not None:
        command.extend(["--source-repo", str(source_repo)])
    if worktree_opt_in:
        command.append("--worktree-opt-in")
    if trusted_local_machine:
        command.append("--trusted-local-machine")
    command.extend(["--operation-class", operation_class])
    if operator_authorized:
        command.append("--operator-authorized")
    if context:
        command.extend(
            [
                "--slice-id", str(context["slice_id"]),
                "--agent-id", str(context["agent_id"]),
                "--context-hash", context_hash(context),
                "--reservation-ref", str(context["reservation_ref"]),
                "--expected-branch", str(context["branch"]),
                "--expected-head", required_command(["git", "rev-parse", "HEAD"], repo, "context HEAD inspection"),
            ]
        )
    if restart_session:
        command.append("--restart-session")
    code, stdout, stderr = run_command(command, repo)
    if not stdout:
        return code, {}, stderr or "Git safety preflight emitted no JSON report"
    try:
        report = json.loads(stdout)
    except json.JSONDecodeError as exc:
        return 2, {}, f"invalid Git safety JSON: {exc}; stderr={stderr}"
    return code, report, stderr


def print_safety_failure(report: dict[str, Any], fallback: str) -> None:
    print("Git safety preflight blocked writable isolation.", file=sys.stderr)
    blockers = report.get("decision", {}).get("blockers", []) if report else []
    for blocker in blockers:
        print(f"- {blocker}", file=sys.stderr)
    if not blockers and fallback:
        print(f"- {fallback}", file=sys.stderr)
    if report:
        print(
            f"Effective mode: {report.get('decision', {}).get('effective_mode', 'read_only')}; "
            "diagnosis only until repaired and explicitly restarted.",
            file=sys.stderr,
        )


CONTEXT_KEYS = {
    "schema", "agent_id", "slice_id", "reservation_ref", "worktree_path", "branch",
    "base_branch", "created_at", "isolation_mode", "source_repo", "identity",
    "attestations", "git_safety",
}
IDENTITY_KEYS = {"effective_uid", "effective_gid", "machine_fingerprint_sha256"}
ATTESTATION_KEYS = {"worktree_opt_in", "trusted_local_machine", "effective_uid", "effective_gid", "machine_fingerprint_sha256"}
SAFETY_KEYS = {"schema", "generated_at", "mode", "mutation_permitted"}


def context_hash(context: dict[str, Any]) -> str:
    return hashlib.sha256((json.dumps(context, sort_keys=True) + "\n").encode("utf-8")).hexdigest()


def reject_symlink_components(path: Path) -> None:
    absolute = Path(os.path.abspath(path))
    current = Path(absolute.anchor)
    for component in absolute.parts[1:]:
        current /= component
        if current.is_symlink():
            raise ValueError(f"symlinked context path component is not allowed: {current}")


def strict_json_object(text: str, source: Path) -> dict[str, Any]:
    def pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key {key!r} in {source}")
            result[key] = value
        return result

    value = json.loads(text, object_pairs_hook=pairs)
    if not isinstance(value, dict):
        raise ValueError(f"agent context must be a JSON object: {source}")
    return value


def validate_context_shape(data: dict[str, Any], context_path: Path) -> str | None:
    if set(data) != CONTEXT_KEYS:
        unknown = sorted(set(data) - CONTEXT_KEYS)
        missing = sorted(CONTEXT_KEYS - set(data))
        return f"agent context fields are not closed-world (unknown={unknown}, missing={missing})"
    if data.get("schema") != AGENT_CONTEXT_SCHEMA:
        return f"unexpected agent context schema: {data.get('schema')}"
    for key in ("agent_id", "slice_id", "reservation_ref", "worktree_path", "branch", "base_branch", "created_at", "isolation_mode", "source_repo"):
        if not isinstance(data.get(key), str):
            return f"agent context field {key!r} must be a string"
    if not Path(data["worktree_path"]).is_absolute():
        return "agent context worktree_path must be absolute"
    for nested_key, nested_keys in (("identity", IDENTITY_KEYS), ("attestations", ATTESTATION_KEYS), ("git_safety", SAFETY_KEYS)):
        nested = data.get(nested_key)
        if not isinstance(nested, dict) or set(nested) != nested_keys:
            return f"agent context {nested_key} fields are not closed-world"
    if data["isolation_mode"] == "worktree":
        if data["reservation_ref"] != reservation_ref(data["branch"]):
            return "worktree reservation ref does not exactly match its branch"
        if data["attestations"]["worktree_opt_in"] is not True or data["attestations"]["trusted_local_machine"] is not True:
            return "worktree context lacks explicit trusted-local attestations"
    elif data["reservation_ref"]:
        return "clone/normal-branch context must not carry a reservation ref"
    return None


def load_agent_context(path: Path) -> tuple[int, dict[str, Any], str]:
    context_path = path / ".statedd" / "agent.context" if path.is_dir() else path
    try:
        reject_symlink_components(context_path)
        data = strict_json_object(context_path.read_text(encoding="utf-8"), context_path)
    except FileNotFoundError:
        return 2, {}, f"agent context not found: {context_path}"
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        return 2, {}, f"invalid agent context JSON: {exc}"
    error = validate_context_shape(data, context_path)
    if error:
        return 2, {}, error
    return 0, data, ""


def write_agent_context(target: Path, context: dict[str, Any]) -> None:
    statedd_dir = target / ".statedd"
    statedd_dir.mkdir(parents=True, exist_ok=True)
    context_path = statedd_dir / "agent.context"
    descriptor, temporary_name = tempfile.mkstemp(prefix="agent.context.", dir=statedd_dir)
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        temporary.write_text(json.dumps(context, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(temporary, context_path)
    finally:
        temporary.unlink(missing_ok=True)


def verify_agent_context_binding(worktree: Path, context: dict[str, Any]) -> None:
    """Prove that context is owned by this exact repository and reservation."""
    worktree = Path(os.path.abspath(worktree))
    reject_symlink_components(worktree)
    if context["worktree_path"] != str(worktree):
        raise MutationBlocked("agent context worktree_path does not match the requested repository")
    if resolve_repo(worktree) != worktree:
        raise MutationBlocked("agent context does not resolve to the exact repository root")
    if current_branch(worktree) != context["branch"]:
        raise MutationBlocked("agent context branch does not match the checked-out branch")
    if context["isolation_mode"] == "clone":
        source_repo = Path(context["source_repo"])
        if not source_repo.is_absolute():
            raise MutationBlocked("clone agent context source_repo must be absolute")
    if context["isolation_mode"] == "worktree":
        topology = required_command(["git", "worktree", "list", "--porcelain"], worktree, "worktree ownership inspection")
        registered = False
        for block in topology.split("\n\n"):
            lines = block.splitlines()
            registered_path = next((line.removeprefix("worktree ") for line in lines if line.startswith("worktree ")), "")
            registered_branch = next((line.removeprefix("branch ").removeprefix("refs/heads/") for line in lines if line.startswith("branch ")), "")
            if registered_path == str(worktree) and registered_branch == context["branch"]:
                registered = True
                break
        if not registered:
            raise MutationBlocked("agent context is not bound to the registered Git worktree")
        message_code, message, message_error = run_command(
            ["git", "log", "-g", "-1", "--format=%gs", context["reservation_ref"]], worktree
        )
        expected_message = json.dumps(context, sort_keys=True)
        if message_code != 0 or message != expected_message:
            raise MutationBlocked(
                "agent context reservation reflog payload does not match this context"
                + (f": {message_error or message}" if message_error or message else "")
            )
    identity = context["identity"]
    if identity["effective_uid"] != getattr(os, "geteuid", lambda: None)():
        raise MutationBlocked("agent context effective UID does not match the current process")
    if identity["effective_gid"] != getattr(os, "getegid", lambda: None)():
        raise MutationBlocked("agent context effective GID does not match the current process")


def context_payload(
    *,
    agent_id: str,
    slice_id: str,
    target: Path,
    branch: str,
    base: str,
    isolation_mode: str,
    reservation: str,
    source_repo: Path,
    safety_report: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema": AGENT_CONTEXT_SCHEMA,
        "agent_id": agent_id,
        "slice_id": slice_id,
        "reservation_ref": reservation,
        "worktree_path": str(target),
        "branch": branch,
        "base_branch": base,
        "created_at": dt.datetime.now(dt.timezone.utc).astimezone().isoformat(timespec="seconds"),
        "isolation_mode": isolation_mode,
        "source_repo": str(source_repo),
        "identity": {
            "effective_uid": safety_report.get("identity", {}).get("effective_uid"),
            "effective_gid": safety_report.get("identity", {}).get("effective_gid"),
            "machine_fingerprint_sha256": safety_report.get("runtime", {}).get(
                "machine_fingerprint_sha256"
            ),
        },
        "attestations": {
            "worktree_opt_in": isolation_mode == "worktree",
            "trusted_local_machine": isolation_mode == "worktree",
            "effective_uid": safety_report.get("identity", {}).get("effective_uid"),
            "effective_gid": safety_report.get("identity", {}).get("effective_gid"),
            "machine_fingerprint_sha256": safety_report.get("runtime", {}).get(
                "machine_fingerprint_sha256"
            ),
        },
        "git_safety": {
            "schema": safety_report.get("schema"),
            "generated_at": safety_report.get("generated_at"),
            "mode": safety_report.get("decision", {}).get("effective_mode"),
            "mutation_permitted": safety_report.get("decision", {}).get("mutation_permitted"),
        },
    }


def cmd_start_worktree(args: argparse.Namespace, source: Path, slice_id: str, agent_id: str, short_id: str) -> int:
    if not args.worktree_opt_in or not args.trusted_local_machine:
        print(
            "Managed worktree creation is disabled by default; both --worktree-opt-in "
            "and --trusted-local-machine are required.",
            file=sys.stderr,
        )
        return 1
    source = main_worktree_root(source)
    if check_locks_or_fail(source):
        return 1
    code, report, error = run_git_safety(
        source,
        "worktree",
        worktree_opt_in=True,
        trusted_local_machine=True,
        restart_session=args.restart_session,
    )
    if code != 0 or not report.get("decision", {}).get("mutation_permitted"):
        print_safety_failure(report, error)
        return 1 if code != 2 else 2

    branch = args.branch or compute_branch_name(slice_id, short_id)
    target = Path(args.target).resolve() if args.target else worktree_path_for_branch(source, branch)
    ref = reservation_ref(branch)
    base, base_commit = resolve_base_ref(source, args.base, report)
    code, existing, _ = run_command(["git", "rev-parse", "--verify", "--quiet", ref], source)
    if code == 0 and existing:
        print(f"Reservation ref already exists: {ref}", file=sys.stderr)
        return 1
    code, existing, _ = run_command(["git", "rev-parse", "--verify", "--quiet", branch], source)
    if code == 0 and existing:
        print(f"Branch already exists: {branch}", file=sys.stderr)
        return 1
    if target.exists():
        print(f"Worktree path already exists: {target}", file=sys.stderr)
        return 1

    code, _, stderr = run_command(
        ["git", "worktree", "add", "-b", branch, str(target), base],
        source,
    )
    if code != 0:
        latch_error = record_required_git_failure(source, "git worktree add", stderr)
        print(f"Failed to create worktree {target}: {stderr}", file=sys.stderr)
        if latch_error:
            print(f"Read-only latch persistence failed: {latch_error}", file=sys.stderr)
        print("No automatic rollback was attempted; inspect the reported topology read-only.", file=sys.stderr)
        return 1

    context = context_payload(
        agent_id=agent_id,
        slice_id=slice_id,
        target=target,
        branch=branch,
        base=base,
        isolation_mode="worktree",
        reservation=ref,
        source_repo=source,
        safety_report=report,
    )
    try:
        write_agent_context(target, context)
    except OSError as exc:
        latch_error = record_required_git_failure(target, "agent context write", str(exc))
        print(f"Worktree was created but agent context write failed: {exc}", file=sys.stderr)
        if latch_error:
            print(f"Read-only latch persistence failed: {latch_error}", file=sys.stderr)
        print(f"Left intact for diagnosis: {target}", file=sys.stderr)
        return 2
    context_json = json.dumps(context, sort_keys=True)
    code, _, stderr = run_command(
        ["git", "update-ref", "--create-reflog", "-m", context_json, ref, base_commit],
        source,
    )
    if code != 0:
        latch_error = record_required_git_failure(source, "git update-ref reservation", stderr)
        print(f"Worktree was created but reservation ref failed: {stderr}", file=sys.stderr)
        if latch_error:
            print(f"Read-only latch persistence failed: {latch_error}", file=sys.stderr)
        print(f"Left intact for diagnosis: {target}", file=sys.stderr)
        return 1
    print(f"Agent worktree ready: {target}")
    print(f"Branch: {branch}")
    print("Isolation mode: worktree (explicit trusted-local opt-in; shared common directory)")
    return 0


def cmd_start_clone(args: argparse.Namespace, source: Path, slice_id: str, agent_id: str, short_id: str) -> int:
    code, source_report, error = run_git_safety(source, "read_only")
    if code != 0:
        print_safety_failure(source_report, error)
        return 2 if code == 2 else 1
    if source_report.get("fsck", {}).get("result") != "pass":
        print("Source repository fsck failed; clone provisioning is blocked.", file=sys.stderr)
        return 1
    if source_report.get("runtime", {}).get("git_environment_overrides"):
        print("Redirecting Git environment blocks clone provisioning.", file=sys.stderr)
        return 1
    source_metadata = source_report.get("metadata", {})
    if not source_metadata.get("scan_complete") or source_metadata.get("unreadable") or source_metadata.get("symlinks"):
        print("Source repository cannot be read reliably enough to provision a clone.", file=sys.stderr)
        return 1

    branch = args.branch or compute_branch_name(slice_id, short_id)
    default = source_report.get("repository", {}).get("default_branch", "")
    base = (args.base or default).removeprefix("origin/")
    if not base or base == "not proven":
        print("Clone base branch is not proven; pass --base explicitly.", file=sys.stderr)
        return 1
    target = Path(args.target).resolve() if args.target else clone_path_for_branch(source, branch)
    if target.exists():
        print(f"Clone target already exists: {target}", file=sys.stderr)
        return 1
    source_url = source_report.get("repository", {}).get("origin_url", "")
    if not source_url or source_url.startswith("not proven"):
        source_url = str(source)

    target.parent.mkdir(parents=True, exist_ok=True)
    code, _, stderr = run_command(
        [
            "git",
            "clone",
            "--no-local",
            "--no-hardlinks",
            "--branch",
            base,
            source_url,
            str(target),
        ],
        source,
    )
    if code != 0:
        latch_error = record_required_git_failure(source, "git clone", stderr)
        print(f"Full clone failed: {stderr}", file=sys.stderr)
        if latch_error:
            print(f"Read-only latch persistence failed: {latch_error}", file=sys.stderr)
        print(f"Any partial target is left intact for read-only diagnosis: {target}", file=sys.stderr)
        return 1
    code, _, stderr = run_command(["git", "switch", "-c", branch], target)
    if code != 0:
        latch_error = record_required_git_failure(target, "git switch feature branch", stderr)
        print(f"Clone exists but feature branch creation failed: {stderr}", file=sys.stderr)
        if latch_error:
            print(f"Read-only latch persistence failed: {latch_error}", file=sys.stderr)
        print(f"Left intact for read-only diagnosis: {target}", file=sys.stderr)
        return 1

    code, report, error = run_git_safety(
        target,
        "clone",
        source_repo=source,
        restart_session=args.restart_session,
    )
    if code != 0 or not report.get("decision", {}).get("mutation_permitted"):
        print_safety_failure(report, error)
        print(f"Clone left intact in read-only state: {target}", file=sys.stderr)
        return 1 if code != 2 else 2

    context = context_payload(
        agent_id=agent_id,
        slice_id=slice_id,
        target=target,
        branch=branch,
        base=f"origin/{base}",
        isolation_mode="clone",
        reservation="",
        source_repo=source,
        safety_report=report,
    )
    try:
        write_agent_context(target, context)
    except OSError as exc:
        latch_error = record_required_git_failure(target, "agent context write", str(exc))
        print(f"Clone is safe but agent context write failed: {exc}", file=sys.stderr)
        if latch_error:
            print(f"Read-only latch persistence failed: {latch_error}", file=sys.stderr)
        print(f"Left intact for diagnosis: {target}", file=sys.stderr)
        return 2
    print(f"Agent clone ready: {target}")
    print(f"Branch: {branch}")
    print("Isolation mode: clone (independent Git common directory/object database)")
    return 0


def cmd_start(args: argparse.Namespace) -> int:
    source = resolve_repo(Path(args.repo))
    slice_id = (args.slice_id or "").strip()
    if not slice_id:
        print("--slice-id is required", file=sys.stderr)
        return 1
    agent_id, short_id = generate_agent_id()
    if args.agent_id:
        agent_id = args.agent_id.strip()
        short_id = agent_id[:4].lower()
    branch = args.branch or compute_branch_name(slice_id, short_id)
    isolation_mode = args.isolation_mode

    if args.dry_run:
        target = (
            Path(args.target).resolve()
            if args.target
            else worktree_path_for_branch(source, branch)
            if isolation_mode == "worktree"
            else clone_path_for_branch(source, branch)
        )
        print("DRY RUN: no Git or filesystem mutation performed")
        print(f"  requested isolation mode: {isolation_mode}")
        print(f"  branch: {branch}")
        print(f"  target: {target}")
        print("  execution will require the centralized Git safety preflight")
        return 0

    if isolation_mode == "read_only":
        code, report, error = run_git_safety(source, "read_only")
        if code == 2:
            print_safety_failure(report, error)
            return 2
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0
    if isolation_mode == "normal_branch":
        code, report, error = run_git_safety(
            source,
            "normal_branch",
            restart_session=args.restart_session,
        )
        if code != 0:
            print_safety_failure(report, error)
            return 1 if code != 2 else 2
        print(f"Normal feature branch ready: {source}")
        print(f"Branch: {report['repository']['branch']}")
        return 0
    if isolation_mode == "worktree":
        return cmd_start_worktree(args, source, slice_id, agent_id, short_id)
    return cmd_start_clone(args, source, slice_id, agent_id, short_id)


def dirty_files(repo: Path) -> list[str]:
    output = required_command(
        ["git", "--no-optional-locks", "status", "--porcelain=v1", "--untracked-files=all"],
        repo,
        "dirty-state inspection",
    )
    paths: list[str] = []
    for line in output.splitlines():
        if not line:
            continue
        path = line[3:] if len(line) > 3 else line
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        paths.append(path)
    return paths


def safety_for_context(
    worktree: Path,
    context: dict[str, Any],
    restart_session: bool,
    *,
    operation_class: str = "local_mutation",
    operator_authorized: bool = False,
) -> tuple[int, dict[str, Any], str]:
    mode = context.get("isolation_mode", "worktree")
    if mode not in {"clone", "worktree", "normal_branch"}:
        return 2, {}, f"agent context is not writable: isolation_mode={mode}"
    attestations = context.get("attestations", {})
    source_value = context.get("source_repo")
    source = Path(source_value).resolve() if source_value and mode == "clone" else None
    code, report, error = run_git_safety(
        worktree,
        mode,
        source_repo=source,
        worktree_opt_in=mode == "worktree" and attestations.get("worktree_opt_in") is True,
        trusted_local_machine=mode == "worktree" and attestations.get("trusted_local_machine") is True,
        restart_session=restart_session,
        operation_class=operation_class,
        operator_authorized=operator_authorized,
        context=context,
    )
    if code == 0 and report:
        stored = context.get("identity", {})
        fresh_identity = report.get("identity", {})
        fresh_runtime = report.get("runtime", {})
        comparisons = {
            "effective_uid": fresh_identity.get("effective_uid"),
            "effective_gid": fresh_identity.get("effective_gid"),
            "machine_fingerprint_sha256": fresh_runtime.get("machine_fingerprint_sha256"),
        }
        mismatches = [key for key, value in comparisons.items() if stored.get(key) != value]
        if mismatches:
            report.setdefault("decision", {}).setdefault("blockers", []).append(
                "agent context identity/host mismatch: " + ", ".join(mismatches)
            )
            report["decision"]["permitted"] = False
            report["decision"]["mutation_permitted"] = False
            report["decision"]["effective_mode"] = "read_only"
            report["decision"]["restart_required"] = True
            return 1, report, "agent context identity/host mismatch"
    return code, report, error


def cmd_guard(args: argparse.Namespace) -> int:
    worktree = Path(os.path.abspath(args.worktree)) if args.worktree else Path.cwd().resolve()
    code, context, error = load_agent_context(worktree)
    if code:
        print(error, file=sys.stderr)
        return 2
    try:
        verify_agent_context_binding(worktree, context)
    except (MutationBlocked, RuntimeError) as exc:
        print(f"Agent context ownership verification failed: {exc}", file=sys.stderr)
        return 1
    safety_code, report, safety_error = safety_for_context(worktree, context, args.restart_session)
    if safety_code != 0 or not report.get("decision", {}).get("mutation_permitted"):
        print_safety_failure(report, safety_error)
        return 1 if safety_code != 2 else 2
    changed = dirty_files(worktree)
    if args.mode == "closure" and changed:
        print("Closure mode requires a clean worktree.", file=sys.stderr)
        return 1
    print("StateDD Agent Isolation Guard")
    print(f"Mode: {args.mode}")
    print(f"Agent context: {context.get('agent_id')} / {context.get('slice_id')}")
    print(f"Isolation mode: {context.get('isolation_mode', 'worktree')}")
    print(f"Git safety mutation permit: {report['decision']['mutation_permitted']}")
    print(f"Git common dir: {report['repository']['git_common_dir']}")
    print(f"Linked worktree count: {report['worktrees']['linked_count']}")
    print("Dirty files:")
    for path in changed or ["none"]:
        print(f"- {path}")
    return 0


def cmd_handoff(args: argparse.Namespace) -> int:
    worktree = Path(os.path.abspath(args.worktree)) if args.worktree else Path.cwd().resolve()
    code, context, error = load_agent_context(worktree)
    if code:
        print(error, file=sys.stderr)
        return 2
    try:
        verify_agent_context_binding(worktree, context)
    except (MutationBlocked, RuntimeError) as exc:
        print(f"Agent context ownership verification failed: {exc}", file=sys.stderr)
        return 1
    if args.release:
        if not args.validated:
            print("Release refused: pass --validated only after the applicable local closure gate has passed.", file=sys.stderr)
            return 1
        changed = dirty_files(worktree)
        if changed:
            print("Release refused: worktree is dirty or unclassified; reservation retained.", file=sys.stderr)
            return 1
        safety_code, report, safety_error = safety_for_context(worktree, context, False)
        if safety_code != 0 or not report.get("decision", {}).get("mutation_permitted"):
            print_safety_failure(report, safety_error)
            return 1
        try:
            require_mutation_permit(
                worktree,
                "reservation release",
                authorization={
                    "slice_id": context["slice_id"],
                    "agent_id": context["agent_id"],
                    "context_hash": context_hash(context),
                    "reservation_ref": context["reservation_ref"],
                    "expected_branch": context["branch"],
                },
            )
        except MutationBlocked as exc:
            print(str(exc), file=sys.stderr)
            return 1
        if context["reservation_ref"]:
            code, _, stderr = run_command(["git", "update-ref", "-d", context["reservation_ref"]], worktree)
            if code != 0:
                latch_error = record_required_git_failure(worktree, "reservation release", stderr)
                print(f"Reservation release failed; state retained: {stderr}", file=sys.stderr)
                if latch_error:
                    print(f"Read-only latch persistence failed: {latch_error}", file=sys.stderr)
                return 1
        print("Reservation released after clean, validated local closure; worktree retained for explicit cleanup.")
        return 0
    handoff_script = ROOT / "scripts" / "statedd_handoff.py"
    code, output, stderr = run_command(
        [sys.executable, str(handoff_script), "--repo", str(worktree)], worktree
    )
    if output:
        print(output)
    if stderr:
        print(stderr, file=sys.stderr)
    return code


def cmd_close(args: argparse.Namespace) -> int:
    worktree = Path(os.path.abspath(args.worktree)) if args.worktree else Path.cwd().resolve()
    code, context, error = load_agent_context(worktree)
    if code:
        print(error, file=sys.stderr)
        return 2
    try:
        verify_agent_context_binding(worktree, context)
    except (MutationBlocked, RuntimeError) as exc:
        print(f"Agent context ownership verification failed: {exc}", file=sys.stderr)
        return 1
    if not args.pr or args.pr <= 0:
        print("--pr must be a positive integer", file=sys.stderr)
        return 1
    if args.dry_run:
        print("DRY RUN: would require explicit remote-mutation authorization, then push and invoke remote closure finalizer")
        print("No worktree, clone, branch, or reservation cleanup would occur.")
        return 0
    if not args.remote_mutation or not args.operator_authorized:
        print(
            "Remote push is disabled by default; pass --remote-mutation and "
            "--operator-authorized for this explicit remote-mutation path.",
            file=sys.stderr,
        )
        return 1
    if dirty_files(worktree):
        print("Remote push blocked: remote mutation requires a clean worktree.", file=sys.stderr)
        return 1
    safety_code, report, safety_error = safety_for_context(
        worktree,
        context,
        args.restart_session,
        operation_class="remote_mutation",
        operator_authorized=True,
    )
    if safety_code != 0 or not report.get("decision", {}).get("mutation_permitted"):
        print_safety_failure(report, safety_error)
        return 1 if safety_code != 2 else 2
    branch = context.get("branch", "")
    expected_head = required_command(["git", "rev-parse", "HEAD"], worktree, "exact push head inspection")
    if report.get("repository", {}).get("branch") != branch or report.get("repository", {}).get("head") != expected_head:
        print("Remote push blocked: branch or HEAD changed after the centralized safety decision.", file=sys.stderr)
        return 1
    try:
        require_mutation_permit(
            worktree,
            "remote push",
            operation_class="remote_mutation",
            authorization={
                "slice_id": context["slice_id"],
                "agent_id": context["agent_id"],
                "context_hash": context_hash(context),
                "reservation_ref": context["reservation_ref"],
                "expected_branch": branch,
                "expected_head": expected_head,
            },
        )
    except MutationBlocked as exc:
        print(str(exc), file=sys.stderr)
        return 1
    code, _, stderr = run_command(["git", "push", "origin", f"HEAD:refs/heads/{branch}"], worktree)
    if code != 0:
        latch_error = record_required_git_failure(
            worktree,
            "git push",
            stderr,
            binding={
                "branch": branch,
                "head": expected_head,
                "slice_id": context["slice_id"],
                "agent_id": context["agent_id"],
                "context_hash": context_hash(context),
                "reservation_ref": context["reservation_ref"],
                "worktree_clean": True,
            },
        )
        print(f"Push failed; isolation path retained: {stderr}", file=sys.stderr)
        if latch_error:
            print(f"Read-only latch persistence failed: {latch_error}", file=sys.stderr)
        return 1
    finalizer = ROOT / "scripts" / "statedd_remote_closure_finalizer.py"
    code, output, stderr = run_command(
        [sys.executable, str(finalizer), "--root", str(worktree), "--pr-number", str(args.pr)],
        worktree,
    )
    if output:
        print(output)
    if stderr:
        print(stderr, file=sys.stderr)
    if code != 0:
        print(f"Remote closure failed; isolation path retained: {worktree}", file=sys.stderr)
        return code
    print(f"Remote closure verified; isolation path retained for explicit human cleanup: {worktree}")
    return 0


def list_reservations(repo: Path) -> list[tuple[str, str, dict[str, Any]]]:
    output = required_command(
        ["git", "for-each-ref", "--format=%(refname) %(objectname)", RESERVATION_REF_PREFIX],
        repo,
        "reservation inspection",
    )
    results: list[tuple[str, str, dict[str, Any]]] = []
    for line in output.splitlines():
        refname, _, sha = line.partition(" ")
        if not refname or not sha:
            continue
        branch = refname.removeprefix(RESERVATION_REF_PREFIX)
        code, message, _ = run_command(["git", "log", "-g", "-1", "--format=%gs", refname], repo)
        try:
            context = json.loads(message) if code == 0 and message else {}
        except json.JSONDecodeError:
            context = {}
        results.append((branch, sha, context))
    return results


def list_worktrees(repo: Path) -> dict[str, dict[str, Any]]:
    output = required_command(
        ["git", "worktree", "list", "--porcelain"], repo, "worktree topology inspection"
    )
    worktrees: dict[str, dict[str, Any]] = {}
    current: dict[str, Any] = {}
    for line in [*output.splitlines(), ""]:
        if not line:
            key = current.get("branch") or current.get("path")
            if key:
                worktrees[str(key)] = current
            current = {}
        elif line.startswith("worktree "):
            current["path"] = line.removeprefix("worktree ")
        elif line.startswith("HEAD "):
            current["head"] = line.removeprefix("HEAD ")
        elif line.startswith("branch "):
            current["branch"] = line.removeprefix("branch ")
        elif line.startswith("locked"):
            current["locked"] = line.removeprefix("locked").strip() or True
        elif line.startswith("prunable"):
            current["prunable"] = line.removeprefix("prunable").strip() or True
    return worktrees


def is_merged(repo: Path, branch: str, default: str) -> bool:
    code, _, _ = run_command(["git", "merge-base", "--is-ancestor", branch, default], repo)
    return code == 0


def cmd_cleanup(args: argparse.Namespace) -> int:
    repo = resolve_repo(Path(args.repo))
    reservations = list_reservations(repo)
    worktrees = list_worktrees(repo)
    default = origin_default_branch(repo) or "main"
    print("StateDD Agent Isolation Cleanup Report (non-mutating)")
    print("No automatic deletion, force removal, branch deletion, or pruning is available.")
    print("Reservations:")
    for branch, sha, context in reservations or [("none", "", {})]:
        if branch == "none":
            print("- none")
            continue
        key = f"refs/heads/{branch}"
        worktree = worktrees.get(key)
        reasons: list[str] = []
        if worktree is None:
            reasons.append("no registered worktree")
        if is_merged(repo, branch, default):
            reasons.append(f"merged to {default}")
        print(
            f"- {branch}: head={sha} agent={context.get('agent_id', 'unknown')} "
            f"slice={context.get('slice_id', 'unknown')} status={', '.join(reasons) or 'active/not proven stale'}"
        )
    print("Worktrees:")
    for key, info in worktrees.items():
        print(
            f"- {key}: {info.get('path')} HEAD={info.get('head', 'not proven')} "
            f"locked={info.get('locked', False)} prunable={info.get('prunable', False)}"
        )
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    repo = resolve_repo(Path(args.repo))
    reservations = list_reservations(repo)
    worktrees = list_worktrees(repo)
    locks = detect_git_locks(repo)
    print("StateDD Agent Isolation Inventory")
    print("Reservations:")
    for branch, sha, context in reservations:
        print(f"- {branch}: {sha} agent={context.get('agent_id', 'unknown')}")
    if not reservations:
        print("- none")
    print("Worktrees:")
    for key, info in worktrees.items():
        print(f"- {key}: {info.get('path')} HEAD={info.get('head', 'not proven')}")
    print("Git lock files:")
    for lock in locks or ["none"]:
        print(f"- {lock}")
    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="StateDD agent strong-isolation orchestrator")
    parser.add_argument("--dry-run", action="store_true", help="Report intended action without preflight or mutation")
    parser.add_argument("--repo", default=str(ROOT), help="Source repository")
    subparsers = parser.add_subparsers(dest="command", required=True)

    start = subparsers.add_parser("start", help="Prepare an isolated agent session")
    start.add_argument("--slice-id", required=True)
    start.add_argument("--agent-id")
    start.add_argument("--base")
    start.add_argument("--branch")
    start.add_argument("--target")
    start.add_argument(
        "--isolation-mode",
        choices=("clone", "worktree", "normal_branch", "read_only"),
        default="clone",
        help="Default clone gives an independent object database; worktree is explicit opt-in",
    )
    start.add_argument("--worktree-opt-in", action="store_true")
    start.add_argument("--trusted-local-machine", action="store_true")
    start.add_argument("--restart-session", action="store_true")

    guard = subparsers.add_parser("guard", help="Run the central safety gate in agent context")
    guard.add_argument("--mode", choices=("start-slice", "closure"), default="start-slice")
    guard.add_argument("--worktree")
    guard.add_argument("--restart-session", action="store_true")

    handoff = subparsers.add_parser("handoff", help="Generate a handoff without releasing/deleting isolation state")
    handoff.add_argument("--worktree")
    handoff.add_argument("--release", action="store_true", help="Release only after a clean, validated session")
    handoff.add_argument("--validated", action="store_true", help="Assert that the applicable local closure gate passed")

    close = subparsers.add_parser("close", help="Push and run remote closure without automatic cleanup")
    close.add_argument("--pr", type=int, required=True)
    close.add_argument("--worktree")
    close.add_argument("--restart-session", action="store_true")
    close.add_argument("--remote-mutation", action="store_true", help="Explicitly select the remote-mutation path")
    close.add_argument("--operator-authorized", action="store_true", help="Explicit operator authorization for push")

    subparsers.add_parser("cleanup", help="Report stale/dirty isolation state; never remove it")
    subparsers.add_parser("list", help="List isolation paths, reservations, and locks")
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
        return 2
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Unexpected error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
