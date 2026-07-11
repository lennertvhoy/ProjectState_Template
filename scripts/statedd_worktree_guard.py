#!/usr/bin/env python3
"""Pre-slice and closure guard for StateDD git worktree state.

Exit codes:
  0 = guard passed or classification template printed
  1 = guard found unsafe/ambiguous state for the requested mode
  2 = guard could not inspect the repository
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from statedd_git_safety_session import sanitized_git_environment


ROOT = Path(__file__).resolve().parents[1]
GIT_SAFETY_SCRIPT = ROOT / "scripts" / "statedd_git_safety_check.py"

AGENT_CONTEXT_SCHEMA = "statedd.agent_context.v2"
AGENT_CONTEXT_PATH = ".statedd/agent.context"

VALID_CATEGORIES = {
    "intended_slice_work",
    "pre_existing_unrelated",
    "generated_artifact",
    "unknown_do_not_touch",
    "safe_to_discard_after_proof",
}


@dataclass(frozen=True)
class DirtyEntry:
    status: str
    path: str
    staged: bool
    unstaged: bool
    untracked: bool


@dataclass(frozen=True)
class GitContext:
    repo: Path
    branch: str
    detached: bool
    local_head: str
    origin_url: str
    upstream_branch: str
    upstream_head: str
    default_branch: str
    same_name_origin_head: str
    worktree_porcelain: str
    status_porcelain: str
    dirty_entries: list[DirtyEntry]


def run_command(args: list[str], cwd: Path) -> tuple[int, str, str]:
    try:
        completed = subprocess.run(
            args,
            cwd=cwd,
            env=sanitized_git_environment(),
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        return 127, "", str(exc)
    # Preserve leading spaces: `git status --porcelain` uses the first two
    # columns as staged/unstaged state. Stripping the whole output corrupts the
    # first entry and can also remove a leading dot from its path.
    return completed.returncode, completed.stdout.rstrip(), completed.stderr.rstrip()


def git_value(repo: Path, args: list[str], fallback: str = "not proven") -> str:
    code, stdout, stderr = run_command(["git", *args], repo)
    if code != 0:
        return fallback if fallback != "" else ""
    return stdout or fallback


def git_required(repo: Path, args: list[str]) -> str:
    code, stdout, stderr = run_command(["git", *args], repo)
    if code != 0:
        raise RuntimeError(
            f"required git {' '.join(args)} failed ({code}): {stderr or stdout or 'no diagnostic'}"
        )
    return stdout


def resolve_repo(path: Path) -> tuple[int, Path, str]:
    code, stdout, stderr = run_command(["git", "rev-parse", "--show-toplevel"], path)
    if code != 0:
        return 2, path.resolve(), stderr or "not a git repository"
    return 0, Path(stdout).resolve(), ""


def detect_git_locks(repo: Path) -> tuple[bool, str]:
    git_dir_str = git_value(repo, ["rev-parse", "--git-dir"], fallback="")
    common_dir_str = git_value(repo, ["rev-parse", "--git-common-dir"], fallback="")
    for directory_str in {git_dir_str, common_dir_str}:
        if not directory_str:
            continue
        directory = Path(directory_str)
        if not directory.is_absolute():
            directory = repo / directory
        directory = directory.resolve()
        for name in ("index.lock", "config.lock"):
            lock_path = directory / name
            if lock_path.exists():
                return False, f"Another git operation holds {lock_path}; use --wait or retry."
    return True, ""


def default_agent_context_path(repo: Path) -> Path:
    return repo / AGENT_CONTEXT_PATH


def load_agent_context(path: Path) -> dict | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    required_keys = {
        "schema",
        "agent_id",
        "slice_id",
        "reservation_ref",
        "worktree_path",
        "branch",
        "base_branch",
    }
    if not required_keys.issubset(data.keys()):
        return None
    if data.get("schema") != AGENT_CONTEXT_SCHEMA:
        return None
    if data.get("isolation_mode") not in {"clone", "worktree", "normal_branch"}:
        return None
    if data.get("isolation_mode") == "worktree":
        attestations = data.get("attestations")
        if not isinstance(attestations, dict):
            return None
        if attestations.get("worktree_opt_in") is not True:
            return None
        if attestations.get("trusted_local_machine") is not True:
            return None
    return data


def parse_status(status: str) -> list[DirtyEntry]:
    entries: list[DirtyEntry] = []
    for raw in status.splitlines():
        if not raw:
            continue
        code = raw[:2]
        path = raw[3:] if len(raw) > 3 else ""
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        untracked = code == "??"
        staged = code[0] not in {" ", "?"}
        unstaged = code[1] not in {" ", "?"}
        entries.append(
            DirtyEntry(
                status=code,
                path=path,
                staged=staged,
                unstaged=unstaged,
                untracked=untracked,
            )
        )
    return entries


def current_branch(repo: Path) -> tuple[str, bool]:
    branch = git_required(repo, ["branch", "--show-current"])
    if branch:
        return branch, False
    abbrev = git_required(repo, ["rev-parse", "--abbrev-ref", "HEAD"])
    if abbrev == "HEAD":
        return "not proven (detached HEAD)", True
    return abbrev, abbrev in {"not proven", ""}


def origin_default_branch(repo: Path) -> str:
    ref = git_value(repo, ["symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD"], fallback="")
    if ref.startswith("origin/"):
        return ref.removeprefix("origin/")
    return "not proven"


def collect_context(repo: Path) -> GitContext:
    branch, detached = current_branch(repo)
    local_head = git_required(repo, ["rev-parse", "HEAD"])
    origin_url = git_value(repo, ["remote", "get-url", "origin"])
    upstream_branch = git_value(repo, ["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"])
    upstream_head = "not proven"
    if upstream_branch != "not proven":
        upstream_head = git_value(repo, ["rev-parse", "@{u}"])
    default_branch = origin_default_branch(repo)
    same_name_origin_head = "not proven"
    if not detached and branch not in {"not proven", ""}:
        same_name_origin_head = git_value(repo, ["rev-parse", f"origin/{branch}"])
    worktree_porcelain = git_required(repo, ["worktree", "list", "--porcelain"])
    status_porcelain = git_required(
        repo,
        ["--no-optional-locks", "status", "--porcelain=v1", "--untracked-files=all"],
    )
    dirty_entries = parse_status(status_porcelain)
    return GitContext(
        repo=repo,
        branch=branch,
        detached=detached,
        local_head=local_head,
        origin_url=origin_url,
        upstream_branch=upstream_branch,
        upstream_head=upstream_head,
        default_branch=default_branch,
        same_name_origin_head=same_name_origin_head,
        worktree_porcelain=worktree_porcelain,
        status_porcelain=status_porcelain,
        dirty_entries=dirty_entries,
    )


def run_git_safety(
    repo: Path,
    isolation_mode: str,
    *,
    agent_context: dict | None,
    worktree_opt_in: bool,
    trusted_local_machine: bool,
    restart_session: bool,
) -> tuple[int, dict, str]:
    command = [
        sys.executable,
        str(GIT_SAFETY_SCRIPT),
        "--repo",
        str(repo),
        "--mode",
        isolation_mode,
        "--format",
        "json",
    ]
    if isolation_mode == "worktree":
        attestations = agent_context.get("attestations", {}) if agent_context else {}
        if worktree_opt_in or attestations.get("worktree_opt_in") is True:
            command.append("--worktree-opt-in")
        if trusted_local_machine or attestations.get("trusted_local_machine") is True:
            command.append("--trusted-local-machine")
    if isolation_mode == "clone" and agent_context and agent_context.get("source_repo"):
        command.extend(["--source-repo", str(agent_context["source_repo"])])
    if restart_session:
        command.append("--restart-session")
    code, stdout, stderr = run_command(command, repo)
    if not stdout:
        return code, {}, stderr or "Git safety preflight emitted no JSON report"
    try:
        report = json.loads(stdout)
    except json.JSONDecodeError as exc:
        return 2, {}, f"invalid Git safety JSON: {exc}"
    return code, report, stderr


def print_git_safety_failure(report: dict, fallback: str) -> None:
    print("StateDD Worktree Guard")
    print("Mode: start-slice")
    print()
    print("Git safety preflight")
    print(f"- effective mode: {report.get('decision', {}).get('effective_mode', 'read_only')}")
    print("- mutation permitted: no")
    print("- restart required: yes")
    print()
    print("Blocking problems")
    blockers = report.get("decision", {}).get("blockers", []) if report else []
    for blocker in blockers or [fallback or "Git safety preflight failed without a diagnostic"]:
        print(f"- {blocker}")


def latest_evidence_readme(repo: Path) -> Path | None:
    evidence_root = repo / "docs" / "evidence"
    if not evidence_root.exists():
        return None
    candidates = [
        entry / "README.md"
        for entry in evidence_root.iterdir()
        if entry.is_dir() and not entry.name.startswith(".") and (entry / "README.md").exists()
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda path: path.stat().st_mtime)


def normalize_cell(cell: str) -> str:
    return cell.strip().strip("`").strip()


def parse_classification_file(path: Path) -> dict[str, str]:
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
        path = ""
        category = ""
        if len(cells) >= 3 and cells[2] in VALID_CATEGORIES:
            path = cells[1]
            category = cells[2]
        elif len(cells) >= 2 and cells[1] in VALID_CATEGORIES:
            path = cells[0]
            category = cells[1]
        if path and category:
            classifications[path] = category
    return classifications


def classification_source(repo: Path, explicit: str | None) -> Path | None:
    if explicit:
        return Path(explicit).resolve()
    return latest_evidence_readme(repo)


def head_equals_upstream(ctx: GitContext) -> str:
    if ctx.upstream_head == "not proven" or ctx.local_head == "not proven":
        return "not proven"
    return "yes" if ctx.local_head == ctx.upstream_head else "no"


def shared_or_default_branch(ctx: GitContext, agent_context: dict | None = None) -> str:
    if agent_context is not None:
        return "no"
    if ctx.detached:
        return "not proven"
    if ctx.default_branch != "not proven" and ctx.branch == ctx.default_branch:
        return "yes"
    return "no"


def linked_worktree_paths(ctx: GitContext) -> list[str]:
    paths: list[str] = []
    for line in ctx.worktree_porcelain.splitlines():
        if not line.startswith("worktree "):
            continue
        path = line.removeprefix("worktree ").strip()
        if path and Path(path).resolve() != ctx.repo:
            paths.append(path)
    return paths


def print_classification_template(ctx: GitContext) -> None:
    print("## Worktree Dirty File Classification")
    print()
    print("| status | path | category | owner/notes |")
    print("| --- | --- | --- | --- |")
    if ctx.dirty_entries:
        for entry in ctx.dirty_entries:
            print(f"| {entry.status} | `{entry.path}` | unknown_do_not_touch | classify before edits |")
    else:
        print("| clean | not applicable | safe_to_discard_after_proof | no dirty files |")
    print()
    print("Valid categories:")
    for category in sorted(VALID_CATEGORIES):
        print(f"- {category}")


def print_report(
    mode: str,
    ctx: GitContext,
    classifications: dict[str, str],
    classification_file: Path | None,
    safe: bool,
    warnings: list[str],
    problems: list[str],
    agent_context: dict | None = None,
) -> None:
    dirty_paths = [entry.path for entry in ctx.dirty_entries]
    untracked = [entry.path for entry in ctx.dirty_entries if entry.untracked]
    staged = [entry.path for entry in ctx.dirty_entries if entry.staged]
    unstaged = [entry.path for entry in ctx.dirty_entries if entry.unstaged]
    linked = linked_worktree_paths(ctx)
    classified = "not applicable"
    if dirty_paths:
        classified = "yes" if all(path in classifications for path in dirty_paths) else "no"

    print("StateDD Worktree Guard")
    print(f"Mode: {mode}")
    print()
    print("Repo truth")
    if agent_context:
        print(f"- agent_id: {agent_context['agent_id']}")
        print(f"- slice_id: {agent_context['slice_id']}")
    print(f"- repo root: {ctx.repo}")
    print(f"- current branch: {ctx.branch}")
    print(f"- local HEAD: {ctx.local_head}")
    print(f"- origin remote URL: {ctx.origin_url}")
    print(f"- upstream branch: {ctx.upstream_branch}")
    print(f"- upstream HEAD: {ctx.upstream_head}")
    print(f"- default branch: {ctx.default_branch}")
    print(f"- current branch is shared/default branch: {shared_or_default_branch(ctx, agent_context)}")
    print(f"- local HEAD equals upstream: {head_equals_upstream(ctx)}")
    print(f"- safe to start: {'yes' if safe else 'no'}")
    print()
    print("Worktree topology")
    print("- worktree topology captured: yes")
    print(f"- current worktree path: {ctx.repo}")
    if linked:
        print("- linked worktrees:")
        for path in linked:
            print(f"  - {path}")
    else:
        print("- linked worktrees: none")
    print("- git worktree list --porcelain:")
    if ctx.worktree_porcelain:
        for line in ctx.worktree_porcelain.splitlines():
            print(f"  {line}")
    else:
        print("  not proven")
    print()
    print("Dirty state")
    print(f"- dirty files classified: {classified}")
    print(f"- classification file: {classification_file if classification_file else 'not found'}")
    print(f"- dirty file count: {len(dirty_paths)}")
    print(f"- staged file count: {len(staged)}")
    print(f"- unstaged file count: {len(unstaged)}")
    print(f"- untracked file count: {len(untracked)}")
    print("- dirty files:")
    if dirty_paths:
        for entry in ctx.dirty_entries:
            category = classifications.get(entry.path, "not classified")
            print(f"  - {entry.status} {entry.path} [{category}]")
    else:
        print("  - none")
    print("- untracked files:")
    if untracked:
        for path in untracked:
            print(f"  - {path}")
    else:
        print("  - none")
    print()
    print("Warnings")
    if warnings:
        for warning in warnings:
            print(f"- {warning}")
    else:
        print("- none")
    print()
    print("Blocking problems")
    if problems:
        for problem in problems:
            print(f"- {problem}")
    else:
        print("- none")


def evaluate_start_slice(
    ctx: GitContext,
    classifications: dict[str, str],
    classification_file: Path | None,
    agent_context: dict | None = None,
) -> tuple[bool, list[str], list[str]]:
    warnings: list[str] = []
    problems: list[str] = []

    if ctx.detached:
        problems.append("Detached HEAD is ambiguous for a non-trivial slice; create or switch to a branch first.")
    if ctx.origin_url == "not proven":
        warnings.append("origin remote URL is not proven; remote visibility cannot be checked yet.")
    if ctx.upstream_branch == "not proven":
        warnings.append("upstream branch is not proven; local HEAD versus upstream is not comparable yet.")

    dirty_paths = [entry.path for entry in ctx.dirty_entries]
    if dirty_paths:
        missing = [path for path in dirty_paths if path not in classifications]
        if missing:
            if agent_context is not None:
                warnings.append(
                    "Dirty files are expected slice work but are not yet classified; classification table is required."
                )
            else:
                problems.append(
                    "Dirty files are not fully classified; run --mode classify-dirty and record the table in evidence before edits."
                )
        else:
            do_not_touch = [
                path for path in dirty_paths
                if "do_not_touch" in classifications.get(path, "")
            ]
            if do_not_touch:
                problems.append(
                    f"Dirty files classified as do-not-touch cannot be part of a slice: {', '.join(do_not_touch)}"
                )
            else:
                warnings.append("Dirty files are classified; preserve category boundaries and do not touch unrelated dirt.")
        if shared_or_default_branch(ctx, agent_context) == "yes":
            warnings.append("Current branch is shared/default and dirty; prefer an isolated branch/worktree for non-trivial work.")

    return not problems, warnings, problems


def evaluate_closure(ctx: GitContext) -> tuple[bool, list[str], list[str]]:
    warnings: list[str] = []
    problems: list[str] = []
    if ctx.dirty_entries:
        problems.append("Closure mode requires a clean worktree.")
    if ctx.origin_url == "not proven":
        warnings.append("origin remote URL is not proven; remote truth still needs separate proof.")
    if ctx.upstream_branch == "not proven":
        warnings.append("upstream branch is not proven; pushed branch truth still needs separate proof.")
    return not problems, warnings, problems


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="StateDD worktree isolation guard")
    parser.add_argument("--repo", default=str(ROOT), help="Repo path to inspect")
    parser.add_argument(
        "--mode",
        required=True,
        choices=("start-slice", "classify-dirty", "closure"),
        help="Guard mode to run",
    )
    parser.add_argument(
        "--classification-file",
        help="Evidence README or markdown file containing a dirty-file classification table",
    )
    parser.add_argument(
        "--agent-context",
        help="Path to agent.context JSON file (default: .statedd/agent.context in repo root)",
    )
    parser.add_argument(
        "--isolation-mode",
        choices=("normal_branch", "worktree", "clone", "read_only"),
        default="normal_branch",
        help="Requested mutation/isolation mode when no agent context selects one",
    )
    parser.add_argument(
        "--worktree-opt-in",
        action="store_true",
        help="Explicitly opt into linked-worktree mode",
    )
    parser.add_argument("--trusted-local-machine", action="store_true")
    parser.add_argument("--restart-session", action="store_true")
    return parser.parse_args(argv[1:])


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv)
    code, repo, error = resolve_repo(Path(args.repo))
    if code != 0:
        print(f"StateDD Worktree Guard\nMode: {args.mode}\n\nBlocking problems\n- {error}")
        return code

    if args.mode in ("start-slice", "closure"):
        locks_ok, lock_msg = detect_git_locks(repo)
        if not locks_ok:
            print(f"StateDD Worktree Guard\nMode: {args.mode}\n\nBlocking problems\n- {lock_msg}")
            return 1

    try:
        ctx = collect_context(repo)
    except RuntimeError as exc:
        print(f"StateDD Worktree Guard\nMode: {args.mode}\n\nBlocking problems\n- {exc}")
        return 2
    if args.mode == "classify-dirty":
        print_classification_template(ctx)
        return 0

    agent_context = None
    if args.agent_context:
        agent_context = load_agent_context(Path(args.agent_context).resolve())
        if agent_context is None:
            print(
                f"StateDD Worktree Guard\nMode: {args.mode}\n\nBlocking problems\n"
                f"- Invalid or missing agent context file: {args.agent_context}"
            )
            return 1
    else:
        default_path = default_agent_context_path(repo)
        if default_path.exists():
            agent_context = load_agent_context(default_path)

    if args.mode == "start-slice":
        isolation_mode = (
            agent_context.get("isolation_mode", "worktree")
            if agent_context is not None
            else args.isolation_mode
        )
        safety_code, safety_report, safety_error = run_git_safety(
            repo,
            isolation_mode,
            agent_context=agent_context,
            worktree_opt_in=args.worktree_opt_in,
            trusted_local_machine=args.trusted_local_machine,
            restart_session=args.restart_session,
        )
        if safety_code != 0 or not safety_report.get("decision", {}).get("mutation_permitted"):
            print_git_safety_failure(safety_report, safety_error)
            return 1 if safety_code != 2 else 2

    source = classification_source(repo, args.classification_file)
    classifications = parse_classification_file(source) if source and source.exists() else {}

    if args.mode == "start-slice":
        safe, warnings, problems = evaluate_start_slice(ctx, classifications, source, agent_context)
    else:
        safe, warnings, problems = evaluate_closure(ctx)

    print_report(args.mode, ctx, classifications, source, safe, warnings, problems, agent_context)
    return 0 if safe else 1


if __name__ == "__main__":
    raise SystemExit(main())
