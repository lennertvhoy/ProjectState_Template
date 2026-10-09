#!/usr/bin/env python3
"""Tests for the read-only fleet doctor (scripts/projectstate_fleet.py).

Every test builds a throwaway fleet in a temporary directory: real ``git init`` repositories, and a
temporary template root with copies of the real gate and helper modules, a test release index, and a
test managed block. Nothing outside the temporary directory is touched.
"""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import projectstate_fleet as fleet


SCRIPTS = Path(__file__).resolve().parent
TODAY = "2026-10-06"
DATE_1 = "2026-09-01T12:00:00+00:00"
DATE_2 = "2026-09-03T12:00:00+00:00"
DATE_3 = "2026-09-10T12:00:00+00:00"
DATE_4 = "2026-09-12T12:00:00+00:00"

GATE_OLD = b"# vendored gate, release 1.0.0\n"
GATE_CURRENT = b"# vendored gate, release 1.1.0\n"
BLOCK_OLD = "# Managed contract\n\nOld rules.\n"
BLOCK_CURRENT = "# Managed contract\n\nCurrent rules.\n"
PLAIN_AGENTS = "# Local rules\n\nBe careful.\n"
HOOKS_OLD = b"#!/usr/bin/env python3\n# host hooks tool of 1.0.0\n"
HOOKS_CURRENT = b"#!/usr/bin/env python3\n# host hooks tool of 1.1.0\n"
PLUGIN_OLD = b"// opencode plugin of 1.0.0\n"
PLUGIN_CURRENT = b"// opencode plugin of 1.1.0\n"

PROJECT_MD = """# Demo

## User

A person using the demo.

## Outcome

The demo does something useful.

## Scope

- One small thing.

## Non-goals

- Anything else.

## Durable constraints

- Stay safe.
"""

RISK = """  - id: {id}
    category: reliability
    severity: medium
    exposure: local_only
    affected_environment: "fixture"
    consequence: "none"
    owner: "owner"
    decision: accept_temporarily
    approval: "owner approved"
    rationale: "known"
    expires: {expires}
"""


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def state_yaml(
    slice_id: str = "demo-001",
    *,
    status: str = "implementing",
    journey: str = "not_run",
    human: str = "pending",
    objective: str = "Ship the demo slice.",
    next_action: str = "Run the journey.",
    blockers: list[str] | None = None,
    risks: str = "",
    padding: int = 0,
) -> str:
    blocker_text = "blockers:\n" + "".join(f'  - "{item}"\n' for item in blockers) if blockers else "blockers: []\n"
    risk_text = "risks:\n" + risks if risks else "risks: []\n"
    return (
        'version: "projectstate-template-v6"\n'
        "profile: core\n"
        "project:\n"
        '  outcome_ref: "PROJECT.md#outcome"\n'
        "current_slice:\n"
        f"  id: {slice_id}\n"
        f'  objective: "{objective}"\n'
        f"  status: {status}\n"
        "  acceptance:\n"
        '    - "The demo works end to end."\n'
        "  primary_journey:\n"
        '    description: "Run the demo."\n'
        '    command: "python3 demo.py"\n'
        '    environment: "local test fixture"\n'
        f"    status: {journey}\n"
        f'    evidence: "evidence/{slice_id}/summary.md"\n'
        "validation:\n"
        f"  primary_journey: {journey}\n"
        "  automated_tests: not_run\n"
        f"  human_acceptance: {human}\n"
        "delivery_boundary:\n"
        "  name: demo_boundary\n"
        "  failed_attempts: []\n"
        "  simplification_review: null\n"
        f"{blocker_text}{risk_text}"
        f'next_action: "{next_action}"\n'
        + (f"# {'x' * 70}\n" * padding)
    )


def summary_md(slice_id: str, *, passed: bool = False, owner_decision: bool = False) -> str:
    text = (
        f"# {slice_id}\n\n"
        "## Primary journey\n\n"
        "- Command: `python3 demo.py`\n"
        "- Environment: local test fixture\n"
        f"- Result: {'passed' if passed else 'not run'}\n"
        f"- Exit code: {0 if passed else 'not recorded'}\n\n"
        "## Secondary checks\n\n- None.\n\n## Artifacts\n\n- None.\n\n## Limitations\n\n- Fixture only.\n"
    )
    if owner_decision:
        text += '\n## Owner decision\n\n- Decision: accepted\n- Date: 2026-09-02\n- Owner words: "ship it"\n'
    return text


def slice_files(slice_id: str = "demo-001", *, owner_decision: bool = False, **options: object) -> dict[str, str]:
    passed = options.get("journey") == "passed"
    return {
        "STATE.yaml": state_yaml(slice_id, **options),  # type: ignore[arg-type]
        f"evidence/{slice_id}/summary.md": summary_md(slice_id, passed=passed, owner_decision=owner_decision),
    }


def managed_agents(release: str, block: str, local: str = "# Local rules\n\nBe careful.\n") -> str:
    return local + "\n" + fleet.release_mod.render_managed_block(release, block)


def git(repo: Path, *args: str, date: str | None = None) -> str:
    env = dict(os.environ)
    env.update(GIT_AUTHOR_NAME="Test", GIT_AUTHOR_EMAIL="test@example.com",
               GIT_COMMITTER_NAME="Test", GIT_COMMITTER_EMAIL="test@example.com")
    if date:
        env.update(GIT_AUTHOR_DATE=date, GIT_COMMITTER_DATE=date)
    command = ["git", "-C", str(repo), "-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null", *args]
    return subprocess.run(command, capture_output=True, text=True, env=env, check=True).stdout


def commit(repo: Path, message: str, date: str) -> None:
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "--allow-empty", "-m", message, date=date)


def write_files(root: Path, files: dict[str, str | bytes]) -> None:
    for relative, content in files.items():
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            target.write_bytes(content)
        else:
            target.write_text(content, encoding="utf-8")


def write_template(path: Path) -> None:
    """A template root: real gate and helper modules, a test release index and a test managed block."""
    for name in ("projectstate_gate.py", "projectstate_release.py", "projectstate_fleet.py"):
        (path / "scripts").mkdir(parents=True, exist_ok=True)
        shutil.copy2(SCRIPTS / name, path / "scripts" / name)
    (path / "core").mkdir()
    (path / "core" / "AGENTS.managed.md").write_text(BLOCK_CURRENT, encoding="utf-8")
    contract = fleet.release_mod.contract_sha256
    index = {
        "format": "projectstate-release-index/1",
        "state_schema": "projectstate-template-v6",
        "latest": "1.2.0",
        "releases": [
            {"release": "1.0.0", "status": "released", "gate_sha256": sha256(GATE_OLD),
             "contract_sha256": contract(BLOCK_OLD), "hooks_sha256": sha256(HOOKS_OLD),
             "opencode_plugin_sha256": sha256(PLUGIN_OLD)},
            {"release": "1.1.0", "status": "released", "gate_sha256": sha256(GATE_CURRENT),
             "contract_sha256": contract(BLOCK_CURRENT), "hooks_sha256": sha256(HOOKS_CURRENT),
             "opencode_plugin_sha256": sha256(PLUGIN_CURRENT)},
            {"release": "1.2.0", "status": "draft", "gate_sha256": None, "contract_sha256": None},
        ],
    }
    (path / "releases").mkdir()
    (path / "releases" / "index.json").write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8")


def tree_state(root: Path) -> dict[str, tuple[str, int, str]]:
    """Kind, mtime and sha256 (or link target) of every entry under ``root``, .git internals included."""
    state: dict[str, tuple[str, int, str]] = {}
    for current, directories, files in os.walk(root):
        for name in directories + files:
            path = Path(current) / name
            relative = path.relative_to(root).as_posix()
            if path.is_symlink():
                state[relative] = ("link", 0, os.readlink(path))
            elif path.is_dir():
                state[relative] = ("dir", 0, "")
            else:
                state[relative] = ("file", path.stat().st_mtime_ns, sha256(path.read_bytes()))
    return state


def run_cli(*args: str) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    code: object = 0
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = fleet.main(list(args))
        except SystemExit as exc:  # argparse exits with 2 on bad arguments
            code = exc.code
    return int(code), out.getvalue(), err.getvalue()  # type: ignore[arg-type]


class Workspace:
    """A temporary fleet root and template."""

    def __init__(self, base: Path, *, template_in_root: bool = False) -> None:
        self.base = base
        self.root = base / "fleet"
        self.out = base / "out"
        self.root.mkdir()
        self.template = (self.root / "ProjectState_Template") if template_in_root else (base / "template")
        write_template(self.template)

    def add(self, name: str, files: dict[str, str | bytes], *, date: str | None = DATE_1) -> Path:
        repo = self.root / name
        repo.mkdir()
        write_files(repo, files)
        if date is not None:
            subprocess.run(["git", "init", "-q", "-b", "main", str(repo)], check=True)
            commit(repo, "initial", date)
        return repo

    def add_v6(self, name: str, *, gate: bytes | None = GATE_CURRENT, agents: str | None = PLAIN_AGENTS,
               date: str | None = DATE_1, slice_id: str = "demo-001", owner_decision: bool = False,
               extra: dict[str, str | bytes] | None = None, **options: object) -> Path:
        files: dict[str, str | bytes] = {"PROJECT.md": PROJECT_MD}
        files.update(slice_files(slice_id, owner_decision=owner_decision, **options))
        if agents is not None:
            files["AGENTS.md"] = agents
        if gate is not None:
            files["scripts/projectstate_gate.py"] = gate
        files.update(extra or {})
        return self.add(name, files, date=date)

    def args(self, *extra: str) -> list[str]:
        return ["--root", str(self.root), "--template", str(self.template), "--today", TODAY, *extra]

    def report(self, *extra: str) -> dict:
        code, out, err = run_cli(*self.args("--stdout", "--format", "json", *extra))
        assert code == 0, err
        return json.loads(out)


def repo_of(report: dict, name: str) -> dict:
    return next(repo for repo in report["repositories"] if repo["name"] == name)


def kinds_of(report: dict, section: str) -> list[tuple[str, str]]:
    return [(item["repository"], item["kind"]) for item in report["inbox"][section]]


class FleetTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.ws = Workspace(Path(self._tmp.name).resolve())


class GateAndContractTests(FleetTestCase):
    def test_gate_status_current_behind_edited_missing_and_symlink(self) -> None:
        self.ws.add_v6("current", gate=GATE_CURRENT)
        self.ws.add_v6("behind", gate=GATE_OLD)
        self.ws.add_v6("edited", gate=GATE_CURRENT + b"# local edit\n")
        self.ws.add_v6("missing", gate=None)
        linked = self.ws.add_v6("linked", gate=None)
        (linked / "scripts").mkdir()
        (self.ws.base / "elsewhere.py").write_bytes(GATE_CURRENT)
        os.symlink(self.ws.base / "elsewhere.py", linked / "scripts" / "projectstate_gate.py")
        report = self.ws.report()
        gates = {name: repo_of(report, name)["gate"] for name in ("current", "behind", "edited", "missing", "linked")}
        self.assertEqual(gates["current"]["status"], "current")
        self.assertEqual(gates["current"]["release"], "1.1.0")
        self.assertEqual(gates["current"]["sha256"], sha256(GATE_CURRENT))
        self.assertEqual((gates["behind"]["status"], gates["behind"]["release"]), ("behind", "1.0.0"))
        self.assertEqual((gates["edited"]["status"], gates["edited"]["release"]), ("unknown", None))
        self.assertEqual(gates["missing"]["status"], "missing")
        self.assertEqual(gates["linked"]["status"], "symlink")
        self.assertIsNone(gates["linked"]["sha256"])  # a symlinked gate is refused, never read
        self.assertEqual(kinds_of(report, "needs_review"), [("edited", "gate-unknown")])
        self.assertEqual(report["summary"]["gates"]["current"], 1)
        self.assertEqual(report["summary"]["gates"]["behind"], 1)

    def test_contract_status_missing_unmanaged_current_behind_edited_and_malformed(self) -> None:
        self.ws.add_v6("missing", agents=None)
        self.ws.add_v6("unmanaged", agents=PLAIN_AGENTS)
        self.ws.add_v6("current", agents=managed_agents("1.1.0", BLOCK_CURRENT))
        self.ws.add_v6("behind", agents=managed_agents("1.0.0", BLOCK_OLD))
        self.ws.add_v6("edited", agents=managed_agents("1.1.0", BLOCK_CURRENT + "An extra rule.\n"))
        self.ws.add_v6("crlf", agents=managed_agents("1.1.0", BLOCK_CURRENT).replace("\n", "\r\n"))
        broken = managed_agents("1.1.0", BLOCK_CURRENT).replace("<!-- projectstate:managed:end -->\n", "")
        self.ws.add_v6("malformed", agents=broken)
        report = self.ws.report()
        status = {name: repo_of(report, name)["contract"] for name in
                  ("missing", "unmanaged", "current", "behind", "edited", "crlf", "malformed")}
        self.assertEqual({name: item["status"] for name, item in status.items()}, {
            "missing": "missing", "unmanaged": "unmanaged", "current": "current", "behind": "behind",
            "edited": "edited", "crlf": "current", "malformed": "malformed"})
        self.assertEqual(status["behind"]["release"], "1.0.0")
        self.assertEqual(status["current"]["declared"], "1.1.0")
        self.assertEqual(status["edited"]["sha256"], fleet.release_mod.contract_sha256(BLOCK_CURRENT + "An extra rule.\n"))
        self.assertEqual(sorted(kinds_of(report, "needs_review")),
                         [("edited", "contract-edited"), ("malformed", "contract-malformed")])

    def test_template_repository_is_marked_and_not_reported_as_drifting(self) -> None:
        ws = Workspace(Path(tempfile.mkdtemp(dir=self._tmp.name)).resolve(), template_in_root=True)
        write_files(ws.template, {"PROJECT.md": PROJECT_MD, "AGENTS.md": PLAIN_AGENTS,
                                  **slice_files("release-001"), "scripts/projectstate_gate.py": GATE_CURRENT + b"# draft\n"})
        ws.add_v6("instance", gate=GATE_CURRENT + b"# edited\n")
        report = ws.report()
        template = repo_of(report, "ProjectState_Template")
        # The template carries the draft candidate (its latest index entry is a draft): "draft", not drift.
        self.assertEqual((template["kind"], template["role"], template["gate"]["status"]), ("v6", "template", "draft"))
        self.assertIsNone(repo_of(report, "instance")["role"])
        self.assertEqual(kinds_of(report, "needs_review"), [("instance", "gate-unknown")])

    def test_instance_carrying_the_draft_candidate_reads_draft_and_needs_no_review(self) -> None:
        ws = Workspace(Path(tempfile.mkdtemp(dir=self._tmp.name)).resolve(), template_in_root=True)
        draft_gate = GATE_CURRENT + b"# draft\n"
        write_files(ws.template, {"PROJECT.md": PROJECT_MD, "AGENTS.md": PLAIN_AGENTS,
                                  **slice_files("release-001"), "scripts/projectstate_gate.py": draft_gate})
        ws.add_v6("candidate", gate=draft_gate)
        report = ws.report()
        self.assertEqual(repo_of(report, "candidate")["gate"]["status"], "draft")
        self.assertEqual(kinds_of(report, "needs_review"), [])


def settings_text(*events: str, v1: bool = False) -> str:
    """A .claude/settings.json body with projectstate_hooks.py entries (or a v1 owner-log entry)."""
    commands = {"SessionStart": "brief", "UserPromptSubmit": "record", "Stop": "stop"}
    hooks_block: dict[str, list] = {}
    for event in events:
        hooks_block[event] = [{"hooks": [{"type": "command",
                                          "command": f'python3 "$CLAUDE_PROJECT_DIR"/scripts/'
                                                     f'projectstate_hooks.py {commands[event]}'}]}]
    if v1:
        hooks_block["SessionStart"] = [{"hooks": [{"type": "command",
                                                   "command": 'python3 "$CLAUDE_PROJECT_DIR"/scripts/'
                                                              'projectstate_owner_log.py inject'}]}]
    return json.dumps({"hooks": hooks_block})


class HostHooksTests(FleetTestCase):
    """The opt-in host hooks: the vendored tool plus Claude hook entries, and the opencode plugin."""

    def repo(self, name: str, *, tool: bytes | None = None, settings: str | None = None,
             plugin: bytes | None = None, legacy_plugin: bytes | None = None, **options: object) -> Path:
        extra: dict[str, str | bytes] = {}
        if tool is not None:
            extra["scripts/projectstate_hooks.py"] = tool
        if settings is not None:
            extra[".claude/settings.json"] = settings
        if plugin is not None:
            extra[".opencode/plugins/projectstate.js"] = plugin
        if legacy_plugin is not None:
            extra[".opencode/plugin/projectstate.js"] = legacy_plugin
        return self.ws.add_v6(name, extra=extra, **options)

    def hooks_of(self, report: dict, name: str) -> dict:
        return repo_of(report, name)["hooks"]

    def test_every_hooks_status(self) -> None:
        full = settings_text("SessionStart", "UserPromptSubmit", "Stop")
        nostop = settings_text("SessionStart", "UserPromptSubmit")
        self.repo("current", tool=HOOKS_CURRENT, settings=full)
        self.repo("no-stop", tool=HOOKS_CURRENT, settings=nostop)
        self.repo("behind", tool=HOOKS_OLD, settings=full)
        self.repo("edited", tool=HOOKS_CURRENT + b"# local edit\n", settings=full)
        self.repo("tool-only", tool=HOOKS_CURRENT)
        self.repo("hooks-only", settings=full)
        self.repo("bad-settings", tool=HOOKS_CURRENT, settings="{not json")
        self.repo("v1", settings=settings_text(v1=True))
        self.repo("absent")
        report = self.ws.report()
        status = {name: self.hooks_of(report, name) for name in
                  ("current", "no-stop", "behind", "edited", "tool-only", "hooks-only", "bad-settings", "v1",
                   "absent")}
        self.assertEqual({name: item["status"] for name, item in status.items()}, {
            "current": "current", "no-stop": "current (no stop)", "behind": "behind", "edited": "edited",
            "tool-only": "partial", "hooks-only": "partial", "bad-settings": "partial", "v1": "v1",
            "absent": "absent"})
        self.assertEqual(status["current"]["release"], "1.1.0")
        self.assertTrue(status["current"]["stop"])
        self.assertFalse(status["no-stop"]["stop"])
        self.assertEqual(status["no-stop"]["release"], "1.1.0")
        self.assertEqual((status["behind"]["release"], status["behind"]["sha256"]), ("1.0.0", sha256(HOOKS_OLD)))
        self.assertIsNone(status["edited"]["release"])
        self.assertIsNone(status["absent"]["sha256"])
        self.assertEqual(sorted(kinds_of(report, "needs_review")), [
            ("bad-settings", "hooks-partial"), ("behind", "hooks-behind"), ("edited", "hooks-edited"),
            ("hooks-only", "hooks-partial"), ("tool-only", "hooks-partial"), ("v1", "hooks-v1")])
        self.assertEqual(report["summary"]["inbox"]["needs_review"], 6)
        self.assertEqual(report["summary"]["hooks"], {
            "current": 1, "current (no stop)": 1, "behind": 1, "edited": 1, "draft": 0,
            "v1": 1, "partial": 3, "absent": 1, "unreadable": 0})

    def test_the_review_command_names_the_template_tool_and_the_instance(self) -> None:
        self.repo("plain-behind", tool=HOOKS_OLD, settings=settings_text(
            "SessionStart", "UserPromptSubmit", "Stop"))
        self.repo("with-plugin", tool=HOOKS_OLD, settings=settings_text(
            "SessionStart", "UserPromptSubmit", "Stop"), plugin=PLUGIN_CURRENT)
        self.repo("current-with-plugin", tool=HOOKS_CURRENT, settings=settings_text(
            "SessionStart", "UserPromptSubmit", "Stop"), plugin=PLUGIN_OLD)  # plugin drift alone is silent
        report = self.ws.report()
        items = {item["repository"]: item for item in report["inbox"]["needs_review"]}
        self.assertEqual(sorted(items), ["plain-behind", "with-plugin"])
        base = f"python3 {self.ws.template}/scripts/projectstate_hooks.py install --root"
        self.assertEqual(items["plain-behind"]["command"], f"{base} {self.ws.root}/plain-behind")
        self.assertEqual(items["with-plugin"]["command"], f"{base} {self.ws.root}/with-plugin --host all")
        self.assertTrue(items["with-plugin"]["message"].endswith(f"{base} {self.ws.root}/with-plugin --host all"))

    def test_opencode_plugin_statuses(self) -> None:
        self.repo("current", plugin=PLUGIN_CURRENT)
        self.repo("behind", plugin=PLUGIN_OLD)
        self.repo("edited", plugin=PLUGIN_CURRENT + b"// local edit\n")
        self.repo("legacy", legacy_plugin=PLUGIN_CURRENT)
        self.repo("absent")
        report = self.ws.report()
        opencode = {name: repo_of(report, name)["opencode"] for name in
                    ("current", "behind", "edited", "legacy", "absent")}
        self.assertEqual({name: item["status"] for name, item in opencode.items()}, {
            "current": "current", "behind": "behind", "edited": "edited", "legacy": "current", "absent": "absent"})
        self.assertTrue(opencode["legacy"]["legacy"])
        self.assertFalse(opencode["current"]["legacy"])
        self.assertEqual(opencode["behind"]["release"], "1.0.0")
        self.assertEqual(opencode["current"]["sha256"], sha256(PLUGIN_CURRENT))
        self.assertEqual(report["inbox"]["needs_review"], [])  # the plugin is opt-in: drift alone is not reviewed
        self.assertEqual(report["summary"]["opencode"],
                         {"current": 2, "behind": 1, "edited": 1, "draft": 0, "absent": 1, "unreadable": 0})

    def test_an_instance_carrying_the_draft_hooks_candidate_reads_draft(self) -> None:
        candidate = HOOKS_CURRENT + b"# not released yet\n"
        write_files(self.ws.template, {"scripts/projectstate_hooks.py": candidate})
        self.repo("candidate", tool=candidate, settings=settings_text(
            "SessionStart", "UserPromptSubmit", "Stop"))
        report = self.ws.report()
        self.assertEqual(self.hooks_of(report, "candidate")["status"], "draft")
        self.assertEqual(self.hooks_of(report, "candidate")["release"], "1.2.0")
        self.assertEqual(report["inbox"]["needs_review"], [])

    def test_a_symlinked_hooks_tool_is_reported_unreadable_and_never_read(self) -> None:
        repo = self.repo("linked", settings=settings_text("SessionStart", "UserPromptSubmit", "Stop"))
        (self.ws.base / "outside.py").write_bytes(HOOKS_CURRENT)
        os.symlink(self.ws.base / "outside.py", repo / "scripts" / "projectstate_hooks.py")
        report = self.ws.report()
        linked = self.hooks_of(report, "linked")
        self.assertEqual((linked["status"], linked["sha256"]), ("unreadable", None))
        self.assertEqual(report["summary"]["hooks"]["unreadable"], 1)


class ContextSizeTests(FleetTestCase):
    def test_notices_are_counted_from_blocks_and_headings(self) -> None:
        agents = (
            "<!-- projectstate-persistent-threads-2026-09-05:start -->\n"
            "## Required first action - refresh ProjectState\n\nBody.\n"
            "<!-- projectstate-long-run-control-2026-09-06:start -->\n"
            "# Latest required refresh\n\n"
            "### Required first action\n\n"
            "#### Required first action (level four does not count)\n\n"
            "## Unrelated heading\n\n"
            "```\n<!-- projectstate-in-fence:start -->\n## Required first action\n```\n"
            "<!-- projectstate:managed:start release=1.1.0 -->\n"  # the managed marker is not a notice
            + BLOCK_CURRENT + "<!-- projectstate:managed:end -->\n"
        )
        self.ws.add_v6("noisy", agents=agents)
        self.ws.add_v6("quiet")
        report = self.ws.report()
        self.assertEqual(repo_of(report, "noisy")["notices"], {"blocks": 2, "headings": 3, "total": 5})
        self.assertEqual(repo_of(report, "quiet")["notices"]["total"], 0)
        self.assertEqual(report["summary"]["notices"], 5)

    def test_sizes_tokens_and_flags(self) -> None:
        self.ws.add_v6("small")
        self.ws.add_v6("heavy", extra={"PROJECT.md": PROJECT_MD + "x" * 6200}, padding=250)  # STATE > 16384
        long_local = "---\nrole: test\n---\n" + "local line\n" * 151
        self.ws.add_v6("long-local", agents=long_local + "\n" + fleet.release_mod.render_managed_block("1.1.0", BLOCK_CURRENT))
        self.ws.add_v6("long-plain", agents="line\n" * 201)
        self.ws.add_v6("fits", agents="---\nrole: test\n---\n" + "local line\n" * 150
                       + fleet.release_mod.render_managed_block("1.1.0", "block line\n" * 80))
        report = self.ws.report()
        small = repo_of(report, "small")["sizes"]
        total = sum(small[key]["bytes"] for key in ("agents", "project", "state"))
        self.assertEqual(small["startup_tokens"], total // 4)
        self.assertEqual(small["flags"], [])
        self.assertEqual(small["agents"]["lines"], PLAIN_AGENTS.count("\n"))
        heavy = repo_of(report, "heavy")["sizes"]
        self.assertGreater(heavy["state"]["bytes"], 16384)
        self.assertGreater(heavy["project"]["bytes"], 6144)
        self.assertEqual(len(heavy["flags"]), 2)
        self.assertTrue(heavy["flags"][0].startswith("STATE.yaml") and heavy["flags"][1].startswith("PROJECT.md"))
        local = repo_of(report, "long-local")["sizes"]
        self.assertEqual(local["local_lines"], 152)  # frontmatter and managed block are not local lines
        self.assertEqual(len(local["flags"]), 1)
        self.assertIn("local lines", local["flags"][0])
        self.assertEqual(len(repo_of(report, "long-plain")["sizes"]["flags"]), 1)
        fits = repo_of(report, "fits")["sizes"]
        self.assertEqual((fits["local_lines"], fits["flags"]), (150, []))  # a long managed block is not penalized
        self.assertEqual(report["summary"]["size_flagged"], 3)

    def test_owner_directives_are_counted_and_expired_ones_listed(self) -> None:
        agents = (
            "# Local rules\n\n"
            "## Owner directives\n\n"
            "- 2026-09-01 Do not touch the vault until 2026-09-30\n"
            "- 2026-09-02 Keep the demo frozen until 2026-12-01\n"
            "- 2026-09-03 A directive with no end date\n"
            "  - 2026-09-04 nested bullets are not directives until 2026-01-01\n"
            "### Sub heading stays inside the section\n"
            "- 2026-09-05 Pause releases until 2026-10-05\n"
            "```\n- 2026-09-06 inside a fence until 2026-01-01\n```\n\n"
            "## Other section\n\n"
            "- 2026-09-07 Outside the section until 2026-01-01\n"
        )
        self.ws.add_v6("directed", agents=agents, extra={"PROJECT.md": PROJECT_MD + "\n## Owner directives\n\n"
                                                         "- 2026-08-01 Freeze scope until 2026-08-31\n"})
        report = self.ws.report()
        directives = repo_of(report, "directed")["directives"]
        self.assertEqual((directives["total"], directives["expired"]), (4, 3))
        self.assertEqual(sorted(item["until"] for item in directives["expired_items"]),
                         ["2026-08-31", "2026-09-30", "2026-10-05"])
        self.assertEqual(kinds_of(report, "needs_review"), [("directed", "directive-expired")] * 3)


class InboxTests(FleetTestCase):
    def test_awaiting_owner_blocked_and_expiring_risk_items(self) -> None:
        self.ws.add_v6("waiting", slice_id="ship-001", status="validated", journey="passed")
        self.ws.add_v6("review", slice_id="ship-002", status="ready_for_human", journey="passed")
        self.ws.add_v6("decided", slice_id="ship-003", status="accepted", journey="passed", human="accepted")
        self.ws.add_v6("working", status="implementing", journey="not_run")
        self.ws.add_v6("stuck", status="blocked", blockers=["Waiting for the vendor API key", "Second blocker"])
        self.ws.add_v6("blocked-run", status="implementing", journey="blocked")
        risks = (RISK.format(id="soon", expires="2026-10-10") + RISK.format(id="late", expires="2026-09-30")
                 + RISK.format(id="edge", expires="2026-10-20") + RISK.format(id="far", expires="2026-10-21"))
        self.ws.add_v6("risky", risks=risks)
        report = self.ws.report()

        decisions = report["inbox"]["decisions"]
        self.assertEqual([item["repository"] for item in decisions], ["review", "waiting"])
        waiting = next(item for item in decisions if item["repository"] == "waiting")
        quoted = f"{self.ws.template}/scripts/projectstate_decide.py {self.ws.root}/waiting"
        self.assertEqual(waiting["message"], f'waiting: ship-001 is validated and waits for your decision. Run: '
                                             f'python3 {quoted} accept|reject|waive "<your words>"')
        self.assertEqual(waiting["slice"], "ship-001")
        self.assertEqual(repo_of(report, "waiting")["verdict"], {"verdict": "validated", "detail": None})

        blocked = {item["repository"]: item for item in report["inbox"]["blocked"]}
        self.assertEqual(sorted(blocked), ["blocked-run", "stuck"])
        self.assertEqual(blocked["stuck"]["message"],
                         "stuck: demo-001 is blocked (slice status): Waiting for the vendor API key")
        self.assertIn("primary journey", blocked["blocked-run"]["message"])
        self.assertIn("primary journey is blocked", blocked["blocked-run"]["blocker"])  # falls back to the gate's text

        risk_items = {item["id"]: item for item in report["inbox"]["needs_review"] if item["kind"] == "risk-acceptance"}
        self.assertEqual(sorted(risk_items), ["edge", "late", "soon"])  # 14 days out is included, 15 is not
        self.assertEqual((risk_items["soon"]["days_left"], risk_items["late"]["days_left"]), (4, -6))
        self.assertIn("expired on 2026-09-30 (6 days ago)", risk_items["late"]["message"])
        self.assertIn("expires on 2026-10-10 (in 4 days)", risk_items["soon"]["message"])
        self.assertEqual(report["summary"]["inbox"],
                         {"decisions": 2, "blocked": 2, "needs_review": 3, "ready_to_merge": 0})

    def test_inbox_sections_are_ordered_and_empty_sections_say_none(self) -> None:
        self.ws.add_v6("quiet")
        code, out, _ = run_cli(*self.ws.args("--stdout"))
        self.assertEqual(code, 0)
        headings = [line for line in out.splitlines() if line.startswith("## ")]
        self.assertEqual(headings[:4], ["## Your decisions (0)", "## Blocked (0)", "## Needs review (0)",
                                        "## Ready to merge (0)"])
        inbox = out.split("## ProjectState v6 repositories")[0]
        self.assertEqual(inbox.count("\nNone.\n"), 4)


class SilentReplacementTests(FleetTestCase):
    def replace_slice(self, repo: Path, new_id: str, *, date: str | None) -> None:
        (repo / "STATE.yaml").write_text(state_yaml(new_id), encoding="utf-8")
        write_files(repo, {f"evidence/{new_id}/summary.md": summary_md(new_id)})
        if date:
            commit(repo, f"start {new_id}", date)

    def waiting_repo(self, name: str, *, owner_decision: bool = False, managed: bool = True) -> Path:
        # A managed block committed with the repository means the owner-decision rule applies from then on.
        agents = managed_agents("1.1.0", BLOCK_CURRENT) if managed else PLAIN_AGENTS
        return self.ws.add_v6(name, slice_id="alpha-001", status="validated", journey="passed",
                              owner_decision=owner_decision, agents=agents)

    def test_replacement_without_an_owner_decision_is_reported(self) -> None:
        repo = self.waiting_repo("swap")
        self.replace_slice(repo, "beta-002", date=DATE_2)
        report = self.ws.report()
        found = repo_of(report, "swap")["silent_replacements"]
        self.assertEqual([(item["from"], item["to"], item["date"], item["uncommitted"]) for item in found],
                         [("alpha-001", "beta-002", "2026-09-03", False)])
        self.assertEqual(kinds_of(report, "needs_review"), [("swap", "silent-replacement")])
        self.assertIn("slice alpha-001 was replaced by beta-002 (on 2026-09-03)", report["inbox"]["needs_review"][0]["message"])
        self.assertEqual(repo_of(report, "swap")["slice"]["id"], "beta-002")

    def test_replacement_before_the_rule_was_adopted_is_history_not_review(self) -> None:
        repo = self.waiting_repo("legacy", managed=False)
        self.replace_slice(repo, "beta-002", date=DATE_2)
        report = self.ws.report()
        self.assertEqual(len(repo_of(report, "legacy")["silent_replacements"]), 1)  # still recorded as data
        self.assertIsNone(repo_of(report, "legacy")["rule_since"])
        self.assertEqual(report["inbox"]["needs_review"], [])
        self.assertEqual(report["summary"]["silent_replacements_before_rule"], 1)

    def test_owner_decision_record_clears_the_replacement(self) -> None:
        repo = self.waiting_repo("recorded", owner_decision=True)
        self.replace_slice(repo, "beta-002", date=DATE_2)
        self.assertEqual(repo_of(self.ws.report(), "recorded")["silent_replacements"], [])

    def test_owner_decision_falls_back_to_head_when_the_working_file_is_gone(self) -> None:
        repo = self.waiting_repo("head-record", owner_decision=True)
        self.replace_slice(repo, "beta-002", date=DATE_2)
        (repo / "evidence" / "alpha-001" / "summary.md").unlink()  # deleted in the working tree, still in HEAD
        self.assertEqual(repo_of(self.ws.report(), "head-record")["silent_replacements"], [])
        git(repo, "rm", "-q", "evidence/alpha-001/summary.md")
        commit(repo, "drop old evidence", DATE_3)  # now neither the working tree nor HEAD has the record
        self.assertEqual(len(repo_of(self.ws.report(), "head-record")["silent_replacements"]), 1)

    def test_replacing_a_slice_that_was_not_awaiting_the_owner_is_not_silent(self) -> None:
        working = self.ws.add_v6("working", slice_id="alpha-001", status="implementing")
        self.replace_slice(working, "beta-002", date=DATE_2)
        accepted = self.ws.add_v6("accepted", slice_id="alpha-001", status="accepted", journey="passed",
                                  human="accepted")
        self.replace_slice(accepted, "beta-002", date=DATE_2)
        report = self.ws.report()
        self.assertEqual(repo_of(report, "working")["silent_replacements"], [])
        self.assertEqual(repo_of(report, "accepted")["silent_replacements"], [])
        self.assertEqual(report["inbox"]["needs_review"], [])

    def test_uncommitted_replacement_is_reported(self) -> None:
        repo = self.waiting_repo("wip")
        self.replace_slice(repo, "beta-002", date=None)
        report = self.ws.report()
        found = repo_of(report, "wip")["silent_replacements"]
        self.assertEqual([(item["from"], item["to"], item["date"], item["uncommitted"]) for item in found],
                         [("alpha-001", "beta-002", None, True)])
        self.assertIn("(uncommitted)", report["inbox"]["needs_review"][0]["message"])
        self.assertIsNone(repo_of(report, "wip")["history"]["age_days"])  # an uncommitted slice has unknown age

    def test_unparsable_historical_versions_are_skipped(self) -> None:
        repo = self.waiting_repo("history")
        (repo / "STATE.yaml").write_text("id: broken\n  id: nope\n\tbad", encoding="utf-8")
        commit(repo, "corrupt state", DATE_2)
        self.replace_slice(repo, "beta-002", date=DATE_3)
        report = self.ws.report()
        self.assertEqual(repo_of(report, "history")["kind"], "v6")
        self.assertEqual(repo_of(report, "history")["silent_replacements"], [])


class HistoryAndGitTests(FleetTestCase):
    def test_slice_age_and_state_churn(self) -> None:
        repo = self.ws.add_v6("aging", date=DATE_1)
        (repo / "notes.txt").write_text("a\n")
        commit(repo, "notes", DATE_2)
        (repo / "STATE.yaml").write_text(state_yaml(next_action="Do the second thing."), encoding="utf-8")
        commit(repo, "state", DATE_3)
        (repo / "notes.txt").write_text("b\n")
        commit(repo, "notes again", DATE_4)
        history = repo_of(self.ws.report(), "aging")["history"]
        self.assertEqual(history, {"first_commit": "2026-09-01", "age_days": 35, "state_commits": 2, "all_commits": 4})
        table = run_cli(*self.ws.args("--stdout"))[1]
        self.assertIn("| 35 | 2/4 |", table)

    def test_git_facts_branch_head_date_upstream_and_dirty_counts(self) -> None:
        repo = self.ws.add_v6("facts", date=DATE_3, extra={"README.md": "first\n"})
        git(repo, "branch", "base")
        git(repo, "branch", "--set-upstream-to=base", "main")
        (repo / "notes.txt").write_text("notes\n")
        commit(repo, "notes", DATE_4)
        (repo / "README.md").write_text("changed\n")  # modified, not staged
        (repo / "staged.txt").write_text("s\n")
        git(repo, "add", "staged.txt")  # staged
        (repo / "scratch.txt").write_text("u\n")  # untracked
        (repo / "more.txt").write_text("u2\n")  # untracked
        self.ws.add_v6("plain", date=DATE_3)
        report = self.ws.report()
        facts = repo_of(report, "facts")["git"]
        head = git(repo, "rev-parse", "HEAD").strip()
        self.assertEqual((facts["branch"], facts["last_commit"], facts["upstream"]), ("main", "2026-09-12", "base"))
        self.assertTrue(head.startswith(facts["head"]) and len(facts["head"]) >= 7)
        self.assertEqual((facts["staged"], facts["unstaged"], facts["untracked"], facts["error"]), (1, 1, 2, None))
        plain = repo_of(report, "plain")["git"]
        self.assertEqual((plain["upstream"], plain["staged"], plain["unstaged"], plain["untracked"]), (None, 0, 0, 0))
        table = run_cli(*self.ws.args("--stdout"))[1]
        self.assertIn("| facts | current | unmanaged | absent | demo-001 | implementing | not_run | pending | 26 | 1/2 | ", table)
        self.assertIn("+1 ~1 ?2 |", table)

    def test_status_counts_cover_staged_unstaged_untracked_conflicts_and_ignored(self) -> None:
        self.assertEqual(fleet.count_status(" M a\nM  b\nMM c\n?? d\n?? e\n!! f\nUU g\nA  h\n"), (4, 3, 2))
        self.assertEqual(fleet.count_status(""), (0, 0, 0))

    def test_detached_head_and_unborn_repository(self) -> None:
        detached = self.ws.add_v6("detached")
        git(detached, "checkout", "-q", "--detach")
        unborn = self.ws.root / "unborn"
        unborn.mkdir()
        subprocess.run(["git", "init", "-q", "-b", "main", str(unborn)], check=True)
        report = self.ws.report()
        self.assertEqual(repo_of(report, "detached")["git"]["branch"], "(detached)")
        facts = repo_of(report, "unborn")["git"]
        self.assertEqual((repo_of(report, "unborn")["kind"], facts["branch"], facts["head"], facts["last_commit"]),
                         ("other", "main", None, None))

    def test_update_branch_detection(self) -> None:
        release = "projectstate/release-1.1.0"
        ahead = self.ws.add_v6("ahead")
        git(ahead, "switch", "-q", "-c", release)
        (ahead / "gate-update.txt").write_text("mechanical update\n")
        commit(ahead, "update", DATE_2)
        git(ahead, "switch", "-q", "main")
        merged = self.ws.add_v6("merged")
        git(merged, "branch", release)
        diverged = self.ws.add_v6("diverged")
        git(diverged, "switch", "-q", "-c", release)
        (diverged / "gate-update.txt").write_text("update\n")
        commit(diverged, "update", DATE_2)
        git(diverged, "switch", "-q", "main")
        (diverged / "local.txt").write_text("local work\n")
        commit(diverged, "local", DATE_3)
        old = self.ws.add_v6("old")
        git(old, "switch", "-q", "-c", "projectstate/release-1.0.0")
        (old / "x.txt").write_text("x\n")
        commit(old, "old update", DATE_2)
        git(old, "switch", "-q", "main")
        self.ws.add_v6("none")
        # A second checkout of "ahead" (shared refs) whose HEAD moved on: the branch is not for it.
        shared = self.ws.root / "ahead-checkout"
        git(ahead, "worktree", "add", "-q", "-b", "other", str(shared), "main")
        commit(shared, "other work", DATE_3)
        report = self.ws.report()
        branches = {item["repository"]: item for item in report["inbox"]["ready_to_merge"]}
        self.assertEqual(sorted(branches), ["ahead"])  # only branches that can fast-forward are ready
        self.assertEqual(branches["ahead"]["command"], f"git -C {self.ws.root}/ahead merge --ff-only {release}")
        self.assertTrue(branches["ahead"]["fast_forward"])
        stale = [item for item in report["inbox"]["needs_review"] if item["kind"] == "update-branch-stale"]
        self.assertEqual([item["repository"] for item in stale], ["diverged"])  # not the shared checkout
        self.assertFalse(stale[0]["fast_forward"])
        self.assertIsNone(repo_of(report, "merged")["update_branch"])
        self.assertIsNone(repo_of(report, "old")["update_branch"])  # only the current release's branch counts

    def test_git_commands_are_local_read_only_and_hardened(self) -> None:
        self.ws.add_v6("a", slice_id="alpha-001", status="validated", journey="passed")
        self.replace_and_commit("a")
        calls: list[list[str]] = []
        real_run = subprocess.run

        def spy(command: list[str], **kwargs: object) -> subprocess.CompletedProcess:
            calls.append(list(command))
            env = kwargs["env"]
            self.assertEqual((env["GIT_OPTIONAL_LOCKS"], env["GIT_TERMINAL_PROMPT"]), ("0", "0"))  # type: ignore[index]
            self.assertNotIn("GIT_DIR", env)  # type: ignore[operator]
            self.assertIn("timeout", kwargs)
            return real_run(command, **kwargs)  # type: ignore[call-overload]

        with mock.patch.dict(os.environ, {"GIT_DIR": "/nonexistent", "GIT_WORK_TREE": "/nonexistent"}):
            with mock.patch.object(fleet.subprocess, "run", side_effect=spy):
                report = self.ws.report()
        self.assertEqual(repo_of(report, "a")["git"]["branch"], "main")  # GIT_DIR in the caller's env is ignored
        self.assertGreater(len(calls), 5)
        subcommands = set()
        for command in calls:
            self.assertEqual(command[:2], ["git", "--no-pager"])
            self.assertIn("core.fsmonitor=false", command)
            subcommands.add(command[command.index("core.fsmonitor=false") + 1])
        self.assertLessEqual(subcommands, {"symbolic-ref", "log", "rev-parse", "status", "rev-list", "cat-file",
                                           "merge-base"})

    def replace_and_commit(self, name: str) -> None:
        repo = self.ws.root / name
        (repo / "STATE.yaml").write_text(state_yaml("beta-002"), encoding="utf-8")
        commit(repo, "replace", DATE_2)


class DiscoveryTests(FleetTestCase):
    def test_kinds_v5_other_invalid_and_both_state_files(self) -> None:
        self.ws.add("v5-only", {"PROJECT_STATE.yaml": "schema: v5\n", "AGENTS.md": PLAIN_AGENTS})
        self.ws.add_v6("both", extra={"PROJECT_STATE.yaml": "schema: v5\n"})
        self.ws.add("plain-dir", {"README.md": "hello\n"}, date=None)
        self.ws.add("git-only", {"README.md": "hello\n"})
        self.ws.add("dup-keys", {"STATE.yaml": "version: x\nversion: y\n"})
        self.ws.add("wrong-version", {"STATE.yaml": 'version: "projectstate-template-v5"\nprofile: core\n',
                                      "PROJECT_STATE.yaml": "schema: v5\n"})
        self.ws.add("empty-state", {"STATE.yaml": ""})
        report = self.ws.report()
        kinds = {repo["name"]: repo["kind"] for repo in report["repositories"]}
        self.assertEqual(kinds, {"v5-only": "v5", "both": "v6", "plain-dir": "other", "git-only": "other",
                                 "dup-keys": "v6-invalid", "wrong-version": "v6-invalid", "empty-state": "v6-invalid"})
        self.assertIn("duplicate key", repo_of(report, "dup-keys")["problem"])
        self.assertIn("projectstate-template-v6", repo_of(report, "wrong-version")["problem"])
        self.assertIsNone(repo_of(report, "plain-dir")["git"])
        self.assertEqual(repo_of(report, "git-only")["git"]["last_commit"], "2026-09-01")
        self.assertNotIn("gate", repo_of(report, "v5-only"))
        self.assertEqual(report["summary"]["kinds"], {"v6": 1, "v6-invalid": 3, "v5": 1, "other": 2})

    def test_unparsable_state_is_reported_without_stopping_the_scan(self) -> None:
        self.ws.add("aaa-broken", {"STATE.yaml": "current_slice: [unclosed\n\t- tab\n"})
        linked = self.ws.add("bbb-linked", {"README.md": "x\n"})
        os.symlink(self.ws.base / "nowhere", linked / "STATE.yaml")  # dangling symlink: refused, not followed
        self.ws.add_v6("zzz-good", status="validated", journey="passed")
        code, out, _ = run_cli(*self.ws.args("--stdout"))
        self.assertEqual(code, 0)
        report = self.ws.report()
        self.assertEqual([repo["kind"] for repo in report["repositories"]], ["v6-invalid", "v6-invalid", "v6"])
        self.assertIn("symlink", repo_of(report, "bbb-linked")["problem"])
        self.assertEqual(len(report["inbox"]["decisions"]), 1)  # the good repository after the broken ones is scanned
        self.assertIn("Unreadable STATE.yaml: 2:", out)

    def test_discovery_skips_symlinks_hidden_underscore_and_files_and_sorts_case_insensitively(self) -> None:
        for name in ("beta", "Alpha", "alpha2", "Zed", ".hidden", "_private"):
            self.ws.add_v6(name)
        (self.ws.root / "notes.txt").write_text("not a directory\n")
        os.symlink(self.ws.root / "beta", self.ws.root / "linked-beta")
        os.symlink(self.ws.base, self.ws.root / "linked-dir")
        report = self.ws.report()
        self.assertEqual([repo["name"] for repo in report["repositories"]], ["Alpha", "alpha2", "beta", "Zed"])

    def test_gate_crash_or_unreadable_state_never_stops_the_scan(self) -> None:
        self.ws.add_v6("first")
        self.ws.add_v6("second")
        with mock.patch.object(fleet.gate_mod, "validate", side_effect=RuntimeError("boom")):
            report = self.ws.report()
        for name in ("first", "second"):
            self.assertEqual(repo_of(report, name)["verdict"]["verdict"], "invalid")
            self.assertIn("gate failed", repo_of(report, name)["verdict"]["detail"])

    def test_gate_verdicts_and_detail_length(self) -> None:
        self.ws.add_v6("validated", status="validated", journey="passed")
        self.ws.add_v6("open", status="implementing", journey="not_run")
        self.ws.add_v6("invalid", status="validated", journey="not_run")  # closure status needs a passed journey
        self.ws.add_v6("wordy", status="validated", journey="passed", blockers=["B" * 400])
        report = self.ws.report()
        self.assertEqual(repo_of(report, "validated")["verdict"], {"verdict": "validated", "detail": None})
        self.assertEqual(repo_of(report, "open")["verdict"]["verdict"], "not validated")
        self.assertIn("primary journey is not_run", repo_of(report, "open")["verdict"]["detail"])
        self.assertEqual(repo_of(report, "invalid")["verdict"]["verdict"], "invalid")
        self.assertIn("requires a passed primary journey", repo_of(report, "invalid")["verdict"]["detail"])
        wordy = repo_of(report, "wordy")["verdict"]
        self.assertEqual(wordy["verdict"], "not validated")
        self.assertEqual(len(wordy["detail"]), 160)
        self.assertTrue(wordy["detail"].endswith("..."))
        self.assertEqual(report["summary"]["verdicts"], {"validated": 1, "not validated": 2, "invalid": 1})

    def test_slice_summary_fields_are_clipped(self) -> None:
        self.ws.add_v6("clipped", objective="O" * 300, next_action="N" * 300, status="validated", journey="passed")
        current = repo_of(self.ws.report(), "clipped")["slice"]
        self.assertEqual((current["id"], current["status"], current["journey"], current["human_acceptance"]),
                         ("demo-001", "validated", "passed", "pending"))
        self.assertEqual((len(current["objective"]), len(current["next_action"])), (120, 160))


class CommandLineTests(FleetTestCase):
    def populate(self) -> None:
        self.ws.add_v6("alpha", slice_id="alpha-001", status="validated", journey="passed")
        self.ws.add_v6("beta", gate=GATE_OLD)
        self.ws.add("v5", {"PROJECT_STATE.yaml": "schema: v5\n"})
        self.ws.add("loose", {"README.md": "x\n"}, date=None)

    def test_out_inside_root_is_refused_with_exit_2(self) -> None:
        self.populate()
        for target in (self.ws.root / "reports", self.ws.root, self.ws.root / "alpha" / "docs"):
            before = tree_state(self.ws.root)
            code, out, err = run_cli(*self.ws.args("--out", str(target)))
            self.assertEqual(code, 2)
            self.assertEqual(out, "")
            self.assertIn("inside --root", err)
            self.assertEqual(tree_state(self.ws.root), before)
        linked = self.ws.base / "sneaky"
        os.symlink(self.ws.root / "alpha", linked)  # a symlink into the root is resolved before the check
        self.assertEqual(run_cli(*self.ws.args("--out", str(linked / "docs")))[0], 2)
        self.assertEqual(run_cli(*self.ws.args("--out", str(self.ws.root / "x"), "--stdout"))[0], 2)

    def test_stdout_writes_nothing(self) -> None:
        self.populate()
        before = tree_state(self.ws.base)
        for fmt in ("md", "json"):
            code, out, err = run_cli(*self.ws.args("--stdout", "--format", fmt))
            self.assertEqual((code, err), (0, ""))
            self.assertTrue(out.startswith("# ProjectState fleet\n") if fmt == "md" else out.startswith("{"))
        self.assertEqual(tree_state(self.ws.base), before)
        self.assertFalse(self.ws.out.exists())

    def test_default_run_writes_report_files_atomically_and_nothing_inside_any_repository(self) -> None:
        ws = Workspace(Path(tempfile.mkdtemp(dir=self._tmp.name)).resolve(), template_in_root=True)
        ws.add_v6("alpha", slice_id="alpha-001", status="validated", journey="passed")
        ws.add_v6("beta", gate=GATE_OLD, extra={"dirty.txt": "uncommitted\n"})
        ws.add("v5", {"PROJECT_STATE.yaml": "schema: v5\n"})
        ws.add("loose", {"README.md": "x\n"}, date=None)
        ahead = ws.add_v6("ahead")
        git(ahead, "switch", "-q", "-c", "projectstate/release-1.1.0")
        (ahead / "u.txt").write_text("u\n")
        commit(ahead, "update", DATE_2)
        git(ahead, "switch", "-q", "main")
        for repo in (ws.root / "alpha", ws.root / "beta"):  # stale stat data tempts git status to refresh the index
            os.utime(repo / "STATE.yaml", (1_700_000_000, 1_700_000_000))
        os.symlink(ws.root / "alpha", ws.root / "linked")
        before = tree_state(ws.root)
        self.assertTrue(any(path.endswith(".git/index") for path in before))
        script = ws.template / "scripts" / "projectstate_fleet.py"
        done = subprocess.run([sys.executable, str(script), "--out", str(ws.out), "--today", TODAY],
                              capture_output=True, text=True, cwd=ws.base, check=False)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(tree_state(ws.root), before)  # no file, directory, ref, index or bytecode changed
        self.assertEqual(sorted(os.listdir(ws.out)), ["fleet.json", "fleet.md"])
        lines = done.stdout.splitlines()
        self.assertEqual(lines[:2], [str(ws.out / "fleet.md"), str(ws.out / "fleet.json")])
        self.assertTrue(lines[2].startswith("fleet: "))
        self.assertIn("1 decisions", lines[2])
        self.assertEqual(len(lines), 3)
        report = json.loads((ws.out / "fleet.json").read_text(encoding="utf-8"))
        self.assertEqual(report["format"], "projectstate-fleet/1")
        self.assertEqual(report["root"], str(ws.root))  # default root is the template's parent
        self.assertEqual(report["template"]["path"], str(ws.template))
        self.assertEqual(repo_of(report, "ProjectState_Template")["role"], "template")
        self.assertTrue((ws.out / "fleet.md").read_text(encoding="utf-8").startswith("# ProjectState fleet\n"))

    def test_report_is_deterministic_apart_from_the_generation_time(self) -> None:
        self.populate()
        first, second = self.ws.report(), self.ws.report()
        first.pop("generated"), second.pop("generated")
        self.assertEqual(first, second)
        one = [line for line in run_cli(*self.ws.args("--stdout"))[1].splitlines() if not line.startswith("Generated ")]
        two = [line for line in run_cli(*self.ws.args("--stdout"))[1].splitlines() if not line.startswith("Generated ")]
        self.assertEqual(one, two)

    def test_markdown_report_layout(self) -> None:
        self.populate()
        self.ws.add_v6("stuck", status="blocked", blockers=["Needs | a pipe"])
        text = run_cli(*self.ws.args("--stdout"))[1]
        lines = text.splitlines()
        self.assertEqual(lines[0], "# ProjectState fleet")
        self.assertRegex(lines[2], r"^Generated \S+(, date set to 2026-10-06)?; template release 1\.1\.0 "
                                   r"\(draft 1\.2\.0 in progress\); root " + re.escape(str(self.ws.root)) + "$")
        self.assertEqual(lines[4], "Read-only: no repository was modified.")
        self.assertEqual([line for line in lines if line.startswith("## ")], [
            "## Your decisions (1)", "## Blocked (1)", "## Needs review (0)", "## Ready to merge (0)",
            "## ProjectState v6 repositories (3)", "## v5 and other repositories (2)", "## Summary"])
        header = ("| repository | gate | contract | hooks | slice | status | journey | owner | age days | "
                  "STATE churn | startup tokens | notices | dirty |")
        self.assertIn(header, lines)
        self.assertIn("| repository | kind | last commit | dirty |", lines)
        self.assertIn("| beta | behind (1.0.0) | unmanaged | absent | demo-001 | implementing | not_run | pending | "
                      "35 | 1/1 |", text)
        self.assertIn("| v5 | v5 | 2026-09-01 | clean |", lines)
        self.assertIn("| loose | other | - | no git |", lines)
        self.assertIn("Needs | a pipe", text)  # inbox lines are plain text; table cells escape the pipe
        self.assertTrue(text.endswith("\n"))
        self.assertIn("- Repositories: 5 (v6 3, v6-invalid 0, v5 1, other 1); 4 with git, 0 dirty.", text)

    def test_overridden_date_is_stated_in_the_header(self) -> None:
        self.ws.add_v6("quiet")
        text = run_cli("--root", str(self.ws.root), "--template", str(self.ws.template), "--stdout",
                       "--today", "2000-01-01")[1]
        self.assertRegex(text.splitlines()[2], r"^Generated \S+, date set to 2000-01-01; template release 1\.1\.0 ")

    def test_json_report_shape(self) -> None:
        self.populate()
        report = self.ws.report()
        self.assertEqual(list(report)[:8], ["format", "generated", "today", "read_only", "root", "template", "summary",
                                            "inbox"])
        self.assertEqual((report["format"], report["read_only"], report["today"]), ("projectstate-fleet/1", True, TODAY))
        self.assertEqual(report["template"]["current_release"], "1.1.0")
        self.assertEqual(report["template"]["draft_release"], "1.2.0")
        copied_gate = (self.ws.template / "scripts" / "projectstate_gate.py").read_bytes()
        self.assertEqual(report["template"]["gate_sha256"], sha256(copied_gate))
        self.assertEqual(report["template"]["contract_sha256"], fleet.release_mod.contract_sha256(BLOCK_CURRENT))
        self.assertIsNone(report["template"]["hooks_sha256"])  # the fixture template vendors no hooks tool
        self.assertIsNone(report["template"]["opencode_plugin_sha256"])
        self.assertEqual(list(report["inbox"]), ["decisions", "blocked", "needs_review", "ready_to_merge"])

    def test_bad_arguments_and_missing_index_exit_2(self) -> None:
        self.assertEqual(run_cli("--root", str(self.ws.base / "nope"), "--template", str(self.ws.template),
                                 "--stdout")[0], 2)
        self.assertEqual(run_cli("--stdout", "--today", "not-a-date")[0], 2)
        self.assertEqual(run_cli("--stdout", "--format", "xml")[0], 2)
        (self.ws.template / "releases" / "index.json").write_text("{not json", encoding="utf-8")
        code, _, err = run_cli(*self.ws.args("--stdout"))
        self.assertEqual(code, 2)
        self.assertIn("cannot read the release index", err)

    def test_released_template_has_no_draft_note(self) -> None:
        index = json.loads((self.ws.template / "releases" / "index.json").read_text(encoding="utf-8"))
        index["latest"] = "1.1.0"
        index["releases"][2]["status"] = "released"
        (self.ws.template / "releases" / "index.json").write_text(json.dumps(index), encoding="utf-8")
        text = run_cli(*self.ws.args("--stdout"))[1]
        self.assertIn("template release 1.2.0;", text)
        self.assertNotIn("draft", text.splitlines()[2])


if __name__ == "__main__":
    unittest.main()
