#!/usr/bin/env python3
"""Focused regressions for explicit quality-gate configuration semantics."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from statedd_quality_gate import QualityGate  # noqa: E402


class FakeGate(QualityGate):
    def __init__(self, root: Path, result: tuple[int, str, str] = (0, "ok", "")):
        super().__init__(root)
        self.result = result
        self.commands: list[list[str]] = []

    def run_cmd(self, cmd: list[str], cwd: Path | None = None) -> tuple[int, str, str]:
        self.commands.append(cmd)
        return self.result


def test_missing_test_configuration_is_not_configured() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        gate = FakeGate(Path(tmp))
        assert gate.check_tests() is False
        assert not gate.commands
        assert any("Tests NOT_CONFIGURED" in failure for failure in gate.failures)


def test_missing_lint_configuration_is_not_configured() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        gate = FakeGate(Path(tmp))
        assert gate.check_static_analysis() is False
        assert not gate.commands
        assert any("Static analysis NOT_CONFIGURED" in failure for failure in gate.failures)


def test_discovered_python_tests_are_run() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        tests = root / "scripts"
        tests.mkdir()
        (tests / "test_sample.py").write_text("def test_sample():\n    assert True\n", encoding="utf-8")

        gate = FakeGate(root)
        assert gate.check_tests() is True
        assert len(gate.commands) == 1
        assert gate.commands[0][1:3] == ["-m", "pytest"]


def test_configured_linter_is_run() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / ".ruff.toml").write_text("line-length = 100\n", encoding="utf-8")

        gate = FakeGate(root)
        assert gate.check_static_analysis() is True
        assert gate.commands == [["ruff", "check", "."]]


def test_global_evidence_log_does_not_pass_without_slice_binding() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        docs = root / "docs"
        docs.mkdir()
        (docs / "EVIDENCE_LOG.md").write_text(
            "Historical validation evidence exists and passed many checks.\n" * 4,
            encoding="utf-8",
        )

        gate = FakeGate(root)
        assert gate.check_evidence() is False
        assert any("Evidence NOT_CONFIGURED" in failure for failure in gate.failures)


def main() -> int:
    tests = [
        test_missing_test_configuration_is_not_configured,
        test_missing_lint_configuration_is_not_configured,
        test_discovered_python_tests_are_run,
        test_configured_linter_is_run,
        test_global_evidence_log_does_not_pass_without_slice_binding,
    ]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
