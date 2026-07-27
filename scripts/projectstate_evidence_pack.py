#!/usr/bin/env python3
"""Manage ProjectState evidence pack manifests and a conservative redaction gate.

This script stays stdlib-only. It creates, validates, hashes, and scans
artifact manifests under a single evidence folder. It never claims that an
absence of flagged secrets proves that no secrets exist.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

try:
    from projectstate_contracts import (
        ContractError,
        UnsafePathError,
        confined_path,
        load_json_file,
        normalize_relative_path,
        safe_root_path,
    )
    from projectstate_validate_schema import validate_file
except ModuleNotFoundError:  # pragma: no cover - pytest package import path
    from scripts.projectstate_contracts import (
        ContractError,
        UnsafePathError,
        confined_path,
        load_json_file,
        normalize_relative_path,
        safe_root_path,
    )
    from scripts.projectstate_validate_schema import validate_file


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "projectstate.evidence_manifest.v1"
MANIFEST_NAME = "manifest.json"
RUNTIME_IDENTITY_NAME = "runtime_identity.json"

# Text-like suffixes the scanner will read. Binary or image artifacts must be
# reviewed manually.
TEXT_SUFFIXES = {
    ".txt",
    ".md",
    ".json",
    ".yaml",
    ".yml",
    ".py",
    ".sh",
    ".bash",
    ".log",
    ".csv",
    ".ini",
    ".cfg",
    ".conf",
    ".toml",
}

# Suffixes that are always treated as binary/image for redaction purposes.
BINARY_SUFFIXES = {
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".gif",
    ".bmp",
    ".svg",
    ".pdf",
    ".zip",
    ".tar",
    ".gz",
    ".bz2",
    ".xz",
    ".7z",
    ".bin",
    ".exe",
    ".dll",
    ".so",
    ".dylib",
}

# Conservative secret patterns. Matches are "possible" findings, not proof.
SECRET_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "private key",
        re.compile(r"-----BEGIN (RSA |DSA |EC |OPENSSH )?PRIVATE KEY-----", re.IGNORECASE),
    ),
    (
        "API key / token",
        re.compile(r"\b(api[_-]?key|apikey|api_secret|secret[_-]?key)\b\s*[:=]\s*['\"\w-]{8,}", re.IGNORECASE),
    ),
    (
        "Bearer token",
        re.compile(r"\b[bB]earer\s+[A-Za-z0-9_\-\.]{20,}"),
    ),
    (
        "password assignment",
        re.compile(r"\b(password|passwd|pwd)\b\s*[:=]\s*['\"][^'\"]{4,}['\"]", re.IGNORECASE),
    ),
    (
        "env-like secret",
        re.compile(r"\b[A-Z_]*(?:SECRET|TOKEN|PASSWORD|API_KEY|ACCESS_KEY|PRIVATE_KEY)[A-Z_]*\b\s*[:=]\s*['\"][^'\"]{4,}['\"]", re.IGNORECASE),
    ),
]


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


def git_value(repo: Path, args: list[str], fallback: str | None = None) -> str | None:
    code, stdout, _ = run_command(["git", *args], repo)
    if code != 0:
        return fallback
    return stdout or fallback


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def looks_textual(path: Path) -> bool:
    return path.suffix.lower() in TEXT_SUFFIXES


def looks_binary(path: Path) -> bool:
    return path.suffix.lower() in BINARY_SUFFIXES


def load_manifest(evidence_dir: Path) -> dict[str, Any]:
    path = confined_path(evidence_dir, MANIFEST_NAME)
    if not path.exists():
        raise SystemExit(f"Manifest not found: {path}")
    try:
        data = load_json_file(path)
    except ContractError as exc:
        raise SystemExit(f"Malformed manifest JSON: {exc}")
    if not isinstance(data, dict):
        raise SystemExit("Manifest top-level value must be an object")
    return data


def save_manifest(evidence_dir: Path, data: dict[str, Any]) -> Path:
    path = confined_path(evidence_dir, MANIFEST_NAME)
    content = (json.dumps(data, indent=2, sort_keys=True) + "\n").encode("utf-8")
    fd, tmp_name = tempfile.mkstemp(prefix=".manifest.", dir=evidence_dir)
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, path)
    finally:
        tmp_path.unlink(missing_ok=True)
    return path


def preflight_evidence_paths(
    evidence_dir: Path,
    refs: list[Any],
    *,
    reject_duplicates: bool = False,
) -> tuple[dict[str, Path], list[str]]:
    """Validate every repository-controlled path before reading any artifact."""
    paths: dict[str, Path] = {}
    issues: list[str] = []
    for index, ref in enumerate(refs):
        if not isinstance(ref, str) or not ref:
            issues.append(f"Evidence path {index} is not a non-empty string")
            continue
        try:
            normalized = normalize_relative_path(ref)
            canonical_ref = normalized.as_posix()
            path = confined_path(evidence_dir, normalized)
        except UnsafePathError as exc:
            issues.append(f"Unsafe evidence path {ref!r}: {exc}")
            continue
        if reject_duplicates and canonical_ref in paths:
            issues.append(f"Duplicate evidence artifact path: {canonical_ref}")
            continue
        paths[canonical_ref] = path
    return paths, issues


def artifact_kind(path: Path) -> str:
    suffix = path.suffix.lower()
    name = path.name.lower()
    if name == RUNTIME_IDENTITY_NAME:
        return "runtime_identity"
    if suffix in {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".svg"}:
        return "screenshot"
    if suffix in {".log"}:
        return "log"
    if suffix in {".md", ".txt"}:
        return "doc"
    if suffix in {".json", ".yaml", ".yml", ".py", ".sh", ".bash", ".csv", ".ini", ".cfg", ".conf", ".toml"}:
        return "command_output"
    return "other"


def scan_text_file(path: Path) -> tuple[str, list[str]]:
    """Return (sensitive_data_status, list_of_finding_descriptions)."""
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return "unknown", [f"Could not decode {path.name} as text; treat as binary/manual review."]

    findings: list[str] = []
    for label, pattern in SECRET_PATTERNS:
        if pattern.search(text):
            findings.append(f"Possible {label} pattern found in {path.name}")
    if findings:
        return "possible", findings
    return "none_found", []


def scan_text(text: str, label: str) -> list[str]:
    """Return possible-secret findings for in-memory manifest metadata."""
    return [
        f"Possible {finding_label} pattern found in {label}"
        for finding_label, pattern in SECRET_PATTERNS
        if pattern.search(text)
    ]


def manifest_strings(value: Any):
    """Yield raw string keys/values without JSON escaping away secret syntax."""
    if isinstance(value, dict):
        for key, nested in value.items():
            yield str(key)
            yield from manifest_strings(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from manifest_strings(nested)
    elif isinstance(value, str):
        yield value


def repo_block(repo: Path | None) -> dict[str, Any]:
    if repo is None:
        return {"branch": None, "head": None}
    return {
        "branch": git_value(repo, ["rev-parse", "--abbrev-ref", "HEAD"]),
        "head": git_value(repo, ["rev-parse", "HEAD"]),
    }


def command_init(
    evidence_dir: Path,
    slice_id: str | None = None,
    *,
    force: bool = False,
    repo: Path | None = None,
) -> int:
    try:
        evidence_dir = safe_root_path(evidence_dir, must_exist=False)
        evidence_dir.mkdir(parents=True, exist_ok=True)
        # Recheck after creation to close the normal create-then-write gap.
        evidence_dir = safe_root_path(evidence_dir, must_exist=True)
    except UnsafePathError as exc:
        raise SystemExit(str(exc)) from exc
    manifest_path = confined_path(evidence_dir, MANIFEST_NAME)
    if manifest_path.exists() and not force:
        print(f"Manifest already exists: {manifest_path}")
        print("Use --force to overwrite.")
        return 1

    if repo is not None:
        repo = safe_root_path(repo, must_exist=True)
        try:
            evidence_dir.relative_to(repo)
        except ValueError as exc:
            raise SystemExit("Evidence directory must remain inside the explicit repository") from exc
    else:
        code, stdout, _ = run_command(["git", "rev-parse", "--show-toplevel"], evidence_dir)
        if code == 0 and stdout:
            try:
                discovered = safe_root_path(stdout, must_exist=True)
                evidence_dir.relative_to(discovered)
            except (UnsafePathError, ValueError):
                repo = None
            else:
                repo = discovered

    runtime_path = confined_path(evidence_dir, RUNTIME_IDENTITY_NAME)
    runtime_identity: dict[str, Any] = {
        "required": runtime_path.exists(),
        "path": RUNTIME_IDENTITY_NAME,
        "status": "valid" if runtime_path.exists() else "not_applicable",
    }

    manifest: dict[str, Any] = {
        "schema": SCHEMA,
        "slice_id": slice_id or "BL-000",
        "manifest_status": "skeleton",
        "created_at": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "repo": repo_block(repo),
        "runtime_identity": runtime_identity,
        "claims": [],
        "artifacts": [],
        "redaction": {
            "status": "unchecked",
            "automated_scan": "not_applicable",
            "manual_review": "required",
            "known_limits": ["Manifest created; redaction review not yet performed."],
        },
    }
    save_manifest(evidence_dir, manifest)
    print(f"Created manifest: {manifest_path}")
    return 0


def command_check(evidence_dir: Path, *, strict: bool = False) -> int:
    manifest = load_manifest(evidence_dir)
    issues: list[str] = []

    schema_path = ROOT / "schemas" / "evidence_manifest.schema.json"
    schema_issues = validate_file(confined_path(evidence_dir, MANIFEST_NAME), schema_path)
    issues.extend(f"Schema {issue.path}: {issue.message}" for issue in schema_issues)

    # Schema-level checks (beyond the JSON schema itself).
    if manifest.get("schema") != SCHEMA:
        issues.append(f"Unexpected schema: {manifest.get('schema')}")

    claims = manifest.get("claims", [])
    if not isinstance(claims, list):
        issues.append("'claims' must be an array")
        claims = []

    artifacts = manifest.get("artifacts", [])
    if not isinstance(artifacts, list):
        issues.append("'artifacts' must be an array")
        artifacts = []

    raw_artifact_refs = [a.get("path") for a in artifacts if isinstance(a, dict)]
    raw_claim_refs = [
        ref
        for claim in claims
        if isinstance(claim, dict) and isinstance(claim.get("evidence"), list)
        for ref in claim["evidence"]
    ]
    runtime_identity = manifest.get("runtime_identity")
    raw_runtime_ref = (
        runtime_identity.get("path", RUNTIME_IDENTITY_NAME)
        if isinstance(runtime_identity, dict) and runtime_identity.get("required") is True
        else None
    )
    artifact_path_map, path_issues = preflight_evidence_paths(
        evidence_dir,
        raw_artifact_refs,
        reject_duplicates=True,
    )
    all_ref_map, all_ref_issues = preflight_evidence_paths(
        evidence_dir,
        [*raw_artifact_refs, *raw_claim_refs, *([raw_runtime_ref] if raw_runtime_ref else [])],
    )
    issues.extend(path_issues)
    issues.extend(all_ref_issues)
    if path_issues or all_ref_issues:
        print("Manifest check failed:")
        for issue in issues:
            print(f"  - {issue}")
        return 1
    artifact_paths = set(artifact_path_map)
    referenced_artifacts: set[str] = set()
    claim_ids: set[str] = set()

    for index, claim in enumerate(claims):
        if not isinstance(claim, dict):
            issues.append(f"Claim {index} is not an object")
            continue
        claim_id = claim.get("id")
        if isinstance(claim_id, str):
            if claim_id in claim_ids:
                issues.append(f"Duplicate claim id: {claim_id}")
            claim_ids.add(claim_id)
        if strict and claim.get("status") != "validated":
            issues.append(
                f"Strict check failed: claim {claim.get('id', index)} has status={claim.get('status')}"
            )
        evidence = claim.get("evidence", [])
        if not isinstance(evidence, list) or not evidence:
            issues.append(f"Claim {claim.get('id', index)} has no evidence artifacts")
            continue
        for ref in evidence:
            canonical_ref = normalize_relative_path(ref).as_posix()
            referenced_artifacts.add(canonical_ref)
            artifact_path = all_ref_map[canonical_ref]
            if not artifact_path.exists():
                issues.append(f"Claim {claim.get('id', index)} references missing artifact: {ref}")
            if ref not in artifact_paths:
                issues.append(f"Claim {claim.get('id', index)} references artifact not listed in artifacts: {ref}")

    for index, artifact in enumerate(artifacts):
        if not isinstance(artifact, dict):
            issues.append(f"Artifact {index} is not an object")
            continue
        ref = artifact.get("path")
        if not ref:
            issues.append(f"Artifact {index} has no path")
            continue
        artifact_path = artifact_path_map[normalize_relative_path(ref).as_posix()]
        if not artifact_path.exists():
            issues.append(f"Missing artifact: {ref}")
            continue
        if artifact_path.is_symlink() or not artifact_path.is_file():
            issues.append(f"Artifact is not a regular file: {ref}")
            continue
        expected_hash = artifact.get("sha256")
        valid_hash = isinstance(expected_hash, str) and re.fullmatch(r"[0-9a-f]{64}", expected_hash)
        if strict and not valid_hash:
            issues.append(f"Strict check failed: artifact {ref} has no sha256")
        if expected_hash is not None and not valid_hash:
            issues.append(f"Invalid sha256 for {ref}")
        if valid_hash:
            actual_hash = sha256_file(artifact_path)
            if actual_hash != expected_hash:
                issues.append(f"Hash mismatch for {ref}: expected {expected_hash[:16]}..., got {actual_hash[:16]}...")
        if strict and looks_textual(artifact_path):
            scan_status, scan_findings = scan_text_file(artifact_path)
            if scan_status != "none_found":
                issues.append(
                    f"Strict check failed: artifact {ref} has detectable sensitive content: "
                    f"{scan_findings}"
                )

    if isinstance(runtime_identity, dict) and runtime_identity.get("required") is True:
        runtime_ref = runtime_identity.get("path", RUNTIME_IDENTITY_NAME)
        runtime_path = all_ref_map[normalize_relative_path(runtime_ref).as_posix()]
        if not runtime_path.exists():
            issues.append(f"runtime_identity.required=true but {RUNTIME_IDENTITY_NAME} is missing")
        if strict:
            canonical_runtime = normalize_relative_path(runtime_ref).as_posix()
            if runtime_identity.get("status") != "valid":
                issues.append("Strict check failed: required runtime identity status is not valid")
            if canonical_runtime not in artifact_paths:
                issues.append("Strict check failed: required runtime identity is not a listed artifact")
            referenced_artifacts.add(canonical_runtime)
            if runtime_path.exists() and runtime_path.is_file() and not runtime_path.is_symlink():
                try:
                    runtime_payload = load_json_file(runtime_path)
                except ContractError:
                    runtime_payload = {}
                runtime_schema = (
                    "runtime_identity_v2.schema.json"
                    if isinstance(runtime_payload, dict)
                    and runtime_payload.get("schema") == "projectstate.runtime_identity.v2"
                    else "runtime_identity.schema.json"
                )
                runtime_issues = validate_file(
                    runtime_path,
                    ROOT / "schemas" / runtime_schema,
                )
                issues.extend(
                    f"Strict runtime identity {issue.path}: {issue.message}"
                    for issue in runtime_issues
                )

    redaction = manifest.get("redaction", {})
    if not isinstance(redaction, dict):
        redaction = {}
    redaction_status = redaction.get("status")
    manifest_status = manifest.get("manifest_status")

    if strict:
        exact_contracts = [
            (manifest, "manifest", {"schema", "slice_id", "manifest_status", "created_at", "repo", "runtime_identity", "claims", "artifacts", "redaction"}),
            (manifest.get("repo"), "repo", {"branch", "head"}),
            (runtime_identity, "runtime_identity", {"required", "path", "status"}),
            (redaction, "redaction", {"status", "automated_scan", "manual_review", "known_limits"}),
        ]
        exact_contracts.extend(
            (claim, f"claims[{index}]", {"id", "claim", "status", "evidence"})
            for index, claim in enumerate(claims)
        )
        exact_contracts.extend(
            (
                artifact,
                f"artifacts[{index}]",
                {"path", "kind", "sha256", "redaction_status", "sensitive_data"},
            )
            for index, artifact in enumerate(artifacts)
        )
        for value, label, allowed in exact_contracts:
            if not isinstance(value, dict):
                continue
            unknown = set(value) - allowed
            if unknown:
                issues.append(
                    f"Strict check failed: {label} contains unknown fields: {sorted(unknown)}"
                )
        manifest_findings = scan_text(
            "\n".join(manifest_strings(manifest)),
            MANIFEST_NAME,
        )
        if manifest_findings:
            issues.extend(
                f"Strict check failed: {finding}" for finding in manifest_findings
            )
        disk_files: set[str] = set()
        for current_root, directory_names, file_names in os.walk(
            evidence_dir, topdown=True, followlinks=False
        ):
            current = Path(current_root)
            for name in [*directory_names, *file_names]:
                candidate = current / name
                relative = candidate.relative_to(evidence_dir).as_posix()
                if candidate.is_symlink():
                    issues.append(f"Strict check failed: evidence tree contains symlink: {relative}")
            directory_names[:] = [
                name for name in directory_names if not (current / name).is_symlink()
            ]
            for name in file_names:
                candidate = current / name
                relative = candidate.relative_to(evidence_dir).as_posix()
                if candidate.is_symlink() or not candidate.is_file():
                    issues.append(
                        f"Strict check failed: evidence tree contains non-regular file: {relative}"
                    )
                    continue
                disk_files.add(relative)
        unlisted = disk_files - artifact_paths - {MANIFEST_NAME}
        if unlisted:
            issues.append(
                "Strict check failed: unlisted evidence files: " + ", ".join(sorted(unlisted))
            )
        if manifest_status != "complete":
            issues.append(f"Strict check failed: manifest_status must be complete, got {manifest_status!r}")
        if not claims:
            issues.append("Strict check failed: claims is empty")
        if not artifacts:
            issues.append("Strict check failed: artifacts is empty")
        repo = manifest.get("repo")
        head = repo.get("head") if isinstance(repo, dict) else None
        branch = repo.get("branch") if isinstance(repo, dict) else None
        if not isinstance(head, str) or not re.fullmatch(r"[0-9a-f]{40}", head):
            issues.append("Strict check failed: repo.head must be a full 40-character commit SHA")
        if not isinstance(branch, str) or not branch:
            issues.append("Strict check failed: repo.branch must be a non-empty string")
        if not isinstance(runtime_identity, dict) or not isinstance(
            runtime_identity.get("required"), bool
        ):
            issues.append("Strict check failed: runtime_identity must explicitly declare required true/false")
        elif runtime_identity.get("required") is False and runtime_identity.get("status") != "not_applicable":
            issues.append(
                "Strict check failed: runtime_identity.required=false requires status=not_applicable"
            )
        if redaction_status not in {"checked", "checked_with_limits"}:
            issues.append(f"Strict check failed: redaction status is {redaction_status!r}")
        if redaction.get("manual_review") not in {"completed", "not_applicable"}:
            issues.append("Strict check failed: manual redaction review is not complete")
        if redaction.get("automated_scan") not in {"passed", "not_applicable"}:
            issues.append("Strict check failed: automated redaction scan has unresolved findings")
        automated_scan = redaction.get("automated_scan")
        manual_review = redaction.get("manual_review")
        if automated_scan != "passed" and manual_review != "completed":
            issues.append(
                "Strict check failed: redaction requires a passed automated scan or completed manual review"
            )
        known_limits = redaction.get("known_limits")
        if (
            redaction_status == "checked_with_limits"
            and (not isinstance(known_limits, list) or not known_limits)
        ):
            issues.append("Strict check failed: checked_with_limits requires non-empty known_limits")
        for artifact in artifacts:
            if not isinstance(artifact, dict):
                continue
            status = artifact.get("redaction_status")
            kind = artifact.get("kind")
            if status not in ("checked", "checked_with_limits"):
                issues.append(
                    f"Strict check failed: artifact {artifact.get('path')} has redaction_status={status}"
                )
            if artifact.get("sensitive_data") not in {"none_found", "redacted"}:
                issues.append(
                    f"Strict check failed: artifact {artifact.get('path')} has "
                    f"sensitive_data={artifact.get('sensitive_data')}"
                )
            ref = artifact.get("path")
            artifact_path = artifact_path_map.get(ref) if isinstance(ref, str) else None
            if kind in ("screenshot", "other") and artifact_path is not None and looks_binary(artifact_path):
                if manual_review != "completed":
                    issues.append(
                        f"Strict check failed: binary/image artifact {artifact.get('path')} "
                        "requires completed manual review"
                    )
            if status == "checked_with_limits" and (
                not isinstance(known_limits, list) or not known_limits
            ):
                issues.append(
                    f"Strict check failed: artifact {artifact.get('path')} is checked_with_limits "
                    "but the manifest records no known limits"
                )
        orphaned = artifact_paths - referenced_artifacts
        if orphaned:
            issues.append(
                "Strict check failed: unreferenced artifacts: " + ", ".join(sorted(orphaned))
            )

    if issues:
        print("Manifest check failed:")
        for issue in issues:
            print(f"  - {issue}")
        return 1

    print("Manifest check passed.")
    return 0


def command_hash(evidence_dir: Path) -> int:
    manifest = load_manifest(evidence_dir)
    artifacts = manifest.get("artifacts", [])
    if not isinstance(artifacts, list):
        raise SystemExit("'artifacts' must be an array")

    refs = [artifact.get("path") for artifact in artifacts if isinstance(artifact, dict) and artifact.get("path")]
    path_map, issues = preflight_evidence_paths(evidence_dir, refs, reject_duplicates=True)
    if issues:
        print("Manifest hash refused:")
        for issue in issues:
            print(f"  - {issue}")
        return 1

    updated = 0
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            continue
        ref = artifact.get("path")
        if not ref:
            continue
        if ref == MANIFEST_NAME:
            # The manifest cannot hash itself; leave sha256 null or externally supplied.
            continue
        artifact_path = path_map[normalize_relative_path(ref).as_posix()]
        if not artifact_path.exists() or artifact_path.is_symlink() or not artifact_path.is_file():
            print(f"Manifest hash refused: artifact is missing or not a regular file: {ref}")
            return 1
        artifact["sha256"] = sha256_file(artifact_path)
        updated += 1

    save_manifest(evidence_dir, manifest)
    print(f"Updated sha256 for {updated} artifact(s).")
    return 0


def command_scan(evidence_dir: Path) -> int:
    manifest = load_manifest(evidence_dir)
    artifacts = manifest.get("artifacts", [])
    if not isinstance(artifacts, list):
        artifacts = []

    refs = [artifact.get("path") for artifact in artifacts if isinstance(artifact, dict) and artifact.get("path")]
    path_map, issues = preflight_evidence_paths(evidence_dir, refs, reject_duplicates=True)
    if issues:
        print("Manifest scan refused:")
        for issue in issues:
            print(f"  - {issue}")
        return 1

    for ref, path in path_map.items():
        if not path.exists() or path.is_symlink() or not path.is_file():
            print(f"Manifest scan refused: artifact is missing or not a regular file: {ref}")
            return 1

    known_limits: list[str] = []
    automated_scan: str = "passed"

    for artifact in artifacts:
        if not isinstance(artifact, dict):
            continue
        ref = artifact.get("path")
        if not ref:
            continue
        artifact_path = path_map[normalize_relative_path(ref).as_posix()]
        if not artifact_path.exists():
            artifact["redaction_status"] = "unchecked"
            artifact["sensitive_data"] = "unknown"
            known_limits.append(f"Cannot scan missing artifact: {ref}")
            continue

        kind = artifact.get("kind") or artifact_kind(artifact_path)
        if looks_binary(artifact_path) or kind == "screenshot":
            artifact["redaction_status"] = "manual_required"
            artifact["sensitive_data"] = "unknown"
            known_limits.append(
                f"Binary/image artifact {ref} requires manual review; automated scan cannot inspect content."
            )
            continue

        if not looks_textual(artifact_path) and kind != "doc":
            artifact["redaction_status"] = "manual_required"
            artifact["sensitive_data"] = "unknown"
            known_limits.append(
                f"Artifact {ref} has unrecognized content type; automated scan skipped, manual review required."
            )
            continue

        status, findings = scan_text_file(artifact_path)
        artifact["sensitive_data"] = status
        if findings:
            automated_scan = "findings"
            artifact["redaction_status"] = "manual_required"
            known_limits.extend(findings)
        else:
            artifact["redaction_status"] = "checked_with_limits"
            known_limits.append(
                f"Automated scan found no obvious patterns in {ref}; this does not prove absence of secrets."
            )

    redaction: dict[str, Any] = manifest.get("redaction", {})
    if not isinstance(redaction, dict):
        redaction = {}
    redaction["automated_scan"] = automated_scan
    redaction["manual_review"] = "required"
    redaction["status"] = "manual_required" if automated_scan == "findings" else "checked_with_limits"
    if known_limits:
        redaction["known_limits"] = known_limits
    manifest["redaction"] = redaction

    save_manifest(evidence_dir, manifest)
    print(
        "Scan complete. Redaction status is "
        f"{redaction['status']!r}; manual review remains required."
    )
    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Manage ProjectState evidence pack manifests")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Create a manifest skeleton")
    init_parser.add_argument("evidence_dir", help="Evidence directory")
    init_parser.add_argument("--slice-id", help="Backlog slice ID")
    init_parser.add_argument("--force", action="store_true", help="Overwrite an existing manifest")
    init_parser.add_argument("--repo", type=Path, help="Explicit repository root owning this evidence pack")

    check_parser = subparsers.add_parser("check", help="Validate a manifest")
    check_parser.add_argument("evidence_dir", help="Evidence directory")
    check_parser.add_argument("--strict", action="store_true", help="Fail on unchecked redaction")

    hash_parser = subparsers.add_parser("hash", help="Compute sha256 for listed artifacts")
    hash_parser.add_argument("evidence_dir", help="Evidence directory")

    scan_parser = subparsers.add_parser("scan", help="Run conservative redaction scan")
    scan_parser.add_argument("evidence_dir", help="Evidence directory")

    return parser.parse_args(argv[1:])


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv)
    try:
        evidence_dir = safe_root_path(
            args.evidence_dir,
            must_exist=args.command != "init",
        )
    except UnsafePathError as exc:
        print(f"Evidence pack refused: {exc}")
        return 1

    try:
        if args.command == "init":
            return command_init(evidence_dir, args.slice_id, force=args.force, repo=args.repo)
        if args.command == "check":
            return command_check(evidence_dir, strict=args.strict)
        if args.command == "hash":
            return command_hash(evidence_dir)
        if args.command == "scan":
            return command_scan(evidence_dir)
    except (ContractError, UnsafePathError, OSError, UnicodeDecodeError) as exc:
        print(f"Evidence pack refused: {exc}")
        return 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
