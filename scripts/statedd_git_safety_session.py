#!/usr/bin/env python3
"""Session-state enforcement for the StateDD Git safety preflight.

The executable preflight owns the transition between an external read-only
latch and a short-lived mutation permit. StateDD writers consume that permit;
they do not infer authorization from a successful process exit alone.

State is deliberately stored outside the repository. A repository whose Git
metadata is damaged or read-only must not need to be mutated in order to record
that the session is blocked.
"""

from __future__ import annotations

import contextlib
import datetime as dt
import hashlib
import json
import os
import secrets
import socket
import stat
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Iterator

try:  # POSIX is required for writable modes; unsupported hosts fail closed.
    import fcntl
except ImportError:  # pragma: no cover - exercised by portable policy tests.
    fcntl = None  # type: ignore[assignment]


LATCH_SCHEMA = "statedd.git_safety_latch.v1"
PERMIT_SCHEMA = "statedd.git_safety_permit.v1"
PERMIT_TTL_SECONDS = 8 * 60 * 60

# These variables can redirect repository discovery or critical metadata away
# from the paths that the preflight inspects. Trace/transport-only variables are
# intentionally not included.
UNSAFE_GIT_ENV_EXACT = {
    "GIT_ALTERNATE_OBJECT_DIRECTORIES",
    "GIT_CEILING_DIRECTORIES",
    "GIT_COMMON_DIR",
    "GIT_CONFIG",
    "GIT_CONFIG_GLOBAL",
    "GIT_CONFIG_NOSYSTEM",
    "GIT_CONFIG_SYSTEM",
    "GIT_DIR",
    "GIT_DISCOVERY_ACROSS_FILESYSTEM",
    "GIT_INDEX_FILE",
    "GIT_NAMESPACE",
    "GIT_OBJECT_DIRECTORY",
    "GIT_QUARANTINE_PATH",
    "GIT_REPLACE_REF_BASE",
    "GIT_SHALLOW_FILE",
    "GIT_WORK_TREE",
}
UNSAFE_GIT_ENV_PREFIXES = ("GIT_CONFIG_KEY_", "GIT_CONFIG_VALUE_")


class MutationBlocked(RuntimeError):
    """A StateDD-managed write lacks a valid session mutation permit."""


def effective_uid() -> int | None:
    return os.geteuid() if hasattr(os, "geteuid") else None


def effective_gid() -> int | None:
    return os.getegid() if hasattr(os, "getegid") else None


def active_git_environment_overrides() -> list[str]:
    names: list[str] = []
    for name in os.environ:
        if name in UNSAFE_GIT_ENV_EXACT or name.startswith(UNSAFE_GIT_ENV_PREFIXES):
            names.append(name)
    if "GIT_CONFIG_COUNT" in os.environ:
        names.append("GIT_CONFIG_COUNT")
    return sorted(set(names))


def sanitized_git_environment() -> dict[str, str]:
    env = dict(os.environ)
    for name in active_git_environment_overrides():
        env.pop(name, None)
    env["GIT_OPTIONAL_LOCKS"] = "0"
    return env


def machine_fingerprint() -> str:
    parts = [socket.gethostname()]
    for path in (Path("/etc/machine-id"), Path("/proc/sys/kernel/random/boot_id")):
        try:
            value = path.read_text(encoding="utf-8", errors="replace").strip()
        except OSError:
            value = ""
        if value:
            parts.append(value)
    return hashlib.sha256("\0".join(parts).encode("utf-8")).hexdigest()


def default_state_root() -> Path:
    configured = os.environ.get("STATEDD_GIT_SAFETY_STATE_ROOT", "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    uid = effective_uid()
    return Path(tempfile.gettempdir()) / f"statedd-git-safety-{uid if uid is not None else 'unknown'}"


def _validate_state_directory(path: Path) -> None:
    info = path.lstat()
    if not stat.S_ISDIR(info.st_mode) or path.is_symlink():
        raise MutationBlocked(f"Git safety state root is not a real directory: {path}")
    uid = effective_uid()
    if uid is None or info.st_uid != uid:
        raise MutationBlocked(f"Git safety state root owner is not the effective UID: {path}")
    if stat.S_IMODE(info.st_mode) & 0o077:
        raise MutationBlocked(f"Git safety state root is group/world accessible: {path}")


def ensure_state_root(path: Path) -> Path:
    path = path.expanduser().resolve()
    try:
        path.mkdir(parents=True, mode=0o700, exist_ok=True)
        _validate_state_directory(path)
    except OSError as exc:
        raise MutationBlocked(f"Cannot establish secure Git safety state root {path}: {exc}") from exc
    return path


def _validate_state_file(path: Path) -> os.stat_result:
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or path.is_symlink():
        raise MutationBlocked(f"Git safety state is not a regular file: {path}")
    uid = effective_uid()
    if uid is None or info.st_uid != uid:
        raise MutationBlocked(f"Git safety state owner is not the effective UID: {path}")
    if stat.S_IMODE(info.st_mode) & 0o077:
        raise MutationBlocked(f"Git safety state is group/world accessible: {path}")
    if info.st_nlink != 1:
        raise MutationBlocked(f"Git safety state has an unexpected hardlink count: {path}")
    return info


@contextlib.contextmanager
def state_lock(root: Path | None = None) -> Iterator[Path]:
    if fcntl is None:
        raise MutationBlocked("POSIX file locking is unavailable; writable StateDD sessions are blocked")
    state_root = ensure_state_root(root or default_state_root())
    lock_path = state_root / ".state.lock"
    flags = os.O_CREAT | os.O_RDWR
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(lock_path, flags, 0o600)
    try:
        _validate_state_file(lock_path)
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield state_root
    finally:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
        finally:
            os.close(descriptor)


def state_key(value: Path | str) -> str:
    return hashlib.sha256(str(Path(value).resolve()).encode("utf-8")).hexdigest()


def state_paths(state_root: Path, common_dir: Path | str) -> tuple[Path, Path]:
    key = state_key(common_dir)
    return state_root / f"{key}.latch.json", state_root / f"{key}.permit.json"


def global_latch_path(state_root: Path) -> Path:
    return state_root / "global.latch.json"


def read_state(path: Path) -> dict[str, Any] | None:
    if not path.exists() and not path.is_symlink():
        return None
    _validate_state_file(path)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise MutationBlocked(f"Cannot read trusted Git safety state {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise MutationBlocked(f"Git safety state is not a JSON object: {path}")
    return payload


def write_state(path: Path, payload: dict[str, Any]) -> None:
    ensure_state_root(path.parent)
    if path.exists() or path.is_symlink():
        _validate_state_file(path)
    temporary = path.parent / f".{path.name}.{secrets.token_hex(12)}.tmp"
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(temporary, flags, 0o600)
    try:
        data = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
        os.write(descriptor, data)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    try:
        _validate_state_file(temporary)
        os.replace(temporary, path)
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        temporary.unlink(missing_ok=True)


def remove_state(path: Path) -> None:
    if not path.exists() and not path.is_symlink():
        return
    _validate_state_file(path)
    path.unlink()


def latch_payload(
    *,
    requested_path: Path,
    canonical_root: Path | None,
    common_dir: Path | None,
    blockers: list[str],
) -> dict[str, Any]:
    return {
        "schema": LATCH_SCHEMA,
        "created_at": dt.datetime.now(dt.timezone.utc).astimezone().isoformat(timespec="seconds"),
        "nonce": secrets.token_hex(16),
        "requested_path": str(requested_path.resolve()),
        "canonical_root": str(canonical_root.resolve()) if canonical_root else None,
        "git_common_dir": str(common_dir.resolve()) if common_dir else None,
        "effective_uid": effective_uid(),
        "effective_gid": effective_gid(),
        "machine_fingerprint_sha256": machine_fingerprint(),
        "blockers": blockers or ["mandatory Git safety operation failed without a diagnostic"],
        "restart_required": True,
    }


def permit_payload(report: dict[str, Any]) -> dict[str, Any]:
    now = dt.datetime.now(dt.timezone.utc)
    return {
        "schema": PERMIT_SCHEMA,
        "created_at": now.astimezone().isoformat(timespec="seconds"),
        "expires_at": (now + dt.timedelta(seconds=PERMIT_TTL_SECONDS)).astimezone().isoformat(timespec="seconds"),
        "nonce": secrets.token_hex(16),
        "canonical_root": report["repository"]["canonical_root"],
        "git_common_dir": report["repository"]["git_common_dir"],
        "head": report["repository"]["head"],
        "branch": report["repository"]["branch"],
        "effective_uid": report["identity"]["effective_uid"],
        "effective_gid": report["identity"]["effective_gid"],
        "machine_fingerprint_sha256": report["runtime"]["machine_fingerprint_sha256"],
        "mode": report["decision"]["effective_mode"],
        "mutation_permitted": True,
    }


def _run_git(cwd: Path, args: list[str]) -> tuple[int, str, str]:
    try:
        completed = subprocess.run(
            ["git", "--no-optional-locks", *args],
            cwd=cwd,
            env=sanitized_git_environment(),
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return 127, "", str(exc)
    return completed.returncode, completed.stdout.rstrip(), completed.stderr.rstrip()


def _existing_anchor(target: Path) -> Path:
    candidate = target.expanduser().resolve()
    if candidate.is_file() or (not candidate.exists() and candidate.suffix):
        candidate = candidate.parent
    while not candidate.exists() and candidate != candidate.parent:
        candidate = candidate.parent
    return candidate


def resolve_repository(target: Path) -> tuple[Path, Path, str] | None:
    anchor = _existing_anchor(target)
    code, root_text, _ = _run_git(anchor, ["rev-parse", "--show-toplevel"])
    if code != 0 or not root_text:
        return None
    root = Path(root_text).resolve()
    code, common_text, error = _run_git(root, ["rev-parse", "--git-common-dir"])
    if code != 0 or not common_text:
        raise MutationBlocked(f"Cannot resolve Git common directory: {error or 'no diagnostic'}")
    common = Path(common_text)
    if not common.is_absolute():
        common = root / common
    code, head, error = _run_git(root, ["rev-parse", "HEAD"])
    if code != 0 or not head:
        raise MutationBlocked(f"Cannot resolve Git HEAD: {error or 'no diagnostic'}")
    return root, common.resolve(), head


def record_required_git_failure(repo: Path, operation: str, diagnostic: str) -> str | None:
    """Persist a failed mandatory Git operation as read-only session state."""
    requested = repo.expanduser().resolve()
    try:
        with state_lock() as root:
            resolved = resolve_repository(requested)
            if resolved is None:
                latch = global_latch_path(root)
                payload = latch_payload(
                    requested_path=requested,
                    canonical_root=None,
                    common_dir=None,
                    blockers=[f"{operation} failed: {diagnostic or 'no diagnostic'}"],
                )
            else:
                canonical, common, _ = resolved
                latch, permit = state_paths(root, common)
                remove_state(permit)
                payload = latch_payload(
                    requested_path=requested,
                    canonical_root=canonical,
                    common_dir=common,
                    blockers=[f"{operation} failed: {diagnostic or 'no diagnostic'}"],
                )
            write_state(latch, payload)
        return None
    except (OSError, MutationBlocked) as exc:
        return str(exc)


def require_mutation_permit(
    target: Path,
    operation: str,
    *,
    allow_non_git: bool = False,
) -> dict[str, Any] | None:
    """Require a valid external permit before a StateDD-managed repository write."""
    overrides = active_git_environment_overrides()
    if overrides:
        raise MutationBlocked(
            f"{operation} blocked: redirecting Git environment is active: {', '.join(overrides)}"
        )
    resolved = resolve_repository(target)
    if resolved is None:
        if allow_non_git:
            return None
        raise MutationBlocked(f"{operation} blocked: target is not inside a proven Git repository")
    canonical, common, head = resolved

    with state_lock() as root:
        global_latch = read_state(global_latch_path(root))
        if global_latch is not None:
            raise MutationBlocked(
                f"{operation} blocked by global Git safety latch; explicit repaired-session restart required"
            )
        latch_path, permit_path = state_paths(root, common)
        latch = read_state(latch_path)
        if latch is not None:
            reasons = "; ".join(str(item) for item in latch.get("blockers", []))
            raise MutationBlocked(
                f"{operation} blocked by Git safety read-only latch; explicit restart required"
                + (f": {reasons}" if reasons else "")
            )
        permit = read_state(permit_path)
        if permit is None:
            raise MutationBlocked(
                f"{operation} blocked: no current Git safety mutation permit; run the executable preflight"
            )

        expected = {
            "schema": PERMIT_SCHEMA,
            "canonical_root": str(canonical),
            "git_common_dir": str(common),
            "head": head,
            "effective_uid": effective_uid(),
            "effective_gid": effective_gid(),
            "machine_fingerprint_sha256": machine_fingerprint(),
            "mutation_permitted": True,
        }
        mismatches = [
            key for key, value in expected.items() if permit.get(key) != value
        ]
        if permit.get("mode") not in {"normal_branch", "worktree", "clone"}:
            mismatches.append("mode")
        try:
            expires_at = dt.datetime.fromisoformat(str(permit.get("expires_at", "")))
            if expires_at.tzinfo is None or expires_at <= dt.datetime.now(dt.timezone.utc):
                mismatches.append("expires_at")
        except ValueError:
            mismatches.append("expires_at")
        if mismatches:
            raise MutationBlocked(
                f"{operation} blocked: Git safety permit is stale or mismatched ({', '.join(sorted(set(mismatches)))})"
            )
        return permit

