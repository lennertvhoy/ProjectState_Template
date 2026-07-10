#!/usr/bin/env python3
"""Validate runtime truth from the exact current-slice evidence bundle.

Exit codes: 0=match, 1=mismatch/invalid evidence, 2=execution error.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from statedd_validate_schema import ArtifactContractError, EvidenceBundle, load_evidence_bundle


class RuntimeTruthCheck:
    def __init__(
        self,
        root: Path,
        *,
        slice_id: str,
        expected_head: str | None = None,
        evidence_dir: Path | None = None,
        privacy_profile: str = "public",
        verbose: bool = False,
    ):
        self.root = root.resolve()
        self.slice_id = slice_id
        self.expected_head = expected_head
        self.evidence_dir = evidence_dir
        self.privacy_profile = privacy_profile
        self.verbose = verbose
        self.mismatches: list[str] = []
        self.bundle: EvidenceBundle | None = None

    def git_value(self, *args: str) -> str:
        completed = subprocess.run(
            ["git", *args],
            cwd=self.root,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if completed.returncode != 0:
            raise RuntimeError(completed.stderr.strip() or f"git {' '.join(args)} failed")
        value = completed.stdout.strip()
        if not value:
            raise RuntimeError(f"git {' '.join(args)} returned no value")
        return value

    def compare_repo_identity(self, bundle: EvidenceBundle, head: str, branch: str) -> None:
        manifest_repo = bundle.manifest.get("repo")
        if not isinstance(manifest_repo, dict):
            self.mismatches.append("manifest repo identity is missing")
            return
        if manifest_repo.get("head") != head:
            self.mismatches.append(
                f"manifest head {manifest_repo.get('head')!r} does not match current head {head!r}"
            )
        if manifest_repo.get("branch") != branch:
            self.mismatches.append(
                f"manifest branch {manifest_repo.get('branch')!r} does not match current branch {branch!r}"
            )

    def compare_runtime_claim(self, bundle: EvidenceBundle) -> None:
        runtime = bundle.runtime_identity.get("runtime")
        checks = bundle.runtime_identity.get("checks")
        if not isinstance(runtime, dict) or not isinstance(checks, dict):
            self.mismatches.append("runtime identity is missing runtime/checks objects")
            return
        if runtime.get("required") is True and checks.get("endpoint_reachable") is not True:
            self.mismatches.append("required runtime does not record endpoint_reachable=true")
        if runtime.get("required") is False and checks.get("runtime_not_applicable_recorded") is not True:
            self.mismatches.append(
                "non-required runtime does not record runtime_not_applicable_recorded=true"
            )

    def display_path(self, path: Path) -> str:
        try:
            return path.relative_to(self.root).as_posix()
        except ValueError:
            return path.as_posix()

    def run(self) -> int:
        print("=" * 60)
        print("StateDD Runtime Truth Check")
        print("=" * 60)

        try:
            current_head = self.git_value("rev-parse", "HEAD").lower()
            current_branch = self.git_value("branch", "--show-current")
            expected_head = (self.expected_head or current_head).lower()
            if expected_head != current_head:
                print(
                    f"FAIL expected head {expected_head} does not match current repository head {current_head}"
                )
                return 1

            self.bundle = load_evidence_bundle(
                self.root,
                self.slice_id,
                expected_head,
                evidence_dir=self.evidence_dir,
                privacy_profile=self.privacy_profile,
            )
            self.compare_repo_identity(self.bundle, current_head, current_branch)
            self.compare_runtime_claim(self.bundle)

            print(f"slice: {self.slice_id}")
            print(f"head: {current_head}")
            print(f"manifest: {self.display_path(self.bundle.manifest_path)}")
            print(f"runtime artifact: {self.display_path(self.bundle.runtime_identity_path)}")

            if self.mismatches:
                print("FAIL runtime truth mismatch:")
                for mismatch in self.mismatches:
                    print(f"  - {mismatch}")
                return 1

            runtime = self.bundle.runtime_identity["runtime"]
            runtime_state = "required" if runtime.get("required") is True else "not_applicable"
            print(f"PASS runtime identity is schema-valid and exact-head bound ({runtime_state})")
            return 0
        except ArtifactContractError as exc:
            print(f"FAIL artifact contract: {exc}")
            return 1
        except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
            print(f"ERROR runtime truth check could not execute: {exc}")
            return 2


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate exact-slice StateDD runtime truth")
    parser.add_argument("--root", default=".", help="Repository root")
    parser.add_argument("--slice-id", required=True, help="Exact backlog slice identity")
    parser.add_argument("--head", help="Expected exact commit; defaults to current HEAD")
    parser.add_argument("--evidence-dir", help="Explicit evidence bundle directory")
    parser.add_argument(
        "--privacy-profile",
        choices=["public", "private", "local_only"],
        default="public",
        help="Required evidence privacy profile",
    )
    parser.add_argument("--verbose", "-v", action="store_true")
    return parser.parse_args(argv[1:])


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv)
    checker = RuntimeTruthCheck(
        Path(args.root),
        slice_id=args.slice_id,
        expected_head=args.head,
        evidence_dir=Path(args.evidence_dir) if args.evidence_dir else None,
        privacy_profile=args.privacy_profile,
        verbose=args.verbose,
    )
    return checker.run()


if __name__ == "__main__":
    raise SystemExit(main())
