#!/usr/bin/env python3
"""
StateDD Remote Truth Check

Hard gate: No closure claim without proving remote GitHub state matches local claims.
Truth boundaries: sandbox → local worktree → git index → local commit → remote branch → GitHub main → CI → user-accepted
No transition crosses a boundary without proof.
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
        self.closure_label = "NOT CLOSURE-GRADE — LOCAL OR UNVERIFIED CLAIM"
        self.upstream_ref = ""
        self.upstream_head = ""
        self.remote_head = ""

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
        self.boundaries.clear()
        self.failures.clear()
        self.warnings.clear()
        self.closure_label = "NOT CLOSURE-GRADE — LOCAL OR UNVERIFIED CLAIM"
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
        if b2.passed and not b2.actual.strip():
            b2.passed = False
            self.failures.append("Boundary 'git_remote' failed: no remotes configured")
        self.boundaries.append(b2)

        # Boundary 3: Current branch
        b3 = TruthBoundary("current_branch", ["git", "branch", "--show-current"], evidence="git branch --show-current")
        self.check_boundary(b3)
        if b3.passed and not b3.actual.strip():
            b3.passed = False
            self.failures.append("Boundary 'current_branch' failed: detached HEAD or empty branch")
        self.boundaries.append(b3)

        # Boundary 4: Git status. Porcelain output is a semantic set of index,
        # worktree, and untracked changes; any entry makes closure dirty.
        status_cmd = ["git", "status", "--porcelain=v1", "--untracked-files=all"]
        code, out, err = self.run_cmd(status_cmd)
        b4 = TruthBoundary("worktree_clean", status_cmd, actual=out, evidence="git status --porcelain=v1 --untracked-files=all")
        b4.passed = code == 0 and not out.strip()
        if code != 0:
            self.failures.append(f"Boundary 'worktree_clean' failed: {err or 'git status failed'}")
        elif out.strip():
            self.failures.append(f"Boundary 'worktree_clean' failed: worktree is dirty:\n{out}")
        self.boundaries.append(b4)

        # Boundary 5: Git log (recent commits)
        b5 = TruthBoundary("git_log", ["git", "log", "--oneline", "-8"], evidence="git log --oneline -8")
        self.check_boundary(b5)
        self.boundaries.append(b5)

        # Boundary 6: HEAD commit SHA
        b6 = TruthBoundary("head_sha", ["git", "rev-parse", "HEAD"], evidence="git rev-parse HEAD")
        self.check_boundary(b6)
        if b6.passed and not re.fullmatch(r"[0-9a-fA-F]{40}", b6.actual):
            b6.passed = False
            self.failures.append(f"Boundary 'head_sha' failed: expected a full 40-character commit SHA, got '{b6.actual}'")
        self.boundaries.append(b6)

        branch = b3.actual.strip() if b3.passed else ""
        local_head = b6.actual.strip().lower() if b6.passed else ""

        # Boundary 7: The branch must have the matching origin upstream, and
        # the local remote-tracking ref must equal local HEAD exactly.
        upstream_cmd = ["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}"]
        code, out, err = self.run_cmd(upstream_cmd)
        self.upstream_ref = out.strip()
        expected_upstream = f"origin/{branch}" if branch else ""
        b7 = TruthBoundary("upstream_ref", upstream_cmd, expected=expected_upstream, actual=self.upstream_ref, evidence="git rev-parse --abbrev-ref --symbolic-full-name @{upstream}")
        b7.passed = code == 0 and bool(expected_upstream) and self.upstream_ref == expected_upstream
        if not b7.passed:
            self.failures.append(
                "Boundary 'upstream_ref' failed: "
                + (err or f"expected '{expected_upstream}', got '{self.upstream_ref or 'missing'}'")
            )
        self.boundaries.append(b7)

        upstream_head_cmd = ["git", "rev-parse", "@{upstream}"]
        code, out, err = self.run_cmd(upstream_head_cmd)
        self.upstream_head = out.strip().lower()
        b8 = TruthBoundary("upstream_head", upstream_head_cmd, expected=local_head, actual=self.upstream_head, evidence="git rev-parse @{upstream}")
        b8.passed = code == 0 and bool(local_head) and self.upstream_head == local_head
        if not b8.passed:
            self.failures.append(
                "Boundary 'upstream_head' failed: "
                + (err or f"upstream SHA {self.upstream_head or 'missing'} != local HEAD {local_head or 'missing'}")
            )
        self.boundaries.append(b8)

        # Boundary 9: The authoritative origin branch must equal both local
        # HEAD and the configured upstream tracking ref.
        remote_cmd = ["git", "ls-remote", "--heads", "origin", f"refs/heads/{branch}"]
        code, out, err = self.run_cmd(remote_cmd)
        remote_lines = [line.split("\t", 1) for line in out.splitlines() if "\t" in line]
        matching = [parts[0].lower() for parts in remote_lines if parts[1] == f"refs/heads/{branch}"]
        self.remote_head = matching[0] if len(matching) == 1 else ""
        b9 = TruthBoundary("remote_head", remote_cmd, expected=local_head, actual=out, evidence=f"git ls-remote --heads origin refs/heads/{branch}")
        b9.passed = code == 0 and len(matching) == 1 and self.remote_head == local_head == self.upstream_head
        if not b9.passed:
            detail = err or (
                f"remote SHA {self.remote_head or 'missing/ambiguous'} != "
                f"local HEAD {local_head or 'missing'} and upstream {self.upstream_head or 'missing'}"
            )
            self.failures.append(f"Boundary 'remote_head' failed: {detail}")
        self.boundaries.append(b9)

        # Boundary 10: Claimed files are tracked.
        if self.claimed_files:
            claimed_ok = True
            for f in self.claimed_files:
                code, _, err = self.run_cmd(["git", "ls-files", "--error-unmatch", "--", f])
                if code != 0:
                    claimed_ok = False
                    self.failures.append(f"Claimed file not tracked: {f}")
            b10 = TruthBoundary(
                "claimed_files_tracked",
                ["git", "ls-files", "--error-unmatch", "--", *self.claimed_files],
                passed=claimed_ok,
                evidence="git ls-files --error-unmatch -- <claimed files>",
            )
            self.boundaries.append(b10)

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
            # This gate proves Git remote equality, not PR/CI truth. Only the
            # remote closure finalizer may issue a CI-verified label.
            self.closure_label = "pushed"

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
            "upstream_ref": self.upstream_ref,
            "upstream_head": self.upstream_head,
            "remote_head": self.remote_head,
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
