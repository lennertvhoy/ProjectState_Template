#!/usr/bin/env python3
"""Validate the truth-first workflow docs."""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

RULES = {
    "AGENTS.md": {"max_lines": 1000, "must_contain": ["repo_mode:", "bootstrap", "operating"]},
    "STATUS.md": {"max_lines": 120, "max_headline_bullets": 7},
    "PROJECT_STATE.yaml": {"max_lines": 900},
    "PROJECT_DNA.yaml": {"max_lines": 1000},
    "NEXT_ACTIONS.md": {"max_lines": 180, "max_items": 10, "forbidden": ["COMPLETE", "REMOVED"]},
    "BACKLOG.md": {"max_lines": 250, "max_now_items": 10},
}

README_REQUIRED_SECTIONS = [
    "## Quick Start",
    "## Git Safety",
    "## First 10 Minutes",
    "## Setting Up The AI CTO Agent",
    "## Workflow Diagram",
    "## Non-Trivial Work",
    "## Common Failure Modes",
    "## Single-Agent Fallback",
    "## Example Flow",
]


def count_nonempty_lines(text: str) -> int:
    return sum(1 for line in text.splitlines() if line.strip())


def status_bullet_count(text: str) -> int:
    match = re.search(r"^##\s+Snapshot\s*$([\s\S]*?)(?=^## |\Z)", text, re.MULTILINE)
    if not match:
        return 0
    section = match.group(1)
    return sum(1 for line in section.splitlines() if line.lstrip().startswith("- "))


def next_actions_count(text: str) -> int:
    match = re.search(r"^##\s+Active Work\s*$([\s\S]*?)(?=^## |\Z)", text, re.MULTILINE)
    if not match:
        return 0
    section = match.group(1)
    return sum(1 for line in section.splitlines() if line.startswith("### "))


def backlog_now_count(text: str) -> int:
    match = re.search(r"^##\s+NOW\s*$([\s\S]*?)(?=^## |\Z)", text, re.MULTILINE)
    if not match:
        return 0
    section = match.group(1)
    return sum(1 for line in section.splitlines() if line.lstrip().startswith("- "))


def check_file(path: Path) -> list[str]:
    text = path.read_text()
    rules = RULES[path.name]
    issues: list[str] = []

    line_count = count_nonempty_lines(text)
    if line_count > rules.get("max_lines", 10**9):
        issues.append(f"Line count {line_count} exceeds max {rules['max_lines']}")

    if path.name == "STATUS.md":
        bullets = status_bullet_count(text)
        if bullets > rules.get("max_headline_bullets", 10**9):
            issues.append(f"Snapshot has {bullets} bullets, max is {rules['max_headline_bullets']}")

    if path.name == "NEXT_ACTIONS.md":
        items = next_actions_count(text)
        if items > rules.get("max_items", 10**9):
            issues.append(f"Found {items} active queue items, max is {rules['max_items']}")
        for forbidden in rules.get("forbidden", []):
            if re.search(rf"\b{re.escape(forbidden)}\b", text):
                issues.append(f"Found forbidden status '{forbidden}' in NEXT_ACTIONS.md")

    if path.name == "BACKLOG.md":
        now_items = backlog_now_count(text)
        if now_items > rules.get("max_now_items", 10**9):
            issues.append(f"NOW section has {now_items} items, max is {rules['max_now_items']}")

    for required in rules.get("must_contain", []):
        if required not in text:
            issues.append(f"Missing required text: {required}")

    return issues


def check_readme(path: Path) -> list[str]:
    text = path.read_text()
    issues: list[str] = []

    for required in README_REQUIRED_SECTIONS:
        if required not in text:
            issues.append(f"Missing required README section: {required}")

    if "prompts/CTO_SESSION_PROMPT.md" not in text:
        issues.append("README must reference prompts/CTO_SESSION_PROMPT.md")

    if "ChatGPT, Claude, Gemini" not in text:
        issues.append("README must explicitly mention ChatGPT, Claude, Gemini")

    if "rm -rf .git" not in text or "git remote -v" not in text:
        issues.append("README must explain how to remove inherited git metadata and verify the remote before first push")

    return issues


def main() -> int:
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT
    print("============================================================")
    print("DOCUMENTATION HYGIENE CHECK")
    print("============================================================")

    failures: list[tuple[str, list[str]]] = []
    for filename in RULES:
        path = root / filename
        if not path.exists():
            failures.append((filename, [f"File not found: {filename}"]))
            continue
        issues = check_file(path)
        if issues:
            failures.append((filename, issues))

    readme = root / "README.md"
    if readme.exists():
        issues = check_readme(readme)
        if issues:
            failures.append(("README.md", issues))

    for filename in RULES:
        print(f"\n📄 {filename}")
        current = next((issues for name, issues in failures if name == filename), [])
        if current:
            for issue in current:
                print(f"  ❌ {issue}")
        else:
            print("  ✅ All checks passed")

    if readme.exists():
        print("\n📄 README.md")
        current = next((issues for name, issues in failures if name == "README.md"), [])
        if current:
            for issue in current:
                print(f"  ❌ {issue}")
        else:
            print("  ✅ All checks passed")

    print("\n============================================================")
    if failures:
        print(f"FAILED: {sum(len(issues) for _, issues in failures)} issue(s) found")
        print()
        print("Summary:")
        for filename, issues in failures:
            for issue in issues:
                print(f"  - {filename}: {issue}")
        return 1

    print("PASSED: All state documentation checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
