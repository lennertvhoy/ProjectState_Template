#!/usr/bin/env python3
"""Tests for statedd_instruction_lint.py"""

import tempfile
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import pytest

from statedd_instruction_lint import (
    InstructionLinter,
    Severity,
    SmellType,
    meets_failure_threshold,
)


def test_context_bloat():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        # Create file with too many lines
        big_file = root / "AGENTS.md"
        big_file.write_text("\n".join([f"line {i}" for i in range(200)]))
        linter = InstructionLinter(root, max_lines=180)
        count, smells = linter.run()
        assert any(s.type == SmellType.CONTEXT_BLOAT for s in smells)


def test_conflicting_instructions():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        f = root / "AGENTS.md"
        f.write_text("run browser test\n\nskip browser test")
        linter = InstructionLinter(root)
        count, smells = linter.run()
        assert any(s.type == SmellType.CONFLICTING_INSTRUCTIONS for s in smells)


def test_lint_leakage():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        f = root / "AGENTS.md"
        f.write_text("run flake8 on every commit\nrun ruff on every push")
        linter = InstructionLinter(root)
        count, smells = linter.run()
        assert any(s.type == SmellType.LINT_LEAKAGE for s in smells)


def test_skill_leakage():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        f = root / "AGENTS.md"
        f.write_text("step 1: run pytest\nthen run lint\nfinally run build")
        linter = InstructionLinter(root)
        count, smells = linter.run()
        assert any(s.type == SmellType.SKILL_LEAKAGE for s in smells)


def test_missing_failure_cases():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        skill_dir = root / "skills" / "test-skill"
        skill_dir.mkdir(parents=True)
        f = skill_dir / "SKILL.md"
        f.write_text("name: test\ndescription: test\nstep_by_step:\n  - name: do thing\n    command: echo hi")
        linter = InstructionLinter(root)
        count, smells = linter.run()
        assert any(s.type == SmellType.MISSING_FAILURE_CASES for s in smells)


def test_structured_failure_cases_are_recognized():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        skill_dir = root / "skills" / "test-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            "name: test\nfailure_cases:\n  - name: command fails\n    recovery: stop\n"
        )
        linter = InstructionLinter(root)
        _, smells = linter.run()
        assert not any(s.type == SmellType.MISSING_FAILURE_CASES for s in smells)


def test_outdated_claims():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        f = root / "AGENTS.md"
        f.write_text("version 1.2.3\nas of 2024-01-01\nlatest version")
        linter = InstructionLinter(root)
        count, smells = linter.run()
        assert any(s.type == SmellType.OUTDATED_CLAIMS for s in smells)


def test_cross_file_lint_leakage():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        for name in ["AGENTS.md", "CLAUDE.md", "docs/guide.md"]:
            f = root / name
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text("run flake8 on every commit")
        linter = InstructionLinter(root)
        count, smells = linter.run()
        # Should detect cross-file leakage
        assert any(s.type == SmellType.LINT_LEAKAGE and "3 files" in s.message for s in smells)


def test_no_smells_clean_file():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        f = root / "AGENTS.md"
        f.write_text("short file\nno issues here")
        linter = InstructionLinter(root)
        count, smells = linter.run()
        assert count == 0


@pytest.mark.parametrize(
    ("findings", "threshold", "expected"),
    [
        ([Severity.ERROR], Severity.ERROR, True),
        ([Severity.ERROR], Severity.WARNING, True),
        ([Severity.ERROR], Severity.INFO, True),
        ([Severity.WARNING], Severity.ERROR, False),
        ([Severity.WARNING], Severity.WARNING, True),
        ([Severity.INFO], Severity.WARNING, False),
        ([Severity.INFO], Severity.INFO, True),
        ([], Severity.INFO, False),
    ],
)
def test_failure_threshold_uses_numeric_severity_order(
    findings: list[Severity], threshold: Severity, expected: bool
) -> None:
    assert meets_failure_threshold(findings, threshold) is expected


if __name__ == "__main__":
    test_context_bloat()
    test_conflicting_instructions()
    test_lint_leakage()
    test_skill_leakage()
    test_missing_failure_cases()
    test_structured_failure_cases_are_recognized()
    test_outdated_claims()
    test_cross_file_lint_leakage()
    test_no_smells_clean_file()
    print("All tests passed!")
