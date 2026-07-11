#!/usr/bin/env python3
"""Prove clean local-commit parity with the configured remote branch.

This is a remote-branch preflight, not a closure gate. It deliberately does not
inspect a pull request, GitHub-visible file contents, CI, merge state, runtime,
or human acceptance. ``statedd_remote_closure_finalizer.py`` owns those checks.
"""

import argparse
import json
import re
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
        self.closure_label = "local-only"

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

        # Boundary 1: Repo identity. `pwd` can succeed outside a repository, so
        # prove the Git top-level is the requested root.
        b1 = TruthBoundary(
            "repo_identity",
            ["git", "rev-parse", "--show-toplevel"],
            expected=str(self.root.resolve()),
            evidence="git rev-parse --show-toplevel",
        )
        self.check_boundary(b1)
        self.boundaries.append(b1)

        # Boundary 2: Git remote
        b2 = TruthBoundary("git_remote", ["git", "remote", "get-url", "origin"], evidence="git remote get-url origin")
        self.check_boundary(b2)
        if b2.passed and not b2.actual:
            b2.passed = False
            self.failures.append("Boundary 'git_remote' failed: origin URL is empty")
        self.boundaries.append(b2)

        # Boundary 3: Current branch
        b3 = TruthBoundary("current_branch", ["git", "branch", "--show-current"], evidence="git branch --show-current")
        self.check_boundary(b3)
        if b3.passed and not b3.actual:
            b3.passed = False
            self.failures.append("Boundary 'current_branch' failed: detached HEAD")
        self.boundaries.append(b3)

        # Boundary 4: Git status (tracked files)
        b4 = TruthBoundary("git_status", ["git", "status", "--short"], evidence="git status --short")
        self.check_boundary(b4)
        if b4.passed and b4.actual:
            b4.passed = False
            self.failures.append("Boundary 'git_status' failed: worktree is dirty")
        self.boundaries.append(b4)

        # Boundary 5: Git log (recent commits)
        b5 = TruthBoundary("git_log", ["git", "log", "--oneline", "-8"], evidence="git log --oneline -8")
        self.check_boundary(b5)
        self.boundaries.append(b5)

        # Boundary 6: HEAD commit SHA
        b6 = TruthBoundary("head_sha", ["git", "rev-parse", "HEAD"], evidence="git rev-parse HEAD")
        self.check_boundary(b6)
        if b6.passed and not re.fullmatch(r"[0-9a-f]{40}", b6.actual):
            b6.passed = False
            self.failures.append("Boundary 'head_sha' failed: expected a full commit SHA")
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
            b7.actual = remote_sha
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

        # Determine remote branch state. This label intentionally stops at the
        # pushed truth boundary and never implies PR, CI, or closure proof.
        if not self.failures:
            self.closure_label = "pushed"

        print(f"\nRemote Branch State: {self.closure_label}")
        print("PR, CI, merge state, and closure evidence: not checked")
        print("=" * 60)

        if self.failures:
            print(f"❌ REMOTE BRANCH PREFLIGHT FAILED — {self.closure_label}")
            return 1

        print(f"✅ REMOTE BRANCH PREFLIGHT PASSED — {self.closure_label}")
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
