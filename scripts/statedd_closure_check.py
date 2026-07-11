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
from typing import Dict, List, Tuple


AGENT_CONTEXT_SCHEMA = "statedd.agent_context.v2"
AGENT_CONTEXT_FILE = Path(".statedd/agent.context")
CLASSIFIED_DIRT_CATEGORIES = {"intended_slice_work", "generated_artifact"}


def find_agent_context(root: Path, explicit: str | None = None) -> Path | None:
    """Return the path to an agent context file, or None if not found."""
    candidate: Path
    if explicit:
        path = Path(explicit)
        if path.is_absolute():
            candidate = path
        else:
            candidate = (root / path).resolve()
        # Allow passing the worktree root or the context file itself.
        if candidate.is_dir():
            candidate = candidate / AGENT_CONTEXT_FILE
        return candidate if candidate.exists() else None
    candidate = root / AGENT_CONTEXT_FILE
    return candidate if candidate.exists() else None


def load_agent_context(path: Path) -> dict | None:
    """Load and validate an agent.context JSON file."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    if data.get("schema") != AGENT_CONTEXT_SCHEMA:
        return None
    return data


def normalize_cell(cell: str) -> str:
    return cell.strip().strip("`").strip()


def parse_classification_file(path: Path) -> Dict[str, str]:
    """Parse a markdown classification table into {path: category}."""
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return {}
    classifications: Dict[str, str] = {}
    for raw in text.splitlines():
        stripped = raw.strip()
        if not stripped.startswith("|"):
            continue
        cells = [normalize_cell(cell) for cell in stripped.strip("|").split("|")]
        if not cells or set(cells[0]) <= {"-", ":"}:
            continue
        lower = [cell.lower() for cell in cells]
        if "path" in lower and "category" in lower:
            continue
        file_path = ""
        category = ""
        if len(cells) >= 3 and cells[2] in {
            "intended_slice_work",
            "pre_existing_unrelated",
            "generated_artifact",
            "unknown_do_not_touch",
            "safe_to_discard_after_proof",
        }:
            file_path = cells[1]
            category = cells[2]
        elif len(cells) >= 2 and cells[1] in {
            "intended_slice_work",
            "pre_existing_unrelated",
            "generated_artifact",
            "unknown_do_not_touch",
            "safe_to_discard_after_proof",
        }:
            file_path = cells[0]
            category = cells[1]
        if file_path and category:
            classifications[file_path] = category
    return classifications


class ClosureCheck:
    def __init__(self, root: Path, verbose: bool = False, claimed_files: List[str] = None, gate_level: int = 2, agent_context: dict | None = None):
        self.root = root
        self.verbose = verbose
        self.claimed_files = claimed_files or []
        self.gate_level = gate_level
        self.agent_context = agent_context
        self.failures: List[str] = []
        self.warnings: List[str] = []

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

    def latest_evidence_folder(self) -> Path | None:
        evidence_root = self.root / "docs" / "evidence"
        if not evidence_root.exists():
            return None
        candidates = [entry for entry in evidence_root.iterdir() if entry.is_dir() and not entry.name.startswith(".")]
        if not candidates:
            return None
        return max(candidates, key=lambda p: p.stat().st_mtime)

    def runtime_identity_path(self) -> Path:
        folder = self.latest_evidence_folder()
        if folder:
            candidate = folder / "runtime_identity.json"
            if candidate.exists():
                return candidate
        return self.root / "runtime_identity.json"

    def check_runtime_proof(self) -> bool:
        """Verify runtime identity proof exists for user-facing changes."""
        print("🖥️  Checking runtime proof...")
        runtime_identity = self.runtime_identity_path()
        if not runtime_identity.exists():
            self.failures.append("runtime_identity.json not found")
            return False
        try:
            data = json.loads(runtime_identity.read_text())
            required = ["os", "kernel", "git_head", "timestamp"]
            for field in required:
                if field not in data:
                    self.failures.append(f"runtime_identity.json missing field: {field}")
                    return False
            print(f"  ✓ Runtime identity present and complete ({runtime_identity.relative_to(self.root)})")
            return True
        except json.JSONDecodeError:
            self.failures.append("runtime_identity.json is invalid JSON")
            return False

    def check_evidence_bundle(self) -> bool:
        """Check evidence bundle exists and is complete."""
        print("📦 Checking evidence bundle...")
        evidence_log = self.root / "docs" / "EVIDENCE_LOG.md"
        if not evidence_log.exists():
            self.failures.append("EVIDENCE_LOG.md not found")
            return False
        content = evidence_log.read_text()
        if len(content.strip()) < 100:
            self.failures.append("EVIDENCE_LOG.md appears minimal")
            return False
        print("  ✓ Evidence log has content")
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

    def check_dirty_worktree(self) -> bool:
        """In agent context, dirty files must be classified slice work."""
        if self.agent_context is None:
            return True
        print("🧹 Checking dirty worktree classification in agent context...")
        code, out, _ = self.run_cmd(["git", "status", "--short"])
        if code != 0:
            self.failures.append("Could not check worktree status")
            return False
        if not out.strip():
            return True
        changed = []
        for line in out.splitlines():
            raw = line.rstrip("\n")
            if not raw.strip():
                continue
            # git status --short is two status chars, a space, then the path.
            if len(raw) >= 3 and raw[2] == " ":
                path = raw[3:].strip()
            elif len(raw) >= 2 and raw[1] == " ":
                # Already-trimmed line (e.g. "M file.txt").
                path = raw[2:].strip()
            else:
                path = raw.strip()
            if " -> " in path:
                path = path.split(" -> ", 1)[1]
            changed.append(path)
        if not changed:
            return True
        folder = self.latest_evidence_folder()
        if folder is None:
            self.failures.append("Dirty worktree in agent context and no evidence folder to classify dirt")
            return False
        readme = folder / "README.md"
        if not readme.exists():
            self.failures.append("Dirty worktree in agent context and no evidence README to classify dirt")
            return False
        classifications = parse_classification_file(readme)
        unclassified = [p for p in changed if classifications.get(p) not in CLASSIFIED_DIRT_CATEGORIES]
        if unclassified:
            self.failures.append(f"Unclassified dirty files in agent context: {', '.join(unclassified)}")
            return False
        print("  ✓ Dirty worktree classified as intended slice work or generated artifact")
        return True

    def check_remote_truth(self) -> bool:
        """Verify remote GitHub state matches local claims (Truth Boundary Gate)."""
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
            ("Unproven Claims", self.check_no_unproven_claims),
            ("Broken Links", self.check_no_broken_links),
            ("Runtime Proof", self.check_runtime_proof),
            ("Evidence Bundle", self.check_evidence_bundle),
            ("Acceptance Freeze", self.check_acceptance_freeze),
            ("Handoff Complete", self.check_handoff_complete),
            ("Dirty Worktree", self.check_dirty_worktree),
            ("Remote Truth", self.check_remote_truth),
            ("Efficiency", self.check_efficiency),
        ]

        for name, check in checks:
            try:
                check()
            except Exception as e:
                self.failures.append(f"{name} check crashed: {e}")

        print("\n" + "=" * 50)
        if self.warnings:
            print("Warnings:")
            for w in self.warnings:
                print(f"  ⚠ {w}")

        if self.failures:
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
    parser.add_argument(
        "--agent-context",
        default=None,
        help="Path to agent.context JSON (auto-detects .statedd/agent.context if omitted)",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    agent_context_path = find_agent_context(root, args.agent_context)
    agent_context = load_agent_context(agent_context_path) if agent_context_path else None
    checker = ClosureCheck(root, args.verbose, args.claimed_files, args.gate_level, agent_context)
    sys.exit(checker.run())


if __name__ == "__main__":
    main()
