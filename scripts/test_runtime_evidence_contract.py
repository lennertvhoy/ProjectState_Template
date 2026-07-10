#!/usr/bin/env python3
"""Negative and positive regressions for the slice-bound evidence contract."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from statedd_evidence_type_check import EvidenceTypeCheck  # noqa: E402
from statedd_runtime_truth_check import RuntimeTruthCheck  # noqa: E402
from statedd_validate_schema import ArtifactContractError, load_evidence_bundle  # noqa: E402


SLICE_ID = "BL-CORE-001"


def git(root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise AssertionError(f"git {' '.join(args)} failed: {completed.stderr}")
    return completed.stdout.strip()


def make_repo(root: Path) -> str:
    git(root, "init", "-q", "-b", "main")
    git(root, "config", "user.name", "StateDD Test")
    git(root, "config", "user.email", "statedd@example.invalid")
    (root / "seed.txt").write_text("seed\n", encoding="utf-8")
    git(root, "add", "seed.txt")
    git(root, "commit", "-q", "-m", "seed")
    return git(root, "rev-parse", "HEAD")


def write_bundle(
    root: Path,
    folder_name: str,
    *,
    slice_id: str,
    head: str,
    evidence_types: tuple[str, ...] = ("diff", "validation_output"),
    sensitive_runtime: bool = False,
    malformed_artifact: bool = False,
    runtime_head: str | None = None,
) -> Path:
    evidence_dir = root / "docs" / "evidence" / folder_name
    evidence_dir.mkdir(parents=True)

    runtime_identity: dict[str, object] = {
        "schema": "statedd.runtime_identity.v1",
        "captured_at": "2026-07-10T12:00:00Z",
        "privacy": {
            "profile": "public",
            "machine_identity": "normalized",
        },
        "repo": {
            "path": "$REPO_ROOT",
            "branch": "main",
            "head": runtime_head or head,
            "worktree_clean": False,
        },
        "runtime": {
            "required": False,
            "reason": "scripts-only validation slice",
        },
        "checks": {
            "runtime_not_applicable_recorded": True,
            "head_recorded": True,
        },
        "limits": [],
    }
    if sensitive_runtime:
        runtime_identity["repo"] = {
            "path": "/home/alice/private-project",
            "branch": "main",
            "head": head,
            "worktree_clean": False,
        }
        runtime_identity["runtime"] = {
            "required": True,
            "endpoint": "http://192.168.1.10:8123/private",
            "process": {
                "detected": True,
                "pid": 4242,
                "cwd": "/home/alice/private-project",
                "command": "python private_server.py --token secret",
            },
        }
        runtime_identity["checks"] = {
            "endpoint_reachable": True,
            "head_recorded": True,
        }
    (evidence_dir / "runtime_identity.json").write_text(
        json.dumps(runtime_identity, indent=2) + "\n",
        encoding="utf-8",
    )

    artifacts: list[dict[str, object]] = [
        {
            "path": "runtime_identity.json",
            "kind": "runtime_identity",
            "evidence_types": ["runtime_proof"],
            "redaction_status": "checked",
            "sensitive_data": "none_found",
        }
    ]
    for index, evidence_type in enumerate(evidence_types):
        artifact_path = f"proof-{index}.txt"
        (evidence_dir / artifact_path).write_text(f"{evidence_type}\n", encoding="utf-8")
        artifact: dict[str, object] = {
            "path": artifact_path,
            "kind": "command_output",
            "evidence_types": [evidence_type],
            "redaction_status": "checked",
            "sensitive_data": "none_found",
        }
        if malformed_artifact and index == 0:
            artifact.pop("redaction_status")
        artifacts.append(artifact)

    manifest = {
        "schema": "statedd.evidence_manifest.v1",
        "slice_id": slice_id,
        "manifest_status": "complete",
        "created_at": "2026-07-10T12:00:00Z",
        "repo": {"branch": "main", "head": head},
        "privacy": {
            "profile": "public",
            "machine_identity": "normalized",
        },
        "change": {"type": "config"},
        "runtime_identity": {
            "required": sensitive_runtime,
            "path": "runtime_identity.json",
            "status": "valid" if sensitive_runtime else "not_applicable",
        },
        "claims": [
            {
                "id": "C1",
                "claim": "Focused validation completed.",
                "status": "validated",
                "evidence": [artifact["path"] for artifact in artifacts],
            }
        ],
        "artifacts": artifacts,
        "redaction": {
            "status": "checked",
            "automated_scan": "passed",
            "manual_review": "completed",
            "known_limits": [],
        },
    }
    (evidence_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )
    return evidence_dir


def test_consumers_select_exact_slice_and_head_not_future_mtime() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        head = make_repo(root)
        exact = write_bundle(root, "exact", slice_id=SLICE_ID, head=head)
        stale = write_bundle(root, "stale", slice_id=SLICE_ID, head="f" * 40)
        os.utime(stale, (4_102_444_800, 4_102_444_800))

        bundle = load_evidence_bundle(root, SLICE_ID, head, privacy_profile="public")
        assert bundle.directory == exact
        explicit_bundle = load_evidence_bundle(
            root,
            SLICE_ID,
            head,
            evidence_dir=exact,
            privacy_profile="public",
        )
        assert explicit_bundle.directory == exact
        assert RuntimeTruthCheck(
            root,
            slice_id=SLICE_ID,
            expected_head=head,
            evidence_dir=exact,
            privacy_profile="public",
        ).run() == 0
        assert EvidenceTypeCheck(
            root,
            slice_id=SLICE_ID,
            expected_head=head,
            evidence_dir=exact,
            privacy_profile="public",
        ).run() == 0


def test_wrong_slice_or_head_cannot_reuse_historical_evidence() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        head = make_repo(root)
        write_bundle(root, "history", slice_id="BL-OLD-001", head=head)

        for slice_id, expected_head in ((SLICE_ID, head), ("BL-OLD-001", "a" * 40)):
            try:
                load_evidence_bundle(root, slice_id, expected_head, privacy_profile="public")
            except ArtifactContractError:
                pass
            else:
                raise AssertionError("Wrong-slice or wrong-head evidence was accepted")


def test_global_log_keywords_do_not_replace_typed_bundle_evidence() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        head = make_repo(root)
        write_bundle(
            root,
            "missing-validation",
            slice_id=SLICE_ID,
            head=head,
            evidence_types=("diff",),
        )
        docs = root / "docs"
        (docs / "EVIDENCE_LOG.md").write_text(
            "Historical validation, check, lint, schema, and coverage all passed.\n",
            encoding="utf-8",
        )

        checker = EvidenceTypeCheck(
            root,
            slice_id=SLICE_ID,
            expected_head=head,
            privacy_profile="public",
        )
        assert checker.run() == 1
        assert "validation_output" in checker.missing


def test_manifest_schema_is_applied_to_nested_artifacts() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        head = make_repo(root)
        write_bundle(
            root,
            "invalid",
            slice_id=SLICE_ID,
            head=head,
            malformed_artifact=True,
        )
        try:
            load_evidence_bundle(root, SLICE_ID, head, privacy_profile="public")
        except ArtifactContractError as exc:
            assert "redaction_status" in str(exc)
        else:
            raise AssertionError("Nested artifact schema violation was accepted")


def test_runtime_artifact_head_must_match_manifest_head() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        head = make_repo(root)
        write_bundle(
            root,
            "runtime-stale",
            slice_id=SLICE_ID,
            head=head,
            runtime_head="b" * 40,
        )
        try:
            load_evidence_bundle(root, SLICE_ID, head, privacy_profile="public")
        except ArtifactContractError as exc:
            assert "runtime identity repo.head" in str(exc)
        else:
            raise AssertionError("Stale runtime identity was accepted")


def test_public_bundle_rejects_sensitive_machine_identity() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        head = make_repo(root)
        write_bundle(
            root,
            "sensitive",
            slice_id=SLICE_ID,
            head=head,
            sensitive_runtime=True,
        )
        try:
            load_evidence_bundle(root, SLICE_ID, head, privacy_profile="public")
        except ArtifactContractError as exc:
            message = str(exc)
            assert "public runtime identity" in message
            assert "repo.path" in message
            assert "pid" in message
            assert "command" in message
        else:
            raise AssertionError("Sensitive public runtime identity was accepted")


def main() -> int:
    tests = [
        test_consumers_select_exact_slice_and_head_not_future_mtime,
        test_wrong_slice_or_head_cannot_reuse_historical_evidence,
        test_global_log_keywords_do_not_replace_typed_bundle_evidence,
        test_manifest_schema_is_applied_to_nested_artifacts,
        test_runtime_artifact_head_must_match_manifest_head,
        test_public_bundle_rejects_sensitive_machine_identity,
    ]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
