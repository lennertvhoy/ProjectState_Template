#!/usr/bin/env python3
"""Tests for projectstate_verify.py: the journey result is observed and recorded, never typed."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
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


# --- --receipt: an independent run that writes nothing in the repository ------------------------------------------


def receipt_run(root: Path, receipts: Path, *extra: str) -> int:
    return verify.main(["--root", str(root), "--receipt", "--receipts", str(receipts), *extra])


def read_receipt(receipts: Path, root: Path) -> dict:
    return json.loads((receipts / root.name / "demo-001.json").read_text())


def git(root: Path, *args: str) -> str:
    env = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull,
           "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.invalid",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.invalid"}
    done = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=False, env=env)
    assert done.returncode == 0, done.stderr
    return done.stdout


def committed(root: Path) -> str:
    """Commit everything in ``root``; background maintenance is off so .git is still when it is compared."""
    git(root, "init", "-q")
    for setting in ("gc.auto=0", "maintenance.auto=false"):
        git(root, "config", *setting.split("="))
    git(root, "add", "-A")
    git(root, "commit", "-qm", "fixture")
    return git(root, "rev-parse", "HEAD").strip()


needs_git = pytest.mark.skipif(shutil.which("git") is None, reason="git is required")


def test_receipt_dry_run_executes_and_writes_nothing(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    root, receipts = make(tmp_path / "repo", command="touch ran-anyway"), tmp_path / "receipts"
    before = digest(root)
    assert receipt_run(root, receipts) == 0
    assert digest(root) == before and not receipts.exists()
    assert "touch ran-anyway" in capsys.readouterr().out


def test_receipt_records_a_pass_outside_the_repository_and_leaves_it_untouched(tmp_path: Path) -> None:
    command = "echo observed > created-by-journey && cat created-by-journey"
    root, receipts = make(tmp_path / "repo", command=command, status="implementing", journey="not_run"), tmp_path / "receipts"
    before = digest(root)
    assert receipt_run(root, receipts, "--run", "--by", "a reviewer") == 0
    assert digest(root) == before, "neither the tool nor the journey may change the repository"
    found = read_receipt(receipts, root)
    assert found["format"] == verify.RECEIPT_FORMAT
    assert (found["repository"], found["path"], found["slice"]) == (root.name, str(root.resolve()), "demo-001")
    assert (found["result"], found["exit_code"], found["timed_out"]) == ("passed", 0, False)
    assert (found["ran_in"], found["head"], found["uncommitted_paths"]) == ("copy", None, None)
    assert found["command"] == command and found["command_sha256"] == hashlib.sha256(command.encode()).hexdigest()
    assert (found["recorded_journey"], found["slice_status"], found["by"]) == ("not_run", "implementing", "a reviewer")
    assert "observed" in (receipts / root.name / "demo-001.log").read_text()
    assert parsed(root)["current_slice"]["primary_journey"]["status"] == "not_run", "a receipt never edits the record"


def test_a_failing_receipt_run_changes_no_record_and_says_the_record_disagrees(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    root, receipts = make(tmp_path / "repo", command="echo broken; exit 3", status="validated", journey="passed"), tmp_path / "receipts"
    before = digest(root)
    assert receipt_run(root, receipts, "--run") == 1
    assert digest(root) == before, "an independent run never downgrades the slice; that is the writer's job"
    found = read_receipt(receipts, root)
    assert (found["result"], found["exit_code"], found["recorded_journey"], found["slice_status"]) == ("failed", 3, "passed", "validated")
    out = capsys.readouterr().out
    assert "records this journey as passed" in out and "broken" in out


def test_receipt_records_a_timeout_as_failed(tmp_path: Path) -> None:
    root, receipts = make(tmp_path / "repo", command="sleep 30"), tmp_path / "receipts"
    assert receipt_run(root, receipts, "--run", "--timeout", "0.3") == 1
    found = read_receipt(receipts, root)
    assert (found["result"], found["timed_out"], found["exit_code"]) == ("failed", True, 124)


@needs_git
def test_receipt_runs_the_committed_head_and_in_place_runs_the_working_tree(tmp_path: Path) -> None:
    root, receipts = make(tmp_path / "repo", command="grep -q committed marker.txt"), tmp_path / "receipts"
    (root / "marker.txt").write_text("committed\n")
    head = committed(root)
    (root / "marker.txt").write_text("changed later\n")
    before = digest(root)

    assert receipt_run(root, receipts, "--run") == 0, "the clone holds the committed file, so the journey passes"
    found = read_receipt(receipts, root)
    assert (found["ran_in"], found["head"], found["uncommitted_paths"], found["result"]) == ("clone-of-head", head, 1, "passed")
    assert digest(root) == before, "cloning and reading status must not write in the work tree or in .git"

    assert receipt_run(root, receipts, "--run", "--in-place") == 1, "the working tree holds the edit, so the journey fails"
    found = read_receipt(receipts, root)
    assert (found["ran_in"], found["head"], found["result"]) == ("working-tree", head, "failed")
    assert digest(root) == before


@needs_git
def test_receipt_treats_a_subdirectory_of_another_repository_as_unversioned(tmp_path: Path) -> None:
    outer = tmp_path / "outer"
    root, receipts = make(outer / "repo", command="exit 0"), tmp_path / "receipts"
    committed(outer)
    assert receipt_run(root, receipts, "--run") == 0
    found = read_receipt(receipts, root)
    assert (found["ran_in"], found["head"]) == ("copy", None), "HEAD of an enclosing repository is not this repository's HEAD"


def test_receipt_refuses_a_receipts_directory_inside_the_repository(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    root = make(tmp_path / "repo", command="touch ran-anyway")
    before = digest(root)
    assert receipt_run(root, root / "receipts", "--run") == 2
    assert digest(root) == before
    assert "inside the repository" in capsys.readouterr().err


def test_receipt_refuses_names_that_cannot_be_file_names(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    root, receipts = make(tmp_path / "re po", command="touch ran-anyway"), tmp_path / "receipts"
    assert receipt_run(root, receipts, "--run") == 2
    assert not receipts.exists() and not (root / "ran-anyway").exists()
    assert "cannot be used as a receipt file name" in capsys.readouterr().err


def test_in_place_without_receipt_is_a_usage_error(tmp_path: Path) -> None:
    root = make(tmp_path / "repo")
    with pytest.raises(SystemExit) as error:
        run(root, "--run", "--in-place")
    assert error.value.code == 2


# --- 6.5.0: a passed journey is what `validated` means, and the gate says how the record was made ----------------


def test_a_passing_journey_marks_an_open_slice_validated_and_prints_the_gate_verdict(
        tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    for status in ("planned", "implementing", "implemented"):
        root = make(tmp_path / status, command="echo ok", status=status)
        capsys.readouterr()
        assert run(root, "--run") == 0
        assert parsed(root)["current_slice"]["status"] == "validated"
        out = capsys.readouterr().out
        assert f"slice status set from {status} to validated" in out
        gate_part = out.split("--- gate ---\n", 1)[1]
        assert "RECORDED OUTCOME VALIDATED" in gate_part
        assert "- primary journey: recorded as passed by a run (scripts/projectstate_verify.py, 20" in gate_part
        assert "the next slice may start meanwhile" in gate_part
        stamp = gate.journey_run(root)
        assert stamp is not None and f"- Verified: {stamp} by scripts/projectstate_verify.py" in summary(root)
        assert (gate.validate(root)[0], gate.validate(root)[1]) == ([], [])


def test_a_passing_journey_leaves_a_blocked_or_closed_status_alone(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    for status in ("blocked", "validated", "ready_for_human"):
        root = make(tmp_path / status, command="echo ok", status=status)
        assert run(root, "--run") == 0
        assert parsed(root)["current_slice"]["status"] == status
        assert "slice status set" not in capsys.readouterr().out


def test_an_open_blocker_keeps_the_status_and_the_passing_journey_is_still_recorded(
        tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    root = make(tmp_path, command="echo ok", status="implementing")
    state = root / "STATE.yaml"
    state.write_text(state.read_text().replace("blockers: []\n", 'blockers:\n  - "The licence question is open."\n'))
    assert run(root, "--run") == 0
    after = parsed(root)
    assert after["current_slice"]["primary_journey"]["status"] == "passed"
    assert after["current_slice"]["status"] == "implementing"  # validated would claim more than the gate allows
    out = capsys.readouterr().out
    assert "slice status stays implementing: The licence question is open." in out
    assert "OUTCOME NOT VALIDATED" in out.split("--- gate ---\n", 1)[1]


def test_a_failing_journey_never_upgrades_and_the_gate_verdict_is_printed(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    root = make(tmp_path, command="exit 4", status="implementing")
    assert run(root, "--run") == 1
    assert parsed(root)["current_slice"]["status"] == "implementing"
    out = capsys.readouterr().out
    assert "primary journey is failed" in out.split("--- gate ---\n", 1)[1]
    assert gate.journey_run(root) is None  # a run is on record, but not of a passed journey


def test_the_gate_names_a_hand_typed_record_and_such_a_slice_waits_for_the_owner(
        tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    root = make(tmp_path, command="echo ok", status="validated", journey="passed")
    assert gate.main(["--root", str(root)]) == 0
    out = capsys.readouterr().out
    assert "- primary journey: recorded as passed, typed by hand (no run by scripts/projectstate_verify.py is on record)" in out
    assert "The journey was typed by hand, so this slice waits for the answer" in out
    assert gate.journey_run(root) is None
    path = root / "evidence" / "demo-001" / "summary.md"
    for line in ("- Verified: yesterday, by me", "- Verified: 2026-11-11 by scripts/projectstate_verify.py",
                 "- Verified: 2026-11-11T10:00:00Z by scripts/projectstate_verify.pyx"):
        path.write_text(summary_text("echo ok", "passed", "0", extra=line + "\n"))
        assert gate.journey_run(root) is None, line
    # the tool's own line, but under another heading, is not the journey's record
    path.write_text(summary_text("echo ok", "passed", "0").replace(
        "## Limitations\n", "## Limitations\n\n- Verified: 2026-11-11T10:00:00Z by scripts/projectstate_verify.py in 1.0s\n"))
    assert gate.journey_run(root) is None
    path.write_text(summary_text("echo ok", "passed", "0",
                                 extra="- Verified: 2026-11-11T10:00:00Z by scripts/projectstate_verify.py in 1.0s\n"))
    assert gate.journey_run(root) == "2026-11-11T10:00:00Z"


def test_a_new_line_joins_the_labelled_lines_and_not_the_prose_after_them(tmp_path: Path) -> None:
    prose = "\nThe journey drives the real command line.\nIt has two paragraphs.\n\nSecond paragraph.\n"
    root = make(tmp_path / "prose", command="echo ok", summary=summary_text("echo ok", extra=prose))
    assert run(root, "--run") == 0
    lines = summary(root).splitlines()
    verified = next(i for i, line in enumerate(lines) if line.startswith("- Verified: "))
    assert lines[verified - 1] == "- Exit code: 0" and lines[verified + 1] == ""
    assert lines[verified + 2] == "The journey drives the real command line."
    assert gate.journey_run(root) is not None
    # a section that has no labelled line at all still gets its lines, after the last text
    bare = ("# Evidence: demo-001\n\n## Primary journey\n\nNothing recorded yet.\n\n## Secondary checks\n\n- None.\n\n"
            "## Artifacts\n\n- None recorded.\n\n## Limitations\n\n- None.\n")
    root = make(tmp_path / "bare", command="echo ok", summary=bare)
    assert run(root, "--run") == 0
    text = summary(root)
    assert text.index("Nothing recorded yet.") < text.index("- Environment: ") < text.index("- Verified: ")
    assert text.index("- Verified: ") < text.index("## Secondary checks")
    assert gate.validate(root)[0] == []


# --- found by an independent review on 2026-11-11: the recorder is vendored now, so its paths are checked first ---


def test_a_slice_id_that_is_not_an_id_is_refused_before_anything_runs(tmp_path: Path) -> None:
    """The id names the evidence folder. An id such as ../../outside pointed the summary, the artifact and the
    recorded status outside the repository."""
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "summary.md").write_text(summary_text("touch ran.marker"))
    for bad in ("../../outside", "../outside", "a/b", "Demo-001", "demo_001", ".", ""):
        root = make(tmp_path / "repo" / f"case-{abs(hash(bad))}", command="touch ran.marker")
        state = root / "STATE.yaml"
        state.write_text(state.read_text().replace("  id: demo-001\n", f"  id: {json.dumps(bad)}\n"))
        before, outside_before = digest(root), digest(outside)
        assert run(root, "--run") == 2, bad
        assert digest(root) == before and digest(outside) == outside_before, bad
        assert not (root / "ran.marker").exists(), bad  # the journey command itself never ran


def test_a_relative_path_that_leaves_the_repository_is_never_a_regular_file_of_it(tmp_path: Path) -> None:
    (tmp_path / "repo").mkdir()
    (tmp_path / "secret.txt").write_text("outside")
    for relative in ("../secret.txt", "evidence/../../secret.txt", str(tmp_path / "secret.txt")):
        with pytest.raises(verify.Refused):
            verify.regular(tmp_path / "repo", relative)


def test_a_symlinked_artifact_is_refused_and_left_exactly_as_it_was(tmp_path: Path) -> None:
    elsewhere = tmp_path / "elsewhere.txt"
    elsewhere.write_text("not the repository's file")
    for name, target in (("live", elsewhere), ("dangling", tmp_path / "does-not-exist")):
        root = make(tmp_path / name, command="touch ran.marker")
        link = root / "evidence" / "demo-001" / verify.ARTIFACT
        link.symlink_to(target)
        before = digest(root)
        assert run(root, "--run") == 2
        assert link.is_symlink() and os.readlink(link) == str(target)  # a rollback used to delete a dangling link
        assert digest(root) == before and not (root / "ran.marker").exists()
    assert elsewhere.read_text() == "not the repository's file"


# --- second review, 2026-11-11 ------------------------------------------------------------------------------------


def test_a_run_line_beside_a_failed_record_is_not_a_passed_run(tmp_path: Path) -> None:
    """STATE.yaml says passed, the summary says failed and carries the tool's line: invalid, and not a run."""
    text = summary_text("echo ok", "failed", "1", extra="- Verified: 2026-11-11T10:00:00Z by scripts/projectstate_verify.py in 1.0s\n")
    root = make(tmp_path, command="echo ok", status="validated", journey="passed", summary=text)
    assert gate.validate(root)[0] != []
    assert gate.journey_run(root) is None


def test_a_journey_that_swaps_the_evidence_folder_for_a_symlink_records_nothing(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    root = make(tmp_path / "repo", command="mv evidence/demo-001 ../outside/moved && ln -s ../../outside/moved evidence/demo-001")
    state_before = (root / "STATE.yaml").read_bytes()
    assert run(root, "--run") == 2
    assert (root / "STATE.yaml").read_bytes() == state_before  # nothing recorded
    moved = outside / "moved"
    assert "- Result: not run" in (moved / "summary.md").read_text() and not (moved / verify.ARTIFACT).exists()
