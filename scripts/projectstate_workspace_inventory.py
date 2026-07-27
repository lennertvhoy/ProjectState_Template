#!/usr/bin/env python3
"""Inventory ProjectState-managed workspaces and unexpected same-origin siblings.

Managed full clones live outside the source repository's parent directory under
one deterministic, per-user root.  This module is deliberately read-only except
for callers explicitly creating the returned active/quarantine directories.

Exit codes:
  0 = inventory completed and no requested refusal condition was found
  1 = unmanaged same-origin sibling clones were found when refusal was requested
  2 = repository identity or inventory could not be established safely
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

try:
    from projectstate_git_safety_session import sanitized_git_environment
except ModuleNotFoundError:  # pragma: no cover - package-import fallback
    from scripts.projectstate_git_safety_session import sanitized_git_environment


INVENTORY_SCHEMA = "projectstate.workspace_inventory.v1"
AGENT_CONTEXT_PATH = Path(".projectstate/agent.context")
_SCP_REMOTE_RE = re.compile(r"^(?:[^@/\s]+@)?([^:/\s]+):(.+)$")
_SAFE_COMPONENT_RE = re.compile(r"[^A-Za-z0-9._-]+")


def _run_git(repo: Path, *args: str) -> tuple[int, str, str]:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=repo,
            env=sanitized_git_environment(),
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 127, "", str(exc)
    return completed.returncode, completed.stdout.strip(), completed.stderr.strip()


def resolve_repo(path: Path) -> Path:
    candidate = Path(os.path.abspath(path))
    if candidate.is_symlink():
        raise ValueError(f"symlinked repository paths are not allowed: {candidate}")
    code, stdout, stderr = _run_git(candidate, "rev-parse", "--show-toplevel")
    if code != 0 or not stdout:
        raise ValueError(f"repository resolution failed for {candidate}: {stderr or stdout}")
    root = Path(stdout).resolve()
    if root != candidate.resolve():
        raise ValueError(f"path is not the exact repository root: {candidate} -> {root}")
    return root


def _strip_dot_git(path: str) -> str:
    value = path.rstrip("/")
    return value[:-4] if value.lower().endswith(".git") else value


def normalize_remote(remote: str, *, repo: Path) -> str:
    """Return a credential-free identity shared by equivalent Git URL forms."""
    value = remote.strip()
    if not value:
        raise ValueError("origin URL is empty")

    parsed = urlsplit(value)
    if parsed.scheme == "file":
        local = Path(unquote(parsed.path)).expanduser().resolve()
        return f"local:{_strip_dot_git(str(local))}"
    if parsed.scheme and parsed.hostname:
        host = parsed.hostname.lower()
        port = f":{parsed.port}" if parsed.port else ""
        path = _strip_dot_git(unquote(parsed.path).lstrip("/"))
        if not path:
            raise ValueError(f"origin URL has no repository path: {remote!r}")
        return f"remote:{host}{port}/{path}"

    scp_match = _SCP_REMOTE_RE.fullmatch(value)
    if scp_match and not value.startswith(("./", "../")):
        host, raw_path = scp_match.groups()
        path = _strip_dot_git(raw_path.lstrip("/"))
        return f"remote:{host.lower()}/{path}"

    local_path = Path(value).expanduser()
    if not local_path.is_absolute():
        local_path = repo / local_path
    return f"local:{_strip_dot_git(str(local_path.resolve()))}"


def origin_identity(repo: Path) -> str:
    code, stdout, stderr = _run_git(repo, "remote", "get-url", "origin")
    if code != 0 or not stdout:
        # Bootstrap repositories may legitimately have no remote yet. Their
        # exact root remains a local-only identity; once origin is configured,
        # the remote identity becomes the cross-clone authority.
        return f"unconfigured:{repo.resolve()}"
    return normalize_remote(stdout, repo=repo)


def safe_component(value: str, *, fallback: str = "workspace") -> str:
    component = _SAFE_COMPONENT_RE.sub("-", value).strip("-.")
    return (component or fallback)[:80]


def workspace_state_root() -> Path:
    override = os.environ.get("PROJECTSTATE_WORKSPACE_ROOT", "").strip()
    if not override:
        # Backward-compat: honor the legacy env var for one migration cycle.
        override = os.environ.get("STATEDD_WORKSPACE_ROOT", "").strip()
    if override:
        root = Path(override).expanduser()
    else:
        xdg_state = os.environ.get("XDG_STATE_HOME", "").strip()
        root = (
            Path(xdg_state).expanduser() / "projectstate" / "workspaces"
            if xdg_state
            else Path.home() / ".local" / "state" / "projectstate" / "workspaces"
        )
    if not root.is_absolute():
        raise ValueError("ProjectState workspace root must be absolute")
    return Path(os.path.abspath(root))


def repository_workspace_root(repo: Path) -> Path:
    root = resolve_repo(repo)
    identity = origin_identity(root)
    digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:16]
    return workspace_state_root() / f"{safe_component(root.name)}-{digest}"


def managed_active_root(repo: Path) -> Path:
    return repository_workspace_root(repo) / "active"


def managed_quarantine_root(repo: Path) -> Path:
    return repository_workspace_root(repo) / "quarantine"


def managed_clone_path(repo: Path, branch: str) -> Path:
    digest = hashlib.sha256(branch.encode("utf-8")).hexdigest()[:10]
    return managed_active_root(repo) / f"{safe_component(branch)}-{digest}"


def path_is_within(path: Path, parent: Path) -> bool:
    absolute = Path(os.path.abspath(path))
    ancestor = Path(os.path.abspath(parent))
    try:
        absolute.relative_to(ancestor)
    except ValueError:
        return False
    return True


def _load_context(path: Path) -> dict[str, Any] | None:
    context_path = path / AGENT_CONTEXT_PATH
    try:
        payload = json.loads(context_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def inventory_anchor(repo: Path) -> Path:
    """Use a managed workspace's declared source for repository-wide inventory."""
    root = resolve_repo(repo)
    context = _load_context(root)
    if not context:
        return root
    source = context.get("source_repo")
    if not isinstance(source, str) or not source or not Path(source).is_absolute():
        return root
    try:
        return resolve_repo(Path(source))
    except (OSError, ValueError):
        return root


def linked_worktree_paths(repo: Path) -> list[Path]:
    code, stdout, _ = _run_git(repo, "worktree", "list", "--porcelain")
    if code != 0:
        raise ValueError(f"worktree topology is not inspectable for {repo}")
    paths: list[Path] = []
    for line in stdout.splitlines():
        if line.startswith("worktree "):
            paths.append(Path(line.removeprefix("worktree ")).resolve())
    return paths


def discover_managed_clones(repo: Path) -> list[dict[str, Any]]:
    active = managed_active_root(repo)
    if not active.exists():
        return []
    if active.is_symlink() or not active.is_dir():
        raise ValueError(f"managed active workspace root is unsafe: {active}")
    results: list[dict[str, Any]] = []
    for candidate in sorted(active.iterdir(), key=lambda item: item.name):
        try:
            if candidate.is_symlink() or not candidate.is_dir():
                continue
        except OSError:
            continue
        context = _load_context(candidate)
        code, head, _ = _run_git(candidate, "rev-parse", "HEAD")
        results.append(
            {
                "path": str(candidate),
                "head": head if code == 0 and head else "not proven",
                "branch": context.get("branch", "not proven") if context else "not proven",
                "slice_id": context.get("slice_id", "not proven") if context else "not proven",
                "context_present": context is not None,
                "path_binding_matches": bool(
                    context and context.get("worktree_path") == str(candidate)
                ),
            }
        )
    return results


def discover_quarantined_clones(repo: Path) -> list[dict[str, Any]]:
    quarantine = managed_quarantine_root(repo)
    if not quarantine.exists():
        return []
    if quarantine.is_symlink() or not quarantine.is_dir():
        raise ValueError(f"managed quarantine root is unsafe: {quarantine}")
    results: list[dict[str, Any]] = []
    for candidate in sorted(quarantine.iterdir(), key=lambda item: item.name):
        try:
            if candidate.is_symlink() or not candidate.is_dir():
                continue
        except OSError:
            continue
        context = _load_context(candidate)
        code, head, _ = _run_git(candidate, "rev-parse", "HEAD")
        results.append(
            {
                "path": str(candidate),
                "head": head if code == 0 and head else "not proven",
                "branch": context.get("branch", "not proven") if context else "not proven",
                "slice_id": context.get("slice_id", "not proven") if context else "not proven",
                "context_present": context is not None,
                "path_binding_matches": bool(
                    context and context.get("worktree_path") == str(candidate)
                ),
            }
        )
    return results


def discover_same_origin_siblings(repo: Path) -> list[dict[str, Any]]:
    """Find immediate sibling clones that bypass the managed workspace root."""
    anchor = resolve_repo(repo)
    expected_origin = origin_identity(anchor)
    linked = set(linked_worktree_paths(anchor))
    results: list[dict[str, Any]] = []
    try:
        entries = sorted(anchor.parent.iterdir(), key=lambda item: item.name)
    except OSError as exc:
        raise ValueError(f"cannot inspect repository parent {anchor.parent}: {exc}") from exc
    for candidate in entries:
        try:
            if candidate == anchor or candidate.is_symlink() or not candidate.is_dir():
                continue
            absolute = candidate.resolve()
        except OSError:
            continue
        if absolute in linked:
            continue
        code, top, _ = _run_git(candidate, "rev-parse", "--show-toplevel")
        if code != 0 or not top or Path(top).resolve() != absolute:
            continue
        try:
            candidate_origin = origin_identity(absolute)
        except ValueError:
            continue
        if candidate_origin != expected_origin:
            continue
        context = _load_context(absolute)
        head_code, head, _ = _run_git(absolute, "rev-parse", "HEAD")
        status_code, status, _ = _run_git(
            absolute, "--no-optional-locks", "status", "--porcelain=v1", "--untracked-files=all"
        )
        results.append(
            {
                "path": str(absolute),
                "head": head if head_code == 0 and head else "not proven",
                "dirty": bool(status) if status_code == 0 else "not proven",
                "managed_context": context is not None,
            }
        )
    return results


def build_inventory(repo: Path) -> dict[str, Any]:
    requested = resolve_repo(repo)
    anchor = inventory_anchor(requested)
    linked = linked_worktree_paths(anchor)
    return {
        "schema": INVENTORY_SCHEMA,
        "requested_repo": str(requested),
        "source_repo": str(anchor),
        "origin_identity": origin_identity(anchor),
        "workspace_root": str(repository_workspace_root(anchor)),
        "managed_clones": discover_managed_clones(anchor),
        "quarantined_clones": discover_quarantined_clones(anchor),
        "linked_worktrees": [str(path) for path in linked if path != anchor],
        "unmanaged_same_origin_siblings": discover_same_origin_siblings(anchor),
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inventory ProjectState workspace lifecycle state")
    parser.add_argument("--repo", default=str(Path.cwd()), help="Exact Git repository root")
    parser.add_argument("--format", choices=("human", "json"), default="human")
    parser.add_argument(
        "--fail-on-unmanaged",
        action="store_true",
        help="Exit nonzero when an immediate same-origin sibling clone is found",
    )
    return parser.parse_args(argv[1:])


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv)
    try:
        inventory = build_inventory(Path(args.repo))
    except (OSError, ValueError) as exc:
        print(f"Workspace inventory failed: {exc}", file=sys.stderr)
        return 2
    if args.format == "json":
        print(json.dumps(inventory, indent=2, sort_keys=True))
    else:
        print("ProjectState Workspace Inventory")
        print(f"Source repository: {inventory['source_repo']}")
        print(f"Managed workspace root: {inventory['workspace_root']}")
        print("Managed active clones:")
        for item in inventory["managed_clones"] or [{"path": "none", "slice_id": ""}]:
            suffix = f" slice={item['slice_id']}" if item.get("slice_id") else ""
            print(f"- {item['path']}{suffix}")
        print("Linked worktrees:")
        for path in inventory["linked_worktrees"] or ["none"]:
            print(f"- {path}")
        print("Quarantined clones (recoverable, inactive):")
        for item in inventory["quarantined_clones"] or [{"path": "none", "slice_id": ""}]:
            suffix = f" slice={item['slice_id']}" if item.get("slice_id") else ""
            print(f"- {item['path']}{suffix}")
        print("Unmanaged same-origin sibling clones:")
        for item in inventory["unmanaged_same_origin_siblings"] or [{"path": "none"}]:
            print(f"- {item['path']}")
    return 1 if args.fail_on_unmanaged and inventory["unmanaged_same_origin_siblings"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
