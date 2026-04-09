#!/usr/bin/env python3
"""Validate the State-Driven Development Template docs."""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

RULES = {
    "AGENTS.md": {"max_lines": 1000, "must_contain": ["repo_mode:", "bootstrap", "operating"]},
    "STATUS.md": {"max_lines": 120, "max_headline_bullets": 7},
    "PROJECT_STATE.yaml": {"max_lines": 900, "forbidden": ["DESIGN.md"]},
    "PROJECT_DNA.yaml": {"max_lines": 1000, "forbidden": ["DESIGN.md"]},
    "NEXT_ACTIONS.md": {"max_lines": 180, "max_items": 10, "forbidden": ["COMPLETE", "REMOVED"]},
    "BACKLOG.md": {"max_lines": 250, "max_now_items": 10},
}

README_REQUIRED_SECTIONS = [
    "## Quick Start",
    "## Git Safety",
    "## First 10 Minutes",
    "## Safe Initialization Paths",
    "## Bootstrap Completion Gate",
    "## Setting Up The AI CTO Agent",
    "## Workflow Diagram",
    "## Non-Trivial Work",
    "## Common Failure Modes",
    "## Single-Agent Fallback",
    "## Example Flow",
    "## Validation",
    "## Publishing A Downstream Project",
]

TEMPLATE_ASSET_PATHS = [
    "scripts/init_template.py",
    "scripts/check_state_docs.py",
    "prompts/CTO_SESSION_PROMPT.md",
    "prompts/CODING_AGENT_PROMPT_GUIDE.md",
    "prompts/BOOTSTRAP_INTAKE_PROMPT.md",
    ".github/workflows/validate.yml",
    ".github/pull_request_template.md",
    ".github/ISSUE_TEMPLATE/config.yml",
    ".github/ISSUE_TEMPLATE/bootstrap-init.md",
    ".github/ISSUE_TEMPLATE/bug-regression.md",
    ".github/ISSUE_TEMPLATE/backlog-item.md",
    ".github/ISSUE_TEMPLATE/architecture-change.md",
]

PR_TEMPLATE_REQUIRED_SECTIONS = [
    "## What changed",
    "## Verification",
    "## Evidence refs",
    "## Contract checks",
    "## What remains unproven",
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

    if path.name == "BACKLOG.md":
        now_items = backlog_now_count(text)
        if now_items > rules.get("max_now_items", 10**9):
            issues.append(f"NOW section has {now_items} items, max is {rules['max_now_items']}")

    for forbidden in rules.get("forbidden", []):
        if re.search(rf"\b{re.escape(forbidden)}\b", text):
            issues.append(f"Found forbidden text '{forbidden}' in {path.name}")

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

    if "--force-overwrite" not in text:
        issues.append("README must explain the force-overwrite safeguard for conflicting existing targets")

    if "DESIGN.md" in text:
        issues.append("README must not reference missing DESIGN.md guidance")

    if "does not have direct access to the repo or state files" not in text:
        issues.append("README must explain that the CTO lane only sees pasted repo context")

    if "fresh coding-agent session" not in text:
        issues.append("README must explain the fresh coding-agent session loop")

    if "real `BACKLOG.md`, not a placeholder" not in text:
        issues.append("README must explain that bootstrap needs a real backlog before operating mode")

    if "backlog slice" not in text:
        issues.append("README must explain that operating mode is driven by backlog slices")

    return issues


def check_template_assets(root: Path) -> list[str]:
    issues: list[str] = []

    for relpath in TEMPLATE_ASSET_PATHS:
        if not (root / relpath).exists():
            issues.append(f"Missing required template asset: {relpath}")

    pr_template = root / ".github" / "pull_request_template.md"
    if pr_template.exists():
        text = pr_template.read_text()
        for section in PR_TEMPLATE_REQUIRED_SECTIONS:
            if section not in text:
                issues.append(f"Pull request template missing section: {section}")

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
        readme_text = readme.read_text()
        issues = check_readme(readme)
        if issues:
            failures.append(("README.md", issues))

        if "public template" in readme_text.lower() or "State-Driven Development Template" in readme_text:
            asset_issues = check_template_assets(root)
            if asset_issues:
                failures.append(("template_assets", asset_issues))

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

        print("\n📄 template assets")
        current = next((issues for name, issues in failures if name == "template_assets"), [])
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
