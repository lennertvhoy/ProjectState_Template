#!/usr/bin/env python3
"""Regression tests for the outcome-first ProjectState core."""

from __future__ import annotations

import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipapp
from collections.abc import Iterator
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

import init_template  # noqa: E402
from projectstate_release import (  # noqa: E402
    contract_sha256,
    extract_managed_block,
    gate_release,
    managed_block_text,
    normalize_newlines,
)

INIT = ROOT / "scripts" / "init_template.py"
GATE = ROOT / "scripts" / "projectstate_gate.py"
EXISTING_README = "# Existing product\n\nRun it with `make start`.\n"
HARDENED_RULE = (
    "This project uses the hardened profile. Read `HARDENED_POLICY.md` before release, security, or "
    "compliance work; its checks can add blockers but never override the primary journey."
)
LOCAL_HEADINGS = ["## Local rules", "## Owner directives"]
# Opt-in workflows add nothing to the generated file until the owner selects one.
OPT_IN_PHRASES = ("Continuation decision", "Optional persistent threads", "IMPROVE", "improvement round")
STARTUP_FILES = ("AGENTS.md", "PROJECT.md", "STATE.yaml")
STARTUP_BUDGET_CHARS = 10000  # 2.5K tokens at four characters per token
THREADS_PROMPT = ROOT / "prompts" / "PERSISTENT_THREADS.md"
THREADS_COPY_HEADING = "## Copy into the project's local sections when the owner selects this workflow"
# Distinctive sentences of the former generated "Optional persistent threads" rules.
THREAD_RULE_PHRASES = (
    "Use named threads only when the human selects this workflow and the current slice has separable work.",
    "One coordinator owns integration and writes canonical state and evidence.",
    "A thread name or past conversation is not an assignment or fresh authority.",
    "Concurrent writers use separate private branches and worktrees (or clones where required).",
    "replace stale assignments rather than adding a ledger.",
    "escalate failed narrow work instead of assuming a cheaper model plus review is always economical.",
    "Worker tests or reviewer confidence cannot establish product validation.",
    "Persistent conversations can become stale.",
    "Do not silently substitute subagents or launch background work.",
    "Two failures still trigger the simplification rule.",
)
LEGACY_TRUTH_FILES = {
    "BACKLOG.md",
    "EFFICIENCY_BUDGET.yaml",
    "NEXT_ACTIONS.md",
    "PROJECT_ADAPTER.yaml",
    "PROJECT_DNA.yaml",
    "PROJECT_STATE.yaml",
    "PROJECTSTATE_ASSETS.json",
    "STATUS.md",
    "WORKLOG.md",
    "docs/EVIDENCE_LOG.md",
}


def run_init(target: Path, *, profile: str | None = None, adopt: bool = False) -> subprocess.CompletedProcess[str]:
    command = [
        sys.executable,
        str(INIT),
        "adopt" if adopt else "new",
        "--name",
        "Outcome Demo",
        "--target",
        str(target),
    ]
    if profile is not None:
        command.extend(["--profile", profile])
    if not adopt:
        command.append("--no-init-git")
    return subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)


def run_gate(target: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(target / "scripts" / "projectstate_gate.py"), "--root", str(target)],
        cwd=target,
        capture_output=True,
        text=True,
        check=False,
    )


def generated_cases(root: Path, *, modes: tuple[bool, ...] = (False, True)) -> Iterator[tuple[str, bool, str, Path]]:
    """Generate new and adopt for core and hardened with the real CLI: (label, adopt, profile, target)."""
    for adopt in modes:
        for profile in ("core", "hardened"):
            label = f"{'adopt' if adopt else 'new'}-{profile}"
            target = root / label
            if adopt:
                target.mkdir()
                (target / "README.md").write_text(EXISTING_README, encoding="utf-8")
            completed = run_init(target, profile=profile, adopt=adopt)
            if completed.returncode != 0:
                raise AssertionError(f"{label}: {completed.stdout}{completed.stderr}")
            yield label, adopt, profile, target


def record_passing_fixture(target: Path) -> None:
    """Write synthetic records for gate tests; this does not run a product journey."""
    project = (target / "PROJECT.md").read_text(encoding="utf-8")
    project = project.replace(
        "Not yet defined — the human must confirm the primary user.",
        "A student using the local application.",
    ).replace(
        "Not yet defined — the human must state the observable product outcome.",
        "A student completes one saved workflow through the documented launcher.",
    )
    (target / "PROJECT.md").write_text(project, encoding="utf-8")

    state = (target / "STATE.yaml").read_text(encoding="utf-8")
    state = state.replace("status: planned", "status: validated", 1)
    state = state.replace(
        'description: "Not yet defined — derive the smallest end-to-end user journey from PROJECT.md."',
        'description: "Run the documented local workflow end to end."',
    ).replace(
        'command: "Not yet defined — record the exact human-authorized command."',
        'command: "python3 -m unittest"',
    ).replace(
        'environment: "Not yet defined — record the representative environment."',
        'environment: "clean local test fixture"',
    ).replace("status: not_run", "status: passed", 1)
    state = state.replace("primary_journey: not_run", "primary_journey: passed")
    state = state.replace("automated_tests: not_run", "automated_tests: passed")
    state = state.replace(
        'blockers:\n  - "Primary user and product outcome require human confirmation."',
        "blockers: []",
    )
    (target / "STATE.yaml").write_text(state, encoding="utf-8")

    evidence = (target / "evidence" / "bootstrap-001" / "summary.md").read_text(encoding="utf-8")
    evidence = evidence.replace("Environment: not recorded", "Environment: clean local test fixture")
    evidence = evidence.replace("Command: not recorded", "Command: `python3 -m unittest`")
    evidence = evidence.replace("Result: not run", "Result: passed")
    evidence = evidence.replace("Exit code: not recorded", "Exit code: 0")
    (target / "evidence" / "bootstrap-001" / "summary.md").write_text(evidence, encoding="utf-8")


class OutcomeCoreTests(unittest.TestCase):
    def test_default_profile_is_small_and_honestly_not_validated(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "core"
            completed = run_init(target)
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            self.assertIn("Profile: core", completed.stdout)
            files = {
                path.relative_to(target).as_posix()
                for path in target.rglob("*")
                if path.is_file()
            }
            self.assertEqual(
                files,
                {
                    "AGENTS.md",
                    "PROJECT.md",
                    "README.md",
                    "STATE.yaml",
                    "evidence/bootstrap-001/summary.md",
                    "scripts/projectstate_gate.py",
                },
            )
            self.assertFalse(files & LEGACY_TRUTH_FILES)
            combined = "\n".join((target / path).read_text(encoding="utf-8") for path in sorted(files))
            for forbidden in ("controlHead", "behaviouralHead", "companion control commit", "line budget"):
                self.assertNotIn(forbidden, combined)
            agents = (target / "AGENTS.md").read_text(encoding="utf-8")
            self.assertIn("The owner decides", agents)
            self.assertIn("primary journey", agents)
            self.assertIn("Two evidenced failures", agents)
            self.assertIn("never imports or requires ProjectState", agents)
            gate = run_gate(target)
            self.assertEqual(gate.returncode, 1, gate.stdout + gate.stderr)
            self.assertIn("primary journey is not_run", gate.stdout)

    def test_generated_agents_md_carries_one_managed_block_stamped_with_the_gate_release(self) -> None:
        canonical = managed_block_text()
        release = gate_release(GATE.read_text(encoding="utf-8"))
        self.assertIsNotNone(release, "the template gate must declare RELEASE")
        regions = set()
        with tempfile.TemporaryDirectory() as tmp:
            for label, _adopt, _profile, target in generated_cases(Path(tmp)):
                with self.subTest(case=label):
                    agents = normalize_newlines((target / "AGENTS.md").read_text(encoding="utf-8"))
                    block, error = extract_managed_block(agents)
                    self.assertIsNone(error)
                    self.assertIsNotNone(block)
                    self.assertEqual(agents.count("projectstate:managed:start"), 1)
                    self.assertEqual(agents.count("projectstate:managed:end"), 1)
                    self.assertEqual(contract_sha256(block.content), contract_sha256(canonical))
                    self.assertEqual(block.release, release)
                    vendored = (target / "scripts" / "projectstate_gate.py").read_text(encoding="utf-8")
                    self.assertEqual(block.release, gate_release(vendored))
                    regions.add(agents[block.start : block.end])
        self.assertEqual(len(regions), 1, "the managed block must be byte-identical across profiles and modes")

    def test_generated_agents_md_has_only_frontmatter_the_block_and_two_local_sections(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            for label, _adopt, profile, target in generated_cases(Path(tmp)):
                with self.subTest(case=label):
                    agents = normalize_newlines((target / "AGENTS.md").read_text(encoding="utf-8"))
                    block, error = extract_managed_block(agents)
                    self.assertIsNone(error)
                    before, after = agents[: block.start], agents[block.end :]
                    self.assertRegex(before, r"\A---\n(?:[a-z_]+: .*\n)+---\n\n\Z")
                    self.assertIn(f"\nprofile: {profile}\n", before)
                    self.assertEqual(re.findall(r"^## .*$", after, flags=re.MULTILINE), LOCAL_HEADINGS)
                    # Nothing else: only the headings, project-owned placeholder comments, and the hardened pointer.
                    remainder = re.sub(r"<!--.*?-->", "", after, flags=re.DOTALL).replace(HARDENED_RULE, "")
                    self.assertEqual([line for line in remainder.splitlines() if line.strip()], LOCAL_HEADINGS)
                    if profile == "hardened":
                        rule_at = after.index(HARDENED_RULE)
                        self.assertLess(after.index("## Local rules"), rule_at)
                        self.assertLess(rule_at, after.index("<!-- Project-owned"))
                        self.assertLess(rule_at, after.index("## Owner directives"))
                    else:
                        self.assertNotIn("hardened", after.lower())

    def test_generated_agents_md_carries_no_opt_in_workflow_text(self) -> None:
        # The managed block's own pointer line names "improvement rounds"; any other mention would be
        # opt-in text that must stay out of the generated file until the owner selects the workflow.
        canonical = managed_block_text()
        self.assertEqual({phrase for phrase in OPT_IN_PHRASES if phrase in canonical}, {"improvement round"})
        with tempfile.TemporaryDirectory() as tmp:
            for label, _adopt, _profile, target in generated_cases(Path(tmp)):
                with self.subTest(case=label):
                    agents = (target / "AGENTS.md").read_text(encoding="utf-8")
                    for phrase in OPT_IN_PHRASES:
                        self.assertEqual(agents.count(phrase), canonical.count(phrase), phrase)

    def test_persistent_thread_rules_live_in_the_prompt_not_the_generated_core(self) -> None:
        prompt = THREADS_PROMPT.read_text(encoding="utf-8")
        self.assertEqual(prompt.count(THREADS_COPY_HEADING), 1)
        copyable = " ".join(prompt.split(THREADS_COPY_HEADING, 1)[1].split())
        for phrase in THREAD_RULE_PHRASES:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, copyable)
        with tempfile.TemporaryDirectory() as tmp:
            for label, _adopt, _profile, target in generated_cases(Path(tmp)):
                with self.subTest(case=label):
                    agents = " ".join((target / "AGENTS.md").read_text(encoding="utf-8").split())
                    for phrase in THREAD_RULE_PHRASES:
                        self.assertNotIn(phrase, agents)

    def test_generated_startup_files_fit_the_context_budget(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            for label, _adopt, _profile, target in generated_cases(Path(tmp)):
                with self.subTest(case=label):
                    sizes = {name: len((target / name).read_text(encoding="utf-8")) for name in STARTUP_FILES}
                    self.assertLessEqual(sum(sizes.values()), STARTUP_BUDGET_CHARS, sizes)

    def test_adoption_preserves_an_existing_readme_for_both_outcome_profiles(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            for label, _adopt, _profile, target in generated_cases(Path(tmp), modes=(True,)):
                with self.subTest(case=label):
                    self.assertEqual((target / "README.md").read_text(encoding="utf-8"), EXISTING_README)

    def test_template_root_agents_md_carries_the_managed_block_exactly(self) -> None:
        agents = normalize_newlines((ROOT / "AGENTS.md").read_text(encoding="utf-8"))
        block, error = extract_managed_block(agents)
        self.assertIsNone(error)
        self.assertIsNotNone(block)
        self.assertEqual(block.content, managed_block_text())
        self.assertEqual(block.release, gate_release(GATE.read_text(encoding="utf-8")))
        for heading in ("## Template repository rules", "## Owner directives"):
            self.assertIn(f"\n{heading}\n", agents[block.end :])
        self.assertNotIn("Optional persistent threads", agents)

    def assertRenderExits(self, case: str, expected: str) -> None:
        with self.subTest(case=case):
            with self.assertRaises(SystemExit) as caught:
                init_template.render_outcome_agents_template("2026-10-06", "core")
            self.assertIn(expected, str(caught.exception))

    def test_missing_or_malformed_contract_sources_fail_loudly(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fake = Path(tmp)
            (fake / "core").mkdir()
            (fake / "scripts").mkdir()
            block_source = fake / "core" / "AGENTS.managed.md"
            gate_source = fake / "scripts" / "projectstate_gate.py"
            shutil.copy(ROOT / "core" / "AGENTS.managed.md", block_source)
            gate_source.write_text('RELEASE = "6.3.0"\n', encoding="utf-8")
            with mock.patch.object(init_template, "TEMPLATE_ROOT", fake):
                rendered = init_template.render_outcome_agents_template("2026-10-06", "core")
                block, error = extract_managed_block(rendered)
                self.assertIsNone(error, "control: valid sources must render")
                self.assertEqual(block.release, "6.3.0")

                for case, text in (
                    ("gate without a release line", "# gate\n"),
                    ("gate with a malformed release", 'RELEASE = "6.3"\n'),
                    ("gate with the release only in a comment", '# RELEASE = "6.3.0"\n'),
                ):
                    gate_source.write_text(text, encoding="utf-8")
                    self.assertRenderExits(case, "RELEASE")

                gate_source.write_text('RELEASE = "6.3.0"\n', encoding="utf-8")
                block_source.unlink()
                self.assertRenderExits("missing block source", "Cannot read the managed AGENTS.md")
                block_source.symlink_to(ROOT / "core" / "AGENTS.managed.md")
                self.assertRenderExits("symlinked block source", "Cannot read the managed AGENTS.md")
                block_source.unlink()
                shutil.copy(ROOT / "core" / "AGENTS.managed.md", block_source)
                gate_source.unlink()
                self.assertRenderExits("missing gate", "Cannot read the managed AGENTS.md")

    def test_consistent_passing_records_can_validate_core(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "core"
            self.assertEqual(run_init(target).returncode, 0)
            record_passing_fixture(target)
            gate = run_gate(target)
            self.assertEqual(gate.returncode, 0, gate.stdout + gate.stderr)
            self.assertIn("RECORDED OUTCOME VALIDATED", gate.stdout)
            self.assertIn("does not execute journeys or authenticate human approval", gate.stdout)

    def test_packaged_journey_survives_handoff(self) -> None:
        """Run a real toy product; the fresh-process handoff is not an AI benchmark."""
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            target = workspace / "core"
            self.assertEqual(run_init(target).returncode, 0)
            product = target / "product"
            (product / "notes").mkdir(parents=True)
            (product / "notes/__init__.py").write_text("", encoding="utf-8")
            (product / "notes/title.txt").write_text("Saved note", encoding="utf-8")
            (product / "__main__.py").write_text(
                "from importlib.resources import files\n"
                "from pathlib import Path\n"
                "import sys\n"
                "title = files('notes').joinpath('title.txt').read_text().strip()\n"
                "action, filename, *words = sys.argv[1:]\n"
                "if action == 'add':\n"
                "    Path(filename).write_text(' '.join(words) + '\\n')\n"
                "elif action == 'show':\n"
                "    print(title + ': ' + Path(filename).read_text().strip())\n",
                encoding="utf-8",
            )
            installed = workspace / "clean-install"
            installed.mkdir()
            artifact = installed / "notes.pyz"
            data = installed / "note.txt"
            zipapp.create_archive(product, target=artifact, filter=lambda path: path.suffix != ".txt")
            project_path = target / "PROJECT.md"
            project_path.write_text(project_path.read_text().replace(
                "Not yet defined — the human must confirm the primary user.", "A student saving a local note."
            ).replace(
                "Not yet defined — the human must state the observable product outcome.",
                "The packaged launcher saves a note and displays it after restarting."
            ))
            state_path = target / "STATE.yaml"
            command = 'python3 -I notes.pyz add note.txt "Remember this" && python3 -I notes.pyz show note.txt'
            environment = "Local Python; isolated interpreter; clean install directory outside the source tree"
            state = state_path.read_text().replace("status: planned", "status: implementing", 1)
            state = state.replace(
                'description: "Not yet defined — derive the smallest end-to-end user journey from PROJECT.md."',
                'description: "Save through the packaged launcher, restart, and read the saved note."',
            ).replace(
                'command: "Not yet defined — record the exact human-authorized command."',
                "command: " + json.dumps(command),
            ).replace(
                'environment: "Not yet defined — record the representative environment."',
                "environment: " + json.dumps(environment),
            ).replace(
                'blockers:\n  - "Primary user and product outcome require human confirmation."', "blockers: []",
            )
            state_path.write_text(state)

            def launch(entry: Path, action: str, *words: str) -> subprocess.CompletedProcess[str]:
                # Arguments are fixed by this test, never executed from recorded repo text.
                return subprocess.run(
                    [sys.executable, "-I", str(entry), action, str(data), *words],
                    cwd=installed, capture_output=True, text=True, check=False,
                )

            source_result = launch(product, "add", "Source works")
            self.assertEqual(source_result.returncode, 0, source_result.stderr)
            data.unlink()  # Clean target: a source run must not prepare the packaged journey.
            failed = launch(artifact, "add", "Remember this")
            self.assertNotEqual(failed.returncode, 0)
            self.assertIn("title.txt", failed.stderr)
            self.assertFalse(data.exists())
            summary_path = target / "evidence/bootstrap-001/summary.md"
            (summary_path.parent / "attempt-1.txt").write_text(failed.stdout + failed.stderr)
            next_action = "Include the missing packaged title.txt; rebuild notes.pyz; rerun save and show in a clean directory."
            state = state.replace("status: implementing", "status: implemented", 1)
            state = state.replace("status: not_run", "status: failed", 1).replace("primary_journey: not_run", "primary_journey: failed")
            state = state.replace("automated_tests: not_run", "automated_tests: passed")
            state = state.replace("  failed_attempts: []", (
                "  failed_attempts:\n    - evidence: evidence/bootstrap-001/attempt-1.txt\n"
                "      cause: source succeeds but the shipped archive omits title.txt"
            ))
            state = state[:state.index("next_action:")] + "next_action: " + json.dumps(next_action) + "\n"
            state_path.write_text(state)
            summary_path.write_text(
                f"# Evidence: bootstrap-001\n\n## Primary journey\n\n- Environment: {environment}\n"
                f"- Command: `{command}`\n- Result: failed\n- Exit code: {failed.returncode}\n\n"
                "## Secondary checks\n\n- Source launcher: passed; packaged launcher: failed.\n\n"
                "## Artifacts\n\n- attempt-1.txt: missing packaged title.txt.\n\n"
                "## Limitations\n\n- Human acceptance pending. No remote delivery tested.\n"
            )
            gate = run_gate(target)
            self.assertEqual(gate.returncode, 1, gate.stdout + gate.stderr)
            self.assertIn("primary journey is failed", gate.stdout)

            # A new interpreter has only the on-disk contract, state, and evidence.
            resumed = subprocess.run(
                [sys.executable, "-I", "-c",
                 "import json, pathlib, runpy, sys; root = pathlib.Path(sys.argv[1]); "
                 "gate = runpy.run_path(str(root / 'scripts/projectstate_gate.py')); "
                 "state = gate['parse_state']((root / 'STATE.yaml').read_text()); "
                 "print(json.dumps({'state': state, 'project': (root / 'PROJECT.md').read_text(), "
                 "'agents': (root / 'AGENTS.md').read_text(), "
                 "'evidence': (root / state['current_slice']['primary_journey']['evidence']).read_text()}))",
                 str(target)], cwd=installed, capture_output=True, text=True, check=False,
            )
            self.assertEqual(resumed.returncode, 0, resumed.stderr)
            handoff = json.loads(resumed.stdout)
            self.assertEqual(handoff["state"]["next_action"], next_action)
            self.assertEqual(handoff["state"]["current_slice"]["primary_journey"]["status"], "failed")
            self.assertIn("title.txt", handoff["evidence"])
            self.assertIn("after restarting", handoff["project"])
            self.assertIn("The owner decides", handoff["agents"])

            # Remove the incomplete packaging filter and retry the unchanged journey.
            zipapp.create_archive(product, target=artifact)
            product.rename(target / "source-hidden")
            self.assertEqual({p.name for p in installed.iterdir()}, {"notes.pyz"})
            saved = launch(artifact, "add", "Remember this")
            self.assertEqual(saved.returncode, 0, saved.stderr)
            restarted = launch(artifact, "show")
            self.assertEqual(restarted.returncode, 0, restarted.stderr)
            self.assertEqual(restarted.stdout.strip(), "Saved note: Remember this")
            (summary_path.parent / "recovery.txt").write_text(restarted.stdout)
            state = state_path.read_text().replace("status: implemented", "status: validated", 1)
            state = state.replace("status: failed", "status: passed", 1).replace("primary_journey: failed", "primary_journey: passed")
            state = state.replace(json.dumps(next_action), json.dumps("Ask the human to review the saved-note result."))
            state_path.write_text(state)
            summary_path.write_text(summary_path.read_text().replace(
                f"- Result: failed\n- Exit code: {failed.returncode}", "- Result: passed\n- Exit code: 0"
            ).replace(
                "- Source launcher: passed; packaged launcher: failed.", "- Source launcher: passed."
            ).replace(
                "- attempt-1.txt: missing packaged title.txt.",
                "- attempt-1.txt: original missing resource failure.\n- recovery.txt: saved note read by a new process."
            ))
            gate = run_gate(target)
            self.assertEqual(gate.returncode, 0, gate.stdout + gate.stderr)
            self.assertIn("human_acceptance: pending", state_path.read_text())
            for filename in ("PROJECT.md", "STATE.yaml", "AGENTS.md", "evidence", "scripts"):
                (target / filename).rename(target / ("hidden-" + filename))
            self.assertEqual(launch(artifact, "show").stdout.strip(), "Saved note: Remember this")
            print("\nPackaged journey: source passed; clean archive failed; fresh-process handoff recovered; "
                  "restart and runtime independence passed; human acceptance pending.", flush=True)

    def test_undefined_contract_or_journey_cannot_validate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "core"
            self.assertEqual(run_init(target).returncode, 0)
            scaffold_project = (target / "PROJECT.md").read_text()
            record_passing_fixture(target)
            project_path = target / "PROJECT.md"
            state_path = target / "STATE.yaml"
            project = project_path.read_text()
            state = state_path.read_text()
            summary_path = target / "evidence/bootstrap-001/summary.md"
            summary = summary_path.read_text()
            for field in ("User", "Outcome", "Scope", "Non-goals", "Durable constraints"):
                for placeholder in ("Not yet defined — confirm with the human.", "TODO", "TBD", "<!-- pending -->"):
                    with self.subTest(field=field, placeholder=placeholder):
                        before, body = project.split(f"## {field}\n\n", 1)
                        _, separator, after = body.partition("\n## ")
                        project_path.write_text(before + f"## {field}\n\n{placeholder}\n" + separator + after)
                        self.assertNotEqual(run_gate(target).returncode, 0)
            project_path.write_text(scaffold_project)
            self.assertIn("unresolved", run_gate(target).stdout)
            project_path.write_text(project)
            for field, valid in (("description", "Run the documented local workflow end to end."),
                                 ("command", "python3 -m unittest"),
                                 ("environment", "clean local test fixture")):
                with self.subTest(field=field):
                    state_path.write_text(state.replace(f'{field}: "{valid}"', f'{field}: "TBD"'))
                    summary_path.write_text(summary.replace(valid, "TBD"))
                    gate = run_gate(target)
                    self.assertEqual(gate.returncode, 1, gate.stdout + gate.stderr)
                    self.assertIn("unresolved", gate.stdout)
            summary_path.write_text(summary)
            for valid in ("Define and prove the first real user journey.",
                          "The documented primary journey succeeds in a representative environment."):
                state_path.write_text(state.replace(valid, "TODO: define with the human"))
                self.assertEqual(run_gate(target).returncode, 1)
            state_path.write_text(state)
            project_path.write_text(project.replace("A student using the local application.", "Todo app users."))
            self.assertEqual(run_gate(target).returncode, 0)

    def test_reachable_risk_cannot_escape_by_category(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "core"
            self.assertEqual(run_init(target).returncode, 0)
            record_passing_fixture(target)
            state_path = target / "STATE.yaml"
            state = state_path.read_text()
            for category in ("security", "security_vulnerability", "vulnerability", "availability", "unrecognized"):
                for severity, exposure, decision, expected in (
                    ("critical", "reachable", "defer", 1),
                    ("high", "unknown", "mitigate", 1),
                    ("medium", "reachable", "defer", 0),
                    ("high", "build_only", "defer", 0),
                    ("critical", "unreachable", "defer", 0),
                    ("high", "reachable", "resolved", 0),
                ):
                    with self.subTest(category=category, severity=severity, exposure=exposure, decision=decision):
                        risk = (
                            f"risks:\n  - id: finding\n    category: {category}\n    severity: {severity}\n"
                            f"    exposure: {exposure}\n    affected_environment: shipped product\n"
                            f"    consequence: service unavailable\n    owner: maintainer\n"
                            f"    decision: {decision}\n    expires: null"
                        )
                        state_path.write_text(state.replace("risks: []", risk))
                        gate = run_gate(target)
                        self.assertEqual(gate.returncode, expected, gate.stdout + gate.stderr)

    def test_mandatory_risks_need_bounded_unexpired_exceptions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "core"
            self.assertEqual(run_init(target).returncode, 0)
            record_passing_fixture(target)
            state_path = target / "STATE.yaml"
            state = state_path.read_text()
            tomorrow = (dt.date.today() + dt.timedelta(days=1)).isoformat()
            yesterday = (dt.date.today() - dt.timedelta(days=1)).isoformat()
            for category in ("data_loss", "data_corruption", "destructive_operation", "privilege_escalation",
                             "secrets_exposure", "private_data_exposure", "permission_boundary"):
                base = (
                    f"risks:\n  - id: finding\n    category: {category}\n    severity: low\n"
                    "    exposure: local_only\n    affected_environment: test fixture\n"
                    "    consequence: user data affected\n    owner: maintainer\n"
                )
                for decision, exception, expected in (
                    ("defer", "    expires: null", 1),
                    ("accept_temporarily", "    expires: null", 2),
                    ("accept_temporarily", f"    approval: Test human\n    rationale: Disposable fixture\n    expires: {tomorrow}", 0),
                    ("accept_temporarily", f"    approval: Test human\n    rationale: Disposable fixture\n    expires: {yesterday}", 2),
                ):
                    with self.subTest(category=category, decision=decision, exception=exception):
                        state_path.write_text(state.replace("risks: []", base + f"    decision: {decision}\n" + exception))
                        gate = run_gate(target)
                        self.assertEqual(gate.returncode, expected, gate.stdout + gate.stderr)

    def test_human_rejection_and_blocked_slice_prevent_closure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "core"
            self.assertEqual(run_init(target).returncode, 0)
            record_passing_fixture(target)
            state_path = target / "STATE.yaml"
            state = state_path.read_text()
            for before, after in (("human_acceptance: pending", "human_acceptance: rejected"),
                                  ("status: validated", "status: blocked")):
                state_path.write_text(state.replace(before, after, 1))
                self.assertEqual(run_gate(target).returncode, 1)

    def test_state_stays_a_current_view_not_a_journal(self) -> None:
        # Measured 2026-09-27: an adopter's blockers became a 329-entry, 1 MB journal of resolved work.
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "core"
            self.assertEqual(run_init(target).returncode, 0)
            record_passing_fixture(target)
            state_path = target / "STATE.yaml"
            state = state_path.read_text()
            self.assertEqual(run_gate(target).returncode, 0)

            state_path.write_text(state.replace(
                "blockers: []", 'blockers:\n  - "RESOLVED 2026-09-27: the flaky fixture was pinned."', 1))
            result = run_gate(target)
            self.assertEqual(result.returncode, 2)
            self.assertIn("resolved work", result.stdout)

            many = "".join(f'\n  - "Open item {i}."' for i in range(13))
            state_path.write_text(state.replace("blockers: []", "blockers:" + many, 1))
            result = run_gate(target)
            self.assertEqual(result.returncode, 2)
            self.assertIn("13 entries", result.stdout)

            state_path.write_text(state.replace("blockers: []", 'blockers:\n  - "' + "x" * 700 + '"', 1))
            result = run_gate(target)
            self.assertEqual(result.returncode, 1)
            self.assertIn("WARN: blockers[0] is 700 chars", result.stdout)

            state_path.write_text(state + "# " + "y" * (64 * 1024) + "\n")
            result = run_gate(target)
            self.assertEqual(result.returncode, 2)
            self.assertIn("current-state view", result.stdout)

    def test_secondary_evidence_cannot_supply_a_primary_result(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "core"
            self.assertEqual(run_init(target).returncode, 0)
            record_passing_fixture(target)
            summary_path = target / "evidence/bootstrap-001/summary.md"
            summary = summary_path.read_text()
            for invalid in (
                summary.replace("## Primary journey", "## Secondary checks", 1).replace("## Secondary checks", "## Primary journey\n\n## Secondary checks", 1),
                summary.replace("- Result: passed", "- Result: passed\n- Result: failed"),
                summary.replace("## Secondary checks", "## Primary journey\n\n- Result: failed\n\n## Secondary checks"),
            ):
                with self.subTest(summary=invalid):
                    summary_path.write_text(invalid)
                    self.assertEqual(run_gate(target).returncode, 2)

    def test_invalid_status_types_and_delivery_statuses_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "core"
            self.assertEqual(run_init(target).returncode, 0)
            record_passing_fixture(target)
            state_path = target / "STATE.yaml"
            state = state_path.read_text()
            for before, values in (
                ("profile: core", ("[]", "{}")),
                ("status: validated", ("[]", "{}")),
                ("status: passed", ("[]", "{}", "publicly_verified", "deployed")),
                ("primary_journey: passed", ("[]", "{}")),
                ("automated_tests: passed", ("[]", "{}")),
                ("human_acceptance: pending", ("[]", "{}")),
            ):
                key = before.split(":", 1)[0]
                for value in values:
                    with self.subTest(key=key, value=value):
                        state_path.write_text(state.replace(before, f"{key}: {value}", 1))
                        gate = run_gate(target)
                        self.assertEqual(gate.returncode, 2, gate.stdout + gate.stderr)
                        self.assertNotIn("Traceback", gate.stderr)

    def test_gate_rejects_symlinked_inputs_without_reading_them(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "core"
            self.assertEqual(run_init(target, profile="hardened").returncode, 0)
            record_passing_fixture(target)
            for name in ("STATE.yaml", "PROJECT.md", "AGENTS.md", "HARDENED_POLICY.md", "evidence/bootstrap-001/summary.md"):
                with self.subTest(name=name):
                    path = target / name
                    content = path.read_text()
                    outside = Path(tmp) / "external"
                    outside.write_text(content)
                    path.unlink()
                    path.symlink_to(outside)
                    gate = run_gate(target)
                    self.assertEqual(gate.returncode, 2, gate.stdout + gate.stderr)
                    self.assertIn("symlink", gate.stdout)
                    path.unlink()
                    path.write_text(content)
            evidence = target / "evidence"
            moved = target / "moved-evidence"
            evidence.rename(moved)
            evidence.symlink_to(moved, target_is_directory=True)
            self.assertEqual(run_gate(target).returncode, 2)

    def test_passing_secondary_tests_cannot_override_failed_journey(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "core"
            self.assertEqual(run_init(target).returncode, 0)
            record_passing_fixture(target)
            state_path = target / "STATE.yaml"
            state = state_path.read_text(encoding="utf-8")
            state = state.replace("status: passed", "status: failed", 1)
            state = state.replace("primary_journey: passed", "primary_journey: failed")
            state_path.write_text(state, encoding="utf-8")
            gate = run_gate(target)
            self.assertNotEqual(gate.returncode, 0, gate.stdout + gate.stderr)
            self.assertIn("secondary checks cannot override", gate.stdout)
            self.assertIn("automated_tests: passed", state)

    def test_two_failures_require_simplification_review(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "core"
            self.assertEqual(run_init(target).returncode, 0)
            record_passing_fixture(target)
            state_path = target / "STATE.yaml"
            state = state_path.read_text(encoding="utf-8").replace(
                "  failed_attempts: []",
                "  failed_attempts:\n"
                "    - evidence: evidence/bootstrap-001/attempt-1.txt\n"
                "      cause: launcher import failed\n"
                "    - evidence: evidence/bootstrap-001/attempt-2.txt\n"
                "      cause: packaging repair still failed",
            )
            evidence = target / "evidence" / "bootstrap-001"
            (evidence / "attempt-1.txt").write_text("launcher import failed\n", encoding="utf-8")
            (evidence / "attempt-2.txt").write_text("packaging repair failed\n", encoding="utf-8")
            state_path.write_text(state, encoding="utf-8")
            gate = run_gate(target)
            self.assertEqual(gate.returncode, 1, gate.stdout + gate.stderr)
            self.assertIn("require simplification", gate.stdout)
            state_path.write_text(
                state_path.read_text(encoding="utf-8").replace(
                    "  simplification_review: null",
                    "  simplification_review:\n"
                    "    assumption_reconsidered: package installation must wrap the local service\n"
                    "    complexity_removed: bypassed the package repository\n"
                    "    smallest_rerun: run the documented local launcher",
                ),
                encoding="utf-8",
            )
            self.assertEqual(run_gate(target).returncode, 0)

    def test_risk_gate_is_exposure_aware(self) -> None:
        risk = (
            "risks:\n"
            "  - id: browser-build-cve\n"
            "    category: security_vulnerability\n"
            "    severity: high\n"
            "    exposure: build_only\n"
            "    affected_environment: image build tooling\n"
            "    consequence: vulnerable browser package exists only in the builder\n"
            "    owner: maintainer\n"
            "    decision: defer\n"
            "    expires: null"
        )
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "core"
            self.assertEqual(run_init(target).returncode, 0)
            record_passing_fixture(target)
            state_path = target / "STATE.yaml"
            state_path.write_text(
                state_path.read_text(encoding="utf-8").replace("risks: []", risk),
                encoding="utf-8",
            )
            build_only = run_gate(target)
            self.assertEqual(build_only.returncode, 0, build_only.stdout + build_only.stderr)
            state_path.write_text(
                state_path.read_text(encoding="utf-8").replace("exposure: build_only", "exposure: reachable"),
                encoding="utf-8",
            )
            reachable = run_gate(target)
            self.assertEqual(reachable.returncode, 1, reachable.stdout + reachable.stderr)
            self.assertIn("mandatory stop-line", reachable.stdout)

    def test_hardened_overlay_is_explicit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            core = root / "core"
            hardened = root / "hardened"
            self.assertEqual(run_init(core).returncode, 0)
            self.assertEqual(run_init(hardened, profile="hardened").returncode, 0)
            self.assertFalse((core / "HARDENED_POLICY.md").exists())
            self.assertTrue((hardened / "HARDENED_POLICY.md").is_file())
            self.assertIn("profile: hardened", (hardened / "STATE.yaml").read_text(encoding="utf-8"))
            hardened_files = {
                path.relative_to(hardened).as_posix()
                for path in hardened.rglob("*")
                if path.is_file()
            }
            self.assertFalse(hardened_files & LEGACY_TRUTH_FILES)
            self.assertEqual(hardened_files - {"HARDENED_POLICY.md"}, {
                path.relative_to(core).as_posix() for path in core.rglob("*") if path.is_file()
            })

    def test_state_cannot_expand_itself_with_governance_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "core"
            self.assertEqual(run_init(target).returncode, 0)
            record_passing_fixture(target)
            state_path = target / "STATE.yaml"
            state_path.write_text(
                state_path.read_text(encoding="utf-8")
                + "governance:\n  agent_may_change_acceptance: true\n",
                encoding="utf-8",
            )
            gate = run_gate(target)
            self.assertEqual(gate.returncode, 2, gate.stdout + gate.stderr)
            self.assertIn("unsupported fields ['governance']", gate.stdout)

    def test_accepted_status_requires_explicit_human_acceptance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "core"
            self.assertEqual(run_init(target).returncode, 0)
            record_passing_fixture(target)
            state_path = target / "STATE.yaml"
            state_path.write_text(
                state_path.read_text(encoding="utf-8").replace("status: validated", "status: accepted", 1),
                encoding="utf-8",
            )
            gate = run_gate(target)
            self.assertEqual(gate.returncode, 2, gate.stdout + gate.stderr)
            self.assertIn("requires explicit human acceptance", gate.stdout)

    def test_gate_never_executes_the_recorded_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "core"
            marker = Path(tmp) / "must-not-exist"
            self.assertEqual(run_init(target).returncode, 0)
            state_path = target / "STATE.yaml"
            state = state_path.read_text(encoding="utf-8").replace(
                'command: "Not yet defined — record the exact human-authorized command."',
                f'command: "touch {marker}"',
            )
            state_path.write_text(state, encoding="utf-8")
            self.assertEqual(run_gate(target).returncode, 1)
            self.assertFalse(marker.exists())

    def test_core_adoption_rejects_symlinked_evidence_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "adopt"
            outside = root / "outside"
            target.mkdir()
            outside.mkdir()
            (target / "README.md").write_text("# Existing\n", encoding="utf-8")
            os.symlink(outside, target / "evidence")
            completed = run_init(target, adopt=True)
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("symlink", (completed.stdout + completed.stderr).lower())
            self.assertEqual(list(outside.iterdir()), [])

    def test_adoption_preserves_product_readme_and_avoids_legacy_truth(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "adopt"
            target.mkdir()
            original = "# Existing product\n\nRun it with `make start`.\n"
            (target / "README.md").write_text(original, encoding="utf-8")
            completed = run_init(target, adopt=True)
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            self.assertEqual((target / "README.md").read_text(encoding="utf-8"), original)
            self.assertTrue((target / "STATE.yaml").is_file())
            for path in LEGACY_TRUTH_FILES:
                self.assertFalse((target / path).exists(), path)

    def test_adoption_dry_run_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "adopt"
            target.mkdir()
            original = "# Existing product\n"
            (target / "README.md").write_text(original, encoding="utf-8")
            completed = subprocess.run(
                [
                    sys.executable,
                    str(INIT),
                    "adopt",
                    "--name",
                    "Outcome Demo",
                    "--target",
                    str(target),
                    "--dry-run",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            self.assertEqual((target / "README.md").read_text(encoding="utf-8"), original)
            self.assertEqual(
                {path.relative_to(target).as_posix() for path in target.rglob("*") if path.is_file()},
                {"README.md"},
            )


if __name__ == "__main__":
    unittest.main()
