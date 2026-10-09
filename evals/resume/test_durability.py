#!/usr/bin/env python3
"""Tests for the durability eval. No model calls: the noise week, the anchors, the harness and the reports."""

from __future__ import annotations

import io
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import durability as du  # noqa: E402
import handoff  # noqa: E402
import projectstate_owner_log as owner_log  # noqa: E402
import scenarios as sc  # noqa: E402

# Stated tolerance for the owner's real prompt-length distribution, in characters (the brief's median ~45,
# p75 ~90, p90 ~230 cannot be hit exactly by hand-written prompts).
MEDIAN_TOLERANCE, P75_TOLERANCE, P90_TOLERANCE = 12.0, 20.0, 45.0
FORBIDDEN = (
    "export", "import", "csv", "delimiter", "separator", "semicolon", "bom", "excel", "bookkeeper", "overwrite", "force",
)


class NoiseTests(unittest.TestCase):
    def test_list_is_the_documented_constant(self) -> None:
        self.assertEqual(len(du.NOISE), 30)
        self.assertEqual(len(du.STANDING_DIRECTIVES), 3)

    def test_noise_selection_uses_the_first_n_in_groups_of_about_four_per_session(self) -> None:
        self.assertEqual(du.noise_sessions(0), [])
        self.assertEqual(sum(len(prompts) for _session, prompts in du.noise_sessions(7)), 7)
        sessions = du.noise_sessions(len(du.NOISE))
        self.assertEqual([len(prompts) for _session, prompts in sessions], [4, 4, 4, 4, 4, 4, 4, 2])
        self.assertEqual(sessions[0][0], "noise-01")
        self.assertEqual(sessions[-1][0], "noise-08")
        flat = [prompt for _session, prompts in sessions for prompt in prompts]
        self.assertEqual(flat, list(du.NOISE))

    def test_no_noise_prompt_mentions_the_constraints_or_their_subjects(self) -> None:
        for prompt in du.NOISE:
            lowered = prompt.lower()
            for word in FORBIDDEN:
                self.assertNotIn(word, lowered, f"forbidden {word!r} in: {prompt[:80]!r}")

    def test_exactly_three_prompts_carry_the_standing_directives(self) -> None:
        directed = [prompt for prompt in du.NOISE if prompt in du.STANDING_DIRECTIVES]
        self.assertEqual(sorted(directed), sorted(du.STANDING_DIRECTIVES))

    def test_exactly_two_pasted_blocks_in_claude_code_form_with_a_short_owner_sentence(self) -> None:
        pastes = [prompt for prompt in du.NOISE if "<pasted_content" in prompt]
        self.assertEqual(len(pastes), 2)
        seen_ids = set()
        for prompt in pastes:
            match = du.PASTE_TAG.search(prompt)
            self.assertIsNotNone(match, prompt[:120])
            wrapped = match.group(0)
            self.assertTrue(1500 <= len(prompt) <= 3000, len(prompt))
            seen_ids.add(match.group(1))
            owner_sentence = prompt.replace(wrapped, "")
            self.assertTrue(0 < len(owner_sentence.strip()) <= 200, owner_sentence[:120])
        self.assertEqual(len(seen_ids), 2)

    def test_one_paste_is_a_bug_report_with_a_traceback_and_one_an_agent_report(self) -> None:
        pastes = [prompt for prompt in du.NOISE if "<pasted_content" in prompt]
        self.assertEqual(sum("Traceback (most recent call last):" in prompt for prompt in pastes), 1)

    def test_length_distribution_matches_the_owner(self) -> None:
        stats = du.noise_stats()
        self.assertAlmostEqual(stats["median_chars"], 45.0, delta=MEDIAN_TOLERANCE)
        self.assertAlmostEqual(stats["p75_chars"], 90.0, delta=P75_TOLERANCE)
        self.assertAlmostEqual(stats["p90_chars"], 230.0, delta=P90_TOLERANCE)

    def test_quantile_helper_interpolates_like_numpy(self) -> None:
        self.assertEqual(du.quantile([1, 2, 3, 4], 0.5), 2.5)
        self.assertEqual(du.quantile([1, 2, 3, 4], 0.0), 1)
        self.assertEqual(du.quantile([1, 2, 3, 4], 1.0), 4)
        self.assertAlmostEqual(du.quantile([10, 20], 0.9), 19.0)


class AnchorTests(unittest.TestCase):
    def build(self, condition: str) -> Path:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        return handoff.build_repo(Path(tmp.name), condition)

    def test_core_anchor_exists_and_starts_without_the_constraints(self) -> None:
        report = du.anchor_capture(self.build("with"), core=True)
        self.assertEqual(report["anchor"], du.DURABLE_ANCHOR)
        self.assertTrue(report["present"])
        self.assertEqual(report["constraints"], {name: False for name in handoff.RECORDED_PATTERNS})
        self.assertFalse(report["scope_limit_promoted"])

    def test_a_constraint_written_into_the_anchor_is_found_and_a_promoted_scope_limit_is_flagged(self) -> None:
        repo = self.build("with")
        project = (repo / "PROJECT.md").read_text(encoding="utf-8")
        self.assertEqual(project.count(du.DURABLE_ANCHOR), 1)
        (repo / "PROJECT.md").write_text(
            project.replace(
                du.DURABLE_ANCHOR + "\n",
                du.DURABLE_ANCHOR + "\n\n"
                "- export writes semicolon CSV with a UTF-8 BOM and refuses overwrite without --force\n"
                "- do not implement or start export or import; the owner scheduled them for a later session\n",
            ),
            encoding="utf-8",
        )
        report = du.anchor_capture(repo, core=True)
        self.assertTrue(report["all"])
        self.assertTrue(report["scope_limit_promoted"])

    def test_nocore_anchor_is_the_standing_file(self) -> None:
        repo = self.build("without")
        report = du.anchor_capture(repo, core=False)
        self.assertEqual(report["anchor"], du.STANDING_FILE)
        self.assertFalse(report["present"])
        standing = repo / ".projectstate" / "standing.md"
        standing.parent.mkdir()
        standing.write_text("always keep the readme short\n", encoding="utf-8")
        self.assertTrue(du.anchor_capture(repo, core=False)["present"])


class InjectTests(unittest.TestCase):
    def build_log_repo(self, condition: str = "with-log") -> Path:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        return handoff.build_repo(Path(tmp.name), condition)

    def test_session1_prompt_is_visible_with_zero_noise(self) -> None:
        repo = self.build_log_repo()
        self.assertIsNone(du.apply_noise(repo, "core-log1", 0))
        self.assertTrue(owner_log.append_entry(repo, handoff.PROMPTS["plain"], "session1"))
        visible = du.visible_constraints(owner_log.inject_text(repo))
        self.assertEqual(visible, {name: True for name in handoff.RECORDED_PATTERNS})

    def test_thirty_noise_prompts_roll_the_constraints_out_of_the_v1_injection(self) -> None:
        # The deterministic failure this eval measures: v1 injects the newest ~3500 characters, and the two
        # pastes alone fill that budget, so the constraint-carrying first entry is never shown again.
        repo = self.build_log_repo()
        self.assertTrue(owner_log.append_entry(repo, handoff.PROMPTS["plain"], "session1"))
        info = du.apply_noise(repo, "core-log1", len(du.NOISE))
        self.assertEqual((info["prompts"], info["sessions"], info["entries"]), (30, 8, 31))
        text = owner_log.inject_text(repo)
        for name in ("semicolon", "bom"):
            self.assertIsNone(handoff.RECORDED_PATTERNS[name].search(text))
        self.assertFalse(du.visible_constraints(text)["semicolon"])
        self.assertLess((repo / ".projectstate" / "owner-log.md").stat().st_size, owner_log.MAX_LOG_BYTES)

    def test_noise_reaches_only_log_conditions(self) -> None:
        repo = self.build_log_repo("with")
        self.assertIsNone(du.apply_noise(repo, "core", len(du.NOISE)))
        self.assertIsNone(du.s2_context(repo, "core"))
        self.assertFalse((repo / ".projectstate").exists())


@unittest.skipUnless(du.v2_available(), f"scripts/{du.V2_TOOL} is not in the template yet (branch work/hooks-v2)")
class HostToolTests(unittest.TestCase):
    def test_brief_still_shows_the_constraints_after_thirty_noise_prompts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo, _installed = du.build(Path(tmp), "core-host")
            info = du.apply_noise(repo, "core-host", len(du.NOISE))
            self.assertEqual(info["prompts"], 30)
            text = du.s2_context(repo, "core-host")
            self.assertIsNotNone(handoff.RECORDED_PATTERNS["semicolon"].search(text))


class RenderingTests(unittest.TestCase):
    def run_record(self, condition: str, score: int, *, visible: dict | None, anchor_all: bool = False,
                   scope: bool = False, cost: float = 0.1, tokens: int = 1000) -> dict:
        checks = {name: index < score for index, name in enumerate(handoff.CHECKS)}
        metrics = {"cost_usd": cost, "total_tokens": tokens}
        return {
            "model": "m", "variant": "plain", "condition": condition, "repeat": 1, "noise": 30, "infra_failure": None,
            "after_session1": {
                "checks": {name: False for name in handoff.CHECKS}, "overreach": False,
                "recorded": {name: (["NOTES.md"] if anchor_all else []) for name in handoff.RECORDED_PATTERNS},
                "anchor": {
                    "anchor": du.DURABLE_ANCHOR, "present": anchor_all,
                    "constraints": {name: anchor_all for name in handoff.RECORDED_PATTERNS},
                    "all": anchor_all, "scope_limit_promoted": scope,
                },
            },
            "s2_context": {"chars": 3500 if visible is not None else 0, "visible": visible, "head": ""},
            "session1": {"metrics": metrics}, "session2": {"metrics": metrics},
            "final": {"checks": checks, "score": score, "honest": True, "done_but_wrong": False, "regressions": []},
        }

    def test_summary_rows_count_what_measured_what(self) -> None:
        runs = [
            self.run_record("core-log1", len(handoff.CHECKS),
                            visible={"semicolon": False, "bom": False, "force": True}),
            self.run_record("core-log1", 3, visible={"semicolon": True, "bom": True, "force": True},
                            anchor_all=True, scope=True),
            self.run_record("core-log1", 9, visible=None),
            self.run_record("core-log1", 9, visible=None, anchor_all=True),
            {"model": "m", "variant": "plain", "condition": "core-log1", "repeat": 9, "noise": 30,
             "infra_failure": "timed out"},
        ]
        overreach = self.run_record("core-log1", 8, visible=None)
        overreach["after_session1"]["overreach"] = True
        runs.append(overreach)
        rows = du.summarize(runs)
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["chains"], 4)  # the infrastructure failure and the overreach are excluded
        self.assertEqual(row["mean_checks"], round((8 + 3 + 9 + 9) / 4, 2))
        self.assertEqual((row["visible_at_s2"], row["visible_n"]), (1, 2))
        self.assertEqual((row["anchor_all"], row["scope_promoted"]), (2, 1))
        self.assertEqual(row["memory_only_kept"], 3)  # scores 8, 9 and 9 carry csv_format and no_overwrite; 3 does not
        self.assertEqual(row["tokens_per_session"], 1000)
        self.assertEqual(row["cost_usd"], 0.8)

    def test_markdown_renders_rows_and_chain_lines(self) -> None:
        runs = [
            self.run_record("core-log1", len(handoff.CHECKS),
                            visible={"semicolon": False, "bom": False, "force": True}),
            self.run_record("core", 3, visible=None),
        ]
        results = {
            "schema": du.SCHEMA, "model": "m", "claude_version": "x", "stopped": None, "noise": 30,
            "noise_stats": du.noise_stats(), "v2_available": du.v2_available(),
            "runs": runs, "summary": du.summarize(runs),
        }
        text = du.render_markdown(results)
        self.assertIn("| m | core-log1 | 1 | 8.0 | 1/1 | 0/1 | 0/1 | 0/1 | 1/1 | 0/1 | 0/1 | 1,000 | $0.20 |", text)
        self.assertIn("| m | core | 1 | 3.0 | 0/1 | n/a | 0/1 | 0/1 | 1/1 | 0/1 | 0/1 | 1,000 | $0.20 |", text)
        self.assertIn("n/n/Y", text)  # semicolon gone, bom gone, force still matched (the header alone matches)
        self.assertIn("-/-/-", text)  # no injected context in the core condition


class DryRunTests(unittest.TestCase):
    def test_dry_run_builds_every_available_condition_and_grades_the_untouched_skeleton(self) -> None:
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            self.assertEqual(du.main(["--dry-run"]), 0)
        output = buffer.getvalue()
        for condition in du.CONDITIONS:
            self.assertIn(condition, output)
        for condition in ("core", "core-log1", "nocore-log1"):
            self.assertIn(f"{condition}: checks 0/{len(handoff.CHECKS)}, journey exit 1", output)
        if not du.v2_available():
            self.assertIn(f"core-host: skipped (scripts/{du.V2_TOOL} is missing", output)


class CliTests(unittest.TestCase):
    def test_unknown_condition_is_refused(self) -> None:
        self.assertEqual(du.main(["--conditions", "nope", "--dry-run"]), 2)

    def test_noise_bounds(self) -> None:
        with self.assertRaises(SystemExit):
            du.parse_args(["--noise", str(len(du.NOISE) + 1)])
        self.assertEqual(du.parse_args(["--noise", "0"]).noise, 0)
        self.assertEqual(du.parse_args([]).noise, len(du.NOISE))

    def test_out_must_be_outside_every_repository(self) -> None:
        with self.assertRaises(SystemExit):
            du.prepare_out(str(sc.ROOT))

    @unittest.skipIf(du.v2_available(), "the v2 tool is present")
    def test_host_conditions_refuse_while_the_v2_tool_is_missing(self) -> None:
        for conditions in ("core-host", "nocore-host,core-host-nostop", "core-log1,core-host"):
            err = io.StringIO()
            with redirect_stderr(err):
                self.assertEqual(du.main(["--conditions", conditions]), 2)
            self.assertIn(du.V2_TOOL, err.getvalue())
            self.assertIn("work/hooks-v2", err.getvalue())


if __name__ == "__main__":
    unittest.main()
