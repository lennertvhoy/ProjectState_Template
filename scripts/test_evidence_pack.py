#!/usr/bin/env python3
"""Regression tests for statedd_evidence_pack.py.

Stays stdlib-only.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACK_SCRIPT = ROOT / "scripts" / "statedd_evidence_pack.py"


def run_pack(args: list[str], *, expect_success: bool) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        [sys.executable, str(PACK_SCRIPT), *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if expect_success and completed.returncode != 0:
        raise AssertionError(
            f"Expected success for {args}, got {completed.returncode}\n"
            f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )
    if not expect_success and completed.returncode == 0:
        raise AssertionError(
            f"Expected failure for {args}, got success\nstdout:\n{completed.stdout}"
        )
    return completed


def write_manifest(evidence_dir: Path, data: dict) -> None:
    (evidence_dir / "manifest.json").write_text(
        json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def test_init_creates_manifest() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        evidence = Path(tmp) / "evidence"
        run_pack(["init", str(evidence), "--slice-id", "BL-012"], expect_success=True)
        manifest = json.loads((evidence / "manifest.json").read_text(encoding="utf-8"))
        if manifest.get("schema") != "statedd.evidence_manifest.v1":
            raise AssertionError("Manifest has wrong schema")
        if manifest.get("slice_id") != "BL-012":
            raise AssertionError("Manifest has wrong slice_id")


def test_init_detects_runtime_identity() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        evidence = Path(tmp) / "evidence"
        evidence.mkdir()
        (evidence / "runtime_identity.json").write_text("{}", encoding="utf-8")
        run_pack(["init", str(evidence), "--slice-id", "BL-012"], expect_success=True)
        manifest = json.loads((evidence / "manifest.json").read_text(encoding="utf-8"))
        if manifest["runtime_identity"].get("required") is not True:
            raise AssertionError("Expected runtime_identity.required=true")


def test_valid_manifest_passes_check() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        evidence = Path(tmp) / "evidence"
        evidence.mkdir()
        (evidence / "artifact.txt").write_text("hello world\n", encoding="utf-8")
        write_manifest(
            evidence,
            {
                "schema": "statedd.evidence_manifest.v1",
                "slice_id": "BL-012",
                "created_at": "2026-06-23T00:00:00+00:00",
                "repo": {"branch": "main", "head": "abc1234"},
                "runtime_identity": {"required": False},
                "claims": [
                    {
                        "id": "C1",
                        "claim": "artifact exists",
                        "status": "validated",
                        "evidence": ["artifact.txt"],
                    }
                ],
                "artifacts": [
                    {
                        "path": "artifact.txt",
                        "kind": "doc",
                        "sha256": None,
                        "redaction_status": "checked",
                        "sensitive_data": "none_found",
                    }
                ],
                "redaction": {
                    "status": "checked",
                    "automated_scan": "passed",
                    "manual_review": "completed",
                    "known_limits": [],
                },
            },
        )
        run_pack(["check", str(evidence)], expect_success=True)


def test_missing_artifact_fails() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        evidence = Path(tmp) / "evidence"
        evidence.mkdir()
        write_manifest(
            evidence,
            {
                "schema": "statedd.evidence_manifest.v1",
                "slice_id": "BL-012",
                "created_at": "2026-06-23T00:00:00+00:00",
                "repo": {"branch": "main", "head": "abc1234"},
                "runtime_identity": {"required": False},
                "claims": [
                    {
                        "id": "C1",
                        "claim": "missing artifact exists",
                        "status": "validated",
                        "evidence": ["missing.txt"],
                    }
                ],
                "artifacts": [
                    {
                        "path": "missing.txt",
                        "kind": "doc",
                        "sha256": None,
                        "redaction_status": "checked",
                        "sensitive_data": "none_found",
                    }
                ],
                "redaction": {
                    "status": "checked",
                    "automated_scan": "passed",
                    "manual_review": "completed",
                    "known_limits": [],
                },
            },
        )
        run_pack(["check", str(evidence)], expect_success=False)


def test_hash_mismatch_fails() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        evidence = Path(tmp) / "evidence"
        evidence.mkdir()
        (evidence / "artifact.txt").write_text("hello world\n", encoding="utf-8")
        write_manifest(
            evidence,
            {
                "schema": "statedd.evidence_manifest.v1",
                "slice_id": "BL-012",
                "created_at": "2026-06-23T00:00:00+00:00",
                "repo": {"branch": "main", "head": "abc1234"},
                "runtime_identity": {"required": False},
                "claims": [
                    {
                        "id": "C1",
                        "claim": "artifact hash matches",
                        "status": "validated",
                        "evidence": ["artifact.txt"],
                    }
                ],
                "artifacts": [
                    {
                        "path": "artifact.txt",
                        "kind": "doc",
                        "sha256": "0000000000000000000000000000000000000000000000000000000000000000",
                        "redaction_status": "checked",
                        "sensitive_data": "none_found",
                    }
                ],
                "redaction": {
                    "status": "checked",
                    "automated_scan": "passed",
                    "manual_review": "completed",
                    "known_limits": [],
                },
            },
        )
        run_pack(["check", str(evidence)], expect_success=False)


def test_claim_without_evidence_fails() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        evidence = Path(tmp) / "evidence"
        evidence.mkdir()
        write_manifest(
            evidence,
            {
                "schema": "statedd.evidence_manifest.v1",
                "slice_id": "BL-012",
                "created_at": "2026-06-23T00:00:00+00:00",
                "repo": {"branch": "main", "head": "abc1234"},
                "runtime_identity": {"required": False},
                "claims": [
                    {
                        "id": "C1",
                        "claim": "no evidence",
                        "status": "validated",
                        "evidence": [],
                    }
                ],
                "artifacts": [],
                "redaction": {
                    "status": "checked",
                    "automated_scan": "passed",
                    "manual_review": "completed",
                    "known_limits": [],
                },
            },
        )
        run_pack(["check", str(evidence)], expect_success=False)


def test_unchecked_redaction_fails_strict() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        evidence = Path(tmp) / "evidence"
        evidence.mkdir()
        (evidence / "artifact.txt").write_text("hello\n", encoding="utf-8")
        write_manifest(
            evidence,
            {
                "schema": "statedd.evidence_manifest.v1",
                "slice_id": "BL-012",
                "created_at": "2026-06-23T00:00:00+00:00",
                "repo": {"branch": "main", "head": "abc1234"},
                "runtime_identity": {"required": False},
                "claims": [
                    {
                        "id": "C1",
                        "claim": "artifact exists",
                        "status": "validated",
                        "evidence": ["artifact.txt"],
                    }
                ],
                "artifacts": [
                    {
                        "path": "artifact.txt",
                        "kind": "doc",
                        "sha256": None,
                        "redaction_status": "unchecked",
                        "sensitive_data": "unknown",
                    }
                ],
                "redaction": {
                    "status": "unchecked",
                    "automated_scan": "not_applicable",
                    "manual_review": "required",
                    "known_limits": [],
                },
            },
        )
        run_pack(["check", str(evidence), "--strict"], expect_success=False)


def test_checked_with_limits_passes_strict() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        evidence = Path(tmp) / "evidence"
        evidence.mkdir()
        (evidence / "artifact.txt").write_text("hello\n", encoding="utf-8")
        write_manifest(
            evidence,
            {
                "schema": "statedd.evidence_manifest.v1",
                "slice_id": "BL-012",
                "created_at": "2026-06-23T00:00:00+00:00",
                "repo": {"branch": "main", "head": "abc1234"},
                "runtime_identity": {"required": False},
                "claims": [
                    {
                        "id": "C1",
                        "claim": "artifact exists",
                        "status": "validated",
                        "evidence": ["artifact.txt"],
                    }
                ],
                "artifacts": [
                    {
                        "path": "artifact.txt",
                        "kind": "doc",
                        "sha256": None,
                        "redaction_status": "checked_with_limits",
                        "sensitive_data": "none_found",
                    }
                ],
                "redaction": {
                    "status": "checked_with_limits",
                    "automated_scan": "passed",
                    "manual_review": "required",
                    "known_limits": ["Automated scan only; manual review not performed."],
                },
            },
        )
        run_pack(["check", str(evidence), "--strict"], expect_success=True)


def test_binary_artifact_without_manual_review_fails_strict() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        evidence = Path(tmp) / "evidence"
        evidence.mkdir()
        (evidence / "screenshot.png").write_bytes(b"\x89PNG\r\n\x1a\n")
        write_manifest(
            evidence,
            {
                "schema": "statedd.evidence_manifest.v1",
                "slice_id": "BL-012",
                "created_at": "2026-06-23T00:00:00+00:00",
                "repo": {"branch": "main", "head": "abc1234"},
                "runtime_identity": {"required": False},
                "claims": [
                    {
                        "id": "C1",
                        "claim": "screenshot exists",
                        "status": "validated",
                        "evidence": ["screenshot.png"],
                    }
                ],
                "artifacts": [
                    {
                        "path": "screenshot.png",
                        "kind": "screenshot",
                        "sha256": None,
                        "redaction_status": "unchecked",
                        "sensitive_data": "unknown",
                    }
                ],
                "redaction": {
                    "status": "checked_with_limits",
                    "automated_scan": "not_applicable",
                    "manual_review": "required",
                    "known_limits": [],
                },
            },
        )
        run_pack(["check", str(evidence), "--strict"], expect_success=False)


def test_hash_command_updates_hashes() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        evidence = Path(tmp) / "evidence"
        evidence.mkdir()
        (evidence / "artifact.txt").write_text("hello world\n", encoding="utf-8")
        write_manifest(
            evidence,
            {
                "schema": "statedd.evidence_manifest.v1",
                "slice_id": "BL-012",
                "created_at": "2026-06-23T00:00:00+00:00",
                "repo": {"branch": "main", "head": "abc1234"},
                "runtime_identity": {"required": False},
                "claims": [],
                "artifacts": [
                    {
                        "path": "artifact.txt",
                        "kind": "doc",
                        "sha256": None,
                        "redaction_status": "unchecked",
                        "sensitive_data": "unknown",
                    }
                ],
                "redaction": {
                    "status": "unchecked",
                    "automated_scan": "not_applicable",
                    "manual_review": "required",
                    "known_limits": [],
                },
            },
        )
        run_pack(["hash", str(evidence)], expect_success=True)
        manifest = json.loads((evidence / "manifest.json").read_text(encoding="utf-8"))
        artifact = manifest["artifacts"][0]
        if not artifact.get("sha256") or len(artifact["sha256"]) != 64:
            raise AssertionError("hash command did not set a valid sha256")


def test_scan_flags_possible_secret() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        evidence = Path(tmp) / "evidence"
        evidence.mkdir()
        (evidence / "command_output.txt").write_text(
            "export API_KEY=sk-1234567890abcdef1234567890abcdef\n", encoding="utf-8"
        )
        write_manifest(
            evidence,
            {
                "schema": "statedd.evidence_manifest.v1",
                "slice_id": "BL-012",
                "created_at": "2026-06-23T00:00:00+00:00",
                "repo": {"branch": "main", "head": "abc1234"},
                "runtime_identity": {"required": False},
                "claims": [],
                "artifacts": [
                    {
                        "path": "command_output.txt",
                        "kind": "command_output",
                        "sha256": None,
                        "redaction_status": "unchecked",
                        "sensitive_data": "unknown",
                    }
                ],
                "redaction": {
                    "status": "unchecked",
                    "automated_scan": "not_applicable",
                    "manual_review": "required",
                    "known_limits": [],
                },
            },
        )
        run_pack(["scan", str(evidence)], expect_success=True)
        manifest = json.loads((evidence / "manifest.json").read_text(encoding="utf-8"))
        artifact = manifest["artifacts"][0]
        if artifact.get("sensitive_data") != "possible":
            raise AssertionError("scan did not flag possible secret")
        if artifact.get("redaction_status") != "checked_with_limits":
            raise AssertionError("scan did not set checked_with_limits")


def main() -> int:
    tests = [
        test_init_creates_manifest,
        test_init_detects_runtime_identity,
        test_valid_manifest_passes_check,
        test_missing_artifact_fails,
        test_hash_mismatch_fails,
        test_claim_without_evidence_fails,
        test_unchecked_redaction_fails_strict,
        test_checked_with_limits_passes_strict,
        test_binary_artifact_without_manual_review_fails_strict,
        test_hash_command_updates_hashes,
        test_scan_flags_possible_secret,
    ]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
