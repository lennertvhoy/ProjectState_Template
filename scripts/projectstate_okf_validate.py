#!/usr/bin/env python3
"""Validate an optional OKF v0.1 knowledge bundle and ProjectState governance.

The validator intentionally uses only the Python standard library plus the
already-shipped ProjectState YAML subset parser. OKF's base contract is permissive:
unknown types, unknown frontmatter fields, broken links, and missing indexes are
warnings. The namespaced ``projectstate`` extension adds ownership, provenance, and
staleness checks that are strict when ``--strict`` is requested.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    from projectstate_contracts import (
        ContractError,
        UnsafePathError,
        normalize_relative_path,
        regular_source_path,
        safe_root_path,
    )
    from projectstate_validate_schema import ProjectStateYamlError, parse_yaml_text
except ModuleNotFoundError:  # pragma: no cover - package import path in pytest
    from scripts.projectstate_contracts import (
        ContractError,
        UnsafePathError,
        normalize_relative_path,
        regular_source_path,
        safe_root_path,
    )
    from scripts.projectstate_validate_schema import ProjectStateYamlError, parse_yaml_text


OKF_VERSION = "0.1"
OKF_SPEC_COMMIT = "ee67a5ca27044ebe7c38385f5b6cffc2305a9c1a"
SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
DATE_HEADING_RE = re.compile(r"^##\s+(\d{4}-\d{2}-\d{2})\s*$")
LINK_RE = re.compile(r"!?(?:\[[^\]]*\])\(([^)\s]+)(?:\s+[^)]*)?\)")
ABSOLUTE_LOCAL_PATH_RE = re.compile(
    r"(?:^|[\s`\"'])/(?:home|Users|tmp|private/tmp|var/tmp)/|"
    r"(?:^|[\s`\"'])[A-Za-z]:[\\/]Users[\\/]",
    re.IGNORECASE,
)
SECRET_RE = re.compile(
    r"\b(?:api[_-]?key|api[_-]?secret|access[_-]?token|private[_-]?key|password)\b"
    r"\s*[:=]\s*['\"]?[^\s'\"]{8,}",
    re.IGNORECASE,
)


@dataclass
class Finding:
    path: str
    message: str


@dataclass
class Report:
    bundle: str
    source_root: str
    concepts: int = 0
    warnings: list[Finding] = field(default_factory=list)
    errors: list[Finding] = field(default_factory=list)
    stale: list[Finding] = field(default_factory=list)

    def error(self, path: Path | str, message: str) -> None:
        self.errors.append(Finding(str(path), message))

    def warning(self, path: Path | str, message: str) -> None:
        self.warnings.append(Finding(str(path), message))


def _split_flow_items(value: str) -> list[str]:
    """Split a simple YAML flow collection without treating quoted commas as separators."""
    inner = value[1:-1].strip()
    if not inner:
        return []
    parts: list[str] = []
    start = 0
    depth = 0
    quote: str | None = None
    escaped = False
    for index, char in enumerate(inner):
        if escaped:
            escaped = False
            continue
        if char == "\\" and quote == '"':
            escaped = True
            continue
        if char in {"'", '"'}:
            if quote == char:
                quote = None
            elif quote is None:
                quote = char
        elif quote is None and char in "[{":
            depth += 1
        elif quote is None and char in "]}":
            depth -= 1
        elif quote is None and char == "," and depth == 0:
            parts.append(inner[start:index].strip())
            start = index + 1
    parts.append(inner[start:].strip())
    return parts


def _flow_scalar(value: str) -> Any:
    """Parse the small flow scalar subset commonly used in OKF frontmatter."""
    value = value.strip()
    if value.startswith("[") and value.endswith("]"):
        return [_flow_scalar(item) for item in _split_flow_items(value)]
    if value.startswith("{") and value.endswith("}"):
        result: dict[str, Any] = {}
        for item in _split_flow_items(value):
            if ":" not in item:
                return value
            key, raw = item.split(":", 1)
            key = key.strip().strip("'\"")
            if not key or key in result:
                raise ProjectStateYamlError(f"duplicate or empty flow mapping key {key!r}")
            result[key] = _flow_scalar(raw)
        return result
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return value[1:-1]
    lowered = value.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if lowered == "null":
        return None
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    return value


def _expand_flow_values(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _expand_flow_values(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_expand_flow_values(item) for item in value]
    if isinstance(value, str):
        stripped = value.strip()
        if (stripped.startswith("[") and stripped.endswith("]")) or (
            stripped.startswith("{") and stripped.endswith("}")
        ):
            return _flow_scalar(stripped)
    return value


def parse_frontmatter(text: str, path: Path) -> tuple[dict[str, Any], str]:
    if not text.startswith("---\n") and text != "---":
        raise ProjectStateYamlError(f"{path}: missing YAML frontmatter opening delimiter")
    lines = text.splitlines(keepends=True)
    closing_index = next(
        (index for index, line in enumerate(lines[1:], start=1) if line.rstrip("\r\n") == "---"),
        None,
    )
    if closing_index is None:
        raise ProjectStateYamlError(f"{path}: missing YAML frontmatter closing delimiter")
    raw = "".join(lines[1:closing_index])
    # The shared ProjectState YAML subset intentionally treats ``- key: value`` as
    # a mapping. Quote bare URL sequence items so valid citation lists such as
    # ``- https://example.com`` remain scalar strings without broadening the
    # parser used by the rest of ProjectState.
    raw = re.sub(r"(?m)^(\s*)-\s+(https?://[^\s#]+)\s*$", r'\1- "\2"', raw)
    data = _expand_flow_values(parse_yaml_text(raw))
    if not isinstance(data, dict):
        raise ProjectStateYamlError(f"{path}: frontmatter must be a mapping")
    body = "".join(lines[closing_index + 1 :])
    return data, body


def parse_timestamp(value: Any, field: str, path: Path, report: Report) -> bool:
    if not isinstance(value, str) or not value.strip():
        report.error(path, f"{field} must be a non-empty ISO 8601 timestamp")
        return False
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        report.error(path, f"{field} is not a valid ISO 8601 timestamp")
        return False
    if parsed.tzinfo is None:
        report.error(path, f"{field} must include a timezone")
        return False
    return True


def check_text_hygiene(text: str, path: Path, report: Report) -> None:
    if ABSOLUTE_LOCAL_PATH_RE.search(text):
        report.error(path, "contains a personal or machine-local absolute path")
    if SECRET_RE.search(text):
        report.error(path, "contains a secret-like assignment; remove it or use a reference")


def check_links(root: Path, path: Path, body: str, report: Report) -> None:
    for raw_target in LINK_RE.findall(body):
        target = raw_target.split("#", 1)[0]
        if not target or target.startswith(("http://", "https://", "mailto:", "data:")):
            continue
        if target.startswith("/"):
            candidate = root / target.lstrip("/")
        else:
            candidate = path.parent / target
        try:
            candidate = candidate.resolve(strict=False)
            candidate.relative_to(root)
        except (OSError, ValueError):
            report.warning(path.relative_to(root), f"broken or escaping link: {raw_target}")
            continue
        if not candidate.exists():
            report.warning(path.relative_to(root), f"broken link target: {raw_target}")


def check_index(path: Path, root: Path, text: str, report: Report) -> None:
    relative = path.relative_to(root)
    if path.name == "index.md" and path == root / "index.md" and text.startswith("---"):
        try:
            frontmatter, body = parse_frontmatter(text, path)
        except ProjectStateYamlError as exc:
            report.error(relative, str(exc))
            return
        if set(frontmatter) != {"okf_version"} or frontmatter.get("okf_version") != OKF_VERSION:
            report.error(relative, "root index frontmatter must contain only okf_version: '0.1'")
        check_text_hygiene(text, relative, report)
        check_links(root, path, body, report)
        return
    if text.startswith("---"):
        report.error(relative, "reserved index.md/log.md files must not contain frontmatter")
    if path.name == "log.md":
        headings = [line for line in text.splitlines() if line.startswith("## ")]
        for heading in headings:
            if DATE_HEADING_RE.match(heading) is None:
                report.error(relative, "log.md level-two headings must use YYYY-MM-DD dates")
    check_text_hygiene(text, relative, report)
    check_links(root, path, text, report)


def validate_source(source_root: Path, source: dict[str, Any], path: Path, report: Report) -> None:
    if not isinstance(source, dict):
        report.error(path, "each projectstate.sources entry must be a mapping")
        return
    source_path = source.get("path")
    digest = source.get("sha256")
    if not isinstance(source_path, str) or not source_path:
        report.error(path, "derived source path must be a non-empty repository-relative path")
        return
    try:
        normalized = normalize_relative_path(source_path)
        source_file = regular_source_path(source_root, normalized)
    except (ContractError, OSError) as exc:
        report.error(path, f"unsafe or unavailable derived source {source_path!r}: {exc}")
        return
    if not isinstance(digest, str) or SHA256_RE.fullmatch(digest) is None:
        report.error(path, f"derived source {source_path!r} must have a 64-character sha256")
        return
    actual = hashlib.sha256(source_file.read_bytes()).hexdigest()
    if actual.lower() != digest.lower():
        finding = Finding(str(path), f"derived source is stale: {source_path!r} hash differs")
        report.stale.append(finding)
        report.error(path, finding.message)


def check_governance(
    path: Path,
    frontmatter: dict[str, Any],
    source_root: Path,
    report: Report,
) -> None:
    extension = frontmatter.get("projectstate")
    if extension is None:
        return
    if not isinstance(extension, dict):
        report.error(path, "projectstate extension must be a mapping")
        return
    authority = extension.get("authority")
    if authority not in {"canonical", "derived", "reference"}:
        report.error(path, "projectstate.authority must be canonical, derived, or reference")
        return
    if authority == "canonical":
        if not isinstance(extension.get("owner"), str) or not extension["owner"].strip():
            report.error(path, "canonical concepts require a non-empty projectstate.owner")
        parse_timestamp(extension.get("reviewed_at"), "projectstate.reviewed_at", path, report)
    elif authority == "derived":
        sources = extension.get("sources")
        if not isinstance(sources, list) or not sources:
            report.error(path, "derived concepts require a non-empty projectstate.sources list")
        else:
            for source in sources:
                validate_source(source_root, source, path, report)
    else:
        citations = extension.get("citations")
        if not isinstance(citations, list) or not citations or not all(
            isinstance(item, str) and item.strip() for item in citations
        ):
            report.error(path, "reference concepts require a non-empty projectstate.citations list")
        parse_timestamp(extension.get("last_checked_at"), "projectstate.last_checked_at", path, report)


def validate_bundle(bundle: Path, source_root: Path) -> Report:
    report = Report(bundle=str(bundle), source_root=str(source_root))
    markdown_files: list[Path] = []
    casefold_paths: dict[str, Path] = {}
    try:
        entries = sorted(bundle.rglob("*"))
    except OSError as exc:
        report.error(bundle, f"cannot enumerate bundle: {exc}")
        return report
    for path in entries:
        relative = path.relative_to(bundle)
        try:
            normalize_relative_path(relative.as_posix())
        except UnsafePathError as exc:
            report.error(relative, str(exc))
        if path.is_symlink():
            report.error(relative, "symlink components are not allowed in an OKF bundle")
            continue
        if not path.is_file() or path.suffix.lower() != ".md":
            continue
        folded = relative.as_posix().casefold()
        previous = casefold_paths.get(folded)
        if previous is not None and previous != relative:
            report.error(relative, f"case-colliding concept path with {previous}")
        casefold_paths[folded] = relative
        markdown_files.append(path)

    for path in markdown_files:
        relative = path.relative_to(bundle)
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            report.error(relative, f"cannot read UTF-8 Markdown: {exc}")
            continue
        if path.name in {"index.md", "log.md"}:
            check_index(path, bundle, text, report)
            continue
        report.concepts += 1
        try:
            frontmatter, body = parse_frontmatter(text, path)
        except (ProjectStateYamlError, UnicodeDecodeError) as exc:
            report.error(relative, str(exc))
            continue
        concept_type = frontmatter.get("type")
        if not isinstance(concept_type, str) or not concept_type.strip():
            report.error(relative, "concept frontmatter requires a non-empty type")
        check_governance(relative, frontmatter, source_root, report)
        check_text_hygiene(text, relative, report)
        check_links(bundle, path, body, report)

    directories = {path.parent for path in markdown_files}
    for directory in sorted(directories):
        if not (directory / "index.md").exists():
            report.warning(directory.relative_to(bundle) or ".", "directory has concepts but no index.md")
    return report


def output_report(report: Report, *, as_json: bool = False) -> None:
    payload = {
        "bundle": report.bundle,
        "source_root": report.source_root,
        "okf_version": OKF_VERSION,
        "okf_spec_commit": OKF_SPEC_COMMIT,
        "concepts": report.concepts,
        "warnings": [finding.__dict__ for finding in report.warnings],
        "errors": [finding.__dict__ for finding in report.errors],
        "stale": [finding.__dict__ for finding in report.stale],
        "status": "failed" if report.errors else "passed",
    }
    if as_json:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return
    print(f"OKF v{OKF_VERSION} validation: {payload['status']}")
    print(f"Bundle: {report.bundle}")
    print(f"Concepts: {report.concepts}")
    for label, findings in (("ERROR", report.errors), ("WARNING", report.warnings)):
        for finding in findings:
            print(f"{label} {finding.path}: {finding.message}")
    if not report.errors:
        print("Base OKF conformance and ProjectState governance checks passed.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate an OKF v0.1 bundle and ProjectState governance metadata")
    parser.add_argument("bundle", help="Bundle directory, normally knowledge/")
    parser.add_argument("--source-root", help="Repository root used to resolve projectstate.sources paths")
    parser.add_argument("--strict", action="store_true", help="Retained for explicit governance intent; base warnings remain non-fatal")
    parser.add_argument("--json", action="store_true", dest="as_json", help="Emit a machine-readable report")
    args = parser.parse_args(argv)
    try:
        bundle = safe_root_path(args.bundle, must_exist=True)
        source_root = safe_root_path(args.source_root or bundle.parent, must_exist=True)
    except (ContractError, OSError) as exc:
        print(f"OKF validation failed before reading bundle: {exc}", file=sys.stderr)
        return 2
    report = validate_bundle(bundle, source_root)
    output_report(report, as_json=args.as_json)
    return 1 if report.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
