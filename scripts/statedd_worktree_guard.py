#!/usr/bin/env python3
"""Pre-slice and closure guard for StateDD git worktree state.

Exit codes:
  0 = guard passed or classification template printed
  1 = guard found unsafe/ambiguous state for the requested mode
  2 = guard could not inspect the repository
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

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
        return fallback if fallback != "" else ""
    return stdout or fallback


def resolve_repo(path: Path) -> tuple[int, Path, str]:
    code, stdout, stderr = run_command(["git", "rev-parse", "--show-toplevel"], path)
    if code != 0:
        return 2, path.resolve(), stderr or "not a git repository"
    return 0, Path(stdout).resolve(), ""


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
    branch = git_value(repo, ["branch", "--show-current"], fallback="")
    if branch:
        return branch, False
    abbrev = git_value(repo, ["rev-parse", "--abbrev-ref", "HEAD"], fallback="not proven")
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
    local_head = git_value(repo, ["rev-parse", "HEAD"])
    origin_url = git_value(repo, ["remote", "get-url", "origin"])
    upstream_branch = git_value(repo, ["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"])
    upstream_head = "not proven"
    if upstream_branch != "not proven":
        upstream_head = git_value(repo, ["rev-parse", "@{u}"])
    default_branch = origin_default_branch(repo)
    same_name_origin_head = "not proven"
    if not detached and branch not in {"not proven", ""}:
        same_name_origin_head = git_value(repo, ["rev-parse", f"origin/{branch}"])
    worktree_porcelain = git_value(repo, ["worktree", "list", "--porcelain"], fallback="")
    status_porcelain = git_value(repo, ["status", "--porcelain=v1", "--untracked-files=all"], fallback="")
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


def shared_or_default_branch(ctx: GitContext) -> str:
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
    print(f"- repo root: {ctx.repo}")
    print(f"- current branch: {ctx.branch}")
    print(f"- local HEAD: {ctx.local_head}")
    print(f"- origin remote URL: {ctx.origin_url}")
    print(f"- upstream branch: {ctx.upstream_branch}")
    print(f"- upstream HEAD: {ctx.upstream_head}")
    print(f"- default branch: {ctx.default_branch}")
    print(f"- current branch is shared/default branch: {shared_or_default_branch(ctx)}")
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


def evaluate_start_slice(ctx: GitContext, classifications: dict[str, str]) -> tuple[bool, list[str], list[str]]:
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
        if shared_or_default_branch(ctx) == "yes":
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
        "--warn-only",
        action="store_true",
        help="Print unsafe state but exit 0; use only for diagnostics, not closure",
    )
    return parser.parse_args(argv[1:])


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv)
    code, repo, error = resolve_repo(Path(args.repo))
    if code != 0:
        print(f"StateDD Worktree Guard\nMode: {args.mode}\n\nBlocking problems\n- {error}")
        return code

    ctx = collect_context(repo)
    if args.mode == "classify-dirty":
        print_classification_template(ctx)
        return 0

    source = classification_source(repo, args.classification_file)
    classifications = parse_classification_file(source) if source and source.exists() else {}

    if args.mode == "start-slice":
        safe, warnings, problems = evaluate_start_slice(ctx, classifications)
    else:
        safe, warnings, problems = evaluate_closure(ctx)

    print_report(args.mode, ctx, classifications, source, safe, warnings, problems)
    if safe or args.warn_only:
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
