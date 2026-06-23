#!/usr/bin/env python3
"""Validate StateDD state, evidence, runtime, and handoff contracts.

The validator intentionally stays stdlib-only. It implements the small JSON
Schema subset used by this template and a tiny YAML parser for the StateDD YAML
style emitted by `scripts/init_template.py`.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_ROOT = ROOT / "schemas"


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
                extra, index = parse_mapping(lines, index, lines[index][0])
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
        index += 1
        if value_text in {"|", ">"}:
            mapping[key], index = parse_block_scalar(lines, index, indent + 2)
        elif value_text == "":
            if index < len(lines) and lines[index][0] > indent:
                mapping[key], index = parse_block(lines, index, lines[index][0])
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


def validate_json_schema(value: Any, schema: dict[str, Any], path: str = "$") -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []

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
                issues.extend(validate_json_schema(item, item_schema, f"{path}[{index}]"))

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
                    issues.extend(validate_json_schema(value[key], property_schema, f"{path}.{key}"))
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
                issues.extend(validate_json_schema(nested, additional, f"{path}.{key}"))

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
