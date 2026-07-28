#!/usr/bin/env python3
"""Focused regression tests for projectstate_runtime_proof.py.

These tests stay stdlib-only and avoid real network or /proc dependencies.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import projectstate_runtime_proof as runtime_proof  # noqa: E402
from projectstate_validate_schema import validate_file  # noqa: E402


def fake_probe(
    url: str,
    timeout: float,
    revision_header: str | None = None,
    expected_revision: str | None = None,
) -> tuple[dict[str, object], list[str]]:
    probe: dict[str, object] = {
            "url": url,
            "http_status": 200,
            "content_type": "text/plain",
            "response_sha256": "0" * 64,
            "response_bytes": 4,
    }
    if revision_header:
        probe["revision_header"] = revision_header
        probe["revision_matches_expected"] = bool(expected_revision)
    return probe, []


def make_args(
    url: str,
    *,
    expect_local: bool = False,
    port: int | None = None,
    revision_header: str | None = None,
) -> argparse.Namespace:
    return argparse.Namespace(
        url=url,
        timeout=0.01,
        port=port,
        process_name=None,
        revision_header=revision_header,
        kind="web",
        expect_local=expect_local,
    )


def build_with_fake_process(
    url: str,
    *,
    expect_local: bool = False,
    revision_header: str | None = None,
) -> tuple[dict[str, object], list[int | None]]:
    calls: list[int | None] = []
    original_fetch_url = runtime_proof.fetch_url
    original_detect_process = runtime_proof.detect_process

    def fake_detect(port: int | None, expected_repo: Path, expected_name: str | None) -> tuple[dict[str, object], list[str], bool]:
        calls.append(port)
        return (
            {
                "detected": True,
                "pid": 12345,
                "port": port,
                "cwd_relation": "repo_root",
                "executable": "python3",
                "argv_sha256": "0" * 64,
                "argv_count": 2,
                "cwd_matches_repo": True,
                "all_candidate_pids": [12345],
            },
            [],
            True,
        )

    runtime_proof.fetch_url = fake_probe
    runtime_proof.detect_process = fake_detect
    try:
        artifact, exit_code = runtime_proof.build_url_artifact(
            make_args(url, expect_local=expect_local, revision_header=revision_header),
            ROOT,
        )
    finally:
        runtime_proof.fetch_url = original_fetch_url
        runtime_proof.detect_process = original_detect_process

    if exit_code != 0:
        raise AssertionError(f"Expected reachable fake endpoint for {url}, got exit {exit_code}")
    return artifact, calls


def test_localhost_attempts_process_detection() -> None:
    artifact, calls = build_with_fake_process("http://localhost:8123")
    if calls != [8123]:
        raise AssertionError(f"localhost should inspect local port 8123, got calls {calls}")
    if artifact["checks"]["process_detected"] is not True:
        raise AssertionError("localhost process proof should be marked detected")


def test_loopback_attempts_process_detection() -> None:
    artifact, calls = build_with_fake_process("http://127.0.0.1:8124")
    if calls != [8124]:
        raise AssertionError(f"127.0.0.1 should inspect local port 8124, got calls {calls}")
    if artifact["checks"]["duplicate_runtime_checked"] is not True:
        raise AssertionError("loopback process proof should mark duplicate runtime checked")


def test_remote_url_skips_local_port_detection() -> None:
    artifact, calls = build_with_fake_process(
        "https://example.com",
        revision_header="X-ProjectState-Revision",
    )
    if calls:
        raise AssertionError(f"remote endpoint should not inspect local port 443, got calls {calls}")
    process = artifact["runtime"]["process"]
    if process["detected"] is not False:
        raise AssertionError("remote endpoint process proof should be not detected")
    if process["reason"] != "remote endpoint; local process ownership is not applicable":
        raise AssertionError(f"Unexpected remote skip reason: {process['reason']}")
    if artifact["checks"]["duplicate_runtime_checked"] is not False:
        raise AssertionError("remote endpoint should not mark duplicate runtime checked")
    if artifact["runtime"]["ownership_mode"] != "remote_revision":
        raise AssertionError("remote endpoint should require revision-header ownership")


def test_remote_url_can_be_explicitly_treated_as_local() -> None:
    artifact, calls = build_with_fake_process("https://example.com", expect_local=True)
    if calls != [443]:
        raise AssertionError(f"--expect-local should inspect inferred port 443, got calls {calls}")
    if artifact["checks"]["process_detected"] is not True:
        raise AssertionError("--expect-local process proof should be marked detected")


def test_runtime_artifact_omits_absolute_repo_and_raw_process_arguments() -> None:
    sentinel = "sentinel-process-secret-value"
    with (
        mock.patch.object(runtime_proof, "socket_inodes_for_port", return_value={"1"}),
        mock.patch.object(runtime_proof, "pids_for_socket_inodes", return_value={12345}),
        mock.patch.object(
            runtime_proof,
            "process_argv",
            return_value=["/usr/bin/python3", "server.py", f"--password={sentinel}"],
        ),
        mock.patch.object(runtime_proof, "process_cwd", return_value=str(ROOT)),
        mock.patch.object(runtime_proof, "fetch_url", side_effect=fake_probe),
    ):
        artifact, exit_code = runtime_proof.build_url_artifact(
            make_args("http://127.0.0.1:8125"),
            ROOT,
        )

    assert exit_code == 0
    serialized = json.dumps(artifact, sort_keys=True)
    assert str(ROOT) not in serialized
    assert str(Path.home()) not in serialized
    assert sentinel not in serialized
    process = artifact["runtime"]["process"]
    assert process["cwd_relation"] == "repo_root"
    assert process["executable"] == "python3"
    assert process["argv_sha256"]
    assert "cwd" not in process
    assert "command" not in process
    assert artifact["repo"]["path"] == "."


def test_remote_runtime_without_revision_binding_fails_proof() -> None:
    with mock.patch.object(runtime_proof, "fetch_url", side_effect=fake_probe):
        artifact, exit_code = runtime_proof.build_url_artifact(
            make_args("https://example.com"),
            ROOT,
        )
    assert exit_code == 1
    assert any("revision-header binding" in limit for limit in artifact["limits"])


def test_runtime_endpoint_rejects_serialized_secrets() -> None:
    for endpoint in (
        "https://user:secret@example.com/health",
        "https://example.com/health?token=secret",
        "https://example.com/health#secret",
    ):
        try:
            runtime_proof.validate_endpoint(endpoint)
        except ValueError:
            continue
        raise AssertionError(f"unsafe endpoint should be rejected: {endpoint}")


def test_generated_v2_artifact_is_strict_and_schema_valid() -> None:
    artifact, _ = build_with_fake_process("http://127.0.0.1:8126")
    with tempfile.TemporaryDirectory(prefix="projectstate-runtime-schema-") as tmp:
        path = Path(tmp) / "runtime_identity.json"
        runtime_proof.write_artifact(path, artifact)
        issues = validate_file(path, ROOT / "schemas" / "runtime_identity_v2.schema.json")
        assert not issues, [f"{issue.path}: {issue.message}" for issue in issues]

        artifact["hostname"] = "must-not-validate"
        runtime_proof.write_artifact(path, artifact)
        issues = validate_file(path, ROOT / "schemas" / "runtime_identity_v2.schema.json")
        assert any("additional property" in issue.message for issue in issues)


def main() -> int:
    tests = [
        test_localhost_attempts_process_detection,
        test_loopback_attempts_process_detection,
        test_remote_url_skips_local_port_detection,
        test_remote_url_can_be_explicitly_treated_as_local,
        test_runtime_artifact_omits_absolute_repo_and_raw_process_arguments,
        test_remote_runtime_without_revision_binding_fails_proof,
        test_runtime_endpoint_rejects_serialized_secrets,
        test_generated_v2_artifact_is_strict_and_schema_valid,
    ]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
