#!/usr/bin/env python3
"""Run local slice-readiness checks.

The filename remains for compatibility, but this command cannot establish remote
closure. Only ``statedd_remote_closure_finalizer.py`` binds the final pushed head,
pull request, evidence, and exact-head CI result.
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Tuple


AGENT_CONTEXT_SCHEMA = "statedd.agent_context.v1"
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
    def __init__(
        self,
        root: Path,
        verbose: bool = False,
        claimed_files: List[str] = None,
        gate_level: int = 2,
        agent_context: dict | None = None,
        evidence_folder: Path | None = None,
        runtime_endpoint: str | None = None,
        allow_remote_runtime: bool = False,
    ):
        self.root = root
        self.verbose = verbose
        self.claimed_files = claimed_files or []
        self.gate_level = gate_level
        self.agent_context = agent_context
        self.evidence_folder = evidence_folder
        self.runtime_endpoint = runtime_endpoint
        self.allow_remote_runtime = allow_remote_runtime
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
        if self.evidence_folder is not None:
            return self.evidence_folder
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
        """Re-probe the explicitly selected runtime identity artifact."""
        print("🖥️  Checking runtime proof...")
        runtime_identity = self.runtime_identity_path()
        if not runtime_identity.exists():
            self.failures.append("runtime_identity.json not found")
            return False
        command = [
            sys.executable,
            "scripts/statedd_runtime_truth_check.py",
            "--artifact",
            str(runtime_identity.relative_to(self.root)),
        ]
        if self.runtime_endpoint:
            command.extend(["--expected-endpoint", self.runtime_endpoint])
        if self.allow_remote_runtime:
            command.append("--allow-remote")
        code, out, err = self.run_cmd(command)
        if code != 0:
            self.failures.append(f"Runtime truth check failed:\n{err or out}")
            return False
        print(f"  ✓ Runtime truth re-probed ({runtime_identity.relative_to(self.root)})")
        return True

    def check_evidence_bundle(self) -> bool:
        """Validate the selected local evidence pack, not just its prose log."""
        print("📦 Checking evidence bundle...")
        folder = self.latest_evidence_folder()
        if folder is None:
            self.failures.append("No local evidence folder found")
            return False
        code, out, err = self.run_cmd(
            [sys.executable, "scripts/statedd_evidence_pack.py", "check", "--strict", str(folder)]
        )
        if code != 0:
            self.failures.append(f"Evidence pack validation failed:\n{err or out}")
            return False
        evidence_log = self.root / "docs" / "EVIDENCE_LOG.md"
        if not evidence_log.exists():
            self.failures.append("EVIDENCE_LOG.md not found")
            return False
        content = evidence_log.read_text()
        if len(content.strip()) < 100:
            self.failures.append("EVIDENCE_LOG.md appears minimal")
            return False
        print(f"  ✓ Strict evidence pack validation passed ({folder.relative_to(self.root)})")
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

    def check_efficiency(self) -> bool:
        """Run efficiency budget check."""
        print("⚡ Running efficiency check...")
        code, out, err = self.run_cmd(
            [sys.executable, "scripts/statedd_efficiency_check.py", "--gate-level", str(self.gate_level)]
        )
        if code == 0:
            print("  ✓ Efficiency check passed")
            return True
        self.failures.append(f"Efficiency check failed:\n{err or out}")
        return False

    def run(self) -> int:
        print("=" * 50)
        print("StateDD Local Slice Preflight")
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
            print("❌ LOCAL SLICE PREFLIGHT FAILED — NOT CLOSURE-GRADE")
            return 1

        print("✅ LOCAL SLICE PREFLIGHT PASSED")
        print("Remote branch, PR, exact-head CI, and final evidence agreement: not checked")
        print("Run statedd_remote_closure_finalizer.py after commit, push, and CI.")
        print("=" * 50)
        return 0


def main():
    parser = argparse.ArgumentParser(description="StateDD local slice preflight (not remote closure)")
    parser.add_argument("--root", default=".", help="Repository root")
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--claimed-files", nargs="*", default=[], help="Files claimed as deliverables")
    parser.add_argument("--gate-level", type=int, default=2, help="Gate level being proven")
    parser.add_argument(
        "--evidence-folder",
        required=True,
        help="Explicit evidence folder; modification-time selection is not closure proof",
    )
    parser.add_argument("--runtime-endpoint", help="Trusted endpoint for runtime-required evidence")
    parser.add_argument(
        "--allow-remote-runtime",
        action="store_true",
        help="Permit remote re-probe when revision-header binding is present",
    )
    parser.add_argument(
        "--agent-context",
        default=None,
        help="Path to agent.context JSON (auto-detects .statedd/agent.context if omitted)",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    requested_evidence = Path(args.evidence_folder)
    evidence_folder = (
        requested_evidence.resolve()
        if requested_evidence.is_absolute()
        else (root / requested_evidence).resolve()
    )
    try:
        evidence_folder.relative_to(root)
    except ValueError:
        parser.error("--evidence-folder must stay inside the repository")
    if not evidence_folder.is_dir():
        parser.error("--evidence-folder must identify an existing directory")
    agent_context_path = find_agent_context(root, args.agent_context)
    agent_context = load_agent_context(agent_context_path) if agent_context_path else None
    checker = ClosureCheck(
        root,
        args.verbose,
        args.claimed_files,
        args.gate_level,
        agent_context,
        evidence_folder,
        args.runtime_endpoint,
        args.allow_remote_runtime,
    )
    sys.exit(checker.run())


if __name__ == "__main__":
    main()
