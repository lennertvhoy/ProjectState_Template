#!/usr/bin/env python3
"""Create a ProjectState project (`new`) or install the workflow into a repository (`adopt`).

Profiles: `core` (the default) and `hardened`. The v5 profiles live at tag v5-final.
SOURCE_DATE_EPOCH, when set, fixes the generated dates.
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import subprocess
import sys
import tempfile
from contextlib import contextmanager, suppress
from pathlib import Path, PureWindowsPath

try:
    from projectstate_release import GATE_PATH, MANAGED_PATH, gate_release, managed_block_text, render_managed_block
except ModuleNotFoundError:  # pragma: no cover - pytest package import path
    from scripts.projectstate_release import (
        GATE_PATH,
        MANAGED_PATH,
        gate_release,
        managed_block_text,
        render_managed_block,
    )


TEMPLATE_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_NAME = "ProjectState Template"
TEMPLATE_VERSION = "projectstate-template-v6"
PROFILES = ("core", "hardened")
LEGACY_PROFILES = ("minimal", "solo", "team", "regulated")
V5_TAG = "v5-final"
# Template files copied into a generated project, in copy order.
PROFILE_ASSETS = {"core": (GATE_PATH,), "hardened": (Path("HARDENED_POLICY.md"), GATE_PATH)}


class UnsafePathError(ValueError):
    """A requested path can escape its root or cross a symlink."""


def current_time() -> dt.datetime:
    """Return reproducible UTC time when SOURCE_DATE_EPOCH is configured."""
    raw = os.environ.get("SOURCE_DATE_EPOCH")
    if raw is None:
        return dt.datetime.now(dt.timezone.utc).astimezone()
    try:
        epoch = int(raw)
    except ValueError as exc:
        raise SystemExit("SOURCE_DATE_EPOCH must be an integer Unix timestamp") from exc
    return dt.datetime.fromtimestamp(epoch, tz=dt.timezone.utc)


# --- Path safety ------------------------------------------------------------------------------


def normalize_relpath(value: str | Path) -> Path:
    """Return a portable managed path or fail before any filesystem access."""
    raw = value.as_posix() if isinstance(value, Path) else value
    if not isinstance(raw, str) or not raw or "\x00" in raw:
        raise UnsafePathError(f"unsafe relative path: {value!r}")
    if "\\" in raw:
        raise UnsafePathError(f"managed paths must use POSIX separators: {raw!r}")
    if raw.startswith("/") or PureWindowsPath(raw).drive:
        raise UnsafePathError(f"absolute managed path is not allowed: {raw!r}")
    parts = raw.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise UnsafePathError(f"traversal or non-normalized managed path: {raw!r}")
    return Path(*parts)


def reject_symlinks(path: Path, label: str) -> None:
    """Refuse every existing symlink component of an absolute path, including the last one."""
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current = current / part
        if current.is_symlink():
            raise UnsafePathError(f"refusing symlink component in {label}: {current}")


def safe_root(value: str, *, must_exist: bool) -> Path:
    """Validate the requested target root and return its canonical path."""
    text = os.fspath(value)
    if os.name != "nt" and ("\\" in text or PureWindowsPath(text).drive):
        raise UnsafePathError(f"foreign Windows target root is not allowed: {value}")
    raw = Path(value)
    if ".." in raw.parts:
        raise UnsafePathError(f"target root traversal is not allowed: {value}")
    requested = Path(os.path.abspath(raw if raw.is_absolute() else Path.cwd() / raw))
    reject_symlinks(requested, "target root")
    canonical = requested.resolve(strict=False)
    if must_exist and not canonical.is_dir():
        raise UnsafePathError(f"target root is not an existing directory: {requested}")
    if canonical.exists() and not canonical.is_dir():
        raise UnsafePathError(f"target root is not a directory: {requested}")
    return canonical


def confined(root: Path, relpath: str | Path) -> Path:
    """root/relpath for a normalized relative path, refusing any existing symlink component."""
    candidate = root.resolve(strict=False) / normalize_relpath(relpath)
    reject_symlinks(candidate, "managed path")
    return candidate


def regular_source_path(root: Path, relpath: str | Path) -> Path:
    """A confined regular source file; source symlinks are never followed."""
    source = confined(root, relpath)
    if not source.is_file():
        raise UnsafePathError(f"source is not a regular file: {relpath}")
    return source


# --- Generated text -----------------------------------------------------------------------------


def render_managed_agents_block() -> str:
    """The template-owned AGENTS.md contract block, stamped with the template gate's release."""
    try:
        gate_text = regular_source_path(TEMPLATE_ROOT, GATE_PATH).read_text(encoding="utf-8")
        regular_source_path(TEMPLATE_ROOT, MANAGED_PATH)  # refuse a symlinked or non-regular block source
        block = managed_block_text(TEMPLATE_ROOT)
    except (UnsafePathError, OSError, UnicodeDecodeError) as exc:
        raise SystemExit(f"Cannot read the managed AGENTS.md contract sources: {exc}") from exc
    release = gate_release(gate_text)
    if release is None:
        raise SystemExit(
            f'{GATE_PATH.as_posix()} declares no RELEASE = "X.Y.Z"; refusing to generate AGENTS.md without a release'
        )
    return render_managed_block(release, block)


def render_outcome_agents_template(today: str, profile: str) -> str:
    """Frontmatter, the managed contract block, and two project-owned local sections.

    Opt-in workflows add nothing here until the owner selects one; their text lives under prompts/.
    """
    hardened_rule = (
        "This project uses the hardened profile. Read `HARDENED_POLICY.md` before release, security, or "
        "compliance work; its checks can add blockers but never override the primary journey.\n\n"
        if profile == "hardened"
        else ""
    )
    return f"""---
repo_role: downstream_project
projectstate_version: "{TEMPLATE_VERSION}"
profile: {profile}
initialized_on: {today}
last_updated: {today}
---

{render_managed_agents_block()}
## Local rules

{hardened_rule}<!-- Project-owned: domain rules, commands, and safety limits for this project. -->

## Owner directives

<!-- Standing instructions from the owner, one line each:
- 2026-10-06, until 2026-12-31: the directive.
Use "until revoked" for open-ended ones. Delete lines once they expire. -->
"""


def render_outcome_project(project_name: str, *, adopted: bool) -> str:
    scope_note = (
        "- Preserve observed existing behavior while the first vertical journey is established."
        if adopted
        else "- Establish the first vertical product journey without premature platform machinery."
    )
    return f"""# {project_name}

## User

Not yet defined — the human must confirm the primary user.

## Outcome

Not yet defined — the human must state the observable product outcome.

## Scope

{scope_note}
- Deliver one real user-visible slice at a time.

## Non-goals

- Workflow machinery that does not advance the current user journey.
- Treating automated checks as human acceptance.

## Durable constraints

- ProjectState coordination files are never application runtime dependencies.
- The human owns this file and the slice acceptance criteria.
- Unknown product or environment facts remain explicit until observed.
"""


def render_outcome_state(profile: str) -> str:
    return f"""# Canonical current truth. Keep exactly one active slice; history belongs in Git.
version: "{TEMPLATE_VERSION}"
profile: {profile}
project:
  outcome_ref: "PROJECT.md#outcome"
current_slice:
  id: bootstrap-001
  objective: "Define and prove the first real user journey."
  status: planned
  # Human-owned. Agents may report results but may not weaken these criteria.
  acceptance:
    - "The documented primary journey succeeds in a representative environment."
    - "The result is visible to the intended user and survives any restart named by the outcome."
  primary_journey:
    description: "Not yet defined — derive the smallest end-to-end user journey from PROJECT.md."
    command: "Not yet defined — record the exact human-authorized command."
    environment: "Not yet defined — record the representative environment."
    status: not_run
    evidence: "evidence/bootstrap-001/summary.md"
validation:
  primary_journey: not_run
  automated_tests: not_run
  human_acceptance: pending
delivery_boundary:
  name: first_user_journey
  failed_attempts: []
  simplification_review: null
blockers:
  - "Primary user and product outcome require human confirmation."
risks: []
next_action: "Confirm PROJECT.md, replace the placeholder journey, and run it before broad secondary checks."
"""


def render_outcome_evidence_summary() -> str:
    return """# Evidence: bootstrap-001

## Primary journey

- Environment: not recorded
- Command: not recorded
- Result: not run
- Exit code: not recorded

## Secondary checks

- Not run. Secondary checks cannot override the primary journey.

## Artifacts

- None recorded.

## Limitations

- Primary user and outcome still need human confirmation.
- Product validation and human acceptance are not proven.
"""


def render_outcome_readme(project_name: str, profile: str) -> str:
    overlay = (
        "This repo also uses the explicit `HARDENED_POLICY.md` overlay."
        if profile == "hardened"
        else "Hardened release or compliance controls are not enabled by default."
    )
    return f"""# {project_name}

This repository uses the ProjectState `{profile}` profile.

## Start

1. Read `AGENTS.md`, `PROJECT.md`, and `STATE.yaml`.
2. Confirm the user and observable outcome in `PROJECT.md`.
3. Replace the placeholder primary journey in `STATE.yaml`.
4. Run that real journey before broad secondary checks.
5. Record bounded evidence in `evidence/bootstrap-001/summary.md`.
6. Run `python3 scripts/projectstate_gate.py`.

The initial gate is expected to fail until the real journey is defined and
passed. That failure is truthful bootstrap state, not a setup defect. {overlay}

`RECORDED OUTCOME VALIDATED` means the records support validation; the gate does
not execute the journey or authenticate human approval.

ProjectState files coordinate work only. The application must start and run
without reading them.
"""


def render_readme_section(profile: str = "core") -> str:
    return f"""
## ProjectState workflow

This repo uses the ProjectState `{profile}` profile. The human-owned product
contract lives in `PROJECT.md`, the one current slice lives in `STATE.yaml`, and
its bounded proof lives under `evidence/<slice-id>/summary.md`. A failed primary
journey overrides passing secondary checks.
"""


def build_files(project_name: str, today: str, profile: str, *, adopt: bool) -> dict[str, str]:
    """The project-owned files a run writes; `adopt` leaves the repository's own README alone."""
    files = {
        "AGENTS.md": render_outcome_agents_template(today, profile),
        "PROJECT.md": render_outcome_project(project_name, adopted=adopt),
        "STATE.yaml": render_outcome_state(profile),
    }
    if not adopt:
        files["README.md"] = render_outcome_readme(project_name, profile)
    files["evidence/bootstrap-001/summary.md"] = render_outcome_evidence_summary()
    return files


# --- Writing --------------------------------------------------------------------------------------


def atomic_replace_bytes(path: Path, content: bytes, *, mode: int) -> None:
    """Replace one destination inode atomically without mutating hard-link peers."""
    descriptor, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(tmp_path, mode)
        os.replace(tmp_path, path)
        # Persist the directory entry where the platform permits directory fsync.
        with suppress(OSError):
            directory_fd = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
    finally:
        tmp_path.unlink(missing_ok=True)


def write_bytes(root: Path, relpath: str | Path, content: bytes, mode: int | None = None) -> None:
    """Atomically write one confined file; without `mode` an existing file keeps its own."""
    path = confined(root, relpath)
    path.parent.mkdir(parents=True, exist_ok=True)
    path = confined(root, relpath)  # the parents may have changed while they were created
    if path.is_dir():
        raise SystemExit(f"Refusing to replace directory with file: {relpath}")
    if mode is None:
        mode = path.stat().st_mode & 0o777 if path.exists() else 0o644
    atomic_replace_bytes(path, content, mode=mode)


def copy_asset(target: Path, relpath: Path) -> None:
    source = regular_source_path(TEMPLATE_ROOT, relpath)
    write_bytes(target, relpath, source.read_bytes(), mode=source.stat().st_mode & 0o777)


def preflight(target: Path, assets: list[Path], managed: list[Path]) -> None:
    """Check every source and destination before the first write."""
    for relpath in [*assets, *managed]:
        if relpath in assets:
            regular_source_path(TEMPLATE_ROOT, relpath)
        destination = confined(target, relpath)
        current = target
        for part in relpath.parts[:-1]:
            current = current / part
            if current.exists() and not current.is_dir():
                raise SystemExit(f"Refusing managed asset beneath non-directory destination parent: {current}")
        if destination.exists() and not destination.is_file():
            raise SystemExit(f"Refusing non-file destination for managed asset: {relpath}")


@contextmanager
def transaction(target: Path, relpaths: list[Path]):
    """Roll back every write if any step fails, removing the directories this run created."""
    target_existed = target.exists()
    snapshots: dict[Path, tuple[bytes, int] | None] = {}
    parent_existed: dict[Path, bool] = {}
    for relpath in sorted(set(relpaths), key=lambda path: path.as_posix()):
        destination = target / relpath
        snapshots[destination] = (
            (destination.read_bytes(), destination.stat().st_mode & 0o777) if os.path.lexists(destination) else None
        )
        for parent in relpath.parents:
            if parent != Path("."):
                parent_existed.setdefault(target / parent, (target / parent).exists())
    try:
        yield
    except BaseException:
        errors: list[str] = []
        for destination, snapshot in reversed(list(snapshots.items())):
            try:
                if snapshot is not None:
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    atomic_replace_bytes(destination, snapshot[0], mode=snapshot[1])
                elif destination.is_file() and not destination.is_symlink():
                    destination.unlink()
            except OSError as exc:
                errors.append(f"{destination}: {exc}")
        for directory, existed in sorted(parent_existed.items(), key=lambda item: len(item[0].parts), reverse=True):
            if not existed:
                with suppress(OSError):
                    directory.rmdir()
        if not target_existed:
            with suppress(OSError):
                target.rmdir()
        if errors:
            raise RuntimeError(f"initializer failed and rollback was incomplete: {errors}")
        raise


def initialize_fresh_git(target: Path) -> None:
    """Initialize a downstream repository on a fresh main branch."""
    if os.path.lexists(target / ".git"):
        raise SystemExit(
            "Refusing to initialize a new project over existing Git metadata. "
            "Use an empty target or the `adopt` command."
        )
    try:
        completed = subprocess.run(
            ["git", "init", "-b", "main"], cwd=target, capture_output=True, text=True, check=False
        )
    except FileNotFoundError as exc:
        raise SystemExit(f"Git is required to initialize a fresh downstream repository: {exc}") from exc
    if completed.returncode != 0:
        raise SystemExit(
            "Fresh Git initialization failed: "
            f"{completed.stderr.strip() or completed.stdout.strip() or 'unknown error'}"
        )


def preview(items: list[str]) -> str:
    return ", ".join(items[:8]) + (", ..." if len(items) > 8 else "")


def print_planned_writes(files: dict[str, str]) -> None:
    print("Planned managed-file writes:")
    for relpath in files:
        print(f"  - write {relpath}")


# --- The two commands ---------------------------------------------------------------------------


def run_new(args: argparse.Namespace, target: Path, assets: list[Path], files: dict[str, str]) -> None:
    managed = [Path(path) for path in files]
    preflight(target, assets, managed)
    if target != TEMPLATE_ROOT and target.is_relative_to(TEMPLATE_ROOT):
        raise SystemExit("Refusing to initialize into a nested path inside the template checkout.")
    occupied = target.exists() and any(target.iterdir())
    if occupied and not args.overwrite:
        raise SystemExit("Target exists and is not empty. Re-run with --overwrite or choose an empty directory.")
    if occupied and not args.force_overwrite:
        conflicts = sorted(relpath for relpath in [*assets, *managed] if os.path.lexists(target / relpath))
        if conflicts:
            raise SystemExit(
                "Target contains files that would be overwritten by the template: "
                f"{preview([str(path) for path in conflicts])}. Review/back up those files first, then re-run with "
                "--force-overwrite only if replacing them is intentional."
            )
    if args.dry_run:
        print_planned_writes(files)
        return
    with transaction(target, [*assets, *managed]):
        target.mkdir(parents=True, exist_ok=True)
        for relpath in assets:
            copy_asset(target, relpath)
        for relpath, content in files.items():
            write_bytes(target, relpath, content.encode("utf-8"))
    if args.init_git:
        initialize_fresh_git(target)


def run_adopt(args: argparse.Namespace, target: Path, assets: list[Path], files: dict[str, str]) -> None:
    managed = [Path(path) for path in files]
    readme = target / "README.md"
    if args.readme_link and readme.is_symlink():
        raise SystemExit("Refusing to append workflow section to symlinked README.md.")
    linked = [Path("README.md")] if args.readme_link else []
    preflight(target, assets, [*managed, *linked])
    existing = [relpath for relpath in [*assets, *managed] if os.path.lexists(target / relpath)]
    forced = args.overwrite and args.force_overwrite
    if existing and not forced:
        raise SystemExit(
            f"Adoption would overwrite existing workflow assets: {preview([str(path) for path in existing])}. "
            "Re-run with --overwrite --force-overwrite only if replacing them is intentional."
        )
    section = render_readme_section(args.profile).strip()
    link_text = None
    if args.readme_link and readme.exists():
        text = readme.read_text(encoding="utf-8")
        link_text = None if section in text else text.rstrip() + "\n\n" + section + "\n"
    if args.dry_run:
        print("Planned support-asset actions:")
        for relpath in assets:
            print(f"  - {'overwrite' if relpath in existing else 'create'} {relpath}")
        print_planned_writes(files)
        if link_text is not None:
            print("Planned README action:")
            print("  - append ProjectState workflow section to README.md")
        return
    with transaction(target, [*assets, *managed, *linked]):
        for relpath in assets:
            copy_asset(target, relpath)
        for relpath, content in files.items():
            write_bytes(target, relpath, content.encode("utf-8"))
        if link_text is not None:
            write_bytes(target, "README.md", link_text.encode("utf-8"))


# --- Command line ---------------------------------------------------------------------------------


def legacy_profile_message(profile: str) -> str:
    return (
        f"profile {profile!r} was a v5 profile and is not part of this template any more. "
        f"The v5 material lives at tag {V5_TAG}: git worktree add ../projectstate-v5 {V5_TAG}"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Initialize or adopt the ProjectState workflow")
    commands = parser.add_subparsers(dest="command", required=True)
    summaries = {"new": "Create a new repo from the template", "adopt": "Install the workflow into an existing repo"}
    for name, summary in summaries.items():
        command = commands.add_parser(name, help=summary)
        command.add_argument("--name", required=True, help="Project name to stamp into the workflow files")
        command.add_argument(
            "--target", default=".", help="Repo root to initialize" if name == "new" else "Existing repo root to adopt"
        )
        command.add_argument("--profile", default="core", help="Profile: core (default) or hardened")
        command.add_argument("--dry-run", action="store_true", help="Preview actions without writing files")
        command.add_argument(
            "--overwrite",
            action="store_true",
            help=(
                "Allow initialization into an existing non-empty target when no template-path collisions are present"
                if name == "new"
                else "Allow replacing existing workflow-managed files in the target"
            ),
        )
        command.add_argument(
            "--force-overwrite",
            action="store_true",
            help=(
                "Allow template files to replace conflicting files in an existing non-empty target"
                if name == "new"
                else "Actually replace conflicting workflow files when used with --overwrite"
            ),
        )
        if name == "new":
            command.add_argument("--minimal", action="store_true", help=argparse.SUPPRESS)  # refused: a v5 profile
            command.add_argument(
                "--init-git",
                action=argparse.BooleanOptionalAction,
                default=True,
                help="Initialize a fresh downstream Git repository on main (default: enabled)",
            )
        else:
            command.add_argument(
                "--readme-link",
                action="store_true",
                help="Append a short workflow section to the existing README instead of leaving it untouched",
            )
    return parser


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = build_parser()
    arguments = list(argv[1:])
    if arguments and arguments[0] not in {"-h", "--help", "new", "adopt"}:
        arguments.insert(0, "new")  # the legacy form without a subcommand creates a new project
    args = parser.parse_args(arguments)
    profile = "minimal" if getattr(args, "minimal", False) else args.profile
    if profile in LEGACY_PROFILES:
        parser.error(legacy_profile_message(profile))
    if profile not in PROFILES:
        parser.error(f"unknown profile {profile!r}; choose one of: {', '.join(PROFILES)}")
    args.profile = profile
    return args


def check_template_version() -> None:
    """The generated `version:` must be the template's own, before anything is written."""
    try:
        recorded = regular_source_path(TEMPLATE_ROOT, "VERSION").read_text(encoding="utf-8").strip()
    except (UnsafePathError, OSError, UnicodeDecodeError) as exc:
        raise SystemExit(f"Invalid ProjectState template VERSION source: {exc}") from exc
    if recorded != TEMPLATE_VERSION:
        raise SystemExit("ProjectState template version mismatch between scripts/init_template.py and VERSION")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv)
    if args.force_overwrite and not args.overwrite:
        raise SystemExit("--force-overwrite requires --overwrite.")
    check_template_version()
    today = current_time().date().isoformat()
    adopt = args.command == "adopt"
    try:
        target = safe_root(args.target, must_exist=adopt)
        if not adopt and target == TEMPLATE_ROOT:
            raise SystemExit(
                "Refusing to initialize into the template root itself. Choose a different target directory."
            )
        assets = list(PROFILE_ASSETS[args.profile])
        files = build_files(args.name, today, args.profile, adopt=adopt)
        (run_adopt if adopt else run_new)(args, target, assets, files)
    except UnsafePathError as exc:
        raise SystemExit(str(exc)) from exc
    if args.dry_run:
        print("Dry run complete.")
        return 0

    python = Path(sys.executable).name
    declared = len(assets) + len(files)
    if adopt:
        print(f"Adopted repo into the {TEMPLATE_NAME} workflow")
        print(f"Target: {target}")
        print(f"Profile: {args.profile} ({declared} declared assets)")
        print("README behavior: existing README preserved")
        if args.readme_link:
            print("README behavior: appended workflow section")
        print("Next:")
        print("1. Read AGENTS.md, PROJECT.md, and STATE.yaml against the real repo")
        print("2. Confirm the product outcome and define the smallest primary journey")
        print("3. Run the journey and record evidence/bootstrap-001/summary.md")
    else:
        print(f"Initialized {TEMPLATE_NAME} repo")
        print(f"Target: {target}")
        print(f"Profile: {args.profile} ({declared} declared assets)")
        if (target / ".git").is_dir():
            print("Fresh Git repository: main (template history was not inherited)")
        print("Next:")
        print("1. Read README.md and AGENTS.md")
        print("2. Confirm PROJECT.md and define the primary journey in STATE.yaml")
        print("3. Run the real journey and record evidence/bootstrap-001/summary.md")
    print(f"4. Run {python} scripts/projectstate_gate.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
