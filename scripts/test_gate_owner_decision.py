#!/usr/bin/env python3
"""Tests for the gate's owner-decision record, `waived`, soft-limit warnings, and --version.

Fixtures are hand-built in temporary directories so these tests do not depend on what
`init_template.py` generates. The gate is always run as a subprocess against a fixture; the
real repository files are never modified.
"""

from __future__ import annotations

import datetime as dt
import importlib.util
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "scripts" / "projectstate_gate.py"
RELEASE_TOOL = ROOT / "scripts" / "projectstate_release.py"
START = "<!-- projectstate:managed:start release=6.3.0 -->"
END = "<!-- projectstate:managed:end -->"
PENDING_LINE = "- owner decision: pending; ask the owner to accept, reject, or waive"
VALIDATED_LINES = [
    "RECORDED OUTCOME VALIDATED",
    "- primary journey: recorded as passed",
    "- secondary checks: do not override the primary journey",
    "- this gate does not execute journeys or authenticate human approval",
]
NO_BLOCK_WARNING = (
    "WARN: AGENTS.md has no managed ProjectState block; "
    "update it with the template's scripts/projectstate_update.py"
)
TODAY = dt.date.today().isoformat()
SUMMARY_PATH = "evidence/demo-001/summary.md"
# Typographic quotes by name: they look alike in review. None of them may count as the owner's words.
LEFT_DQ, RIGHT_DQ = "\N{LEFT DOUBLE QUOTATION MARK}", "\N{RIGHT DOUBLE QUOTATION MARK}"
LEFT_SQ, RIGHT_SQ = "\N{LEFT SINGLE QUOTATION MARK}", "\N{RIGHT SINGLE QUOTATION MARK}"
LEFT_GUILLEMET = "\N{LEFT-POINTING DOUBLE ANGLE QUOTATION MARK}"
RIGHT_GUILLEMET = "\N{RIGHT-POINTING DOUBLE ANGLE QUOTATION MARK}"
# 2026-01-15 in Arabic-Indic digits: a regex \d matches them, so the gate must not rely on \d alone.
ARABIC_INDIC_DATE = "".join(chr(0x0660 + int(char)) if char.isdigit() else char for char in "2026-01-15")

STATE = """\
version: "projectstate-template-v6"
profile: core
project:
  outcome_ref: "PROJECT.md#outcome"
current_slice:
  id: demo-001
  objective: "Deliver the demo outcome."
  status: validated
  acceptance:
    - "The demo runs end to end."
  primary_journey:
    description: "Run the demo."
    command: "python3 demo.py"
    environment: "local test fixture"
    status: passed
    evidence: "evidence/demo-001/summary.md"
validation:
  primary_journey: passed
  automated_tests: passed
  human_acceptance: pending
delivery_boundary:
  name: demo_delivery
  failed_attempts: []
  simplification_review: null
blockers: []
risks: []
next_action: "Ask the owner to decide."
"""

PROJECT = """\
# Demo project

## User

A student using the demo.

## Outcome

The demo runs end to end.

## Scope

One demo.

## Non-goals

Anything else.

## Durable constraints

Standard library only.
"""

SUMMARY = """\
# Evidence: demo-001

## Primary journey

- Environment: local test fixture
- Command: `python3 demo.py`
- Result: passed
- Exit code: 0

## Secondary checks

- None.

## Artifacts

- None.

## Limitations

- None.
"""

AGENTS = f"""\
{START}
# ProjectState contract

Managed text lives here.
{END}

## Local rules

- Keep the demo small.
"""


def load_module(name: str, path: Path) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def owner_section(
    decision: str | None = "accepted", date: str | None = TODAY, words: str | None = '"Looks right to me."'
) -> str:
    """An `## Owner decision` section; a field set to None is left out entirely."""
    lines = ["", "## Owner decision", ""]
    for label, value in (("Decision", decision), ("Date", date), ("Owner words", words)):
        if value is not None:
            lines.append(f"- {label}: {value}")
    return "\n".join(lines) + "\n"


def agents_text(before: int = 0, block: int | None = 3, after: int = 0, frontmatter: str = "") -> str:
    """AGENTS.md with `before`/`after` local lines around a managed block of `block` content lines."""
    parts = [frontmatter] if frontmatter else []
    parts += [f"local rule {number}\n" for number in range(before)]
    if block is not None:
        parts.append(START + "\n" + "".join(f"managed line {number}\n" for number in range(block)) + END + "\n")
    parts += [f"local rule {before + number}\n" for number in range(after)]
    return "".join(parts)


class GateFixture(unittest.TestCase):
    """A throwaway project the gate can validate; each test edits files in place."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "project"
        self.fresh()

    def fresh(self) -> None:
        """(Re)write the baseline project: validated, pending acceptance, managed block present."""
        (self.root / "evidence" / "demo-001").mkdir(parents=True, exist_ok=True)
        for relative, text in (
            ("STATE.yaml", STATE), ("PROJECT.md", PROJECT), (SUMMARY_PATH, SUMMARY), ("AGENTS.md", AGENTS),
        ):
            (self.root / relative).write_text(text, encoding="utf-8")

    def edit(self, relative: str, old: str, new: str) -> None:
        path = self.root / relative
        text = path.read_text(encoding="utf-8")
        self.assertIn(old, text, f"fixture edit would be a no-op: {old!r} not in {relative}")
        path.write_text(text.replace(old, new, 1), encoding="utf-8")

    def append(self, relative: str, text: str) -> None:
        path = self.root / relative
        path.write_text(path.read_text(encoding="utf-8") + text, encoding="utf-8")

    def decide(self, human: str, slice_status: str | None = None) -> None:
        self.edit("STATE.yaml", "human_acceptance: pending", f"human_acceptance: {human}")
        if slice_status is not None:
            self.edit("STATE.yaml", "status: validated", f"status: {slice_status}")

    def set_journey(self, status: str) -> None:
        """Record the primary journey as `status`; the slice drops to `implemented` (closure needs a pass)."""
        self.edit("STATE.yaml", "status: passed", f"status: {status}")
        self.edit("STATE.yaml", "primary_journey: passed", f"primary_journey: {status}")
        self.edit("STATE.yaml", "status: validated", "status: implemented")
        self.edit(SUMMARY_PATH, "- Result: passed\n- Exit code: 0", f"- Result: {status}\n- Exit code: 1")

    def pad(self, relative: str, size: int, comment: tuple[str, str]) -> None:
        """Grow a file to exactly `size` bytes with a trailing comment the parsers ignore."""
        path = self.root / relative
        gap = size - path.stat().st_size
        opener, closer = comment
        overhead = len(opener) + len(closer) + 1
        self.assertGreaterEqual(gap, overhead, "fixture is already larger than the target size")
        filler = opener + "y" * (gap - overhead) + closer + "\n"
        path.write_text(path.read_text(encoding="utf-8") + filler, encoding="utf-8")
        self.assertEqual(path.stat().st_size, size)

    def gate(self, *args: str) -> subprocess.CompletedProcess[str]:
        completed = subprocess.run(
            [sys.executable, str(GATE), "--root", str(self.root), *args],
            cwd=self._tmp.name, capture_output=True, text=True, check=False,
        )
        self.assertNotIn("Traceback", completed.stderr, completed.stderr)
        return completed

    def assertExit(self, expected: int, *, message: str = "") -> subprocess.CompletedProcess[str]:
        completed = self.gate()
        self.assertEqual(completed.returncode, expected, f"{message}\n{completed.stdout}{completed.stderr}")
        return completed

    @staticmethod
    def warnings(completed: subprocess.CompletedProcess[str]) -> list[str]:
        return [line for line in completed.stdout.splitlines() if line.startswith("WARN:")]


class BaselineTests(GateFixture):
    def test_baseline_fixture_is_valid_and_warning_free(self) -> None:
        completed = self.assertExit(0)
        self.assertEqual(self.warnings(completed), [])

    def test_pending_validates_and_asks_the_owner_after_the_existing_lines(self) -> None:
        completed = self.assertExit(0)
        self.assertEqual(completed.stdout.splitlines(), VALIDATED_LINES + [PENDING_LINE])

    def test_pending_line_is_only_printed_on_a_validated_result(self) -> None:
        self.set_journey("failed")
        not_validated = self.assertExit(1)
        self.assertNotIn("owner decision", not_validated.stdout)
        self.fresh()
        self.edit("STATE.yaml", "profile: core", "profile: bogus")
        invalid = self.assertExit(2)
        self.assertNotIn("owner decision", invalid.stdout)


class OwnerDecisionTests(GateFixture):
    def test_every_decision_needs_a_matching_record(self) -> None:
        # (human_acceptance, slice status, recorded Decision or None for no section, expected exit)
        matrix = [
            ("accepted", "accepted", None, 2), ("accepted", "accepted", "accepted", 0),
            ("accepted", "accepted", "rejected", 2), ("accepted", "accepted", "waived", 2),
            ("accepted", "accepted", "pending", 2),
            ("rejected", "validated", None, 2), ("rejected", "validated", "rejected", 1),
            ("rejected", "validated", "accepted", 2), ("rejected", "validated", "waived", 2),
            ("waived", "validated", None, 2), ("waived", "validated", "waived", 0),
            ("waived", "validated", "accepted", 2), ("waived", "validated", "rejected", 2),
        ]
        for human, slice_status, decision, expected in matrix:
            with self.subTest(human=human, decision=decision):
                self.fresh()
                self.decide(human, slice_status)
                if decision is not None:
                    self.append(SUMMARY_PATH, owner_section(decision=decision))
                completed = self.assertExit(expected)
                if expected == 2:
                    self.assertIn("Owner decision", completed.stdout)

    def test_decided_results_do_not_ask_the_owner_again(self) -> None:
        self.decide("accepted", "accepted")
        self.append(SUMMARY_PATH, owner_section("accepted"))
        self.assertNotIn("owner decision", self.assertExit(0).stdout)
        self.fresh()
        self.decide("waived")
        self.append(SUMMARY_PATH, owner_section("waived"))
        self.assertNotIn("owner decision", self.assertExit(0).stdout)

    def test_pending_with_any_owner_decision_section_is_an_error(self) -> None:
        for name, section in (
            ("matching-looking", owner_section("pending")),
            ("other decision", owner_section("accepted")),
            ("empty section", "\n## Owner decision\n"),
            ("different case", "\n## OWNER DECISION\n\n- Decision: accepted\n"),
        ):
            with self.subTest(section=name):
                self.fresh()
                self.append(SUMMARY_PATH, section)
                completed = self.assertExit(2)
                self.assertIn("pending", completed.stdout)
                self.assertIn("disagree", completed.stdout)

    def test_pending_ignores_an_owner_decision_that_is_only_a_comment_or_a_subheading(self) -> None:
        self.append(SUMMARY_PATH, "\n<!--\n" + owner_section("accepted") + "-->\n")
        self.append(SUMMARY_PATH, "\n### Owner decision\n\n- Decision: accepted\n")
        self.assertExit(0)

    def test_record_must_be_a_section_of_the_slice_summary(self) -> None:
        for name, place in (
            ("html comment", lambda: self.append(SUMMARY_PATH, "\n<!--\n" + owner_section("accepted") + "-->\n")),
            ("subheading", lambda: self.append(SUMMARY_PATH, "\n### Owner decision\n\n- Decision: accepted\n")),
            ("bullets inside another section", lambda: self.edit(
                SUMMARY_PATH, "## Limitations\n\n- None.\n",
                "## Limitations\n\n- Decision: accepted\n- Date: " + TODAY + "\n- Owner words: \"fine\"\n")),
            ("project file", lambda: self.append("PROJECT.md", owner_section("accepted"))),
        ):
            with self.subTest(place=name):
                self.fresh()
                self.decide("accepted", "accepted")
                place()
                self.assertIn("no ## Owner decision section", self.assertExit(2).stdout)

    def test_record_in_a_decided_state_cannot_hide_behind_duplicate_sections(self) -> None:
        self.decide("accepted", "accepted")
        self.append(SUMMARY_PATH, owner_section("accepted") + owner_section("accepted"))
        self.assertIn("duplicate", self.assertExit(2).stdout)

    def test_decision_line_must_be_present_once_and_equal_the_state(self) -> None:
        for name, section, needle in (
            ("missing", owner_section(decision=None), "'- Decision:' line"),
            ("duplicated", owner_section("accepted") + "- Decision: accepted\n", "'- Decision:' line"),
            ("differs", owner_section("rejected"), "records 'rejected'"),
            ("different case", owner_section("Accepted"), "records 'Accepted'"),
            ("quoted", owner_section('"accepted"'), "records"),
            ("blank", owner_section(""), "records ''"),
        ):
            with self.subTest(decision=name):
                self.fresh()
                self.decide("accepted", "accepted")
                self.append(SUMMARY_PATH, section)
                self.assertIn(needle, self.assertExit(2).stdout)

    def test_date_line_must_be_present_once_and_be_an_iso_date_not_in_the_future(self) -> None:
        future = (dt.date.today() + dt.timedelta(days=2)).isoformat()
        for name, section, needle in (
            ("missing", owner_section(date=None), "'- Date:' line"),
            ("duplicated", owner_section() + "- Date: 2020-01-01\n", "'- Date:' line"),
            ("blank", owner_section(date=""), "ISO date"),
            ("word", owner_section(date="yesterday"), "ISO date"),
            ("month 13", owner_section(date="2026-13-01"), "ISO date"),
            ("day 30 of february", owner_section(date="2026-02-30"), "ISO date"),
            ("basic format", owner_section(date="20260115"), "ISO date"),
            ("week date", owner_section(date="2026-W03-4"), "ISO date"),
            ("slashes", owner_section(date="06/10/2026"), "ISO date"),
            ("datetime", owner_section(date="2026-01-15T10:00:00"), "ISO date"),
            ("non-ascii digits", owner_section(date=ARABIC_INDIC_DATE), "ISO date"),
            ("future", owner_section(date=future), "in the future"),
            ("far future", owner_section(date="2999-12-31"), "in the future"),
        ):
            with self.subTest(date=name):
                self.fresh()
                self.decide("accepted", "accepted")
                self.append(SUMMARY_PATH, section)
                self.assertIn(needle, self.assertExit(2).stdout)

    def test_past_and_current_dates_are_accepted(self) -> None:
        for date in (TODAY, "2026-01-15", "2000-02-29", f"`{TODAY}`"):
            with self.subTest(date=date):
                self.fresh()
                self.decide("accepted", "accepted")
                self.append(SUMMARY_PATH, owner_section(date=date))
                self.assertExit(0)

    def test_date_boundary_is_today_not_tomorrow(self) -> None:
        """Deterministic: freeze the gate's clock instead of racing midnight in a subprocess."""
        gate = load_module("projectstate_gate_clock", GATE)

        class Frozen(dt.date):
            @classmethod
            def today(cls) -> "Frozen":
                return cls(2026, 10, 6)

        gate.dt = types.SimpleNamespace(date=Frozen)
        for date, expect_error in (("2026-10-05", False), ("2026-10-06", False), ("2026-10-07", True)):
            with self.subTest(date=date):
                self.fresh()
                self.decide("accepted", "accepted")
                self.append(SUMMARY_PATH, owner_section(date=date))
                errors, _, _ = gate.validate(self.root)
                self.assertEqual(any("future" in error for error in errors), expect_error, errors)
                self.assertEqual(bool(errors), expect_error, errors)

    def test_owner_words_must_be_present_once_and_non_empty_after_stripping_quotes(self) -> None:
        for name, section, needle in (
            ("missing", owner_section(words=None), "'- Owner words:' line"),
            ("duplicated", owner_section() + '- Owner words: "again"\n', "'- Owner words:' line"),
            ("blank", owner_section(words=""), "not be empty"),
            ("spaces", owner_section(words="   "), "not be empty"),
            ("empty double quotes", owner_section(words='""'), "not be empty"),
            ("empty single quotes", owner_section(words="''"), "not be empty"),
            ("quoted spaces", owner_section(words='"  "'), "not be empty"),
            ("empty backticks", owner_section(words="``"), "not be empty"),
            ("typographic quotes", owner_section(words=LEFT_DQ + RIGHT_DQ), "not be empty"),
            ("mixed quotes and spaces", owner_section(words=f"{LEFT_SQ} \" ' {RIGHT_SQ}"), "not be empty"),
            ("guillemets", owner_section(words=f"{LEFT_GUILLEMET} {RIGHT_GUILLEMET}"), "not be empty"),
        ):
            with self.subTest(words=name):
                self.fresh()
                self.decide("accepted", "accepted")
                self.append(SUMMARY_PATH, section)
                self.assertIn(needle, self.assertExit(2).stdout)

    def test_owner_words_with_content_are_accepted_however_they_are_quoted(self) -> None:
        for words in ('"Looks right to me."', "Looks right to me.", "'ok'", f"{LEFT_DQ}ok{RIGHT_DQ}", "`ok`",
                      'He said "ship it"'):
            with self.subTest(words=words):
                self.fresh()
                self.decide("accepted", "accepted")
                self.append(SUMMARY_PATH, owner_section(words=words))
                self.assertExit(0)

    def test_labels_tolerate_spacing_but_the_record_still_needs_all_three(self) -> None:
        self.decide("accepted", "accepted")
        self.append(
            SUMMARY_PATH,
            f"\n## Owner decision\n\n-   Decision:   accepted   \n- Date:{TODAY}\n- Owner words:\"ok\"\n",
        )
        self.assertExit(0)

    def test_rejected_owner_decision_works_whatever_the_journey_status(self) -> None:
        for journey in ("failed", "blocked", "not_run"):
            with self.subTest(journey=journey):
                self.fresh()
                self.set_journey(journey)
                self.decide("rejected")
                without = self.assertExit(2)
                self.assertIn("no ## Owner decision section", without.stdout)
                self.append(SUMMARY_PATH, owner_section("rejected", words='"This is not what I asked for."'))
                with_record = self.assertExit(1)
                self.assertIn(f"primary journey is {journey}", with_record.stdout)
                self.assertIn("human product acceptance is rejected", with_record.stdout)

    def test_waived_and_rejected_records_are_honest_beside_a_failed_journey(self) -> None:
        for human in ("waived", "rejected"):
            with self.subTest(human=human):
                self.fresh()
                self.set_journey("failed")
                self.decide(human)
                self.append(SUMMARY_PATH, owner_section(human))
                completed = self.assertExit(1)
                self.assertIn("primary journey is failed", completed.stdout)

    def test_accepted_beside_a_failed_journey_fails_on_the_status_rule_not_the_record(self) -> None:
        self.set_journey("failed")
        self.decide("accepted")
        self.append(SUMMARY_PATH, owner_section("accepted"))
        completed = self.assertExit(2)
        self.assertIn("human acceptance requires current_slice.status: accepted", completed.stdout)
        self.assertNotIn("## Owner decision", completed.stdout)

    def test_owner_decision_does_not_replace_the_primary_journey_result(self) -> None:
        """A decision record is never evidence of the journey; an unrecorded pass stays invalid."""
        self.decide("accepted", "accepted")
        self.append(SUMMARY_PATH, owner_section("accepted"))
        self.edit(SUMMARY_PATH, "- Result: passed", "- Result: failed")
        self.assertIn("Result: passed", self.assertExit(2).stdout)


class WaivedTests(GateFixture):
    def test_waived_is_a_valid_value_and_adds_no_blocker(self) -> None:
        self.decide("waived")
        self.append(SUMMARY_PATH, owner_section("waived", words='"Not worth a review; ship it."'))
        completed = self.assertExit(0)
        self.assertEqual(completed.stdout.splitlines(), VALIDATED_LINES)

    def test_slice_status_accepted_still_requires_human_acceptance_accepted(self) -> None:
        self.decide("waived", "accepted")
        self.append(SUMMARY_PATH, owner_section("waived"))
        completed = self.assertExit(2)
        self.assertIn("current_slice.status: accepted requires explicit human acceptance", completed.stdout)

    def test_human_acceptance_accepted_still_requires_slice_status_accepted(self) -> None:
        self.decide("accepted")
        self.append(SUMMARY_PATH, owner_section("accepted"))
        completed = self.assertExit(2)
        self.assertIn("human acceptance requires current_slice.status: accepted", completed.stdout)

    def test_unknown_acceptance_values_are_still_rejected_without_cascading_errors(self) -> None:
        for value in ("maybe", "Waived", "waive", "[]", "{}", "null"):
            with self.subTest(value=value):
                self.fresh()
                self.decide(value)
                self.append(SUMMARY_PATH, owner_section("accepted"))
                completed = self.assertExit(2)
                self.assertIn("validation.human_acceptance is invalid", completed.stdout)
                self.assertNotIn("Owner decision", completed.stdout)


class VersionTests(unittest.TestCase):
    def test_version_prints_the_release_and_state_schema_and_exits_zero(self) -> None:
        gate = load_module("projectstate_gate_version", GATE)
        expected = f"projectstate-gate {gate.RELEASE} (state schema {gate.VERSION})"
        with tempfile.TemporaryDirectory() as tmp:
            completed = subprocess.run(
                [sys.executable, str(GATE), "--version"], cwd=tmp, capture_output=True, text=True, check=False
            )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stdout, expected + "\n")
        self.assertEqual(completed.stderr, "")

    def test_version_reads_no_files_and_ignores_the_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "does-not-exist"
            broken = Path(tmp) / "broken"
            broken.mkdir()
            (broken / "STATE.yaml").write_bytes(b"\xff\xfe not yaml")
            outputs = set()
            for root in (missing, broken):
                completed = subprocess.run(
                    [sys.executable, str(GATE), "--root", str(root), "--version"],
                    cwd=tmp, capture_output=True, text=True, check=False,
                )
                self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
                outputs.add(completed.stdout)
            self.assertEqual(len(outputs), 1)
            self.assertFalse(missing.exists())

    def test_version_is_one_line_whatever_the_terminal_width(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            completed = subprocess.run(
                [sys.executable, str(GATE), "--version"], cwd=tmp, capture_output=True, text=True, check=False,
                env={"COLUMNS": "10", "PATH": "/usr/bin:/bin"},
            )
        self.assertEqual(len(completed.stdout.splitlines()), 1, completed.stdout)


class SoftLimitWarningTests(GateFixture):
    def test_state_over_16384_bytes_warns_without_changing_the_exit_code(self) -> None:
        for size, warns in ((16384, False), (16385, True), (65536, True)):
            with self.subTest(size=size):
                self.fresh()
                self.pad("STATE.yaml", size, ("# ", ""))
                completed = self.assertExit(0)
                self.assertEqual(any(f"STATE.yaml is {size} bytes" in line for line in self.warnings(completed)), warns)
                if warns:
                    self.assertIn("16384", "".join(self.warnings(completed)))

    def test_state_over_65536_bytes_keeps_its_error_and_also_warns(self) -> None:
        self.pad("STATE.yaml", 65537, ("# ", ""))
        completed = self.assertExit(2)
        self.assertIn("(max 65536)", completed.stdout)
        self.assertIn("current-state view", completed.stdout)
        self.assertEqual(len(self.warnings(completed)), 1)

    def test_project_over_6144_bytes_warns_without_changing_the_exit_code(self) -> None:
        for size, warns in ((6144, False), (6145, True), (20000, True)):
            with self.subTest(size=size):
                self.fresh()
                self.pad("PROJECT.md", size, ("<!--", "-->"))
                completed = self.assertExit(0)
                self.assertEqual(any(f"PROJECT.md is {size} bytes" in line for line in self.warnings(completed)), warns)
                if warns:
                    self.assertIn("6144", "".join(self.warnings(completed)))

    def test_agents_without_a_managed_block_warns_with_the_exact_text(self) -> None:
        (self.root / "AGENTS.md").write_text("# Local rules only\n\n- Keep it small.\n", encoding="utf-8")
        completed = self.assertExit(0)
        self.assertEqual(self.warnings(completed), [NO_BLOCK_WARNING])
        self.assertTrue(completed.stdout.startswith(NO_BLOCK_WARNING + "\n"))

    def test_agents_with_a_managed_block_does_not_warn(self) -> None:
        self.assertNotIn(NO_BLOCK_WARNING, self.assertExit(0).stdout)

    def test_agents_lines_outside_block_and_frontmatter_are_limited_to_150(self) -> None:
        frontmatter = "---\nproject: demo\nrepo_role: demo\n---\n"
        cases = (
            # name, AGENTS.md text, expected local line count (None = no warning)
            ("150 local lines around a large block", agents_text(100, 80, 50), None),
            ("151 local lines around a large block", agents_text(100, 80, 51), 151),
            ("block lines never count", agents_text(0, 5000, 10), None),
            ("frontmatter does not count", agents_text(150, 3, 0, frontmatter), None),
            ("frontmatter plus one extra line", agents_text(151, 3, 0, frontmatter), 151),
            ("unclosed frontmatter counts as content", agents_text(150, 3, 0, "---\nproject: demo\n"), 152),
            # One blank line first, so the frontmatter-looking lines (4) are content: 1 + 4 + 146 = 151.
            ("frontmatter must lead the file", agents_text(146, 3, 0, "\n" + frontmatter), 151),
            ("no block counts every line", agents_text(150, None, 0), None),
            ("no block, 151 lines", agents_text(151, None, 0), 151),
            ("no trailing newline", agents_text(150, 3, 0).rstrip("\n") + "\nlast", 151),
        )
        for name, text, local in cases:
            with self.subTest(case=name):
                (self.root / "AGENTS.md").write_text(text, encoding="utf-8")
                completed = self.assertExit(0)
                lines = [line for line in self.warnings(completed) if "lines outside" in line]
                if local is None:
                    self.assertEqual(lines, [])
                else:
                    self.assertEqual(len(lines), 1, completed.stdout)
                    self.assertIn(f"AGENTS.md has {local} lines outside the managed block and frontmatter", lines[0])
                    self.assertIn("150", lines[0])

    def test_unmanaged_agents_over_the_limit_gets_both_warnings(self) -> None:
        (self.root / "AGENTS.md").write_text(agents_text(200, None, 0), encoding="utf-8")
        completed = self.assertExit(0)
        self.assertEqual(len(self.warnings(completed)), 2, completed.stdout)
        self.assertIn(NO_BLOCK_WARNING, completed.stdout)

    def test_warnings_never_change_the_exit_code_and_print_before_the_verdict(self) -> None:
        self.pad("STATE.yaml", 20000, ("# ", ""))
        self.pad("PROJECT.md", 7000, ("<!--", "-->"))
        (self.root / "AGENTS.md").write_text(agents_text(200, None, 0), encoding="utf-8")
        passing = self.assertExit(0)
        self.assertEqual(len(self.warnings(passing)), 4, passing.stdout)
        first_verdict = passing.stdout.splitlines().index("RECORDED OUTCOME VALIDATED")
        self.assertEqual(first_verdict, 4)
        self.set_journey("failed")
        failing = self.assertExit(1)
        self.assertEqual(len(self.warnings(failing)), 4, failing.stdout)
        self.assertEqual(failing.stdout.splitlines()[4], "OUTCOME NOT VALIDATED")

    def test_warnings_ride_along_with_errors(self) -> None:
        self.pad("STATE.yaml", 20000, ("# ", ""))
        self.edit("STATE.yaml", "profile: core", "profile: bogus")
        completed = self.assertExit(2)
        self.assertIn("INVALID PROJECTSTATE CORE", completed.stdout)
        self.assertEqual(len(self.warnings(completed)), 1)


class ManagedMarkerTests(GateFixture):
    def test_malformed_markers_are_an_error(self) -> None:
        cases = {
            "two starts": f"{START}\nx\n{START}\ny\n{END}\n",
            "two ends": f"{START}\nx\n{END}\n{END}\n",
            "two complete blocks": f"{START}\nx\n{END}\n{START}\ny\n{END}\n",
            "end before start": f"{END}\nx\n{START}\n",
            "start only": f"{START}\nx\n",
            "end only": f"x\n{END}\n",
            "marker mentioned in prose after a valid block": f"{START}\nx\n{END}\nSee projectstate:managed:start.\n",
            "marker mentioned in prose without a block": "Mentions projectstate:managed: markers.\n",
            "unparseable release in start": f"<!-- projectstate:managed:start release=latest -->\nx\n{END}\n",
            "trailing space on end marker": f"{START}\nx\n{END} \n",
            "indented start marker": f" {START}\nx\n{END}\n",
            "unknown marker kind": f"{START}\nx\n{END}\n<!-- projectstate:managed:middle -->\n",
        }
        for name, text in cases.items():
            with self.subTest(case=name):
                (self.root / "AGENTS.md").write_text(text, encoding="utf-8")
                completed = self.assertExit(2)
                self.assertIn("malformed managed block markers", completed.stdout)
                self.assertNotIn(NO_BLOCK_WARNING, completed.stdout)

    def test_well_formed_block_is_accepted_in_any_position(self) -> None:
        for name, text in (
            ("block first", agents_text(0, 4, 4)),
            ("block last", agents_text(4, 4, 0)),
            ("block only", agents_text(0, 4, 0)),
            ("empty block", agents_text(2, 0, 2)),
            ("after frontmatter", agents_text(2, 4, 2, "---\nrepo_role: demo\n---\n")),
        ):
            with self.subTest(case=name):
                (self.root / "AGENTS.md").write_text(text, encoding="utf-8")
                completed = self.assertExit(0)
                self.assertEqual(self.warnings(completed), [])

    def test_block_with_crlf_line_endings_is_recognised(self) -> None:
        (self.root / "AGENTS.md").write_bytes(agents_text(2, 4, 2).replace("\n", "\r\n").encode("utf-8"))
        completed = self.assertExit(0)
        self.assertEqual(self.warnings(completed), [])

    def test_markers_match_the_release_tool_and_the_gate_stays_standalone(self) -> None:
        gate = load_module("projectstate_gate_markers", GATE)
        release = load_module("projectstate_release_markers", RELEASE_TOOL)
        for name in ("START_MARKER", "END_MARKER"):
            with self.subTest(marker=name):
                self.assertEqual(getattr(gate, name).pattern, getattr(release, name).pattern)
                self.assertEqual(getattr(gate, name).flags, getattr(release, name).flags)
        completed = subprocess.run(
            [sys.executable, "-I", "-c",
             "import sys; sys.path.insert(0, sys.argv[1]); import projectstate_gate; "
             "print(any(name.startswith('projectstate_release') for name in sys.modules))",
             str(GATE.parent)],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(completed.stdout.strip(), "False", completed.stderr)

    def test_symlinked_agents_is_rejected_unread(self) -> None:
        outside = Path(self._tmp.name) / "outside-agents.md"
        outside.write_text(agents_text(0, 3, 0), encoding="utf-8")
        (self.root / "AGENTS.md").unlink()
        (self.root / "AGENTS.md").symlink_to(outside)
        completed = self.assertExit(2)
        self.assertIn("AGENTS.md is symlinked", completed.stdout)
        self.assertNotIn("managed", completed.stdout)

    def test_unreadable_agents_is_an_error_not_a_crash(self) -> None:
        (self.root / "AGENTS.md").write_bytes(b"\xff\xfe\x00 not utf-8 \xc3\x28\n")
        completed = self.assertExit(2)
        self.assertIn("cannot read AGENTS.md", completed.stdout)


if __name__ == "__main__":
    unittest.main()
