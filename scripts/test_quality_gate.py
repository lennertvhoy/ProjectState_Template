#!/usr/bin/env python3
"""Tests for the authoritative StateDD quality-gate entrypoint."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

try:
    from statedd_quality_gate import QualityGate
except ModuleNotFoundError:  # pragma: no cover - pytest package import path
    from scripts.statedd_quality_gate import QualityGate


def configured_multi_suite_root(root: Path) -> None:
    (root / "test_sample.py").write_text("def test_ok(): assert True\n", encoding="utf-8")
    (root / "Makefile").write_text("test:\n\t@true\n", encoding="utf-8")
    (root / "package.json").write_text(json.dumps({"scripts": {"test": "true"}}), encoding="utf-8")
    (root / "Cargo.toml").write_text("[package]\nname='demo'\nversion='0.1.0'\n", encoding="utf-8")


def test_all_applicable_suites_run_and_failures_aggregate() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        configured_multi_suite_root(root)
        gate = QualityGate(root)
        commands: list[tuple[str, ...]] = []

        def fake_run(cmd: list[str], cwd: Path | None = None) -> tuple[int, str, str]:
            commands.append(tuple(cmd))
            if cmd[0] in {"make", "cargo"}:
                return 1, f"{cmd[0]} failed", ""
            return 0, "ok", ""

        gate.run_cmd = fake_run  # type: ignore[method-assign]
        assert gate.check_tests() is False
        assert [command[0] for command in commands] == [sys.executable, "make", "npm", "cargo"]
        assert len(gate.failures) == 2
        assert "make test" in gate.failures[0]
        assert "cargo test" in gate.failures[1]


def test_unavailable_declared_runner_fails_but_later_suite_still_runs() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "Makefile").write_text("test:\n\t@true\n", encoding="utf-8")
        (root / "package.json").write_text(json.dumps({"scripts": {"test": "true"}}), encoding="utf-8")
        gate = QualityGate(root)
        commands: list[str] = []

        def fake_run(cmd: list[str], cwd: Path | None = None) -> tuple[int, str, str]:
            commands.append(cmd[0])
            return (-1, "", "not found") if cmd[0] == "make" else (0, "ok", "")

        gate.run_cmd = fake_run  # type: ignore[method-assign]
        assert gate.check_tests() is False
        assert commands == ["make", "npm"]
        assert any("unavailable" in failure for failure in gate.failures)


def test_no_suite_is_distinct_from_unavailable_tooling() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        gate = QualityGate(Path(tmp))
        assert gate.check_tests() is True
        assert gate.failures == []
        assert gate.warnings == ["No project test command detected"]


def test_malformed_package_json_fails_configuration() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "package.json").write_text('{"scripts":{},"scripts":{}}', encoding="utf-8")
        gate = QualityGate(root)
        assert gate.check_tests() is False
        assert any("package.json is invalid" in failure for failure in gate.failures)


def test_internal_python_checks_use_current_interpreter() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        gate = QualityGate(Path(tmp))
        commands: list[list[str]] = []

        def fake_run(cmd: list[str], cwd: Path | None = None) -> tuple[int, str, str]:
            commands.append(cmd)
            return 0, "ok", ""

        gate.run_cmd = fake_run  # type: ignore[method-assign]
        assert gate.check_state_files()
        assert gate.check_schemas()
        assert gate.check_instruction_lint()
        assert gate.check_efficiency()
        assert all(command[0] == sys.executable for command in commands)


def test_regulated_lock_requires_level_two() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "STATEDD_ASSETS.json").write_text(
            json.dumps(
                {
                    "schema": "statedd.runtime_assets.v2",
                    "profile": "regulated",
                    "required_gate_level": 2,
                }
            ),
            encoding="utf-8",
        )
        low = QualityGate(root, gate_level=1)
        assert low.check_profile_policy() is False
        high = QualityGate(root, gate_level=2)
        assert high.check_profile_policy() is True


def test_profile_validation_ids_dispatch_and_fail_on_unknown_or_missing_assets() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        manifest = root / "STATEDD_ASSETS.json"
        manifest.write_text(
            json.dumps(
                {
                    "schema": "statedd.runtime_assets.v2",
                    "validations": ["quality_gate_level_1"],
                }
            ),
            encoding="utf-8",
        )
        gate = QualityGate(root, gate_level=1)
        assert gate.check_profile_validations() is False
        assert any("requires regular asset" in failure for failure in gate.failures)

        (root / "scripts").mkdir()
        (root / "scripts" / "statedd_quality_gate.py").write_text("# present\n")
        gate = QualityGate(root, gate_level=1)
        assert gate.check_profile_validations() is True

        manifest.write_text(
            json.dumps(
                {"schema": "statedd.runtime_assets.v2", "validations": ["unknown"]}
            ),
            encoding="utf-8",
        )
        gate = QualityGate(root, gate_level=1)
        assert gate.check_profile_validations() is False
        assert any("unknown validation" in failure.lower() for failure in gate.failures)


def test_level_two_requires_slice_evidence_unless_conformance_mode() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "docs").mkdir()
        (root / "docs" / "EVIDENCE_LOG.md").write_text("# Evidence\n\n" + "proof " * 20)

        closure = QualityGate(root, gate_level=2)
        assert closure.check_evidence() is False
        assert any("active slice context" in failure for failure in closure.failures)

        conformance = QualityGate(root, gate_level=2, conformance=True)
        assert conformance.check_evidence() is True
        assert conformance.failures == []


def test_setup_cfg_without_flake8_section_does_not_declare_runner() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "setup.cfg").write_text("[metadata]\nname = demo\n", encoding="utf-8")
        gate = QualityGate(root)
        assert gate.check_static_analysis() is True
        assert gate.failures == []


def test_failure_output_preserves_stdout_and_stderr() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "Makefile").write_text("test:\n\t@true\n", encoding="utf-8")
        gate = QualityGate(root)
        gate.run_cmd = lambda cmd, cwd=None: (1, "assertion failed", "runner warning")  # type: ignore[method-assign]
        assert gate.check_tests() is False
        assert "assertion failed" in gate.failures[0]
        assert "runner warning" in gate.failures[0]


def test_run_fails_when_a_check_returns_false_without_diagnostic() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        gate = QualityGate(Path(tmp))
        method_names = [
            "check_compile",
            "check_profile_policy",
            "check_profile_validations",
            "check_profile_metrics",
            "check_tests",
            "check_static_analysis",
            "check_state_files",
            "check_schemas",
            "check_evidence",
            "check_acceptance_freezes",
            "check_instruction_lint",
            "check_efficiency",
            "check_diff_whitespace",
        ]
        for name in method_names:
            setattr(gate, name, lambda: True)
        gate.check_tests = lambda: False  # type: ignore[method-assign]
        assert gate.run() == 1
        assert gate.failures == ["One or more quality checks returned failure without a diagnostic"]
