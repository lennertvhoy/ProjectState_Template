#!/usr/bin/env python3
"""Validate StateDD workflow docs and bootstrap readiness."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

try:
    from statedd_generated_controls import confirmed_delivery_policy_refusal
    from statedd_validate_schema import StateDDYamlError, parse_yaml_text
except ModuleNotFoundError:  # pragma: no cover - module import path under pytest
    from scripts.statedd_generated_controls import confirmed_delivery_policy_refusal
    from scripts.statedd_validate_schema import StateDDYamlError, parse_yaml_text


ROOT = Path(__file__).resolve().parents[1]
BACKLOG_ID_RE = re.compile(r"\[(BL-(?:[A-Z][A-Za-z]*-)*\d{3})\]")
WORKLOG_BACKLOG_ID_RE = re.compile(r"(?:\[|\()(BL-(?:[A-Z][A-Za-z]*-)*\d{3})(?:\]|\))")
NEXT_ACTION_ID_RE = re.compile(r"^###\s+P\d+\s+\[(BL-(?:[A-Z][A-Za-z]*-)*\d{3})\]\s+.+$", re.MULTILINE)
TERMINAL_NEXT_ACTION_TITLE_RE = re.compile(
    r"^###\s+P\d+\s+\[(BL-(?:[A-Z][A-Za-z]*-)*\d{3})\]\s+"
    r"(?:accepted|closed|complete(?:d)?|merged)\b",
    re.IGNORECASE | re.MULTILINE,
)
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
    "VERSION",
    "CHANGELOG.md",
    "QUALITY_FIREWALL.md",
    "FAILURE_TAXONOMY.md",
    "INCIDENT_RESPONSE.md",
    "ANTI_BRITTLENESS_GUARD.md",
    "scripts/init_template.py",
    "scripts/check_state_docs.py",
    "scripts/statedd_version_check.py",
    "scripts/statedd_handoff.py",
    "scripts/statedd_audit.py",
    "scripts/statedd_doctor.py",
    "scripts/statedd_worktree_guard.py",
    "scripts/statedd_brittleness_check.py",
    "scripts/statedd_runtime_proof.py",
    "scripts/statedd_runtime_truth_check.py",
    "scripts/statedd_validate_schema.py",
    "scripts/test_init_template.py",
    "scripts/test_worktree_guard.py",
    "scripts/test_brittleness_check.py",
    "scripts/test_runtime_proof.py",
    "scripts/test_runtime_truth_check.py",
    "scripts/test_schema_validation.py",
    "scripts/statedd_evidence_pack.py",
    "scripts/statedd_upgrade.py",
    "scripts/statedd_browser_verify.py",
    "scripts/test_evidence_pack.py",
    "scripts/test_upgrade.py",
    "scripts/test_browser_verification.py",
    "scripts/statedd_remote_closure_finalizer.py",
    "scripts/test_remote_closure_finalizer.py",
    "scripts/statedd_post_merge_verify.py",
    "scripts/test_post_merge_verify.py",
    "EFFICIENCY_BUDGET.yaml",
    "scripts/statedd_efficiency_check.py",
    "scripts/test_efficiency_check.py",
    "schemas/project_state.schema.json",
    "schemas/project_dna.schema.json",
    "schemas/project_adapter.schema.json",
    "schemas/statedd_assets.schema.json",
    "schemas/runtime_identity.schema.json",
    "schemas/runtime_identity_v2.schema.json",
    "schemas/evidence_readme_contract.json",
    "schemas/evidence_manifest.schema.json",
    "schemas/final_handoff_contract.json",
    "schemas/browser_verification.schema.json",
    "schemas/examples/runtime_identity_not_required.json",
    "schemas/tests/README.md",
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
    "docs/failure_scans/TEMPLATE.md",
    "docs/incidents/README.md",
    "docs/quality_gates/README.md",
    "docs/quality_gates/ANTI_BRITTLENESS_GATE.md",
    "docs/UPGRADING.md",
    "docs/ADOPTION_PROFILES.md",
    "docs/ACCEPTANCE_FREEZES.md",
    "docs/BROWSER_VERIFICATION.md",
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

OPTIONAL_ASSETS_FOR_MINIMAL_PROFILE = {
    "docs/WORKFLOW_FOR_BEGINNERS.md",
    "docs/BOOTSTRAP_QUALITY.md",
}

VALID_REPO_ROLES = {"template_repository", "downstream_project"}
VALID_STATEDD_MODES = {"template-maintenance", "bootstrap", "operating"}
TERMINAL_WORKLOG_STATUSES = {
    "ACCEPTED",
    "CLOSED",
    "COMPLETE",
    "CLOSURE_GRADE_CI_VERIFIED",
    "MERGED_AND_VERIFIED",
    "MERGED_MAIN_CI_PASSING",
    "MERGED_MAIN_CI_VERIFIED",
}
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
RECONCILED_REMOTE_KEYS = {
    "reconciled_remote_truth",
    "remote_reconciliation",
    "remote_truth_reconciliation",
}
TERMINAL_PR_STATES = {"CLOSED", "MERGED"}
VERIFIED_CI_STATES = {"PASS", "PASSED", "SUCCESS", "VERIFIED"}
UNPROVEN_CI_RE = re.compile(
    r"\b(?:not\s+(?:yet\s+)?(?:proven|verified|run)|unproven|pending|unknown|failed)\b",
    re.IGNORECASE,
)


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


def extract_backlog_sections(text: str) -> dict[str, list[str]]:
    """Return mapping of section name -> list of backlog IDs found in that section."""
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for line in text.splitlines():
        heading = re.match(r"^##\s+(.+?)\s*$", line)
        if heading:
            current = heading.group(1).strip()
            sections.setdefault(current, [])
            continue
        if current is not None:
            ids = BACKLOG_ID_RE.findall(line)
            sections[current].extend(ids)
    return sections


def check_backlog_structure(text: str) -> list[str]:
    """Fail on duplicate second-level sections and duplicate backlog IDs."""
    issues: list[str] = []
    headings = re.findall(r"^##\s+(.+?)\s*$", text, re.MULTILINE)
    seen: dict[str, int] = {}
    for heading in headings:
        seen[heading] = seen.get(heading, 0) + 1
    for heading, count in seen.items():
        if count > 1:
            issues.append(f"Duplicate second-level section '## {heading}' appears {count} times")

    sections = extract_backlog_sections(text)
    id_locations: dict[str, list[str]] = {}
    for section, ids in sections.items():
        for bid in ids:
            id_locations.setdefault(bid, []).append(section)

    for bid, locations in id_locations.items():
        if len(locations) > 1:
            issues.append(
                f"Backlog ID {bid} appears in multiple sections: {', '.join(locations)}"
            )

    return issues


def extract_next_action_ids(text: str) -> list[str]:
    return NEXT_ACTION_ID_RE.findall(text)


def extract_status_open_failure_ids(text: str) -> set[str]:
    match = re.search(r"^##\s+Open P0/P1 Failures\s*$([\s\S]*?)(?=^##\s|\Z)", text, re.MULTILINE)
    return set(BACKLOG_ID_RE.findall(match.group(1))) if match else set()


def extract_terminal_worklog_ids(text: str) -> set[str]:
    terminal: set[str] = set()
    entries = re.split(r"(?=^##\s+)", text, flags=re.MULTILINE)
    for body in entries:
        if not body.startswith("## "):
            continue
        status_match = re.search(r"^\*\*Status:\*\*\s*([^\n]+)", body, re.MULTILINE)
        if not status_match:
            continue
        status = status_match.group(1).strip().upper().replace("-", "_").replace(" ", "_")
        if status in TERMINAL_WORKLOG_STATUSES:
            terminal.update(WORKLOG_BACKLOG_ID_RE.findall(body))
    return terminal


def extract_active_problems(project_state_text: str) -> tuple[dict[str, str], list[str]]:
    try:
        state = parse_yaml_text(project_state_text)
    except StateDDYamlError as exc:
        return {}, [f"PROJECT_STATE.yaml could not be parsed for lifecycle checks: {exc}"]
    if not isinstance(state, dict):
        return {}, ["PROJECT_STATE.yaml root must be a mapping for lifecycle checks"]
    raw_problems = state.get("active_problems", [])
    if not isinstance(raw_problems, list):
        return {}, ["PROJECT_STATE.yaml active_problems must be a list"]
    problems: dict[str, str] = {}
    issues: list[str] = []
    for item in raw_problems:
        if not isinstance(item, dict):
            issues.append("PROJECT_STATE.yaml active_problems entries must be mappings")
            continue
        problem_id = item.get("id")
        severity = item.get("severity")
        if not isinstance(problem_id, str):
            issues.append("PROJECT_STATE.yaml active problem is missing a string id")
            continue
        if problem_id in problems:
            issues.append(f"PROJECT_STATE.yaml repeats active problem ID {problem_id}")
            continue
        problems[problem_id] = severity if isinstance(severity, str) else "unknown"
    return problems, issues


def normalize_lifecycle_status(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"[^A-Z0-9]+", "_", value.strip().upper()).strip("_")


def parse_project_state(project_state_text: str) -> tuple[dict[str, Any], list[str]]:
    try:
        state = parse_yaml_text(project_state_text)
    except StateDDYamlError as exc:
        return {}, [f"PROJECT_STATE.yaml could not be parsed for semantic checks: {exc}"]
    if not isinstance(state, dict):
        return {}, ["PROJECT_STATE.yaml root must be a mapping for semantic checks"]
    return state, []


def walk_state(value: Any, path: tuple[str, ...] = ()) -> list[tuple[tuple[str, ...], Any]]:
    """Return every nested value with its structural path."""
    found: list[tuple[tuple[str, ...], Any]] = [(path, value)]
    if isinstance(value, dict):
        for key, nested in value.items():
            found.extend(walk_state(nested, (*path, str(key))))
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            found.extend(walk_state(nested, (*path, str(index))))
    return found


def state_remote_reconciliation(state: dict[str, Any]) -> dict[str, Any] | None:
    current_state = state.get("current_state")
    if not isinstance(current_state, dict):
        return None
    candidates = [
        value
        for key, value in current_state.items()
        if str(key).lower() in RECONCILED_REMOTE_KEYS and isinstance(value, dict)
    ]
    return candidates[0] if len(candidates) == 1 else None


def reconciled_pr_states(reconciliation: dict[str, Any] | None) -> dict[int, str]:
    if not isinstance(reconciliation, dict):
        return {}
    raw = reconciliation.get("pull_requests")
    states: dict[int, str] = {}
    records: list[tuple[Any, Any]] = []
    if isinstance(raw, list):
        records = [
            (item.get("number"), item.get("state"))
            for item in raw
            if isinstance(item, dict)
        ]
    elif isinstance(raw, dict):
        records = [
            (value.get("number", key), value.get("state"))
            if isinstance(value, dict)
            else (key, value)
            for key, value in raw.items()
        ]
    for raw_number, raw_state in records:
        try:
            number = int(str(raw_number).removeprefix("pr_").removeprefix("#"))
        except ValueError:
            continue
        state = normalize_lifecycle_status(raw_state)
        if number > 0 and state:
            states[number] = state
    return states


def reconciled_main_ci_verified(reconciliation: dict[str, Any] | None) -> bool:
    if not isinstance(reconciliation, dict):
        return False
    raw = reconciliation.get("main_ci") or reconciliation.get("default_branch_ci")
    if not isinstance(raw, dict):
        return False
    status = normalize_lifecycle_status(raw.get("status") or raw.get("state"))
    evidence = raw.get("evidence") or raw.get("evidence_ref") or raw.get("handoff")
    return status in VERIFIED_CI_STATES and isinstance(evidence, str) and bool(evidence.strip())


def markdown_section(text: str, heading: str) -> str:
    match = re.search(
        rf"^##\s+{re.escape(heading)}\s*$([\s\S]*?)(?=^##\s+|\Z)",
        text,
        re.MULTILINE,
    )
    return match.group(1) if match else ""


def check_live_state_semantics(
    state: dict[str, Any],
    *,
    status_text: str,
    next_actions_text: str,
) -> list[str]:
    """Validate stable live truth without binding files to their containing commit."""
    issues: list[str] = []
    raw_active = state.get("active_problems")
    active = raw_active if isinstance(raw_active, list) else []
    active_records = [item for item in active if isinstance(item, dict)]
    active_p0_ids = {
        str(item.get("id"))
        for item in active_records
        if str(item.get("severity", "")).upper() == "P0"
    }
    terminal_active_ids: set[str] = set()
    for item in active_records:
        problem_id = item.get("id")
        lifecycle = normalize_lifecycle_status(item.get("status"))
        if isinstance(problem_id, str) and lifecycle in TERMINAL_ACTIVE_PROBLEM_STATUSES:
            terminal_active_ids.add(problem_id)
            issues.append(
                f"PROJECT_STATE.yaml keeps terminal problem {problem_id} active with status {lifecycle}"
            )

    current_state = state.get("current_state")
    if isinstance(current_state, dict):
        declared_open_p0 = current_state.get("open_p0_failures")
        if isinstance(declared_open_p0, list):
            declared_ids = {str(item) for item in declared_open_p0}
            if declared_ids != active_p0_ids:
                issues.append(
                    "PROJECT_STATE.yaml current_state.open_p0_failures must match active P0 problems: "
                    f"declared={sorted(declared_ids)}, active={sorted(active_p0_ids)}"
                )

        execution = current_state.get("execution_mode")
        execution_mode = (
            normalize_lifecycle_status(execution.get("mode"))
            if isinstance(execution, dict)
            else ""
        )
        quality_gates = current_state.get("quality_gates")
        quality_status = (
            normalize_lifecycle_status(quality_gates.get("status"))
            if isinstance(quality_gates, dict)
            else ""
        )
        status_mode_match = re.search(r"^\*\*Execution Mode:\*\*\s*(.+)$", status_text, re.MULTILINE)
        status_mode = normalize_lifecycle_status(status_mode_match.group(1)) if status_mode_match else ""
        if (
            execution_mode == "QUALITY_FREEZE"
            or "QUALITY_FREEZE" in status_mode
            or "OPEN_P0" in quality_status
        ) and not active_p0_ids:
            issues.append("quality_freeze/active_with_open_p0 requires an actual active P0 problem")

    for path, value in walk_state(state):
        if not path or not isinstance(value, str):
            continue
        field = path[-1].lower()
        if field in VOLATILE_CONTAINING_HEAD_FIELDS and re.fullmatch(r"[0-9a-f]{7,40}", value):
            issues.append(
                "PROJECT_STATE.yaml must not couple live state to a volatile containing-main SHA at "
                + ".".join(path)
            )

    current_truth = markdown_section(status_text, "Current Truth")
    for line in current_truth.splitlines():
        if re.search(r"\bmain\b", line, re.IGNORECASE) and re.search(r"\b[0-9a-f]{40}\b", line):
            issues.append("STATUS.md Current Truth must not embed a volatile exact main SHA")
            break

    reconciliation = state_remote_reconciliation(state)
    pr_states = reconciled_pr_states(reconciliation)
    if pr_states:
        for label, text in (("STATUS.md", status_text), ("NEXT_ACTIONS.md", next_actions_text)):
            for line in text.splitlines():
                numbers = {int(number) for number in re.findall(r"\bPR\s*#(\d+)\b", line, re.IGNORECASE)}
                if not numbers or not re.search(r"\b(?:open|draft)\b", line, re.IGNORECASE):
                    continue
                for number in sorted(numbers):
                    if pr_states.get(number) in TERMINAL_PR_STATES:
                        issues.append(
                            f"{label} declares PR #{number} open/draft but reconciled remote state is {pr_states[number]}"
                        )

    if reconciled_main_ci_verified(reconciliation):
        for label, text in (("STATUS.md", status_text), ("NEXT_ACTIONS.md", next_actions_text)):
            for line in text.splitlines():
                if re.search(r"\bCI\b", line) and UNPROVEN_CI_RE.search(line):
                    issues.append(
                        f"{label} says CI is unproven/pending after reconciled main CI evidence was verified"
                    )
                    break
        if isinstance(current_state, dict):
            for path, value in walk_state(current_state):
                if path and "ci" in path[-1].lower() and isinstance(value, str) and UNPROVEN_CI_RE.search(value):
                    # The reconciliation subtree is the stable authority, not a contradiction.
                    if not any(part.lower() in RECONCILED_REMOTE_KEYS for part in path):
                        issues.append(
                            "PROJECT_STATE.yaml contains unproven CI truth after verified reconciliation at "
                            + ".".join(("current_state", *path))
                        )

    action_ids = set(extract_next_action_ids(next_actions_text))
    for problem_id in sorted(terminal_active_ids & action_ids):
        issues.append(f"NEXT_ACTIONS.md contains terminal active-problem item {problem_id}")
    return issues


def read_optional(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8") if path.exists() else ""
    except UnicodeDecodeError:
        return ""


def extract_scalar(text: str, key: str) -> str | None:
    match = re.search(rf'^\s*{re.escape(key)}:\s*"?([^"\n#]+)"?\s*$', text, re.MULTILINE)
    return match.group(1).strip() if match else None


def detect_repo_context(root: Path) -> tuple[str | None, str | None]:
    project_state = read_optional(root / "PROJECT_STATE.yaml")
    agents = read_optional(root / "AGENTS.md")
    role = extract_scalar(project_state, "repo_role") or extract_scalar(agents, "repo_role")
    mode = (
        extract_scalar(project_state, "statedd_mode")
        or extract_scalar(agents, "statedd_mode")
        or extract_scalar(project_state, "repo_mode")
        or extract_scalar(agents, "repo_mode")
    )
    return role, mode


def detect_repo_mode(root: Path) -> str | None:
    _, mode = detect_repo_context(root)
    return mode


def is_template_style_repo(root: Path) -> bool:
    role, _ = detect_repo_context(root)
    return role == "template_repository"


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
        for terminal_id in TERMINAL_NEXT_ACTION_TITLE_RE.findall(text):
            issues.append(
                f"NEXT_ACTIONS.md active title for {terminal_id} starts with a terminal lifecycle state"
            )

    if path.name == "BACKLOG.md":
        now_items = backlog_now_count(text)
        if now_items > rules.get("max_now_items", 10**9):
            issues.append(f"NOW section has {now_items} items, max is {rules['max_now_items']}")
        ids = extract_backlog_ids(text)
        if not ids:
            issues.append("BACKLOG.md must include stable backlog IDs like [BL-001]")
        structure_issues = check_backlog_structure(text)
        issues.extend(structure_issues)

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
    project_state = root / "PROJECT_STATE.yaml"
    status = root / "STATUS.md"
    worklog = root / "WORKLOG.md"
    if not all(path.exists() for path in (backlog, next_actions, project_state, status, worklog)):
        return issues

    backlog_text = backlog.read_text(encoding="utf-8")
    next_actions_text = next_actions.read_text(encoding="utf-8")
    state_text = project_state.read_text(encoding="utf-8")
    status_text = status.read_text(encoding="utf-8")
    worklog_text = worklog.read_text(encoding="utf-8")

    sections = extract_backlog_sections(backlog_text)
    backlog_ids = extract_backlog_ids(backlog_text)
    now_ids = set(sections.get("NOW", []))
    closed_ids = set(sections.get("CLOSED", []))
    action_ids = extract_next_action_ids(next_actions_text)
    for backlog_id in action_ids:
        if backlog_id not in backlog_ids:
            issues.append(f"NEXT_ACTIONS.md references missing backlog ID {backlog_id}")
        elif backlog_id not in now_ids:
            issues.append(f"NEXT_ACTIONS.md ID {backlog_id} must be in BACKLOG.md NOW")

    active_problems, problem_issues = extract_active_problems(state_text)
    issues.extend(problem_issues)
    parsed_state, state_parse_issues = parse_project_state(state_text)
    issues.extend(state_parse_issues)
    if parsed_state:
        issues.extend(
            check_live_state_semantics(
                parsed_state,
                status_text=status_text,
                next_actions_text=next_actions_text,
            )
        )
    active_ids = set(active_problems)
    for problem_id in sorted(active_ids):
        if problem_id in closed_ids:
            issues.append(f"PROJECT_STATE.yaml active problem {problem_id} is CLOSED in BACKLOG.md")
        elif problem_id not in now_ids:
            issues.append(f"PROJECT_STATE.yaml active problem {problem_id} must be in BACKLOG.md NOW")

    expected_status_ids = {
        problem_id for problem_id, severity in active_problems.items() if severity.upper() in {"P0", "P1"}
    }
    status_ids = extract_status_open_failure_ids(status_text)
    if status_ids != expected_status_ids:
        issues.append(
            "STATUS.md Open P0/P1 Failures must match PROJECT_STATE.yaml active_problems: "
            f"status={sorted(status_ids)}, state={sorted(expected_status_ids)}"
        )

    terminal_ids = extract_terminal_worklog_ids(worklog_text)
    for problem_id in sorted(terminal_ids & now_ids):
        issues.append(f"BACKLOG.md NOW contains terminal WORKLOG.md item {problem_id}")
    for problem_id in sorted(terminal_ids & set(action_ids)):
        issues.append(f"NEXT_ACTIONS.md contains terminal WORKLOG.md item {problem_id}")
    for problem_id in sorted(terminal_ids & active_ids):
        issues.append(f"PROJECT_STATE.yaml keeps terminal WORKLOG.md item {problem_id} active")
    return issues


def check_repo_role_mode(root: Path) -> list[str]:
    issues: list[str] = []
    role, mode = detect_repo_context(root)
    project_state = read_optional(root / "PROJECT_STATE.yaml")
    agents = read_optional(root / "AGENTS.md")

    if role is None:
        issues.append("Missing repo_role; expected template_repository or downstream_project")
    elif role not in VALID_REPO_ROLES:
        issues.append(f"Invalid repo_role: {role}")

    if mode is None:
        issues.append("Missing statedd_mode/repo_mode; expected template-maintenance, bootstrap, or operating")
    elif mode not in VALID_STATEDD_MODES:
        issues.append(f"Invalid statedd_mode/repo_mode: {mode}")

    if role == "template_repository":
        if mode != "template-maintenance":
            issues.append("template_repository must use statedd_mode: template-maintenance")
        if 'repo_role: template_repository' not in project_state:
            issues.append("PROJECT_STATE.yaml must declare repo_role: template_repository")
        if 'statedd_mode: template-maintenance' not in project_state:
            issues.append("PROJECT_STATE.yaml must declare statedd_mode: template-maintenance")
        for relpath in ("AGENTS.md", "STATUS.md", "PROJECT_STATE.yaml", "PROJECT_DNA.yaml", "PROJECT_ADAPTER.yaml"):
            text = read_optional(root / relpath)
            if "Your Project" in text:
                issues.append(f"{relpath} contains downstream placeholder text in template-maintenance mode")

    if role == "downstream_project":
        if mode == "template-maintenance":
            issues.append("downstream_project cannot use statedd_mode: template-maintenance")
        if 'repo_role: downstream_project' not in project_state:
            issues.append("PROJECT_STATE.yaml must declare repo_role: downstream_project")

    if role and f"repo_role: {role}" not in project_state and f'repo_role: "{role}"' not in agents:
        issues.append("repo_role must be visible in PROJECT_STATE.yaml or AGENTS.md")

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
        "scripts/statedd_worktree_guard.py",
        "ANTI_BRITTLENESS_GUARD.md",
        "scripts/statedd_runtime_proof.py",
        "scripts/statedd_runtime_truth_check.py",
        "scripts/statedd_validate_schema.py",
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
        "statedd-template-v5",
        "scripts/statedd_version_check.py",
        "repo_role",
        "statedd_mode",
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
        "anti-brittleness",
    ]
    for phrase in required_phrases:
        if phrase not in text:
            issues.append(f"README must mention: {phrase}")

    if "DESIGN.md" in text:
        issues.append("README must not reference missing DESIGN.md guidance")

    return issues


def check_version_alignment(root: Path) -> list[str]:
    script = root / "scripts" / "statedd_version_check.py"
    if not script.exists():
        return []

    completed = subprocess.run(
        [sys.executable, str(script), str(root)],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode == 0:
        return []

    output = "\n".join(part for part in (completed.stdout.strip(), completed.stderr.strip()) if part)
    if not output:
        output = f"version check exited with {completed.returncode}"
    return output.splitlines()


def check_schema_validation(root: Path) -> list[str]:
    script = root / "scripts" / "statedd_validate_schema.py"
    if not script.exists():
        fallback = ROOT / "scripts" / "statedd_validate_schema.py"
        if fallback.exists():
            script = fallback
        else:
            return ["Missing schema validator: scripts/statedd_validate_schema.py"]

    completed = subprocess.run(
        [sys.executable, str(script), str(root), "--quiet"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode == 0:
        return []

    output = "\n".join(part for part in (completed.stdout.strip(), completed.stderr.strip()) if part)
    if not output:
        output = f"schema validation exited with {completed.returncode}"
    return output.splitlines()


def latest_evidence_folder(root: Path) -> Path | None:
    evidence_root = root / "docs" / "evidence"
    if not evidence_root.exists():
        return None
    candidates = [
        entry
        for entry in evidence_root.iterdir()
        if entry.is_dir() and not entry.name.startswith(".")
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


def check_evidence_manifest(root: Path) -> list[str]:
    issues: list[str] = []
    folder = latest_evidence_folder(root)
    if folder is None:
        return issues
    manifest = folder / "manifest.json"
    if not manifest.exists():
        return issues
    schema = root / "schemas" / "evidence_manifest.schema.json"
    if not schema.exists():
        issues.append("manifest.json exists but schemas/evidence_manifest.schema.json is missing")
        return issues
    validator = root / "scripts" / "statedd_validate_schema.py"
    if not validator.exists():
        issues.append("manifest.json exists but scripts/statedd_validate_schema.py is missing")
        return issues
    completed = subprocess.run(
        [sys.executable, str(validator), "--file", str(manifest), "--schema", str(schema)],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        output = "\n".join(part for part in (completed.stdout.strip(), completed.stderr.strip()) if part)
        issues.append(f"Evidence manifest validation failed: {output[:400]}")
    return issues


def profile_optional_assets(root: Path) -> set[str]:
    project_state = read_optional(root / "PROJECT_STATE.yaml")
    profile = extract_scalar(project_state, "profile")
    if profile == "minimal":
        return OPTIONAL_ASSETS_FOR_MINIMAL_PROFILE
    return set()


def check_template_assets(root: Path) -> list[str]:
    issues: list[str] = []
    optional_assets = profile_optional_assets(root)

    for relpath in TEMPLATE_ASSET_PATHS:
        if relpath in optional_assets:
            continue
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
        for phrase in (
            "repo path",
            "branch",
            "process/container",
            "port/base URL",
            "rebuilt in this slice",
            "Runtime identity artifact",
            "worktree topology captured",
            "upstream branch",
            "GitHub-visible deliverables",
            "local-only files claimed",
        ):
            if phrase not in handoff_text:
                issues.append(f"Final handoff template missing phrase: {phrase}")

    cto_prompt = root / "prompts" / "CTO_SESSION_PROMPT.md"
    if cto_prompt.exists():
        cto_text = cto_prompt.read_text(encoding="utf-8")
        for phrase in ("TOOL_MODEL_ROUTING_GUIDE.md", "recommended tool/model/settings", "not proven", "statedd_worktree_guard.py", "ANTI_BRITTLENESS_GUARD.md"):
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
        for phrase in ("OpenCode", "AGENTS.md", "statedd_handoff.py", "not proven", "statedd_worktree_guard.py"):
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
        for phrase in ("StateDD Handoff Snapshot", "repo path", "not proven", "--test-command", "GitHub-visible deliverables", "local-only files claimed"):
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
        for phrase in ("non_goals", "acceptance_criteria", "Human override used: yes", "anti_brittleness", "statedd_worktree_guard.py"):
            if phrase not in slice_text:
                issues.append(f"Slice contract template missing phrase: {phrase}")

    evidence_readme = root / "prompts" / "EVIDENCE_README_TEMPLATE.md"
    if evidence_readme.exists():
        evidence_text = evidence_readme.read_text(encoding="utf-8")
        for phrase in ("Claims", "Verification Log", "Closure State", "Runtime Identity", "runtime_identity.json", "Anti-Brittleness Review", "Worktree Dirty File Classification"):
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
        for phrase in ("Closure verdict:", "Missing proof:", "Contradictions:", "Next best slice:", "Anti-brittleness:", "GitHub-visible deliverables"):
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
        authoritative = "python3 scripts/statedd_quality_gate.py --gate-level 2 --conformance"
        if authoritative not in workflow_text:
            issues.append(f"GitHub workflow must run the authoritative local gate: {authoritative}")
        manual_script_tests = re.findall(r"python3?\s+(scripts/test_[^\s]+\.py)", workflow_text)
        if manual_script_tests:
            issues.append(
                "GitHub workflow must not manually enumerate script tests: "
                + ", ".join(sorted(set(manual_script_tests)))
            )

    return issues


def check_bootstrap_gate(root: Path) -> list[str]:
    role, mode = detect_repo_context(root)
    if role == "template_repository" or mode == "template-maintenance":
        return check_template_maintenance_gate(root)
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
    try:
        parsed_state = parse_yaml_text(project_state)
    except StateDDYamlError as exc:
        issues.append(f"Bootstrap gate failed: PROJECT_STATE.yaml is invalid: {exc}")
    else:
        policy = parsed_state.get("delivery_policy") if isinstance(parsed_state, dict) else None
        policy_refusal = confirmed_delivery_policy_refusal(policy)
        if policy_refusal is not None:
            issues.append(f"Bootstrap gate failed: {policy_refusal}")
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
    return issues


def check_template_maintenance_gate(root: Path) -> list[str]:
    issues: list[str] = []
    project_state = read_optional(root / "PROJECT_STATE.yaml")
    next_actions = read_optional(root / "NEXT_ACTIONS.md")
    backlog = read_optional(root / "BACKLOG.md")
    worklog = read_optional(root / "WORKLOG.md")
    evidence = read_optional(root / "docs" / "EVIDENCE_LOG.md")

    if "repo_role: template_repository" not in project_state:
        issues.append("Template gate failed: PROJECT_STATE.yaml does not declare repo_role: template_repository")
    if "statedd_mode: template-maintenance" not in project_state:
        issues.append("Template gate failed: PROJECT_STATE.yaml does not declare statedd_mode: template-maintenance")
    if "Your Project" in project_state:
        issues.append("Template gate failed: PROJECT_STATE.yaml still contains downstream placeholder text")
    if next_actions_count(next_actions) == 0:
        issues.append("Template gate failed: NEXT_ACTIONS.md does not contain a real active queue")
    if len(extract_backlog_ids(backlog)) < 3:
        issues.append("Template gate failed: BACKLOG.md does not contain enough stable backlog IDs")
    if not WORKLOG_ENTRY_RE.search(worklog):
        issues.append("Template gate failed: WORKLOG.md does not record dated template-maintenance history")
    if not EVIDENCE_ENTRY_RE.search(evidence):
        issues.append("Template gate failed: docs/EVIDENCE_LOG.md does not record any evidence entries")

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

    role_mode_issues = check_repo_role_mode(root)
    if role_mode_issues:
        failures.append(("repo_role_mode", role_mode_issues))

    version_issues = check_version_alignment(root)
    if version_issues:
        failures.append(("version_alignment", version_issues))

    schema_issues = check_schema_validation(root)
    if schema_issues:
        failures.append(("schema_validation", schema_issues))

    readme = root / "README.md"
    template_style_repo = is_template_style_repo(root)
    if readme.exists() and template_style_repo:
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
    print_failure_block("repo role/mode", next((issues for name, issues in failures if name == "repo_role_mode"), []))
    print_failure_block("version alignment", next((issues for name, issues in failures if name == "version_alignment"), []))
    print_failure_block("schema validation", next((issues for name, issues in failures if name == "schema_validation"), []))

    manifest_issues = check_evidence_manifest(root)
    if manifest_issues:
        failures.append(("evidence_manifest", manifest_issues))
    if readme.exists() and template_style_repo:
        print_failure_block("README.md", next((issues for name, issues in failures if name == "README.md"), []))
        print_failure_block("template assets", next((issues for name, issues in failures if name == "template_assets"), []))
    print_failure_block("evidence manifest", next((issues for name, issues in failures if name == "evidence_manifest"), []))

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
