#!/usr/bin/env python3
"""Manage StateDD evidence pack manifests and a conservative redaction gate.

This script stays stdlib-only. It creates, validates, hashes, and scans
artifact manifests under a single evidence folder. It never claims that an
absence of flagged secrets proves that no secrets exist.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from statedd_git_safety_session import MutationBlocked, require_mutation_permit, sanitized_git_environment


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "statedd.evidence_manifest.v1"
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
    command = ["git", "--no-optional-locks", *args[1:]] if args and args[0] == "git" else args
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            env=sanitized_git_environment(),
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
    path = evidence_dir / MANIFEST_NAME
    if not path.exists():
        raise SystemExit(f"Manifest not found: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Malformed manifest JSON: {exc}")
    if not isinstance(data, dict):
        raise SystemExit("Manifest top-level value must be an object")
    return data


def save_manifest(evidence_dir: Path, data: dict[str, Any]) -> Path:
    path = evidence_dir / MANIFEST_NAME
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


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


def repo_block(repo: Path) -> dict[str, Any]:
    return {
        "branch": git_value(repo, ["rev-parse", "--abbrev-ref", "HEAD"]),
        "head": git_value(repo, ["rev-parse", "HEAD"]),
    }


def command_init(evidence_dir: Path, slice_id: str | None = None, *, force: bool = False) -> int:
    evidence_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = evidence_dir / MANIFEST_NAME
    if manifest_path.exists() and not force:
        print(f"Manifest already exists: {manifest_path}")
        print("Use --force to overwrite.")
        return 1

    runtime_path = evidence_dir / RUNTIME_IDENTITY_NAME
    runtime_identity: dict[str, Any] = {
        "required": runtime_path.exists(),
        "path": RUNTIME_IDENTITY_NAME,
        "status": "valid" if runtime_path.exists() else "not_applicable",
    }

    manifest: dict[str, Any] = {
        "schema": SCHEMA,
        "slice_id": slice_id or "BL-000",
        "manifest_status": "complete",
        "created_at": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "repo": repo_block(ROOT),
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

    artifact_paths = {a.get("path") for a in artifacts if isinstance(a, dict)}

    for index, claim in enumerate(claims):
        if not isinstance(claim, dict):
            issues.append(f"Claim {index} is not an object")
            continue
        evidence = claim.get("evidence", [])
        if not isinstance(evidence, list) or not evidence:
            issues.append(f"Claim {claim.get('id', index)} has no evidence artifacts")
            continue
        for ref in evidence:
            artifact_path = evidence_dir / ref
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
        artifact_path = evidence_dir / ref
        if not artifact_path.exists():
            issues.append(f"Missing artifact: {ref}")
            continue
        expected_hash = artifact.get("sha256")
        if expected_hash:
            actual_hash = sha256_file(artifact_path)
            if actual_hash != expected_hash:
                issues.append(f"Hash mismatch for {ref}: expected {expected_hash[:16]}..., got {actual_hash[:16]}...")

    runtime_identity = manifest.get("runtime_identity")
    if isinstance(runtime_identity, dict) and runtime_identity.get("required") is True:
        runtime_path = evidence_dir / RUNTIME_IDENTITY_NAME
        if not runtime_path.exists():
            issues.append(f"runtime_identity.required=true but {RUNTIME_IDENTITY_NAME} is missing")

    redaction = manifest.get("redaction", {})
    if not isinstance(redaction, dict):
        redaction = {}
    redaction_status = redaction.get("status")
    manifest_status = manifest.get("manifest_status", "complete")

    if strict:
        if manifest_status not in {"skeleton", "legacy"}:
            if not claims:
                issues.append("Strict check failed: claims is empty (use manifest_status=skeleton/legacy if intentional)")
            if not artifacts:
                issues.append("Strict check failed: artifacts is empty (use manifest_status=skeleton/legacy if intentional)")
        if redaction_status == "unchecked":
            issues.append("Strict check failed: redaction status is unchecked")
        if redaction.get("manual_review") == "required" and not redaction.get("known_limits"):
            issues.append("Strict check failed: manual_review is required but known_limits is empty")
        for artifact in artifacts:
            if not isinstance(artifact, dict):
                continue
            status = artifact.get("redaction_status")
            kind = artifact.get("kind")
            if status in ("unchecked", "manual_required"):
                issues.append(
                    f"Strict check failed: artifact {artifact.get('path')} has redaction_status={status}"
                )
            if kind in ("screenshot", "other") and looks_binary(evidence_dir / artifact.get("path", "")):
                if status not in ("checked", "checked_with_limits"):
                    issues.append(
                        f"Strict check failed: binary/image artifact {artifact.get('path')} "
                        "requires manual review or explicit checked_with_limits"
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
        artifact_path = evidence_dir / ref
        if not artifact_path.exists():
            print(f"Skipping missing artifact: {ref}")
            continue
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

    known_limits: list[str] = []
    automated_scan: str = "passed"

    for artifact in artifacts:
        if not isinstance(artifact, dict):
            continue
        ref = artifact.get("path")
        if not ref:
            continue
        artifact_path = evidence_dir / ref
        if not artifact_path.exists():
            artifact["redaction_status"] = "unchecked"
            artifact["sensitive_data"] = "unknown"
            known_limits.append(f"Cannot scan missing artifact: {ref}")
            continue

        kind = artifact.get("kind") or artifact_kind(artifact_path)
        if kind == "runtime_identity":
            artifact["redaction_status"] = "checked"
            artifact["sensitive_data"] = "none_found"
            continue

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
            artifact["redaction_status"] = "checked_with_limits"
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
    redaction["status"] = "checked_with_limits"
    if known_limits:
        existing = redaction.get("known_limits", [])
        if not isinstance(existing, list):
            existing = []
        redaction["known_limits"] = existing + known_limits
    manifest["redaction"] = redaction

    save_manifest(evidence_dir, manifest)
    print("Scan complete. Redaction status is 'checked_with_limits' with explicit limits.")
    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Manage StateDD evidence pack manifests")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Create a manifest skeleton")
    init_parser.add_argument("evidence_dir", help="Evidence directory")
    init_parser.add_argument("--slice-id", help="Backlog slice ID")
    init_parser.add_argument("--force", action="store_true", help="Overwrite an existing manifest")

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
    evidence_dir = Path(args.evidence_dir).resolve()

    if args.command in {"init", "hash", "scan"}:
        try:
            require_mutation_permit(
                evidence_dir,
                f"StateDD evidence-pack {args.command}",
                allow_non_git=True,
            )
        except MutationBlocked as exc:
            print(str(exc), file=sys.stderr)
            return 1

    if args.command == "init":
        return command_init(evidence_dir, args.slice_id, force=args.force)
    if args.command == "check":
        return command_check(evidence_dir, strict=args.strict)
    if args.command == "hash":
        return command_hash(evidence_dir)
    if args.command == "scan":
        return command_scan(evidence_dir)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
