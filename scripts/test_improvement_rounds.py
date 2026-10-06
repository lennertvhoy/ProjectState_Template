#!/usr/bin/env python3
"""Behavioral tests for optional measured improvement rounds.

The optional asset must stay out of the generated default, and its mechanical
guards (stop rule, protected paths, instruction files that may only shrink,
verbatim measure output, token cap, patch verification) must hold against the
adversarial records a self-improving agent could produce. Compliance of a real
model, and whether rounds improve any instance, are not claimed here.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INIT = ROOT / "scripts" / "init_template.py"
CHECK = ROOT / "scripts" / "projectstate_improve_check.py"
TEMPLATE = ROOT / "prompts" / "IMPROVE_MD_TEMPLATE.md"
GUIDE = ROOT / "prompts" / "IMPROVEMENT_ROUNDS.md"

CONFIG = {
    "enabled": "true",
    "instance_type": "study",
    "measure_name": "coverage",
    "measure_command": "python3 scripts/measure.py",
    "measure_direction": "higher",
    "baseline_value": "0.40",
    "baseline_observed_on": "2026-10-06",
    "min_gain": "0.02",
    "stop_after_rounds": "3",
    "round_token_cap": "1000",
    "protected": "scripts/measure.py",
}


def front_matter(**overrides: str | None) -> str:
    values = {**CONFIG, **overrides}
    lines = [f"{key}: {value}" for key, value in values.items() if value is not None]
    return "---\n" + "\n".join(lines) + "\n---\n\n# Improve\n"


def make_instance(tmp: str, **overrides: str | None) -> Path:
    target = Path(tmp) / "instance"
    done = subprocess.run(
        [sys.executable, str(INIT), "new", "--name", "Improve Demo", "--target", str(target), "--no-init-git"],
        cwd=ROOT, capture_output=True, text=True, check=False)
    assert done.returncode == 0, done.stdout + done.stderr
    shutil.copy(CHECK, target / "scripts" / "projectstate_improve_check.py")
    (target / "scripts" / "measure.py").write_text(
        "from pathlib import Path\nPath('RAN').write_text('x')\nprint('coverage 0.40')\n", encoding="utf-8")
    (target / "IMPROVE.md").write_text(front_matter(**overrides), encoding="utf-8")
    return target


def patch(path: str, added: list[str], removed: list[str]) -> str:
    body = [f"-{line}" for line in removed] + [f"+{line}" for line in added]
    return (f"diff --git a/{path} b/{path}\n--- a/{path}\n+++ b/{path}\n"
            f"@@ -1,{len(removed)} +1,{len(added)} @@\n" + "\n".join(body) + "\n")


def write_round(target: Path, number: int, value: float, *, slice_id: str | None = None,
                raw: str | None = None, proposal: str | None = None, tokens: int | None = None,
                decision: str | None = None, extra: dict | None = None) -> Path:
    folder = target / "evidence" / f"improve-{number:03d}"
    folder.mkdir(parents=True, exist_ok=True)
    raw = raw if raw is not None else f"coverage {value}"
    (folder / "measure.txt").write_text(f"{raw}\n", encoding="utf-8")
    (folder / "summary.md").write_text("# Round\n\nHypothesis recorded.\n", encoding="utf-8")
    if proposal is not None:
        (folder / "proposal.patch").write_text(proposal, encoding="utf-8")
    record = {
        "round": number, "slice": slice_id or f"slice-{number:03d}", "closure": "validated",
        "measure_value": value, "measure_raw": raw,
        "proposal": "proposal.patch" if proposal is not None else None,
        "tokens_used": tokens,
        "decision": decision or ("proposed" if proposal is not None else "none"),
    }
    record.update(extra or {})
    (folder / "round.json").write_text(json.dumps(record), encoding="utf-8")
    return folder


def check(target: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(target / "scripts" / "projectstate_improve_check.py"), "--root", str(target), *args],
        cwd=target, capture_output=True, text=True, check=False)


def snapshot(target: Path) -> dict[str, str]:
    return {p.relative_to(target).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(target.rglob("*")) if p.is_file() and "__pycache__" not in p.parts}


class ImprovementRoundsTests(unittest.TestCase):
    def assertExit(self, done: subprocess.CompletedProcess[str], code: int, text: str = "") -> None:
        output = done.stdout + done.stderr
        self.assertEqual(done.returncode, code, output)
        self.assertIn(text, output)

    def test_default_core_is_unchanged_and_template_is_inert(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "core"
            done = subprocess.run(
                [sys.executable, str(INIT), "new", "--name", "Core", "--target", str(target), "--no-init-git"],
                cwd=ROOT, capture_output=True, text=True, check=False)
            self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
            files = {p.relative_to(target).as_posix() for p in target.rglob("*") if p.is_file()}
            self.assertEqual(files, {
                "AGENTS.md", "PROJECT.md", "README.md", "STATE.yaml",
                "evidence/bootstrap-001/summary.md", "scripts/projectstate_gate.py"})
            agents = (target / "AGENTS.md").read_text(encoding="utf-8").lower()
            self.assertNotIn("improve.md", agents)
            self.assertNotIn("improvement round", agents)
            shutil.copy(CHECK, target / "scripts" / "projectstate_improve_check.py")
            shutil.copy(TEMPLATE, target / "IMPROVE.md")
            self.assertIn("enabled: false", TEMPLATE.read_text(encoding="utf-8"))
            self.assertExit(check(target), 1, "DISABLED")

    def test_guide_and_template_state_boundaries(self) -> None:
        guide = " ".join(GUIDE.read_text(encoding="utf-8").split())
        for phrase in ("only when the human selects it", "No measure, no loop", "pull, not push",
                       "never executes the measure command", "stays tripped", "no model"):
            self.assertIn(phrase.lower(), guide.lower())
        template = " ".join(TEMPLATE.read_text(encoding="utf-8").split())
        for phrase in ("at most one proposal", "Nothing is applied without the owner's explicit approval",
                       "Never touch gates", "never estimate it"):
            self.assertIn(phrase, template)

    def test_missing_or_symlinked_configuration(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = make_instance(tmp)
            real = target / "real.md"
            (target / "IMPROVE.md").rename(real)
            self.assertExit(check(target), 1, "not selected")
            (target / "IMPROVE.md").symlink_to(real)
            self.assertExit(check(target), 2, "symlinks are not allowed")

    def test_enabled_start_check_and_missing_measure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = make_instance(tmp)
            self.assertExit(check(target), 0, "improve-001")
            (target / "IMPROVE.md").write_text(front_matter(measure_command=None), encoding="utf-8")
            self.assertExit(check(target), 2, "no measure means no loop")

    def test_stop_rule_trips_stays_tripped_and_only_owner_rearms(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = make_instance(tmp)
            for number, value in enumerate((0.41, 0.40, 0.405), start=1):
                write_round(target, number, value)
            self.assertExit(check(target), 1, "stop rule")
            write_round(target, 4, 0.90)  # a later gain must not undo the trip
            self.assertExit(check(target), 1, "stop rule")
            self.assertExit(check(target, "--round", "4"), 1, "stop rule")
            (target / "IMPROVE.md").write_text(
                front_matter(first_counted_round="5", baseline_value="0.90"), encoding="utf-8")
            self.assertExit(check(target), 0, "improve-005")

    def test_gain_resets_flat_count_and_direction_lower(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = make_instance(tmp)
            for number, value in enumerate((0.43, 0.43, 0.43), start=1):
                write_round(target, number, value)
            self.assertExit(check(target), 0, "flat rounds 2/3")
            write_round(target, 4, 0.43)
            self.assertExit(check(target), 1, "stop rule")
        with tempfile.TemporaryDirectory() as tmp:
            target = make_instance(tmp, measure_direction="lower", baseline_value="10", min_gain="1")
            for number, value in enumerate((8.5, 7.0, 6.0), start=1):
                write_round(target, number, value)
            self.assertExit(check(target), 0, "flat rounds 0/3")

    def test_protected_paths_are_refused(self) -> None:
        for path in ("PROJECT.md", "STATE.yaml", "IMPROVE.md", "scripts/projectstate_gate.py",
                     "scripts/projectstate_improve_check.py", "evidence/improve-001/round.json",
                     "scripts/measure.py", ".github/workflows/ci.yml", ".git/hooks/pre-commit",
                     "project.md"):
            with self.subTest(path=path), tempfile.TemporaryDirectory() as tmp:
                target = make_instance(tmp)
                write_round(target, 1, 0.41, proposal=patch(path, ["x"], ["y", "z"]))
                self.assertExit(check(target, "--round", "1"), 1, "protected")

    def test_unprotected_proposal_is_valid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = make_instance(tmp)
            write_round(target, 1, 0.41, proposal=patch("src/app.py", ["a", "b"], ["c"]))
            self.assertExit(check(target, "--round", "1"), 0, "ROUND RECORD VALID")

    def test_instruction_files_may_only_shrink(self) -> None:
        for path, added, removed, code in (
            ("AGENTS.md", ["a", "b"], ["c"], 1),
            ("AGENTS.md", ["a"], ["c"], 1),
            ("docs/AGENTS.md", ["a"], ["c", "d"], 0),
            ("CLAUDE.md", ["a", "b"], ["c"], 1),
            ("GEMINI.md", ["a"], ["c", "d"], 0),
        ):
            with self.subTest(path=path, added=len(added), removed=len(removed)), tempfile.TemporaryDirectory() as tmp:
                target = make_instance(tmp)
                write_round(target, 1, 0.41, proposal=patch(path, added, removed))
                self.assertExit(check(target, "--round", "1"), code)

    def test_measure_record_must_match_raw_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = make_instance(tmp)
            folder = write_round(target, 1, 0.55)
            (folder / "measure.txt").write_text("coverage 0.41\n", encoding="utf-8")
            self.assertExit(check(target, "--round", "1"), 2, "not a line of measure.txt")
        with tempfile.TemporaryDirectory() as tmp:
            target = make_instance(tmp)
            write_round(target, 1, 0.55, raw="coverage 0.41")
            self.assertExit(check(target, "--round", "1"), 2, "does not appear in 'measure_raw'")

    def test_token_cap_and_unknown_usage(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = make_instance(tmp)
            write_round(target, 1, 0.41, tokens=1001)
            self.assertExit(check(target, "--round", "1"), 1, "exceeds round_token_cap")
        with tempfile.TemporaryDirectory() as tmp:
            target = make_instance(tmp)
            write_round(target, 1, 0.41, tokens=None)
            self.assertExit(check(target, "--round", "1"), 0, "token usage unknown")

    def test_unsupported_duplicate_and_nonfinite_fields_are_invalid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = make_instance(tmp)
            (target / "IMPROVE.md").write_text(front_matter(auto_apply="true"), encoding="utf-8")
            self.assertExit(check(target), 2, "unsupported field")
            (target / "IMPROVE.md").write_text(front_matter() .replace("---\n\n#", "min_gain: 1\n---\n\n#"), encoding="utf-8")
            self.assertExit(check(target), 2, "duplicate key")
        with tempfile.TemporaryDirectory() as tmp:
            target = make_instance(tmp)
            write_round(target, 1, 0.41, extra={"applied": True})
            self.assertExit(check(target), 2, "unsupported fields")
        with tempfile.TemporaryDirectory() as tmp:
            target = make_instance(tmp)
            folder = write_round(target, 1, 0.41)
            (folder / "round.json").write_text('{"round": 1, "round": 2}', encoding="utf-8")
            self.assertExit(check(target), 2, "duplicate key")
            (folder / "round.json").write_text(
                json.dumps({"round": 1}).replace("}", ', "measure_value": NaN}'), encoding="utf-8")
            self.assertExit(check(target), 2)

    def test_measure_script_must_be_protected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = make_instance(tmp, protected=None)
            self.assertExit(check(target), 2, "list it in protected")

    def test_unverifiable_patches_are_refused(self) -> None:
        bad = {
            "traversal": patch("../outside.py", ["a"], ["b"]),
            "absolute": "diff --git a//etc/passwd b//etc/passwd\n--- a//etc/passwd\n+++ b//etc/passwd\n@@ -1 +1 @@\n-a\n+b\n",
            "symlink": "diff --git a/l b/l\nnew file mode 120000\n--- /dev/null\n+++ b/l\n@@ -0,0 +1 @@\n+PROJECT.md\n",
            "binary": "diff --git a/x.bin b/x.bin\nBinary files a/x.bin and b/x.bin differ\n",
            "truncated": "diff --git a/f b/f\n--- a/f\n+++ b/f\n@@ -1,3 +1,3 @@\n-a\n+b\n",
            "empty": "not a patch\n",
            "rename into protected": "diff --git a/src/x.py b/STATE.yaml\nrename from src/x.py\nrename to STATE.yaml\n",
        }
        for name, text in bad.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                target = make_instance(tmp)
                write_round(target, 1, 0.41, proposal=text)
                self.assertExit(check(target, "--round", "1"), 1)

    def test_one_round_per_closed_slice_and_valid_decision_pairing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = make_instance(tmp)
            write_round(target, 1, 0.41, slice_id="same")
            write_round(target, 2, 0.42, slice_id="same")
            self.assertExit(check(target), 2, "one round per closed slice")
        with tempfile.TemporaryDirectory() as tmp:
            target = make_instance(tmp)
            write_round(target, 1, 0.41, decision="approved")
            self.assertExit(check(target), 2, "exactly when there is no proposal")

    def test_dirty_worktree_is_refused_at_round_start(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = make_instance(tmp)
            git = ["git", "-C", str(target), "-c", "user.name=t", "-c", "user.email=t@example.invalid"]
            subprocess.run([*git, "init", "-q"], check=True)
            subprocess.run([*git, "add", "-A"], check=True)
            subprocess.run([*git, "commit", "-q", "-m", "baseline"], check=True)
            self.assertExit(check(target, "--require-clean"), 0, "ROUND MAY START")
            (target / "notes.txt").write_text("uncommitted\n", encoding="utf-8")
            self.assertExit(check(target, "--require-clean"), 1, "not clean")

    def test_check_is_read_only_and_never_runs_the_measure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = make_instance(tmp)
            write_round(target, 1, 0.41, proposal=patch("src/app.py", ["a"], ["b", "c"]))
            before = snapshot(target)
            for args in ((), ("--round", "1"), ("--format", "json")):
                check(target, *args)
            self.assertEqual(snapshot(target), before)
            self.assertFalse((target / "RAN").exists())


if __name__ == "__main__":
    unittest.main()
