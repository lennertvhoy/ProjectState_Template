#!/usr/bin/env python3
"""Fail-closed Git identity, metadata, synchronization, and isolation preflight.

Writable modes perform one transaction: resolve strict Git identity, inspect the
Git common directory recursively, prove real writability, run fsck, fetch the
requested remote with automatic maintenance disabled, re-inspect metadata, and
then issue a mutation decision. Any failed mandatory operation selects and
externally latches ``read_only``. The script never repairs permissions or removes
repository/worktree state.

Exit codes:
  0 = requested mode established (read_only never permits mutation)
  1 = inspection completed but the requested writable mode is blocked
  2 = repository or report could not be inspected/validated reliably
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import platform
import secrets
import stat
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable

try:
    import grp
except ImportError:  # Non-POSIX identity is reported as unknown and fails closed.
    grp = None  # type: ignore[assignment]

try:
    import pwd
except ImportError:  # Non-POSIX identity is reported as unknown and fails closed.
    pwd = None  # type: ignore[assignment]

from statedd_git_safety_session import (
    MutationBlocked,
    active_git_environment_overrides,
    default_state_root,
    global_latch_path,
    latch_payload,
    machine_fingerprint,
    permit_payload,
    read_state,
    remove_state,
    sanitized_git_environment,
    state_lock,
    state_paths,
    write_state,
)


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_ID = "statedd.git_safety_report.v1"
SCHEMA_PATH = ROOT / "schemas" / "git_safety_report.schema.json"
WRITABLE_MODES = {"normal_branch", "worktree", "clone"}
OPERATION_CLASSES = {"read_only", "local_mutation", "remote_mutation"}
RISKY_CAPABILITIES = {
    0: "CAP_CHOWN",
    1: "CAP_DAC_OVERRIDE",
    2: "CAP_DAC_READ_SEARCH",
    3: "CAP_FOWNER",
    21: "CAP_SYS_ADMIN",
}


class InspectionError(RuntimeError):
    """A required Git or filesystem read failed."""


Runner = Callable[[list[str], Path, float], tuple[int, str, str]]


def run_command(args: list[str], cwd: Path, timeout: float = 30.0) -> tuple[int, str, str]:
    """Run a command without shell interpretation and preserve Git porcelain columns."""
    try:
        completed = subprocess.run(
            args,
            cwd=cwd,
            env=sanitized_git_environment(),
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
        )
    except FileNotFoundError as exc:
        return 127, "", str(exc)
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout if isinstance(exc.stdout, str) else ""
        stderr = exc.stderr if isinstance(exc.stderr, str) else ""
        return 124, stdout.rstrip(), (stderr or f"command timed out after {timeout:g}s").rstrip()
    return completed.returncode, completed.stdout.rstrip(), completed.stderr.rstrip()


def strict_git(repo: Path, args: list[str], *, timeout: float, runner: Runner = run_command) -> str:
    code, stdout, stderr = runner(["git", *args], repo, timeout)
    if code != 0:
        raise InspectionError(f"git {' '.join(args)} failed ({code}): {stderr or stdout or 'no diagnostic'}")
    return stdout


def resolve_git_path(repo: Path, value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = repo / path
    return path.resolve()


def resolve_repo_paths(requested: Path, *, timeout: float, runner: Runner = run_command) -> tuple[Path, Path, Path]:
    base = requested.resolve()
    root = Path(strict_git(base, ["rev-parse", "--show-toplevel"], timeout=timeout, runner=runner)).resolve()
    git_dir = resolve_git_path(root, strict_git(root, ["rev-parse", "--git-dir"], timeout=timeout, runner=runner))
    common_dir = resolve_git_path(
        root,
        strict_git(root, ["rev-parse", "--git-common-dir"], timeout=timeout, runner=runner),
    )
    return root, git_dir, common_dir


def user_name(uid: int | None) -> str:
    if uid is None or pwd is None:
        return "unknown"
    try:
        return pwd.getpwuid(uid).pw_name
    except (KeyError, OSError):
        return f"uid:{uid}"


def group_name(gid: int | None) -> str:
    if gid is None or grp is None:
        return "unknown"
    try:
        return grp.getgrgid(gid).gr_name
    except (KeyError, OSError):
        return f"gid:{gid}"


def collect_identity() -> dict[str, Any]:
    required = ("getuid", "geteuid", "getgid", "getegid", "getgroups")
    known = all(hasattr(os, name) for name in required) and pwd is not None and grp is not None
    real_uid = os.getuid() if hasattr(os, "getuid") else None
    effective_uid = os.geteuid() if hasattr(os, "geteuid") else None
    real_gid = os.getgid() if hasattr(os, "getgid") else None
    effective_gid = os.getegid() if hasattr(os, "getegid") else None
    supplementary = sorted(os.getgroups()) if hasattr(os, "getgroups") else []
    return {
        "real_uid": real_uid,
        "effective_uid": effective_uid,
        "real_gid": real_gid,
        "effective_gid": effective_gid,
        "supplementary_gids": supplementary,
        "user": user_name(effective_uid),
        "group": group_name(effective_gid),
        "known": known and effective_uid is not None and effective_gid is not None,
        "is_root": effective_uid == 0,
    }


def read_text_best_effort(path: Path, errors: list[str]) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        errors.append(f"{path}: {exc}")
        return ""


def collect_runtime(identity: dict[str, Any], requested: Path, *, timeout: float) -> dict[str, Any]:
    signals: list[str] = []
    errors: list[str] = []
    runtime_names: list[str] = []

    for marker, name in ((Path("/.dockerenv"), "docker"), (Path("/run/.containerenv"), "podman")):
        if marker.exists():
            signals.append(f"marker:{marker}")
            runtime_names.append(name)

    container_env = os.environ.get("container", "").strip()
    if container_env:
        signals.append("env:container")
        runtime_names.append(container_env)
    if os.environ.get("KUBERNETES_SERVICE_HOST"):
        signals.append("env:kubernetes")
        runtime_names.append("kubernetes")

    system = platform.system()
    if system == "Linux":
        for cgroup_path in (Path("/proc/self/cgroup"), Path("/proc/1/cgroup")):
            text = read_text_best_effort(cgroup_path, errors).lower()
            for token in ("docker", "kubepods", "containerd", "podman", "libpod", "lxc"):
                if token in text:
                    signals.append(f"cgroup:{token}")
                    runtime_names.append(token)

    host_evidence = False
    code, stdout, stderr = run_command(["systemd-detect-virt", "--container"], requested, timeout)
    detected = stdout.strip().lower()
    if code == 0 and detected and detected != "none":
        signals.append(f"systemd-detect-virt:{detected}")
        runtime_names.append(detected)
    elif code == 1 and detected in {"", "none"}:
        host_evidence = True
    elif code not in {0, 1, 127}:
        errors.append(f"systemd-detect-virt failed ({code}): {stderr or stdout}")
    if system in {"Darwin", "FreeBSD", "OpenBSD", "NetBSD"} and not signals:
        host_evidence = True

    cap_hex: str | None = None
    risky: list[str] = []
    capability_proven = system != "Linux"
    if system == "Linux":
        status_text = read_text_best_effort(Path("/proc/self/status"), errors)
        for line in status_text.splitlines():
            if line.startswith("CapEff:"):
                cap_hex = line.split(":", 1)[1].strip()
                try:
                    cap_value = int(cap_hex, 16)
                except ValueError:
                    errors.append(f"invalid CapEff value: {cap_hex}")
                    break
                risky = [name for bit, name in RISKY_CAPABILITIES.items() if cap_value & (1 << bit)]
                capability_proven = True
                break

    classification = "container" if signals else "host" if host_evidence else "unknown"
    if identity.get("is_root") or risky:
        privilege = "privileged"
    elif identity.get("known") and capability_proven:
        privilege = "unprivileged"
    else:
        privilege = "unknown"
    overrides = active_git_environment_overrides()

    return {
        "classification": classification,
        "container_runtime": sorted(set(runtime_names))[0] if runtime_names else None,
        "privilege": privilege,
        "proof_complete": classification != "unknown" and privilege != "unknown",
        "machine_fingerprint_sha256": machine_fingerprint(),
        "signals": sorted(set(signals)),
        "detection_errors": errors,
        "effective_capabilities_hex": cap_hex,
        "risky_capabilities": risky,
        "git_environment_overrides": overrides,
    }


def effective_access(path: Path, mode: int) -> bool:
    """Check access using effective IDs; inability to do so fails closed."""
    try:
        return os.access(
            path,
            mode,
            dir_fd=None,
            effective_ids=True,
            follow_symlinks=False,
        )
    except (NotImplementedError, TypeError, ValueError):
        return False


def path_record(
    path: Path,
    *,
    effective_uid: int | None,
    effective_gid: int | None,
    stat_fn: Callable[[os.PathLike[str] | str], Any] = os.lstat,
) -> dict[str, Any]:
    info = stat_fn(path)
    mode = info.st_mode
    is_dir = stat.S_ISDIR(mode)
    is_file = stat.S_ISREG(mode)
    is_symlink = stat.S_ISLNK(mode)
    kind = "directory" if is_dir else "file" if is_file else "symlink" if is_symlink else "other"
    return {
        "path": str(path),
        "kind": kind,
        "uid": info.st_uid,
        "gid": info.st_gid,
        "owner": user_name(info.st_uid),
        "group": group_name(info.st_gid),
        "mode_octal": f"{stat.S_IMODE(mode):04o}",
        "mode_symbolic": stat.filemode(mode),
        "readable": effective_access(path, os.R_OK),
        "writable": effective_access(path, os.W_OK),
        "searchable": effective_access(path, os.X_OK) if is_dir else None,
        "uid_matches": effective_uid is not None and info.st_uid == effective_uid,
        "gid_matches": effective_gid is not None and info.st_gid == effective_gid,
        "nlink": info.st_nlink,
    }


def issue(record: dict[str, Any], reason: str) -> dict[str, Any]:
    return {
        "path": record.get("path", "not proven"),
        "reason": reason,
        "uid": record.get("uid"),
        "gid": record.get("gid"),
        "mode_octal": record.get("mode_octal"),
    }


def scan_metadata_tree(
    root: Path,
    *,
    label: str,
    effective_uid: int | None,
    effective_gid: int | None,
    stat_fn: Callable[[os.PathLike[str] | str], Any] = os.lstat,
) -> dict[str, Any]:
    """Recursively inspect one critical Git metadata tree without following symlinks."""
    result: dict[str, Any] = {
        "label": label,
        "path": str(root),
        "present": root.exists() or root.is_symlink(),
        "entries_scanned": 0,
        "scan_complete": True,
        "mismatches": [],
        "unreadable": [],
        "unwritable": [],
        "symlinks": [],
        "hardlinked_regular_files": 0,
    }
    if not result["present"]:
        return result

    stack = [root]
    while stack:
        path = stack.pop()
        try:
            record = path_record(
                path,
                effective_uid=effective_uid,
                effective_gid=effective_gid,
                stat_fn=stat_fn,
            )
        except OSError as exc:
            result["scan_complete"] = False
            result["unreadable"].append({"path": str(path), "reason": f"lstat failed: {exc}"})
            continue

        result["entries_scanned"] += 1
        if record["kind"] == "symlink":
            result["symlinks"].append(issue(record, "symlink in critical Git metadata is not followed"))
            continue
        if not record["uid_matches"] or not record["gid_matches"]:
            result["mismatches"].append(issue(record, "owner/group does not match effective UID/GID"))
        if not record["readable"] or (record["kind"] == "directory" and not record["searchable"]):
            result["unreadable"].append(issue(record, "metadata is not readable/searchable by the effective identity"))

        write_required = record["kind"] == "directory" or label in {"logs", "worktrees"}
        if write_required and not record["writable"]:
            result["unwritable"].append(issue(record, "metadata is not writable by the effective identity"))
        if label == "objects" and record["kind"] == "file" and record["nlink"] > 1:
            result["hardlinked_regular_files"] += 1

        if record["kind"] != "directory":
            continue
        try:
            with os.scandir(path) as entries:
                children = [Path(entry.path) for entry in entries]
        except OSError as exc:
            result["scan_complete"] = False
            result["unreadable"].append(issue(record, f"directory scan failed: {exc}"))
            continue
        stack.extend(reversed(sorted(children, key=lambda item: item.name)))
    return result


def collect_metadata(common_dir: Path, git_dir: Path, identity: dict[str, Any]) -> dict[str, Any]:
    euid = identity.get("effective_uid")
    egid = identity.get("effective_gid")
    try:
        common_record = path_record(common_dir, effective_uid=euid, effective_gid=egid)
        git_record = path_record(git_dir, effective_uid=euid, effective_gid=egid)
    except OSError as exc:
        raise InspectionError(f"critical Git directory stat failed: {exc}") from exc

    trees = {
        name: scan_metadata_tree(
            common_dir / name,
            label=name,
            effective_uid=euid,
            effective_gid=egid,
        )
        for name in ("objects", "refs", "logs", "worktrees")
    }
    special_paths = [
        common_dir / "config",
        common_dir / "packed-refs",
        git_dir / "HEAD",
        git_dir / "index",
        git_dir / "commondir",
        git_dir / "gitdir",
    ]
    special: list[dict[str, Any]] = []
    for path in dict.fromkeys(special_paths):
        if not path.exists() and not path.is_symlink():
            continue
        try:
            special.append(path_record(path, effective_uid=euid, effective_gid=egid))
        except OSError as exc:
            special.append({"path": str(path), "kind": "unreadable", "error": str(exc)})

    mismatches: list[dict[str, Any]] = []
    unreadable: list[dict[str, Any]] = []
    unwritable: list[dict[str, Any]] = []
    symlinks: list[dict[str, Any]] = []
    locks: list[dict[str, Any]] = []

    for record, label in ((common_record, "Git common directory"), (git_record, "Git directory")):
        if record["kind"] == "symlink":
            symlinks.append(issue(record, f"{label} is a symlink"))
        if not record["uid_matches"] or not record["gid_matches"]:
            mismatches.append(issue(record, f"{label} owner/group does not match effective UID/GID"))
        if not record["readable"] or not record.get("searchable"):
            unreadable.append(issue(record, f"{label} is not readable/searchable"))
        if not record["writable"]:
            unwritable.append(issue(record, f"{label} is not writable"))

    for name, tree in trees.items():
        if name in {"objects", "refs"} and not tree["present"]:
            unreadable.append({"path": tree["path"], "reason": f"required {name} metadata tree is missing"})
        mismatches.extend(tree["mismatches"])
        unreadable.extend(tree["unreadable"])
        unwritable.extend(tree["unwritable"])
        symlinks.extend(tree["symlinks"])

    for record in special:
        if record.get("kind") == "unreadable":
            unreadable.append({"path": record["path"], "reason": record["error"]})
            continue
        if record["kind"] == "symlink":
            symlinks.append(issue(record, "special Git metadata entry is a symlink"))
        if not record["uid_matches"] or not record["gid_matches"]:
            mismatches.append(issue(record, "special Git metadata owner/group mismatch"))
        if not record["readable"]:
            unreadable.append(issue(record, "special Git metadata entry is unreadable"))
        if record["kind"] != "file" or not record["writable"]:
            unwritable.append(issue(record, "special Git metadata entry is not a writable regular file"))

    lock_candidates = [
        common_dir / "index.lock",
        common_dir / "config.lock",
        common_dir / "packed-refs.lock",
        common_dir / "shallow.lock",
        git_dir / "index.lock",
    ]
    refs_dir = common_dir / "refs"
    if refs_dir.exists():
        lock_candidates.extend(path for path in refs_dir.rglob("*.lock") if path.is_file())
    for path in dict.fromkeys(lock_candidates):
        if path.exists():
            locks.append({"path": str(path), "reason": "active or stale Git lock requires diagnosis"})

    entries_scanned = 2 + len(special) + sum(tree["entries_scanned"] for tree in trees.values())
    scan_complete = all(tree["scan_complete"] for tree in trees.values())
    return {
        "common_dir": common_record,
        "git_dir": git_record,
        "critical_trees": trees,
        "special_entries": special,
        "entries_scanned": entries_scanned,
        "scan_complete": scan_complete,
        "mismatches": mismatches,
        "unreadable": unreadable,
        "unwritable": unwritable,
        "symlinks": symlinks,
        "locks": locks,
    }


def collect_worktrees(repo: Path, *, runner: Runner = run_command, timeout: float = 30.0) -> dict[str, Any]:
    code, stdout, stderr = runner(["git", "worktree", "list", "--porcelain"], repo, timeout)
    if code != 0:
        raise InspectionError(f"git worktree list --porcelain failed ({code}): {stderr or stdout}")

    blocks: list[dict[str, Any]] = []
    current: dict[str, Any] = {}
    for line in [*stdout.splitlines(), ""]:
        if not line:
            if current:
                blocks.append(current)
            current = {}
            continue
        if line.startswith("worktree "):
            current["path"] = line.removeprefix("worktree ")
        elif line.startswith("HEAD "):
            current["head"] = line.removeprefix("HEAD ")
        elif line.startswith("branch "):
            current["branch"] = line.removeprefix("branch ")
        elif line == "bare":
            current["bare"] = True
        elif line.startswith("locked"):
            current["locked"] = True
            current["lock_reason"] = line.removeprefix("locked").strip()
        elif line.startswith("prunable"):
            current["prunable"] = True
            current["prune_reason"] = line.removeprefix("prunable").strip()
        elif line == "detached":
            current["detached"] = True

    identity = collect_identity()
    euid = identity["effective_uid"]
    egid = identity["effective_gid"]
    entries: list[dict[str, Any]] = []
    unknown = 0
    mismatched = 0
    for block in blocks:
        path = Path(block.get("path", ""))
        missing = not path.exists()
        dirty = False
        status_result = "not_applicable"
        owner_uid: int | None = None
        owner_gid: int | None = None
        identity_status = "unknown"
        if missing:
            unknown += 1
            status_result = "missing"
        elif block.get("bare"):
            status_result = "bare"
        else:
            try:
                info = path.lstat()
                owner_uid, owner_gid = info.st_uid, info.st_gid
                identity_status = "match" if info.st_uid == euid and info.st_gid == egid else "mismatch"
                if identity_status == "mismatch":
                    mismatched += 1
            except OSError:
                unknown += 1
                identity_status = "unknown"
            code, status_out, status_err = runner(
                ["git", "--no-optional-locks", "status", "--porcelain=v1", "--untracked-files=all"],
                path,
                timeout,
            )
            if code != 0:
                raise InspectionError(f"git status failed for worktree {path} ({code}): {status_err or status_out}")
            dirty = bool(status_out)
            status_result = "dirty" if dirty else "clean"
        entries.append(
            {
                "path": str(path),
                "head": block.get("head"),
                "branch": block.get("branch"),
                "bare": bool(block.get("bare")),
                "detached": bool(block.get("detached")),
                "locked": bool(block.get("locked")),
                "lock_reason": block.get("lock_reason", ""),
                "prunable": bool(block.get("prunable")),
                "prune_reason": block.get("prune_reason", ""),
                "missing": missing,
                "dirty": dirty,
                "status_result": status_result,
                "owner_uid": owner_uid,
                "owner_gid": owner_gid,
                "identity_status": identity_status,
            }
        )
    if not entries:
        raise InspectionError("git worktree list returned no worktrees")
    return {
        "total_count": len(entries),
        "linked_count": max(len(entries) - 1, 0),
        "unknown_identity_count": unknown,
        "mismatched_identity_count": mismatched,
        "entries": entries,
    }


def default_branch(repo: Path, remote: str, *, timeout: float) -> str:
    code, stdout, _ = run_command(
        ["git", "symbolic-ref", "--quiet", "--short", f"refs/remotes/{remote}/HEAD"], repo, timeout
    )
    if code == 0 and stdout.startswith(f"{remote}/"):
        return stdout.removeprefix(f"{remote}/")
    for candidate in ("main", "master"):
        code, _, _ = run_command(["git", "show-ref", "--verify", "--quiet", f"refs/remotes/{remote}/{candidate}"], repo, timeout)
        if code == 0:
            return candidate
    return "not proven"


def collect_repository(repo: Path, git_dir: Path, common_dir: Path, worktrees: dict[str, Any], remote: str, *, timeout: float) -> dict[str, Any]:
    branch = strict_git(repo, ["branch", "--show-current"], timeout=timeout)
    if not branch:
        branch = "not proven (detached HEAD)"
    head = strict_git(repo, ["rev-parse", "HEAD"], timeout=timeout)
    code, origin_url, origin_error = run_command(["git", "remote", "get-url", remote], repo, timeout)
    if code != 0:
        origin_url = f"not proven: {origin_error or 'remote lookup failed'}"
    current_path = repo.resolve()
    current_entry = next(
        (entry for entry in worktrees["entries"] if Path(entry["path"]).resolve() == current_path),
        None,
    )
    if current_entry is None:
        raise InspectionError("current canonical root is absent from git worktree list")
    try:
        common_inside = common_dir.is_relative_to(repo)
    except ValueError:
        common_inside = False
    return {
        "canonical_root": str(repo),
        "git_dir": str(git_dir),
        "git_common_dir": str(common_dir),
        "git_dir_equals_common_dir": git_dir == common_dir,
        "common_dir_inside_repo": common_inside,
        "branch": branch,
        "head": head,
        "default_branch": default_branch(repo, remote, timeout=timeout),
        "origin_url": origin_url,
        "worktree_clean": not current_entry["dirty"],
    }


def probe_directory(path: Path) -> tuple[dict[str, Any], str | None]:
    token = secrets.token_hex(12)
    probe = path / f".statedd-write-probe-{token}"
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    created = False
    error: str | None = None
    try:
        descriptor = os.open(probe, flags, 0o600)
        created = True
        try:
            os.write(descriptor, b"statedd git safety write probe\n")
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    except OSError as exc:
        error = str(exc)
    cleanup_error: str | None = None
    if created:
        try:
            probe.unlink()
        except OSError as exc:
            cleanup_error = str(exc)
    result = "pass" if error is None and cleanup_error is None else "fail"
    record = {
        "path": str(path),
        "probe_path": str(probe),
        "result": result,
        "error": error,
        "cleanup_error": cleanup_error,
    }
    return record, str(probe) if cleanup_error else None


def perform_write_probes(repo: Path, git_dir: Path, common_dir: Path) -> dict[str, Any]:
    candidates = [repo, common_dir, git_dir]
    candidates.extend(common_dir / name for name in ("objects", "refs", "logs", "worktrees"))
    targets: list[dict[str, Any]] = []
    residue: list[str] = []
    seen: set[Path] = set()
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved in seen or not resolved.exists():
            continue
        seen.add(resolved)
        if not resolved.is_dir():
            targets.append({"path": str(resolved), "result": "fail", "error": "probe target is not a directory", "cleanup_error": None})
            continue
        record, leftover = probe_directory(resolved)
        targets.append(record)
        if leftover:
            residue.append(leftover)
    passed = bool(targets) and all(item["result"] == "pass" for item in targets) and not residue
    return {"required": True, "result": "pass" if passed else "fail", "targets": targets, "residue": residue}


def run_fsck(repo: Path, *, timeout: float) -> dict[str, Any]:
    command = ["git", "fsck", "--no-dangling"]
    started = time.monotonic()
    code, stdout, stderr = run_command(command, repo, timeout)
    elapsed = int((time.monotonic() - started) * 1000)
    diagnostic = stderr or stdout
    return {
        "command": command,
        "result": "pass" if code == 0 else "fail",
        "exit_code": code,
        "duration_ms": elapsed,
        "stderr": diagnostic[-4000:],
    }


def run_synchronization(repo: Path, remote: str, *, timeout: float) -> dict[str, Any]:
    command = [
        "git",
        "-c",
        "gc.auto=0",
        "-c",
        "maintenance.auto=false",
        "fetch",
        "--prune",
        remote,
    ]
    started = time.monotonic()
    code, stdout, stderr = run_command(command, repo, timeout)
    elapsed = int((time.monotonic() - started) * 1000)
    return {
        "required": True,
        "operation": "fetch",
        "remote": remote,
        "attempted": True,
        "result": "pass" if code == 0 else "fail",
        "exit_code": code,
        "duration_ms": elapsed,
        "stderr": (stderr or stdout)[-4000:],
    }


def skipped_synchronization(remote: str, result: str) -> dict[str, Any]:
    return {
        "required": result != "not_run_read_only",
        "operation": "fetch",
        "remote": remote,
        "attempted": False,
        "result": result,
        "exit_code": None,
        "duration_ms": 0,
        "stderr": "",
    }


def skipped_write_probe(result: str) -> dict[str, Any]:
    return {"required": result != "not_run_read_only", "result": result, "targets": [], "residue": []}


def source_common_dir(source_repo: str | None, *, timeout: float) -> str | None:
    if not source_repo:
        return None
    _, _, common = resolve_repo_paths(Path(source_repo), timeout=timeout)
    return str(common)


def build_isolation(
    mode: str,
    common_dir: Path,
    metadata: dict[str, Any],
    source_common: str | None,
) -> dict[str, Any]:
    alternates_file = common_dir / "objects" / "info" / "alternates"
    alternates_present = bool(os.environ.get("GIT_ALTERNATE_OBJECT_DIRECTORIES"))
    if alternates_file.exists():
        try:
            alternates_present = alternates_present or bool(alternates_file.read_text(encoding="utf-8").strip())
        except OSError:
            alternates_present = True
    hardlinks = metadata["critical_trees"]["objects"]["hardlinked_regular_files"]
    independent = source_common is not None and Path(source_common).resolve() != common_dir.resolve()
    rules = [
        "normal_branch requires a private feature branch in one unprivileged host clone",
        "worktree requires explicit opt-in, trusted-local attestation, safe same identity, and a non-privileged host runtime",
        "clone requires a distinct common directory, no alternates, no hardlinked object files, and one worktree",
        "read_only never permits StateDD-managed mutation",
    ]
    return {
        "requested_mode": mode,
        "selected_mode": mode,
        "independent_common_dir": independent,
        "source_common_dir": source_common,
        "alternates_present": alternates_present,
        "hardlinked_object_files": hardlinks,
        "rules": rules,
    }


def mode_policy(
    mode: str,
    report: dict[str, Any],
    *,
    worktree_opt_in: bool,
    trusted_local_machine: bool,
    operation_class: str = "local_mutation",
    operator_authorized: bool = False,
) -> tuple[list[str], list[str]]:
    """Return deterministic blockers/warnings for an already-collected report."""
    blockers: list[str] = []
    warnings: list[str] = []
    metadata = report["metadata"]
    identity = report["identity"]
    runtime = report["runtime"]
    repository = report["repository"]
    worktrees = report["worktrees"]
    isolation = report["isolation"]

    if operation_class not in OPERATION_CLASSES:
        blockers.append(f"unknown Git operation class: {operation_class}")
    if operation_class == "remote_mutation":
        if not operator_authorized:
            blockers.append("remote mutation requires explicit operator authorization")
        if not repository.get("worktree_clean"):
            blockers.append("remote mutation requires a clean worktree")

    if mode == "read_only":
        if report["fsck"]["result"] != "pass":
            warnings.append("git fsck failed; diagnosis remains read-only")
        for key, label in (
            ("mismatches", "metadata ownership mismatch"),
            ("unreadable", "unreadable metadata"),
            ("unwritable", "unwritable metadata"),
            ("symlinks", "metadata symlink"),
            ("locks", "Git lock"),
        ):
            if metadata.get(key):
                warnings.append(f"{label} reported; mutation is disabled")
        return blockers, warnings

    if not identity.get("known"):
        blockers.append("effective UID/GID is unknown")
    if runtime.get("git_environment_overrides"):
        blockers.append(
            "redirecting Git environment is active: "
            + ", ".join(runtime["git_environment_overrides"])
        )
    if not metadata.get("scan_complete"):
        blockers.append("critical Git metadata scan was incomplete")
    if metadata.get("mismatches"):
        blockers.append("critical Git metadata owner/group does not match effective identity")
    if metadata.get("unreadable"):
        blockers.append("critical Git metadata is unreadable or unsearchable")
    if metadata.get("unwritable"):
        blockers.append("critical Git metadata is not writable")
    if metadata.get("symlinks"):
        blockers.append("critical Git metadata contains an untrusted symlink")
    if metadata.get("locks"):
        blockers.append("Git lock metadata is present and requires diagnosis")
    if report["write_probe"]["result"] != "pass":
        blockers.append("required real write probes did not pass")
    if report["fsck"]["result"] != "pass":
        blockers.append("git fsck did not pass")
    if report["synchronization"]["result"] != "pass":
        blockers.append("mandatory git fetch synchronization did not pass")

    if mode in {"normal_branch", "worktree"}:
        if not runtime.get("proof_complete"):
            blockers.append("runtime/container privilege proof is incomplete")
        if runtime.get("classification") != "host":
            blockers.append("normal-branch/worktree mutation requires a proven host runtime; use an independent clone")
        if runtime.get("privilege") != "unprivileged":
            blockers.append("normal-branch/worktree mutation is blocked for root or capability-bearing privilege")

    if mode == "normal_branch":
        if not repository.get("git_dir_equals_common_dir") or not repository.get("common_dir_inside_repo"):
            blockers.append("normal_branch requires a full clone/main worktree with its own in-repo common directory")
        if worktrees.get("total_count") != 1:
            blockers.append("normal_branch requires exactly one registered worktree")
        branch = repository.get("branch")
        default = repository.get("default_branch")
        if not branch or branch.startswith("not proven"):
            blockers.append("normal_branch requires an attached branch")
        elif branch in {default, "main", "master"}:
            blockers.append("normal_branch requires a private feature branch, not the default branch")

    if mode == "worktree":
        if not worktree_opt_in:
            blockers.append("worktree mode requires explicit --worktree-opt-in")
        if not trusted_local_machine:
            blockers.append("worktree mode requires explicit --trusted-local-machine attestation")
        if worktrees.get("unknown_identity_count", 0):
            blockers.append("worktree identity is unknown for one or more registered worktrees")
        if worktrees.get("mismatched_identity_count", 0):
            blockers.append("worktree identity mismatches the effective UID/GID")

    if mode == "clone":
        if not repository.get("git_dir_equals_common_dir") or not repository.get("common_dir_inside_repo"):
            blockers.append("clone mode requires a full clone with an in-repo common directory")
        if worktrees.get("total_count") != 1:
            blockers.append("clone mode requires exactly one registered worktree")
        if not isolation.get("independent_common_dir"):
            blockers.append("clone mode requires a source repo and a distinct Git common directory")
        if isolation.get("alternates_present"):
            blockers.append("clone mode forbids alternate object databases")
        if isolation.get("hardlinked_object_files", 0):
            blockers.append("clone mode forbids hardlinked object files; clone with --no-local --no-hardlinks")

    return list(dict.fromkeys(blockers)), list(dict.fromkeys(warnings))


def validate_report(report: dict[str, Any]) -> list[str]:
    try:
        from statedd_validate_schema import validate_json_schema
    except ImportError:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from statedd_validate_schema import validate_json_schema
    try:
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"cannot load Git safety schema {SCHEMA_PATH}: {exc}"]
    return [f"{item.path}: {item.message}" for item in validate_json_schema(report, schema)]


def build_report(
    args: argparse.Namespace,
    resolved: tuple[Path, Path, Path] | None = None,
    *,
    locked_state_root: Path | None = None,
) -> tuple[dict[str, Any], int]:
    requested = Path(args.repo).resolve()
    repo, git_dir, common_dir = resolved or resolve_repo_paths(requested, timeout=args.timeout)
    state_root = locked_state_root or Path(args.latch_root).resolve()
    identity = collect_identity()
    runtime = collect_runtime(identity, requested, timeout=args.timeout)
    metadata = collect_metadata(common_dir, git_dir, identity)
    worktrees = collect_worktrees(repo, timeout=args.timeout)
    repository = collect_repository(repo, git_dir, common_dir, worktrees, args.remote, timeout=args.timeout)
    fsck = run_fsck(repo, timeout=args.timeout)
    try:
        source_common = source_common_dir(args.source_repo, timeout=args.timeout)
    except InspectionError as exc:
        source_common = None
        source_error = str(exc)
    else:
        source_error = None
    isolation = build_isolation(args.mode, common_dir, metadata, source_common)
    latch_file, permit_file = state_paths(state_root, common_dir)
    global_latch = global_latch_path(state_root)
    latch_active_before = read_state(latch_file) is not None
    global_active_before = read_state(global_latch) is not None
    permit_active_before = read_state(permit_file) is not None
    active_before = latch_active_before or global_active_before

    if args.mode == "read_only":
        write_probe = skipped_write_probe("not_run_read_only")
        synchronization = skipped_synchronization(args.remote, "not_run_read_only")
    elif active_before and not args.restart_session:
        write_probe = skipped_write_probe("not_attempted_latched")
        synchronization = skipped_synchronization(args.remote, "not_attempted_latched")
    else:
        write_probe = skipped_write_probe("not_attempted_blocked")
        synchronization = skipped_synchronization(args.remote, "not_attempted_blocked")

    report: dict[str, Any] = {
        "schema": SCHEMA_ID,
        "generated_at": dt.datetime.now(dt.timezone.utc).astimezone().isoformat(timespec="seconds"),
        "request": {
            "path": str(requested),
            "mode": args.mode,
            "sync": "fetch",
            "remote": args.remote,
            "worktree_opt_in": args.worktree_opt_in,
            "trusted_local_machine": args.trusted_local_machine,
            "restart_session": args.restart_session,
            "source_repo": str(Path(args.source_repo).resolve()) if args.source_repo else None,
            "operation_class": args.operation_class,
            "operator_authorized": args.operator_authorized,
            "slice_id": args.slice_id,
            "agent_id": args.agent_id,
            "context_hash": args.context_hash,
            "reservation_ref": args.reservation_ref,
            "expected_branch": args.expected_branch,
            "expected_head": args.expected_head,
        },
        "repository": repository,
        "identity": identity,
        "runtime": runtime,
        "metadata": metadata,
        "worktrees": worktrees,
        "write_probe": write_probe,
        "fsck": fsck,
        "synchronization": synchronization,
        "isolation": isolation,
        "latch": {
            "path": str(latch_file),
            "global_path": str(global_latch),
            "active_before": active_before,
            "active_after": active_before,
            "written": False,
            "cleared": False,
            "error": None,
            "permit_path": str(permit_file),
            "permit_active_before": permit_active_before,
            "permit_active_after": permit_active_before,
            "permit_written": False,
            "permit_cleared": False,
        },
        "decision": {
            "permitted": False,
            "mutation_permitted": False,
            "effective_mode": "read_only",
            "restart_required": active_before,
            "enforcement_scope": "statedd_managed_session_permit",
            "operation_class": args.operation_class,
            "authorized_operations": ["read_only", "local_mutation"]
            if args.operation_class != "remote_mutation"
            else ["read_only", "local_mutation", "remote_mutation"],
            "exact_authorization_boundary": {
                "operator_authorized": args.operator_authorized,
                "expected_branch": args.expected_branch,
                "expected_head": args.expected_head,
                "slice_id": args.slice_id,
                "agent_id": args.agent_id,
                "context_hash": args.context_hash,
                "reservation_ref": args.reservation_ref,
            },
            "blockers": [],
            "warnings": [],
        },
    }

    if source_error:
        report["decision"]["blockers"].append(source_error)
    if args.expected_branch and repository.get("branch") != args.expected_branch:
        report["decision"]["blockers"].append(
            f"expected branch mismatch: wanted {args.expected_branch}, observed {repository.get('branch')}"
        )
    if args.expected_head and repository.get("head") != args.expected_head:
        report["decision"]["blockers"].append(
            f"expected HEAD mismatch: wanted {args.expected_head}, observed {repository.get('head')}"
        )

    if args.mode == "read_only":
        blockers, warnings = mode_policy(
            args.mode,
            report,
            worktree_opt_in=args.worktree_opt_in,
            trusted_local_machine=args.trusted_local_machine,
            operation_class=args.operation_class,
            operator_authorized=args.operator_authorized,
        )
        report["decision"].update(
            {
                "permitted": True,
                "mutation_permitted": False,
                "effective_mode": "read_only",
                "restart_required": True,
                "blockers": blockers,
                "warnings": warnings,
            }
        )
        return report, 0

    if active_before and not args.restart_session:
        report["decision"]["blockers"].append(
            "a previous mandatory Git failure latched this repository read-only; repair it and rerun with --restart-session"
        )
    else:
        # Evaluate structural safety with the still-unattempted transactional
        # operations provisionally marked pass. Unsafe structure must not trigger
        # a write probe or fetch.
        report["write_probe"] = {"required": True, "result": "pass", "targets": [], "residue": []}
        report["synchronization"] = {
            "required": True,
            "operation": "fetch",
            "remote": args.remote,
            "attempted": False,
            "result": "pass",
            "exit_code": None,
            "duration_ms": 0,
            "stderr": "",
        }
        structural_blockers, _ = mode_policy(
            args.mode,
            report,
            worktree_opt_in=args.worktree_opt_in,
            trusted_local_machine=args.trusted_local_machine,
            operation_class=args.operation_class,
            operator_authorized=args.operator_authorized,
        )
        if source_error:
            structural_blockers.append(source_error)
        if structural_blockers:
            report["write_probe"] = skipped_write_probe("not_attempted_blocked")
            report["synchronization"] = skipped_synchronization(args.remote, "not_attempted_blocked")
        else:
            report["write_probe"] = perform_write_probes(repo, git_dir, common_dir)
            if report["write_probe"]["result"] == "pass":
                report["synchronization"] = run_synchronization(repo, args.remote, timeout=args.timeout)
                if report["synchronization"]["result"] == "pass":
                    # Fetch writes the common directory. Re-scan it before issuing
                    # the permit so post-fetch drift cannot pass on stale evidence.
                    report["metadata"] = collect_metadata(common_dir, git_dir, identity)
                    report["worktrees"] = collect_worktrees(repo, timeout=args.timeout)
                    report["repository"] = collect_repository(
                        repo,
                        git_dir,
                        common_dir,
                        report["worktrees"],
                        args.remote,
                        timeout=args.timeout,
                    )
                    report["isolation"] = build_isolation(
                        args.mode,
                        common_dir,
                        report["metadata"],
                        source_common,
                    )

    blockers, warnings = mode_policy(
        args.mode,
        report,
        worktree_opt_in=args.worktree_opt_in,
        trusted_local_machine=args.trusted_local_machine,
    )
    blockers = [*report["decision"]["blockers"], *blockers]
    blockers = list(dict.fromkeys(blockers))
    permitted = not blockers
    report["isolation"]["selected_mode"] = args.mode if permitted else "read_only"
    report["decision"].update(
        {
            "permitted": permitted,
            "mutation_permitted": permitted,
            "effective_mode": args.mode if permitted else "read_only",
            "restart_required": not permitted,
            "blockers": blockers,
            "warnings": warnings,
        }
    )

    return report, 0 if report["decision"]["permitted"] else 1


def _failure_payload_for_report(report: dict[str, Any], fallback: str | None = None) -> dict[str, Any]:
    blockers = list(report["decision"].get("blockers", []))
    if not blockers and fallback:
        blockers.append(fallback)
    if report["request"]["mode"] == "read_only" and not blockers:
        blockers.append("explicit read_only mode selected")
    return latch_payload(
        requested_path=Path(report["request"]["path"]),
        canonical_root=Path(report["repository"]["canonical_root"]),
        common_dir=Path(report["repository"]["git_common_dir"]),
        blockers=blockers,
        branch=report["repository"].get("branch"),
        head=report["repository"].get("head"),
        slice_id=report["request"].get("slice_id"),
        agent_id=report["request"].get("agent_id"),
        context_hash=report["request"].get("context_hash"),
        reservation_ref=report["request"].get("reservation_ref"),
        worktree_clean=report["repository"].get("worktree_clean"),
    )


def apply_session_transition(
    report: dict[str, Any],
    args: argparse.Namespace,
    state_root: Path,
) -> int:
    """Persist one serialized deny/permit transition after schema validation."""
    latch_file = Path(report["latch"]["path"])
    global_latch = Path(report["latch"]["global_path"])
    permit_file = Path(report["latch"]["permit_path"])
    mutation_permitted = bool(report["decision"]["mutation_permitted"])

    try:
        if mutation_permitted:
            write_state(permit_file, permit_payload(report))
            report["latch"]["permit_written"] = True
            if args.restart_session:
                had_latch = read_state(latch_file) is not None or read_state(global_latch) is not None
                remove_state(latch_file)
                remove_state(global_latch)
                report["latch"]["cleared"] = had_latch
            if read_state(latch_file) is not None or read_state(global_latch) is not None:
                raise MutationBlocked("read-only latch remained active after permit issuance")
        else:
            if read_state(permit_file) is not None:
                remove_state(permit_file)
                report["latch"]["permit_cleared"] = True
            if read_state(latch_file) is None and read_state(global_latch) is None:
                write_state(latch_file, _failure_payload_for_report(report))
                report["latch"]["written"] = True
    except (OSError, MutationBlocked) as exc:
        report["latch"]["error"] = str(exc)
        report["decision"]["permitted"] = False
        report["decision"]["mutation_permitted"] = False
        report["decision"]["effective_mode"] = "read_only"
        report["decision"]["restart_required"] = True
        report["decision"]["blockers"].append(f"failed to persist Git safety session state: {exc}")
        try:
            remove_state(permit_file)
            write_state(latch_file, _failure_payload_for_report(report))
            report["latch"]["written"] = True
        except (OSError, MutationBlocked) as latch_exc:
            report["latch"]["error"] += f"; fallback latch failed: {latch_exc}"

    report["latch"]["active_after"] = (
        read_state(latch_file) is not None or read_state(global_latch) is not None
    )
    report["latch"]["permit_active_after"] = read_state(permit_file) is not None
    if report["decision"]["mutation_permitted"] and not report["latch"]["permit_active_after"]:
        report["decision"]["permitted"] = False
        report["decision"]["mutation_permitted"] = False
        report["decision"]["effective_mode"] = "read_only"
        report["decision"]["restart_required"] = True
        report["decision"]["blockers"].append("Git safety mutation permit was not durably recorded")
    if report["decision"]["mutation_permitted"] and report["latch"]["active_after"]:
        report["decision"]["permitted"] = False
        report["decision"]["mutation_permitted"] = False
        report["decision"]["effective_mode"] = "read_only"
        report["decision"]["restart_required"] = True
        report["decision"]["blockers"].append("read-only latch remains active")
    return 0 if report["decision"]["permitted"] else 1


def persist_unreported_failure(
    state_root: Path,
    requested: Path,
    resolved: tuple[Path, Path, Path] | None,
    diagnostic: str,
) -> str | None:
    """Latch inspection/schema/crash failures that cannot produce a full report."""
    try:
        if resolved is None:
            latch_file = global_latch_path(state_root)
            canonical = None
            common = None
        else:
            canonical, _, common = resolved
            latch_file, permit_file = state_paths(state_root, common)
            remove_state(permit_file)
        write_state(
            latch_file,
            latch_payload(
                requested_path=requested,
                canonical_root=canonical,
                common_dir=common,
                blockers=[diagnostic],
            ),
        )
        return None
    except (OSError, MutationBlocked) as exc:
        return str(exc)


def print_human(report: dict[str, Any]) -> None:
    print("StateDD Git Safety Preflight")
    print(f"Requested path: {report['request']['path']}")
    print(f"Canonical repo root: {report['repository']['canonical_root']}")
    print(f"Git dir: {report['repository']['git_dir']}")
    print(f"Git common dir: {report['repository']['git_common_dir']}")
    print(
        "Effective identity: "
        f"uid={report['identity']['effective_uid']} gid={report['identity']['effective_gid']} "
        f"({report['identity']['user']}:{report['identity']['group']})"
    )
    print(
        "Runtime: "
        f"{report['runtime']['classification']} / {report['runtime']['privilege']}"
    )
    print(
        "Metadata: "
        f"scanned={report['metadata']['entries_scanned']} complete={report['metadata']['scan_complete']} "
        f"mismatches={len(report['metadata']['mismatches'])} "
        f"unwritable={len(report['metadata']['unwritable'])}"
    )
    print(
        "Worktrees: "
        f"total={report['worktrees']['total_count']} linked={report['worktrees']['linked_count']}"
    )
    print(f"Write probe: {report['write_probe']['result']}")
    print(f"Git fsck: {report['fsck']['result']}")
    print(f"Synchronization: {report['synchronization']['result']}")
    print(f"Requested isolation mode: {report['isolation']['requested_mode']}")
    print(f"Effective mode: {report['decision']['effective_mode']}")
    print(f"Mutation permitted: {'yes' if report['decision']['mutation_permitted'] else 'no'}")
    print(f"Restart required: {'yes' if report['decision']['restart_required'] else 'no'}")
    print("Warnings:")
    for warning in report["decision"]["warnings"] or ["none"]:
        print(f"- {warning}")
    print("Blocking problems:")
    for blocker in report["decision"]["blockers"] or ["none"]:
        print(f"- {blocker}")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="StateDD fail-closed Git safety preflight")
    parser.add_argument("--repo", default=str(ROOT), help="Requested path inside the Git repository")
    parser.add_argument(
        "--mode",
        required=True,
        choices=("normal_branch", "worktree", "clone", "read_only"),
        help="Requested isolation/mutation mode",
    )
    parser.add_argument("--sync", choices=("fetch",), default="fetch", help="Mandatory writable-mode synchronization")
    parser.add_argument("--remote", default="origin", help="Remote to fetch inside the transaction")
    parser.add_argument("--format", choices=("human", "json"), default="human", help="Report format")
    parser.add_argument("--worktree-opt-in", action="store_true", help="Explicitly opt into shared-common-dir worktree mode")
    parser.add_argument(
        "--trusted-local-machine",
        action="store_true",
        help="Attest that worktree peers are on the same trusted local machine",
    )
    parser.add_argument("--source-repo", help="Source repository used to prove clone common-directory independence")
    parser.add_argument(
        "--operation-class",
        choices=sorted(OPERATION_CLASSES),
        default="local_mutation",
        help="Exact authorization boundary for this decision",
    )
    parser.add_argument(
        "--operator-authorized",
        action="store_true",
        help="Explicit operator authorization required for remote mutation",
    )
    parser.add_argument("--slice-id", help=argparse.SUPPRESS)
    parser.add_argument("--agent-id", help=argparse.SUPPRESS)
    parser.add_argument("--context-hash", help=argparse.SUPPRESS)
    parser.add_argument("--reservation-ref", help=argparse.SUPPRESS)
    parser.add_argument("--expected-branch", help=argparse.SUPPRESS)
    parser.add_argument("--expected-head", help=argparse.SUPPRESS)
    parser.add_argument(
        "--restart-session",
        action="store_true",
        help="After repair, rerun all mandatory checks and clear a prior external read-only latch only on success",
    )
    parser.add_argument("--latch-root", default=str(default_state_root()), help=argparse.SUPPRESS)
    parser.add_argument("--timeout", type=float, default=60.0, help="Per-command timeout in seconds")
    args = parser.parse_args(argv[1:])
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv)
    requested = Path(args.repo).resolve()
    resolved: tuple[Path, Path, Path] | None = None
    report: dict[str, Any] | None = None
    try:
        with state_lock(Path(args.latch_root).resolve()) as locked_state_root:
            try:
                resolved = resolve_repo_paths(requested, timeout=args.timeout)
                report, _ = build_report(
                    args,
                    resolved,
                    locked_state_root=locked_state_root,
                )
            except InspectionError as exc:
                diagnostic = f"StateDD Git safety inspection failed: {exc}"
                latch_error = persist_unreported_failure(
                    locked_state_root, requested, resolved, diagnostic
                )
                print(diagnostic, file=sys.stderr)
                if latch_error:
                    print(f"Read-only latch persistence also failed: {latch_error}", file=sys.stderr)
                return 2
            except Exception as exc:
                diagnostic = f"StateDD Git safety preflight crashed: {exc}"
                latch_error = persist_unreported_failure(
                    locked_state_root, requested, resolved, diagnostic
                )
                print(diagnostic, file=sys.stderr)
                if latch_error:
                    print(f"Read-only latch persistence also failed: {latch_error}", file=sys.stderr)
                return 2

            schema_issues = validate_report(report)
            if schema_issues:
                diagnostic = "Git safety report failed schema before session-state transition"
                latch_error = persist_unreported_failure(
                    locked_state_root, requested, resolved, diagnostic
                )
                print("StateDD Git safety report failed its schema:", file=sys.stderr)
                for item in schema_issues:
                    print(f"- {item}", file=sys.stderr)
                if latch_error:
                    print(f"Read-only latch persistence also failed: {latch_error}", file=sys.stderr)
                return 2

            exit_code = apply_session_transition(report, args, locked_state_root)
            schema_issues = validate_report(report)
            if schema_issues:
                diagnostic = "Git safety report failed schema after session-state transition"
                latch_error = persist_unreported_failure(
                    locked_state_root, requested, resolved, diagnostic
                )
                print("StateDD Git safety final report failed its schema:", file=sys.stderr)
                for item in schema_issues:
                    print(f"- {item}", file=sys.stderr)
                if latch_error:
                    print(f"Read-only latch persistence also failed: {latch_error}", file=sys.stderr)
                return 2
    except (OSError, MutationBlocked) as exc:
        print(f"StateDD Git safety session-state lock failed closed: {exc}", file=sys.stderr)
        return 2

    assert report is not None
    if args.format == "json":
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print_human(report)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
