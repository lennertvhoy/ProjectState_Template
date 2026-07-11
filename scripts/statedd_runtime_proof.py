#!/usr/bin/env python3
"""Capture a StateDD runtime identity proof artifact.

The artifact records the repo identity, runtime applicability, endpoint probe,
and best-effort process ownership for URL-based runtime evidence. Process
inspection is intentionally honest: unsupported or blocked detection is recorded
as a limit instead of being treated as proof.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import ipaddress
import json
import os
import platform
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

from statedd_git_safety_session import MutationBlocked, require_mutation_permit


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "statedd.runtime_identity.v1"


def runtime_identity_compat_block(head: str | None = None) -> dict[str, object]:
    """Return legacy top-level fields kept for consumers still using the v0 layout."""
    block: dict[str, object] = {
        "timestamp": dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z"),
        "os": platform.system(),
        "os_version": platform.version(),
        "kernel": platform.release(),
        "arch": platform.machine(),
        "python": platform.python_version(),
        "hostname": platform.node(),
        "git_head": head or "not proven",
        "in_container": Path("/.dockerenv").exists(),
    }
    if block["in_container"]:
        try:
            cgroup = Path("/proc/self/cgroup").read_text()
            if "docker" in cgroup:
                block["container_runtime"] = "docker"
            elif "kubepods" in cgroup:
                block["container_runtime"] = "kubernetes"
            else:
                block["container_runtime"] = "unknown"
        except OSError:
            block["container_runtime"] = "unknown"
    return block


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


def git_value(repo: Path, args: list[str]) -> str | None:
    code, stdout, _ = run_command(["git", *args], repo)
    if code != 0:
        return None
    return stdout or None


def repo_block(repo: Path) -> dict[str, object]:
    status = git_value(repo, ["status", "--short"]) or ""
    return {
        "path": str(repo),
        "branch": git_value(repo, ["rev-parse", "--abbrev-ref", "HEAD"]),
        "head": git_value(repo, ["rev-parse", "HEAD"]),
        "worktree_clean": status.strip() == "",
        "status_porcelain": status,
    }


def sha256_bytes(data: bytes) -> str:
    digest = hashlib.sha256()
    digest.update(data)
    return digest.hexdigest()


def fetch_url(url: str, timeout: float) -> tuple[dict[str, object], list[str]]:
    limits: list[str] = []
    request = urllib.request.Request(url, headers={"User-Agent": "StateDD-runtime-proof/1"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read()
            content_type = response.headers.get("Content-Type")
            status = getattr(response, "status", None)
            return (
                {
                    "url": url,
                    "http_status": status,
                    "content_type": content_type,
                    "response_sha256": sha256_bytes(body),
                    "response_bytes": len(body),
                },
                limits,
            )
    except urllib.error.HTTPError as exc:
        body = exc.read()
        return (
            {
                "url": url,
                "http_status": exc.code,
                "content_type": exc.headers.get("Content-Type"),
                "response_sha256": sha256_bytes(body),
                "response_bytes": len(body),
            },
            limits,
        )
    except urllib.error.URLError as exc:
        limits.append(f"Endpoint fetch failed: {exc.reason}")
    except TimeoutError:
        limits.append("Endpoint fetch timed out.")
    except OSError as exc:
        limits.append(f"Endpoint fetch failed: {exc}")
    return (
        {
            "url": url,
            "http_status": None,
            "content_type": None,
            "response_sha256": None,
            "response_bytes": 0,
        },
        limits,
    )


def port_from_url(url: str) -> int | None:
    parsed = urlparse(url)
    if parsed.port is not None:
        return parsed.port
    if parsed.scheme == "http":
        return 80
    if parsed.scheme == "https":
        return 443
    return None


def host_is_local(host: str | None) -> bool:
    if host is None:
        return False
    normalized = host.strip().lower().removeprefix("[").removesuffix("]")
    if normalized in {"localhost", "0.0.0.0"}:
        return True
    try:
        address = ipaddress.ip_address(normalized)
    except ValueError:
        return False
    return address.is_loopback or address.is_unspecified


def should_attempt_local_process_detection(url: str, expect_local: bool) -> bool:
    if expect_local:
        return True
    return host_is_local(urlparse(url).hostname)


def remote_process_not_applicable(url: str) -> tuple[dict[str, object], list[str], bool]:
    host = urlparse(url).hostname or "not proven"
    return (
        {
            "detected": False,
            "host": host,
            "reason": "remote endpoint; local process ownership is not applicable",
            "impact": "endpoint identity was probed, but serving process ownership was not proven",
        },
        ["Process detection skipped because the endpoint host is not local."],
        False,
    )


def socket_inodes_for_port(port: int) -> set[str]:
    inodes: set[str] = set()
    hex_port = f"{port:04X}"
    for relpath in ("net/tcp", "net/tcp6"):
        path = Path("/proc") / relpath
        try:
            lines = path.read_text(encoding="utf-8").splitlines()[1:]
        except (OSError, UnicodeDecodeError, IndexError):
            continue
        for line in lines:
            fields = line.split()
            if len(fields) < 10:
                continue
            local_address = fields[1]
            state = fields[3]
            inode = fields[9]
            if ":" not in local_address:
                continue
            _, local_port = local_address.rsplit(":", 1)
            if local_port.upper() == hex_port and state == "0A":
                inodes.add(inode)
    return inodes


def pids_for_socket_inodes(inodes: set[str]) -> set[int]:
    pids: set[int] = set()
    if not inodes:
        return pids
    proc = Path("/proc")
    for pid_dir in proc.iterdir():
        if not pid_dir.name.isdigit():
            continue
        fd_dir = pid_dir / "fd"
        try:
            fds = list(fd_dir.iterdir())
        except OSError:
            continue
        for fd in fds:
            try:
                target = os.readlink(fd)
            except OSError:
                continue
            if target.startswith("socket:[") and target.removeprefix("socket:[").removesuffix("]") in inodes:
                pids.add(int(pid_dir.name))
                break
    return pids


def process_command(pid: int) -> str | None:
    cmdline = Path("/proc") / str(pid) / "cmdline"
    try:
        raw = cmdline.read_bytes()
    except OSError:
        return None
    parts = [part.decode("utf-8", errors="replace") for part in raw.split(b"\0") if part]
    return " ".join(parts) if parts else None


def process_cwd(pid: int) -> str | None:
    try:
        return str((Path("/proc") / str(pid) / "cwd").resolve())
    except OSError:
        return None


def path_matches_repo(cwd: str | None, repo: Path) -> bool | None:
    if cwd is None:
        return None
    cwd_path = Path(cwd).resolve()
    repo_path = repo.resolve()
    if cwd_path == repo_path:
        return True
    try:
        cwd_path.relative_to(repo_path)
    except ValueError:
        return False
    return True


def detect_process(port: int | None, expected_repo: Path, expected_name: str | None) -> tuple[dict[str, object], list[str], bool]:
    limits: list[str] = []
    duplicate_checked = False
    if port is None:
        return (
            {
                "detected": False,
                "reason": "no port supplied or inferable from URL",
                "impact": "runtime endpoint may be reachable, but process ownership was not proven",
            },
            ["Process detection skipped because no port was available."],
            duplicate_checked,
        )
    if not Path("/proc/net/tcp").exists():
        return (
            {
                "detected": False,
                "port": port,
                "reason": "Linux /proc TCP tables are unavailable",
                "impact": "runtime endpoint may be reachable, but process ownership was not proven",
            },
            ["Process owner detection unavailable on this platform."],
            duplicate_checked,
        )

    duplicate_checked = True
    inodes = socket_inodes_for_port(port)
    pids = sorted(pids_for_socket_inodes(inodes))
    if not pids:
        return (
            {
                "detected": False,
                "port": port,
                "reason": "port owner not found in /proc",
                "impact": "runtime endpoint may be reachable, but process ownership was not proven",
            },
            ["Process cwd could not be determined because no port owner was found."],
            duplicate_checked,
        )

    if len(pids) > 1:
        limits.append(f"Multiple listener processes were found for port {port}: {pids}.")

    pid = pids[0]
    command = process_command(pid)
    cwd = process_cwd(pid)
    if command is None:
        limits.append(f"Command line could not be read for PID {pid}.")
    if cwd is None:
        limits.append(f"Process cwd could not be determined for PID {pid}.")
    if expected_name and command and expected_name not in command:
        limits.append(f"Process command did not include expected name '{expected_name}'.")

    return (
        {
            "detected": True,
            "pid": pid,
            "port": port,
            "cwd": cwd,
            "command": command,
            "cwd_matches_repo": path_matches_repo(cwd, expected_repo),
            "all_candidate_pids": pids,
        },
        limits,
        duplicate_checked,
    )


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Capture StateDD runtime identity proof")
    parser.add_argument("--url", help="Runtime URL or endpoint to probe")
    parser.add_argument("--evidence-dir", help="Evidence directory that should receive runtime_identity.json")
    parser.add_argument("--output", help="Explicit output path for the JSON artifact")
    parser.add_argument("--no-runtime-required", action="store_true", help="Record runtime.required=false")
    parser.add_argument("--reason", default="docs/scripts-only slice", help="Reason used with --no-runtime-required")
    parser.add_argument("--kind", default="web", help="Runtime kind for URL proof")
    parser.add_argument("--expected-repo", default=str(ROOT), help="Repo path expected to own the runtime")
    parser.add_argument("--process-name", help="Optional command substring expected for the runtime process")
    parser.add_argument("--port", type=int, help="Port to inspect for process ownership")
    parser.add_argument(
        "--expect-local",
        "--local-process-proof",
        dest="expect_local",
        action="store_true",
        help="Attempt local process ownership detection even when the URL host is not localhost/loopback",
    )
    parser.add_argument("--timeout", type=float, default=10.0, help="Endpoint fetch timeout in seconds")
    return parser.parse_args(argv[1:])


def output_path(args: argparse.Namespace) -> Path:
    if args.output:
        return Path(args.output).resolve()
    if args.evidence_dir:
        return (Path(args.evidence_dir).resolve() / "runtime_identity.json")
    raise SystemExit("Provide --evidence-dir or --output.")


def build_not_applicable_artifact(repo: Path, reason: str) -> dict[str, object]:
    repo_info = repo_block(repo)
    return {
        "schema": SCHEMA,
        "captured_at": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "repo": repo_info,
        "runtime": {
            "required": False,
            "reason": reason,
        },
        "checks": {
            "runtime_not_applicable_recorded": True,
            "head_recorded": bool(repo_info.get("head")),
        },
        "limits": [],
        **runtime_identity_compat_block(repo_info.get("head")),
    }


def build_url_artifact(args: argparse.Namespace, repo: Path) -> tuple[dict[str, object], int]:
    url = args.url
    assert url is not None
    probe, probe_limits = fetch_url(url, args.timeout)
    if should_attempt_local_process_detection(url, args.expect_local):
        port = args.port if args.port is not None else port_from_url(url)
        process, process_limits, duplicate_checked = detect_process(port, repo, args.process_name)
    else:
        process, process_limits, duplicate_checked = remote_process_not_applicable(url)
    http_status = probe.get("http_status")
    endpoint_reachable = http_status is not None and 200 <= int(http_status) < 400
    cwd_matches = None
    if isinstance(process, dict):
        cwd_matches = process.get("cwd_matches_repo")
    limits = [*probe_limits, *process_limits]
    repo_info = repo_block(repo)

    artifact = {
        "schema": SCHEMA,
        "captured_at": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "repo": repo_info,
        "runtime": {
            "required": True,
            "kind": args.kind,
            "endpoint": url,
            "process": process,
        },
        "probe": probe,
        "checks": {
            "endpoint_reachable": endpoint_reachable,
            "process_cwd_matches_repo": cwd_matches if cwd_matches is not None else "unknown",
            "head_recorded": bool(repo_info.get("head")),
            "duplicate_runtime_checked": duplicate_checked,
            "process_detected": bool(process.get("detected")) if isinstance(process, dict) else False,
        },
        "limits": limits,
        **runtime_identity_compat_block(repo_info.get("head")),
    }
    return artifact, 0 if endpoint_reachable else 1


def write_artifact(path: Path, artifact: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(artifact, indent=2, sort_keys=True) + "\n"
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(payload)
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv)
    repo = Path(args.expected_repo).resolve()
    if args.no_runtime_required and args.url:
        raise SystemExit("--url cannot be combined with --no-runtime-required.")
    if not args.no_runtime_required and not args.url:
        raise SystemExit("Provide --url for runtime proof or --no-runtime-required for docs/scripts-only proof.")

    path = output_path(args)
    try:
        require_mutation_permit(
            path,
            "StateDD runtime identity artifact write",
            allow_non_git=True,
        )
    except MutationBlocked as exc:
        print(str(exc), file=sys.stderr)
        return 1
    if args.no_runtime_required:
        artifact = build_not_applicable_artifact(repo, args.reason)
        write_artifact(path, artifact)
        print(path)
        return 0

    artifact, exit_code = build_url_artifact(args, repo)
    write_artifact(path, artifact)
    print(path)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
