#!/usr/bin/env python3
"""Verify typed evidence in the exact current-slice artifact manifest.

Selection is based only on manifest slice/head fields. Global evidence logs,
filenames, directory mtimes, and historical keyword matches are not evidence.

Exit codes: 0=match, 1=mismatch/invalid evidence, 2=execution error.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from enum import Enum
from pathlib import Path

from statedd_validate_schema import ArtifactContractError, EvidenceBundle, load_evidence_bundle


class ChangeType(Enum):
    UI = "ui"
    API = "api"
    CONFIG = "config"
    DOCS = "docs"
    REFACTOR = "refactor"
    INFRA = "infra"


class EvidenceType(Enum):
    BROWSER_SCREENSHOT = "browser_screenshot"
    RUNTIME_PROOF = "runtime_proof"
    REQUEST_RESPONSE_LOG = "request_response_log"
    SCHEMA_VALIDATION = "schema_validation"
    DIFF = "diff"
    VALIDATION_OUTPUT = "validation_output"
    RENDERED_PREVIEW = "rendered_preview"
    TEST_COVERAGE = "test_coverage"
    BENCHMARK = "benchmark"


REQUIRED_EVIDENCE: dict[ChangeType, tuple[EvidenceType, ...]] = {
    ChangeType.UI: (EvidenceType.BROWSER_SCREENSHOT, EvidenceType.RUNTIME_PROOF),
    ChangeType.API: (EvidenceType.REQUEST_RESPONSE_LOG, EvidenceType.SCHEMA_VALIDATION),
    ChangeType.CONFIG: (EvidenceType.DIFF, EvidenceType.VALIDATION_OUTPUT),
    ChangeType.DOCS: (EvidenceType.RENDERED_PREVIEW,),
    ChangeType.REFACTOR: (EvidenceType.TEST_COVERAGE, EvidenceType.BENCHMARK),
    ChangeType.INFRA: (EvidenceType.RUNTIME_PROOF, EvidenceType.VALIDATION_OUTPUT),
}


class EvidenceTypeCheck:
    def __init__(
        self,
        root: Path,
        *,
        slice_id: str,
        expected_head: str | None = None,
        evidence_dir: Path | None = None,
        change_type: ChangeType | str | None = None,
        privacy_profile: str = "public",
        verbose: bool = False,
    ):
        self.root = root.resolve()
        self.slice_id = slice_id
        self.expected_head = expected_head
        self.evidence_dir = evidence_dir
        self.expected_change_type = (
            change_type
            if isinstance(change_type, ChangeType) or change_type is None
            else ChangeType(change_type)
        )
        self.privacy_profile = privacy_profile
        self.verbose = verbose
        self.missing: list[str] = []
        self.bundle: EvidenceBundle | None = None

    def current_head(self) -> str:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=self.root,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if completed.returncode != 0 or not completed.stdout.strip():
            raise RuntimeError(completed.stderr.strip() or "git rev-parse HEAD returned no value")
        return completed.stdout.strip().lower()

    def manifest_change_type(self, bundle: EvidenceBundle) -> ChangeType:
        change = bundle.manifest.get("change")
        value = change.get("type") if isinstance(change, dict) else None
        try:
            return ChangeType(value)
        except (TypeError, ValueError) as exc:
            raise ArtifactContractError(f"unsupported manifest change.type: {value!r}") from exc

    def available_evidence(self, bundle: EvidenceBundle) -> set[EvidenceType]:
        available: set[EvidenceType] = set()
        artifacts = bundle.manifest.get("artifacts")
        if not isinstance(artifacts, list):
            return available
        for artifact in artifacts:
            if not isinstance(artifact, dict):
                continue
            evidence_types = artifact.get("evidence_types")
            if not isinstance(evidence_types, list):
                continue
            for value in evidence_types:
                try:
                    available.add(EvidenceType(value))
                except (TypeError, ValueError):
                    continue
        return available

    def display_path(self, path: Path) -> str:
        try:
            return path.relative_to(self.root).as_posix()
        except ValueError:
            return path.as_posix()

    def run(self) -> int:
        print("=" * 60)
        print("StateDD Evidence Type Check")
        print("=" * 60)

        try:
            actual_head = self.current_head()
            expected_head = (self.expected_head or actual_head).lower()
            if expected_head != actual_head:
                print(
                    f"FAIL expected head {expected_head} does not match current repository head {actual_head}"
                )
                return 1

            self.bundle = load_evidence_bundle(
                self.root,
                self.slice_id,
                expected_head,
                evidence_dir=self.evidence_dir,
                privacy_profile=self.privacy_profile,
            )
            change_type = self.manifest_change_type(self.bundle)
            if self.expected_change_type is not None and change_type != self.expected_change_type:
                print(
                    f"FAIL manifest change.type {change_type.value!r} does not match "
                    f"requested type {self.expected_change_type.value!r}"
                )
                return 1

            required = REQUIRED_EVIDENCE[change_type]
            available = self.available_evidence(self.bundle)
            self.missing = [item.value for item in required if item not in available]

            print(f"slice: {self.slice_id}")
            print(f"head: {actual_head}")
            print(f"manifest: {self.display_path(self.bundle.manifest_path)}")
            print(f"change type: {change_type.value}")
            print(f"required evidence: {[item.value for item in required]}")
            print(f"declared evidence: {sorted(item.value for item in available)}")

            if self.missing:
                print("FAIL missing required typed evidence:")
                for missing in self.missing:
                    print(f"  - {missing}")
                return 1

            print("PASS exact-slice manifest contains every required typed artifact")
            return 0
        except ArtifactContractError as exc:
            print(f"FAIL artifact contract: {exc}")
            return 1
        except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
            print(f"ERROR evidence type check could not execute: {exc}")
            return 2


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate exact-slice StateDD evidence types")
    parser.add_argument("--root", default=".", help="Repository root")
    parser.add_argument("--slice-id", required=True, help="Exact backlog slice identity")
    parser.add_argument("--head", help="Expected exact commit; defaults to current HEAD")
    parser.add_argument("--evidence-dir", help="Explicit evidence bundle directory")
    parser.add_argument("--change-type", choices=[item.value for item in ChangeType])
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
    checker = EvidenceTypeCheck(
        Path(args.root),
        slice_id=args.slice_id,
        expected_head=args.head,
        evidence_dir=Path(args.evidence_dir) if args.evidence_dir else None,
        change_type=args.change_type,
        privacy_profile=args.privacy_profile,
        verbose=args.verbose,
    )
    return checker.run()


if __name__ == "__main__":
    raise SystemExit(main())
