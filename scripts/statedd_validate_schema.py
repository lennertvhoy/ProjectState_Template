#!/usr/bin/env python3
"""Validate StateDD state, evidence, runtime, and handoff contracts.

The validator intentionally stays stdlib-only. It implements the small JSON
Schema subset used by this template and a tiny YAML parser for the StateDD YAML
style emitted by `scripts/init_template.py`.
"""

from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import re
import sys
import urllib.parse
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_ROOT = ROOT / "schemas"
EVIDENCE_MANIFEST_SCHEMA = "statedd.evidence_manifest.v1"
RUNTIME_IDENTITY_SCHEMA = "statedd.runtime_identity.v1"
PRIVACY_PROFILES = {"public", "private", "local_only"}
CHANGE_TYPES = {"ui", "api", "config", "docs", "refactor", "infra"}
EVIDENCE_TYPES = {
    "browser_screenshot",
    "runtime_proof",
    "request_response_log",
    "schema_validation",
    "diff",
    "validation_output",
    "rendered_preview",
    "test_coverage",
    "benchmark",
}


@dataclass
class ValidationIssue:
    path: str
    message: str


@dataclass(frozen=True)
class EvidenceBundle:
    """A schema-validated evidence manifest and its bound runtime artifact."""

    directory: Path
    manifest_path: Path
    manifest: dict[str, Any]
    runtime_identity_path: Path
    runtime_identity: dict[str, Any]


class StateDDYamlError(ValueError):
    pass


class ArtifactContractError(ValueError):
    """Raised when current-slice evidence violates the shared artifact contract."""

    pass


def strip_inline_comment(value: str) -> str:
    in_quote: str | None = None
    escaped = False
    for index, char in enumerate(value):
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char in {"'", '"'}:
            if in_quote == char:
                in_quote = None
            elif in_quote is None:
                in_quote = char
            continue
        if char == "#" and in_quote is None and (index == 0 or value[index - 1].isspace()):
            return value[:index].rstrip()
    return value.rstrip()


def scalar(value: str) -> Any:
    value = strip_inline_comment(value.strip())
    if value == "":
        return ""
    if value in {"[]", "[ ]"}:
        return []
    if value in {"{}", "{ }"}:
        return {}
    if value.lower() == "null":
        return None
    if value.lower() == "true":
        return True
    if value.lower() == "false":
        return False
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return value[1:-1]
    if re.fullmatch(r"-?\d+", value):
        try:
            return int(value)
        except ValueError:
            pass
    return value


def preprocess_yaml(text: str) -> list[tuple[int, str, int]]:
    lines: list[tuple[int, str, int]] = []
    for lineno, raw in enumerate(text.splitlines(), start=1):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        if "\t" in raw[:indent]:
            raise StateDDYamlError(f"line {lineno}: tabs are not supported in indentation")
        lines.append((indent, raw[indent:].rstrip(), lineno))
    return lines


def parse_yaml_text(text: str) -> Any:
    lines = preprocess_yaml(text)
    if not lines:
        return {}
    value, index = parse_block(lines, 0, lines[0][0])
    if index != len(lines):
        _, content, lineno = lines[index]
        raise StateDDYamlError(f"line {lineno}: unexpected content after YAML block: {content}")
    return value


def parse_block(lines: list[tuple[int, str, int]], index: int, indent: int) -> tuple[Any, int]:
    if index >= len(lines):
        return {}, index
    current_indent, content, _ = lines[index]
    if current_indent < indent:
        return {}, index
    if content.startswith("- "):
        return parse_sequence(lines, index, current_indent)
    return parse_mapping(lines, index, current_indent)


def parse_sequence(lines: list[tuple[int, str, int]], index: int, indent: int) -> tuple[list[Any], int]:
    items: list[Any] = []
    while index < len(lines):
        current_indent, content, lineno = lines[index]
        if current_indent < indent:
            break
        if current_indent != indent or not content.startswith("- "):
            break
        item_text = content[2:].strip()
        index += 1
        if item_text == "":
            if index < len(lines) and lines[index][0] > indent:
                item, index = parse_block(lines, index, lines[index][0])
            else:
                item = None
            items.append(item)
            continue
        if re.match(r"^[A-Za-z0-9_.-]+:\s*", item_text):
            key, value_text = split_key_value(item_text, lineno)
            item_map: dict[str, Any] = {}
            if value_text in {"|", ">"}:
                value, index = parse_block_scalar(lines, index, indent + 2)
            elif value_text == "":
                if index < len(lines) and lines[index][0] > indent:
                    value, index = parse_block(lines, index, lines[index][0])
                else:
                    value = {}
            else:
                value = scalar(value_text)
            set_mapping_value(item_map, key, value, lineno)
            if index < len(lines) and lines[index][0] > indent:
                extra, index = parse_mapping(lines, index, lines[index][0])
                for extra_key, extra_value in extra.items():
                    set_mapping_value(item_map, extra_key, extra_value, lines[index - 1][2])
            items.append(item_map)
        else:
            items.append(scalar(item_text))
    return items, index


def split_key_value(content: str, lineno: int) -> tuple[str, str]:
    if ":" not in content:
        raise StateDDYamlError(f"line {lineno}: expected key: value")
    key, value = content.split(":", 1)
    key = key.strip()
    if not key:
        raise StateDDYamlError(f"line {lineno}: empty mapping key")
    return key, value.strip()


def set_mapping_value(mapping: dict[str, Any], key: str, value: Any, lineno: int) -> None:
    """Reject duplicate YAML keys instead of silently overwriting prior data."""
    if key in mapping:
        raise StateDDYamlError(f"line {lineno}: duplicate mapping key {key!r}")
    mapping[key] = value


def parse_mapping(lines: list[tuple[int, str, int]], index: int, indent: int) -> tuple[dict[str, Any], int]:
    mapping: dict[str, Any] = {}
    while index < len(lines):
        current_indent, content, lineno = lines[index]
        if current_indent < indent:
            break
        if current_indent != indent or content.startswith("- "):
            break
        key, value_text = split_key_value(content, lineno)
        index += 1
        if value_text in {"|", ">"}:
            value, index = parse_block_scalar(lines, index, indent + 2)
        elif value_text == "":
            if index < len(lines) and lines[index][0] > indent:
                value, index = parse_block(lines, index, lines[index][0])
            else:
                value = {}
        else:
            value = scalar(value_text)
        set_mapping_value(mapping, key, value, lineno)
    return mapping, index


def parse_block_scalar(lines: list[tuple[int, str, int]], index: int, min_indent: int) -> tuple[str, int]:
    parts: list[str] = []
    block_indent: int | None = None
    while index < len(lines):
        indent, content, _ = lines[index]
        if indent < min_indent:
            break
        if block_indent is None:
            block_indent = indent
        if indent < block_indent:
            break
        parts.append(" " * max(indent - block_indent, 0) + content)
        index += 1
    return "\n".join(parts), index


def load_data(path: Path) -> Any:
    if path.suffix.lower() == ".json":
        return json.loads(path.read_text(encoding="utf-8"))
    if path.suffix.lower() in {".yaml", ".yml"}:
        return parse_yaml_text(path.read_text(encoding="utf-8"))
    return path.read_text(encoding="utf-8")


def type_matches(value: Any, expected: str) -> bool:
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "null":
        return value is None
    return False


def resolve_local_ref(root_schema: dict[str, Any], ref: str) -> dict[str, Any]:
    """Resolve the local JSON Schema references used by StateDD schemas."""
    if not ref.startswith("#/"):
        raise ValueError(f"unsupported schema reference {ref!r}; only local references are supported")
    current: Any = root_schema
    for raw_part in ref[2:].split("/"):
        part = raw_part.replace("~1", "/").replace("~0", "~")
        if not isinstance(current, dict) or part not in current:
            raise ValueError(f"schema reference {ref!r} does not exist")
        current = current[part]
    if not isinstance(current, dict):
        raise ValueError(f"schema reference {ref!r} does not resolve to an object")
    return current


def validate_json_schema(
    value: Any,
    schema: dict[str, Any],
    path: str = "$",
    root_schema: dict[str, Any] | None = None,
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    root_schema = root_schema or schema

    ref = schema.get("$ref")
    if isinstance(ref, str):
        try:
            resolved = resolve_local_ref(root_schema, ref)
        except ValueError as exc:
            return [ValidationIssue(path, str(exc))]
        siblings = {key: nested for key, nested in schema.items() if key != "$ref"}
        schema = {**resolved, **siblings}

    expected_type = schema.get("type")
    if isinstance(expected_type, list):
        if not any(type_matches(value, item) for item in expected_type):
            issues.append(ValidationIssue(path, f"expected one of types {expected_type}, got {type(value).__name__}"))
            return issues
    elif isinstance(expected_type, str) and not type_matches(value, expected_type):
        issues.append(ValidationIssue(path, f"expected type {expected_type}, got {type(value).__name__}"))
        return issues

    if "const" in schema and value != schema["const"]:
        issues.append(ValidationIssue(path, f"expected constant {schema['const']!r}, got {value!r}"))
    if "enum" in schema and value not in schema["enum"]:
        issues.append(ValidationIssue(path, f"expected one of {schema['enum']}, got {value!r}"))

    if isinstance(value, str):
        min_length = schema.get("minLength")
        if isinstance(min_length, int) and len(value) < min_length:
            issues.append(ValidationIssue(path, f"expected string length >= {min_length}"))
        pattern = schema.get("pattern")
        if isinstance(pattern, str) and not re.search(pattern, value):
            issues.append(ValidationIssue(path, f"string does not match pattern {pattern!r}"))

    if isinstance(value, list):
        min_items = schema.get("minItems")
        if isinstance(min_items, int) and len(value) < min_items:
            issues.append(ValidationIssue(path, f"expected at least {min_items} item(s)"))
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, item in enumerate(value):
                issues.extend(validate_json_schema(item, item_schema, f"{path}[{index}]", root_schema))

    if isinstance(value, dict):
        required = schema.get("required", [])
        if isinstance(required, list):
            for key in required:
                if key not in value:
                    issues.append(ValidationIssue(path, f"missing required property {key!r}"))
        properties = schema.get("properties", {})
        if isinstance(properties, dict):
            for key, property_schema in properties.items():
                if key in value and isinstance(property_schema, dict):
                    issues.extend(validate_json_schema(value[key], property_schema, f"{path}.{key}", root_schema))
        additional = schema.get("additionalProperties", True)
        if additional is False and isinstance(properties, dict):
            allowed = set(properties)
            for key in value:
                if key not in allowed:
                    issues.append(ValidationIssue(f"{path}.{key}", "additional property is not allowed"))
        elif isinstance(additional, dict):
            for key, nested in value.items():
                if isinstance(properties, dict) and key in properties:
                    continue
                issues.extend(validate_json_schema(nested, additional, f"{path}.{key}", root_schema))

    semantics = schema.get("statedd_semantics")
    if isinstance(semantics, dict):
        issues.extend(validate_statedd_semantics(value, semantics, path))

    return issues


SENSITIVE_MACHINE_KEYS = {
    "hostname",
    "host_name",
    "kernel",
    "os_version",
    "pid",
    "pids",
    "all_candidate_pids",
    "command",
    "command_line",
    "cmdline",
    "cwd",
    "status_porcelain",
}
ABSOLUTE_HOME_RE = re.compile(r"(?:^|[\s\"'])(?:/home/[^/\s]+|/Users/[^/\s]+|[A-Za-z]:\\Users\\[^\\\s]+)")
URL_RE = re.compile(r"https?://[^\s\"'<>]+", re.IGNORECASE)


def is_private_url(value: str) -> bool:
    """Return whether a URL exposes a local/private endpoint or credentials."""
    try:
        parsed = urllib.parse.urlsplit(value)
    except ValueError:
        return True
    if parsed.scheme not in {"http", "https"}:
        return False
    if parsed.username or parsed.password:
        return True
    hostname = (parsed.hostname or "").lower().rstrip(".")
    if not hostname:
        return True
    if hostname in {"localhost", "localhost.localdomain"}:
        return True
    if hostname.endswith((".local", ".internal", ".lan", ".home", ".test")):
        return True
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        return "." not in hostname
    return not address.is_global


def public_runtime_identity_issues(value: Any, path: str = "$") -> list[ValidationIssue]:
    """Reject host-specific values from artifacts declared safe for public tracking."""
    issues: list[ValidationIssue] = []
    if isinstance(value, dict):
        for key, nested in value.items():
            nested_path = f"{path}.{key}"
            normalized_key = key.lower().replace("-", "_")
            if normalized_key in SENSITIVE_MACHINE_KEYS:
                issues.append(
                    ValidationIssue(
                        nested_path,
                        f"public runtime identity must omit or normalize machine field {key!r}",
                    )
                )
            if nested_path == "$.repo.path" and nested not in {"$REPO_ROOT", "<repo-root>", "."}:
                issues.append(
                    ValidationIssue(
                        nested_path,
                        "public runtime identity repo.path must use $REPO_ROOT, <repo-root>, or .",
                    )
                )
            issues.extend(public_runtime_identity_issues(nested, nested_path))
        return issues

    if isinstance(value, list):
        for index, nested in enumerate(value):
            issues.extend(public_runtime_identity_issues(nested, f"{path}[{index}]"))
        return issues

    if isinstance(value, str):
        if ABSOLUTE_HOME_RE.search(value):
            issues.append(
                ValidationIssue(path, "public runtime identity contains an absolute user home path")
            )
        for url in URL_RE.findall(value):
            if is_private_url(url):
                issues.append(
                    ValidationIssue(path, "public runtime identity contains a private or local URL")
                )
    return issues


def validate_statedd_semantics(value: Any, semantics: dict[str, Any], path: str) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    if semantics.get("runtime_required_requires_endpoint_reachable") is True and isinstance(value, dict):
        runtime = value.get("runtime")
        checks = value.get("checks")
        if isinstance(runtime, dict) and runtime.get("required") is True:
            reachable = checks.get("endpoint_reachable") if isinstance(checks, dict) else None
            if reachable is not True:
                issues.append(
                    ValidationIssue(
                        f"{path}.checks.endpoint_reachable",
                        "runtime.required is true, so checks.endpoint_reachable must be true",
                    )
                )
    if semantics.get("repo_role_mode_compatibility") is True and isinstance(value, dict):
        workflow = value.get("workflow")
        if isinstance(workflow, dict):
            role = workflow.get("repo_role")
            mode = workflow.get("statedd_mode") or workflow.get("repo_mode")
            if role == "template_repository" and mode != "template-maintenance":
                issues.append(
                    ValidationIssue(
                        f"{path}.workflow.statedd_mode",
                        "template_repository must use statedd_mode: template-maintenance",
                    )
                )
            if role == "downstream_project" and mode == "template-maintenance":
                issues.append(
                    ValidationIssue(
                        f"{path}.workflow.statedd_mode",
                        "downstream_project cannot use statedd_mode: template-maintenance",
                    )
                )
    if semantics.get("statedd_mode_matches_repo_mode") is True and isinstance(value, dict):
        workflow = value.get("workflow")
        if isinstance(workflow, dict) and workflow.get("statedd_mode") != workflow.get("repo_mode"):
            issues.append(
                ValidationIssue(
                    f"{path}.workflow.repo_mode",
                    "repo_mode must match statedd_mode",
                )
            )
    if semantics.get("public_runtime_identity") is True and isinstance(value, dict):
        privacy = value.get("privacy")
        if isinstance(privacy, dict) and privacy.get("profile") == "public":
            issues.extend(public_runtime_identity_issues(value, path))
    return issues


def validate_markdown_contract(text: str, contract: dict[str, Any]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for heading in contract.get("required_headings", []):
        if heading not in text:
            issues.append(ValidationIssue("$", f"missing required heading {heading!r}"))
    for marker in contract.get("required_markers", []):
        if marker not in text:
            issues.append(ValidationIssue("$", f"missing required marker {marker!r}"))
    return issues


def load_schema(schema_path: Path) -> dict[str, Any]:
    return json.loads(schema_path.read_text(encoding="utf-8"))


def validate_file(path: Path, schema_path: Path) -> list[ValidationIssue]:
    schema = load_schema(schema_path)
    if schema.get("contract_type") == "markdown_contract":
        return validate_markdown_contract(path.read_text(encoding="utf-8"), schema)
    data = load_data(path)
    return validate_json_schema(data, schema, root_schema=schema)


def schema_path(root: Path, relpath: str) -> Path:
    local = root / "schemas" / relpath
    if local.exists():
        return local
    return SCHEMA_ROOT / relpath


def format_validation_issues(label: str, issues: list[ValidationIssue]) -> str:
    details = "; ".join(f"{issue.path}: {issue.message}" for issue in issues)
    return f"{label} violates its schema: {details}"


def read_json_object(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ArtifactContractError(f"{label} not found: {path}") from exc
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ArtifactContractError(f"could not read {label} {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ArtifactContractError(f"{label} must be a JSON object: {path}")
    return value


def safe_bundle_artifact(evidence_dir: Path, reference: str) -> Path:
    relative = Path(reference)
    if relative.is_absolute():
        raise ArtifactContractError(f"artifact path must be relative to its evidence bundle: {reference}")
    target = (evidence_dir / relative).resolve()
    try:
        target.relative_to(evidence_dir.resolve())
    except ValueError as exc:
        raise ArtifactContractError(f"artifact path escapes its evidence bundle: {reference}") from exc
    return target


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def manifest_candidates(root: Path, evidence_dir: Path | None) -> list[Path]:
    """Return deterministic candidates without using filesystem timestamps."""
    if evidence_dir is not None:
        directory = evidence_dir.resolve()
        return [directory if directory.name == "manifest.json" else directory / "manifest.json"]
    evidence_root = root / "docs" / "evidence"
    if not evidence_root.is_dir():
        return []
    return sorted(evidence_root.glob("*/manifest.json"), key=lambda path: path.as_posix())


def load_evidence_bundle(
    root: Path,
    slice_id: str,
    head: str,
    *,
    evidence_dir: Path | None = None,
    privacy_profile: str = "public",
) -> EvidenceBundle:
    """Load the one manifest bound to an exact slice/head and validate its artifacts.

    Selection is by structured manifest fields only. Directory names, mtimes,
    README prose, evidence logs, and historical keywords never select evidence.
    """
    root = root.resolve()
    slice_id = slice_id.strip()
    head = head.strip().lower()
    if not slice_id:
        raise ArtifactContractError("slice_id is required for evidence selection")
    if not re.fullmatch(r"[0-9a-f]{40,64}", head):
        raise ArtifactContractError("head must be an exact 40-64 character hexadecimal commit id")
    if privacy_profile not in PRIVACY_PROFILES:
        raise ArtifactContractError(
            f"privacy_profile must be one of {sorted(PRIVACY_PROFILES)}, got {privacy_profile!r}"
        )

    candidates = manifest_candidates(root, evidence_dir)
    if not candidates:
        raise ArtifactContractError("no evidence manifests found under docs/evidence")

    exact: list[tuple[Path, dict[str, Any]]] = []
    slice_heads: list[str] = []
    explicit = evidence_dir is not None
    for candidate in candidates:
        if not candidate.is_file():
            if explicit:
                raise ArtifactContractError(f"evidence manifest not found: {candidate}")
            continue
        try:
            manifest = read_json_object(candidate, "evidence manifest")
        except ArtifactContractError:
            if explicit:
                raise
            continue
        if manifest.get("slice_id") != slice_id:
            continue
        repo = manifest.get("repo")
        manifest_head = repo.get("head") if isinstance(repo, dict) else None
        slice_heads.append(str(manifest_head or "<missing>"))
        if manifest_head == head:
            exact.append((candidate, manifest))

    if not exact:
        if slice_heads:
            raise ArtifactContractError(
                f"no evidence manifest for slice {slice_id} at head {head}; "
                f"slice manifests record: {sorted(set(slice_heads))}"
            )
        raise ArtifactContractError(f"no evidence manifest found for slice {slice_id} at head {head}")
    if len(exact) > 1:
        paths = [path.as_posix() for path, _ in exact]
        raise ArtifactContractError(
            f"ambiguous evidence: multiple manifests bind slice {slice_id} to head {head}: {paths}"
        )

    manifest_path, manifest = exact[0]
    evidence_dir = manifest_path.parent.resolve()
    manifest_schema = schema_path(root, "evidence_manifest.schema.json")
    try:
        manifest_issues = validate_file(manifest_path, manifest_schema)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, StateDDYamlError) as exc:
        raise ArtifactContractError(f"could not validate evidence manifest: {exc}") from exc
    if manifest_issues:
        raise ArtifactContractError(format_validation_issues("evidence manifest", manifest_issues))

    if manifest.get("schema") != EVIDENCE_MANIFEST_SCHEMA:
        raise ArtifactContractError(
            f"evidence manifest schema must be {EVIDENCE_MANIFEST_SCHEMA!r}"
        )
    if manifest.get("manifest_status") != "complete":
        raise ArtifactContractError("current-slice evidence manifest_status must be 'complete'")

    repo = manifest.get("repo")
    branch = repo.get("branch") if isinstance(repo, dict) else None
    if not isinstance(branch, str) or not branch:
        raise ArtifactContractError("current-slice evidence manifest repo.branch must be recorded")

    privacy = manifest.get("privacy")
    if not isinstance(privacy, dict) or privacy.get("profile") != privacy_profile:
        raise ArtifactContractError(
            f"evidence manifest privacy.profile must equal requested profile {privacy_profile!r}"
        )
    if privacy_profile == "public" and privacy.get("machine_identity") != "normalized":
        raise ArtifactContractError(
            "public evidence manifest must declare privacy.machine_identity='normalized'"
        )

    change = manifest.get("change")
    change_type = change.get("type") if isinstance(change, dict) else None
    if change_type not in CHANGE_TYPES:
        raise ArtifactContractError(
            f"current-slice evidence manifest change.type must be one of {sorted(CHANGE_TYPES)}"
        )

    redaction = manifest.get("redaction")
    if privacy_profile == "public":
        if not isinstance(redaction, dict) or redaction.get("automated_scan") != "passed":
            raise ArtifactContractError("public evidence requires redaction.automated_scan='passed'")
        if redaction.get("manual_review") != "completed":
            raise ArtifactContractError("public evidence requires redaction.manual_review='completed'")

    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        raise ArtifactContractError("current-slice evidence manifest must list artifacts")
    artifact_paths: dict[str, tuple[dict[str, Any], Path]] = {}
    for index, artifact in enumerate(artifacts):
        if not isinstance(artifact, dict):
            raise ArtifactContractError(f"manifest artifact {index} must be an object")
        reference = artifact.get("path")
        if not isinstance(reference, str) or not reference:
            raise ArtifactContractError(f"manifest artifact {index} must have a non-empty path")
        if reference in artifact_paths:
            raise ArtifactContractError(f"manifest lists duplicate artifact path {reference!r}")
        target = safe_bundle_artifact(evidence_dir, reference)
        if not target.is_file():
            raise ArtifactContractError(f"manifest artifact is missing: {reference}")
        evidence_types = artifact.get("evidence_types")
        if not isinstance(evidence_types, list) or not evidence_types:
            raise ArtifactContractError(
                f"manifest artifact {reference!r} must declare one or more evidence_types"
            )
        unknown_types = sorted(
            repr(evidence_type)
            for evidence_type in evidence_types
            if not isinstance(evidence_type, str) or evidence_type not in EVIDENCE_TYPES
        )
        if unknown_types:
            raise ArtifactContractError(
                f"manifest artifact {reference!r} has unknown evidence_types: {unknown_types}"
            )
        expected_hash = artifact.get("sha256")
        if isinstance(expected_hash, str) and expected_hash and file_sha256(target) != expected_hash:
            raise ArtifactContractError(f"manifest artifact hash mismatch: {reference}")
        if privacy_profile == "public":
            if artifact.get("redaction_status") not in {"checked", "checked_with_limits"}:
                raise ArtifactContractError(
                    f"public artifact {reference!r} has unacceptable redaction_status"
                )
            if artifact.get("sensitive_data") not in {"none_found", "redacted"}:
                raise ArtifactContractError(
                    f"public artifact {reference!r} has unresolved sensitive_data"
                )
        artifact_paths[reference] = (artifact, target)

    claims = manifest.get("claims")
    if not isinstance(claims, list) or not claims:
        raise ArtifactContractError("current-slice evidence manifest must list claims")
    for claim in claims:
        if not isinstance(claim, dict):
            continue
        references = claim.get("evidence")
        if not isinstance(references, list):
            continue
        missing_references = [reference for reference in references if reference not in artifact_paths]
        if missing_references:
            raise ArtifactContractError(
                f"claim {claim.get('id', '<missing>')!r} references unlisted artifacts: {missing_references}"
            )

    runtime_ref = manifest.get("runtime_identity")
    if not isinstance(runtime_ref, dict):
        raise ArtifactContractError("evidence manifest must include runtime_identity metadata")
    runtime_reference = runtime_ref.get("path")
    if not isinstance(runtime_reference, str) or not runtime_reference:
        raise ArtifactContractError("evidence manifest runtime_identity.path is required")
    runtime_entry = artifact_paths.get(runtime_reference)
    if runtime_entry is None or runtime_entry[0].get("kind") != "runtime_identity":
        raise ArtifactContractError(
            "runtime_identity.path must name an artifact with kind='runtime_identity'"
        )
    runtime_path = runtime_entry[1]
    runtime_schema = schema_path(root, "runtime_identity.schema.json")
    try:
        runtime_issues = validate_file(runtime_path, runtime_schema)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, StateDDYamlError) as exc:
        raise ArtifactContractError(f"could not validate runtime identity: {exc}") from exc
    if runtime_issues:
        raise ArtifactContractError(format_validation_issues("runtime identity", runtime_issues))
    runtime_identity = read_json_object(runtime_path, "runtime identity")
    if runtime_identity.get("schema") != RUNTIME_IDENTITY_SCHEMA:
        raise ArtifactContractError(
            f"runtime identity schema must be {RUNTIME_IDENTITY_SCHEMA!r}"
        )

    runtime_privacy = runtime_identity.get("privacy")
    if not isinstance(runtime_privacy, dict) or runtime_privacy.get("profile") != privacy_profile:
        raise ArtifactContractError(
            "runtime identity privacy.profile must match the evidence manifest profile"
        )
    if privacy_profile == "public":
        if runtime_privacy.get("machine_identity") != "normalized":
            raise ArtifactContractError(
                "public runtime identity must declare privacy.machine_identity='normalized'"
            )
        privacy_issues = public_runtime_identity_issues(runtime_identity)
        if privacy_issues:
            raise ArtifactContractError(
                format_validation_issues("public runtime identity", privacy_issues)
            )

    runtime_repo = runtime_identity.get("repo")
    runtime_head = runtime_repo.get("head") if isinstance(runtime_repo, dict) else None
    runtime_branch = runtime_repo.get("branch") if isinstance(runtime_repo, dict) else None
    if runtime_head != head:
        raise ArtifactContractError(
            f"runtime identity repo.head {runtime_head!r} does not match manifest head {head!r}"
        )
    if runtime_branch != branch:
        raise ArtifactContractError(
            f"runtime identity repo.branch {runtime_branch!r} does not match manifest branch {branch!r}"
        )

    runtime = runtime_identity.get("runtime")
    runtime_required = runtime.get("required") if isinstance(runtime, dict) else None
    if runtime_required is not runtime_ref.get("required"):
        raise ArtifactContractError(
            "manifest runtime_identity.required does not match runtime artifact runtime.required"
        )
    runtime_status = runtime_ref.get("status")
    if runtime_required is True and runtime_status != "valid":
        raise ArtifactContractError("required runtime identity must have status='valid'")
    if runtime_required is False and runtime_status != "not_applicable":
        raise ArtifactContractError("non-required runtime identity must have status='not_applicable'")

    return EvidenceBundle(
        directory=evidence_dir,
        manifest_path=manifest_path.resolve(),
        manifest=manifest,
        runtime_identity_path=runtime_path,
        runtime_identity=runtime_identity,
    )


def root_targets(root: Path) -> list[tuple[Path, Path, bool]]:
    targets: list[tuple[Path, Path, bool]] = [
        (root / "PROJECT_STATE.yaml", schema_path(root, "project_state.schema.json"), True),
        (root / "PROJECT_DNA.yaml", schema_path(root, "project_dna.schema.json"), True),
        (root / "PROJECT_ADAPTER.yaml", schema_path(root, "project_adapter.schema.json"), False),
        (root / "prompts" / "FINAL_HANDOFF_TEMPLATE.md", schema_path(root, "final_handoff_contract.json"), False),
    ]

    evidence_root = root / "docs" / "evidence"
    if evidence_root.exists():
        for readme in sorted(evidence_root.glob("*/README.md")):
            targets.append((readme, schema_path(root, "evidence_readme_contract.json"), True))
        for artifact in sorted(evidence_root.glob("*/runtime_identity.json")):
            targets.append((artifact, schema_path(root, "runtime_identity.schema.json"), True))
        for manifest in sorted(evidence_root.glob("*/manifest.json")):
            targets.append((manifest, schema_path(root, "evidence_manifest.schema.json"), True))
        for browser in sorted(evidence_root.glob("*/browser_verification.json")):
            targets.append((browser, schema_path(root, "browser_verification.schema.json"), True))
    return targets


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate StateDD schemas and markdown contracts")
    parser.add_argument("root", nargs="?", default=str(ROOT), help="Repo root to validate")
    parser.add_argument("--file", help="Validate one file instead of a repo root")
    parser.add_argument("--schema", help="Schema or markdown contract for --file")
    parser.add_argument("--quiet", action="store_true", help="Only print failures")
    return parser.parse_args(argv[1:])


def print_target_result(label: str, issues: list[ValidationIssue], quiet: bool) -> None:
    if not issues:
        if not quiet:
            print(f"  PASS {label}")
        return
    print(f"  FAIL {label}")
    for issue in issues:
        print(f"    - {issue.path}: {issue.message}")


def validate_root(root: Path, quiet: bool) -> int:
    all_issues: list[tuple[str, list[ValidationIssue]]] = []
    if not quiet:
        print("============================================================")
        print("STATEDD SCHEMA VALIDATION")
        print("============================================================")
    for path, schema_path, required in root_targets(root):
        label = path.relative_to(root).as_posix() if path.is_relative_to(root) else str(path)
        if not path.exists():
            if required:
                issues = [ValidationIssue("$", f"missing required validation target: {label}")]
                all_issues.append((label, issues))
                print_target_result(label, issues, quiet)
            elif not quiet:
                print(f"  SKIP {label} (optional target not present)")
            continue
        if not schema_path.exists():
            issues = [ValidationIssue("$", f"missing schema file: {schema_path}")]
            all_issues.append((label, issues))
            print_target_result(label, issues, quiet)
            continue
        try:
            issues = validate_file(path, schema_path)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, StateDDYamlError) as exc:
            issues = [ValidationIssue("$", f"could not parse or validate file: {exc}")]
        if issues:
            all_issues.append((label, issues))
        print_target_result(label, issues, quiet)

    if all_issues:
        print(f"FAILED: {sum(len(issues) for _, issues in all_issues)} schema issue(s) found")
        return 1
    if not quiet:
        print("PASSED: All StateDD schema checks passed")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv)
    root = Path(args.root).resolve()
    if args.file or args.schema:
        if not args.file or not args.schema:
            raise SystemExit("--file and --schema must be used together")
        path = Path(args.file).resolve()
        schema_path = Path(args.schema).resolve()
        try:
            issues = validate_file(path, schema_path)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, StateDDYamlError) as exc:
            issues = [ValidationIssue("$", f"could not parse or validate file: {exc}")]
        label = path.name
        print_target_result(label, issues, args.quiet)
        if issues:
            print(f"FAILED: {len(issues)} schema issue(s) found")
            return 1
        if not args.quiet:
            print("PASSED: File schema check passed")
        return 0
    return validate_root(root, args.quiet)


if __name__ == "__main__":
    raise SystemExit(main())
