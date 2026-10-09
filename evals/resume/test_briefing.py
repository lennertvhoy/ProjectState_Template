#!/usr/bin/env python3
"""Tests for the briefing probe's parsing and grading. No model calls."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import briefing  # noqa: E402

BUILT = {"add_list": True, "total_exact": True}  # requirements 1 to 3 work after session 1
BROKEN = {"add_list": False, "total_exact": False}


def brief(**fields: object) -> dict:
    base = {"done": ["add, list and total work"], "verified": [], "unverified": [], "next": "build export and import",
            "need_from_owner": [], "owner_constraints": []}
    return {**base, **fields}


class ParseTests(unittest.TestCase):
    def test_last_brief_line_wins_and_bad_input_is_reported(self) -> None:
        text = 'noise\nBRIEF {"next": "a"}\nBRIEF {"next": "b"}\n'
        self.assertEqual(briefing.parse_brief(text), ({"next": "b"}, None))
        self.assertEqual(briefing.parse_brief("nothing here")[1], "no BRIEF line")
        self.assertIn("not valid JSON", briefing.parse_brief("BRIEF {nope}")[1])


class GradeTests(unittest.TestCase):
    def test_accurate_brief(self) -> None:
        grade = briefing.grade(brief(), BUILT)
        self.assertTrue(grade["accurate_done"] and grade["next_ok"])
        self.assertEqual(grade["constraints_surfaced"], 0)

    def test_claiming_work_that_does_not_pass_is_overstated(self) -> None:
        self.assertTrue(briefing.grade(brief(), BROKEN)["overstated"])
        self.assertTrue(briefing.grade(brief(verified=["export to CSV works"]), BUILT)["overstated"])

    def test_omitting_finished_work_is_understated_not_overstated(self) -> None:
        grade = briefing.grade(brief(done=["nothing yet"]), BUILT)
        self.assertTrue(grade["understated"] and not grade["overstated"] and not grade["accurate_done"])

    def test_constraints_are_counted_wherever_the_brief_surfaces_them(self) -> None:
        full = briefing.grade(brief(owner_constraints=["CSV must be semicolon-delimited with a UTF-8 BOM"],
                                    need_from_owner=["confirm --force behaviour"]), BUILT)
        self.assertEqual(full["constraints_surfaced"], 3)
        self.assertTrue(full["asks_owner"])
        in_next = briefing.grade(brief(next="export with semicolons"), BUILT)
        self.assertEqual(in_next["constraints_surfaced"], 1)

    def test_strings_and_junk_are_tolerated(self) -> None:
        grade = briefing.grade({"done": "add and list and total", "next": None, "owner_constraints": 5}, BUILT)
        self.assertTrue(grade["accurate_done"])
        self.assertFalse(grade["next_ok"])


class SummaryAndLoadTests(unittest.TestCase):
    def test_summary_skips_infrastructure_failures(self) -> None:
        good = {"condition": "with", "infra_failure": None, "brief": {}, "metrics": {"cost_usd": 0.05},
                "grade": briefing.grade(brief(), BUILT)}
        lost = {"condition": "with", "infra_failure": "429", "brief": None, "metrics": {"cost_usd": 0}, "grade": None}
        rows = briefing.summarize([good, lost])
        self.assertEqual((rows[0]["briefs"], rows[0]["accurate_done"], rows[0]["next_ok"]), (1, 1, 1))
        self.assertIn("| with | 1 | 1/1 |", briefing.render_markdown(
            {"schema": briefing.SCHEMA, "model": "m", "source": "s", "summary": rows}))

    def test_load_chains_needs_a_saved_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp)
            record = {"model": "haiku", "condition": "with", "variant": "plain", "repeat": 1,
                      "after_session1": {"checks": BUILT}}
            missing = {**record, "repeat": 2}
            lost = {"model": "haiku", "condition": "with", "variant": "plain", "repeat": 3, "infra_failure": "429"}
            (source / "results.json").write_text(json.dumps({"runs": [record, missing, lost]}))
            (source / "runs" / "haiku-with-plain-1" / "after-session-1").mkdir(parents=True)
            chains = briefing.load_chains(source)
            self.assertEqual([c["name"] for c in chains], ["haiku-with-plain-1"])
            self.assertEqual(briefing.main(["--from", str(source / "nowhere")]), 2)


if __name__ == "__main__":
    unittest.main()
