#!/usr/bin/env python3
"""Regression tests for scripts/check_state_docs.py backlog structure checks."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from check_state_docs import check_backlog_structure, check_cross_file_rules, extract_backlog_sections  # noqa: E402


def write_lifecycle_repo(
    root: Path,
    *,
    backlog: str,
    next_actions: str,
    active_problems: str = "active_problems: []\n",
    status_failures: str = "- None.\n",
    worklog: str = "# WORKLOG\n",
) -> None:
    (root / "BACKLOG.md").write_text(backlog, encoding="utf-8")
    (root / "NEXT_ACTIONS.md").write_text(next_actions, encoding="utf-8")
    (root / "PROJECT_STATE.yaml").write_text(active_problems, encoding="utf-8")
    (root / "STATUS.md").write_text(
        f"# Status\n\n## Open P0/P1 Failures\n\n{status_failures}\n## Notes\n",
        encoding="utf-8",
    )
    (root / "WORKLOG.md").write_text(worklog, encoding="utf-8")


def test_duplicate_section_detected() -> None:
    text = "## NOW\n- [BL-001] a\n## CLOSED\n- [BL-002] b\n## CLOSED\n- [BL-003] c\n"
    issues = check_backlog_structure(text)
    assert any("Duplicate second-level section '## CLOSED'" in i for i in issues)


def test_duplicate_backlog_id_detected() -> None:
    text = "## NOW\n- [BL-001] a\n## NEXT\n- [BL-001] b\n"
    issues = check_backlog_structure(text)
    assert any("Backlog ID BL-001 appears in multiple sections" in i for i in issues)


def test_duplicate_id_in_same_section_detected() -> None:
    text = "## CLOSED\n- [BL-005] a\n- [BL-005] b\n"
    issues = check_backlog_structure(text)
    assert any("Backlog ID BL-005 appears in multiple sections" in i for i in issues)


def test_clean_backlog_passes() -> None:
    text = "## NOW\n- [BL-001] a\n## NEXT\n- [BL-002] b\n## CLOSED\n- [BL-003] c\n"
    issues = check_backlog_structure(text)
    assert not issues


def test_extract_backlog_sections() -> None:
    text = "## NOW\n- [BL-001] a\n## CLOSED\n- [BL-002] b\n"
    sections = extract_backlog_sections(text)
    assert sections == {"NOW": ["BL-001"], "CLOSED": ["BL-002"]}


def test_root_backlog_has_no_structure_issues() -> None:
    text = (ROOT / "BACKLOG.md").read_text(encoding="utf-8")
    issues = check_backlog_structure(text)
    assert not issues, f"Root BACKLOG.md has structure issues: {issues}"


def test_next_action_must_be_in_now() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_lifecycle_repo(
            root,
            backlog="## NOW\n- [BL-001] open\n## CLOSED\n- [BL-002] closed\n",
            next_actions="## Active Work\n### P1 [BL-002] stale\n",
        )
        issues = check_cross_file_rules(root)
        assert any("BL-002 must be in BACKLOG.md NOW" in issue for issue in issues)


def test_status_must_match_canonical_active_problems() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_lifecycle_repo(
            root,
            backlog="## NOW\n- [BL-001] open\n",
            next_actions="## Active Work\n### P1 [BL-001] open\n",
            active_problems="active_problems:\n  - id: BL-001\n    severity: P1\n",
        )
        issues = check_cross_file_rules(root)
        assert any("must match PROJECT_STATE.yaml active_problems" in issue for issue in issues)


def test_terminal_worklog_item_cannot_remain_active() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_lifecycle_repo(
            root,
            backlog="## NOW\n- [BL-001] open\n",
            next_actions="## Active Work\n### P1 [BL-001] open\n",
            active_problems="active_problems:\n  - id: BL-001\n    severity: P1\n",
            status_failures="- P1 [BL-001]: open.\n",
            worklog="# WORKLOG\n\n## 2026-07-10 - Closed (BL-001)\n\n**Status:** COMPLETE\n",
        )
        issues = check_cross_file_rules(root)
        assert any("terminal WORKLOG.md item BL-001" in issue for issue in issues)


def test_consistent_lifecycle_passes() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_lifecycle_repo(
            root,
            backlog="## NOW\n- [BL-001] open\n## CLOSED\n- [BL-002] closed\n",
            next_actions="## Active Work\n### P1 [BL-001] open\n",
            active_problems="active_problems:\n  - id: BL-001\n    severity: P1\n",
            status_failures="- P1 [BL-001]: open.\n",
            worklog="# WORKLOG\n\n## 2026-07-10 - Local (BL-001)\n\n**Status:** LOCAL_CLOSURE_GRADE\n",
        )
        assert not check_cross_file_rules(root)


if __name__ == "__main__":
    tests = [
        test_duplicate_section_detected,
        test_duplicate_backlog_id_detected,
        test_duplicate_id_in_same_section_detected,
        test_clean_backlog_passes,
        test_extract_backlog_sections,
        test_root_backlog_has_no_structure_issues,
        test_next_action_must_be_in_now,
        test_status_must_match_canonical_active_problems,
        test_terminal_worklog_item_cannot_remain_active,
        test_consistent_lifecycle_passes,
    ]
    for t in tests:
        t()
        print(f"PASS {t.__name__}")
