#!/usr/bin/env python3
"""Focused regression tests for strict runtime truth re-probing."""

from __future__ import annotations

import datetime as dt
import json
import sys
import tempfile
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import projectstate_audit as audit  # noqa: E402
import projectstate_runtime_truth_check as runtime_truth  # noqa: E402
from projectstate_closure_check import ClosureCheck  # noqa: E402


HEAD = "a" * 40


def local_payload(endpoint: str = "http://127.0.0.1:8127") -> dict[str, object]:
    return {
        "captured_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "git_head": HEAD,
        "repo": {
            "path": ".",
            "branch": "main",
            "head": HEAD,
            "worktree_clean": True,
            "status_porcelain": "",
        },
        "runtime": {
            "required": True,
            "endpoint": endpoint,
            "ownership_mode": "local_process",
            "process": {
                "detected": True,
                "port": 8127,
                "cwd_matches_repo": True,
                "executable": "python3",
                "argv_sha256": "b" * 64,
                "argv_count": 2,
            },
        },
        "probe": {
            "url": endpoint,
            "http_status": 200,
            "response_sha256": "c" * 64,
            "response_bytes": 2,
        },
        "checks": {
            "endpoint_reachable": True,
            "head_recorded": True,
            "process_detected": True,
            "process_cwd_matches_repo": True,
            "duplicate_runtime_checked": True,
        },
    }


def make_checker(root: Path, endpoint: str | None = "http://127.0.0.1:8127") -> runtime_truth.RuntimeTruthCheck:
    artifact = root / "docs" / "evidence" / "slice" / "runtime_identity.json"
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text("{}\n", encoding="utf-8")
    checker = runtime_truth.RuntimeTruthCheck(
        root,
        artifact,
        max_age_seconds=3600,
        timeout=0.01,
        expected_endpoint=endpoint,
    )
    checker.current_head = HEAD
    return checker


def live_probe(url: str, timeout: float) -> tuple[dict[str, object], list[str]]:
    return {
        "url": url,
        "http_status": 200,
        "content_type": "text/plain",
        "response_sha256": "c" * 64,
        "response_bytes": 2,
    }, []


def test_dirty_same_head_is_rejected() -> None:
    with tempfile.TemporaryDirectory(prefix="projectstate-runtime-dirty-") as tmp:
        root = Path(tmp)
        checker = make_checker(root)
        snapshot = {"head": HEAD, "branch": "main", "changed": {"src/app.py"}}
        with mock.patch.object(runtime_truth, "git_snapshot", return_value=snapshot):
            checker._check_git(local_payload())
        assert any("uncommitted implementation" in failure for failure in checker.failures)


def test_backlog_is_allowed_post_proof_state_finalization() -> None:
    assert runtime_truth.path_is_allowed_after_proof("BACKLOG.md")


def test_endpoint_port_and_process_digest_must_match() -> None:
    with tempfile.TemporaryDirectory(prefix="projectstate-runtime-process-") as tmp:
        checker = make_checker(Path(tmp))
        current_process = {
            "detected": True,
            "port": 8127,
            "cwd_matches_repo": True,
            "executable": "python3",
            "argv_sha256": "d" * 64,
            "argv_count": 2,
            "all_candidate_pids": [123],
        }
        with (
            mock.patch.object(runtime_truth, "fetch_url", side_effect=live_probe),
            mock.patch.object(
                runtime_truth,
                "detect_process",
                return_value=(current_process, [], True),
            ),
        ):
            checker._check_live_runtime(local_payload())
        assert any("argument digest" in failure for failure in checker.failures)

        checker.failures.clear()
        payload = local_payload()
        payload["runtime"]["process"]["port"] = 9999  # type: ignore[index]
        with mock.patch.object(runtime_truth, "fetch_url", side_effect=live_probe):
            checker._check_live_runtime(payload)
        assert any("process port" in failure for failure in checker.failures)


def test_remote_artifact_cannot_trigger_implicit_probe() -> None:
    endpoint = "https://example.com/health"
    with tempfile.TemporaryDirectory(prefix="projectstate-runtime-remote-") as tmp:
        checker = make_checker(Path(tmp), endpoint)
        payload = local_payload(endpoint)
        payload["runtime"]["ownership_mode"] = "remote_revision"  # type: ignore[index]
        payload["runtime"]["revision_header"] = "X-ProjectState-Revision"  # type: ignore[index]
        with mock.patch.object(runtime_truth, "fetch_url") as fetch:
            checker._check_live_runtime(payload)
        fetch.assert_not_called()
        assert any("--allow-remote" in failure for failure in checker.failures)


def test_nested_symlink_artifact_is_rejected() -> None:
    with tempfile.TemporaryDirectory(prefix="projectstate-runtime-symlink-") as tmp:
        base = Path(tmp)
        root = base / "repo"
        outside = base / "outside"
        root.mkdir()
        outside.mkdir()
        (outside / "runtime_identity.json").write_text("{}\n", encoding="utf-8")
        (root / "evidence").symlink_to(outside, target_is_directory=True)
        try:
            runtime_truth.resolve_artifact(root, "evidence/runtime_identity.json")
        except RuntimeError:
            return
        raise AssertionError("artifact below a symlinked parent must be rejected")


def test_v1_is_migration_only_for_runtime_truth() -> None:
    with tempfile.TemporaryDirectory(prefix="projectstate-runtime-v1-") as tmp:
        root = Path(tmp)
        artifact = root / "runtime_identity.json"
        artifact.write_text(json.dumps({"schema": "projectstate.runtime_identity.v1"}), encoding="utf-8")
        checker = runtime_truth.RuntimeTruthCheck(
            root,
            artifact,
            max_age_seconds=3600,
            timeout=0.01,
        )
        try:
            checker._load()
        except RuntimeError as exc:
            assert "migration-only" in str(exc)
            return
        raise AssertionError("legacy runtime artifact must not establish current runtime truth")


def test_audit_accepts_v2_schema_label() -> None:
    with tempfile.TemporaryDirectory(prefix="projectstate-runtime-audit-") as tmp:
        root = Path(tmp)
        folder = root / "docs" / "evidence" / "slice"
        folder.mkdir(parents=True)
        (folder / "runtime_identity.json").write_text(
            json.dumps(
                {
                    "schema": "projectstate.runtime_identity.v2",
                    "runtime": {"required": False, "reason": "test-only slice"},
                }
            ),
            encoding="utf-8",
        )
        result = audit.AuditResult()
        audit.check_runtime_identity(root, result, True, explicit_folder=folder)
        assert not any(
            finding.status == "fail" and "schema" in finding.message
            for finding in result.findings
        )


def test_closure_preflight_invokes_explicit_runtime_artifact() -> None:
    with tempfile.TemporaryDirectory(prefix="projectstate-runtime-closure-") as tmp:
        root = Path(tmp)
        folder = root / "docs" / "evidence" / "slice"
        folder.mkdir(parents=True)
        (folder / "runtime_identity.json").write_text("{}\n", encoding="utf-8")
        checker = ClosureCheck(root, evidence_folder=folder)
        calls: list[list[str]] = []

        def fake_run(command: list[str]) -> tuple[int, str, str]:
            calls.append(command)
            return 0, "RUNTIME NOT APPLICABLE VERIFIED", ""

        checker.run_cmd = fake_run  # type: ignore[method-assign]
        assert checker.check_runtime_proof()
        assert calls and "docs/evidence/slice/runtime_identity.json" in calls[0]


def main() -> int:
    tests = [
        test_dirty_same_head_is_rejected,
        test_backlog_is_allowed_post_proof_state_finalization,
        test_endpoint_port_and_process_digest_must_match,
        test_remote_artifact_cannot_trigger_implicit_probe,
        test_nested_symlink_artifact_is_rejected,
        test_v1_is_migration_only_for_runtime_truth,
        test_audit_accepts_v2_schema_label,
        test_closure_preflight_invokes_explicit_runtime_artifact,
    ]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
