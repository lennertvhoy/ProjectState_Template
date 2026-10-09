#!/usr/bin/env python3
"""Tests for projectstate_verify.py: the journey result is observed and recorded, never typed."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

import projectstate_gate as gate  # noqa: E402
import projectstate_verify as verify  # noqa: E402

ENVIRONMENT = "Local Python 3"
PROJECT = (
    "# Demo\n\n## User\n\nA person who runs the demo.\n\n## Outcome\n\nThe demo prints its greeting.\n\n"
    "## Scope\n\n- The greeting.\n\n## Non-goals\n\n- Anything else.\n\n## Durable constraints\n\n- None.\n"
)


def state_text(command: str, status: str, journey: str, human: str = "pending", quote: bool = False) -> str:
    q = (lambda value: f'"{value}"') if quote else (lambda value: value)
    return (
        "# Canonical current truth.\n"
        'version: "projectstate-template-v6"\n'
        "profile: core\n"
        "project:\n"
        '  outcome_ref: "PROJECT.md#outcome"\n'
        "current_slice:\n"
        "  id: demo-001\n"
        '  objective: "Print the greeting."\n'
        f"  status: {q(status)}\n"
        "  acceptance:\n"
        '    - "The greeting prints."\n'
        "  primary_journey:\n"
        '    description: "Run the greeting."\n'
        f"    command: {json.dumps(command)}\n"
        f'    environment: "{ENVIRONMENT}"\n'
        f"    status: {q(journey)}  # kept comment\n"
        '    evidence: "evidence/demo-001/summary.md"\n'
        "validation:\n"
        f"  primary_journey: {q(journey)}\n"
        f"  automated_tests: {'passed' if journey == 'passed' else 'not_run'}\n"
        f"  human_acceptance: {human}\n"
        "delivery_boundary:\n"
        "  name: demo\n"
        "  failed_attempts: []\n"
        "  simplification_review: null\n"
        "blockers: []\n"
        "risks: []\n"
        'next_action: "Run the journey."\n'
    )


def summary_text(command: str, result: str = "not run", exit_code: str = "not recorded", extra: str = "") -> str:
    return (
        f"# Evidence: demo-001\n\n## Primary journey\n\n- Environment: {ENVIRONMENT}\n- Command: `{command}`\n"
        f"- Result: {result}\n- Exit code: {exit_code}\n{extra}\n## Secondary checks\n\n- None.\n\n"
        "## Artifacts\n\n- None recorded.\n\n## Limitations\n\n- None.\n"
    )


def make(tmp_path: Path, command: str = "exit 0", status: str = "implementing", journey: str = "not_run",
         human: str = "pending", quote: bool = False, summary: str | None = None) -> Path:
    (tmp_path / "evidence" / "demo-001").mkdir(parents=True)
    (tmp_path / "PROJECT.md").write_text(PROJECT)
    (tmp_path / "AGENTS.md").write_text("# Rules\n")
    (tmp_path / "STATE.yaml").write_text(state_text(command, status, journey, human, quote))
    passed = journey == "passed"
    (tmp_path / "evidence" / "demo-001" / "summary.md").write_text(
        summary if summary is not None else summary_text(command, "passed" if passed else "not run", "0" if passed else "not recorded"))
    return tmp_path


def digest(root: Path) -> dict[str, str]:
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.rglob("*")) if p.is_file()}


def parsed(root: Path) -> dict:
    return gate.parse_state((root / "STATE.yaml").read_text())


def summary(root: Path) -> str:
    return (root / "evidence" / "demo-001" / "summary.md").read_text()


def run(root: Path, *extra: str) -> int:
    return verify.main(["--root", str(root), *extra])


def test_dry_run_prints_the_plan_and_writes_nothing(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    root = make(tmp_path, command="echo hello")
    before = digest(root)
    assert run(root) == 0
    assert digest(root) == before
    assert "echo hello" in capsys.readouterr().out


def test_a_passing_journey_is_recorded_from_the_exit_code(tmp_path: Path) -> None:
    root = make(tmp_path, command="echo hello && exit 0", status="validated")
    assert run(root, "--run") == 0
    state = parsed(root)
    assert state["current_slice"]["primary_journey"]["status"] == "passed"
    assert state["validation"]["primary_journey"] == "passed"
    assert state["current_slice"]["status"] == "validated"
    text = summary(root)
    assert "- Result: passed" in text and "- Exit code: 0" in text and "- Verified: " in text
    assert "last-journey-run.txt" in text and "None recorded" not in text
    assert "hello" in (root / "evidence" / "demo-001" / verify.ARTIFACT).read_text()
    errors, blockers, _warnings = gate.validate(root)
    assert errors == [] and blockers == []


def test_a_failing_journey_is_recorded_and_downgrades_a_validated_slice(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    for status in ("validated", "ready_for_human"):
        root = make(tmp_path / status, command="echo boom >&2; exit 3", status=status, journey="passed")
        (tmp_path / status).mkdir(exist_ok=True)
        assert run(root, "--run") == 1
        state = parsed(root)
        assert state["current_slice"]["primary_journey"]["status"] == "failed"
        assert state["validation"]["primary_journey"] == "failed"
        assert state["current_slice"]["status"] == "implementing"
        assert "- Result: failed" in summary(root) and "- Exit code: 3" in summary(root)
        assert "boom" in (root / "evidence" / "demo-001" / verify.ARTIFACT).read_text()
        errors, blockers, _warnings = gate.validate(root)
        assert errors == [] and any("failed" in blocker for blocker in blockers)
    assert "boom" in capsys.readouterr().out


def test_an_accepted_slice_is_never_altered(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    root = make(tmp_path, command="exit 1", status="accepted", journey="passed", human="accepted",
                summary=summary_text("exit 1", "passed", "0", "") + "\n## Owner decision\n\n- Decision: accepted\n"
                "- Date: 2026-10-01\n- Owner words: \"fine\"\n")
    before = digest(root)
    assert run(root, "--run") == 2
    assert digest(root) == before
    assert "Tell the owner" in capsys.readouterr().err


def test_placeholder_and_empty_commands_are_refused(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    for number, command in enumerate(("Not yet defined", "TODO: write it", "   ")):
        root = make(tmp_path / str(number), command=command)
        before = digest(root)
        assert run(root, "--run") == 2
        assert digest(root) == before
    assert "placeholder" in capsys.readouterr().err


def test_a_timeout_is_a_failure_with_exit_code_124(tmp_path: Path) -> None:
    root = make(tmp_path, command="sleep 30")
    assert run(root, "--run", "--timeout", "1") == 1
    assert parsed(root)["current_slice"]["primary_journey"]["status"] == "failed"
    assert "- Exit code: 124" in summary(root) and "timed out" in summary(root)


def test_recording_twice_changes_only_the_timestamp(tmp_path: Path) -> None:
    root = make(tmp_path, command="exit 0", journey="passed")
    assert run(root, "--run") == 0
    first = (root / "STATE.yaml").read_bytes(), summary(root)
    assert run(root, "--run") == 0
    assert (root / "STATE.yaml").read_bytes() == first[0]
    strip = lambda text: "\n".join(line for line in text.splitlines() if not line.startswith("- Verified:"))  # noqa: E731
    assert strip(summary(root)) == strip(first[1])


def test_quoting_and_comments_in_state_survive(tmp_path: Path) -> None:
    root = make(tmp_path, command="exit 0", quote=True)
    assert run(root, "--run") == 0
    text = (root / "STATE.yaml").read_text()
    assert '    status: "passed"  # kept comment' in text
    assert '  primary_journey: "passed"' in text
    assert text.count("passed") == 2  # only the two journey statuses; automated_tests is not observed here
    assert "  automated_tests: not_run" in text


def test_missing_summary_labels_are_added_and_command_mismatches_are_fixed(tmp_path: Path) -> None:
    thin = ("# Evidence: demo-001\n\n## Primary journey\n\n- Command: `something else`\n\n"
            "## Secondary checks\n\n- None.\n\n## Artifacts\n\n- None recorded.\n\n## Limitations\n\n- None.\n")
    root = make(tmp_path, command="exit 0", summary=thin)
    assert run(root, "--run") == 0
    errors, blockers, _warnings = gate.validate(root)
    assert errors == [] and blockers == []


def test_symlinks_and_missing_files_are_refused(tmp_path: Path) -> None:
    root = make(tmp_path / "a")
    real = root / "evidence" / "demo-001" / "summary.md"
    elsewhere = tmp_path / "elsewhere.md"
    elsewhere.write_text(real.read_text())
    real.unlink()
    real.symlink_to(elsewhere)
    assert run(root, "--run") == 2
    assert elsewhere.read_text().count("not run") >= 1  # untouched
    assert run(tmp_path / "nowhere", "--run") == 2


def test_new_gate_errors_roll_everything_back(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = make(tmp_path, command="echo ok")
    before = digest(root)
    real = gate.validate
    calls = {"n": 0}

    def flaky(path: Path):  # the second call (after recording) reports an error that was not there before
        calls["n"] += 1
        return (["boom"], [], []) if calls["n"] == 2 else real(path)

    monkeypatch.setattr(gate, "validate", flaky)
    assert run(root, "--run") == 2
    assert digest(root) == before  # STATE, summary and the artifact are all back; no artifact left behind


def test_unreadable_summary_structure_is_refused_before_anything_is_written(tmp_path: Path) -> None:
    root = make(tmp_path, summary="# Evidence\n\nno sections\n")
    before = digest(root)
    assert run(root, "--run") == 2
    assert digest(root) == before
