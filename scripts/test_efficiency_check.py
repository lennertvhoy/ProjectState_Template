#!/usr/bin/env python3
"""Tests for scripts/statedd_efficiency_check.py."""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECK_SCRIPT = ROOT / "scripts" / "statedd_efficiency_check.py"


def run_check(args: list[str], *, expect_success: bool) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        [sys.executable, str(CHECK_SCRIPT), *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if expect_success and completed.returncode != 0:
        raise AssertionError(
            f"Expected success for {args}, got {completed.returncode}\n"
            f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )
    if not expect_success and completed.returncode == 0:
        raise AssertionError(
            f"Expected failure for {args}, got success\nstdout:\n{completed.stdout}"
        )
    return completed


def write_budget(root: Path, **overrides: int) -> None:
    defaults = {
        "schema": "statedd.efficiency_budget.v1",
        "instruction_budgets": {
            "root_agents_max_lines": 100,
            "nested_agents_max_lines": 80,
            "skill_max_lines": 180,
            "command_max_lines": 120,
            "prompt_max_lines": 250,
            "duplicate_instruction_max_lines": 5,
            "max_steps_per_workflow": 8,
        },
        "state_budgets": {"active_next_actions_max": 5, "active_backlog_items_max": 12},
        "evidence_budgets": {"default_max_files": 5},
        "anti_bloat_rules": {
            "no_duplicate_instruction_files": True,
            "no_unreferenced_skills": True,
            "no_full_repo_audit_for_single_file_edit": True,
        },
    }
    section_map = {
        "active_next_actions_max": "state_budgets",
        "active_backlog_items_max": "state_budgets",
        "default_max_files": "evidence_budgets",
        "docs_only_max_files": "evidence_budgets",
        "runtime_change_min_files": "evidence_budgets",
        "runtime_change_max_files": "evidence_budgets",
    }
    for key, value in overrides.items():
        if "." in key:
            section, sub = key.split(".", 1)
            defaults[section][sub] = value  # type: ignore[index]
        elif key in section_map:
            defaults[section_map[key]][key] = value  # type: ignore[index]
        else:
            defaults["instruction_budgets"][key] = value  # type: ignore[index]
    import yaml

    (root / "EFFICIENCY_BUDGET.yaml").write_text(yaml.safe_dump(defaults), encoding="utf-8")


def test_oversized_root_agents_fails() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_budget(root, root_agents_max_lines=5)
        (root / "AGENTS.md").write_text("line\n" * 10, encoding="utf-8")
        run_check(["--root", str(root)], expect_success=False)


def test_oversized_skill_fails() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_budget(root, skill_max_lines=5)
        skill = root / "skills" / "big" / "SKILL.md"
        skill.parent.mkdir(parents=True)
        skill.write_text(
            "---\nname: big\ngate_level: 1\n---\n\n" + "line\n" * 10,
            encoding="utf-8",
        )
        (root / "AGENTS.md").write_text("short.\n", encoding="utf-8")
        run_check(["--root", str(root)], expect_success=False)


def test_missing_gate_level_fails() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_budget(root)
        skill = root / "skills" / "nogate" / "SKILL.md"
        skill.parent.mkdir(parents=True)
        skill.write_text("---\nname: nogate\n---\n\nstep_by_step:\n  - name: do thing\n", encoding="utf-8")
        (root / "AGENTS.md").write_text("short.\n", encoding="utf-8")
        run_check(["--root", str(root)], expect_success=False)


def test_full_gate_at_level_one_fails() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_budget(root)
        skill = root / "skills" / "heavy" / "SKILL.md"
        skill.parent.mkdir(parents=True)
        skill.write_text(
            "---\nname: heavy\ngate_level: 1\n---\n\nRun the full pipeline here.\n",
            encoding="utf-8",
        )
        (root / "AGENTS.md").write_text("short.\n", encoding="utf-8")
        run_check(["--root", str(root)], expect_success=False)


def test_too_many_steps_fails() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_budget(root, max_steps_per_workflow=2)
        skill = root / "skills" / "long" / "SKILL.md"
        skill.parent.mkdir(parents=True)
        steps = "\n".join([f"  - name: step {i}" for i in range(5)])
        skill.write_text(
            f"---\nname: long\ngate_level: 2\n---\n\nstep_by_step:\n{steps}\n",
            encoding="utf-8",
        )
        (root / "AGENTS.md").write_text("short.\n", encoding="utf-8")
        run_check(["--root", str(root)], expect_success=False)


def test_duplicate_instructions_fails() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_budget(root)
        lines = "\n".join(
            [f"This is duplicated canonical instruction number {i} that appears in every shim file." for i in range(8)]
        )
        (root / "AGENTS.md").write_text(lines + "\n", encoding="utf-8")
        (root / "CLAUDE.md").write_text(lines + "\n", encoding="utf-8")
        (root / "GEMINI.md").write_text(lines + "\n", encoding="utf-8")
        run_check(["--root", str(root)], expect_success=False)


def test_active_queue_too_long_fails() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_budget(root, active_next_actions_max=2)
        (root / "AGENTS.md").write_text("short.\n", encoding="utf-8")
        items = "\n".join([f"### P{i} [BL-{i:03d}] item" for i in range(1, 5)])
        (root / "NEXT_ACTIONS.md").write_text(f"## Active Work\n\n{items}\n", encoding="utf-8")
        run_check(["--root", str(root)], expect_success=False)


def test_evidence_bundle_too_large_fails() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_budget(root, default_max_files=2)
        (root / "AGENTS.md").write_text("short.\n", encoding="utf-8")
        evidence = root / "docs" / "evidence" / "2026-06-28-test"
        evidence.mkdir(parents=True)
        for i in range(5):
            (evidence / f"a{i}.txt").write_text("x", encoding="utf-8")
        run_check(["--root", str(root)], expect_success=False)


def test_bloat_fixture_fails() -> None:
    fixture = ROOT / "fixtures" / "efficiency_bloat_overcorrection"
    completed = run_check(["--root", str(fixture)], expect_success=False)
    stdout = completed.stdout
    assert "instruction_size" in stdout or "workflow_gate_level" in stdout
    assert "active_queue" in stdout or "evidence_bundle" in stdout


def test_clean_repo_passes() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_budget(root)
        (root / "AGENTS.md").write_text("short.\n", encoding="utf-8")
        run_check(["--root", str(root)], expect_success=True)


if __name__ == "__main__":
    tests = [
        test_oversized_root_agents_fails,
        test_oversized_skill_fails,
        test_missing_gate_level_fails,
        test_full_gate_at_level_one_fails,
        test_too_many_steps_fails,
        test_duplicate_instructions_fails,
        test_active_queue_too_long_fails,
        test_evidence_bundle_too_large_fails,
        test_bloat_fixture_fails,
        test_clean_repo_passes,
    ]
    for t in tests:
        t()
        print(f"PASS {t.__name__}")
