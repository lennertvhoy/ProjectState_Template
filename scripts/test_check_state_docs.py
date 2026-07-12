#!/usr/bin/env python3
"""Regression tests for scripts/check_state_docs.py backlog structure checks."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from check_state_docs import check_backlog_structure, check_cross_file_rules, check_file, extract_backlog_sections  # noqa: E402


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


def test_terminal_lifecycle_title_cannot_be_an_active_action() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "NEXT_ACTIONS.md"
        path.write_text(
            "## Active Work\n\n### P0 [BL-001] Merged integration baseline\n"
            "\n## Queue Rules\n\nEvery item uses a backlog ID.\n",
            encoding="utf-8",
        )
        issues = check_file(path)
        assert any("starts with a terminal lifecycle state" in issue for issue in issues)


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


def test_main_ci_verified_worklog_status_is_terminal() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_lifecycle_repo(
            root,
            backlog="## NOW\n- [BL-001] stale\n",
            next_actions="## Active Work\n### P0 [BL-001] stale\n",
            active_problems="active_problems:\n  - id: BL-001\n    severity: P0\n",
            status_failures="- P0 [BL-001]: stale.\n",
            worklog=(
                "# WORKLOG\n\n## 2026-07-12 - Merge (BL-001)\n\n"
                "**Status:** MERGED_MAIN_CI_PASSING\n"
            ),
        )
        issues = check_cross_file_rules(root)
        assert any("terminal WORKLOG.md item BL-001" in issue for issue in issues)


def test_terminal_problem_status_cannot_remain_active_or_queued() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_lifecycle_repo(
            root,
            backlog="## NOW\n- [BL-001] stale\n",
            next_actions="## Active Work\n### P1 [BL-001] stale\n",
            active_problems=(
                "active_problems:\n"
                "  - id: BL-001\n"
                "    severity: P1\n"
                "    status: merged_into_main\n"
            ),
            status_failures="- P1 [BL-001]: stale.\n",
        )
        issues = check_cross_file_rules(root)
        assert any("keeps terminal problem BL-001 active" in issue for issue in issues)
        assert any("terminal active-problem item BL-001" in issue for issue in issues)


def test_quality_freeze_requires_a_real_open_p0() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_lifecycle_repo(
            root,
            backlog="## NEXT\n- [BL-002] research\n",
            next_actions="## Active Work\n",
            active_problems=(
                "current_state:\n"
                "  execution_mode:\n"
                "    mode: quality_freeze\n"
                "  open_p0_failures: []\n"
                "active_problems: []\n"
            ),
        )
        issues = check_cross_file_rules(root)
        assert any("requires an actual active P0" in issue for issue in issues)


def test_live_state_rejects_containing_main_sha_coupling() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_lifecycle_repo(
            root,
            backlog="## NEXT\n- [BL-002] research\n",
            next_actions="## Active Work\n",
            active_problems=(
                "current_state:\n"
                "  open_p0_failures: []\n"
                "  repository:\n"
                "    last_verified_head: 0123456789abcdef0123456789abcdef01234567\n"
                "active_problems: []\n"
            ),
        )
        issues = check_cross_file_rules(root)
        assert any("volatile containing-main SHA" in issue for issue in issues)


def test_reconciled_closed_pr_cannot_be_declared_open() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_lifecycle_repo(
            root,
            backlog="## NEXT\n- [BL-002] research\n",
            next_actions="## Active Work\n\nPR #6 remains an open draft source candidate.\n",
            active_problems=(
                "current_state:\n"
                "  open_p0_failures: []\n"
                "  remote_reconciliation:\n"
                "    pull_requests:\n"
                "      - number: 6\n"
                "        state: closed\n"
                "active_problems: []\n"
            ),
        )
        issues = check_cross_file_rules(root)
        assert any("PR #6" in issue and "reconciled remote state is CLOSED" in issue for issue in issues)


def test_verified_main_ci_cannot_remain_semantically_unproven() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_lifecycle_repo(
            root,
            backlog="## NEXT\n- [BL-002] research\n",
            next_actions="## Active Work\n\nMain CI is not proven.\n",
            active_problems=(
                "current_state:\n"
                "  open_p0_failures: []\n"
                "  remote_reconciliation:\n"
                "    main_ci:\n"
                "      status: verified\n"
                "      evidence: /external/handoff.json\n"
                "active_problems: []\n"
            ),
        )
        issues = check_cross_file_rules(root)
        assert any("after reconciled main CI evidence was verified" in issue for issue in issues)


def test_stable_post_merge_target_state_passes_without_containing_sha() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_lifecycle_repo(
            root,
            backlog="## NEXT\n- [BL-002] evidence-gated research\n",
            next_actions="## Active Work\n\nNo mandatory implementation item.\n",
            active_problems=(
                "current_state:\n"
                "  execution_mode:\n"
                "    mode: template-maintenance\n"
                "  open_p0_failures: []\n"
                "active_problems: []\n"
            ),
        )
        assert not check_cross_file_rules(root)


def test_merged_item_can_reopen_when_correctness_is_not_closure_grade() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_lifecycle_repo(
            root,
            backlog="## NOW\n- [BL-001] reopened blocker\n",
            next_actions="## Active Work\n### P1 [BL-001] repair merged blocker\n",
            active_problems="active_problems:\n  - id: BL-001\n    severity: P1\n",
            status_failures="- P1 [BL-001]: merged but correctness remains open.\n",
            worklog="# WORKLOG\n\n## 2026-07-10 - Merged (BL-001)\n\n**Status:** MERGED\n",
        )
        assert not check_cross_file_rules(root)


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
        test_terminal_lifecycle_title_cannot_be_an_active_action,
        test_status_must_match_canonical_active_problems,
        test_terminal_worklog_item_cannot_remain_active,
        test_main_ci_verified_worklog_status_is_terminal,
        test_terminal_problem_status_cannot_remain_active_or_queued,
        test_quality_freeze_requires_a_real_open_p0,
        test_live_state_rejects_containing_main_sha_coupling,
        test_reconciled_closed_pr_cannot_be_declared_open,
        test_verified_main_ci_cannot_remain_semantically_unproven,
        test_stable_post_merge_target_state_passes_without_containing_sha,
        test_consistent_lifecycle_passes,
    ]
    for t in tests:
        t()
        print(f"PASS {t.__name__}")
