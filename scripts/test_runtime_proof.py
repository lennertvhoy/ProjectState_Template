#!/usr/bin/env python3
"""Focused regression tests for statedd_runtime_proof.py.

These tests stay stdlib-only and avoid real network or /proc dependencies.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import statedd_runtime_proof as runtime_proof  # noqa: E402


def fake_probe(url: str, timeout: float) -> tuple[dict[str, object], list[str]]:
    return (
        {
            "url": url,
            "http_status": 200,
            "content_type": "text/plain",
            "response_sha256": "fake",
            "response_bytes": 4,
        },
        [],
    )


def make_args(url: str, *, expect_local: bool = False, port: int | None = None) -> argparse.Namespace:
    return argparse.Namespace(
        url=url,
        timeout=0.01,
        port=port,
        process_name=None,
        kind="web",
        expect_local=expect_local,
    )


def build_with_fake_process(url: str, *, expect_local: bool = False) -> tuple[dict[str, object], list[int | None]]:
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
                "cwd": str(ROOT),
                "command": "fake server",
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
            make_args(url, expect_local=expect_local),
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
    artifact, calls = build_with_fake_process("https://example.com")
    if calls:
        raise AssertionError(f"remote endpoint should not inspect local port 443, got calls {calls}")
    process = artifact["runtime"]["process"]
    if process["detected"] is not False:
        raise AssertionError("remote endpoint process proof should be not detected")
    if process["reason"] != "remote endpoint; local process ownership is not applicable":
        raise AssertionError(f"Unexpected remote skip reason: {process['reason']}")
    if artifact["checks"]["duplicate_runtime_checked"] is not False:
        raise AssertionError("remote endpoint should not mark duplicate runtime checked")


def test_remote_url_can_be_explicitly_treated_as_local() -> None:
    artifact, calls = build_with_fake_process("https://example.com", expect_local=True)
    if calls != [443]:
        raise AssertionError(f"--expect-local should inspect inferred port 443, got calls {calls}")
    if artifact["checks"]["process_detected"] is not True:
        raise AssertionError("--expect-local process proof should be marked detected")


def test_written_artifact_normalizes_public_machine_identity() -> None:
    artifact, _ = build_with_fake_process("http://localhost:8123")
    output = ROOT / ".runtime-proof-test.json"
    try:
        runtime_proof.write_artifact(output, artifact)
        written = output.read_text(encoding="utf-8")
        if "/home/" in written or '"pid"' in written or '"command"' in written or '"cwd"' in written:
            raise AssertionError(f"Public runtime artifact retained machine identity:\n{written}")
        parsed = runtime_proof.json.loads(written)
        if parsed["privacy"]["machine_identity"] != "normalized":
            raise AssertionError("Public runtime artifact did not declare normalized machine identity")
    finally:
        output.unlink(missing_ok=True)


def main() -> int:
    tests = [
        test_localhost_attempts_process_detection,
        test_loopback_attempts_process_detection,
        test_remote_url_skips_local_port_detection,
        test_remote_url_can_be_explicitly_treated_as_local,
        test_written_artifact_normalizes_public_machine_identity,
    ]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
