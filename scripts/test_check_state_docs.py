#!/usr/bin/env python3
"""Regression tests for scripts/check_state_docs.py backlog structure checks."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from check_state_docs import check_backlog_structure, extract_backlog_sections


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


if __name__ == "__main__":
    tests = [
        test_duplicate_section_detected,
        test_duplicate_backlog_id_detected,
        test_duplicate_id_in_same_section_detected,
        test_clean_backlog_passes,
        test_extract_backlog_sections,
        test_root_backlog_has_no_structure_issues,
    ]
    for t in tests:
        t()
        print(f"PASS {t.__name__}")
