#!/usr/bin/env python3
"""Regression tests for the outcome-first ProjectState core."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INIT = ROOT / "scripts" / "init_template.py"
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


def make_core_valid(target: Path) -> None:
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
            self.assertIn("The human owns", agents)
            self.assertIn("primary journey", agents)
            self.assertIn("Two evidenced failures", agents)
            self.assertIn("must never import", agents)
            gate = run_gate(target)
            self.assertEqual(gate.returncode, 1, gate.stdout + gate.stderr)
            self.assertIn("primary journey is not_run", gate.stdout)

    def test_real_journey_can_validate_core(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "core"
            self.assertEqual(run_init(target).returncode, 0)
            make_core_valid(target)
            gate = run_gate(target)
            self.assertEqual(gate.returncode, 0, gate.stdout + gate.stderr)
            self.assertIn("OUTCOME VALIDATED", gate.stdout)

    def test_passing_secondary_tests_cannot_override_failed_journey(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "core"
            self.assertEqual(run_init(target).returncode, 0)
            make_core_valid(target)
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
            make_core_valid(target)
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
            make_core_valid(target)
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
            make_core_valid(target)
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
            make_core_valid(target)
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
