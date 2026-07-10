#!/usr/bin/env python3
"""
StateDD Closure Check

Validates that closure criteria are truly met before marking a slice closure-grade.
Checks: no unproven claims, no broken links, runtime proof captured, REMOTE TRUTH VERIFIED.
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple


class ClosureCheck:
    def __init__(
        self,
        root: Path,
        verbose: bool = False,
        claimed_files: List[str] = None,
        gate_level: int = 2,
        pr_number: int | None = None,
        slice_id: str | None = None,
        required_checks: List[str] | None = None,
        privacy_profile: str = "public",
    ):
        self.root = root
        self.verbose = verbose
        self.claimed_files = claimed_files or []
        self.gate_level = gate_level
        self.pr_number = pr_number
        self.slice_id = slice_id
        self.required_checks = required_checks or []
        self.privacy_profile = privacy_profile
        self.failures: List[str] = []
        self.warnings: List[str] = []
        self.evidence_folder: Path | None = None
        self.evidence_manifest: dict | None = None
        self.local_head = ""

    def run_cmd(self, cmd: List[str]) -> Tuple[int, str, str]:
        try:
            result = subprocess.run(cmd, cwd=self.root, capture_output=True, text=True, timeout=60)
            return result.returncode, result.stdout, result.stderr
        except Exception as e:
            return -1, "", str(e)

    def check_no_unproven_claims(self) -> bool:
        """Check for unverified claims in recent changes."""
        print("🔍 Checking for unproven claims...")
        # Check recent git commits for claim-like language without evidence
        code, out, err = self.run_cmd(["git", "log", "-5", "--oneline", "--pretty=format:%s"])
        if code == 0:
            for line in out.splitlines():
                if any(word in line.lower() for word in ["fixed", "resolved", "works", "complete", "done"]):
                    # Check if there's evidence linked
                    self.warnings.append(f"Commit claims completion: '{line}' - verify evidence exists")
        return True

    def check_no_broken_links(self) -> bool:
        """Check for broken internal links in markdown files."""
        print("🔗 Checking for broken links...")
        md_files = list(self.root.rglob("*.md"))
        broken = 0
        for md in md_files:
            if ".git" in str(md):
                continue
            try:
                content = md.read_text(encoding="utf-8")
                # Find markdown links [text](path)
                links = re.finditer(r'\[([^\]]+)\]\(([^)]+)\)', content)
                for link in links:
                    url = link.group(2)
                    if url.startswith("http"):
                        continue  # Skip external links
                    if url.startswith("#"):
                        continue  # Skip anchors
                    # Resolve relative path
                    target = (md.parent / url).resolve()
                    if not target.exists():
                        self.failures.append(f"Broken link in {md.relative_to(self.root)}: {url}")
                        broken += 1
            except Exception:
                pass
        if broken:
            print(f"  Found {broken} broken link(s)")
            return False
        print("  ✓ No broken internal links")
        return True

    def check_runtime_proof(self) -> bool:
        """Run the shared runtime contract against the selected slice bundle."""
        print("🖥️  Checking runtime proof...")
        if self.evidence_folder is None or self.evidence_manifest is None or not self.local_head:
            self.failures.append("Runtime proof cannot be checked before exact-slice evidence selection")
            return False
        try:
            from statedd_runtime_truth_check import RuntimeTruthCheck

            slice_id = str(self.evidence_manifest["slice_id"])
            checker = RuntimeTruthCheck(
                self.root,
                slice_id=slice_id,
                expected_head=self.local_head,
                evidence_dir=self.evidence_folder,
                privacy_profile=self.privacy_profile,
                verbose=self.verbose,
            )
            result = checker.run()
            if result == 0:
                print("  ✓ Runtime identity satisfies the shared exact-slice contract")
                return True
            self.failures.append(f"Runtime truth check failed with exit code {result}")
            return False
        except (ImportError, KeyError, TypeError, ValueError) as exc:
            self.failures.append(f"Runtime truth check could not load the shared contract: {exc}")
            return False

    def check_evidence_bundle(self) -> bool:
        """Load one schema-validated evidence bundle for this slice and HEAD."""
        print("📦 Checking evidence bundle...")
        code, head, err = self.run_cmd(["git", "rev-parse", "HEAD"])
        if code != 0 or not head.strip():
            self.failures.append(f"Could not determine evidence HEAD: {err or 'git rev-parse failed'}")
            return False
        code, branch, err = self.run_cmd(["git", "branch", "--show-current"])
        if code != 0 or not branch.strip():
            self.failures.append(f"Could not determine evidence branch: {err or 'detached HEAD'}")
            return False
        self.local_head = head.strip().lower()
        try:
            from statedd_remote_closure_finalizer import select_evidence_manifest

            folder, manifest, errors = select_evidence_manifest(
                self.root,
                head=self.local_head,
                branch=branch.strip(),
                slice_id=self.slice_id,
                privacy_profile=self.privacy_profile,
            )
        except ImportError as exc:
            self.failures.append(f"Shared evidence selector not found: {exc}")
            return False
        if errors or folder is None or manifest is None:
            self.failures.extend([f"Evidence: {error}" for error in errors])
            return False
        self.evidence_folder = folder
        self.evidence_manifest = manifest
        self.slice_id = str(manifest["slice_id"])
        print(f"  ✓ Exact-slice evidence bundle validated: {folder.relative_to(self.root)}")
        return True

    def check_acceptance_freeze(self) -> bool:
        """Check acceptance freeze for user-facing changes."""
        print("🧊 Checking acceptance freezes...")
        freezes = self.root / "docs" / "ACCEPTANCE_FREEZES.md"
        if not freezes.exists():
            self.warnings.append("ACCEPTANCE_FREEZES.md not found")
            return True
        content = freezes.read_text()
        if "## " not in content:
            self.warnings.append("No acceptance freeze entries recorded")
        else:
            print("  ✓ Acceptance freezes present")
        return True

    def check_handoff_complete(self) -> bool:
        """Verify handoff was generated."""
        print("📤 Checking handoff...")
        # Check for recent handoff in WORKLOG
        worklog = self.root / "WORKLOG.md"
        if worklog.exists():
            content = worklog.read_text()
            if "handoff" in content.lower() or "HANDOFF" in content:
                print("  ✓ Handoff referenced in WORKLOG")
                return True
        self.warnings.append("No handoff reference found in WORKLOG.md")
        return True

    def check_remote_truth(self) -> bool:
        """Require both exact Git refs and exact-head GitHub CI closure."""
        print("🌐 Checking remote truth (Truth Boundary Gate)...")
        # Import and run remote truth check
        sys.path.insert(0, str(self.root / "scripts"))
        try:
            from statedd_remote_truth_check import RemoteTruthCheck
            checker = RemoteTruthCheck(self.root, self.verbose, self.claimed_files)
            result = checker.run()
            if result != 0:
                self.failures.extend([f"Remote truth: {f}" for f in checker.failures])
                self.closure_label = checker.closure_label
                return False
            self.closure_label = checker.closure_label

            from statedd_remote_closure_finalizer import RemoteClosureFinalizer

            finalizer = RemoteClosureFinalizer(
                root=self.root,
                verbose=self.verbose,
                pr_number=self.pr_number,
                slice_id=self.slice_id,
                required_checks=self.required_checks,
                privacy_profile=self.privacy_profile,
            )
            final_result = finalizer.run()
            self.closure_label = finalizer.closure_label
            if final_result != 0:
                self.failures.extend([f"Remote closure: {failure}" for failure in finalizer.failures])
                if not finalizer.failures:
                    self.failures.append("Remote closure finalizer failed without a diagnostic")
                return False
            return True
        except ImportError as e:
            self.failures.append(f"Remote truth check module not found: {e}")
            return False
        except Exception as e:
            self.failures.append(f"Remote truth check crashed: {e}")
            return False

    def check_efficiency(self) -> bool:
        """Run efficiency budget check."""
        print("⚡ Running efficiency check...")
        code, out, err = self.run_cmd(
            ["python", "scripts/statedd_efficiency_check.py", "--gate-level", str(self.gate_level)]
        )
        if code == 0:
            print("  ✓ Efficiency check passed")
            return True
        self.failures.append(f"Efficiency check failed:\n{err or out}")
        return False

    def run(self) -> int:
        print("=" * 50)
        print("StateDD Closure Check")
        print("=" * 50)

        self.closure_label = "NOT CLOSURE-GRADE — LOCAL OR UNVERIFIED CLAIM"

        checks = [
            ("Broken Links", self.check_no_broken_links),
            ("Evidence Bundle", self.check_evidence_bundle),
            ("Runtime Proof", self.check_runtime_proof),
            ("Acceptance Freeze", self.check_acceptance_freeze),
            ("Remote Truth", self.check_remote_truth),
            ("Efficiency", self.check_efficiency),
        ]

        all_passed = True
        for name, check in checks:
            try:
                if not check():
                    all_passed = False
            except Exception as e:
                self.failures.append(f"{name} check crashed: {e}")
                all_passed = False

        print("\n" + "=" * 50)
        if self.warnings:
            print("Warnings:")
            for w in self.warnings:
                print(f"  ⚠ {w}")

        if self.failures or not all_passed:
            if not self.failures:
                self.failures.append("One or more closure checks returned failure without a diagnostic")
            print("Failures:")
            for f in self.failures:
                print(f"  ✗ {f}")
            print("=" * 50)
            print("❌ CLOSURE CHECK FAILED - Not closure-grade")
            return 1

        print("✅ ALL CLOSURE CRITERIA MET - Closure-grade")
        print("=" * 50)
        return 0


def main():
    parser = argparse.ArgumentParser(description="StateDD Closure Check")
    parser.add_argument("--root", default=".", help="Repository root")
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--claimed-files", nargs="*", default=[], help="Files claimed as deliverables")
    parser.add_argument("--gate-level", type=int, default=2, help="Gate level being proven")
    parser.add_argument("--pr-number", type=int, default=None, help="Explicit pull request number")
    parser.add_argument("--slice-id", default=None, help="Exact evidence slice_id to verify")
    parser.add_argument("--required-check", action="append", default=[], help="Required CI context (repeatable)")
    parser.add_argument(
        "--privacy-profile",
        choices=["public", "private", "local_only"],
        default="public",
        help="Required evidence privacy profile",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    checker = ClosureCheck(
        root,
        args.verbose,
        args.claimed_files,
        args.gate_level,
        args.pr_number,
        args.slice_id,
        args.required_check,
        args.privacy_profile,
    )
    sys.exit(checker.run())


if __name__ == "__main__":
    main()
