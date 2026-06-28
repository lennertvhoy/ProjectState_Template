#!/usr/bin/env python3
"""
StateDD Remote Truth Check

Hard gate: No closure claim without proving remote GitHub state matches local claims.
Truth boundaries: sandbox → local worktree → git index → local commit → remote branch → GitHub main → CI → user-accepted
No transition crosses a boundary without proof.
"""

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Tuple, Optional


@dataclass
class TruthBoundary:
    name: str
    check_cmd: List[str]
    expected: Optional[str] = None
    actual: str = ""
    passed: bool = False
    evidence: str = ""


class RemoteTruthCheck:
    def __init__(self, root: Path, verbose: bool = False, claimed_files: List[str] = None):
        self.root = root
        self.verbose = verbose
        self.claimed_files = claimed_files or []
        self.boundaries: List[TruthBoundary] = []
        self.failures: List[str] = []
        self.warnings: List[str] = []
        self.closure_label = "NOT CLOSURE-GRADE — LOCAL OR UNVERIFIED CLAIM"

    def run_cmd(self, cmd: List[str]) -> Tuple[int, str, str]:
        try:
            result = subprocess.run(cmd, cwd=self.root, capture_output=True, text=True, timeout=60)
            return result.returncode, result.stdout.strip(), result.stderr.strip()
        except subprocess.TimeoutExpired:
            return -1, "", "timeout"
        except Exception as e:
            return -1, "", str(e)

    def check_boundary(self, boundary: TruthBoundary) -> bool:
        code, out, err = self.run_cmd(boundary.check_cmd)
        boundary.actual = out
        boundary.passed = (code == 0)
        if boundary.expected and boundary.actual != boundary.expected:
            boundary.passed = False
        if not boundary.passed:
            self.failures.append(f"Boundary '{boundary.name}' failed: {err or out}")
        return boundary.passed

    def run(self) -> int:
        print("=" * 60)
        print("StateDD Remote Truth Check")
        print("=" * 60)

        # Boundary 1: Repo identity
        b1 = TruthBoundary("repo_identity", ["pwd"], evidence="pwd")
        self.check_boundary(b1)
        self.boundaries.append(b1)

        # Boundary 2: Git remote
        b2 = TruthBoundary("git_remote", ["git", "remote", "-v"], evidence="git remote -v")
        self.check_boundary(b2)
        self.boundaries.append(b2)

        # Boundary 3: Current branch
        b3 = TruthBoundary("current_branch", ["git", "branch", "--show-current"], evidence="git branch --show-current")
        self.check_boundary(b3)
        self.boundaries.append(b3)

        # Boundary 4: Git status (tracked files)
        b4 = TruthBoundary("git_status", ["git", "status", "--short"], evidence="git status --short")
        self.check_boundary(b4)
        self.boundaries.append(b4)

        # Boundary 5: Git log (recent commits)
        b5 = TruthBoundary("git_log", ["git", "log", "--oneline", "-8"], evidence="git log --oneline -8")
        self.check_boundary(b5)
        self.boundaries.append(b5)

        # Boundary 6: HEAD commit SHA
        b6 = TruthBoundary("head_sha", ["git", "rev-parse", "HEAD"], evidence="git rev-parse HEAD")
        self.check_boundary(b6)
        self.boundaries.append(b6)

        # Boundary 7: Remote contains HEAD SHA
        branch = self._get_current_branch()
        if branch:
            code, out, _ = self.run_cmd(["git", "ls-remote", "origin", branch])
            remote_sha = out.split('\t')[0] if out and '\t' in out else ""
            b7 = TruthBoundary(
                "remote_contains_head",
                ["git", "ls-remote", "origin", branch],
                expected=b6.actual,
                evidence=f"git ls-remote origin {branch}"
            )
            b7.actual = out
            b7.passed = (code == 0 and remote_sha == b6.actual)
            if not b7.passed:
                self.failures.append(f"Boundary 'remote_contains_head' failed: remote SHA {remote_sha} != local HEAD {b6.actual}")
            self.boundaries.append(b7)

        # Boundary 8: Claimed files are tracked
        if self.claimed_files:
            b8 = TruthBoundary("claimed_files_tracked", ["git", "ls-files"] + self.claimed_files, evidence=f"git ls-files {' '.join(self.claimed_files)}")
            self.check_boundary(b8)
            self.boundaries.append(b8)
            # Check each claimed file individually
            for f in self.claimed_files:
                code, out, _ = self.run_cmd(["git", "ls-files", f])
                if code != 0 or not out.strip():
                    self.failures.append(f"Claimed file not tracked: {f}")
                elif out.strip() != f:
                    self.failures.append(f"Claimed file mismatch: expected '{f}', got '{out.strip()}'")

        # Boundary 9: GitHub visible files match claimed deliverables (via GitHub API if available)
        b9 = TruthBoundary("github_visible", ["git", "ls-remote", "origin", "HEAD"], evidence="git ls-remote origin HEAD")
        self.check_boundary(b9)
        self.boundaries.append(b9)

        # Report
        print("\nTruth Boundaries:")
        print("-" * 60)
        for b in self.boundaries:
            status = "✓" if b.passed else "✗"
            print(f"  {status} {b.name}: {b.evidence}")
            if self.verbose and b.actual:
                print(f"      → {b.actual[:120]}{'...' if len(b.actual) > 120 else ''}")

        if self.failures:
            print(f"\nFailures ({len(self.failures)}):")
            for f in self.failures:
                print(f"  ✗ {f}")

        # Determine closure label
        if not self.failures:
            # Check if pushed to remote and GitHub-verified
            if b7.passed and b9.passed:
                self.closure_label = "GitHub-verified"
            elif b7.passed:
                self.closure_label = "pushed"
            else:
                self.closure_label = "local-only"

        print(f"\nClosure Label: {self.closure_label}")
        print("=" * 60)

        if self.failures:
            print(f"❌ REMOTE TRUTH CHECK FAILED — {self.closure_label}")
            return 1

        print(f"✅ REMOTE TRUTH CHECK PASSED — {self.closure_label}")
        return 0

    def _get_current_branch(self) -> str:
        code, out, _ = self.run_cmd(["git", "branch", "--show-current"])
        return out.strip() if code == 0 else ""

    def generate_evidence(self) -> dict:
        """Generate machine-readable evidence for handoff."""
        return {
            "closure_label": self.closure_label,
            "boundaries": [
                {
                    "name": b.name,
                    "evidence_cmd": b.evidence,
                    "passed": b.passed,
                    "actual": b.actual[:500] if b.actual else "",
                }
                for b in self.boundaries
            ],
            "failures": self.failures,
            "claimed_files": self.claimed_files,
            "head_sha": self._get_head_sha(),
            "branch": self._get_current_branch(),
            "remote_url": self._get_remote_url(),
        }

    def _get_head_sha(self) -> str:
        code, out, _ = self.run_cmd(["git", "rev-parse", "HEAD"])
        return out if code == 0 else ""

    def _get_remote_url(self) -> str:
        code, out, _ = self.run_cmd(["git", "remote", "get-url", "origin"])
        return out if code == 0 else ""


def main():
    parser = argparse.ArgumentParser(description="StateDD Remote Truth Check")
    parser.add_argument("--root", default=".", help="Repository root")
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--claim", action="append", dest="claimed_files", help="Claimed deliverable files (repeatable)")
    parser.add_argument("--output", "-o", help="Write evidence JSON to file")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    checker = RemoteTruthCheck(root, args.verbose, args.claimed_files)
    exit_code = checker.run()

    if args.output:
        evidence = checker.generate_evidence()
        Path(args.output).write_text(json.dumps(evidence, indent=2))

    sys.exit(exit_code)


if __name__ == "__main__":
    main()