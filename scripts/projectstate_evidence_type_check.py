#!/usr/bin/env python3
"""
ProjectState Evidence Type Check

Ensures each user-facing change has the appropriate evidence type:
- UI changes: browser screenshots + runtime proof
- API changes: request/response logs + schema validation
- Config changes: diff + validation output
- Documentation: rendered preview
- Refactoring: test coverage + benchmarks
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Tuple
from dataclasses import dataclass
from enum import Enum


class ChangeType(Enum):
    UI = "ui"
    API = "api"
    CONFIG = "config"
    DOCS = "docs"
    REFACTOR = "refactor"
    INFRA = "infra"
    UNKNOWN = "unknown"


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
    NONE = "none"


# Required evidence per change type
REQUIRED_EVIDENCE: Dict[ChangeType, List[EvidenceType]] = {
    ChangeType.UI: [EvidenceType.BROWSER_SCREENSHOT, EvidenceType.RUNTIME_PROOF],
    ChangeType.API: [EvidenceType.REQUEST_RESPONSE_LOG, EvidenceType.SCHEMA_VALIDATION],
    ChangeType.CONFIG: [EvidenceType.DIFF, EvidenceType.VALIDATION_OUTPUT],
    ChangeType.DOCS: [EvidenceType.RENDERED_PREVIEW],
    ChangeType.REFACTOR: [EvidenceType.TEST_COVERAGE, EvidenceType.BENCHMARK],
    ChangeType.INFRA: [EvidenceType.RUNTIME_PROOF, EvidenceType.VALIDATION_OUTPUT],
    ChangeType.UNKNOWN: [EvidenceType.NONE],
}


@dataclass
class Change:
    files: List[str]
    type: ChangeType
    description: str


class EvidenceTypeCheck:
    def __init__(self, root: Path, verbose: bool = False):
        self.root = root
        self.verbose = verbose
        self.missing: List[str] = []

    def run_cmd(self, cmd: List[str]) -> Tuple[int, str, str]:
        try:
            result = subprocess.run(cmd, cwd=self.root, capture_output=True, text=True, timeout=30)
            return result.returncode, result.stdout, result.stderr
        except Exception as e:
            return -1, "", str(e)

    def detect_change_type(self, files: List[str]) -> ChangeType:
        """Heuristically determine change type from modified files."""
        ui_patterns = [r"\.html?$", r"\.jsx?$", r"\.tsx?$", r"\.vue$", r"\.svelte$", r"\.css$", r"\.scss$",
                       r"templates/", r"static/", r"frontend/", r"ui/", r"components/"]
        api_patterns = [r"\.py$", r"\.go$", r"\.rs$", r"\.java$", r"api/", r"routes/", r"handlers/",
                        r"controllers/", r"endpoints/", r"openapi", r"swagger"]
        config_patterns = [r"\.ya?ml$", r"\.json$", r"\.toml$", r"\.ini$", r"\.conf$", r"config/",
                           r"settings/", r"\.env", r"Dockerfile", r"docker-compose"]
        docs_patterns = [r"\.md$", r"\.rst$", r"\.txt$", r"docs/", r"README", r"CHANGELOG"]
        refactor_patterns = [r"test_", r"_test\.py", r"spec_", r"benchmark", r"bench_"]
        infra_patterns = [r"\.tf$", r"\.tfvars$", r"k8s/", r"kubernetes/", r"helm/", r"ansible/",
                          r"terraform/", r".github/workflows/", r".gitlab-ci.yml"]

        for f in files:
            for pat in ui_patterns:
                if re.search(pat, f, re.IGNORECASE):
                    return ChangeType.UI
            for pat in api_patterns:
                if re.search(pat, f, re.IGNORECASE):
                    return ChangeType.API
            for pat in config_patterns:
                if re.search(pat, f, re.IGNORECASE):
                    return ChangeType.CONFIG
            for pat in infra_patterns:
                if re.search(pat, f, re.IGNORECASE):
                    return ChangeType.INFRA

        # Check if mostly docs
        doc_count = sum(1 for f in files if any(re.search(p, f, re.IGNORECASE) for p in docs_patterns))
        if doc_count > len(files) * 0.5:
            return ChangeType.DOCS

        # Check if mostly tests/refactor
        ref_count = sum(1 for f in files if any(re.search(p, f, re.IGNORECASE) for p in refactor_patterns))
        if ref_count > len(files) * 0.3:
            return ChangeType.REFACTOR

        return ChangeType.UNKNOWN

    def get_recent_changes(self) -> Change:
        """Get recent git changes."""
        code, out, err = self.run_cmd(["git", "diff", "HEAD~1..HEAD", "--name-only"])
        files = [f for f in out.strip().split("\n") if f] if code == 0 else []

        code, out, err = self.run_cmd(["git", "log", "-1", "--pretty=format:%s"])
        desc = out.strip() if code == 0 else "No description"

        change_type = self.detect_change_type(files)
        return Change(files=files, type=change_type, description=desc)

    def check_evidence_exists(self, evidence_type: EvidenceType) -> bool:
        """Check if required evidence type exists."""
        if evidence_type == EvidenceType.BROWSER_SCREENSHOT:
            # Look for screenshots in evidence dir
            evidence_dir = self.root / "docs" / "evidence"
            if evidence_dir.exists():
                for ext in [".png", ".jpg", ".jpeg", ".webp"]:
                    if list(evidence_dir.rglob(f"*{ext}")):
                        return True
            # Check EVIDENCE_LOG.md for screenshot references
            log = self.root / "docs" / "EVIDENCE_LOG.md"
            if log.exists():
                content = log.read_text()
                if "screenshot" in content.lower() or ".png" in content or ".jpg" in content:
                    return True
            return False

        elif evidence_type == EvidenceType.RUNTIME_PROOF:
            return (self.root / "runtime_identity.json").exists()

        elif evidence_type == EvidenceType.REQUEST_RESPONSE_LOG:
            log = self.root / "docs" / "EVIDENCE_LOG.md"
            if log.exists():
                content = log.read_text()
                if "request" in content.lower() and "response" in content.lower():
                    return True
            # Check for network logs
            evidence_dir = self.root / "docs" / "evidence"
            if evidence_dir.exists():
                for f in evidence_dir.rglob("*.har"):
                    return True
                for f in evidence_dir.rglob("*network*"):
                    return True
            return False

        elif evidence_type == EvidenceType.SCHEMA_VALIDATION:
            log = self.root / "docs" / "EVIDENCE_LOG.md"
            if log.exists():
                content = log.read_text()
                if "schema" in content.lower() and "valid" in content.lower():
                    return True
            # Check for validation output
            return (self.root / "schema_validation.json").exists() or \
                   (self.root / "validation_output.json").exists()

        elif evidence_type == EvidenceType.DIFF:
            # Git diff always exists for changes
            return True

        elif evidence_type == EvidenceType.VALIDATION_OUTPUT:
            log = self.root / "docs" / "EVIDENCE_LOG.md"
            if log.exists():
                content = log.read_text()
                if "valid" in content.lower() or "check" in content.lower() or "lint" in content.lower():
                    return True
            return False

        elif evidence_type == EvidenceType.RENDERED_PREVIEW:
            log = self.root / "docs" / "EVIDENCE_LOG.md"
            if log.exists():
                content = log.read_text()
                if "preview" in content.lower() or "render" in content.lower():
                    return True
            return False

        elif evidence_type == EvidenceType.TEST_COVERAGE:
            # Check for coverage report
            for pattern in ["coverage.xml", "coverage.json", "htmlcov/", ".coverage"]:
                if (self.root / pattern).exists():
                    return True
            log = self.root / "docs" / "EVIDENCE_LOG.md"
            if log.exists():
                content = log.read_text()
                if "coverage" in content.lower():
                    return True
            return False

        elif evidence_type == EvidenceType.BENCHMARK:
            log = self.root / "docs" / "EVIDENCE_LOG.md"
            if log.exists():
                content = log.read_text()
                if "benchmark" in content.lower() or "perf" in content.lower():
                    return True
            return False

        return True  # NONE always passes

    def run(self) -> int:
        print("=" * 50)
        print("ProjectState Evidence Type Check")
        print("=" * 50)

        change = self.get_recent_changes()
        print(f"📝 Recent change: {change.description}")
        print(f"📁 Files: {len(change.files)}")
        print(f"🔍 Detected type: {change.type.value}")

        required = REQUIRED_EVIDENCE.get(change.type, [EvidenceType.NONE])
        print(f"📋 Required evidence: {[e.value for e in required]}")

        for ev_type in required:
            if ev_type == EvidenceType.NONE:
                continue
            exists = self.check_evidence_exists(ev_type)
            status = "✅" if exists else "❌"
            print(f"  {status} {ev_type.value}")
            if not exists:
                self.missing.append(ev_type.value)

        print("\n" + "=" * 50)
        if self.missing:
            print("❌ MISSING REQUIRED EVIDENCE:")
            for m in self.missing:
                print(f"  - {m}")
            print("=" * 50)
            return 1

        print("✅ ALL REQUIRED EVIDENCE PRESENT")
        print("=" * 50)
        return 0


def main():
    parser = argparse.ArgumentParser(description="ProjectState Evidence Type Check")
    parser.add_argument("--root", default=".", help="Repository root")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    checker = EvidenceTypeCheck(root, args.verbose)
    sys.exit(checker.run())


if __name__ == "__main__":
    main()
