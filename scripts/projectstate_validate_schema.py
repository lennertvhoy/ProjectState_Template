#!/usr/bin/env python3
"""Validate StateDD state, evidence, runtime, and handoff contracts.

The validator intentionally stays stdlib-only. It implements the small JSON
Schema subset used by this template and a tiny YAML parser for the StateDD YAML
style emitted by `scripts/init_template.py`.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from statedd_contracts import (
        ContractError,
        UnsafePathError,
        confined_path,
        load_json_file,
        load_profile_catalog,
        normalize_relative_path,
        regular_source_path,
        resolve_profile,
        safe_root_path,
    )
except ModuleNotFoundError:  # pragma: no cover - pytest package import path
    from scripts.statedd_contracts import (
        ContractError,
        UnsafePathError,
        confined_path,
        load_json_file,
        load_profile_catalog,
        normalize_relative_path,
        regular_source_path,
        resolve_profile,
        safe_root_path,
    )


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_ROOT = ROOT / "schemas"

TERMINAL_ACTIVE_PROBLEM_STATUSES = {
    "ACCEPTED",
    "CLOSED",
    "COMPLETE",
    "COMPLETED",
    "CLOSURE_GRADE_CI_VERIFIED",
    "MERGED_AND_VERIFIED",
    "MERGED_INTO_MAIN",
    "MERGED_MAIN_CI_PASSING",
    "MERGED_MAIN_CI_VERIFIED",
}
VOLATILE_CONTAINING_HEAD_FIELDS = {
    "containing_commit",
    "containing_head",
    "current_main_head",
    "default_branch_head",
    "github_main",
    "github_main_head",
    "last_verified_head",
    "main_commit",
    "main_head",
}


@dataclass
class ValidationIssue:
    path: str
    message: str


class StateDDYamlError(ValueError):
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
                item_map[key], index = parse_block_scalar(lines, index, indent + 2)
            elif value_text == "":
                if index < len(lines) and lines[index][0] > indent:
                    item_map[key], index = parse_block(lines, index, lines[index][0])
                else:
                    item_map[key] = {}
            else:
                item_map[key] = scalar(value_text)
            if index < len(lines) and lines[index][0] > indent:
                extra_lineno = lines[index][2]
                extra, index = parse_mapping(lines, index, lines[index][0])
                duplicate_keys = sorted(set(item_map) & set(extra))
                if duplicate_keys:
                    raise StateDDYamlError(
                        f"line {extra_lineno}: duplicate mapping key {duplicate_keys[0]!r}"
                    )
                item_map.update(extra)
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


def parse_mapping(lines: list[tuple[int, str, int]], index: int, indent: int) -> tuple[dict[str, Any], int]:
    mapping: dict[str, Any] = {}
    while index < len(lines):
        current_indent, content, lineno = lines[index]
        if current_indent < indent:
            break
        if current_indent != indent or content.startswith("- "):
            break
        key, value_text = split_key_value(content, lineno)
        if key in mapping:
            raise StateDDYamlError(f"line {lineno}: duplicate mapping key {key!r}")
        index += 1
        if value_text in {"|", ">"}:
            mapping[key], index = parse_block_scalar(lines, index, indent + 2)
        elif value_text == "":
            if index < len(lines) and lines[index][0] > indent:
                mapping[key], index = parse_block(lines, index, lines[index][0])
            elif index < len(lines) and lines[index][0] == indent and lines[index][1].startswith("- "):
                # YAML permits a sequence value to use the same indentation as
                # its parent key (the common "indentless sequence" style).
                mapping[key], index = parse_sequence(lines, index, indent)
            else:
                mapping[key] = {}
        else:
            mapping[key] = scalar(value_text)
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
        return load_json_file(path)
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


def _resolve_local_ref(root_schema: dict[str, Any], ref: str) -> dict[str, Any]:
    if not ref.startswith("#/"):
        raise ContractError(f"only local JSON Schema references are supported: {ref!r}")
    current: Any = root_schema
    for raw in ref[2:].split("/"):
        key = raw.replace("~1", "/").replace("~0", "~")
        if not isinstance(current, dict) or key not in current:
            raise ContractError(f"unresolvable JSON Schema reference: {ref!r}")
        current = current[key]
    if not isinstance(current, dict):
        raise ContractError(f"JSON Schema reference does not target an object: {ref!r}")
    return current


def validate_json_schema(
    value: Any,
    schema: dict[str, Any],
    path: str = "$",
    *,
    _root_schema: dict[str, Any] | None = None,
    _ref_stack: tuple[str, ...] = (),
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    root_schema = schema if _root_schema is None else _root_schema

    ref = schema.get("$ref")
    if isinstance(ref, str):
        if ref in _ref_stack:
            return [ValidationIssue(path, f"cyclic JSON Schema reference: {ref!r}")]
        try:
            resolved = _resolve_local_ref(root_schema, ref)
        except ContractError as exc:
            return [ValidationIssue(path, str(exc))]
        issues.extend(
            validate_json_schema(
                value,
                resolved,
                path,
                _root_schema=root_schema,
                _ref_stack=(*_ref_stack, ref),
            )
        )
        schema = {key: nested for key, nested in schema.items() if key != "$ref"}

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

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        minimum = schema.get("minimum")
        maximum = schema.get("maximum")
        if isinstance(minimum, (int, float)) and value < minimum:
            issues.append(ValidationIssue(path, f"expected value >= {minimum}"))
        if isinstance(maximum, (int, float)) and value > maximum:
            issues.append(ValidationIssue(path, f"expected value <= {maximum}"))

    if isinstance(value, list):
        min_items = schema.get("minItems")
        if isinstance(min_items, int) and len(value) < min_items:
            issues.append(ValidationIssue(path, f"expected at least {min_items} item(s)"))
        if schema.get("uniqueItems") is True:
            seen: set[str] = set()
            for index, item in enumerate(value):
                marker = json.dumps(item, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
                if marker in seen:
                    issues.append(ValidationIssue(f"{path}[{index}]", "duplicate array item is not allowed"))
                seen.add(marker)
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, item in enumerate(value):
                issues.extend(
                    validate_json_schema(
                        item,
                        item_schema,
                        f"{path}[{index}]",
                        _root_schema=root_schema,
                        _ref_stack=_ref_stack,
                    )
                )

    if isinstance(value, dict):
        min_properties = schema.get("minProperties")
        max_properties = schema.get("maxProperties")
        if isinstance(min_properties, int) and len(value) < min_properties:
            issues.append(ValidationIssue(path, f"expected at least {min_properties} properties"))
        if isinstance(max_properties, int) and len(value) > max_properties:
            issues.append(ValidationIssue(path, f"expected at most {max_properties} properties"))
        required = schema.get("required", [])
        if isinstance(required, list):
            for key in required:
                if key not in value:
                    issues.append(ValidationIssue(path, f"missing required property {key!r}"))
        properties = schema.get("properties", {})
        if isinstance(properties, dict):
            for key, property_schema in properties.items():
                if key in value and isinstance(property_schema, dict):
                    issues.extend(
                        validate_json_schema(
                            value[key],
                            property_schema,
                            f"{path}.{key}",
                            _root_schema=root_schema,
                            _ref_stack=_ref_stack,
                        )
                    )
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
                issues.extend(
                    validate_json_schema(
                        nested,
                        additional,
                        f"{path}.{key}",
                        _root_schema=root_schema,
                        _ref_stack=_ref_stack,
                    )
                )

    semantics = schema.get("statedd_semantics")
    if isinstance(semantics, dict):
        issues.extend(validate_statedd_semantics(value, semantics, path))

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
    if semantics.get("live_state_is_nonterminal") is True and isinstance(value, dict):
        active = value.get("active_problems")
        active_records = active if isinstance(active, list) else []
        active_p0_ids: set[str] = set()
        for index, record in enumerate(active_records):
            if not isinstance(record, dict):
                continue
            problem_id = record.get("id")
            severity = record.get("severity")
            if isinstance(problem_id, str) and isinstance(severity, str) and severity.upper() == "P0":
                active_p0_ids.add(problem_id)
            raw_status = record.get("status")
            status = (
                re.sub(r"[^A-Z0-9]+", "_", raw_status.strip().upper()).strip("_")
                if isinstance(raw_status, str)
                else ""
            )
            if status in TERMINAL_ACTIVE_PROBLEM_STATUSES:
                issues.append(
                    ValidationIssue(
                        f"{path}.active_problems[{index}].status",
                        "terminal work cannot remain in active_problems",
                    )
                )

        current_state = value.get("current_state")
        if isinstance(current_state, dict):
            declared = current_state.get("open_p0_failures")
            if isinstance(declared, list):
                declared_ids = {str(item) for item in declared}
                if declared_ids != active_p0_ids:
                    issues.append(
                        ValidationIssue(
                            f"{path}.current_state.open_p0_failures",
                            "must match the IDs of active P0 problems",
                        )
                    )
            execution = current_state.get("execution_mode")
            execution_mode = (
                str(execution.get("mode", "")).strip().lower()
                if isinstance(execution, dict)
                else ""
            )
            quality_gates = current_state.get("quality_gates")
            quality_status = (
                str(quality_gates.get("status", "")).strip().lower()
                if isinstance(quality_gates, dict)
                else ""
            )
            if (execution_mode == "quality_freeze" or "open_p0" in quality_status) and not active_p0_ids:
                issues.append(
                    ValidationIssue(
                        f"{path}.current_state.execution_mode",
                        "quality_freeze/active_with_open_p0 requires an active P0 problem",
                    )
                )

        def walk(nested: Any, nested_path: str) -> None:
            if isinstance(nested, dict):
                for key, item in nested.items():
                    item_path = f"{nested_path}.{key}"
                    if (
                        str(key).lower() in VOLATILE_CONTAINING_HEAD_FIELDS
                        and isinstance(item, str)
                        and re.fullmatch(r"[0-9a-f]{7,40}", item)
                    ):
                        issues.append(
                            ValidationIssue(
                                item_path,
                                "live state must not embed a volatile containing-main SHA",
                            )
                        )
                    walk(item, item_path)
            elif isinstance(nested, list):
                for index, item in enumerate(nested):
                    walk(item, f"{nested_path}[{index}]")

        walk(value, path)
    if semantics.get("managed_asset_paths_safe_and_unique") is True and isinstance(value, dict):
        records = value.get("managed_assets")
        if isinstance(records, list):
            seen: set[Path] = set()
            for index, record in enumerate(records):
                raw = record.get("path") if isinstance(record, dict) else None
                if not isinstance(raw, str):
                    continue
                try:
                    normalized = normalize_relative_path(raw)
                except UnsafePathError as exc:
                    issues.append(ValidationIssue(f"{path}.managed_assets[{index}].path", str(exc)))
                    continue
                if normalized in seen:
                    issues.append(
                        ValidationIssue(
                            f"{path}.managed_assets[{index}].path",
                            f"duplicate managed asset path: {raw}",
                        )
                    )
                seen.add(normalized)
    if semantics.get("evidence_paths_safe_and_unique") is True and isinstance(value, dict):
        artifacts = value.get("artifacts")
        claims = value.get("claims")
        seen: set[Path] = set()
        if isinstance(artifacts, list):
            for index, artifact in enumerate(artifacts):
                raw = artifact.get("path") if isinstance(artifact, dict) else None
                if not isinstance(raw, str):
                    continue
                try:
                    normalized = normalize_relative_path(raw)
                except UnsafePathError as exc:
                    issues.append(ValidationIssue(f"{path}.artifacts[{index}].path", str(exc)))
                    continue
                if normalized in seen:
                    issues.append(
                        ValidationIssue(
                            f"{path}.artifacts[{index}].path",
                            f"duplicate evidence artifact path: {raw}",
                        )
                    )
                seen.add(normalized)
        if isinstance(claims, list):
            for claim_index, claim in enumerate(claims):
                refs = claim.get("evidence") if isinstance(claim, dict) else None
                if not isinstance(refs, list):
                    continue
                for ref_index, raw in enumerate(refs):
                    if not isinstance(raw, str):
                        continue
                    try:
                        normalize_relative_path(raw)
                    except UnsafePathError as exc:
                        issues.append(
                            ValidationIssue(
                                f"{path}.claims[{claim_index}].evidence[{ref_index}]",
                                str(exc),
                            )
                        )
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
    schema = load_json_file(schema_path)
    if not isinstance(schema, dict):
        raise ContractError(f"schema root must be an object: {schema_path}")
    return schema


def validate_file(path: Path, schema_path: Path) -> list[ValidationIssue]:
    schema = load_schema(schema_path)
    if schema.get("contract_type") == "markdown_contract":
        return validate_markdown_contract(path.read_text(encoding="utf-8"), schema)
    data = load_data(path)
    return validate_json_schema(data, schema)


def schema_path(root: Path, relpath: str) -> Path:
    local = root / "schemas" / relpath
    if local.exists():
        return local
    return SCHEMA_ROOT / relpath


def root_targets(root: Path) -> list[tuple[Path, Path, bool]]:
    targets: list[tuple[Path, Path, bool]] = [
        (root / "PROJECT_STATE.yaml", schema_path(root, "project_state.schema.json"), True),
        (root / "PROJECT_DNA.yaml", schema_path(root, "project_dna.schema.json"), True),
        (root / "PROJECT_ADAPTER.yaml", schema_path(root, "project_adapter.schema.json"), False),
        (root / "STATEDD_ASSETS.json", schema_path(root, "statedd_assets.schema.json"), False),
        (root / "profiles" / "catalog.json", schema_path(root, "profile_catalog.schema.json"), False),
        (root / "docs" / "metrics" / "profile_metrics.json", schema_path(root, "profile_metrics.schema.json"), False),
        (root / "prompts" / "FINAL_HANDOFF_TEMPLATE.md", schema_path(root, "final_handoff_contract.json"), False),
    ]

    evidence_root = root / "docs" / "evidence"
    if evidence_root.exists():
        if evidence_root.is_symlink() or not evidence_root.is_dir():
            raise UnsafePathError("docs/evidence must be a real directory, not a symlink")
        evidence_contracts = {
            "README.md": "evidence_readme_contract.json",
            "runtime_identity.json": "runtime_identity.schema.json",
            "manifest.json": "evidence_manifest.schema.json",
            "browser_verification.json": "browser_verification.schema.json",
        }
        for folder in sorted(evidence_root.iterdir()):
            if folder.name.startswith("."):
                continue
            if folder.is_symlink():
                raise UnsafePathError(f"refusing symlinked evidence folder: {folder}")
            if not folder.is_dir():
                continue
            for name, contract in evidence_contracts.items():
                candidate = confined_path(root, folder.relative_to(root) / name)
                if candidate.exists():
                    if name == "runtime_identity.json":
                        try:
                            runtime_payload = load_json_file(candidate)
                        except ContractError:
                            runtime_payload = {}
                        if (
                            isinstance(runtime_payload, dict)
                            and runtime_payload.get("schema") == "statedd.runtime_identity.v2"
                        ):
                            contract = "runtime_identity_v2.schema.json"
                    targets.append((candidate, schema_path(root, contract), True))
    return targets


def validate_manifest_catalog_consistency(root: Path) -> list[ValidationIssue]:
    manifest_path = root / "STATEDD_ASSETS.json"
    catalog_path = root / "profiles" / "catalog.json"
    if not manifest_path.exists() or not catalog_path.exists():
        return []
    manifest = load_json_file(manifest_path)
    if not isinstance(manifest, dict) or manifest.get("schema") != "statedd.runtime_assets.v2":
        return []
    catalog = load_profile_catalog(root)
    profile = manifest.get("profile")
    if not isinstance(profile, str) or profile not in catalog["profiles"]:
        return [ValidationIssue("$.profile", f"profile {profile!r} is absent from profiles/catalog.json")]
    raw_sets = manifest.get("asset_sets")
    optional_sets = []
    if isinstance(raw_sets, list):
        optional_sets = [
            set_id
            for set_id in raw_sets
            if set_id in catalog["asset_sets"] and catalog["asset_sets"][set_id].get("optional") is True
        ]
    resolved = resolve_profile(catalog, profile, optional_asset_sets=optional_sets)
    expected = {
        "profile_dependencies": list(resolved.profile_dependencies),
        "asset_sets": list(resolved.asset_sets),
        "capabilities": list(resolved.capabilities),
        "validations": list(resolved.validations),
        "required_gate_level": resolved.required_gate_level,
    }
    issues: list[ValidationIssue] = []
    for field, value in expected.items():
        if manifest.get(field) != value:
            issues.append(ValidationIssue(f"$.{field}", f"must match current profile catalog: {value!r}"))
    catalog_block = manifest.get("catalog")
    actual_hash = hashlib.sha256(catalog_path.read_bytes()).hexdigest()
    if not isinstance(catalog_block, dict) or catalog_block.get("sha256") != actual_hash:
        issues.append(ValidationIssue("$.catalog.sha256", "must match profiles/catalog.json"))
    return issues


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
    try:
        targets = root_targets(root)
    except (ContractError, UnsafePathError, OSError) as exc:
        issues = [ValidationIssue("$", f"unsafe validation target: {exc}")]
        print_target_result("validation targets", issues, quiet)
        return 1
    for path, schema_path, required in targets:
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
        if path.is_symlink() or not path.is_file():
            issues = [ValidationIssue("$", "validation target must be a regular non-symlink file")]
            all_issues.append((label, issues))
            print_target_result(label, issues, quiet)
            continue
        try:
            regular_source_path(schema_path.parent, schema_path.name)
        except (ContractError, UnsafePathError) as exc:
            issues = [ValidationIssue("$", f"schema must be a regular confined file: {exc}")]
            all_issues.append((label, issues))
            print_target_result(label, issues, quiet)
            continue
        try:
            issues = validate_file(path, schema_path)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, StateDDYamlError, ContractError) as exc:
            issues = [ValidationIssue("$", f"could not parse or validate file: {exc}")]
        if issues:
            all_issues.append((label, issues))
        print_target_result(label, issues, quiet)

    try:
        consistency_issues = validate_manifest_catalog_consistency(root)
    except (ContractError, UnsafePathError, OSError) as exc:
        consistency_issues = [ValidationIssue("$", f"could not validate manifest/catalog agreement: {exc}")]
    if consistency_issues:
        all_issues.append(("manifest/catalog agreement", consistency_issues))
    print_target_result("manifest/catalog agreement", consistency_issues, quiet)

    if all_issues:
        print(f"FAILED: {sum(len(issues) for _, issues in all_issues)} schema issue(s) found")
        return 1
    if not quiet:
        print("PASSED: All StateDD schema checks passed")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv)
    try:
        root = safe_root_path(args.root, must_exist=True)
    except UnsafePathError as exc:
        print(f"FAILED: unsafe validation root: {exc}")
        return 1
    if args.file or args.schema:
        if not args.file or not args.schema:
            raise SystemExit("--file and --schema must be used together")
        try:
            raw_path = Path(args.file)
            raw_schema = Path(args.schema)
            path_root = safe_root_path(raw_path.parent or Path("."), must_exist=True)
            schema_root = safe_root_path(raw_schema.parent or Path("."), must_exist=True)
            path = regular_source_path(path_root, raw_path.name)
            schema_path = regular_source_path(schema_root, raw_schema.name)
        except (ContractError, UnsafePathError) as exc:
            print(f"FAILED: unsafe explicit validation target: {exc}")
            return 1
        try:
            issues = validate_file(path, schema_path)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, StateDDYamlError, ContractError) as exc:
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
