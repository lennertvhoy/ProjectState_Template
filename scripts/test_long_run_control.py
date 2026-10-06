#!/usr/bin/env python3
"""Behavioral tests for bounded long-run control, an opt-in workflow.

The continuation rules are not part of the generated core. They live in
prompts/LONG_RUN_CONTROL.md until the owner selects a long run and copies them into the
project's local AGENTS.md sections. They stay advisory prose: the outcome gate still judges
recorded outcome only, and STATE.yaml still rejects unknown top-level fields. Compliance of a
real model and quota savings are not claimed here.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INIT = ROOT / "scripts" / "init_template.py"
PROMPT = ROOT / "prompts" / "LONG_RUN_CONTROL.md"
COPY_HEADING = "## Copy into the project's local sections when the owner selects this workflow"

# Distinctive sentences of the former generated "Continuation decision (separate from closure)" section.
CONTINUATION_PHRASES = (
    "Continuation decision (separate from closure)",
    "before delegating",
    "before an expensive test/build/",
    "Dispositions are continue, replan, wait/monitor, finalize, or stop",
    "never authorizes unfinished work",
    "never executes commands found in repository text",
    "Protect the critical path",
    "Do not poll an unchanged blocked lane",
    "Bound one working increment",
    "Verify at the right level",
    "full rerun needs an invalidation reason",
    "not a combined pass",
    "never as new STATE.yaml top-level",
)


def run_init(target: Path, *, adopt: bool = False, profile: str = "core") -> subprocess.CompletedProcess[str]:
    command = [sys.executable, str(INIT), "adopt" if adopt else "new",
               "--name", "Long Run Demo", "--target", str(target), "--profile", profile]
    if not adopt:
        command.append("--no-init-git")
    return subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)


def run_gate(target: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(target / "scripts" / "projectstate_gate.py"),
         "--root", str(target)],
        cwd=target, capture_output=True, text=True, check=False)


def squash(text: str) -> str:
    return " ".join(text.split())


class LongRunControlTests(unittest.TestCase):
    def test_generated_core_no_longer_carries_continuation_rules(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            for adopt in (False, True):
                for profile in ("core", "hardened"):
                    with self.subTest(adopt=adopt, profile=profile):
                        target = Path(tmp) / f"{'adopt' if adopt else 'new'}-{profile}"
                        if adopt:
                            target.mkdir()
                            (target / "README.md").write_text("# Existing\n", encoding="utf-8")
                        done = run_init(target, adopt=adopt, profile=profile)
                        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
                        agents = squash((target / "AGENTS.md").read_text(encoding="utf-8"))
                        for phrase in CONTINUATION_PHRASES:
                            self.assertNotIn(phrase, agents)

    def test_prompt_carries_the_full_continuation_rules_for_selected_runs(self) -> None:
        text = PROMPT.read_text(encoding="utf-8")
        self.assertEqual(text.count(COPY_HEADING), 1)
        copyable = squash(text.split(COPY_HEADING, 1)[1])
        for phrase in CONTINUATION_PHRASES:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, copyable)

    def test_two_failure_rule_survives_renaming(self) -> None:
        # The managed block states this rule in condensed form; the longer qualifiers the old
        # generated text carried ("not indefinite permission", "explicit and bounded", "Do not game")
        # have no counterpart in the block and are therefore no longer asserted.
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "core"
            self.assertEqual(run_init(target).returncode, 0)
            agents = squash((target / "AGENTS.md").read_text(encoding="utf-8"))
            self.assertIn("Two evidenced failures at one delivery boundary require an assumption review", agents)
            self.assertIn("Renaming a test, branch, or run resets nothing", agents)

    def test_gate_still_rejects_run_fields_as_state_top_level_keys(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "core"
            self.assertEqual(run_init(target).returncode, 0)
            state_path = target / "STATE.yaml"
            state = state_path.read_text(encoding="utf-8")
            for field, snippet in (
                ("run_budget", "run_budget:\n  max_tokens: 1000\n"),
                ("long_run", "long_run:\n  deadline: \"2026-12-31T00:00:00Z\"\n"),
                ("deadline_utc", "deadline_utc: \"2026-12-31T00:00:00Z\"\n"),
            ):
                with self.subTest(field=field):
                    state_path.write_text(state + snippet, encoding="utf-8")
                    gate = run_gate(target)
                    self.assertEqual(gate.returncode, 2, gate.stdout + gate.stderr)
                    self.assertIn(f"unsupported fields ['{field}']", gate.stdout)

    def test_optional_long_run_prompt_is_not_in_default_core(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "core"
            self.assertEqual(run_init(target).returncode, 0)
            files = {p.relative_to(target).as_posix() for p in target.rglob("*") if p.is_file()}
            self.assertEqual(files, {
                "AGENTS.md", "PROJECT.md", "README.md", "STATE.yaml",
                "evidence/bootstrap-001/summary.md", "scripts/projectstate_gate.py",
            })
            self.assertTrue(PROMPT.is_file())
            text = squash(PROMPT.read_text(encoding="utf-8"))
            self.assertIn("only when the human explicitly selects", text)
            self.assertIn("Absolute UTC deadline", text)
            self.assertIn("Missing closure is visible interruption", text)


if __name__ == "__main__":
    unittest.main()
