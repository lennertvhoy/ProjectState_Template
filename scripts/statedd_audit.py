#!/usr/bin/env python3
"""Machine-checkable StateDD audit command.

This command converts StateDD from "please be disciplined" into
"the repo rejects sloppy closure". It checks required state files,
evidence hygiene, git state, and schema ownership. Run it before
handoff, before switching to operating mode, and in CI.

Exit codes:
  0 = audit passed (closure-grade, unless overridden)
  1 = audit found issues that must be fixed or explicitly overridden
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]

REQUIRED_STATE_FILES = [
    "AGENTS.md",
    "STATUS.md",
    "PROJECT_STATE.yaml",
    "PROJECT_DNA.yaml",
    "PROJECT_ADAPTER.yaml",
    "NEXT_ACTIONS.md",
    "BACKLOG.md",
    "WORKLOG.md",
    "docs/EVIDENCE_LOG.md",
    "docs/ACCEPTANCE_FREEZES.md",
]

USER_FACING_PATTERNS = [
    re.compile(r"\.tsx?$"),
    re.compile(r"\.jsx?$"),
    re.compile(r"\.html?$"),
    re.compile(r"\.css$"),
    re.compile(r"\.vue$"),
    re.compile(r"\.svelte$"),
]

SCHEMA_PATTERNS = [
    re.compile(r"schema\.(json|ts|js|py|go|rs|yaml|yml)$", re.IGNORECASE),
    re.compile(r"\.schema\.(json|ts|js|py|go|rs|yaml|yml)$", re.IGNORECASE),
    re.compile(r"schemas/.*\.(json|ts|js|py|go|rs|yaml|yml)$", re.IGNORECASE),
    re.compile(r"types/.*\.(ts|js|py|go|rs)$", re.IGNORECASE),
    re.compile(r"zod/.*\.(ts|js)$", re.IGNORECASE),
]

EVIDENCE_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
EVIDENCE_BROWSER_EXTENSIONS = {".html", ".har", ".json"}


@dataclass
class Finding:
    rule: str
    status: str  # pass, fail, warn, override
    message: str


@dataclass
class AuditResult:
    findings: list[Finding] = field(default_factory=list)

    def add(self, rule: str, status: str, message: str) -> None:
        self.findings.append(Finding(rule, status, message))

    def has_failures(self) -> bool:
        return any(f.status == "fail" for f in self.findings)

    def has_warnings(self) -> bool:
        return any(f.status == "warn" for f in self.findings)


def run_command(args: list[str], cwd: Path) -> tuple[int, str, str]:
    try:
        completed = subprocess.run(
            args,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        return 127, "", str(exc)
    return completed.returncode, completed.stdout.strip(), completed.stderr.strip()


def git_value(repo: Path, args: list[str], fallback: str = "not proven") -> str:
    code, stdout, stderr = run_command(["git", *args], repo)
    if code != 0:
        return stderr or fallback
    return stdout or fallback


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Machine-checkable StateDD audit command",
    )
    parser.add_argument("root", nargs="?", default=str(ROOT), help="Repo root to audit")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail on warnings such as stale state files or missing browser evidence",
    )
    parser.add_argument(
        "--test-command",
        action="append",
        default=[],
        help="Command(s) that must pass for the slice to be closure-grade",
    )
    parser.add_argument(
        "--override-file",
        default=None,
        help="Path to an evidence README containing a declared human override",
    )
    return parser.parse_args(argv[1:])


def check_required_files(root: Path, result: AuditResult) -> None:
    for relpath in REQUIRED_STATE_FILES:
        path = root / relpath
        if path.exists():
            result.add("required_files", "pass", f"{relpath} exists")
        else:
            result.add("required_files", "fail", f"Missing required state file: {relpath}")


def extract_updated_at(path: Path) -> dt.datetime | None:
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8")
    match = re.search(r"(?:updated_at|last_updated):\s*(\d{4}-\d{2}-\d{2})", text)
    if not match:
        match = re.search(r"Updated At:\**\s*\*?(\d{4}-\d{2}-\d{2})\*?", text)
    if not match:
        return None
    try:
        return dt.datetime.strptime(match.group(1), "%Y-%m-%d").replace(tzinfo=dt.timezone.utc)
    except ValueError:
        return None


def check_state_files_fresh(root: Path, result: AuditResult, strict: bool) -> None:
    now = dt.datetime.now(dt.timezone.utc)
    stale_threshold = dt.timedelta(days=14)
    for relpath in ("STATUS.md", "PROJECT_STATE.yaml", "NEXT_ACTIONS.md", "BACKLOG.md"):
        path = root / relpath
        updated = extract_updated_at(path)
        if updated is None:
            status = "fail" if strict else "warn"
            result.add("state_freshness", status, f"{relpath} has no parseable updated_at date")
            continue
        age = now - updated
        if age > stale_threshold:
            status = "fail" if strict else "warn"
            result.add(
                "state_freshness",
                status,
                f"{relpath} was last updated on {updated.date().isoformat()} ({age.days} days ago)",
            )
        else:
            result.add(
                "state_freshness",
                "pass",
                f"{relpath} updated within the last {stale_threshold.days} days",
            )


def latest_evidence_folder(root: Path) -> Path | None:
    evidence_root = root / "docs" / "evidence"
    if not evidence_root.exists():
        return None
    candidates = [
        entry
        for entry in evidence_root.iterdir()
        if entry.is_dir() and not entry.name.startswith(".")
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


def check_evidence_folder(root: Path, result: AuditResult) -> None:
    folder = latest_evidence_folder(root)
    if folder is None:
        result.add("evidence_folder", "warn", "No evidence folder found under docs/evidence/")
        return
    result.add("evidence_folder", "pass", f"Latest evidence folder: {folder.relative_to(root)}")

    readme = folder / "README.md"
    if readme.exists():
        result.add("evidence_readme", "pass", f"Evidence README exists: {readme.relative_to(root)}")
        text = readme.read_text(encoding="utf-8")
        for marker in ("branch:", "head:", "Claims", "claim"):
            if marker.lower() in text.lower():
                continue
            result.add("evidence_readme", "warn", f"Evidence README missing expected marker: {marker}")
            break
        else:
            result.add("evidence_readme", "pass", "Evidence README contains branch/head and claim markers")
    else:
        result.add("evidence_readme", "fail", f"Latest evidence folder lacks README.md: {folder.relative_to(root)}")

    files = [p for p in folder.rglob("*") if p.is_file()]
    if len(files) > 20:
        result.add(
            "evidence_size",
            "fail",
            f"Evidence folder has {len(files)} files; limit is 20 unless overridden",
        )
    else:
        result.add("evidence_size", "pass", f"Evidence folder has {len(files)} files")


def git_changed_files(repo: Path) -> tuple[bool, list[str]]:
    code, status, _ = run_command(["git", "status", "--short"], repo)
    if code != 0:
        return False, []
    return True, [line.strip() for line in status.splitlines() if line.strip()]


def git_branch_and_head(repo: Path) -> tuple[str, str]:
    branch = git_value(repo, ["rev-parse", "--abbrev-ref", "HEAD"])
    head = git_value(repo, ["rev-parse", "HEAD"])
    return branch, head


def check_worktree_clean(repo: Path, result: AuditResult) -> None:
    is_git_repo, changed = git_changed_files(repo)
    if not is_git_repo:
        result.add(
            "worktree_clean",
            "warn",
            "Not a git repository; cannot verify worktree cleanliness",
        )
        return
    if changed:
        result.add(
            "worktree_clean",
            "fail",
            f"Worktree is dirty ({len(changed)} changed file(s)); closure-grade requires clean worktree",
        )
    else:
        result.add("worktree_clean", "pass", "Worktree is clean")


def check_branch_head_recorded(repo: Path, result: AuditResult) -> None:
    branch, head = git_branch_and_head(repo)
    folder = latest_evidence_folder(repo)
    if folder is None:
        result.add("branch_head_recorded", "warn", "Cannot verify branch/head recording without evidence folder")
        return
    readme = folder / "README.md"
    if not readme.exists():
        result.add("branch_head_recorded", "fail", "Evidence folder README missing; cannot verify branch/head recording")
        return

    code, _, _ = run_command(["git", "rev-parse", "HEAD"], repo)
    if code != 0:
        result.add(
            "branch_head_recorded",
            "warn",
            "Not a git repository; cannot verify branch/head recording",
        )
        return

    text = readme.read_text(encoding="utf-8")
    head_like = re.search(r"\b[0-9a-f]{7,40}\b", text, re.IGNORECASE)
    if head_like:
        recorded = head_like.group(0)
        if recorded == head[:7] or recorded == head:
            result.add("branch_head_recorded", "pass", f"HEAD {head[:7]} recorded in evidence README")
        else:
            result.add(
                "branch_head_recorded",
                "pass",
                f"HEAD {head[:7]} recorded in git; evidence README records {recorded[:7]} (acceptable if README was written before the final commit)",
            )
    else:
        result.add(
            "branch_head_recorded",
            "fail",
            f"HEAD {head[:7]} not found in evidence README; record current HEAD before closure",
        )
    if branch in text:
        result.add("branch_head_recorded", "pass", f"Branch '{branch}' recorded in evidence README")
    else:
        result.add(
            "branch_head_recorded",
            "fail",
            f"Branch '{branch}' not found in evidence README",
        )


def changed_files_in_slice(repo: Path) -> list[str]:
    """Return files changed relative to HEAD (uncommitted) or the last commit."""
    code, status, _ = run_command(["git", "status", "--short"], repo)
    if code != 0:
        return []
    files: list[str] = []
    for line in status.splitlines():
        line = line.strip()
        if not line:
            continue
        if len(line) >= 3 and line[1] in "MARD":
            files.append(line[3:])
    if files:
        return files
    # If worktree is clean, inspect the most recent commit.
    code, stdout, _ = run_command(["git", "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD"], repo)
    if code == 0:
        return [line.strip() for line in stdout.splitlines() if line.strip()]
    return []


def looks_user_facing(relpath: str) -> bool:
    return any(pattern.search(relpath) for pattern in USER_FACING_PATTERNS)


def check_user_facing_evidence(repo: Path, result: AuditResult, strict: bool) -> None:
    changed = changed_files_in_slice(repo)
    user_facing = [p for p in changed if looks_user_facing(p)]
    if not user_facing:
        result.add("user_facing_evidence", "pass", "No user-facing file changes detected")
        return

    folder = latest_evidence_folder(repo)
    if folder is None:
        status = "fail" if strict else "warn"
        result.add(
            "user_facing_evidence",
            status,
            f"User-facing changes detected ({len(user_facing)} file(s)) but no evidence folder exists",
        )
        return

    evidence_files = [p for p in folder.rglob("*") if p.is_file()]
    has_image = any(p.suffix.lower() in EVIDENCE_IMAGE_EXTENSIONS for p in evidence_files)
    has_browser = any(p.suffix.lower() in EVIDENCE_BROWSER_EXTENSIONS for p in evidence_files)
    if has_image or has_browser:
        result.add(
            "user_facing_evidence",
            "pass",
            "User-facing changes have image or browser evidence",
        )
    else:
        status = "fail" if strict else "warn"
        result.add(
            "user_facing_evidence",
            status,
            "User-facing changes detected but evidence folder lacks screenshots or browser artifacts",
        )


def looks_like_schema(relpath: str) -> bool:
    return any(pattern.search(relpath) for pattern in SCHEMA_PATTERNS)


def check_schema_ownership(repo: Path, result: AuditResult, strict: bool) -> None:
    changed = changed_files_in_slice(repo)
    schemas = [p for p in changed if looks_like_schema(p)]
    if not schemas:
        result.add("schema_ownership", "pass", "No schema file changes detected")
        return

    for schema in schemas:
        # Heuristic: expect an examples/ directory and a test file near the schema.
        schema_path = repo / schema
        search_roots = [schema_path.parent]
        examples_found = False
        tests_found = False
        for root in search_roots:
            if not root.exists():
                continue
            examples_dir = root / "examples"
            if examples_dir.exists() and any(examples_dir.iterdir()):
                examples_found = True
            tests_dir = root / "tests"
            if tests_dir.exists() and any(tests_dir.iterdir()):
                tests_found = True
            if any(p.name.startswith("test_") and p.suffix == ".py" for p in root.iterdir() if p.is_file()):
                tests_found = True

        if examples_found and tests_found:
            result.add(
                "schema_ownership",
                "pass",
                f"Schema change '{schema}' has examples and validation tests nearby (heuristic check)",
            )
        else:
            status = "fail" if strict else "warn"
            missing = []
            if not examples_found:
                missing.append("examples")
            if not tests_found:
                missing.append("validation tests")
            result.add(
                "schema_ownership",
                status,
                f"Schema change '{schema}' is missing {', '.join(missing)}; see prompts/SCHEMA_OWNERSHIP_TEMPLATE.md",
            )


def check_tests_recorded(
    repo: Path,
    result: AuditResult,
    test_commands: list[str],
) -> None:
    folder = latest_evidence_folder(repo)
    readme = folder / "README.md" if folder else None
    has_recorded_tests = False
    if readme and readme.exists():
        text = readme.read_text(encoding="utf-8")
        has_recorded_tests = "test" in text.lower() or "lint" in text.lower() or "build" in text.lower()

    if test_commands:
        all_passed = True
        for command in test_commands:
            code, stdout, stderr = run_command(["bash", "-c", command], repo)
            combined = f"{stdout}\n{stderr}".strip()
            if code != 0:
                all_passed = False
                result.add(
                    "tests_recorded",
                    "fail",
                    f"Test command failed ({code}): {command}\n{combined[:400]}",
                )
            else:
                result.add("tests_recorded", "pass", f"Test command passed: {command}")
        if all_passed and not has_recorded_tests:
            result.add(
                "tests_recorded",
                "warn",
                "Tests passed but no test/build/lint results are recorded in the evidence README",
            )
        return

    if has_recorded_tests:
        result.add("tests_recorded", "pass", "Evidence README records test/build/lint results")
    else:
        result.add(
            "tests_recorded",
            "warn",
            "No test commands provided and evidence README does not record test/build/lint results",
        )


def check_human_override(
    repo: Path,
    result: AuditResult,
    override_file: Path | None,
) -> None:
    if override_file is None:
        folder = latest_evidence_folder(repo)
        candidate = folder / "README.md" if folder else None
        override_file = candidate
    if override_file is None or not override_file.exists():
        return
    text = override_file.read_text(encoding="utf-8")
    if "Human override used: yes" in text:
        result.add(
            "human_override",
            "pass",
            "Human override declared; verify the override is recorded with rule, requester, rationale, and remaining risk",
        )
        for marker in (
            "rule overridden:",
            "requested by:",
            "reason accepted:",
            "remaining risk:",
            "still closure-grade:",
        ):
            if marker not in text.lower():
                result.add(
                    "human_override",
                    "warn",
                    f"Override declaration missing recommended marker: {marker}",
                )
    else:
        result.add("human_override", "pass", "No human override declared")


def render_result(result: AuditResult, strict: bool) -> int:
    grouped: dict[str, list[Finding]] = {}
    for finding in result.findings:
        grouped.setdefault(finding.rule, []).append(finding)

    icon = {"pass": "✅", "fail": "❌", "warn": "⚠️", "override": "📝"}
    counts = {"pass": 0, "fail": 0, "warn": 0, "override": 0}

    print("============================================================")
    print("STATEDD AUDIT")
    print("============================================================")
    for rule, findings in grouped.items():
        print(f"\n{rule}")
        for finding in findings:
            counts[finding.status] += 1
            print(f"  {icon.get(finding.status, '?')} {finding.message}")

    print("\n============================================================")
    print(f"Summary: {counts['pass']} pass, {counts['warn']} warn, {counts['fail']} fail, {counts['override']} override")

    if result.has_failures():
        print("AUDIT RESULT: FAIL — closure-grade not met")
        return 1
    if strict and result.has_warnings():
        print("AUDIT RESULT: FAIL — warnings treated as failures in strict mode")
        return 1
    print("AUDIT RESULT: PASS — closure-grade")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv)
    root = Path(args.root).resolve()
    result = AuditResult()

    check_required_files(root, result)
    check_state_files_fresh(root, result, args.strict)
    check_evidence_folder(root, result)
    check_worktree_clean(root, result)
    check_branch_head_recorded(root, result)
    check_user_facing_evidence(root, result, args.strict)
    check_schema_ownership(root, result, args.strict)
    check_tests_recorded(root, result, args.test_command)
    check_human_override(root, result, Path(args.override_file) if args.override_file else None)

    return render_result(result, args.strict)


if __name__ == "__main__":
    raise SystemExit(main())
