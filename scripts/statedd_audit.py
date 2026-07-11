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
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

from statedd_git_safety_session import sanitized_git_environment


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
RUNTIME_IDENTITY_FILE = "runtime_identity.json"
BROWSER_VERIFICATION_FILE = "browser_verification.json"
RUNTIME_IDENTITY_SCHEMA = "statedd.runtime_identity.v1"
EVIDENCE_MANIFEST_FILE = "manifest.json"
EVIDENCE_MANIFEST_SCHEMA = "statedd.evidence_manifest.v1"
BROWSER_VERIFICATION_SCHEMA = "statedd.browser_verification.v1"
VALID_BROWSER_PROVIDERS = {
    "kimi_webbridge",
    "playwright",
    "agent_native_browser",
    "existing_e2e",
    "manual_browser",
    "custom",
    "not_applicable",
}
VALID_REPO_ROLES = {"template_repository", "downstream_project"}
VALID_STATEDD_MODES = {"template-maintenance", "bootstrap", "operating"}
AGENT_CONTEXT_SCHEMA = "statedd.agent_context.v2"
AGENT_CONTEXT_FILE = Path(".statedd/agent.context")
CLASSIFIED_DIRT_CATEGORIES = {"intended_slice_work", "generated_artifact"}
ANTI_BRITTLENESS_MARKERS = [
    "What invariant prevents the failure class?",
    "typed/schema/state-machine/validator/contract-based",
    "Which behavior is centralized instead of scattered?",
    "Which observed examples are covered by general rules",
    "What adjacent cases were tested?",
    "What brittle pattern was explicitly avoided?",
    "why is that not the authority path?",
]


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
    command = ["git", "--no-optional-locks", *args[1:]] if args and args[0] == "git" else args
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            env=sanitized_git_environment(),
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


def read_optional(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8") if path.exists() else ""
    except UnicodeDecodeError:
        return ""


def extract_scalar(text: str, key: str) -> str | None:
    match = re.search(rf'^\s*{re.escape(key)}:\s*"?([^"\n#]+)"?\s*$', text, re.MULTILINE)
    return match.group(1).strip() if match else None


SHA_RE = re.compile(r"\b([0-9a-f]{7,40})\b", re.IGNORECASE)


def extract_sha_refs(text: str) -> set[str]:
    """Return all 7-40 character hex strings that look like git SHAs."""
    return set(SHA_RE.findall(text.lower()))


def is_ancestor(repo: Path, ancestor: str, descendant: str) -> bool:
    """Return True if ancestor is an ancestor of descendant in repo history."""
    code, _, _ = run_command(["git", "merge-base", "--is-ancestor", ancestor, descendant], repo)
    return code == 0


def has_proof_final_split(text: str) -> bool:
    """Return True if the evidence README declares a Proof head / Final PR head split."""
    lower = text.lower()
    return "proof head" in lower and ("final pr head" in lower or "final merge commit" in lower)


def repo_context(root: Path) -> tuple[str | None, str | None]:
    project_state = read_optional(root / "PROJECT_STATE.yaml")
    agents = read_optional(root / "AGENTS.md")
    role = extract_scalar(project_state, "repo_role") or extract_scalar(agents, "repo_role")
    mode = (
        extract_scalar(project_state, "statedd_mode")
        or extract_scalar(agents, "statedd_mode")
        or extract_scalar(project_state, "repo_mode")
        or extract_scalar(agents, "repo_mode")
    )
    return role, mode


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
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    if data.get("schema") != AGENT_CONTEXT_SCHEMA:
        return None
    return data


def agent_branch_base(repo: Path, context: dict) -> str | None:
    """Return the base commit for the agent branch from reservation ref or base_branch."""
    reservation_ref = context.get("reservation_ref")
    if reservation_ref:
        code, stdout, _ = run_command(["git", "rev-parse", reservation_ref], repo)
        if code == 0 and stdout:
            return stdout.strip()
    base_branch = context.get("base_branch")
    if base_branch:
        code, merge_base, _ = run_command(["git", "merge-base", "HEAD", base_branch], repo)
        if code == 0 and merge_base:
            return merge_base.strip()
    return None


def normalize_cell(cell: str) -> str:
    return cell.strip().strip("`").strip()


def parse_classification_file(path: Path) -> dict[str, str]:
    """Parse a markdown classification table into {path: category}."""
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return {}
    classifications: dict[str, str] = {}
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


def extract_status_path(line: str) -> str:
    """Extract the file path from a git status --short or --porcelain line."""
    # git status --short is two status characters, a space, then the path.
    stripped = line.rstrip("\n")
    if len(stripped) >= 3 and stripped[2] == " ":
        path = stripped[3:].strip()
        if stripped[0] == "R" and " -> " in path:
            path = path.split(" -> ", 1)[1]
        return path
    # Fallback for already-trimmed status lines (e.g. "M file.txt").
    if len(stripped) >= 2 and stripped[1] == " ":
        path = stripped[2:].strip()
        if stripped[0] == "R" and " -> " in path:
            path = path.split(" -> ", 1)[1]
        return path
    return stripped.strip()


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
    parser.add_argument(
        "--agent-context",
        default=None,
        help="Path to agent.context JSON (auto-detects .statedd/agent.context if omitted)",
    )
    parser.add_argument(
        "--evidence-folder",
        default=None,
        type=Path,
        help="Override the evidence folder used for audit checks",
    )
    return parser.parse_args(argv[1:])


def check_required_files(root: Path, result: AuditResult) -> None:
    for relpath in REQUIRED_STATE_FILES:
        path = root / relpath
        if path.exists():
            result.add("required_files", "pass", f"{relpath} exists")
        else:
            result.add("required_files", "fail", f"Missing required state file: {relpath}")


def check_repo_role_mode(root: Path, result: AuditResult) -> None:
    role, mode = repo_context(root)
    project_state = read_optional(root / "PROJECT_STATE.yaml")

    if role not in VALID_REPO_ROLES:
        result.add("repo_role_mode", "fail", f"Missing or invalid repo_role: {role or 'not proven'}")
        return
    result.add("repo_role_mode", "pass", f"repo_role: {role}")

    if mode not in VALID_STATEDD_MODES:
        result.add("repo_role_mode", "fail", f"Missing or invalid statedd_mode/repo_mode: {mode or 'not proven'}")
        return
    result.add("repo_role_mode", "pass", f"statedd_mode: {mode}")

    if role == "template_repository":
        if mode != "template-maintenance":
            result.add("repo_role_mode", "fail", "template_repository must use statedd_mode: template-maintenance")
        else:
            result.add("repo_role_mode", "pass", "Template repository uses template-maintenance mode")
        if "Your Project" in project_state:
            result.add("repo_role_mode", "fail", "Template-maintenance PROJECT_STATE.yaml still contains downstream placeholders")
        else:
            result.add("repo_role_mode", "pass", "Template-maintenance PROJECT_STATE.yaml has no downstream project placeholder")

    if role == "downstream_project":
        if mode == "template-maintenance":
            result.add("repo_role_mode", "fail", "downstream_project cannot use template-maintenance mode")
        elif mode == "bootstrap":
            result.add("repo_role_mode", "pass", "Downstream bootstrap mode may still contain unproven investigation fields")
        elif mode == "operating":
            for marker in ("system_investigated: false", "repo_investigated: false", "Your Project"):
                if marker in project_state:
                    result.add("repo_role_mode", "fail", f"Operating downstream PROJECT_STATE.yaml contains unresolved marker: {marker}")


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


def latest_evidence_folder(
    root: Path,
    agent_context: dict | None = None,
    explicit_folder: Path | None = None,
) -> Path | None:
    """Return the evidence folder to use for audit checks.

    Explicit --evidence-folder takes precedence. In agent context, prefer a
    folder whose manifest.json slice_id matches the current slice_id before
    falling back to the most recently modified folder.
    """
    if explicit_folder is not None:
        return explicit_folder if explicit_folder.exists() else None

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

    if agent_context and agent_context.get("slice_id"):
        slice_id = agent_context["slice_id"]
        for candidate in candidates:
            manifest = candidate / EVIDENCE_MANIFEST_FILE
            if not manifest.exists():
                continue
            try:
                data = json.loads(manifest.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                continue
            if isinstance(data, dict) and data.get("slice_id") == slice_id:
                return candidate

    return max(candidates, key=lambda p: p.stat().st_mtime)


def evidence_files(folder: Path) -> list[Path]:
    try:
        return [p for p in folder.rglob("*") if p.is_file()]
    except OSError:
        return []


def check_evidence_folder(
    root: Path,
    result: AuditResult,
    agent_context: dict | None = None,
    explicit_folder: Path | None = None,
) -> None:
    folder = latest_evidence_folder(root, agent_context=agent_context, explicit_folder=explicit_folder)
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

    files = evidence_files(folder)
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
    # Preserve leading whitespace so status columns remain aligned; skip blank lines.
    return True, [line.rstrip("\n") for line in status.splitlines() if line.strip()]


def git_branch_and_head(repo: Path) -> tuple[str, str]:
    branch = git_value(repo, ["rev-parse", "--abbrev-ref", "HEAD"])
    head = git_value(repo, ["rev-parse", "HEAD"])
    return branch, head


def check_worktree_clean(
    repo: Path,
    result: AuditResult,
    agent_context: dict | None = None,
    explicit_folder: Path | None = None,
) -> None:
    is_git_repo, changed = git_changed_files(repo)
    if not is_git_repo:
        result.add(
            "worktree_clean",
            "warn",
            "Not a git repository; cannot verify worktree cleanliness",
        )
        return
    if not changed:
        result.add("worktree_clean", "pass", "Worktree is clean")
        return

    if agent_context is not None:
        folder = latest_evidence_folder(repo, agent_context=agent_context, explicit_folder=explicit_folder)
        classifications: dict[str, str] = {}
        if folder is not None:
            readme = folder / "README.md"
            if readme.exists():
                classifications = parse_classification_file(readme)
        unclassified = [
            extract_status_path(line)
            for line in changed
            if classifications.get(extract_status_path(line)) not in CLASSIFIED_DIRT_CATEGORIES
        ]
        if not unclassified:
            result.add(
                "worktree_clean",
                "pass",
                f"Worktree is dirty with {len(changed)} file(s), all classified as intended slice work or generated artifact",
            )
        else:
            result.add(
                "worktree_clean",
                "fail",
                f"Unclassified dirty files in agent context: {', '.join(unclassified)}",
            )
        return

    result.add(
        "worktree_clean",
        "fail",
        f"Worktree is dirty ({len(changed)} changed file(s)); closure-grade requires clean worktree",
    )


def check_worktree_guard_available(repo: Path, result: AuditResult) -> None:
    guard = repo / "scripts" / "statedd_worktree_guard.py"
    if guard.exists():
        result.add(
            "worktree_guard",
            "pass",
            "scripts/statedd_worktree_guard.py available for pre-slice and closure worktree checks",
        )
    else:
        result.add(
            "worktree_guard",
            "warn",
            "scripts/statedd_worktree_guard.py not found; pre-slice worktree isolation guard unavailable",
        )


def check_branch_head_recorded(
    repo: Path,
    result: AuditResult,
    strict: bool,
    agent_context: dict | None = None,
    explicit_folder: Path | None = None,
) -> None:
    branch, head = git_branch_and_head(repo)
    folder = latest_evidence_folder(repo, agent_context=agent_context, explicit_folder=explicit_folder)
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
    recorded_heads = extract_sha_refs(text)
    head_match = head in recorded_heads or head[:7] in recorded_heads
    if head_match:
        result.add("branch_head_recorded", "pass", f"HEAD {head[:7]} recorded in evidence README")
    elif has_proof_final_split(text):
        # Accept a declared proof/final split if at least one recorded head is an
        # ancestor of the current HEAD. This keeps evidence honest while allowing
        # the evidence commit itself to follow the proof commit.
        if any(is_ancestor(repo, h, head) or h.startswith(head[:7]) or head.startswith(h[:7]) for h in recorded_heads if len(h) >= 7):
            result.add(
                "branch_head_recorded",
                "pass",
                f"HEAD {head[:7]} not recorded directly, but evidence README declares a Proof/Final head split with an ancestor commit",
            )
        else:
            status = "fail" if strict else "warn"
            result.add(
                "branch_head_recorded",
                status,
                f"Evidence README declares a Proof/Final head split, but none of the recorded heads are ancestors of {head[:7]}",
            )
    else:
        status = "fail" if strict else "warn"
        result.add(
            "branch_head_recorded",
            status,
            f"HEAD {head[:7]} not found in evidence README; record current HEAD or a Proof head/Final PR head split before closure",
        )
    if branch in text:
        result.add("branch_head_recorded", "pass", f"Branch '{branch}' recorded in evidence README")
    else:
        status = "fail" if strict else "warn"
        result.add(
            "branch_head_recorded",
            status,
            f"Branch '{branch}' not found in evidence README",
        )


def changed_files_in_slice(repo: Path, agent_context: dict | None = None) -> list[str]:
    """Return files changed in the current slice.

    If the worktree is dirty, return the uncommitted files. If the worktree is
    clean, return the files on the current branch since it diverged from the
    default branch (e.g. origin/main). If no default branch can be determined,
    return an empty list rather than guessing from the last commit.

    In agent context, the agent branch base (from the reservation ref or
    base_branch merge-base) is used as the diff base so that both committed and
    uncommitted slice work is captured.
    """
    code, status, _ = run_command(["git", "status", "--short"], repo)
    if code != 0:
        return []
    files: list[str] = []
    for line in status.splitlines():
        line = line.strip()
        if not line:
            continue
        # Porcelain status is two characters followed by a space; the path starts
        # at column 3. Rename lines look like "R  old -> new".
        if len(line) >= 3 and line[1] in "MARD":
            path_part = line[3:]
            if line[0] == "R" and " -> " in path_part:
                path_part = path_part.split(" -> ", 1)[1]
            files.append(path_part)

    if agent_context is not None:
        base_commit = agent_branch_base(repo, agent_context)
        if base_commit:
            code, stdout, _ = run_command(["git", "diff", "--name-only", base_commit], repo)
            if code == 0:
                slice_files = set(files)
                slice_files.update(line.strip() for line in stdout.splitlines() if line.strip())
                return sorted(slice_files)
        # If no agent base found, fall through to default behavior.

    if files:
        return files

    # Worktree is clean; diff against the merge-base with the default branch.
    code, default_branch, _ = run_command(["git", "rev-parse", "--abbrev-ref", "origin/HEAD"], repo)
    if code != 0 or not default_branch:
        return []
    base = default_branch.strip()
    code, merge_base, _ = run_command(["git", "merge-base", "HEAD", base], repo)
    if code != 0 or not merge_base:
        return []
    code, stdout, _ = run_command(["git", "diff", "--name-only", f"{merge_base.strip()}..HEAD"], repo)
    if code == 0:
        return [line.strip() for line in stdout.splitlines() if line.strip()]
    return []


def looks_user_facing(relpath: str) -> bool:
    return any(pattern.search(relpath) for pattern in USER_FACING_PATTERNS)


def check_user_facing_evidence(
    repo: Path,
    result: AuditResult,
    strict: bool,
    agent_context: dict | None = None,
    explicit_folder: Path | None = None,
) -> None:
    changed = changed_files_in_slice(repo, agent_context=agent_context)
    user_facing = [p for p in changed if looks_user_facing(p)]
    if not user_facing:
        result.add("user_facing_evidence", "pass", "No user-facing file changes detected")
        return

    folder = latest_evidence_folder(repo, agent_context=agent_context, explicit_folder=explicit_folder)
    if folder is None:
        status = "fail" if strict else "warn"
        result.add(
            "user_facing_evidence",
            status,
            f"User-facing changes detected ({len(user_facing)} file(s)) but no evidence folder exists",
        )
        return

    files = evidence_files(folder)
    has_image = any(p.suffix.lower() in EVIDENCE_IMAGE_EXTENSIONS for p in files)
    has_browser = any(
        p.suffix.lower() in EVIDENCE_BROWSER_EXTENSIONS
        and p.name != RUNTIME_IDENTITY_FILE
        and p.name != BROWSER_VERIFICATION_FILE
        for p in files
    )
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


def evidence_readme_claims_runtime_identity(folder: Path) -> bool:
    readme = folder / "README.md"
    if not readme.exists():
        return False
    text = read_optional(readme).lower()
    return any(marker in text for marker in ("runtime identity", "runtime proof", RUNTIME_IDENTITY_FILE))


def evidence_has_visual_or_browser_artifact(folder: Path) -> bool:
    files = evidence_files(folder)
    return any(
        p.suffix.lower() in EVIDENCE_IMAGE_EXTENSIONS
        or (
            p.suffix.lower() in EVIDENCE_BROWSER_EXTENSIONS
            and p.name != RUNTIME_IDENTITY_FILE
            and p.name != EVIDENCE_MANIFEST_FILE
            and p.name != BROWSER_VERIFICATION_FILE
        )
        for p in files
    )


def check_runtime_identity(
    repo: Path,
    result: AuditResult,
    strict: bool,
    agent_context: dict | None = None,
    explicit_folder: Path | None = None,
) -> None:
    folder = latest_evidence_folder(repo, agent_context=agent_context, explicit_folder=explicit_folder)
    if folder is None:
        result.add("runtime_identity", "warn", "Cannot inspect runtime_identity.json without an evidence folder")
        return

    artifact = folder / RUNTIME_IDENTITY_FILE
    claims_runtime = evidence_readme_claims_runtime_identity(folder)
    user_facing_changed = any(
        looks_user_facing(p) for p in changed_files_in_slice(repo, agent_context=agent_context)
    )
    visual_or_browser_evidence = evidence_has_visual_or_browser_artifact(folder)
    runtime_required = claims_runtime or user_facing_changed or visual_or_browser_evidence

    if not artifact.exists():
        if runtime_required:
            status = "fail" if strict else "warn"
            result.add(
                "runtime_identity",
                status,
                f"Runtime proof appears required but {artifact.relative_to(repo)} is missing",
            )
        else:
            result.add("runtime_identity", "pass", "No runtime_identity.json found and no runtime proof requirement detected")
        return

    try:
        data = json.loads(artifact.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        status = "fail" if strict else "warn"
        result.add("runtime_identity", status, f"Malformed runtime_identity.json: {exc}")
        return

    schema = data.get("schema") if isinstance(data, dict) else None
    if schema != RUNTIME_IDENTITY_SCHEMA:
        status = "fail" if strict else "warn"
        result.add(
            "runtime_identity",
            status,
            f"runtime_identity.json schema is {schema or 'missing'}; expected {RUNTIME_IDENTITY_SCHEMA}",
        )
    else:
        result.add("runtime_identity", "pass", f"runtime_identity.json schema: {schema}")

    runtime = data.get("runtime") if isinstance(data, dict) else None
    if not isinstance(runtime, dict):
        status = "fail" if strict else "warn"
        result.add("runtime_identity", status, "runtime_identity.json missing runtime object")
        return

    required = runtime.get("required")
    if required is False:
        if user_facing_changed or visual_or_browser_evidence:
            status = "fail" if strict else "warn"
            result.add(
                "runtime_identity",
                status,
                "runtime.required=false but user-facing changes or visual/browser evidence indicate runtime proof is required",
            )
        else:
            result.add("runtime_identity", "pass", "Runtime marked not required for this evidence slice")
        return
    if required is not True:
        status = "fail" if strict else "warn"
        result.add("runtime_identity", status, "runtime.required is not true or false")
        return

    checks = data.get("checks") if isinstance(data, dict) else None
    endpoint_reachable = checks.get("endpoint_reachable") if isinstance(checks, dict) else None
    if endpoint_reachable is True:
        result.add("runtime_identity", "pass", "runtime.required=true and endpoint_reachable=true")
    else:
        status = "fail" if strict else "warn"
        result.add(
            "runtime_identity",
            status,
            f"runtime.required=true but endpoint_reachable is {endpoint_reachable if endpoint_reachable is not None else 'missing'}",
        )

    process = runtime.get("process")
    if isinstance(process, dict) and process.get("detected") is True:
        result.add("runtime_identity", "pass", "Process ownership recorded as detected")
    elif isinstance(process, dict):
        reason = process.get("reason") or "not proven"
        result.add("runtime_identity", "pass", f"Process ownership not proven/not applicable and recorded: {reason}")
    else:
        status = "fail" if strict else "warn"
        result.add("runtime_identity", status, "runtime.process is missing or malformed")


def looks_like_schema(relpath: str) -> bool:
    if relpath.startswith("schemas/examples/") or relpath.startswith("fixtures/"):
        return False
    if Path(relpath).name in {"statedd_validate_schema.py", "test_schema_validation.py"}:
        return False
    return any(pattern.search(relpath) for pattern in SCHEMA_PATTERNS)


def check_schema_ownership(
    repo: Path,
    result: AuditResult,
    strict: bool,
    agent_context: dict | None = None,
) -> None:
    changed = changed_files_in_slice(repo, agent_context=agent_context)
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
    agent_context: dict | None = None,
    explicit_folder: Path | None = None,
) -> None:
    folder = latest_evidence_folder(repo, agent_context=agent_context, explicit_folder=explicit_folder)
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


def check_schema_validation(repo: Path, result: AuditResult) -> None:
    script = repo / "scripts" / "statedd_validate_schema.py"
    if not script.exists():
        result.add("schema_validation", "fail", "Missing schema validator: scripts/statedd_validate_schema.py")
        return
    code, stdout, stderr = run_command([sys.executable, str(script), str(repo), "--quiet"], repo)
    if code == 0:
        result.add("schema_validation", "pass", "StateDD schema validation passed")
        return
    combined = f"{stdout}\n{stderr}".strip()
    result.add(
        "schema_validation",
        "fail",
        f"StateDD schema validation failed ({code}): {combined[:600]}",
    )


def check_evidence_manifest(
    repo: Path,
    result: AuditResult,
    strict: bool,
    agent_context: dict | None = None,
    explicit_folder: Path | None = None,
) -> None:
    folder = latest_evidence_folder(repo, agent_context=agent_context, explicit_folder=explicit_folder)
    if folder is None:
        result.add("evidence_manifest", "warn", "Cannot inspect manifest.json without an evidence folder")
        return

    manifest = folder / EVIDENCE_MANIFEST_FILE
    if not manifest.exists():
        if strict:
            result.add(
                "evidence_manifest",
                "fail",
                f"Strict audit requires {EVIDENCE_MANIFEST_FILE} in the latest evidence folder",
            )
        else:
            result.add(
                "evidence_manifest",
                "pass",
                "No manifest.json in latest evidence folder; legacy evidence accepted in normal mode",
            )
        return

    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        status = "fail"
        result.add("evidence_manifest", status, f"Malformed {EVIDENCE_MANIFEST_FILE}: {exc}")
        return

    schema = data.get("schema") if isinstance(data, dict) else None
    if schema != EVIDENCE_MANIFEST_SCHEMA:
        status = "fail"
        result.add(
            "evidence_manifest",
            status,
            f"manifest.json schema is {schema or 'missing'}; expected {EVIDENCE_MANIFEST_SCHEMA}",
        )
        return
    result.add("evidence_manifest", "pass", f"manifest.json schema: {schema}")

    redaction = data.get("redaction") if isinstance(data, dict) else None
    if not isinstance(redaction, dict):
        status = "fail" if strict else "warn"
        result.add("evidence_manifest", status, "manifest.json missing redaction object")
        return

    redaction_status = redaction.get("status")
    if redaction_status == "unchecked":
        status = "fail" if strict else "warn"
        result.add("evidence_manifest", status, "manifest.json redaction status is unchecked")
    elif redaction_status in ("checked", "checked_with_limits", "override_used"):
        result.add("evidence_manifest", "pass", f"manifest.json redaction status: {redaction_status}")
    elif redaction_status == "manual_required":
        status = "fail" if strict else "warn"
        result.add("evidence_manifest", status, "manifest.json redaction requires manual review")
    else:
        status = "fail" if strict else "warn"
        result.add("evidence_manifest", status, f"manifest.json has unexpected redaction status: {redaction_status}")

    artifacts = data.get("artifacts") if isinstance(data, dict) else None
    if isinstance(artifacts, list):
        for artifact in artifacts:
            if not isinstance(artifact, dict):
                continue
            ref = artifact.get("path")
            status = artifact.get("redaction_status")
            kind = artifact.get("kind")
            if status in ("unchecked", "manual_required"):
                artifact_status = "fail" if strict else "warn"
                result.add(
                    "evidence_manifest",
                    artifact_status,
                    f"Artifact {ref} has redaction_status={status}",
                )
            if kind in ("screenshot",) and status not in ("checked", "checked_with_limits", "override_used"):
                artifact_status = "fail" if strict else "warn"
                result.add(
                    "evidence_manifest",
                    artifact_status,
                    f"Screenshot artifact {ref} requires explicit checked_with_limits or override",
                )

    claims = data.get("claims") if isinstance(data, dict) else None
    if isinstance(claims, list):
        for claim in claims:
            if not isinstance(claim, dict):
                continue
            evidence = claim.get("evidence")
            if not isinstance(evidence, list) or not evidence:
                claim_status = "fail" if strict else "warn"
                result.add(
                    "evidence_manifest",
                    claim_status,
                    f"Claim {claim.get('id')} has no evidence artifacts",
                )

    runtime_identity = data.get("runtime_identity") if isinstance(data, dict) else None
    if isinstance(runtime_identity, dict) and runtime_identity.get("required") is True:
        artifact = folder / RUNTIME_IDENTITY_FILE
        if not artifact.exists():
            status = "fail" if strict else "warn"
            result.add(
                "evidence_manifest",
                status,
                f"manifest.json runtime_identity.required=true but {RUNTIME_IDENTITY_FILE} is missing",
            )


def browser_verification_required(
    repo: Path,
    agent_context: dict | None = None,
    explicit_folder: Path | None = None,
) -> tuple[bool, str]:
    """Return (required, reason) for browser verification in the latest evidence folder."""
    folder = latest_evidence_folder(repo, agent_context=agent_context, explicit_folder=explicit_folder)
    if folder is None:
        return False, "no evidence folder"

    changed = changed_files_in_slice(repo, agent_context=agent_context)
    user_facing_changed = any(looks_user_facing(p) for p in changed)
    visual_or_browser_evidence = evidence_has_visual_or_browser_artifact(folder)
    if user_facing_changed:
        return True, "user-facing file changes detected"
    if visual_or_browser_evidence:
        return True, "visual or browser artifacts present in evidence folder"
    return False, "no user-facing changes or browser evidence"


def load_json_object(path: Path) -> dict | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def check_browser_verification(
    repo: Path,
    result: AuditResult,
    strict: bool,
    agent_context: dict | None = None,
    explicit_folder: Path | None = None,
) -> None:
    folder = latest_evidence_folder(repo, agent_context=agent_context, explicit_folder=explicit_folder)
    required, reason = browser_verification_required(repo, agent_context=agent_context, explicit_folder=explicit_folder)

    if folder is None:
        if required:
            status = "fail" if strict else "warn"
            result.add("browser_verification", status, f"Browser verification required ({reason}) but no evidence folder exists")
        else:
            result.add("browser_verification", "pass", "No evidence folder; browser verification not applicable")
        return

    artifact = folder / BROWSER_VERIFICATION_FILE
    if not artifact.exists():
        if required:
            status = "fail" if strict else "warn"
            result.add(
                "browser_verification",
                status,
                f"Browser verification required ({reason}) but {BROWSER_VERIFICATION_FILE} is missing",
            )
        else:
            result.add("browser_verification", "pass", "Browser verification not required for this slice")
        return

    data = load_json_object(artifact)
    if data is None:
        status = "fail" if strict else "warn"
        result.add("browser_verification", status, f"Malformed {BROWSER_VERIFICATION_FILE}")
        return

    schema = data.get("schema")
    if schema != BROWSER_VERIFICATION_SCHEMA:
        status = "fail" if strict else "warn"
        result.add(
            "browser_verification",
            status,
            f"{BROWSER_VERIFICATION_FILE} schema is {schema or 'missing'}; expected {BROWSER_VERIFICATION_SCHEMA}",
        )
    else:
        result.add("browser_verification", "pass", f"{BROWSER_VERIFICATION_FILE} schema: {schema}")

    provider = data.get("provider")
    if not isinstance(provider, dict):
        result.add("browser_verification", "fail", f"{BROWSER_VERIFICATION_FILE} missing provider object")
        return

    kind = provider.get("kind")
    if kind not in VALID_BROWSER_PROVIDERS:
        status = "fail" if strict else "warn"
        result.add(
            "browser_verification",
            status,
            f"Unrecognized browser verification provider.kind: {kind}",
        )
        return
    result.add("browser_verification", "pass", f"Browser verification provider: {kind}")

    if kind == "not_applicable":
        if required:
            status = "fail" if strict else "warn"
            result.add(
                "browser_verification",
                status,
                "provider.kind=not_applicable but user-facing changes or browser evidence indicate verification is required",
            )
        else:
            result.add("browser_verification", "pass", "Browser verification marked not applicable")
        return

    limits = data.get("limits") if isinstance(data, dict) else []
    if not isinstance(limits, list):
        limits = []

    if kind in ("manual_browser", "custom") and not limits:
        status = "fail" if strict else "warn"
        result.add(
            "browser_verification",
            status,
            f"provider.kind={kind} requires explicit known limits",
        )

    if kind == "custom" and (not provider.get("tool") or not provider.get("command")):
        status = "fail" if strict else "warn"
        result.add(
            "browser_verification",
            status,
            "provider.kind=custom requires both 'tool' and 'command'",
        )

    checks = data.get("checks") if isinstance(data, dict) else []
    if not isinstance(checks, list):
        result.add("browser_verification", "fail", "'checks' must be an array")
        checks = []

    artifacts = data.get("artifacts") if isinstance(data, dict) else []
    if not isinstance(artifacts, list):
        result.add("browser_verification", "fail", "'artifacts' must be an array")
        artifacts = []
    artifact_paths = {a.get("path") for a in artifacts if isinstance(a, dict)}

    if strict and not checks:
        result.add("browser_verification", "fail", "Strict audit requires at least one browser check")

    for check in checks:
        if not isinstance(check, dict):
            continue
        check_id = check.get("id", "unknown")
        evidence = check.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            result.add("browser_verification", "fail", f"Check {check_id} has no evidence artifacts")
            continue
        for ref in evidence:
            ref_path = folder / ref
            if not ref_path.exists():
                result.add("browser_verification", "fail", f"Check {check_id} references missing artifact: {ref}")
            if ref not in artifact_paths:
                result.add(
                    "browser_verification",
                    "warn",
                    f"Check {check_id} references artifact not listed in artifacts: {ref}",
                )

    runtime_identity = data.get("runtime_identity") if isinstance(data, dict) else {}
    if isinstance(runtime_identity, dict):
        runtime_path = folder / runtime_identity.get("path", RUNTIME_IDENTITY_FILE)
        if not runtime_path.exists():
            status = "fail" if strict else "warn"
            result.add(
                "browser_verification",
                status,
                f"Browser verification references missing {RUNTIME_IDENTITY_FILE}",
            )
        else:
            result.add("browser_verification", "pass", "Browser verification linked to runtime_identity.json")
    else:
        result.add("browser_verification", "fail", "Missing runtime_identity link in browser_verification.json")


def evidence_has_anti_brittleness_review(text: str) -> bool:
    if "Anti-Brittleness" not in text:
        return False
    return all(marker.lower() in text.lower() for marker in ANTI_BRITTLENESS_MARKERS)


def evidence_indicates_non_trivial_slice(text: str) -> bool:
    lowered = text.lower()
    if "non-trivial" in lowered or "nontrivial" in lowered:
        return True
    if re.search(r"^\s*-\s*type:\s*(feature|fix|refactor|ops)\b", text, re.MULTILINE | re.IGNORECASE):
        return True
    if re.search(r"^\s*type:\s*(feature|fix|refactor|ops)\b", text, re.MULTILINE | re.IGNORECASE):
        return True
    return False


def check_anti_brittleness_review(
    repo: Path,
    result: AuditResult,
    strict: bool,
    agent_context: dict | None = None,
    explicit_folder: Path | None = None,
) -> None:
    folder = latest_evidence_folder(repo, agent_context=agent_context, explicit_folder=explicit_folder)
    if folder is None:
        result.add("anti_brittleness_review", "warn", "Cannot inspect anti-brittleness review without an evidence folder")
        return
    readme = folder / "README.md"
    if not readme.exists():
        result.add("anti_brittleness_review", "warn", "Cannot inspect anti-brittleness review without an evidence README")
        return

    text = readme.read_text(encoding="utf-8")
    if evidence_has_anti_brittleness_review(text):
        result.add("anti_brittleness_review", "pass", "Evidence README contains anti-brittleness review markers")
        return

    if evidence_indicates_non_trivial_slice(text):
        status = "fail" if strict else "warn"
        result.add(
            "anti_brittleness_review",
            status,
            "Non-trivial slice evidence lacks anti-brittleness review markers",
        )
    else:
        result.add(
            "anti_brittleness_review",
            "pass",
            "Anti-brittleness review not required by latest evidence markers",
        )


def check_human_override(
    repo: Path,
    result: AuditResult,
    override_file: Path | None,
    agent_context: dict | None = None,
    explicit_folder: Path | None = None,
) -> None:
    if override_file is None:
        folder = latest_evidence_folder(repo, agent_context=agent_context, explicit_folder=explicit_folder)
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

    agent_context_path = find_agent_context(root, args.agent_context)
    agent_context = load_agent_context(agent_context_path) if agent_context_path else None
    explicit_folder = Path(args.evidence_folder).resolve() if args.evidence_folder else None

    check_required_files(root, result)
    check_repo_role_mode(root, result)
    check_state_files_fresh(root, result, args.strict)
    check_evidence_folder(root, result, agent_context, explicit_folder)
    check_worktree_clean(root, result, agent_context, explicit_folder)
    check_worktree_guard_available(root, result)
    check_branch_head_recorded(root, result, args.strict, agent_context, explicit_folder)
    check_user_facing_evidence(root, result, args.strict, agent_context, explicit_folder)
    check_runtime_identity(root, result, args.strict, agent_context, explicit_folder)
    check_schema_validation(root, result)
    check_schema_ownership(root, result, args.strict, agent_context)
    check_tests_recorded(root, result, args.test_command, agent_context, explicit_folder)
    check_evidence_manifest(root, result, args.strict, agent_context, explicit_folder)
    check_browser_verification(root, result, args.strict, agent_context, explicit_folder)
    check_anti_brittleness_review(root, result, args.strict, agent_context, explicit_folder)
    check_human_override(root, result, Path(args.override_file) if args.override_file else None, agent_context, explicit_folder)

    return render_result(result, args.strict)


if __name__ == "__main__":
    raise SystemExit(main())
