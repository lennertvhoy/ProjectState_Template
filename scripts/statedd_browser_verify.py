#!/usr/bin/env python3
"""Validate and record provider-agnostic browser verification evidence.

This script stays stdlib-only. It does not drive browsers itself; it validates
and records durable browser proof that can be produced by Kimi WebBridge,
Playwright, agent-native browser tools, existing E2E tests, manual screenshots,
or custom tooling.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from statedd_git_safety_session import MutationBlocked, require_mutation_permit


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "browser_verification.schema.json"
ARTIFACT_NAME = "browser_verification.json"
RUNTIME_IDENTITY_NAME = "runtime_identity.json"

# Import the small JSON Schema subset from the StateSpec validator instead of
# duplicating it. Keep the script runnable on its own by handling an absent
# validator gracefully in development.
try:
    _VALIDATOR_DIR = str(ROOT / "scripts")
    if _VALIDATOR_DIR not in sys.path:
        sys.path.insert(0, _VALIDATOR_DIR)
    from statedd_validate_schema import load_schema, validate_json_schema
except Exception:  # pragma: no cover - validator is required in production
    load_schema = None  # type: ignore[assignment]
    validate_json_schema = None  # type: ignore[assignment]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_artifact_path(evidence_dir: Path, ref: str) -> Path:
    """Resolve an artifact path and ensure it stays inside the evidence directory."""
    if not ref or ref.startswith(("/", "\\")) or ".." in Path(ref).parts:
        raise SystemExit(f"Invalid artifact path: {ref}")
    candidate = (evidence_dir / ref).resolve()
    evidence_dir_resolved = evidence_dir.resolve()
    if evidence_dir_resolved not in candidate.parents and candidate != evidence_dir_resolved:
        raise SystemExit(f"Artifact path escapes evidence directory: {ref}")
    return candidate


def load_browser_verification(evidence_dir: Path) -> dict[str, Any]:
    path = evidence_dir / ARTIFACT_NAME
    if not path.exists():
        raise SystemExit(f"Browser verification artifact not found: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Malformed {ARTIFACT_NAME}: {exc}")
    if not isinstance(data, dict):
        raise SystemExit(f"{ARTIFACT_NAME} top-level value must be an object")
    return data


def save_browser_verification(evidence_dir: Path, data: dict[str, Any]) -> Path:
    path = evidence_dir / ARTIFACT_NAME
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def validate_against_schema(data: dict[str, Any]) -> list[str]:
    if validate_json_schema is None or load_schema is None:
        return ["Browser verification schema validator is not available"]
    try:
        schema = load_schema(SCHEMA_PATH)
    except Exception as exc:
        return [f"Could not load schema {SCHEMA_PATH}: {exc}"]
    issues = validate_json_schema(data, schema)
    return [f"{issue.path}: {issue.message}" for issue in issues]


def command_init(
    evidence_dir: Path,
    slice_id: str | None = None,
    *,
    not_applicable: bool = False,
) -> int:
    evidence_dir.mkdir(parents=True, exist_ok=True)
    path = evidence_dir / ARTIFACT_NAME
    if path.exists():
        print(f"Browser verification artifact already exists: {path}")
        print("Use `check` to validate it or `hash` to refresh artifact hashes.")
        return 1

    runtime_path = evidence_dir / RUNTIME_IDENTITY_NAME
    runtime_identity_required = runtime_path.exists()

    if not_applicable:
        provider: dict[str, Any] = {
            "kind": "not_applicable",
            "required": False,
            "available": False,
            "selection_reason": "Browser verification is not applicable for this docs/scripts-only slice.",
            "fallbacks_considered": [],
        }
        limits = ["Browser verification is not applicable for this docs/scripts-only slice."]
    else:
        provider = {
            "kind": "manual_browser",
            "required": False,
            "available": False,
            "selection_reason": "No browser automation provider selected yet; update provider before closure.",
            "fallbacks_considered": [
                "kimi_webbridge",
                "playwright",
                "agent_native_browser",
                "existing_e2e",
                "manual_browser",
            ],
        }
        limits = ["Browser verification provider not yet confirmed."]

    artifact: dict[str, Any] = {
        "schema": "statedd.browser_verification.v1",
        "captured_at": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "slice_id": slice_id,
        "provider": provider,
        "runtime_identity": {
            "path": RUNTIME_IDENTITY_NAME,
            "head_matches": None,
            "endpoint_matches": None,
        },
        "checks": [],
        "artifacts": [],
        "limits": limits,
    }

    if not runtime_identity_required:
        artifact["runtime_identity"]["status"] = "not_present"
        limits.append(f"{RUNTIME_IDENTITY_NAME} was not found in the evidence folder.")

    save_browser_verification(evidence_dir, artifact)
    print(f"Created browser verification artifact: {path}")
    return 0


def command_check(evidence_dir: Path, *, strict: bool = False) -> int:
    data = load_browser_verification(evidence_dir)
    issues: list[str] = []

    schema_issues = validate_against_schema(data)
    if schema_issues:
        issues.extend(schema_issues)

    provider = data.get("provider") if isinstance(data, dict) else {}
    if not isinstance(provider, dict):
        provider = {}
    provider_kind = provider.get("kind")
    not_applicable = provider_kind == "not_applicable"

    runtime_identity = data.get("runtime_identity") if isinstance(data, dict) else {}
    if not isinstance(runtime_identity, dict):
        runtime_identity = {}
    runtime_identity_path = runtime_identity.get("path", RUNTIME_IDENTITY_NAME)
    runtime_artifact = evidence_dir / runtime_identity_path

    if runtime_artifact.exists() and not runtime_identity_path:
        issues.append("runtime_identity.path is empty")

    artifacts = data.get("artifacts") if isinstance(data, dict) else []
    if not isinstance(artifacts, list):
        issues.append("'artifacts' must be an array")
        artifacts = []

    artifact_paths = {a.get("path") for a in artifacts if isinstance(a, dict)}

    for index, artifact in enumerate(artifacts):
        if not isinstance(artifact, dict):
            issues.append(f"Artifact {index} is not an object")
            continue
        ref = artifact.get("path")
        if not ref:
            issues.append(f"Artifact {index} has no path")
            continue
        artifact_path = safe_artifact_path(evidence_dir, ref)
        if not artifact_path.exists():
            issues.append(f"Missing artifact: {ref}")
            continue
        expected_hash = artifact.get("sha256")
        if expected_hash:
            actual_hash = sha256_file(artifact_path)
            if actual_hash != expected_hash:
                issues.append(
                    f"Hash mismatch for {ref}: expected {expected_hash[:16]}..., got {actual_hash[:16]}..."
                )

    checks = data.get("checks") if isinstance(data, dict) else []
    if not isinstance(checks, list):
        issues.append("'checks' must be an array")
        checks = []

    runtime_required = bool(checks) or provider.get("required") is True or strict
    if not not_applicable and runtime_required and not runtime_artifact.exists():
        issues.append(
            f"Browser verification requires {runtime_identity_path} but it is missing"
        )

    if strict and not not_applicable and not checks:
        issues.append("Strict check failed: no browser checks recorded")

    for index, check in enumerate(checks):
        if not isinstance(check, dict):
            issues.append(f"Check {index} is not an object")
            continue
        check_id = check.get("id", index)
        evidence = check.get("evidence", [])
        if not isinstance(evidence, list) or not evidence:
            issues.append(f"Check {check_id} has no evidence artifacts")
            continue
        for ref in evidence:
            artifact_path = safe_artifact_path(evidence_dir, ref)
            if not artifact_path.exists():
                issues.append(f"Check {check_id} references missing artifact: {ref}")
            if ref not in artifact_paths:
                issues.append(
                    f"Check {check_id} references artifact not listed in artifacts: {ref}"
                )

    limits = data.get("limits") if isinstance(data, dict) else []
    if not isinstance(limits, list):
        issues.append("'limits' must be an array")
        limits = []

    if strict and provider_kind in ("manual_browser", "custom") and not limits:
        issues.append(
            f"Strict check failed: provider.kind={provider_kind} requires explicit known limits"
        )

    if strict and provider_kind == "custom":
        if not provider.get("tool"):
            issues.append("Strict check failed: custom provider requires 'tool' name")
        if not provider.get("command"):
            issues.append("Strict check failed: custom provider requires 'command'")

    if issues:
        print("Browser verification check failed:")
        for issue in issues:
            print(f"  - {issue}")
        return 1

    print("Browser verification check passed.")
    return 0


def command_hash(evidence_dir: Path) -> int:
    data = load_browser_verification(evidence_dir)
    artifacts = data.get("artifacts") if isinstance(data, dict) else []
    if not isinstance(artifacts, list):
        raise SystemExit("'artifacts' must be an array")

    updated = 0
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            continue
        ref = artifact.get("path")
        if not ref:
            continue
        if ref == ARTIFACT_NAME:
            continue
        artifact_path = safe_artifact_path(evidence_dir, ref)
        if not artifact_path.exists():
            print(f"Skipping missing artifact: {ref}")
            continue
        artifact["sha256"] = sha256_file(artifact_path)
        updated += 1

    save_browser_verification(evidence_dir, data)
    print(f"Updated sha256 for {updated} browser artifact(s).")
    return 0


def command_summarize(evidence_dir: Path) -> int:
    data = load_browser_verification(evidence_dir)
    provider = data.get("provider") if isinstance(data, dict) else {}
    if not isinstance(provider, dict):
        provider = {}
    checks = data.get("checks") if isinstance(data, dict) else []
    if not isinstance(checks, list):
        checks = []
    artifacts = data.get("artifacts") if isinstance(data, dict) else []
    if not isinstance(artifacts, list):
        artifacts = []
    limits = data.get("limits") if isinstance(data, dict) else []
    if not isinstance(limits, list):
        limits = []

    print("Browser verification summary")
    print(f"  Provider kind: {provider.get('kind', 'unknown')}")
    print(f"  Required: {provider.get('required', 'unknown')}")
    print(f"  Available: {provider.get('available', 'unknown')}")
    print(f"  Selection reason: {provider.get('selection_reason', 'unknown')}")
    fallbacks = provider.get("fallbacks_considered", [])
    print(f"  Fallbacks considered: {', '.join(fallbacks) if fallbacks else 'none'}")
    print(f"  Checks: {len(checks)}")
    for check in checks:
        if isinstance(check, dict):
            print(f"    - {check.get('id', '?')}: {check.get('claim', '?')} ({check.get('status', '?')})")
    print(f"  Artifacts: {len(artifacts)}")
    for artifact in artifacts:
        if isinstance(artifact, dict):
            print(f"    - {artifact.get('path', '?')} ({artifact.get('kind', '?')})")
    print(f"  Known limits: {len(limits)}")
    for limit in limits:
        print(f"    - {limit}")
    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate and record provider-agnostic browser verification evidence"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Create a browser_verification.json skeleton")
    init_parser.add_argument("evidence_dir", help="Evidence directory")
    init_parser.add_argument("--slice-id", help="Backlog slice ID")
    init_parser.add_argument(
        "--not-applicable",
        action="store_true",
        help="Mark browser verification as not applicable for docs/scripts-only slices",
    )

    check_parser = subparsers.add_parser("check", help="Validate browser_verification.json")
    check_parser.add_argument("evidence_dir", help="Evidence directory")
    check_parser.add_argument("--strict", action="store_true", help="Fail on weak or manual proof without limits")

    hash_parser = subparsers.add_parser("hash", help="Compute sha256 for listed browser artifacts")
    hash_parser.add_argument("evidence_dir", help="Evidence directory")

    summarize_parser = subparsers.add_parser("summarize", help="Print browser verification summary")
    summarize_parser.add_argument("evidence_dir", help="Evidence directory")

    return parser.parse_args(argv[1:])


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv)
    evidence_dir = Path(args.evidence_dir).resolve()

    if args.command in {"init", "hash"}:
        try:
            require_mutation_permit(
                evidence_dir,
                f"StateSpec browser-verification {args.command}",
                allow_non_git=True,
            )
        except MutationBlocked as exc:
            print(str(exc), file=sys.stderr)
            return 1

    if args.command == "init":
        return command_init(evidence_dir, args.slice_id, not_applicable=args.not_applicable)
    if args.command == "check":
        return command_check(evidence_dir, strict=args.strict)
    if args.command == "hash":
        return command_hash(evidence_dir)
    if args.command == "summarize":
        return command_summarize(evidence_dir)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
