#!/usr/bin/env python3
"""Bring one ProjectState instance to the template's current release, mechanically.

The command replaces exactly two template-owned things in the target: the vendored
``scripts/projectstate_gate.py`` and the managed block in ``AGENTS.md``. It never
writes PROJECT.md, STATE.yaml, evidence/ or project-owned AGENTS.md text (STATE.yaml
is only read, for its version), and the only git it runs against a target is
read-only (``git status`` with optional locks off). Default mode is a dry run;
``--apply`` writes atomically; ``--check`` writes nothing and exits 1 when a change
is needed. Exit 2 means refused or invalid, with the reason. Any refusal means zero
writes, and the dry run exits 2 exactly when ``--apply`` with the same flags would refuse.

Source of truth is ``--template`` (default: this repository): its gate, its managed
block and ``releases/index.json``, read through ``projectstate_release``.

First conversion of an ``AGENTS.md`` without a managed block splits the file into
heading blocks, drops template-owned blocks whose text is a known released text
(``releases/contract-history.json``) and keeps every other block byte for byte
after the managed block. A template block that matches no known text is a modified
section: it is reported with a diff and only removed with --accept-modified-sections.

``--build-history`` is a maintenance mode for template maintainers. It regenerates
``releases/contract-history.json`` from the release tags and is the only mode that
runs git commands that write (temporary worktrees outside every repository).
"""

from __future__ import annotations

import argparse
import difflib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, NamedTuple

try:
    import projectstate_gate as gatelib
    import projectstate_release as rel
except ModuleNotFoundError:  # pragma: no cover - pytest package import path
    from scripts import projectstate_gate as gatelib
    from scripts import projectstate_release as rel


AGENTS_NAME = "AGENTS.md"
HISTORY_PATH = Path("releases") / "contract-history.json"
HISTORY_FORMAT = "projectstate-contract-history/1"
# Releases whose generated AGENTS.md carried the contract inline, before the managed block.
HISTORY_RELEASES = ("6.0.0", "6.0.1", "6.1.0", "6.2.0")
HISTORY_PROFILES = ("core", "hardened")
DIFF_LINES = 80
TEMPLATE_HEADINGS = frozenset({
    "projectstate outcome-first contract",
    "projectstate contract",
    "read order",
    "authority",
    "workflow",
    "core workflow",
    "continuation decision (separate from closure)",
    "optional persistent threads",
    "outcome precedence",
    "simplification and risk",
    "simplification rule",
    "closure",
    "risk stop-lines",
    "runtime and git boundaries",
    "profiles",
    "boundaries",
    "template repository note",
})
REFRESH_PREFIXES = ("required first action", "latest required refresh")
FENCE_OPEN = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
FENCE_CLOSE = re.compile(r"^ {0,3}(`{3,}|~{3,})[ \t]*$")
HEADING = re.compile(r"^ {0,3}(#{1,6})(?:[ \t]+(.*?))?[ \t]*$")
CLOSING_HASHES = re.compile(r"(?:^|[ \t]+)#+[ \t]*$")
NOTICE_START = re.compile(r"^[ \t]*<!--[ \t]*projectstate-([A-Za-z0-9][A-Za-z0-9_.-]*):start[ \t]*-->[ \t]*$")
NOTICE_END = re.compile(r"^[ \t]*<!--[ \t]*projectstate-([A-Za-z0-9][A-Za-z0-9_.-]*):end[ \t]*-->[ \t]*$")
TEMPLATE_ROLE = re.compile(r"^repo_role:[ \t]*template_repository[ \t]*$", re.MULTILINE)
GIT_LOCATION_VARIABLES = (
    "GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY", "GIT_COMMON_DIR", "GIT_NAMESPACE",
)
LOCAL_SCAFFOLD = """\
## Local rules

<!-- Project-owned: domain rules, commands, and safety limits for this project. -->

## Owner directives

<!-- Standing instructions from the owner, one line each:
- 2026-10-06, until 2026-12-31: the directive.
Use "until revoked" for open-ended ones. Delete lines once they expire. -->
"""


class UpdateRefused(Exception):
    """The update cannot proceed; nothing is written."""

    def __init__(self, reasons: list[str]) -> None:
        super().__init__("; ".join(reasons))
        self.reasons = reasons


class Template(NamedTuple):
    root: Path
    release: str
    index: dict[str, Any]
    gate_bytes: bytes
    gate_sha: str
    gate_mode: int
    block: str


class Block(NamedTuple):
    """One heading block of an AGENTS.md body; ``text`` is the exact source slice."""

    level: int
    heading: str
    title: str
    text: str
    owner: str


@dataclass
class GatePlan:
    action: str = "none"
    from_release: str | None = None
    releases: list[str] = field(default_factory=list)
    sha_before: str | None = None
    sha_after: str = ""
    data: bytes | None = None
    mode: int = 0o644
    diff: list[str] = field(default_factory=list)
    refusals: list[str] = field(default_factory=list)


@dataclass
class ContractPlan:
    action: str = "none"
    from_release: str | None = None
    text: str | None = None
    mode: int = 0o644
    removed_sections: list[dict[str, Any]] = field(default_factory=list)
    removed_notices: list[dict[str, Any]] = field(default_factory=list)
    modified_sections: list[dict[str, Any]] = field(default_factory=list)
    local_template_headings: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    diff: list[str] = field(default_factory=list)
    refusals: list[str] = field(default_factory=list)
    local_bytes: int = 0
    local_bytes_preserved: bool = True


@dataclass
class Plan:
    target: Path
    template: Template
    gate: GatePlan
    contract: ContractPlan

    @property
    def refusals(self) -> list[str]:
        return [*self.gate.refusals, *self.contract.refusals]

    @property
    def changed(self) -> bool:
        return self.gate.data is not None or self.contract.text is not None


# --- Markdown block splitting -------------------------------------------------------------


def split_lines(text: str) -> list[str]:
    """Split on LF only, keeping terminators, so that ``"".join(lines) == text``."""
    parts = text.split("\n")
    lines = [part + "\n" for part in parts[:-1]]
    if parts[-1]:
        lines.append(parts[-1])
    return lines


def normalize_block(text: str) -> str:
    """Comparison form: trailing spaces stripped per line, trailing blank lines dropped."""
    lines = [line.rstrip(" \t") for line in text.split("\n")]
    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines) + "\n" if lines else ""


def fence_mask(lines: list[str]) -> list[bool]:
    """True for every line inside a fenced code block, fence lines included."""
    mask: list[bool] = []
    fence: tuple[str, int] | None = None
    for line in lines:
        body = line.rstrip("\n")
        if fence is None:
            opened = FENCE_OPEN.match(body)
            if opened and not (opened.group(1)[0] == "`" and "`" in opened.group(2)):
                fence = (opened.group(1)[0], len(opened.group(1)))
                mask.append(True)
            else:
                mask.append(False)
            continue
        mask.append(True)
        closed = FENCE_CLOSE.match(body)
        if closed and closed.group(1)[0] == fence[0] and len(closed.group(1)) >= fence[1]:
            fence = None
    return mask


def parse_heading(line: str) -> tuple[int, str] | None:
    match = HEADING.match(line)
    if not match:
        return None
    title = CLOSING_HASHES.sub("", match.group(2) or "").strip()
    return len(match.group(1)), title


def find_headings(lines: list[str], mask: list[bool]) -> list[tuple[int, int, str]]:
    """ATX headings outside fenced code as (line index, level, title)."""
    found: list[tuple[int, int, str]] = []
    for index, line in enumerate(lines):
        parsed = None if mask[index] else parse_heading(line.rstrip("\n"))
        if parsed:
            found.append((index, parsed[0], parsed[1]))
    return found


def split_blocks(text: str) -> list[Block]:
    """Heading blocks (levels 1-3) with ownership; text before the first heading is local."""
    lines = split_lines(text)
    marks = [mark for mark in find_headings(lines, fence_mask(lines)) if mark[1] <= 3]
    blocks: list[Block] = []
    owner = "local"
    first = marks[0][0] if marks else len(lines)
    if first:
        blocks.append(Block(0, "", "", "".join(lines[:first]), owner))
    for position, (index, level, title) in enumerate(marks):
        end = marks[position + 1][0] if position + 1 < len(marks) else len(lines)
        heading = title.strip().lower()
        if level <= 2:
            owner = "template" if heading in TEMPLATE_HEADINGS else "local"
        blocks.append(Block(level, heading, title, "".join(lines[index:end]), owner))
    return blocks


def split_frontmatter(text: str) -> tuple[str, str]:
    """Leading YAML frontmatter (first line ``---`` through the next ``---`` line) and the rest."""
    lines = split_lines(text)
    if lines and lines[0].rstrip("\n") == "---":
        for index in range(1, len(lines)):
            if lines[index].rstrip("\n") == "---":
                return "".join(lines[: index + 1]), "".join(lines[index + 1 :])
    return "", text


def trim_leading_blank(text: str) -> str:
    lines = split_lines(text)
    while lines and not lines[0].strip():
        lines.pop(0)
    return "".join(lines)


# --- Refresh notices and refresh sections -------------------------------------------------


def find_notice_end(lines: list[str], mask: list[bool], name: str, after: int) -> int | None:
    for index in range(after + 1, len(lines)):
        if mask[index]:
            continue
        match = NOTICE_END.match(lines[index].rstrip("\n"))
        if match and match.group(1) == name:
            return index
    return None


def remove_notices(lines: list[str]) -> tuple[list[str], list[dict[str, Any]], list[str]]:
    """Drop ``<!-- projectstate-NAME:start/end -->`` blocks; unmatched markers stay and warn."""
    mask = fence_mask(lines)
    kept: list[str] = []
    removed: list[dict[str, Any]] = []
    warnings: list[str] = []
    index = 0
    while index < len(lines):
        start = None if mask[index] else NOTICE_START.match(lines[index].rstrip("\n"))
        if start is None:
            kept.append(lines[index])
            index += 1
            continue
        stop = find_notice_end(lines, mask, start.group(1), index)
        if stop is None:
            warnings.append(f"notice marker projectstate-{start.group(1)}:start has no matching end; left in place")
            kept.append(lines[index])
            index += 1
            continue
        removed.append({"name": start.group(1), "lines": stop - index + 1})
        index = stop + 1
        if not kept or not kept[-1].strip():
            while index < len(lines) and not lines[index].strip():
                index += 1
    return kept, removed, warnings


def remove_refresh_sections(lines: list[str]) -> tuple[list[str], list[dict[str, Any]]]:
    """Drop whole sections whose heading starts with a refresh prefix (to the next heading of equal or higher rank)."""
    headings = find_headings(lines, fence_mask(lines))
    drop = [False] * len(lines)
    removed: list[dict[str, Any]] = []
    for position, (index, level, title) in enumerate(headings):
        if drop[index] or not title.strip().lower().startswith(REFRESH_PREFIXES):
            continue
        end = next((later for later, depth, _ in headings[position + 1 :] if depth <= level), len(lines))
        for covered in range(index, end):
            drop[covered] = True
        removed.append({"heading": title, "level": level, "kind": "refresh", "lines": end - index})
    return [line for line, dropped in zip(lines, drop) if not dropped], removed


class Cleaned(NamedTuple):
    text: str
    notices: list[dict[str, Any]]
    sections: list[dict[str, Any]]
    warnings: list[str]


def clean_refresh(text: str) -> Cleaned:
    lines, notices, warnings = remove_notices(split_lines(text))
    lines, sections = remove_refresh_sections(lines)
    return Cleaned("".join(lines), notices, sections, warnings)


# --- Known texts ---------------------------------------------------------------------------


def load_history(root: Path) -> dict[str, list[dict[str, Any]]]:
    path = root / HISTORY_PATH
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise UpdateRefused([f"cannot read {HISTORY_PATH.as_posix()} (needed to convert AGENTS.md): {exc}"]) from exc
    headings = payload.get("headings") if isinstance(payload, dict) else None
    valid = isinstance(headings, dict) and payload.get("format") == HISTORY_FORMAT
    if valid:
        for entries in headings.values():
            valid = valid and isinstance(entries, list) and all(
                isinstance(entry, dict) and isinstance(entry.get("text"), str)
                and isinstance(entry.get("releases"), list) for entry in entries)
    if not valid:
        raise UpdateRefused([f"{HISTORY_PATH.as_posix()} is not a {HISTORY_FORMAT} document"])
    return headings


def known_releases(history: dict[str, list[dict[str, Any]]], heading: str, normalized: str) -> list[str] | None:
    for entry in history.get(heading, []):
        if normalize_block(entry["text"]) == normalized:
            return [str(release) for release in entry["releases"]]
    return None


def closest_known(history: dict[str, list[dict[str, Any]]], heading: str, normalized: str) -> dict[str, Any] | None:
    """The known text for ``heading`` most similar to ``normalized`` (later releases win ties)."""
    best: dict[str, Any] | None = None
    best_ratio = -1.0
    for entry in history.get(heading, []):
        ratio = difflib.SequenceMatcher(
            None, normalize_block(entry["text"]).splitlines(), normalized.splitlines(), autojunk=False).ratio()
        if ratio >= best_ratio:
            best, best_ratio = entry, ratio
    return best


def unified(old: str, new: str, old_label: str, new_label: str) -> list[str]:
    lines = list(difflib.unified_diff(old.splitlines(), new.splitlines(), old_label, new_label, lineterm=""))
    if len(lines) > DIFF_LINES:
        lines = [*lines[:DIFF_LINES], f"... {len(lines) - DIFF_LINES} more diff lines not shown"]
    return lines


# --- Template and target preflight ---------------------------------------------------------


def load_template(root: Path) -> Template:
    gate_path = root / rel.GATE_PATH
    try:
        index = rel.load_index(root)
        gate_bytes = gate_path.read_bytes()
        gate_mode = stat.S_IMODE(gate_path.stat().st_mode)
        block = rel.managed_block_text(root)
    except (OSError, ValueError) as exc:
        raise UpdateRefused([f"template {root} is unusable: {exc}"]) from exc
    release = rel.gate_release(gate_bytes.decode("utf-8", errors="replace"))
    if release is None:
        raise UpdateRefused([f"template gate {rel.GATE_PATH.as_posix()} declares no RELEASE"])
    if release != index.get("latest"):
        raise UpdateRefused([
            f"template gate release {release} does not equal the index latest {index.get('latest')!r}; "
            "fix the template before updating instances"])
    if not isinstance(index.get("state_schema"), str) or not index["state_schema"]:
        raise UpdateRefused(["release index has no state_schema"])
    try:
        rel.render_managed_block(release, block)
    except ValueError as exc:
        raise UpdateRefused([f"template managed block is unusable: {exc}"]) from exc
    return Template(root, release, index, gate_bytes, rel.sha256_bytes(gate_bytes), gate_mode, block)


def check_state(target: Path, schema: str) -> None:
    state_path = target / "STATE.yaml"
    if not state_path.is_file():
        raise UpdateRefused([f"STATE.yaml is missing in {target}; this is not a {schema} instance"])
    try:
        version = gatelib.parse_state(state_path.read_text(encoding="utf-8")).get("version")
    except (OSError, UnicodeDecodeError, gatelib.StateSyntaxError) as exc:
        raise UpdateRefused([f"cannot read STATE.yaml: {exc}"]) from exc
    if version != schema:
        raise UpdateRefused([
            f"STATE.yaml version is {version!r}, not {schema!r}; only {schema} instances are updated mechanically"])


def check_paths(target: Path) -> None:
    """Refuse symlinks on the two files this command writes and on the directory between them and the target."""
    scripts = target / "scripts"
    for path in (target / AGENTS_NAME, scripts, target / rel.GATE_PATH):
        if os.path.islink(path):
            raise UpdateRefused([f"{path.relative_to(target).as_posix()} is a symlink; refusing to write through it"])
    if os.path.lexists(scripts) and not scripts.is_dir():
        raise UpdateRefused(["scripts exists but is not a directory"])


def git_env() -> dict[str, str]:
    env = {key: value for key, value in os.environ.items() if key not in GIT_LOCATION_VARIABLES}
    env["GIT_OPTIONAL_LOCKS"] = "0"
    return env


def check_clean(target: Path) -> None:
    """Refuse when git reports changes to AGENTS.md or the gate; read-only git only."""
    try:
        inside = subprocess.run(
            ["git", "-C", str(target), "rev-parse", "--is-inside-work-tree"],
            capture_output=True, text=True, check=False, env=git_env())
    except OSError:
        return
    if inside.returncode != 0:
        if "not a git repository" in inside.stderr:
            return
        raise UpdateRefused([f"cannot inspect git status ({inside.stderr.strip()}); use --allow-dirty to skip the check"])
    if inside.stdout.strip() != "true":
        return
    status = subprocess.run(
        ["git", "-C", str(target), "status", "--porcelain", "--", AGENTS_NAME, rel.GATE_PATH.as_posix()],
        capture_output=True, text=True, check=False, env=git_env())
    if status.returncode != 0:
        raise UpdateRefused([f"git status failed ({status.stderr.strip()}); use --allow-dirty to skip the check"])
    dirty = [line.strip() for line in status.stdout.splitlines() if line.strip()]
    if dirty:
        raise UpdateRefused([
            f"uncommitted changes in {AGENTS_NAME} or {rel.GATE_PATH.as_posix()} ({'; '.join(dirty)}); "
            "commit or stash them first, or pass --allow-dirty"])


def preflight(target_arg: str, template: Template, allow_dirty: bool) -> Path:
    target = Path(target_arg)
    if not target.is_dir():
        raise UpdateRefused([f"target is not a directory: {target_arg}"])
    resolved = target.resolve()
    if resolved in (template.root, rel.TEMPLATE_ROOT):
        raise UpdateRefused(["target is the template repository itself; update instances, not the template"])
    check_state(resolved, str(template.index["state_schema"]))
    check_paths(resolved)
    if not allow_dirty:
        check_clean(resolved)
    return resolved


# --- Planning ------------------------------------------------------------------------------


def read_target_file(path: Path) -> bytes:
    if not path.is_file():
        raise UpdateRefused([f"{path.name} exists but is not a regular file"])
    try:
        return path.read_bytes()
    except OSError as exc:
        raise UpdateRefused([f"cannot read {path}: {exc}"]) from exc


def plan_gate(target: Path, template: Template, replace_edited: bool) -> GatePlan:
    path = target / rel.GATE_PATH
    plan = GatePlan(sha_after=template.gate_sha, mode=template.gate_mode)
    if not os.path.lexists(path):
        plan.action, plan.data = "install", template.gate_bytes
        return plan
    local = read_target_file(path)
    plan.sha_before = rel.sha256_bytes(local)
    plan.mode = stat.S_IMODE(path.stat().st_mode)
    if plan.sha_before == template.gate_sha:
        plan.from_release = template.release
        return plan
    matches = rel.releases_matching(template.index, "gate_sha256", plan.sha_before)
    if matches:
        plan.action, plan.data = "replace", template.gate_bytes
        plan.releases, plan.from_release = matches, matches[-1]
        return plan
    plan.action, plan.data = "replace_edited", template.gate_bytes
    plan.from_release = rel.gate_release(local.decode("utf-8", errors="replace"))
    plan.diff = unified(
        local.decode("utf-8", errors="replace"), template.gate_bytes.decode("utf-8"),
        f"instance {rel.GATE_PATH.as_posix()}", f"template {rel.GATE_PATH.as_posix()} ({template.release})")
    if not replace_edited:
        plan.refusals.append(
            f"{rel.GATE_PATH.as_posix()} was edited locally (sha256 {plan.sha_before[:12]} is not a released gate); "
            "review the diff, then pass --replace-edited-gate to replace it")
    return plan


def assemble(frontmatter: str, release: str, block: str, local: str) -> str:
    parts: list[str] = []
    if frontmatter:
        parts.append(frontmatter if frontmatter.endswith("\n") else frontmatter + "\n")
        parts.append("\n")
    parts.append(rel.render_managed_block(release, block))
    if local:
        parts.extend(["\n", local])
    return "".join(parts)


def verify_conversion(
    new_text: str, frontmatter: str, local_blocks: list[Block], local: str, template: Template,
) -> list[str]:
    """Problems that make a converted file unsafe to write (empty when it is sound)."""
    problems: list[str] = []
    if not new_text.startswith(frontmatter):
        problems.append("internal check failed: frontmatter changed")
    pieces = [block.text for block in local_blocks]
    if pieces:
        pieces[0] = trim_leading_blank(pieces[0])
    if "".join(pieces) != local or (local and not new_text.endswith(local)):
        problems.append("internal check failed: local text does not follow the managed block unchanged")
    for piece in pieces:
        if piece and piece not in new_text:
            problems.append("internal check failed: a local block is not present verbatim")
            break
    found, error = rel.extract_managed_block(new_text)
    if error or found is None or found.content != template.block or found.release != template.release:
        problems.append("internal check failed: managed block is not the template block")
    return problems


def classify_template_blocks(
    plan: ContractPlan, blocks: list[Block], history: dict[str, list[dict[str, Any]]],
) -> None:
    """Record known template blocks as silent removals and unknown ones as modified sections."""
    for block in blocks:
        if block.owner != "template":
            continue
        normalized = normalize_block(block.text)
        entry = {"heading": block.title, "level": block.level, "lines": len(split_lines(block.text))}
        releases = known_releases(history, block.heading, normalized)
        if releases is not None:
            plan.removed_sections.append({**entry, "kind": "template", "releases": releases})
            continue
        closest = closest_known(history, block.heading, normalized)
        known_text = normalize_block(closest["text"]) if closest else ""
        closest_releases = [str(release) for release in closest["releases"]] if closest else []
        label = f"known template text ({', '.join(closest_releases)})" if closest else "no known template text"
        plan.removed_sections.append({**entry, "kind": "modified"})
        plan.modified_sections.append({
            **entry, "closest_releases": closest_releases, "text": block.text,
            "diff": unified(normalized, known_text, f"instance {AGENTS_NAME}: {block.title}", label),
        })


def find_local_template_headings(blocks: list[Block]) -> list[dict[str, Any]]:
    """Level-3 headings inside local blocks that look like template headings."""
    found: list[dict[str, Any]] = []
    parent = "text before the first heading"
    for block in blocks:
        if block.owner != "local":
            continue
        if block.level in (1, 2):
            parent = block.title
        elif block.level == 3 and block.heading in TEMPLATE_HEADINGS:
            found.append({"heading": block.title, "level": 3, "inside": parent})
    return found


def plan_conversion(
    plan: ContractPlan, text: str, frontmatter: str, template: Template, accept_modified: bool,
) -> None:
    """First conversion: no managed block yet."""
    cleaned = clean_refresh(text[len(frontmatter):])
    plan.removed_notices, plan.warnings = cleaned.notices, cleaned.warnings
    plan.removed_sections = list(cleaned.sections)
    blocks = split_blocks(cleaned.text)
    local_blocks = [block for block in blocks if block.owner == "local"]
    if any(block.owner == "template" for block in blocks):
        classify_template_blocks(plan, blocks, load_history(template.root))
    plan.local_template_headings = find_local_template_headings(blocks)
    if plan.modified_sections and not accept_modified:
        names = ", ".join(repr(section["heading"]) for section in plan.modified_sections)
        plan.refusals.append(
            f"modified template sections: {names}; move any project rule into local sections, "
            "then pass --accept-modified-sections to remove them (their text is kept in this report)")
    if plan.local_template_headings and not accept_modified:
        names = ", ".join(f"{item['heading']!r} inside {item['inside']!r}" for item in plan.local_template_headings)
        plan.refusals.append(
            f"possible template text in local sections: {names}; convert by hand, "
            "or pass --accept-modified-sections to keep them as local text")
    local = trim_leading_blank("".join(block.text for block in local_blocks))
    plan.action = "convert"
    plan.text = assemble(frontmatter, template.release, template.block, local)
    plan.local_bytes = len(local.encode("utf-8"))
    problems = verify_conversion(plan.text, frontmatter, local_blocks, local, template)
    plan.local_bytes_preserved = not problems
    plan.refusals.extend(problems)


def plan_existing_block(
    plan: ContractPlan, text: str, block: rel.ManagedBlock, frontmatter: str, template: Template,
    replace_edited: bool,
) -> None:
    """A managed block exists: refresh it if it is known, and still drop refresh notices around it."""
    if block.start < len(frontmatter):
        plan.refusals.append("malformed managed block markers (inside the frontmatter)")
        return
    head, middle, tail = text[: block.start], text[block.start : block.end], text[block.end :]
    head_clean = clean_refresh(head[len(frontmatter):])
    tail_clean = clean_refresh(tail[1:] if tail.startswith("\n") else tail)
    plan.removed_notices = [*head_clean.notices, *tail_clean.notices]
    plan.removed_sections = [*head_clean.sections, *tail_clean.sections]
    plan.warnings = [*head_clean.warnings, *tail_clean.warnings]
    plan.from_release = block.release
    if block.content == template.block:
        stale_marker = block.release != template.release
        edited = False
    else:
        stale_marker = True
        edited = not rel.releases_matching(template.index, "contract_sha256", rel.contract_sha256(block.content))
    new_middle = rel.render_managed_block(template.release, template.block).rstrip("\n") if stale_marker else middle
    suffix = "\n" + tail_clean.text if tail.startswith("\n") else ""
    if stale_marker and not suffix:
        suffix = "\n"
    plan.text = frontmatter + head_clean.text + new_middle + suffix
    plan.local_bytes = len((head_clean.text + tail_clean.text).encode("utf-8"))
    if edited:
        plan.action = "replace_edited"
        plan.diff = unified(
            block.content, template.block, f"instance {AGENTS_NAME} managed block",
            f"template {rel.MANAGED_PATH.as_posix()} ({template.release})")
        if not replace_edited:
            plan.refusals.append(
                f"the managed block in {AGENTS_NAME} was edited locally (its content matches no released contract); "
                "review the diff, then pass --replace-edited-contract to replace it")
    elif stale_marker:
        plan.action = "replace"
    elif plan.removed_notices or plan.removed_sections:
        plan.action = "clean"
    if plan.text == text:
        plan.text = None
        return
    problems = verify_conversion(plan.text, frontmatter, [], "", template)
    plan.local_bytes_preserved = not problems
    plan.refusals.extend(problems)


def plan_contract(target: Path, template: Template, args: argparse.Namespace) -> ContractPlan:
    path = target / AGENTS_NAME
    plan = ContractPlan()
    if not os.path.lexists(path):
        plan.action = "create"
        plan.text = rel.render_managed_block(template.release, template.block) + "\n" + LOCAL_SCAFFOLD
        return plan
    data = read_target_file(path)
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise UpdateRefused([f"{AGENTS_NAME} is not valid UTF-8: {exc}"]) from exc
    if "\r" in text:
        raise UpdateRefused([f"{AGENTS_NAME} has CR or CRLF line endings; convert it to LF first so local text can be preserved byte for byte"])
    plan.mode = stat.S_IMODE(path.stat().st_mode)
    frontmatter, _ = split_frontmatter(text)
    if TEMPLATE_ROLE.search(frontmatter):
        raise UpdateRefused([f"{AGENTS_NAME} declares repo_role: template_repository; this command updates instances only"])
    block, error = rel.extract_managed_block(text)
    if error:
        plan.refusals.append(f"{AGENTS_NAME}: {error}")
    elif block is None:
        plan_conversion(plan, text, frontmatter, template, args.accept_modified_sections)
    else:
        plan_existing_block(plan, text, block, frontmatter, template, args.replace_edited_contract)
    return plan


def build_plan(target: Path, template: Template, args: argparse.Namespace) -> Plan:
    return Plan(target, template, plan_gate(target, template, args.replace_edited_gate),
                plan_contract(target, template, args))


# --- Applying ------------------------------------------------------------------------------


def write_atomic(path: Path, data: bytes, mode: int) -> None:
    """Write beside the target, then os.replace; the original survives any failure."""
    handle, name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(name, mode)
        os.replace(name, path)
    except BaseException:
        try:
            os.unlink(name)
        except FileNotFoundError:
            pass
        raise


def apply_plan(plan: Plan) -> None:
    """Gate first, then contract; each part is independent, so a rerun finishes an interrupted apply."""
    if plan.gate.data is not None:
        gate_path = plan.target / rel.GATE_PATH
        gate_path.parent.mkdir(exist_ok=True)
        write_atomic(gate_path, plan.gate.data, plan.gate.mode)
    if plan.contract.text is not None:
        write_atomic(plan.target / AGENTS_NAME, plan.contract.text.encode("utf-8"), plan.contract.mode)


# --- Reporting -----------------------------------------------------------------------------


def plan_payload(plan: Plan, applied: bool) -> dict[str, Any]:
    contract = plan.contract
    return {
        "target": str(plan.target),
        "release": plan.template.release,
        "gate": {
            "action": plan.gate.action,
            "from_release": plan.gate.from_release,
            "sha_before": plan.gate.sha_before,
            "sha_after": plan.gate.sha_after,
        },
        "contract": {
            "action": contract.action,
            "from_release": contract.from_release,
            "removed_sections": contract.removed_sections,
            "removed_notices": contract.removed_notices,
            "modified_sections": contract.modified_sections,
            "local_template_headings": contract.local_template_headings,
            "warnings": contract.warnings,
            "local_bytes_preserved": contract.local_bytes_preserved,
        },
        "refused": plan.refusals,
        "applied": applied,
    }


def refusal_payload(target: str, template: Template | None, reasons: list[str]) -> dict[str, Any]:
    return {
        "target": target, "release": template.release if template else None, "gate": None, "contract": None,
        "refused": reasons, "applied": False,
    }


def short(sha: str | None) -> str:
    return sha[:12] if sha else "none"


def gate_lines(plan: Plan) -> list[str]:
    gate = plan.gate
    lines = [f"Gate {rel.GATE_PATH.as_posix()}: {gate.action}"]
    if gate.action == "none":
        lines[0] += f" (already release {plan.template.release})"
    elif gate.action == "install":
        lines.append(f"  not present; install release {plan.template.release} ({short(gate.sha_after)})")
    elif gate.action == "replace":
        lines.append(f"  released gate of {', '.join(gate.releases)} ({short(gate.sha_before)}) -> "
                     f"{plan.template.release} ({short(gate.sha_after)})")
    else:
        lines.append(f"  edited locally ({short(gate.sha_before)}) -> {plan.template.release} ({short(gate.sha_after)})")
    if gate.diff:
        lines.append("  diff (instance -> template, first lines):")
        lines.extend(f"    {line}" for line in gate.diff)
    return lines


def contract_lines(plan: Plan, show_removed_text: bool) -> list[str]:
    contract = plan.contract
    lines = [f"Contract {AGENTS_NAME}: {contract.action}"]
    if contract.action == "create":
        lines.append(f"  {AGENTS_NAME} is missing: create it from the managed block plus empty local sections")
    if contract.from_release:
        lines.append(f"  managed block marker: release {contract.from_release} -> {plan.template.release}")
    for notice in contract.removed_notices:
        lines.append(f"  remove refresh notice projectstate-{notice['name']} ({notice['lines']} lines)")
    known = [item for item in contract.removed_sections if item["kind"] == "template"]
    for section in (item for item in contract.removed_sections if item["kind"] == "refresh"):
        lines.append(f"  remove refresh section {section['heading']!r} ({section['lines']} lines)")
    if known:
        lines.append(f"  replace {len(known)} template sections of known text: "
                     + ", ".join(item["heading"] for item in known))
    for warning in contract.warnings:
        lines.append(f"  warning: {warning}")
    for item in contract.local_template_headings:
        lines.append(f"  possible template text in local sections: {item['heading']!r} inside {item['inside']!r}")
    for section in contract.modified_sections:
        lines.append(f"  modified template section {section['heading']!r} (closest known text: "
                     f"{', '.join(section['closest_releases']) or 'none'}); diff instance -> known:")
        lines.extend(f"    {line}" for line in section["diff"])
        if show_removed_text:
            lines.append("  removed text (move any project rule into the local sections):")
            lines.extend(f"    | {line}" for line in section["text"].rstrip("\n").split("\n"))
    if contract.diff:
        lines.append("  diff (instance -> template block, first lines):")
        lines.extend(f"    {line}" for line in contract.diff)
    if contract.action in ("convert", "replace", "replace_edited", "clean"):
        state = "preserved" if contract.local_bytes_preserved else "NOT verified"
        lines.append(f"  local text: {contract.local_bytes} bytes {state}")
    return lines


def render_report(plan: Plan, args: argparse.Namespace, applied: bool) -> str:
    lines = [f"ProjectState update of {plan.target} to release {plan.template.release} (template {plan.template.root})"]
    lines.extend(gate_lines(plan))
    lines.extend(contract_lines(plan, args.accept_modified_sections))
    if plan.refusals:
        lines.append("Refused, nothing written:")
        lines.extend(f"  - {reason}" for reason in plan.refusals)
    elif applied:
        lines.append("Applied.")
    elif not plan.changed:
        lines.append(f"Up to date at release {plan.template.release}.")
    elif args.check:
        lines.append("Update needed (--check writes nothing).")
    else:
        lines.append("Dry run: nothing written. Pass --apply to write these changes.")
    return "\n".join(lines)


def emit(args: argparse.Namespace, payload: dict[str, Any], human: str, *, error: bool = False) -> None:
    """JSON always goes to stdout; the human report goes to stderr when there is no plan to show."""
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(human, file=sys.stderr if error else sys.stdout)


# --- Contract history builder (maintenance mode) --------------------------------------------


def run_git(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    done = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=False, env=git_env())
    if done.returncode != 0:
        raise UpdateRefused([f"git {' '.join(args)} failed: {(done.stderr or done.stdout).strip()}"])
    return done


def generate_agents_files(template_root: Path, release: str, workspace: Path) -> list[str]:
    """AGENTS.md texts the release's own generator produced: new and adopt, core and hardened."""
    tree = workspace / f"tree-{release}"
    run_git(["-C", str(template_root), "worktree", "add", "--detach", str(tree), f"refs/tags/v{release}"])
    texts: list[str] = []
    env = {**git_env(), "PYTHONDONTWRITEBYTECODE": "1"}
    try:
        for profile in HISTORY_PROFILES:
            for mode in ("new", "adopt"):
                target = workspace / f"{mode}-{release}-{profile}"
                command = [sys.executable, str(tree / "scripts" / "init_template.py"), mode,
                           "--name", "History", "--target", str(target), "--profile", profile]
                if mode == "new":
                    command.append("--no-init-git")
                else:
                    target.mkdir()
                    (target / "README.md").write_text("# History\n\nA project with a README.\n", encoding="utf-8")
                    run_git(["init", "-q"], cwd=target)
                    run_git(["add", "README.md"], cwd=target)
                    run_git(["-c", "user.name=history", "-c", "user.email=history@example.invalid",
                             "-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null",
                             "commit", "-q", "-m", "readme"], cwd=target)
                done = subprocess.run(command, cwd=tree, capture_output=True, text=True, check=False, env=env)
                if done.returncode != 0:
                    raise UpdateRefused([f"{mode} --profile {profile} failed at v{release}: "
                                         f"{(done.stderr or done.stdout).strip()}"])
                texts.append((target / AGENTS_NAME).read_text(encoding="utf-8"))
    finally:
        subprocess.run(["git", "-C", str(template_root), "worktree", "remove", "--force", str(tree)],
                       capture_output=True, text=True, check=False, env=git_env())
    return texts


def add_known_texts(history: dict[str, list[dict[str, Any]]], release: str, agents_text: str) -> None:
    """Record every block of a generated AGENTS.md under its heading; all of it is template text."""
    _, body = split_frontmatter(agents_text)
    for block in split_blocks(body):
        if block.level == 0 and not block.text.strip():
            continue
        if block.owner != "template":
            raise UpdateRefused([
                f"v{release} generated a block {block.title or '(text before the first heading)'!r} that "
                "TEMPLATE_HEADINGS does not cover; extend TEMPLATE_HEADINGS first"])
        text = normalize_block(block.text)
        entries = history.setdefault(block.heading, [])
        entry = next((item for item in entries if item["text"] == text), None)
        if entry is None:
            entries.append({"text": text, "releases": [release]})
        elif release not in entry["releases"]:
            entry["releases"].append(release)
            entry["releases"].sort(key=rel.semver_key)


def build_history(template_root: Path, output: Path) -> dict[str, list[dict[str, Any]]]:
    """Regenerate the known contract texts from the release tags of ``template_root``."""
    workspace = Path(tempfile.mkdtemp(prefix="projectstate-history-"))
    history: dict[str, list[dict[str, Any]]] = {}
    try:
        inside = subprocess.run(["git", "-C", str(workspace), "rev-parse", "--is-inside-work-tree"],
                                capture_output=True, text=True, check=False, env=git_env())
        if inside.returncode == 0:
            raise UpdateRefused([f"temporary directory {workspace} is inside a git work tree; set TMPDIR elsewhere"])
        for release in HISTORY_RELEASES:
            for agents_text in generate_agents_files(template_root, release, workspace):
                add_known_texts(history, release, agents_text)
    finally:
        subprocess.run(["git", "-C", str(template_root), "worktree", "prune"],
                       capture_output=True, text=True, check=False, env=git_env())
        shutil.rmtree(workspace, ignore_errors=True)
    payload = {"format": HISTORY_FORMAT, "headings": history}
    output.parent.mkdir(parents=True, exist_ok=True)
    write_atomic(output, (json.dumps(payload, indent=2, ensure_ascii=False) + "\n").encode("utf-8"), 0o644)
    return history


def run_build_history(args: argparse.Namespace) -> int:
    template_root = Path(args.template).resolve()
    output = Path(args.output) if args.output else template_root / HISTORY_PATH
    try:
        history = build_history(template_root, output)
    except UpdateRefused as exc:
        for reason in exc.reasons:
            print(f"refused: {reason}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"refused: cannot build the history ({exc}); git and a writable temporary directory are required",
              file=sys.stderr)
        return 2
    texts = sum(len(entries) for entries in history.values())
    print(f"Wrote {output}: {len(history)} headings, {texts} known texts from releases {', '.join(HISTORY_RELEASES)}")
    return 0


# --- Command line --------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Bring one ProjectState instance to the template's current release (dry run by default)")
    parser.add_argument("--target", help="Instance repository root to update")
    parser.add_argument("--template", default=str(rel.TEMPLATE_ROOT), help="Template repository root (default: this repository)")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true", help="Write the planned changes atomically")
    mode.add_argument("--check", action="store_true", help="Write nothing; exit 1 when a change is needed")
    parser.add_argument("--json", action="store_true", help="Emit the plan as JSON")
    parser.add_argument("--replace-edited-gate", action="store_true",
                        help="Replace a locally edited scripts/projectstate_gate.py")
    parser.add_argument("--replace-edited-contract", action="store_true",
                        help="Replace a locally edited managed block")
    parser.add_argument("--accept-modified-sections", action="store_true",
                        help="Remove modified template sections (their text is reported) and keep local template-like headings")
    parser.add_argument("--allow-dirty", action="store_true",
                        help="Skip the git check for uncommitted changes to AGENTS.md and the gate")
    parser.add_argument("--build-history", action="store_true",
                        help="Maintenance: regenerate releases/contract-history.json from the release tags (writes git worktrees)")
    parser.add_argument("--output", help="With --build-history: output path (default: <template>/releases/contract-history.json)")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.build_history:
        if args.target or args.apply or args.check:
            parser.error("--build-history takes no --target, --apply or --check")
        return run_build_history(args)
    if not args.target:
        parser.error("--target is required")
    template: Template | None = None
    try:
        template = load_template(Path(args.template).resolve())
        target = preflight(args.target, template, args.allow_dirty)
        plan = build_plan(target, template, args)
    except UpdateRefused as exc:
        emit(args, refusal_payload(args.target, template, exc.reasons),
             "\n".join(f"refused: {reason}" for reason in exc.reasons), error=True)
        return 2
    if plan.refusals:
        emit(args, plan_payload(plan, False), render_report(plan, args, False))
        return 2
    applied = False
    if args.apply and plan.changed:
        try:
            apply_plan(plan)
        except OSError as exc:
            reason = f"write failed: {exc}; rerun --apply to finish"
            emit(args, refusal_payload(args.target, template, [reason]), f"refused: {reason}", error=True)
            return 2
        applied = True
    emit(args, plan_payload(plan, applied), render_report(plan, args, applied))
    return 1 if args.check and plan.changed else 0


if __name__ == "__main__":
    raise SystemExit(main())
