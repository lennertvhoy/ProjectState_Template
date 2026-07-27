#!/usr/bin/env python3
"""Re-probe an explicit StateDD runtime artifact against current local truth.

Exit 0 proves that a fresh v2 artifact still matches the current Git state and
that its required endpoint identity was observed again. It does not prove push,
PR, CI, merge, deployment promotion, or human acceptance truth.
"""

from __future__ import annotations

import argparse
import datetime as dt
import subprocess
import sys
from pathlib import Path
from typing import Any

try:
    from statedd_contracts import ContractError, confined_path, load_json_file, safe_root_path
    from statedd_runtime_proof import (
        detect_process,
        fetch_url,
        port_from_url,
        should_attempt_local_process_detection,
        validate_endpoint,
        validate_revision_header,
    )
    from statedd_validate_schema import validate_file
except ModuleNotFoundError:  # pragma: no cover - package import path
    from scripts.statedd_contracts import ContractError, confined_path, load_json_file, safe_root_path
    from scripts.statedd_runtime_proof import (
        detect_process,
        fetch_url,
        port_from_url,
        should_attempt_local_process_detection,
        validate_endpoint,
        validate_revision_header,
    )
    from scripts.statedd_validate_schema import validate_file


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "statedd.runtime_identity.v2"
SCHEMA_FILE = "runtime_identity_v2.schema.json"
POST_PROOF_EXACT_PATHS = {
    "STATUS.md",
    "PROJECT_STATE.yaml",
    "NEXT_ACTIONS.md",
    "WORKLOG.md",
    "docs/EVIDENCE_LOG.md",
    "docs/ACCEPTANCE_FREEZES.md",
}
POST_PROOF_PREFIXES = ("docs/evidence/", "docs/metrics/")


def run_command(args: list[str], cwd: Path) -> tuple[int, str, str]:
    try:
        completed = subprocess.run(
            args,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return 127, "", str(exc)
    return completed.returncode, completed.stdout.strip(), completed.stderr.strip()


def git_value(root: Path, *args: str) -> str:
    code, output, error = run_command(["git", *args], root)
    if code != 0:
        raise RuntimeError(error or f"git {' '.join(args)} failed")
    return output


def git_paths(root: Path, *args: str) -> set[str]:
    code, output, error = run_command(["git", *args, "-z"], root)
    if code != 0:
        raise RuntimeError(error or f"git {' '.join(args)} failed")
    return {path for path in output.split("\0") if path}


def parse_timestamp(value: Any) -> dt.datetime:
    if not isinstance(value, str) or not value:
        raise RuntimeError("runtime artifact has no captured_at timestamp")
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = dt.datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise RuntimeError(f"runtime captured_at is invalid: {value!r}") from exc
    if parsed.tzinfo is None:
        raise RuntimeError("runtime captured_at must include a timezone")
    return parsed.astimezone(dt.timezone.utc)


def resolve_artifact(root: Path, raw: str) -> Path:
    candidate = Path(raw)
    try:
        if candidate.is_absolute():
            relative = candidate.relative_to(root)
        else:
            relative = candidate
        confined = confined_path(root, relative.as_posix())
    except (ContractError, ValueError) as exc:
        raise RuntimeError(f"runtime artifact is not safely confined to the repository: {exc}") from exc
    if not confined.is_file():
        raise RuntimeError(f"runtime artifact is not a regular file: {relative.as_posix()}")
    return confined


def path_is_allowed_after_proof(path: str, artifact_path: str | None = None) -> bool:
    return (
        path == artifact_path
        or path in POST_PROOF_EXACT_PATHS
        or any(path.startswith(prefix) for prefix in POST_PROOF_PREFIXES)
    )


def allowed_post_proof_changes(root: Path, proof_head: str, current_head: str) -> list[str]:
    if proof_head == current_head:
        return []
    code, _, _ = run_command(["git", "merge-base", "--is-ancestor", proof_head, current_head], root)
    if code != 0:
        return [f"recorded head {proof_head} is not an ancestor of current HEAD {current_head}"]
    changed = git_paths(root, "diff", "--name-only", "--no-renames", f"{proof_head}..{current_head}")
    disallowed = sorted(path for path in changed if not path_is_allowed_after_proof(path))
    return [f"post-proof implementation changes are present: {', '.join(disallowed)}"] if disallowed else []


def current_changed_paths(root: Path) -> set[str]:
    return set().union(
        git_paths(root, "diff", "--name-only", "--no-renames"),
        git_paths(root, "diff", "--cached", "--name-only", "--no-renames"),
        git_paths(root, "ls-files", "--others", "--exclude-standard"),
    )


def git_snapshot(root: Path) -> dict[str, object]:
    top_level = Path(git_value(root, "rev-parse", "--show-toplevel")).resolve()
    if top_level != root.resolve():
        raise RuntimeError(f"configured root is not the Git top-level: {root}")
    return {
        "head": git_value(root, "rev-parse", "HEAD"),
        "branch": git_value(root, "rev-parse", "--abbrev-ref", "HEAD"),
        "changed": current_changed_paths(root),
    }


class RuntimeTruthCheck:
    def __init__(
        self,
        root: Path,
        artifact: Path,
        *,
        max_age_seconds: int,
        timeout: float,
        expected_endpoint: str | None = None,
        allow_remote: bool = False,
        verbose: bool = False,
    ) -> None:
        self.root = root
        self.artifact_path = artifact
        self.max_age_seconds = max_age_seconds
        self.timeout = timeout
        self.expected_endpoint = expected_endpoint
        self.allow_remote = allow_remote
        self.verbose = verbose
        self.failures: list[str] = []
        self.initial_git: dict[str, object] | None = None
        self.current_head: str | None = None
        self.runtime_required: bool | None = None

    def _load(self) -> dict[str, Any]:
        try:
            payload = load_json_file(self.artifact_path)
        except ContractError as exc:
            raise RuntimeError(str(exc)) from exc
        if not isinstance(payload, dict):
            raise RuntimeError("runtime artifact root must be an object")
        if payload.get("schema") != SCHEMA:
            raise RuntimeError(
                f"runtime truth requires {SCHEMA}; legacy artifacts remain migration-only evidence"
            )
        issues = validate_file(self.artifact_path, self.root / "schemas" / SCHEMA_FILE)
        if issues:
            details = "; ".join(f"{issue.path}: {issue.message}" for issue in issues[:8])
            raise RuntimeError(f"runtime artifact schema validation failed: {details}")
        return payload

    def _check_git(self, payload: dict[str, Any]) -> None:
        repo = payload.get("repo") or {}
        recorded_head = repo.get("head")
        recorded_branch = repo.get("branch")
        if repo.get("path") != ".":
            self.failures.append("runtime artifact repo.path must use portable repository identity '.'")
        if repo.get("worktree_clean") is not True or repo.get("status_porcelain") != "":
            self.failures.append("runtime artifact was captured from a dirty worktree")

        snapshot = git_snapshot(self.root)
        self.initial_git = snapshot
        current_head = snapshot["head"]
        current_branch = snapshot["branch"]
        self.current_head = current_head if isinstance(current_head, str) else None
        if not isinstance(recorded_head, str) or len(recorded_head) != 40:
            self.failures.append("runtime artifact does not record a full 40-character Git head")
        elif not isinstance(current_head, str):
            self.failures.append("current Git head could not be determined")
        else:
            self.failures.extend(allowed_post_proof_changes(self.root, recorded_head, current_head))
        if recorded_branch != current_branch:
            self.failures.append(
                f"runtime branch mismatch: recorded={recorded_branch!r}, current={current_branch!r}"
            )
        if payload.get("git_head") != recorded_head:
            self.failures.append("legacy git_head compatibility field disagrees with repo.head")

        artifact_rel = self.artifact_path.relative_to(self.root).as_posix()
        changed = snapshot.get("changed")
        dirty_paths = changed if isinstance(changed, set) else set()
        disallowed = sorted(
            path for path in dirty_paths if not path_is_allowed_after_proof(path, artifact_rel)
        )
        if disallowed:
            self.failures.append(
                f"current uncommitted implementation changes are present: {', '.join(disallowed)}"
            )

    def _check_freshness(self, payload: dict[str, Any]) -> None:
        captured = parse_timestamp(payload.get("captured_at"))
        age = (dt.datetime.now(dt.timezone.utc) - captured).total_seconds()
        if age < -60:
            self.failures.append("runtime capture timestamp is in the future")
        elif age > self.max_age_seconds:
            self.failures.append(
                f"runtime capture is stale ({int(age)}s old; maximum {self.max_age_seconds}s)"
            )

    def _check_live_runtime(self, payload: dict[str, Any]) -> None:
        runtime = payload.get("runtime") or {}
        required = runtime.get("required")
        self.runtime_required = required if isinstance(required, bool) else None
        if required is False:
            if not runtime.get("reason"):
                self.failures.append("runtime.required=false requires an explicit reason")
            return
        if required is not True:
            self.failures.append("runtime.required must be explicitly true or false")
            return

        endpoint = runtime.get("endpoint")
        if not isinstance(endpoint, str) or not endpoint:
            self.failures.append("required runtime has no endpoint")
            return
        try:
            validate_endpoint(endpoint)
        except ValueError as exc:
            self.failures.append(f"runtime endpoint is unsafe: {exc}")
            return
        if self.expected_endpoint is None:
            self.failures.append("required runtime truth needs --expected-endpoint from trusted configuration")
            return
        try:
            validate_endpoint(self.expected_endpoint)
        except ValueError as exc:
            self.failures.append(f"expected endpoint is unsafe: {exc}")
            return
        if endpoint != self.expected_endpoint:
            self.failures.append("recorded runtime endpoint differs from --expected-endpoint")
            return

        endpoint_is_local = should_attempt_local_process_detection(endpoint, False)
        ownership_mode = runtime.get("ownership_mode")
        if ownership_mode not in {"local_process", "remote_revision"}:
            self.failures.append("runtime ownership_mode is missing or invalid")
            return
        if endpoint_is_local and ownership_mode != "local_process":
            self.failures.append("local endpoint must use local_process ownership mode")
            return
        if not endpoint_is_local and not self.allow_remote:
            self.failures.append("remote endpoint re-probe requires explicit --allow-remote")
            return

        recorded_probe = payload.get("probe")
        checks = payload.get("checks")
        if not isinstance(recorded_probe, dict) or not isinstance(checks, dict):
            self.failures.append("required runtime needs probe and checks objects")
            return
        if recorded_probe.get("url") != endpoint:
            self.failures.append("recorded probe URL differs from runtime endpoint")
        recorded_status = recorded_probe.get("http_status")
        if not isinstance(recorded_status, int) or not 200 <= recorded_status < 400:
            self.failures.append("recorded endpoint probe was not reachable")
        if checks.get("endpoint_reachable") is not True or checks.get("head_recorded") is not True:
            self.failures.append("recorded endpoint/head checks are incomplete")

        revision_header = runtime.get("revision_header")
        if revision_header is not None:
            if not isinstance(revision_header, str):
                self.failures.append("runtime revision_header is malformed")
                return
            try:
                validate_revision_header(revision_header)
            except ValueError as exc:
                self.failures.append(str(exc))
                return
        if ownership_mode == "remote_revision" and not revision_header:
            self.failures.append("remote runtime truth requires a revision header bound to Git HEAD")
            return

        if revision_header:
            probe, limits = fetch_url(endpoint, self.timeout, revision_header, self.current_head)
        else:
            probe, limits = fetch_url(endpoint, self.timeout)
        status = probe.get("http_status")
        if not isinstance(status, int) or not 200 <= status < 400:
            detail = "; ".join(limits) if limits else f"HTTP status {status}"
            self.failures.append(f"live endpoint re-probe failed: {detail}")
            return
        if revision_header:
            if checks.get("revision_matches_head") is not True:
                self.failures.append("recorded revision header was not bound to the recorded Git HEAD")
            if recorded_probe.get("revision_matches_expected") is not True:
                self.failures.append("recorded probe revision did not match the recorded Git HEAD")
            if probe.get("revision_matches_expected") is not True:
                self.failures.append("live runtime revision header does not match current Git HEAD")

        if ownership_mode != "local_process":
            return
        port = port_from_url(endpoint)
        recorded_process = runtime.get("process")
        if not isinstance(recorded_process, dict):
            self.failures.append("local runtime has no recorded process identity")
            return
        if recorded_process.get("port") != port:
            self.failures.append("recorded process port differs from the endpoint port")
            return
        if recorded_process.get("detected") is not True:
            self.failures.append("recorded local process was not detected")
        if recorded_process.get("cwd_matches_repo") is not True:
            self.failures.append("recorded local process cwd did not belong to the repository")
        if checks.get("process_detected") is not True:
            self.failures.append("recorded process_detected check is not true")
        if checks.get("process_cwd_matches_repo") is not True:
            self.failures.append("recorded process cwd check is not true")
        if checks.get("duplicate_runtime_checked") is not True:
            self.failures.append("recorded duplicate-runtime check is not true")

        current_process, process_limits, duplicate_checked = detect_process(port, self.root, None)
        if not current_process.get("detected"):
            self.failures.append(
                "live local process ownership was not detected: " + "; ".join(process_limits)
            )
            return
        if current_process.get("cwd_matches_repo") is not True:
            self.failures.append("live local process cwd does not belong to the repository")
        if not duplicate_checked:
            self.failures.append("duplicate local runtime ownership was not checked")
        candidate_pids = current_process.get("all_candidate_pids")
        if not isinstance(candidate_pids, list) or len(candidate_pids) != 1:
            self.failures.append("live runtime ownership is ambiguous across listener processes")
        for field, label in (
            ("executable", "executable"),
            ("argv_sha256", "argument digest"),
            ("argv_count", "argument count"),
        ):
            recorded_value = recorded_process.get(field)
            if recorded_value is None or current_process.get(field) != recorded_value:
                self.failures.append(f"live process {label} differs from the recorded runtime")

    def _check_git_stable(self) -> None:
        if self.initial_git is None:
            return
        final = git_snapshot(self.root)
        if final != self.initial_git:
            self.failures.append("Git HEAD, branch, or worktree changed during the live runtime check")

    def run(self) -> int:
        print("StateDD Runtime Truth Check")
        try:
            payload = self._load()
            self._check_freshness(payload)
            self._check_git(payload)
            self._check_live_runtime(payload)
            self._check_git_stable()
        except RuntimeError as exc:
            print(f"ERROR: {exc}")
            return 2
        if self.failures:
            print("RUNTIME TRUTH FAILED")
            for failure in self.failures:
                print(f"- {failure}")
            return 1
        if self.runtime_required is False:
            print("RUNTIME NOT APPLICABLE VERIFIED")
        else:
            print("RUNTIME TRUTH VERIFIED")
        print(f"- artifact: {self.artifact_path.relative_to(self.root)}")
        return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Re-probe a typed StateDD runtime identity")
    parser.add_argument("--root", default=str(ROOT), help="Repository root")
    parser.add_argument("--artifact", required=True, help="Repository-relative runtime_identity.json")
    parser.add_argument(
        "--expected-endpoint",
        help="Trusted endpoint that must exactly match a runtime-required artifact",
    )
    parser.add_argument(
        "--allow-remote",
        action="store_true",
        help="Permit a non-loopback endpoint with revision-header binding",
    )
    parser.add_argument("--max-age-seconds", type=int, default=3600)
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args(argv[1:])
    if args.max_age_seconds < 1:
        parser.error("--max-age-seconds must be positive")
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv)
    try:
        root = safe_root_path(args.root, must_exist=True)
        artifact = resolve_artifact(root, args.artifact)
    except (ContractError, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return RuntimeTruthCheck(
        root,
        artifact,
        max_age_seconds=args.max_age_seconds,
        timeout=args.timeout,
        expected_endpoint=args.expected_endpoint,
        allow_remote=args.allow_remote,
        verbose=args.verbose,
    ).run()


if __name__ == "__main__":
    raise SystemExit(main())
