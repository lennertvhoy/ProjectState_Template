#!/usr/bin/env python3
"""
StateSpec Probe Guidance

Runs synthetic tasks to probe agent guidance completeness.
Creates fake issues/tasks and checks if agent follows correct workflow.
"""

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum


class ProbeType(Enum):
    FIX_STALE_TEST = "fix_stale_test"
    CLOSE_SLICE = "close_slice"
    INGEST_BAD_EVENT = "ingest_bad_event"
    MIGRATE_STATE = "migrate_state"
    FAILURE_SCAN = "failure_scan"
    RUNTIME_PROOF = "runtime_proof"


@dataclass
class ProbeTask:
    type: ProbeType
    description: str
    expected_skills: List[str]
    expected_commands: List[str]
    expected_gates: List[str]
    setup: str  # shell command to set up the scenario
    verify: str  # shell command to verify completion


# Probe scenarios
PROBES = [
    ProbeTask(
        type=ProbeType.FIX_STALE_TEST,
        description="A test is failing due to a stale selector; fix it and close the slice",
        expected_skills=["failure-scan", "quality-gate", "close-slice"],
        expected_commands=["statedd-failure-scan", "statedd-quality-freeze", "statedd-close-slice"],
        expected_gates=["statedd_quality_gate.py", "statedd_closure_check.py", "statedd_instruction_lint.py"],
        setup="echo 'def test_broken():\n    assert False, \"stale selector\"' > test_stale.py",
        verify="python -m pytest test_stale.py -v"
    ),
    ProbeTask(
        type=ProbeType.CLOSE_SLICE,
        description="Complete a slice and verify all quality gates pass",
        expected_skills=["quality-gate", "close-slice"],
        expected_commands=["statedd-close-slice"],
        expected_gates=["statedd_quality_gate.py", "statedd_closure_check.py", "statedd_runtime_truth_check.py", "statedd_evidence_type_check.py"],
        setup="echo '# New feature\nprint(\"hello\")' > feature.py",
        verify="python scripts/statedd_quality_gate.py"
    ),
    ProbeTask(
        type=ProbeType.INGEST_BAD_EVENT,
        description="Record a bad event (test crash) and create incident",
        expected_skills=["ingest-bad-event", "failure-scan"],
        expected_commands=["statedd-ingest-bad-event", "statedd-failure-scan"],
        expected_gates=["statedd_failure_scan_check.py"],
        setup="mkdir -p docs/ng logs && echo 'ERROR: Connection refused' > logs/app.log",
        verify="ls docs/incidents/"
    ),
    ProbeTask(
        type=ProbeType.MIGRATE_STATE,
        description="Migrate PROJECT_STATE.yaml to new schema version",
        expected_skills=["quality-gate"],
        expected_commands=["statedd-close-slice"],
        expected_gates=["statedd_validate_schema.py", "statedd_instruction_lint.py"],
        setup="cp PROJECT_STATE.yaml PROJECT_STATE.yaml.bak",
        verify="python scripts/statedd_validate_schema.py"
    ),
    ProbeTask(
        type=ProbeType.FAILURE_SCAN,
        description="Run failure scan before risky refactor",
        expected_skills=["failure-scan"],
        expected_commands=["statedd-failure-scan"],
        expected_gates=[],
        setup="echo 'refactor: change core auth' > REFACTOR_NOTE.md",
        verify="ls docs/failure_scans/"
    ),
    ProbeTask(
        type=ProbeType.RUNTIME_PROOF,
        description="Capture and verify runtime identity",
        expected_skills=["runtime-truth"],
        expected_commands=[],
        expected_gates=["statedd_runtime_truth_check.py"],
        setup="",
        verify="python scripts/statedd_runtime_truth_check.py"
    ),
]


class ProbeGuidance:
    def __init__(self, root: Path, verbose: bool = False):
        self.original_root = root
        self.verbose = verbose
        self.results: List[Dict[str, Any]] = []
        self._temp_dir = tempfile.TemporaryDirectory(prefix="statedd_probe_")
        self.root = Path(self._temp_dir.name) / "repo"
        # Copy the repo into an isolated temporary workspace so probes cannot
        # pollute or overwrite the original repository.
        shutil.copytree(
            root,
            self.root,
            symlinks=False,
            ignore=shutil.ignore_patterns(".git", "__pycache__", ".pytest_cache"),
        )
        # Preserve git metadata by re-initializing a fresh repo in the copy.
        # Probes rely on the file tree, not the commit history.
        self.run_cmd(
            "git init -b main && "
            "git config user.email 'probe@example.invalid' && "
            "git config user.name 'Probe' && "
            "git add . && "
            "git commit -m 'probe baseline'"
        )

    def run_cmd(self, cmd: str, cwd: Path = None) -> Tuple[int, str, str]:
        """Run shell command."""
        try:
            result = subprocess.run(
                cmd, shell=True, cwd=cwd or self.root,
                capture_output=True, text=True, timeout=60
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return -1, "", "timeout"
        except Exception as e:
            return -1, "", str(e)

    def check_skill_loadable(self, skill_name: str) -> bool:
        """Check if skill can be loaded (file exists and valid)."""
        skill_path = self.root / "skills" / skill_name / "SKILL.md"
        return skill_path.exists()

    def check_command_exists(self, command_name: str) -> bool:
        """Check if command file exists."""
        cmd_path = self.root / "commands" / f"{command_name}.md"
        return cmd_path.exists()

    def check_gate_exists(self, gate_name: str) -> bool:
        """Check if gate script exists."""
        gate_path = self.root / "scripts" / gate_name
        return gate_path.exists()

    def run_probe(self, probe: ProbeTask) -> Dict[str, Any]:
        """Run a single probe task."""
        print(f"\n🔬 Probe: {probe.type.value}")
        print(f"   {probe.description}")

        result = {
            "probe": probe.type.value,
            "description": probe.description,
            "skills_found": [],
            "skills_missing": [],
            "commands_found": [],
            "commands_missing": [],
            "gates_found": [],
            "gates_missing": [],
            "setup_ok": False,
            "verify_ok": False,
            "passed": False,
        }

        # Check expected skills
        for skill in probe.expected_skills:
            if self.check_skill_loadable(skill):
                result["skills_found"].append(skill)
            else:
                result["skills_missing"].append(skill)

        # Check expected commands
        for cmd in probe.expected_commands:
            if self.check_command_exists(cmd):
                result["commands_found"].append(cmd)
            else:
                result["commands_missing"].append(cmd)

        # Check expected gates
        for gate in probe.expected_gates:
            if self.check_gate_exists(gate):
                result["gates_found"].append(gate)
            else:
                result["gates_missing"].append(gate)

        # Run setup
        if probe.setup:
            code, out, err = self.run_cmd(probe.setup)
            result["setup_ok"] = code == 0
            if not result["setup_ok"]:
                result["setup_error"] = err or out

        # Run verification
        if probe.verify:
            code, out, err = self.run_cmd(probe.verify)
            result["verify_ok"] = code == 0
            if not result["verify_ok"]:
                result["verify_error"] = err or out

        # Overall pass: all expected skills/commands/gates exist
        result["passed"] = (
            len(result["skills_missing"]) == 0 and
            len(result["commands_missing"]) == 0 and
            len(result["gates_missing"]) == 0 and
            result["setup_ok"] and
            result["verify_ok"]
        )

        status = "✅ PASS" if result["passed"] else "❌ FAIL"
        print(f"   {status}")
        if result["skills_missing"]:
            print(f"   Missing skills: {result['skills_missing']}")
        if result["commands_missing"]:
            print(f"   Missing commands: {result['commands_missing']}")
        if result["gates_missing"]:
            print(f"   Missing gates: {result['gates_missing']}")
        if not result["setup_ok"]:
            print(f"   Setup failed: {result.get('setup_error', 'unknown')}")
        if not result["verify_ok"]:
            print(f"   Verify failed: {result.get('verify_error', 'unknown')}")

        return result

    def run_all(self) -> Tuple[int, List[Dict]]:
        """Run all probes."""
        print("=" * 50)
        print("StateSpec Probe Guidance")
        print("=" * 50)

        for probe in PROBES:
            result = self.run_probe(probe)
            self.results.append(result)

        passed = sum(1 for r in self.results if r["passed"])
        total = len(self.results)

        print("\n" + "=" * 50)
        print(f"Results: {passed}/{total} probes passed")
        print("=" * 50)

        for r in self.results:
            status = "✅" if r["passed"] else "❌"
            print(f"  {status} {r['probe']}")

        if passed == total:
            print("\n✅ ALL PROBES PASSED - Guidance is complete")
            return 0, self.results
        else:
            print(f"\n❌ {total - passed} PROBE(S) FAILED - Guidance gaps detected")
            return 1, self.results


def main():
    parser = argparse.ArgumentParser(description="StateSpec Probe Guidance")
    parser.add_argument("--root", default=".", help="Repository root")
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--json", action="store_true", help="Output JSON results")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    probe = ProbeGuidance(root, args.verbose)
    exit_code, results = probe.run_all()

    if args.json:
        print(json.dumps(results, indent=2))

    sys.exit(exit_code)


if __name__ == "__main__":
    main()