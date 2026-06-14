#!/usr/bin/env python3
"""Validate StateDD workflow docs and bootstrap readiness."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKLOG_ID_RE = re.compile(r"\[(BL-\d{3})\]")
NEXT_ACTION_ID_RE = re.compile(r"^###\s+P\d+\s+\[(BL-\d{3})\]\s+.+$", re.MULTILINE)
WORKLOG_ENTRY_RE = re.compile(r"^##\s+\d{4}-\d{2}-\d{2}\s+-\s+.+$", re.MULTILINE)
EVIDENCE_ENTRY_RE = re.compile(r"^##\s+EV-\d{4}-\d{2}-\d{2}-\d{3}:\s+.+$", re.MULTILINE)
PINNED_ACTION_RE = re.compile(r"uses:\s+actions/[^@\s]+@([0-9a-f]{40})")
MUTABLE_ACTION_RE = re.compile(r"uses:\s+actions/[^@\s]+@([^\s#]+)")

RULES = {
    "AGENTS.md": {"max_lines": 1000, "must_contain": ["repo_mode:", "bootstrap", "operating"]},
    "STATUS.md": {"max_lines": 120, "max_headline_bullets": 7},
    "PROJECT_STATE.yaml": {"max_lines": 900, "forbidden": ["DESIGN.md"]},
    "PROJECT_DNA.yaml": {"max_lines": 1000, "forbidden": ["DESIGN.md"]},
    "NEXT_ACTIONS.md": {"max_lines": 220, "max_items": 10, "forbidden": ["COMPLETE", "REMOVED"]},
    "BACKLOG.md": {"max_lines": 260, "max_now_items": 10},
}

README_REQUIRED_SECTIONS = [
    "## Quick Start",
    "## Git Safety",
    "## Setup Paths",
    "## Adopt An Existing Repo",
    "## Agent Read Order",
    "## Bootstrap Completion Gate",
    "## Setting Up The AI CTO Agent",
    "## Tool And Model Routing",
    "## Prompt Files",
    "## Final Handoff Template",
    "## Runtime Identity Proof",
    "## Acceptance Freezes",
    "## Search Honesty",
    "## Workflow Diagram",
    "## Non-Trivial Work",
    "## Common Failure Modes",
    "## Validation",
    "## Executable Audit And State Doctor",
    "## Slice Contracts And Claim Ledgers",
    "## Schema Ownership",
    "## ADRs",
    "## CTO Review Checklist",
    "## Human Override Rule",
    "## Publishing A Downstream Project",
]

TEMPLATE_ASSET_PATHS = [
    "scripts/init_template.py",
    "scripts/check_state_docs.py",
    "scripts/statedd_handoff.py",
    "scripts/statedd_audit.py",
    "scripts/statedd_doctor.py",
    "scripts/test_init_template.py",
    "LICENSE",
    "LICENSE_FAQ.md",
    "prompts/CTO_SESSION_PROMPT.md",
    "prompts/CODING_AGENT_STARTUP_PROMPT.md",
    "prompts/OPENCODE_STARTUP_PROMPT.md",
    "prompts/BOOTSTRAP_INTAKE_PROMPT.md",
    "prompts/TOOL_MODEL_ROUTING_GUIDE.md",
    "prompts/FINAL_HANDOFF_TEMPLATE.md",
    "prompts/RUNTIME_IDENTITY_CHECKLIST.md",
    "prompts/ACCEPTANCE_FREEZE_TEMPLATE.md",
    "prompts/SLICE_CONTRACT_TEMPLATE.md",
    "prompts/EVIDENCE_README_TEMPLATE.md",
    "prompts/SCHEMA_OWNERSHIP_TEMPLATE.md",
    "prompts/SUBAGENT_REVIEW_TEMPLATE.md",
    "prompts/CTO_REVIEW_CHECKLIST.md",
    "docs/GETTING_STARTED_5_MIN.md",
    "docs/ACCEPTANCE_FREEZES.md",
    "docs/WORKFLOW_FOR_BEGINNERS.md",
    "docs/adr/README.md",
    "docs/adr/0000-adr-template.md",
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
    return sum(1 for line in match.group(1).splitlines() if line.lstrip().startswith("- "))


def next_actions_count(text: str) -> int:
    match = re.search(r"^##\s+Active Work\s*$([\s\S]*?)(?=^## |\Z)", text, re.MULTILINE)
    if not match:
        return 0
    return sum(1 for line in match.group(1).splitlines() if line.startswith("### "))


def backlog_now_count(text: str) -> int:
    match = re.search(r"^##\s+NOW\s*$([\s\S]*?)(?=^## |\Z)", text, re.MULTILINE)
    if not match:
        return 0
    return sum(1 for line in match.group(1).splitlines() if line.lstrip().startswith("- "))


def extract_backlog_ids(text: str) -> set[str]:
    return set(BACKLOG_ID_RE.findall(text))


def extract_next_action_ids(text: str) -> list[str]:
    return NEXT_ACTION_ID_RE.findall(text)


def detect_repo_mode(root: Path) -> str | None:
    agents = root / "AGENTS.md"
    if not agents.exists():
        return None
    text = agents.read_text(encoding="utf-8")
    match = re.search(r"^repo_mode:\s*(\w+)$", text, re.MULTILINE)
    return match.group(1) if match else None


def is_template_style_repo(root: Path) -> bool:
    readme = root / "README.md"
    project_state = root / "PROJECT_STATE.yaml"
    readme_text = readme.read_text(encoding="utf-8") if readme.exists() else ""
    project_state_text = project_state.read_text(encoding="utf-8") if project_state.exists() else ""

    if readme_text.startswith("# State Driven Development Template"):
        return True
    if "type: documentation_and_workflow_template" in project_state_text:
        return True
    if "type: project_template" in project_state_text and "## Quick Start" in readme_text:
        return True
    return False


def check_file(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
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
        if items and "backlog ID" not in text:
            issues.append("NEXT_ACTIONS.md must explain backlog ID linkage in queue rules")
        for heading in re.findall(r"^###\s+.+$", text, re.MULTILINE):
            if not NEXT_ACTION_ID_RE.match(heading):
                issues.append(f"Active item heading is missing the `### Pn [BL-001] ...` format: {heading}")

    if path.name == "BACKLOG.md":
        now_items = backlog_now_count(text)
        if now_items > rules.get("max_now_items", 10**9):
            issues.append(f"NOW section has {now_items} items, max is {rules['max_now_items']}")
        ids = extract_backlog_ids(text)
        if not ids:
            issues.append("BACKLOG.md must include stable backlog IDs like [BL-001]")

    for forbidden in rules.get("forbidden", []):
        if re.search(rf"\b{re.escape(forbidden)}\b", text):
            issues.append(f"Found forbidden text '{forbidden}' in {path.name}")

    for required in rules.get("must_contain", []):
        if required not in text:
            issues.append(f"Missing required text: {required}")

    return issues


def check_cross_file_rules(root: Path) -> list[str]:
    issues: list[str] = []
    backlog = root / "BACKLOG.md"
    next_actions = root / "NEXT_ACTIONS.md"
    if not backlog.exists() or not next_actions.exists():
        return issues

    backlog_ids = extract_backlog_ids(backlog.read_text(encoding="utf-8"))
    action_ids = extract_next_action_ids(next_actions.read_text(encoding="utf-8"))
    for backlog_id in action_ids:
        if backlog_id not in backlog_ids:
            issues.append(f"NEXT_ACTIONS.md references missing backlog ID {backlog_id}")
    return issues


def check_readme(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    issues: list[str] = []

    for required in README_REQUIRED_SECTIONS:
        if required not in text:
            issues.append(f"Missing required README section: {required}")

    required_phrases = [
        "prompts/CTO_SESSION_PROMPT.md",
        "prompts/CODING_AGENT_STARTUP_PROMPT.md",
        "prompts/OPENCODE_STARTUP_PROMPT.md",
        "prompts/TOOL_MODEL_ROUTING_GUIDE.md",
        "prompts/FINAL_HANDOFF_TEMPLATE.md",
        "docs/GETTING_STARTED_5_MIN.md",
        "scripts/statedd_handoff.py",
        "LICENSE_FAQ.md",
        "teaching/training rights are reserved",
        "ChatGPT, Claude, Gemini",
        "Tool And Model Routing",
        "model capabilities, pricing, context windows, or tool support",
        "rm -rf .git",
        "git remote -v",
        "--force-overwrite",
        "--bootstrap-gate",
        "new",
        "adopt",
        "does not have direct access to the repo or state files",
        "fresh coding-agent session",
        "real `BACKLOG.md`, not a placeholder",
        "backlog slice",
        "State Driven Development Template",
        "docs/evidence/",
        "scripts/test_init_template.py",
        "existing README preserved",
        "runtime identity",
        "acceptance freeze",
        "not currently locatable",
        "process or container",
        "statedd_audit.py",
        "statedd_doctor.py",
        "slice contract",
        "claim ledger",
        "schema ownership",
        "Human override used: yes",
        "implemented ≠ validated ≠ closure-grade ≠ accepted",
    ]
    for phrase in required_phrases:
        if phrase not in text:
            issues.append(f"README must mention: {phrase}")

    if "DESIGN.md" in text:
        issues.append("README must not reference missing DESIGN.md guidance")

    return issues


def check_template_assets(root: Path) -> list[str]:
    issues: list[str] = []

    for relpath in TEMPLATE_ASSET_PATHS:
        if not (root / relpath).exists():
            issues.append(f"Missing required template asset: {relpath}")

    pr_template = root / ".github" / "pull_request_template.md"
    if pr_template.exists():
        text = pr_template.read_text(encoding="utf-8")
        for section in PR_TEMPLATE_REQUIRED_SECTIONS:
            if section not in text:
                issues.append(f"Pull request template missing section: {section}")

    final_handoff = root / "prompts" / "FINAL_HANDOFF_TEMPLATE.md"
    if final_handoff.exists():
        handoff_text = final_handoff.read_text(encoding="utf-8")
        for phrase in ("repo path", "branch", "process/container", "port/base URL", "rebuilt in this slice"):
            if phrase not in handoff_text:
                issues.append(f"Final handoff template missing phrase: {phrase}")

    cto_prompt = root / "prompts" / "CTO_SESSION_PROMPT.md"
    if cto_prompt.exists():
        cto_text = cto_prompt.read_text(encoding="utf-8")
        for phrase in ("TOOL_MODEL_ROUTING_GUIDE.md", "recommended tool/model/settings", "not proven"):
            if phrase not in cto_text:
                issues.append(f"CTO session prompt missing phrase: {phrase}")

    routing_guide = root / "prompts" / "TOOL_MODEL_ROUTING_GUIDE.md"
    if routing_guide.exists():
        routing_text = routing_guide.read_text(encoding="utf-8")
        for phrase in ("Recommended route", "Paste-ready prompt", "not proven", "pricing"):
            if phrase not in routing_text:
                issues.append(f"Tool/model routing guide missing phrase: {phrase}")

    opencode_prompt = root / "prompts" / "OPENCODE_STARTUP_PROMPT.md"
    if opencode_prompt.exists():
        opencode_text = opencode_prompt.read_text(encoding="utf-8")
        for phrase in ("OpenCode", "AGENTS.md", "statedd_handoff.py", "not proven"):
            if phrase not in opencode_text:
                issues.append(f"OpenCode startup prompt missing phrase: {phrase}")

    getting_started = root / "docs" / "GETTING_STARTED_5_MIN.md"
    if getting_started.exists():
        getting_started_text = getting_started.read_text(encoding="utf-8")
        for phrase in ("5 Minutes", "OPENCODE_STARTUP_PROMPT.md", "check_state_docs.py --bootstrap-gate"):
            if phrase not in getting_started_text:
                issues.append(f"5-minute getting started guide missing phrase: {phrase}")

    handoff_helper = root / "scripts" / "statedd_handoff.py"
    if handoff_helper.exists():
        handoff_helper_text = handoff_helper.read_text(encoding="utf-8")
        for phrase in ("StateDD Handoff Snapshot", "repo path", "not proven", "--test-command"):
            if phrase not in handoff_helper_text:
                issues.append(f"Handoff helper missing phrase: {phrase}")

    license_file = root / "LICENSE"
    if license_file.exists():
        license_text = license_file.read_text(encoding="utf-8")
        for phrase in (
            "Teaching Rights Reserved",
            "commercial or profit-making purposes",
            "does not grant permission to use the Software",
            "ordinary explanations",
            "incidental to permitted use",
        ):
            if phrase not in license_text:
                issues.append(f"LICENSE missing phrase: {phrase}")

    license_faq = root / "LICENSE_FAQ.md"
    if license_faq.exists():
        license_faq_text = license_faq.read_text(encoding="utf-8")
        for phrase in ("commercial or client projects", "Can I teach this workflow?", "No, not without prior written permission"):
            if phrase not in license_faq_text:
                issues.append(f"License FAQ missing phrase: {phrase}")

    runtime_identity = root / "prompts" / "RUNTIME_IDENTITY_CHECKLIST.md"
    if runtime_identity.exists():
        runtime_text = runtime_identity.read_text(encoding="utf-8")
        for phrase in ("process or container", "not currently locatable", "duplicate dev servers", "HEAD commit"):
            if phrase not in runtime_text:
                issues.append(f"Runtime identity checklist missing phrase: {phrase}")

    acceptance_freeze = root / "prompts" / "ACCEPTANCE_FREEZE_TEMPLATE.md"
    if acceptance_freeze.exists():
        freeze_text = acceptance_freeze.read_text(encoding="utf-8")
        for phrase in ("repo path", "head", "process/container", "regression guard"):
            if phrase not in freeze_text:
                issues.append(f"Acceptance freeze template missing phrase: {phrase}")

    slice_contract = root / "prompts" / "SLICE_CONTRACT_TEMPLATE.md"
    if slice_contract.exists():
        slice_text = slice_contract.read_text(encoding="utf-8")
        for phrase in ("non_goals", "acceptance_criteria", "Human override used: yes"):
            if phrase not in slice_text:
                issues.append(f"Slice contract template missing phrase: {phrase}")

    evidence_readme = root / "prompts" / "EVIDENCE_README_TEMPLATE.md"
    if evidence_readme.exists():
        evidence_text = evidence_readme.read_text(encoding="utf-8")
        for phrase in ("Claims", "Verification Log", "Closure State"):
            if phrase not in evidence_text:
                issues.append(f"Evidence README template missing phrase: {phrase}")

    schema_ownership = root / "prompts" / "SCHEMA_OWNERSHIP_TEMPLATE.md"
    if schema_ownership.exists():
        schema_text = schema_ownership.read_text(encoding="utf-8")
        for phrase in ("No schema may exist only in prose", "schemaVersion", "MIGRATION"):
            if phrase not in schema_text:
                issues.append(f"Schema ownership template missing phrase: {phrase}")

    subagent_review = root / "prompts" / "SUBAGENT_REVIEW_TEMPLATE.md"
    if subagent_review.exists():
        subagent_text = subagent_review.read_text(encoding="utf-8")
        for phrase in ("Verdict:", "Findings:", "Required fixes:", "Confidence:"):
            if phrase not in subagent_text:
                issues.append(f"Subagent review template missing phrase: {phrase}")

    cto_review = root / "prompts" / "CTO_REVIEW_CHECKLIST.md"
    if cto_review.exists():
        cto_text = cto_review.read_text(encoding="utf-8")
        for phrase in ("Closure verdict:", "Missing proof:", "Contradictions:", "Next best slice:"):
            if phrase not in cto_text:
                issues.append(f"CTO review checklist missing phrase: {phrase}")

    workflow = root / ".github" / "workflows" / "validate.yml"
    if workflow.exists():
        workflow_text = workflow.read_text(encoding="utf-8")
        for ref in MUTABLE_ACTION_RE.findall(workflow_text):
            if not re.fullmatch(r"[0-9a-f]{40}", ref):
                issues.append(f"GitHub Action reference must be pinned to a full SHA, found: {ref}")
        if not PINNED_ACTION_RE.search(workflow_text):
            issues.append("GitHub workflow must pin action references to full SHAs")
        if "scripts/test_init_template.py" not in workflow_text:
            issues.append("GitHub workflow must run scripts/test_init_template.py")

    return issues


def check_bootstrap_gate(root: Path) -> list[str]:
    mode = detect_repo_mode(root)
    if mode != "bootstrap":
        return []

    issues: list[str] = []
    project_state = (root / "PROJECT_STATE.yaml").read_text(encoding="utf-8") if (root / "PROJECT_STATE.yaml").exists() else ""
    next_actions = (root / "NEXT_ACTIONS.md").read_text(encoding="utf-8") if (root / "NEXT_ACTIONS.md").exists() else ""
    backlog = (root / "BACKLOG.md").read_text(encoding="utf-8") if (root / "BACKLOG.md").exists() else ""
    worklog = (root / "WORKLOG.md").read_text(encoding="utf-8") if (root / "WORKLOG.md").exists() else ""
    evidence = (root / "docs" / "EVIDENCE_LOG.md").read_text(encoding="utf-8") if (root / "docs" / "EVIDENCE_LOG.md").exists() else ""

    if "system_investigated: false" in project_state:
        issues.append("Bootstrap gate failed: system investigation is still false in PROJECT_STATE.yaml")
    if "repo_investigated: false" in project_state:
        issues.append("Bootstrap gate failed: repo investigation is still false in PROJECT_STATE.yaml")
    if next_actions_count(next_actions) == 0:
        issues.append("Bootstrap gate failed: NEXT_ACTIONS.md does not contain a real active queue")
    if "No active work yet." in next_actions or "No active template maintenance work is queued right now." in next_actions:
        issues.append("Bootstrap gate failed: NEXT_ACTIONS.md is still placeholder text")
    if len(extract_backlog_ids(backlog)) < 3:
        issues.append("Bootstrap gate failed: BACKLOG.md does not contain enough stable backlog IDs")
    if "Establish baseline truth." in backlog or "Transition to operating mode." in backlog:
        issues.append("Bootstrap gate failed: BACKLOG.md is still placeholder-level")
    if not WORKLOG_ENTRY_RE.search(worklog):
        issues.append("Bootstrap gate failed: WORKLOG.md does not record any dated bootstrap history")
    if not EVIDENCE_ENTRY_RE.search(evidence):
        issues.append("Bootstrap gate failed: docs/EVIDENCE_LOG.md does not record any evidence entries")
    if count_nonempty_lines(project_state) < 80:
        issues.append("Bootstrap gate failed: PROJECT_STATE.yaml is still too thin to represent a truthful baseline")

    return issues


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate StateDD workflow docs and bootstrap readiness")
    parser.add_argument("root", nargs="?", default=str(ROOT), help="Repo root to validate")
    parser.add_argument(
        "--bootstrap-gate",
        action="store_true",
        help="Fail when a bootstrap repo is still too incomplete to be considered a real baseline",
    )
    return parser.parse_args(argv[1:])


def print_failure_block(label: str, issues: list[str]) -> None:
    print(f"\n📄 {label}")
    if issues:
        for issue in issues:
            print(f"  ❌ {issue}")
    else:
        print("  ✅ All checks passed")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv)
    root = Path(args.root).resolve()

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

    cross_file_issues = check_cross_file_rules(root)
    if cross_file_issues:
        failures.append(("cross_file_rules", cross_file_issues))

    readme = root / "README.md"
    template_style_repo = is_template_style_repo(root)
    if readme.exists() and template_style_repo:
        readme_text = readme.read_text(encoding="utf-8")
        issues = check_readme(readme)
        if issues:
            failures.append(("README.md", issues))

        asset_issues = check_template_assets(root)
        if asset_issues:
            failures.append(("template_assets", asset_issues))

    bootstrap_issues: list[str] = []
    if args.bootstrap_gate:
        bootstrap_issues = check_bootstrap_gate(root)
        if bootstrap_issues:
            failures.append(("bootstrap_gate", bootstrap_issues))

    for filename in RULES:
        current = next((issues for name, issues in failures if name == filename), [])
        print_failure_block(filename, current)

    print_failure_block("cross_file_rules", next((issues for name, issues in failures if name == "cross_file_rules"), []))

    if readme.exists() and template_style_repo:
        print_failure_block("README.md", next((issues for name, issues in failures if name == "README.md"), []))
        print_failure_block("template assets", next((issues for name, issues in failures if name == "template_assets"), []))

    if args.bootstrap_gate:
        print_failure_block("bootstrap gate", bootstrap_issues)

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
