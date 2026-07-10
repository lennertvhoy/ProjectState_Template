#!/usr/bin/env python3
"""Check StateDD template spec-version alignment."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION_RE = re.compile(r"statedd-template-v\d+")

REQUIRED_VERSION_FILES = (
    "AGENTS.md",
    "PROJECT_STATE.yaml",
    "PROJECT_DNA.yaml",
    "PROJECT_ADAPTER.yaml",
    "scripts/init_template.py",
)

TEMPLATE_REPOSITORY_VERSION_FILES = (
    "README.md",
    "CHANGELOG.md",
    "docs/UPGRADING.md",
)

VALID_REPO_ROLES = {"template_repository", "downstream_project"}

SCAN_ROOT_FILES = (
    "AGENTS.md",
    "STATUS.md",
    "PROJECT_STATE.yaml",
    "PROJECT_DNA.yaml",
    "PROJECT_ADAPTER.yaml",
    "NEXT_ACTIONS.md",
    "BACKLOG.md",
    "README.md",
)

SCAN_DIRS = ("docs", "prompts", "scripts", ".github")
TEXT_SUFFIXES = {".md", ".py", ".yaml", ".yml", ".txt", ".json", ".toml"}
SKIP_PARTS = {".git", "__pycache__", ".cache", ".pytest_cache", "statedd_version_check.py"}
HISTORICAL_PATHS = {
    "WORKLOG.md",
    "docs/EVIDENCE_LOG.md",
    "docs/ACCEPTANCE_FREEZES.md",
    "docs/incidents",
    "docs/RELEASE_NOTES_statedd-template-v4.md",
}
HISTORICAL_DIRS = {
    "docs/evidence",
    "docs/incidents",
}


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def parse_front_matter(path: Path) -> tuple[dict[str, str] | None, list[str]]:
    if not path.exists():
        return None, [f"{path.name} is missing; repository role is not proven"]
    try:
        lines = read_text(path).splitlines()
    except UnicodeDecodeError as exc:
        return None, [f"{path.name} is unreadable: {exc}"]

    if not lines or lines[0].strip() != "---":
        return None, [f"{path.name} is missing YAML front matter"]

    try:
        closing_index = next(
            index for index, line in enumerate(lines[1:], start=1) if line.strip() == "---"
        )
    except StopIteration:
        return None, [f"{path.name} has unterminated YAML front matter"]

    values: dict[str, str] = {}
    issues: list[str] = []
    for lineno, line in enumerate(lines[1:closing_index], start=2):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if line[0].isspace() or ":" not in line:
            issues.append(f"{path.name} front matter line {lineno} is not a top-level key/value")
            continue
        key, raw_value = line.split(":", 1)
        key = key.strip()
        raw_value = raw_value.strip()
        if key in values:
            issues.append(f"{path.name} front matter repeats key {key!r}")
            continue
        if raw_value.startswith('"'):
            try:
                parsed_value = json.loads(raw_value)
            except json.JSONDecodeError as exc:
                issues.append(f"{path.name} front matter line {lineno} has invalid quoted value: {exc.msg}")
                continue
        elif raw_value.startswith("'") and raw_value.endswith("'"):
            parsed_value = raw_value[1:-1].replace("''", "'")
        else:
            parsed_value = raw_value.split(" #", 1)[0].strip()
        if not isinstance(parsed_value, str):
            issues.append(f"{path.name} front matter key {key!r} must have a scalar string value")
            continue
        values[key] = parsed_value

    return values, issues


def repository_role(root: Path) -> tuple[str | None, list[str]]:
    values, issues = parse_front_matter(root / "AGENTS.md")
    if values is None:
        return None, issues
    role = values.get("repo_role")
    if role not in VALID_REPO_ROLES:
        expected = ", ".join(sorted(VALID_REPO_ROLES))
        issues.append(f"AGENTS.md repo_role must be one of {expected}; got {role or 'not proven'}")
        return None, issues
    return role, issues


def expected_version(root: Path) -> tuple[str | None, list[str]]:
    version_file = root / "VERSION"
    if not version_file.exists():
        return None, ["VERSION file is missing"]
    try:
        version = read_text(version_file).strip()
    except UnicodeDecodeError as exc:
        return None, [f"VERSION file is unreadable: {exc}"]
    if not VERSION_RE.fullmatch(version):
        return None, [f"VERSION must look like statedd-template-vN, got: {version!r}"]
    return version, []


def rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def is_historical_path(relpath: str) -> bool:
    if relpath in HISTORICAL_PATHS:
        return True
    return any(relpath == directory or relpath.startswith(f"{directory}/") for directory in HISTORICAL_DIRS)


def text_files_to_scan(root: Path) -> list[Path]:
    paths: set[Path] = set()
    for relpath in SCAN_ROOT_FILES:
        path = root / relpath
        if path.exists():
            paths.add(path)
    for dirname in SCAN_DIRS:
        directory = root / dirname
        if not directory.exists():
            continue
        for path in directory.rglob("*"):
            if not path.is_file():
                continue
            if any(part in SKIP_PARTS for part in path.relative_to(root).parts):
                continue
            relpath = rel(path, root)
            if is_historical_path(relpath):
                continue
            if path.suffix.lower() in TEXT_SUFFIXES:
                paths.add(path)
    return sorted(paths)


def check_required_files(root: Path, version: str, role: str | None) -> list[str]:
    issues: list[str] = []
    required = list(REQUIRED_VERSION_FILES)
    if role == "template_repository":
        required.extend(TEMPLATE_REPOSITORY_VERSION_FILES)

    for relpath in required:
        path = root / relpath
        if not path.exists():
            issues.append(f"{relpath} is required to carry {version} but is missing")
            continue
        try:
            text = read_text(path)
        except UnicodeDecodeError as exc:
            issues.append(f"{relpath} is unreadable: {exc}")
            continue
        versions = set(VERSION_RE.findall(text))
        if version not in versions:
            issues.append(f"{relpath} does not mention canonical version {version}")
    return issues


def check_conflicting_versions(root: Path, version: str) -> list[str]:
    issues: list[str] = []
    for path in text_files_to_scan(root):
        relpath = rel(path, root)
        try:
            text = read_text(path)
        except UnicodeDecodeError as exc:
            issues.append(f"{relpath} is unreadable: {exc}")
            continue
        versions = sorted(set(VERSION_RE.findall(text)))
        unexpected = [found for found in versions if found != version]
        if unexpected:
            issues.append(f"{relpath} contains non-canonical version(s): {', '.join(unexpected)}")
    return issues


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check StateDD version alignment")
    parser.add_argument("root", nargs="?", default=str(ROOT), help="Repo root to validate")
    return parser.parse_args(argv[1:])


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv)
    root = Path(args.root).resolve()

    version, issues = expected_version(root)
    if version is not None:
        role, role_issues = repository_role(root)
        issues.extend(role_issues)
        issues.extend(check_required_files(root, version, role))
        issues.extend(check_conflicting_versions(root, version))

    print("StateDD Version Check")
    print(f"Root: {root}")
    print(f"Expected: {version or 'not proven'}")

    if issues:
        print("Result: fail")
        for issue in issues:
            print(f"- {issue}")
        return 1

    print("Result: pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
