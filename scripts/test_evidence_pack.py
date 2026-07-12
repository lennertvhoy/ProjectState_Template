#!/usr/bin/env python3
"""Regression tests for statedd_evidence_pack.py.

Stays stdlib-only.
"""

from __future__ import annotations

import json
import hashlib
import os
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
                "runtime_identity": {
                    "required": False,
                    "path": "runtime_identity.json",
                    "status": "not_applicable",
                },
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
                "runtime_identity": {
                    "required": False,
                    "path": "runtime_identity.json",
                    "status": "not_applicable",
                },
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
                "manifest_status": "complete",
                "repo": {"branch": "main", "head": "a" * 40},
                "runtime_identity": {
                    "required": False,
                    "path": "runtime_identity.json",
                    "status": "not_applicable",
                },
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
                        "sha256": hashlib.sha256(b"hello\n").hexdigest(),
                        "redaction_status": "checked_with_limits",
                        "sensitive_data": "none_found",
                    }
                ],
                "redaction": {
                    "status": "checked_with_limits",
                    "automated_scan": "passed",
                    "manual_review": "completed",
                    "known_limits": ["Automated pattern coverage is intentionally conservative."],
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
        if artifact.get("redaction_status") != "manual_required":
            raise AssertionError("scan did not require manual review after findings")


def test_empty_claims_and_artifacts_fails_strict() -> None:
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
                "claims": [],
                "artifacts": [],
                "redaction": {
                    "status": "checked_with_limits",
                    "automated_scan": "passed",
                    "manual_review": "required",
                    "known_limits": ["Automated scan only."],
                },
            },
        )
        run_pack(["check", str(evidence), "--strict"], expect_success=False)


def test_skeleton_status_never_passes_strict_closure() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        evidence = Path(tmp) / "evidence"
        evidence.mkdir()
        write_manifest(
            evidence,
            {
                "schema": "statedd.evidence_manifest.v1",
                "slice_id": "BL-012",
                "manifest_status": "skeleton",
                "created_at": "2026-06-23T00:00:00+00:00",
                "repo": {"branch": "main", "head": "abc1234"},
                "runtime_identity": {"required": False},
                "claims": [],
                "artifacts": [],
                "redaction": {
                    "status": "checked_with_limits",
                    "automated_scan": "not_applicable",
                    "manual_review": "required",
                    "known_limits": ["Skeleton manifest; redaction review deferred."],
                },
            },
        )
        run_pack(["check", str(evidence), "--strict"], expect_success=False)


def test_strict_rejects_unvalidated_unhashed_sensitive_and_directory_artifacts() -> None:
    cases = (
        ("not_validated", None, "none_found", False),
        ("validated", None, "none_found", False),
        ("validated", "hash", "possible", False),
        ("validated", "hash", "none_found", True),
    )
    for claim_status, hash_mode, sensitive_data, directory in cases:
        with tempfile.TemporaryDirectory() as tmp:
            evidence = Path(tmp) / "evidence"
            evidence.mkdir()
            artifact = evidence / "artifact.txt"
            if directory:
                artifact.mkdir()
                digest = hashlib.sha256(b"").hexdigest()
            else:
                artifact.write_text("hello\n", encoding="utf-8")
                digest = hashlib.sha256(b"hello\n").hexdigest()
            manifest = minimal_manifest("artifact.txt")
            manifest["repo"]["head"] = "a" * 40
            manifest["claims"][0]["status"] = claim_status
            manifest["artifacts"][0]["sha256"] = digest if hash_mode else None
            manifest["artifacts"][0]["sensitive_data"] = sensitive_data
            write_manifest(evidence, manifest)
            run_pack(["check", str(evidence), "--strict"], expect_success=False)


def test_strict_validates_required_runtime_identity_contract() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        evidence = Path(tmp) / "evidence"
        evidence.mkdir()
        runtime = evidence / "runtime_identity.json"
        runtime.write_text("{}\n", encoding="utf-8")
        manifest = minimal_manifest("runtime_identity.json")
        manifest["repo"]["head"] = "a" * 40
        manifest["runtime_identity"] = {
            "required": True,
            "path": "runtime_identity.json",
            "status": "valid",
        }
        manifest["artifacts"][0].update(
            {
                "kind": "runtime_identity",
                "sha256": hashlib.sha256(runtime.read_bytes()).hexdigest(),
            }
        )
        write_manifest(evidence, manifest)

        completed = run_pack(["check", str(evidence), "--strict"], expect_success=False)
        if "Strict runtime identity" not in completed.stdout:
            raise AssertionError(f"Invalid runtime identity contract was not surfaced:\n{completed.stdout}")


def test_strict_requires_known_limits_when_manual_review_required() -> None:
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
                    "known_limits": [],
                },
            },
        )
        run_pack(["check", str(evidence), "--strict"], expect_success=False)


def minimal_manifest(ref: str) -> dict:
    return {
        "schema": "statedd.evidence_manifest.v1",
        "slice_id": "BL-PATH-001",
        "manifest_status": "complete",
        "created_at": "2026-07-11T00:00:00+00:00",
        "repo": {"branch": "main", "head": "abc1234"},
        "runtime_identity": {
            "required": False,
            "path": "runtime_identity.json",
            "status": "not_applicable",
        },
        "claims": [
            {"id": "C1", "claim": "confined artifact", "status": "validated", "evidence": [ref]}
        ],
        "artifacts": [
            {
                "path": ref,
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
    }


def write_strict_fixture(evidence: Path) -> dict:
    artifact = evidence / "artifact.txt"
    artifact.write_text("hello\n", encoding="utf-8")
    manifest = minimal_manifest("artifact.txt")
    manifest["repo"]["head"] = "a" * 40
    manifest["artifacts"][0]["sha256"] = hashlib.sha256(artifact.read_bytes()).hexdigest()
    write_manifest(evidence, manifest)
    return manifest


def test_strict_rejects_unlisted_disk_file_and_secret_manifest_metadata() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        evidence = Path(tmp) / "evidence"
        evidence.mkdir()
        manifest = write_strict_fixture(evidence)
        (evidence / "secret.txt").write_text('API_KEY="supersecretvalue"\n', encoding="utf-8")
        completed = run_pack(["check", str(evidence), "--strict"], expect_success=False)
        if "unlisted evidence files" not in completed.stdout:
            raise AssertionError(f"Unlisted evidence file was not surfaced:\n{completed.stdout}")

        (evidence / "secret.txt").unlink()
        manifest["claims"][0]["claim"] = 'API_KEY="supersecretvalue"'
        write_manifest(evidence, manifest)
        completed = run_pack(["check", str(evidence), "--strict"], expect_success=False)
        if "Possible" not in completed.stdout:
            raise AssertionError(f"Secret-bearing manifest metadata was not surfaced:\n{completed.stdout}")


def test_strict_rescans_hashed_artifact_even_when_manifest_claims_clean() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        evidence = Path(tmp) / "evidence"
        evidence.mkdir()
        artifact = evidence / "artifact.txt"
        artifact.write_text('API_KEY="supersecretvalue"\n', encoding="utf-8")
        manifest = minimal_manifest("artifact.txt")
        manifest["repo"]["head"] = "a" * 40
        manifest["artifacts"][0]["sha256"] = hashlib.sha256(artifact.read_bytes()).hexdigest()
        write_manifest(evidence, manifest)
        completed = run_pack(["check", str(evidence), "--strict"], expect_success=False)
        if "detectable sensitive content" not in completed.stdout:
            raise AssertionError(f"Strict evidence did not rescan artifact bytes:\n{completed.stdout}")


def test_strict_requires_explicit_completion_runtime_and_real_redaction_review() -> None:
    mutations = (
        lambda manifest: manifest.pop("manifest_status"),
        lambda manifest: manifest.pop("runtime_identity"),
        lambda manifest: manifest.update(
            {
                "redaction": {
                    "status": "checked",
                    "automated_scan": "not_applicable",
                    "manual_review": "not_applicable",
                    "known_limits": [],
                }
            }
        ),
        lambda manifest: manifest.update(
            {
                "redaction": {
                    "status": "checked_with_limits",
                    "automated_scan": "passed",
                    "manual_review": "completed",
                    "known_limits": [],
                }
            }
        ),
    )
    for mutate in mutations:
        with tempfile.TemporaryDirectory() as tmp:
            evidence = Path(tmp) / "evidence"
            evidence.mkdir()
            manifest = write_strict_fixture(evidence)
            mutate(manifest)
            write_manifest(evidence, manifest)
            run_pack(["check", str(evidence), "--strict"], expect_success=False)


def test_init_rejects_symlinked_parent_before_creating_external_pack() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        outside = root / "outside"
        outside.mkdir()
        os.symlink(outside, root / "linked")
        run_pack(["init", str(root / "linked" / "new-pack")], expect_success=False)
        if (outside / "new-pack").exists():
            raise AssertionError("Evidence init wrote through a symlinked parent before refusal")


def test_absolute_traversal_and_windows_paths_fail_before_artifact_io() -> None:
    for ref in ("/etc/hosts", "../outside.txt", "nested/../../outside.txt", "C:\\outside.txt"):
        with tempfile.TemporaryDirectory() as tmp:
            evidence = Path(tmp) / "evidence"
            evidence.mkdir()
            write_manifest(evidence, minimal_manifest(ref))
            before = (evidence / "manifest.json").read_bytes()
            for command in ("check", "hash", "scan"):
                run_pack([command, str(evidence), *( ["--strict"] if command == "check" else [])], expect_success=False)
                if (evidence / "manifest.json").read_bytes() != before:
                    raise AssertionError(f"Unsafe {ref!r} mutated manifest during {command}")


def test_nested_artifact_symlink_is_rejected_for_all_commands() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        evidence = root / "evidence"
        outside = root / "outside"
        evidence.mkdir()
        outside.mkdir()
        (outside / "artifact.txt").write_text("external\n", encoding="utf-8")
        os.symlink(outside, evidence / "linked")
        write_manifest(evidence, minimal_manifest("linked/artifact.txt"))
        before = (evidence / "manifest.json").read_bytes()
        for command in ("check", "hash", "scan"):
            run_pack([command, str(evidence)], expect_success=False)
        if (evidence / "manifest.json").read_bytes() != before:
            raise AssertionError("Nested evidence symlink caused manifest mutation")


def test_duplicate_json_keys_fail_closed() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        evidence = Path(tmp) / "evidence"
        evidence.mkdir()
        (evidence / "manifest.json").write_text(
            '{"schema":"statedd.evidence_manifest.v1","artifacts":[],"artifacts":[]}',
            encoding="utf-8",
        )
        run_pack(["check", str(evidence)], expect_success=False)


def test_symlinked_evidence_root_is_rejected() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        actual = root / "actual"
        actual.mkdir()
        write_manifest(actual, minimal_manifest("artifact.txt"))
        (actual / "artifact.txt").write_text("inside\n", encoding="utf-8")
        linked = root / "linked"
        os.symlink(actual, linked)
        completed = run_pack(["check", str(linked)], expect_success=False)
        if "symlink" not in completed.stdout.lower():
            raise AssertionError(f"Expected evidence-root symlink refusal:\n{completed.stdout}")


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
        test_empty_claims_and_artifacts_fails_strict,
        test_skeleton_status_never_passes_strict_closure,
        test_strict_rejects_unvalidated_unhashed_sensitive_and_directory_artifacts,
        test_strict_validates_required_runtime_identity_contract,
        test_strict_requires_known_limits_when_manual_review_required,
        test_absolute_traversal_and_windows_paths_fail_before_artifact_io,
        test_nested_artifact_symlink_is_rejected_for_all_commands,
        test_duplicate_json_keys_fail_closed,
        test_symlinked_evidence_root_is_rejected,
    ]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
