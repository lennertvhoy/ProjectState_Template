#!/usr/bin/env python3
"""Tests for the release tool (scripts/projectstate_release.py): check, cut and hashes.

``releases/index.json`` is what the fleet doctor and the update command trust, so ``check`` must
reject anything that could mislead them, and ``cut`` must only ever fill a draft with the hashes
of the files in front of it. Every adversarial case is built in a temporary template root with a
fake gate and managed block; the real index, gate and block are only read or copied, never changed.
"""

from __future__ import annotations

import contextlib
import copy
import hashlib
import inspect
import io
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, NamedTuple


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import projectstate_release as rel  # noqa: E402


SCHEMA = "projectstate-template-v6"
BLOCK = "# ProjectState contract\n\nManaged text.\n"
OTHER_BLOCK = "# ProjectState contract\n\nEdited managed text.\n"


def gate_source(release: str, version: str = SCHEMA) -> str:
    return f'"""Fake gate of {release}."""\nVERSION = "{version}"\nRELEASE = "{release}"\n'


GATE_600, GATE_620, GATE_630 = (gate_source(release) for release in ("6.0.0", "6.2.0", "6.3.0"))


def sha(text: str | bytes) -> str:
    return hashlib.sha256(text.encode("utf-8") if isinstance(text, str) else text).hexdigest()


def entry(release: str, *, status: str = "released", gate: str | None = None, contract: str | None = None,
          date: str | None = "2026-09-01", action: str = "mechanical") -> dict[str, Any]:
    return {
        "release": release,
        "date": None if status == "draft" else date,
        "tag": f"v{release}",
        "status": status,
        "gate_sha256": gate,
        "contract_sha256": contract,
        "instance_action": action,
        "summary": f"Summary of {release}.",
    }


def consistent_releases(latest: str = "draft") -> list[dict[str, Any]]:
    """6.0.0 and 6.2.0 released before the managed block existed, then 6.3.0 as a draft or released."""
    releases = [
        entry("6.0.0", gate=sha(GATE_600), action="semantic"),
        entry("6.2.0", gate=sha(GATE_620), date="2026-10-01"),
    ]
    if latest == "draft":
        releases.append(entry("6.3.0", status="draft"))
    else:
        releases.append(entry("6.3.0", gate=sha(GATE_630), contract=sha(BLOCK), date="2026-10-06"))
    return releases


def index_payload(releases: list[dict[str, Any]], top: dict[str, Any] | None = None) -> dict[str, Any]:
    """The index document; ``top`` overrides top-level fields (format, state_schema, latest, releases)."""
    payload: dict[str, Any] = {
        "format": rel.INDEX_FORMAT,
        "state_schema": SCHEMA,
        "latest": releases[-1]["release"] if releases else "6.3.0",
        "releases": releases,
    }
    payload.update(top or {})
    return payload


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def make_template(
    root: Path, releases: list[dict[str, Any]] | None = None, *, gate: str = GATE_630, block: str | None = BLOCK,
    raw_index: str | None = None, top: dict[str, Any] | None = None,
) -> Path:
    """A template root with a fake gate, a fake managed block and an index (consistent unless told otherwise)."""
    for directory in ("releases", "scripts", "core"):
        (root / directory).mkdir(parents=True, exist_ok=True)
    (root / rel.GATE_PATH).write_text(gate, encoding="utf-8")
    if block is not None:
        (root / rel.MANAGED_PATH).write_text(block, encoding="utf-8")
    if raw_index is not None:
        (root / rel.INDEX_PATH).write_text(raw_index, encoding="utf-8")
    else:
        write_json(root / rel.INDEX_PATH, index_payload(releases or consistent_releases(), top))
    return root


class Result(NamedTuple):
    code: int
    out: str
    err: str

    @property
    def problems(self) -> list[str]:
        return [line for line in self.err.splitlines() if line.strip()]


def run_tool(*args: str) -> Result:
    """Run the tool in this process; argparse exits become exit codes."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = rel.main(list(args))
        except SystemExit as exc:
            code = exc.code if isinstance(exc.code, int) else 1
    return Result(code, out.getvalue(), err.getvalue())


def run_cli(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(SCRIPTS / "projectstate_release.py"), *args],
                          cwd=cwd, capture_output=True, text=True, check=False)


def git(repo: Path, *args: str) -> str:
    env = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1",
           "GIT_AUTHOR_NAME": "Test", "GIT_AUTHOR_EMAIL": "test@example.com",
           "GIT_COMMITTER_NAME": "Test", "GIT_COMMITTER_EMAIL": "test@example.com"}
    done = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=False, env=env)
    if done.returncode != 0:
        raise AssertionError(f"git {' '.join(args)} failed: {done.stderr}{done.stdout}")
    return done.stdout


def snapshot(root: Path, *, include_git: bool = False) -> dict[str, bytes]:
    """Every file below ``root`` by relative path; the git directory only when asked."""
    return {path.relative_to(root).as_posix(): path.read_bytes()
            for path in sorted(root.rglob("*"))
            if path.is_file() and (include_git or ".git" not in path.relative_to(root).parts)}


class TemporaryRoot(unittest.TestCase):
    def setUp(self) -> None:
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.tmp = Path(holder.name)
        self.root = self.tmp / "template"
        self.root.mkdir()

    def check(self, root: Path | None = None) -> Result:
        return run_tool("check", "--template", str(root or self.root))

    def assertRejected(self, result: Result, *fragments: str, count: int | None = 1) -> None:
        """Exit 2, no traceback, and one line per problem: each fragment appears in some problem line."""
        self.assertEqual(result.code, 2, result.out + result.err)
        self.assertNotIn("Traceback", result.err)
        self.assertEqual(result.out, "", "a rejected index prints nothing on stdout")
        for fragment in fragments:
            self.assertTrue(any(fragment in line for line in result.problems), f"{fragment!r} not in {result.err}")
        if count is not None:
            self.assertEqual(len(result.problems), count, result.err)
        for line in result.problems:
            self.assertTrue(line.startswith("release check: "), line)


class RealIndexTests(unittest.TestCase):
    def test_check_passes_on_the_real_index(self) -> None:
        with tempfile.TemporaryDirectory() as cwd:  # the result must not depend on the working directory
            for args in (["check"], []):
                with self.subTest(args=args):
                    done = run_cli(*args, cwd=Path(cwd))
                    self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
                    self.assertEqual(done.stderr, "")
                    self.assertTrue(done.stdout.startswith("release index OK: "), done.stdout)

    def test_check_on_the_real_index_reports_a_draft_with_its_computed_hashes_or_a_matching_release(self) -> None:
        latest = rel.load_index()["releases"][-1]
        done = run_cli("check", cwd=ROOT)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        gate_sha = rel.sha256_file(ROOT / rel.GATE_PATH)
        contract_sha = rel.contract_sha256(rel.managed_block_text())
        if latest["status"] == "draft":
            self.assertIn(f"gate_sha256: {gate_sha}", done.stdout)
            self.assertIn(f"contract_sha256: {contract_sha}", done.stdout)
        else:
            self.assertEqual(latest["gate_sha256"], gate_sha)
            self.assertEqual(latest["contract_sha256"], contract_sha)
            self.assertNotIn("records no hashes", done.stdout)

    def test_real_released_gate_hashes_match_their_tags_when_the_tags_exist(self) -> None:
        done = run_cli("check", cwd=ROOT)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        if "release tags were not compared" in done.stdout:
            self.skipTest("no git history here (source archive?)")
        for released in rel.released(rel.load_index()):
            tag = released["tag"]
            lines = [line for line in done.stdout.splitlines() if line.startswith((f"tag {tag}:", f"tag {tag} "))]
            self.assertEqual(len(lines), 1, f"{tag} must be reported exactly once: {done.stdout}")
            self.assertTrue("hash matches" in lines[0] or "not found locally" in lines[0], lines[0])

    def test_hashes_prints_the_computed_hashes_as_json(self) -> None:
        done = run_cli("hashes", cwd=ROOT)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(json.loads(done.stdout), {
            "gate_release": rel.gate_release((ROOT / rel.GATE_PATH).read_text(encoding="utf-8")),
            "gate_sha256": rel.sha256_file(ROOT / rel.GATE_PATH),
            "contract_sha256": rel.contract_sha256(rel.managed_block_text()),
        })
        self.assertEqual(list(json.loads(done.stdout)), ["gate_release", "gate_sha256", "contract_sha256"])

    def test_real_index_serializes_back_to_the_same_bytes(self) -> None:
        # cut rewrites the index with json.dumps; if that changed untouched lines the diff of a cut would be noisy
        text = (ROOT / rel.INDEX_PATH).read_text(encoding="utf-8")
        self.assertEqual(rel.index_text(json.loads(text)), text)

    def test_existing_helpers_keep_their_signatures(self) -> None:
        # init_template, the fleet doctor and the update command import these
        expected = {
            "normalize_newlines": ["text"], "sha256_bytes": ["data"], "sha256_text": ["text"], "sha256_file": ["path"],
            "semver_key": ["release"], "load_index": ["template_root"], "gate_release": ["gate_text"],
            "managed_block_text": ["template_root"], "contract_sha256": ["block_text"],
            "render_managed_block": ["release", "block_text"], "extract_managed_block": ["agents_text"],
            "released": ["index"], "current_release": ["index"], "releases_matching": ["index", "field", "sha"],
        }
        for name, parameters in expected.items():
            with self.subTest(helper=name):
                self.assertEqual(list(inspect.signature(getattr(rel, name)).parameters), parameters)
        for constant in ("TEMPLATE_ROOT", "INDEX_FORMAT", "INDEX_PATH", "MANAGED_PATH", "GATE_PATH", "START_MARKER",
                         "END_MARKER", "END_LINE", "RELEASE_LINE", "SEMVER"):
            self.assertTrue(hasattr(rel, constant), constant)
        index = {"releases": [entry("6.1.0", gate="a" * 64), entry("6.2.0", status="draft")]}
        self.assertEqual(rel.current_release(index)["release"], "6.1.0")  # a draft is never current
        self.assertEqual(rel.releases_matching(index, "gate_sha256", "a" * 64), ["6.1.0"])


class CheckTests(TemporaryRoot):
    def test_a_consistent_template_passes_with_a_draft_latest_and_prints_the_computed_hashes(self) -> None:
        make_template(self.root)
        result = self.check()
        self.assertEqual((result.code, result.err), (0, ""))
        self.assertTrue(result.out.startswith("release index OK: 3 releases, latest 6.3.0 (draft)"), result.out)
        self.assertIn(f"gate_sha256: {sha(GATE_630)}", result.out)
        self.assertIn(f"contract_sha256: {sha(BLOCK)}", result.out)

    def test_a_consistent_template_passes_with_a_released_latest(self) -> None:
        make_template(self.root, consistent_releases("released"))
        result = self.check()
        self.assertEqual((result.code, result.err), (0, ""))
        self.assertTrue(result.out.startswith("release index OK: 3 releases, latest 6.3.0 (released)"), result.out)
        self.assertNotIn("records no hashes", result.out)

    def test_a_released_latest_before_the_managed_block_existed_needs_no_contract_hash(self) -> None:
        make_template(self.root, consistent_releases()[:2], gate=GATE_620, block=None)
        result = self.check()
        self.assertEqual((result.code, result.err), (0, ""), result.out)

    def test_check_is_the_default_command_even_before_options(self) -> None:
        make_template(self.root)
        explicit = run_tool("check", "--template", str(self.root))
        self.assertEqual(explicit.code, 0)
        self.assertEqual(run_tool("--template", str(self.root)), explicit)
        self.assertEqual(run_tool("--template", str(self.tmp / "nowhere")).code, 2)


    # --- the index file itself ---

    def test_duplicate_keys_are_rejected(self) -> None:
        good = json.dumps(index_payload(consistent_releases()), indent=2)
        duplicated_entry = good.replace('"tag": "v6.2.0",', '"tag": "v6.2.0",\n      "tag": "v6.2.1",')
        top_level = good.replace('"format"', '"latest": "6.2.0",\n  "format"', 1)
        self.assertNotEqual(duplicated_entry, good)
        self.assertNotEqual(top_level, good)
        for label, text in (("inside an entry", duplicated_entry), ("at the top level", top_level)):
            with self.subTest(case=label):
                make_template(self.root, raw_index=text)
                self.assertRejected(self.check(), "duplicate key")

    def test_unusable_index_files_are_rejected_without_a_traceback(self) -> None:
        for label, text in (("invalid JSON", "{ not json"), ("empty file", ""), ("a JSON list", "[]"),
                            ("a JSON string", '"6.3.0"'), ("deep nesting", "[" * 100000)):
            with self.subTest(case=label):
                make_template(self.root, raw_index=text)
                self.assertRejected(self.check())
        shutil.rmtree(self.root)
        make_template(self.root)
        (self.root / rel.INDEX_PATH).unlink()
        self.assertRejected(self.check(), "releases/index.json is unusable")

    def test_wrong_top_level_fields_are_rejected(self) -> None:
        for label, overrides, fragment in (
            ("format", {"format": "projectstate-release-index/2"}, "format must be"),
            ("missing format", {"format": None}, "format must be"),
            ("state schema", {"state_schema": "projectstate-template-v7"}, "does not equal the gate VERSION"),
            ("latest is not the gate release", {"latest": "6.2.0"}, "does not equal the gate RELEASE"),
            ("latest is not a release number", {"latest": "latest"}, "latest must be"),
            ("empty releases", {"releases": []}, "non-empty list"),
            ("releases is not a list", {"releases": {}}, "non-empty list"),
        ):
            with self.subTest(case=label):
                make_template(self.root, top=overrides)
                result = self.check()
                self.assertRejected(result, fragment, count=None)

    def test_latest_must_name_the_last_entry_and_equal_the_gate_release(self) -> None:
        # the gate says 6.3.0 and the index says latest 6.3.0, but a newer draft exists below it
        releases = consistent_releases()
        releases.append(entry("6.4.0", status="draft"))
        make_template(self.root, releases, top={"latest": "6.3.0"})
        result = self.check()
        self.assertRejected(result, "is not the last entry", "only the last entry may be a draft", count=2)
        make_template(self.root, consistent_releases(), gate=gate_source("6.4.0"))
        self.assertRejected(self.check(), "does not equal the gate RELEASE")

    def test_a_gate_without_version_or_release_cannot_be_checked(self) -> None:
        make_template(self.root, gate='"""A gate that declares nothing."""\n')
        self.assertRejected(self.check(), "declares no VERSION", "declares no RELEASE", count=2)
        make_template(self.root, gate='VERSION = "projectstate-template-v6"\n# RELEASE = "6.3.0"\n')
        self.assertRejected(self.check(), "declares no RELEASE", count=1)
        (self.root / rel.GATE_PATH).unlink()
        self.assertRejected(self.check(), "cannot read scripts/projectstate_gate.py")

    # --- order, uniqueness, drafts ---

    def test_unsorted_and_duplicate_releases_are_rejected(self) -> None:
        releases = consistent_releases()
        for label, mutated, fragment in (
            ("unsorted", [releases[1], releases[0], releases[2]], "releases must ascend"),
            ("equal neighbours", [releases[0], copy.deepcopy(releases[0]), releases[2]], "duplicate release 6.0.0"),
            ("a repeat further down", [releases[0], releases[1], copy.deepcopy(releases[0]), releases[2]],
             "duplicate release 6.0.0"),
        ):
            with self.subTest(case=label):
                make_template(self.root, mutated)
                result = self.check()
                self.assertEqual(result.code, 2, result.out)
                self.assertTrue(any(fragment in line for line in result.problems), result.err)
                self.assertNotIn("Traceback", result.err)

    def test_order_is_numeric_not_textual(self) -> None:
        # "6.10.0" sorts before "6.9.0" as text but follows it as a version
        make_template(self.root, [entry("6.9.0", gate=sha(GATE_600), contract=sha(BLOCK)),
                                  entry("6.10.0", status="draft")], gate=gate_source("6.10.0"))
        result = self.check()
        self.assertEqual((result.code, result.err), (0, ""), result.out)
        make_template(self.root, [entry("6.10.0", gate=sha(GATE_600), contract=sha(BLOCK)),
                                  entry("6.9.0", status="draft")], gate=gate_source("6.9.0"))
        self.assertRejected(self.check(), "releases must ascend, but 6.9.0 follows 6.10.0")

    def test_duplicate_tags_are_rejected(self) -> None:
        releases = consistent_releases()
        releases[1]["tag"] = "v6.0.0"
        make_template(self.root, releases)
        result = self.check()
        self.assertRejected(result, "duplicate tag v6.0.0", "tag v6.0.0 must be v6.2.0", count=2)

    def test_only_the_last_entry_may_be_a_draft(self) -> None:
        for label, latest, drafts, expected in (
            ("two drafts", "draft", (1,), 1),
            ("a draft in the middle", "released", (1,), 1),
            ("every entry a draft", "draft", (0, 1), 2),
        ):
            with self.subTest(case=label):
                releases = consistent_releases(latest)
                for position in drafts:
                    releases[position].update(status="draft", date=None, gate_sha256=None, contract_sha256=None)
                make_template(self.root, releases)
                result = self.check()
                self.assertEqual(result.code, 2, result.out)
                earlier = [line for line in result.problems if "only the last entry may be a draft" in line]
                self.assertEqual(len(earlier), expected, result.err)
                self.assertEqual(len(result.problems), expected, "no other problem is expected: " + result.err)

    # --- entries ---

    def test_entries_need_exactly_the_documented_keys(self) -> None:
        releases = consistent_releases()
        releases[1]["codename"] = "extra"
        make_template(self.root, releases)
        self.assertRejected(self.check(), "unsupported keys ['codename']")
        releases = consistent_releases()
        del releases[2]["summary"]
        make_template(self.root, releases)
        self.assertRejected(self.check(), "missing keys ['summary']")
        releases = consistent_releases()
        releases[0] = "6.0.0"
        make_template(self.root, releases)
        self.assertRejected(self.check(), "releases[0] must be an object")

    def test_malformed_hashes_are_rejected(self) -> None:
        good = sha(GATE_600)
        for label, value in (
            ("uppercase", good.upper()), ("too short", good[:63]), ("too long", good + "0"),
            ("not hex", "g" * 64), ("trailing newline", good + "\n"), ("padded", f" {good}"),
            ("a number", 12345), ("a list", [good]), ("an empty string", ""),
            ("a sha1", hashlib.sha1(b"x").hexdigest()), ("prefixed", f"sha256:{good}"),
        ):
            for field in ("gate_sha256", "contract_sha256"):
                with self.subTest(case=label, field=field):
                    releases = consistent_releases()
                    releases[0][field] = value
                    make_template(self.root, releases)
                    result = self.check()
                    self.assertRejected(result, f"{field} must be 64 lowercase hex characters or null", count=None)
                    self.assertNotIn("Traceback", result.err)

    def test_null_hashes_are_only_allowed_where_the_documentation_says(self) -> None:
        releases = consistent_releases("released")
        releases[2]["gate_sha256"] = None
        make_template(self.root, releases)
        self.assertRejected(self.check(), "gate_sha256 is null; only a draft may leave it null")
        releases = consistent_releases("released")
        releases[2]["contract_sha256"] = None
        make_template(self.root, releases)
        self.assertRejected(self.check(), "contract_sha256 is null; only a draft or a release before 6.3.0")
        releases = consistent_releases("released")
        releases[0]["gate_sha256"] = None  # a released 6.0.0 has no excuse for a missing gate hash
        make_template(self.root, releases)
        self.assertRejected(self.check(), "releases[0] (6.0.0): gate_sha256 is null")
        releases = consistent_releases("released")
        releases.insert(2, entry("6.2.9", gate=sha(GATE_620)))  # before 6.3.0: no contract hash required
        make_template(self.root, releases)
        self.assertEqual(self.check().code, 0)

    def test_invalid_enumerations_tags_dates_and_summaries_are_rejected(self) -> None:
        cases = (
            ("status", "status", "published", "status must be one of"),
            ("instance_action", "instance_action", "manual", "instance_action must be one of"),
            ("instance_action null", "instance_action", None, "instance_action must be one of"),
            ("tag without v", "tag", "6.2.0", "tag must be v<release>"),
            ("tag of another release", "tag", "v6.2.1", "tag v6.2.1 must be v6.2.0"),
            ("tag not a string", "tag", 620, "tag must be v<release>"),
            ("date wrong form", "date", "2026/10/01", "date must be YYYY-MM-DD or null"),
            ("date not a calendar day", "date", "2026-02-30", "date must be YYYY-MM-DD or null"),
            ("date with time", "date", "2026-10-01T00:00:00", "date must be YYYY-MM-DD or null"),
            ("date in other digits", "date", "٢٠٢٦-10-01", "date must be YYYY-MM-DD or null"),
            ("released without a date", "date", None, "a released entry needs a date"),
            ("empty summary", "summary", "  ", "summary must be non-empty text"),
            ("summary not text", "summary", 5, "summary must be non-empty text"),
        )
        for label, field, value, fragment in cases:
            with self.subTest(case=label):
                releases = consistent_releases()
                releases[1][field] = value
                make_template(self.root, releases)
                result = self.check()
                self.assertRejected(result, fragment)

    def test_release_numbers_must_be_plain_ascii_semver(self) -> None:
        for release in ("6.3", "6.3.0.1", "v6.3.0", "06.3.0", "6.03.0", "6.3.0-rc1", "٦.3.0", "6.3.0\n", ""):
            with self.subTest(release=release):
                releases = consistent_releases()
                releases[1]["release"] = release
                releases[1]["tag"] = f"v{release}"
                make_template(self.root, releases)
                result = self.check()
                self.assertEqual(result.code, 2, result.out)
                self.assertTrue(any("release must be a MAJOR.MINOR.PATCH number" in line for line in result.problems),
                                result.err)
                self.assertNotIn("Traceback", result.err)

    # --- hashes of the latest entry ---

    def test_a_released_latest_with_a_wrong_gate_hash_is_rejected(self) -> None:
        releases = consistent_releases("released")
        releases[2]["gate_sha256"] = sha(GATE_620)
        make_template(self.root, releases)
        result = self.check()
        self.assertRejected(result, "release 6.3.0: gate_sha256", "does not match scripts/projectstate_gate.py")
        self.assertIn(sha(GATE_620)[:12], result.err)
        self.assertIn(sha(GATE_630)[:12], result.err)

    def test_a_released_latest_with_a_wrong_contract_hash_is_rejected(self) -> None:
        releases = consistent_releases("released")
        releases[2]["contract_sha256"] = sha(OTHER_BLOCK)
        make_template(self.root, releases)
        self.assertRejected(self.check(), "release 6.3.0: contract_sha256", "does not match core/AGENTS.managed.md")

    def test_editing_the_gate_or_the_block_after_a_cut_is_detected(self) -> None:
        make_template(self.root, consistent_releases("released"))
        self.assertEqual(self.check().code, 0)
        (self.root / rel.GATE_PATH).write_text(GATE_630 + "# edited after the release\n", encoding="utf-8")
        self.assertRejected(self.check(), "gate_sha256")
        (self.root / rel.GATE_PATH).write_text(GATE_630, encoding="utf-8")
        self.assertEqual(self.check().code, 0)
        (self.root / rel.MANAGED_PATH).write_text(OTHER_BLOCK, encoding="utf-8")
        self.assertRejected(self.check(), "contract_sha256")

    def test_the_contract_hash_ignores_line_ending_style_and_extra_trailing_newlines(self) -> None:
        make_template(self.root, consistent_releases("released"))
        (self.root / rel.MANAGED_PATH).write_bytes(BLOCK.replace("\n", "\r\n").encode("utf-8") + b"\r\n\r\n")
        self.assertEqual(self.check().code, 0)

    def test_a_missing_managed_block_is_reported_not_raised(self) -> None:
        make_template(self.root, consistent_releases("released"), block=None)
        self.assertRejected(self.check(), "cannot read core/AGENTS.managed.md")
        make_template(self.root, block=None)
        self.assertRejected(self.check(), "cannot read core/AGENTS.managed.md")

    def test_the_draft_hashes_are_the_computed_ones_even_when_the_draft_carries_stale_ones(self) -> None:
        releases = consistent_releases()
        releases[2].update(gate_sha256=sha("stale"), contract_sha256=sha("stale"))
        make_template(self.root, releases)
        result = self.check()
        self.assertEqual(result.code, 0, result.err)
        self.assertIn(sha(GATE_630), result.out)
        self.assertNotIn(sha("stale"), result.out)


class TagTests(TemporaryRoot):
    """Released entries are also compared with the files at their local tags (read-only git)."""

    def tagged_template(self, *, tag_gate: str = GATE_620, tag_block: str | None = None,
                        recorded_contract: str | None = None) -> None:
        releases = consistent_releases()
        releases[1]["contract_sha256"] = recorded_contract
        make_template(self.root, releases, gate=tag_gate, block=tag_block)
        git(self.root, "init", "-q", "-b", "main")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "release 6.2.0")
        git(self.root, "tag", "v6.2.0")
        make_template(self.root, releases)  # the working tree moves on to the 6.3.0 draft
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "draft 6.3.0")

    def test_matching_tags_pass_and_are_reported(self) -> None:
        self.tagged_template()
        result = self.check()
        self.assertEqual((result.code, result.err), (0, ""), result.out)
        self.assertIn("tag v6.2.0: gate hash matches", result.out)
        self.assertIn("tag v6.0.0 not found locally; not compared", result.out)
        self.assertNotIn("tag v6.3.0", result.out)  # a draft has no tag to compare

    def test_check_never_writes_into_a_git_template(self) -> None:
        self.tagged_template()
        before = snapshot(self.root, include_git=True)
        for _ in range(2):
            self.assertEqual(self.check().code, 0)
        self.assertEqual(snapshot(self.root, include_git=True), before)
        self.assertEqual(git(self.root, "status", "--porcelain"), "")

    def test_a_tag_whose_gate_differs_from_the_recorded_hash_is_rejected(self) -> None:
        self.tagged_template(tag_gate=GATE_620 + "# not what was released\n")
        self.assertRejected(self.check(), "release 6.2.0: gate_sha256", "at tag v6.2.0")

    def test_a_tag_whose_managed_block_differs_from_the_recorded_hash_is_rejected(self) -> None:
        self.tagged_template(tag_block=OTHER_BLOCK, recorded_contract=sha(BLOCK))
        self.assertRejected(self.check(), "release 6.2.0: contract_sha256", "at tag v6.2.0")

    def test_a_recorded_contract_hash_needs_a_managed_block_at_the_tag(self) -> None:
        self.tagged_template(tag_block=None, recorded_contract=sha(BLOCK))
        self.assertRejected(self.check(), "tag v6.2.0 has no core/AGENTS.managed.md")

    def test_a_matching_contract_hash_at_the_tag_is_confirmed(self) -> None:
        self.tagged_template(tag_block=BLOCK, recorded_contract=sha(BLOCK))
        result = self.check()
        self.assertEqual((result.code, result.err), (0, ""), result.out)
        self.assertIn("tag v6.2.0: gate and contract hash matches", result.out)

    def test_annotated_tags_are_followed_to_their_commit(self) -> None:
        self.tagged_template()
        git(self.root, "tag", "-d", "v6.2.0")
        git(self.root, "tag", "-a", "v6.2.0", "HEAD~1", "-m", "release 6.2.0")
        self.assertEqual(git(self.root, "cat-file", "-t", "v6.2.0").strip(), "tag")
        result = self.check()
        self.assertEqual(result.code, 0, result.err)
        self.assertIn("tag v6.2.0: gate hash matches", result.out)

    def test_without_git_history_the_tag_comparison_is_skipped_not_failed(self) -> None:
        make_template(self.root)  # a plain directory, as in a source archive
        result = self.check()
        self.assertEqual((result.code, result.err), (0, ""))
        self.assertIn("not a git repository; release tags were not compared", result.out)

    def test_an_enclosing_repository_is_never_consulted(self) -> None:
        # a template unpacked inside someone else's repository must not use that repository's tags
        outer = self.tmp / "outer"
        outer.mkdir()
        git(outer, "init", "-q", "-b", "main")
        (outer / "file").write_text("x\n", encoding="utf-8")
        git(outer, "add", "-A")
        git(outer, "commit", "-q", "-m", "outer")
        git(outer, "tag", "v6.2.0")
        nested = outer / "vendored-template"
        nested.mkdir()
        make_template(nested)
        result = self.check(nested)
        self.assertEqual(result.code, 0, result.err)
        self.assertNotIn("hash matches", result.out)

    def test_an_option_shaped_tag_is_an_index_problem_and_never_reaches_git(self) -> None:
        sentinel = self.tmp / "written-by-git"
        releases = consistent_releases()
        releases[1]["tag"] = f"--output={sentinel}"
        make_template(self.root, releases)
        git(self.root, "init", "-q", "-b", "main")
        result = self.check()
        self.assertRejected(result, "tag must be v<release>")
        self.assertFalse(sentinel.exists())
        self.assertFalse(Path(f"{sentinel}:scripts/projectstate_gate.py").exists())


class CutTests(TemporaryRoot):
    def cut(self, date: str = "2026-10-06", root: Path | None = None) -> Result:
        return run_tool("cut", f"--date={date}", "--template", str(root or self.root))  # = keeps "-2026..." a value

    def index_bytes(self) -> bytes:
        return (self.root / rel.INDEX_PATH).read_bytes()

    def test_cut_fills_the_hashes_marks_the_draft_released_and_check_then_passes(self) -> None:
        make_template(self.root)
        before = json.loads(self.index_bytes())
        result = self.cut()
        self.assertEqual((result.code, result.err), (0, ""), result.out)
        self.assertIn("cut release 6.3.0 on 2026-10-06", result.out)
        self.assertIn("never creates tags", result.out)
        after = json.loads(self.index_bytes())
        latest = after["releases"][-1]
        self.assertEqual(latest, {**before["releases"][-1], "date": "2026-10-06", "status": "released",
                                  "gate_sha256": sha(GATE_630), "contract_sha256": sha(BLOCK)})
        self.assertEqual(list(latest), list(before["releases"][-1]), "key order is unchanged")
        self.assertEqual(after["releases"][:-1], before["releases"][:-1], "released history is untouched")
        self.assertEqual({key: after[key] for key in ("format", "state_schema", "latest")},
                         {key: before[key] for key in ("format", "state_schema", "latest")})
        checked = self.check()
        self.assertEqual((checked.code, checked.err), (0, ""), checked.out)
        self.assertIn("latest 6.3.0 (released)", checked.out)
        self.assertNotIn("records no hashes", checked.out)

    def test_cut_writes_two_space_json_with_a_trailing_newline_and_changes_only_the_cut_lines(self) -> None:
        make_template(self.root)
        before = self.index_bytes().decode("utf-8")
        self.assertEqual(self.cut().code, 0)
        after = self.index_bytes().decode("utf-8")
        self.assertTrue(after.endswith("}\n") and not after.endswith("\n\n"))
        self.assertEqual(after, json.dumps(json.loads(after), indent=2) + "\n")
        self.assertIn('\n      "date": "2026-10-06",\n', after)
        changed = [(old, new) for old, new in zip(before.splitlines(), after.splitlines()) if old != new]
        self.assertEqual(len(before.splitlines()), len(after.splitlines()))
        self.assertEqual(len(changed), 4, changed)  # date, status, gate_sha256, contract_sha256

    def test_cut_preserves_the_file_mode_and_leaves_no_temporary_files(self) -> None:
        make_template(self.root)
        index = self.root / rel.INDEX_PATH
        index.chmod(0o640)
        self.assertEqual(self.cut().code, 0)
        self.assertEqual(stat.S_IMODE(index.stat().st_mode), 0o640)
        self.assertEqual(sorted(path.name for path in index.parent.iterdir()), ["index.json"])

    def test_cut_never_creates_a_tag(self) -> None:
        make_template(self.root)
        git(self.root, "init", "-q", "-b", "main")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "draft")
        git(self.root, "tag", "v6.2.0")
        tags_before, head_before = git(self.root, "tag", "-l"), git(self.root, "rev-parse", "HEAD")
        self.assertEqual(self.cut().code, 0)
        self.assertEqual(git(self.root, "tag", "-l"), tags_before)
        self.assertEqual(git(self.root, "rev-parse", "HEAD"), head_before)
        self.assertEqual(git(self.root, "status", "--porcelain").split(), ["M", "releases/index.json"])

    def test_cut_refuses_when_the_latest_entry_is_already_released(self) -> None:
        make_template(self.root, consistent_releases("released"))
        before = snapshot(self.root)
        result = self.cut()
        self.assertEqual(result.code, 2)
        self.assertEqual(result.out, "")
        self.assertIn("latest release 6.3.0 is already released", result.err)
        self.assertEqual(snapshot(self.root), before)

    def test_a_second_cut_refuses_and_changes_nothing(self) -> None:
        make_template(self.root)
        self.assertEqual(self.cut().code, 0)
        after_first = snapshot(self.root)
        result = self.cut("2026-10-07")
        self.assertEqual(result.code, 2)
        self.assertIn("already released", result.err)
        self.assertEqual(snapshot(self.root), after_first)

    def test_cut_refuses_invalid_dates_and_writes_nothing(self) -> None:
        make_template(self.root)
        before = snapshot(self.root)
        for date in ("2026-13-01", "2026-02-30", "20261006", "2026-1-1", "2026-10-06T00:00", "today", "", " 2026-10-06",
                     "2026-10-06\n", "٢٠٢٦-10-06", "-2026-10-06"):
            with self.subTest(date=date):
                result = self.cut(date)
                self.assertEqual(result.code, 2, result.out)
                self.assertIn("--date must be a valid YYYY-MM-DD date", result.err)
                self.assertEqual(snapshot(self.root), before)

    def test_cut_requires_a_date(self) -> None:
        make_template(self.root)
        before = snapshot(self.root)
        result = run_tool("cut", "--template", str(self.root))
        self.assertEqual(result.code, 2)
        self.assertIn("--date", result.err)
        self.assertEqual(snapshot(self.root), before)

    def test_cut_refuses_an_inconsistent_index_and_writes_nothing(self) -> None:
        cases = {
            "latest is not the gate release": lambda: make_template(self.root, gate=gate_source("6.4.0")),
            "wrong format": lambda: make_template(self.root, top={"format": "other"}),
            "unsorted releases": lambda: make_template(self.root, list(reversed(consistent_releases()))),
            "duplicate keys": lambda: make_template(
                self.root, raw_index=json.dumps(index_payload(consistent_releases()), indent=2).replace(
                    '"format"', '"latest": "6.2.0",\n  "format"', 1)),
            "malformed hash": lambda: make_template(self.root, [
                *consistent_releases()[:1], {**entry("6.2.0"), "gate_sha256": "XYZ"}, entry("6.3.0", status="draft")]),
        }
        for label, build in cases.items():
            with self.subTest(case=label):
                shutil.rmtree(self.root, ignore_errors=True)
                build()
                before = snapshot(self.root)
                result = self.cut()
                self.assertEqual(result.code, 2, result.out)
                self.assertNotIn("Traceback", result.err)
                self.assertIn("before cutting a release", result.err)
                self.assertEqual(result.out, "")
                self.assertEqual(snapshot(self.root), before)

    def test_cut_needs_the_gate_and_the_managed_block(self) -> None:
        make_template(self.root)
        (self.root / rel.MANAGED_PATH).unlink()
        before = snapshot(self.root)
        result = self.cut()
        self.assertEqual(result.code, 2)
        self.assertIn("cannot read core/AGENTS.managed.md", result.err)
        self.assertEqual(snapshot(self.root), before)
        (self.root / rel.GATE_PATH).unlink()
        result = self.cut()
        self.assertEqual(result.code, 2)
        self.assertIn("cannot read scripts/projectstate_gate.py", result.err)

    def test_cut_does_not_write_through_a_symlinked_index(self) -> None:
        make_template(self.root)
        index = self.root / rel.INDEX_PATH
        elsewhere = self.tmp / "elsewhere.json"
        elsewhere.write_bytes(index.read_bytes())
        index.unlink()
        index.symlink_to(elsewhere)
        before = elsewhere.read_bytes()
        result = self.cut()
        self.assertEqual(result.code, 2)
        self.assertIn("is not a regular file", result.err)
        self.assertEqual(elsewhere.read_bytes(), before)
        self.assertTrue(index.is_symlink())

    def test_cut_uses_the_normalized_block_hash_the_doctor_and_the_update_command_compare(self) -> None:
        make_template(self.root, block=None)
        (self.root / rel.MANAGED_PATH).write_bytes(BLOCK.replace("\n", "\r\n").encode("utf-8") + b"\r\n\r\n")
        self.assertEqual(self.cut().code, 0)
        recorded = json.loads(self.index_bytes())["releases"][-1]["contract_sha256"]
        self.assertEqual(recorded, rel.contract_sha256(rel.managed_block_text(self.root)))
        self.assertEqual(recorded, sha(BLOCK))

    def test_cut_on_a_copy_of_the_real_files_matches_the_real_hashes(self) -> None:
        # The real gate, block and index are copied; the last entry is forced back to a draft so this test
        # keeps working after the real 6.3.0 is cut.
        for relative in (rel.GATE_PATH, rel.MANAGED_PATH, rel.INDEX_PATH):
            (self.root / relative).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / relative, self.root / relative)
        real_before = {relative: (ROOT / relative).read_bytes() for relative in (rel.GATE_PATH, rel.MANAGED_PATH, rel.INDEX_PATH)}
        payload = json.loads(self.index_bytes())
        payload["releases"][-1].update(date=None, status="draft", gate_sha256=None, contract_sha256=None)
        write_json(self.root / rel.INDEX_PATH, payload)
        self.assertEqual(self.check().code, 0)
        self.assertEqual(self.cut("2026-10-06").code, 0)
        cut_entry = json.loads(self.index_bytes())["releases"][-1]
        self.assertEqual(cut_entry["gate_sha256"], rel.sha256_file(ROOT / rel.GATE_PATH))
        self.assertEqual(cut_entry["contract_sha256"], rel.contract_sha256(rel.managed_block_text(ROOT)))
        checked = self.check()
        self.assertEqual((checked.code, checked.err), (0, ""), checked.out)
        self.assertEqual({relative: (ROOT / relative).read_bytes() for relative in real_before}, real_before,
                         "the real files are only read")


class CommandLineTests(TemporaryRoot):
    def test_every_subcommand_takes_template(self) -> None:
        make_template(self.root)
        elsewhere = self.tmp / "other"
        elsewhere.mkdir()
        make_template(elsewhere, gate=gate_source("6.3.0", version="projectstate-template-v9"))
        self.assertEqual(run_tool("check", "--template", str(self.root)).code, 0)
        self.assertEqual(run_tool("check", "--template", str(elsewhere)).code, 2)
        hashes = json.loads(run_tool("hashes", "--template", str(self.root)).out)
        self.assertEqual(hashes, {"gate_release": "6.3.0", "gate_sha256": sha(GATE_630), "contract_sha256": sha(BLOCK)})
        self.assertEqual(run_tool("cut", "--date", "2026-10-06", "--template", str(self.root)).code, 0)

    def test_hashes_reports_missing_files_without_a_traceback(self) -> None:
        make_template(self.root, block=None)
        result = run_tool("hashes", "--template", str(self.root))
        self.assertEqual(result.code, 2)
        self.assertNotIn("Traceback", result.err)
        self.assertEqual(result.out, "")

    def test_help_and_unknown_commands(self) -> None:
        helped = run_tool("--help")
        self.assertEqual(helped.code, 0)
        for command in rel.COMMANDS:
            self.assertIn(command, helped.out)
        for args in (["bogus"], ["check", "extra"], ["cut", "--date"], ["hashes", "--date", "2026-10-06"]):
            with self.subTest(args=args):
                self.assertEqual(run_tool(*args).code, 2)


if __name__ == "__main__":
    unittest.main()
