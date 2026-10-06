#!/usr/bin/env python3
"""Read-only fleet doctor: one report over every ProjectState repository under a root folder.

For each repository below ``--root`` it shows which template release the repository runs, whether its
vendored gate and managed ``AGENTS.md`` block match ``releases/index.json``, how large its startup
context is, what the template gate says about its recorded state, and which decisions wait for the owner.

The doctor never writes inside a repository and never runs instance code. It reads files without
following symlinks, runs a small set of read-only ``git`` commands (no network), and uses only this
checkout's gate module to parse and validate. Its only output files are ``fleet.md`` and ``fleet.json``
in ``--out``, which must lie outside ``--root``; ``--stdout`` writes nothing at all.
"""

from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Iterator, NamedTuple


SCRIPT_DIR = Path(__file__).resolve().parent


def _load_siblings() -> tuple[Any, Any]:
    """Import the gate and release helpers next to this script without leaving bytecode behind."""
    if str(SCRIPT_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPT_DIR))
    previous = sys.dont_write_bytecode
    sys.dont_write_bytecode = True  # a __pycache__ beside the siblings could sit inside a repository
    try:
        import projectstate_gate
        import projectstate_release
    finally:
        sys.dont_write_bytecode = previous
    return projectstate_gate, projectstate_release


gate_mod, release_mod = _load_siblings()

FORMAT = "projectstate-fleet/1"
DEFAULT_OUT = "~/.local/state/projectstate"
GIT_TIMEOUT_SECONDS = 30
MAX_READ_BYTES = 16 * 1024 * 1024
HISTORY_LIMIT = 50
EXPIRY_WINDOW_DAYS = 14
STATE_BYTES_FLAG = 16384
PROJECT_BYTES_FLAG = 6144
LOCAL_LINES_FLAG = 150
UNMANAGED_LINES_FLAG = 200
OBJECTIVE_CHARS = 120
NEXT_ACTION_CHARS = 160
DETAIL_CHARS = 160
AWAITING_STATUSES = {"validated", "ready_for_human"}
KINDS = ("v6", "v6-invalid", "v5", "other")
GATE_STATES = ("current", "behind", "unknown", "missing", "symlink", "unreadable")
CONTRACT_STATES = ("current", "behind", "edited", "unmanaged", "malformed", "missing", "unreadable")
VERDICTS = ("validated", "not validated", "invalid")

SLICE_ID = re.compile(r"[a-z0-9][a-z0-9-]*")
DATE_TEXT = re.compile(r"\d{4}-\d{2}-\d{2}")
COMMIT_TIME = re.compile(r"(\d{4}-\d{2}-\d{2})T\d{2}:\d{2}:\d{2}(Z|[+-]\d{2}:\d{2})")
FENCE = re.compile(r"^[ \t]{0,3}(```|~~~)")
ATX_HEADING = re.compile(r"^(#{1,3})[ \t]+(.*)$")
NOTICE_MARKER = re.compile(r"<!--\s*projectstate-[A-Za-z0-9][A-Za-z0-9._-]*:start\s*-->")
NOTICE_TITLE = re.compile(r"Required first action|Latest required refresh", re.IGNORECASE)
DIRECTIVES_HEADING = re.compile(r"^##[ \t]+Owner directives[ \t]*$", re.IGNORECASE)
DIRECTIVE_LINE = re.compile(r"^-[ \t]+(\d{4}-\d{2}-\d{2})\b(.*)$")
DIRECTIVE_UNTIL = re.compile(r"\buntil[ \t]+(\d{4}-\d{2}-\d{2})\b", re.IGNORECASE)
OWNER_DECISION = re.compile(r"^##[ \t]+Owner decision[ \t]*$", re.IGNORECASE)
SECTION_HEADING = re.compile(r"^#{1,2}[ \t]+\S")
CONTROL_CHARS = re.compile(r"[\x00-\x09\x0b-\x1f\x7f-\x9f]")

# Variables that would redirect git at a different repository than the one being inspected.
GIT_REDIRECT_VARS = frozenset({
    "GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR", "GIT_OBJECT_DIRECTORY",
    "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_NAMESPACE", "GIT_PREFIX", "GIT_QUARANTINE_PATH",
})


class Context(NamedTuple):
    """Template facts shared by every repository scan."""

    template: Path
    index: dict[str, Any]
    schema: str
    current: str | None
    today: dt.date


class Doc(NamedTuple):
    """A repository file read once, without following symlinks."""

    data: bytes | None
    problem: str | None

    @property
    def text(self) -> str:
        return (self.data or b"").decode("utf-8", errors="replace")

    @property
    def size(self) -> int | None:
        return None if self.data is None else len(self.data)

    @property
    def lines(self) -> int | None:
        if self.data is None:
            return None
        return self.data.count(b"\n") + (1 if self.data and not self.data.endswith(b"\n") else 0)


# --- small helpers ---------------------------------------------------------------------------


def clip(value: Any, limit: int) -> str:
    """One-line text of at most ``limit`` characters."""
    text = " ".join(str(value).split())
    return text if len(text) <= limit else text[: limit - 3].rstrip() + "..."


def text_value(value: Any) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def parse_date(value: Any) -> dt.date | None:
    if not isinstance(value, str) or not DATE_TEXT.fullmatch(value.strip()):
        return None
    try:
        return dt.date.fromisoformat(value.strip())
    except ValueError:
        return None


def load_doc(root: Path, relative: str) -> Doc:
    """Read ``root/relative`` without following a symlink at any component."""
    current = root
    try:
        for part in relative.split("/"):
            current = current / part
            if current.is_symlink():
                return Doc(None, "symlink")
        if not current.exists():
            return Doc(None, "missing")
        if not current.is_file():
            return Doc(None, "not a regular file")
        size = current.stat().st_size
        if size > MAX_READ_BYTES:
            return Doc(None, f"too large ({size} bytes)")
        return Doc(current.read_bytes(), None)
    except OSError as exc:
        return Doc(None, f"unreadable: {exc.strerror or exc}")


def outside_fences(text: str) -> Iterator[str]:
    """Yield the lines of a Markdown text that are not inside a fenced code block."""
    fence: str | None = None
    for line in release_mod.normalize_newlines(text).split("\n"):
        match = FENCE.match(line)
        if match is None:
            if fence is None:
                yield line
        elif fence is None:
            fence = match.group(1)
        elif match.group(1) == fence:
            fence = None


def parse_payload(text: str | None) -> dict[str, Any] | None:
    """Parse STATE.yaml text with the template gate; None when it is not usable."""
    if text is None:
        return None
    try:
        payload = gate_mod.parse_state(text)
    except Exception:  # a malformed instance or historical file must never stop the scan
        return None
    return payload if isinstance(payload, dict) else None


# --- git (read-only, no network) -------------------------------------------------------------


def git_environment(repo: Path) -> dict[str, str]:
    env = {key: value for key, value in os.environ.items() if key not in GIT_REDIRECT_VARS}
    env.update(
        GIT_OPTIONAL_LOCKS="0",
        GIT_TERMINAL_PROMPT="0",
        GIT_PAGER="cat",
        LC_ALL="C",
        # Never climb out of the child directory into an enclosing repository.
        GIT_CEILING_DIRECTORIES=str(repo.parent),
    )
    return env


def run_git(repo: Path, *args: str) -> tuple[int, bytes]:
    """Run one read-only git command; (-1, b'') when git is missing or the command times out."""
    command = ["git", "--no-pager", "-C", str(repo), "-c", "core.fsmonitor=false", *args]
    try:
        done = subprocess.run(
            command,
            capture_output=True,
            stdin=subprocess.DEVNULL,
            env=git_environment(repo),
            timeout=GIT_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return -1, b""
    return done.returncode, done.stdout


def git_out(repo: Path, *args: str) -> str | None:
    code, out = run_git(repo, *args)
    return out.decode("utf-8", errors="replace") if code == 0 else None


def git_line(repo: Path, *args: str) -> str | None:
    out = git_out(repo, *args)
    return out.strip() if out is not None else None


def git_count(repo: Path, *args: str) -> int | None:
    value = git_line(repo, *args)
    return int(value) if value is not None and value.isdigit() else None


def git_blob(repo: Path, spec: str) -> str | None:
    """Content of ``<rev>:<path>``; cat-file never applies filters or textconv."""
    code, out = run_git(repo, "cat-file", "blob", spec)
    if code != 0:
        return None
    try:
        return out.decode("utf-8")
    except UnicodeDecodeError:
        return None


def count_status(porcelain: str) -> tuple[int, int, int]:
    """Staged, unstaged and untracked entry counts from ``git status --porcelain=v1`` output."""
    staged = unstaged = untracked = 0
    for line in porcelain.splitlines():
        if len(line) < 3 or line.startswith("!!"):
            continue
        if line.startswith("??"):
            untracked += 1
            continue
        staged += line[0] != " "
        unstaged += line[1] != " "
    return staged, unstaged, untracked


def git_facts(path: Path) -> dict[str, Any] | None:
    """Branch, HEAD, last commit date, upstream and working-tree counts; None without a .git entry."""
    if not os.path.lexists(path / ".git"):
        return None
    facts: dict[str, Any] = {
        "branch": None, "head": None, "last_commit": None, "upstream": None,
        "staged": None, "unstaged": None, "untracked": None, "error": None,
    }
    code, out = run_git(path, "symbolic-ref", "--short", "-q", "HEAD")
    if code == 0:
        facts["branch"] = out.decode("utf-8", errors="replace").strip()
    elif code == 1:
        facts["branch"] = "(detached)"
    else:
        facts["error"] = "not a usable git repository"
        return facts
    last = git_line(path, "log", "-1", "--abbrev=7", "--format=%h %cs")
    if last and " " in last:
        facts["head"], facts["last_commit"] = last.split(" ", 1)
    facts["upstream"] = git_line(path, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}") or None
    status = git_out(path, "status", "--porcelain=v1", "--untracked-files=normal")
    if status is None:
        facts["error"] = "git status failed or timed out"
    else:
        facts["staged"], facts["unstaged"], facts["untracked"] = count_status(status)
    return facts


def git_usable(facts: dict[str, Any] | None) -> bool:
    return facts is not None and facts["branch"] is not None


def slice_history(repo: Path, slice_id: str | None, today: dt.date) -> dict[str, Any]:
    """Age of the current slice and STATE.yaml churn since the commit that introduced its id."""
    unknown: dict[str, Any] = {"first_commit": None, "age_days": None, "state_commits": None, "all_commits": None}
    if not slice_id or not SLICE_ID.fullmatch(slice_id):
        return unknown
    out = git_out(repo, "log", "--reverse", "--format=%cI", f"-S{slice_id}", "--no-textconv", "--no-ext-diff",
                  "--", "STATE.yaml")
    match = COMMIT_TIME.fullmatch(out.splitlines()[0].strip()) if out and out.strip() else None
    if not match:
        return unknown  # an uncommitted slice has no recorded age
    day, zone = match.groups()
    since = f"--since={day}T00:00:00{zone}"
    return {
        "first_commit": day,
        "age_days": max(0, (today - dt.date.fromisoformat(day)).days),
        "state_commits": git_count(repo, "rev-list", "--count", since, "HEAD", "--", "STATE.yaml"),
        "all_commits": git_count(repo, "rev-list", "--count", since, "HEAD"),
    }


def slice_fields(payload: dict[str, Any] | None) -> tuple[str | None, str | None, str | None]:
    current = mapping(mapping(payload).get("current_slice"))
    human = mapping(mapping(payload).get("validation")).get("human_acceptance")
    return text_value(current.get("id")), text_value(current.get("status")), text_value(human)


def has_owner_decision(repo: Path, slice_id: str) -> bool:
    """Whether evidence/<id>/summary.md (working tree, else HEAD) has an '## Owner decision' heading."""
    if not SLICE_ID.fullmatch(slice_id):
        return False
    relative = f"evidence/{slice_id}/summary.md"
    doc = load_doc(repo, relative)
    text = doc.text if doc.data is not None else git_blob(repo, f"HEAD:{relative}")
    return text is not None and any(OWNER_DECISION.match(line) for line in outside_fences(text))


def silent_replacement(
    repo: Path, old: dict[str, Any] | None, new: dict[str, Any] | None, when: str | None, commit: str | None,
    cache: dict[str, bool],
) -> dict[str, Any] | None:
    """A record when ``old`` was validated, awaiting the owner, and replaced by another slice without a decision."""
    old_id, old_status, old_human = slice_fields(old)
    new_id, _, _ = slice_fields(new)
    if not old_id or not new_id or old_id == new_id:
        return None
    if old_status not in AWAITING_STATUSES or old_human != "pending":
        return None
    if old_id not in cache:
        cache[old_id] = has_owner_decision(repo, old_id)
    if cache[old_id]:
        return None
    return {"from": old_id, "to": new_id, "date": when, "commit": commit, "uncommitted": commit is None}


def silent_replacements(repo: Path, working: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Slice replacements without an owner decision: the newest commits that changed the id, then the worktree."""
    found: list[dict[str, Any]] = []
    cache: dict[str, bool] = {}
    log = git_out(repo, "log", "--format=%H %cs", "-G^  id:", "-n", str(HISTORY_LIMIT), "--no-textconv",
                  "--no-ext-diff", "--", "STATE.yaml")
    for line in (log or "").splitlines():
        sha, _, day = line.partition(" ")
        if not sha:
            continue
        old = parse_payload(git_blob(repo, f"{sha}^:STATE.yaml"))
        new = parse_payload(git_blob(repo, f"{sha}:STATE.yaml"))
        record = silent_replacement(repo, old, new, day or None, sha[:7], cache)
        if record:
            found.append(record)
    record = silent_replacement(repo, parse_payload(git_blob(repo, "HEAD:STATE.yaml")), working, None, None, cache)
    if record:
        found.append(record)
    return found


def update_branch(repo: Path, release: str | None) -> dict[str, Any] | None:
    """A local projectstate/release-<current> branch whose commits are not yet in HEAD."""
    if not release:
        return None
    branch = f"projectstate/release-{release}"
    tip = git_line(repo, "rev-parse", "--verify", "--quiet", f"refs/heads/{branch}")
    if not tip:
        return None
    merged, _ = run_git(repo, "merge-base", "--is-ancestor", tip, "HEAD")
    if merged != 1:
        return None  # 0: already merged; anything else: HEAD unreadable
    ahead, _ = run_git(repo, "merge-base", "--is-ancestor", "HEAD", tip)
    return {"branch": branch, "commit": tip[:7], "fast_forward": ahead == 0}


# --- per-repository analysis -----------------------------------------------------------------


def classify(path: Path, schema: str) -> tuple[str, dict[str, Any] | None, str | None]:
    """Kind of a child directory, its parsed STATE.yaml for v6, and a short problem text."""
    if os.path.lexists(path / "STATE.yaml"):
        doc = load_doc(path, "STATE.yaml")
        if doc.data is None:
            return "v6-invalid", None, f"STATE.yaml: {doc.problem}"
        try:
            payload = gate_mod.parse_state(doc.data.decode("utf-8"))
        except Exception as exc:  # any parser failure marks the file unusable, never the scan
            return "v6-invalid", None, f"STATE.yaml: {clip(exc, DETAIL_CHARS)}"
        if not isinstance(payload, dict) or payload.get("version") != schema:
            return "v6-invalid", None, f"STATE.yaml version is not {schema}"
        return "v6", payload, None
    if os.path.lexists(path / "PROJECT_STATE.yaml"):
        return "v5", None, None
    return "other", None, None


def hash_status(sha: str, field: str, ctx: Context, stale: str, unmatched: str) -> tuple[str, str | None]:
    """Compare a hash with the released hashes: current, ``stale`` (name the newest match) or ``unmatched``."""
    matches = release_mod.releases_matching(ctx.index, field, sha)
    if ctx.current is not None and ctx.current in matches:
        return "current", ctx.current
    if matches:
        return stale, matches[-1]
    return unmatched, None


def gate_status(path: Path, ctx: Context) -> dict[str, Any]:
    doc = load_doc(path, "scripts/projectstate_gate.py")
    if doc.data is None:
        state = doc.problem if doc.problem in {"missing", "symlink"} else "unreadable"
        return {"status": state, "sha256": None, "release": None, "problem": doc.problem}
    sha = release_mod.sha256_bytes(doc.data)
    state, name = hash_status(sha, "gate_sha256", ctx, "behind", "unknown")
    return {"status": state, "sha256": sha, "release": name, "problem": None}


def contract_status(agents: Doc, ctx: Context) -> tuple[dict[str, Any], bool]:
    """Status of the managed AGENTS.md block, and whether a well-formed block exists."""
    result: dict[str, Any] = {"status": "missing", "sha256": None, "release": None, "declared": None}
    if agents.data is None:
        if agents.problem != "missing":
            result["status"] = "unreadable"
        return result, False
    block, problem = release_mod.extract_managed_block(agents.text)
    if problem:
        result["status"] = "malformed"
        return result, False
    if block is None:
        result["status"] = "unmanaged"
        return result, False
    sha = release_mod.contract_sha256(block.content)
    result["status"], result["release"] = hash_status(sha, "contract_sha256", ctx, "behind", "edited")
    result["sha256"], result["declared"] = sha, block.release
    return result, True


def local_line_count(text: str) -> int:
    """Lines of AGENTS.md outside the leading frontmatter and the managed block."""
    lines = release_mod.normalize_newlines(text).split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    if lines and lines[0].strip() == "---":
        for position in range(1, len(lines)):
            if lines[position].strip() == "---":
                lines = lines[position + 1:]
                break
    kept: list[str] = []
    inside = False
    for line in lines:
        if release_mod.START_MARKER.fullmatch(line):
            inside = True
        elif inside:
            inside = line != release_mod.END_LINE
        else:
            kept.append(line)
    return len(kept)


def size_report(agents: Doc, project: Doc, state: Doc, managed: bool) -> dict[str, Any]:
    sizes = {
        name: {"bytes": doc.size, "lines": doc.lines}
        for name, doc in (("agents", agents), ("project", project), ("state", state))
    }
    flags: list[str] = []
    if (state.size or 0) > STATE_BYTES_FLAG:
        flags.append(f"STATE.yaml is {state.size} bytes (limit {STATE_BYTES_FLAG})")
    if (project.size or 0) > PROJECT_BYTES_FLAG:
        flags.append(f"PROJECT.md is {project.size} bytes (limit {PROJECT_BYTES_FLAG})")
    local: int | None = None
    if agents.data is not None and managed:
        local = local_line_count(agents.text)
        if local > LOCAL_LINES_FLAG:
            flags.append(f"AGENTS.md has {local} local lines (limit {LOCAL_LINES_FLAG})")
    elif (agents.lines or 0) > UNMANAGED_LINES_FLAG:
        flags.append(f"AGENTS.md has {agents.lines} lines (limit {UNMANAGED_LINES_FLAG})")
    total = sum(doc.size or 0 for doc in (agents, project, state))
    return {**sizes, "startup_tokens": total // 4, "local_lines": local, "flags": flags}


def notice_report(agents: Doc) -> dict[str, int]:
    """Refresh notices: marker blocks plus 'Required first action' / 'Latest required refresh' headings."""
    blocks = headings = 0
    for line in outside_fences(agents.text):
        blocks += len(NOTICE_MARKER.findall(line))
        match = ATX_HEADING.match(line)
        headings += bool(match and NOTICE_TITLE.search(match.group(2)))
    return {"blocks": blocks, "headings": headings, "total": blocks + headings}


def directive_report(docs: dict[str, Doc], today: dt.date) -> dict[str, Any]:
    """Dated owner directives under '## Owner directives' and which of them have expired."""
    total = 0
    expired: list[dict[str, str]] = []
    for name, doc in docs.items():
        inside = False
        for line in outside_fences(doc.text):
            if SECTION_HEADING.match(line):
                inside = bool(DIRECTIVES_HEADING.match(line))
                continue
            match = DIRECTIVE_LINE.match(line) if inside else None
            until = DIRECTIVE_UNTIL.search(match.group(2)) if match else None
            limit = parse_date(until.group(1)) if until else None
            if limit is None:
                continue
            total += 1
            if limit < today:
                expired.append({"file": name, "until": limit.isoformat(), "text": clip(line, DETAIL_CHARS)})
    return {"total": total, "expired": len(expired), "expired_items": expired}


def verdict_report(path: Path) -> dict[str, Any]:
    """The template gate's verdict on the repository's recorded state (never the instance's own gate)."""
    try:
        result = gate_mod.validate(path)
        errors, blockers = list(result[0]), list(result[1])
    except Exception as exc:  # the gate must never stop the scan
        return {"verdict": "invalid", "detail": clip(f"gate failed: {exc!r}", DETAIL_CHARS)}
    if errors:
        return {"verdict": "invalid", "detail": clip(errors[0], DETAIL_CHARS)}
    if blockers:
        return {"verdict": "not validated", "detail": clip(blockers[0], DETAIL_CHARS)}
    return {"verdict": "validated", "detail": None}


def slice_report(payload: dict[str, Any], today: dt.date) -> dict[str, Any]:
    state = mapping(payload)
    current = mapping(state.get("current_slice"))
    journey = mapping(current.get("primary_journey"))
    slice_id, status, human = slice_fields(state)
    blockers = state.get("blockers") if isinstance(state.get("blockers"), list) else []
    first = next((clip(item, DETAIL_CHARS) for item in blockers if text_value(item)), None)
    due: list[dict[str, Any]] = []
    for item in state.get("risks") if isinstance(state.get("risks"), list) else []:
        risk = mapping(item)
        expires = parse_date(risk.get("expires"))
        if expires is None or risk.get("decision") != "accept_temporarily":
            continue
        days = (expires - today).days
        if days <= EXPIRY_WINDOW_DAYS:
            due.append({"id": text_value(risk.get("id")) or "?", "expires": expires.isoformat(), "days_left": days})
    objective = text_value(current.get("objective"))
    next_action = text_value(state.get("next_action"))
    return {
        "id": slice_id,
        "status": status,
        "journey": text_value(journey.get("status")),
        "human_acceptance": human,
        "objective": clip(objective, OBJECTIVE_CHARS) if objective else None,
        "next_action": clip(next_action, NEXT_ACTION_CHARS) if next_action else None,
        "first_blocker": first,
        "risks_due": due,
    }


def scan_repository(path: Path, payload: dict[str, Any] | None, kind: str, problem: str | None,
                    ctx: Context, is_template: bool) -> dict[str, Any]:
    repo: dict[str, Any] = {
        "name": path.name,
        "path": str(path),
        "kind": kind,
        "role": "template" if is_template else None,
        "problem": problem,
        "git": git_facts(path),
    }
    if kind != "v6" or payload is None:
        return repo
    agents, project, state = (load_doc(path, name) for name in ("AGENTS.md", "PROJECT.md", "STATE.yaml"))
    contract, managed = contract_status(agents, ctx)
    repo["gate"] = gate_status(path, ctx)
    repo["contract"] = contract
    repo["sizes"] = size_report(agents, project, state, managed)
    repo["notices"] = notice_report(agents)
    repo["directives"] = directive_report({"AGENTS.md": agents, "PROJECT.md": project}, ctx.today)
    repo["verdict"] = verdict_report(path)
    repo["slice"] = slice_report(payload, ctx.today)
    repo["history"] = {"first_commit": None, "age_days": None, "state_commits": None, "all_commits": None}
    repo["silent_replacements"] = []
    repo["update_branch"] = None
    if git_usable(repo["git"]):
        repo["history"] = slice_history(path, repo["slice"]["id"], ctx.today)
        repo["silent_replacements"] = silent_replacements(path, payload)
        repo["update_branch"] = update_branch(path, ctx.current)
    return repo


def discover(root: Path) -> list[Path]:
    """Immediate child directories: real directories only, no dot or underscore names, sorted case-insensitively."""
    names: list[str] = []
    with os.scandir(root) as entries:
        for entry in entries:
            if entry.name.startswith((".", "_")):
                continue
            try:
                if entry.is_symlink() or not entry.is_dir(follow_symlinks=False):
                    continue
            except OSError:
                continue
            names.append(entry.name)
    names.sort(key=lambda name: (name.casefold(), name))
    return [root / name for name in names]


# --- inbox and summary -----------------------------------------------------------------------


def decision_command(template: Path, repo: Path) -> str:
    script = shlex.quote(str(template / "scripts" / "projectstate_decide.py"))
    return f'python3 {script} {shlex.quote(str(repo))} accept|reject|waive "<your words>"'


def inbox_item(repo: dict[str, Any], kind: str, message: str, **detail: Any) -> dict[str, Any]:
    return {"repository": repo["name"], "path": repo["path"], "kind": kind, "message": message, **detail}


def due_text(risk: dict[str, Any]) -> str:
    days = risk["days_left"]
    if days < 0:
        return f"expired on {risk['expires']} ({-days} days ago)"
    return f"expires on {risk['expires']}" + (" (today)" if days == 0 else f" (in {days} days)")


def build_inbox(repos: list[dict[str, Any]], ctx: Context) -> dict[str, list[dict[str, Any]]]:
    inbox: dict[str, list[dict[str, Any]]] = {
        "decisions": [], "blocked": [], "needs_review": [], "ready_to_merge": [],
    }
    for repo in repos:
        if repo["kind"] != "v6":
            continue
        name, path, current = repo["name"], Path(repo["path"]), repo["slice"]
        slice_id = current["id"] or "(no slice id)"
        if current["status"] in AWAITING_STATUSES and current["human_acceptance"] == "pending":
            command = decision_command(ctx.template, path)
            inbox["decisions"].append(inbox_item(
                repo, "decision", f"{name}: {slice_id} is validated and waits for your decision. Run: {command}",
                slice=slice_id, command=command))
        reasons = [label for label, active in (("slice status", current["status"] == "blocked"),
                                               ("primary journey", current["journey"] == "blocked")) if active]
        if reasons:
            blocker = current["first_blocker"] or (
                repo["verdict"]["detail"] if repo["verdict"]["verdict"] == "not validated" else None
            ) or "no blocker recorded"
            inbox["blocked"].append(inbox_item(
                repo, "blocked", f"{name}: {slice_id} is blocked ({' and '.join(reasons)}): {blocker}",
                slice=slice_id, blocker=blocker))
        review = inbox["needs_review"]
        if repo["role"] != "template":  # the template maintains the gate and block that instances are compared with
            if repo["gate"]["status"] == "unknown":
                review.append(inbox_item(
                    repo, "gate-unknown",
                    f"{name}: gate matches no release (edited or foreign), sha256 {repo['gate']['sha256'][:12]}"))
            if repo["contract"]["status"] == "edited":
                review.append(inbox_item(repo, "contract-edited",
                                         f"{name}: managed AGENTS.md block matches no release (edited)"))
            if repo["contract"]["status"] == "malformed":
                review.append(inbox_item(repo, "contract-malformed",
                                         f"{name}: AGENTS.md has malformed managed block markers"))
        for found in repo["silent_replacements"]:
            when = f"on {found['date']}" if found["date"] else "uncommitted"
            review.append(inbox_item(
                repo, "silent-replacement",
                f"{name}: slice {found['from']} was replaced by {found['to']} ({when}) while awaiting the owner, "
                f"with no '## Owner decision' in evidence/{found['from']}/summary.md", **found))
        for item in repo["directives"]["expired_items"]:
            review.append(inbox_item(repo, "directive-expired",
                                     f"{name}: owner directive expired on {item['until']}: {item['text']}", **item))
        for risk in current["risks_due"]:
            review.append(inbox_item(repo, "risk-acceptance",
                                     f"{name}: risk {risk['id']} temporary acceptance {due_text(risk)}", **risk))
        branch = repo["update_branch"]
        if branch:
            command = f"git -C {shlex.quote(repo['path'])} merge --ff-only {shlex.quote(branch['branch'])}"
            note = "" if branch["fast_forward"] else " (HEAD has diverged: --ff-only will refuse)"
            inbox["ready_to_merge"].append(inbox_item(
                repo, "update-branch", f"{name}: update branch {branch['branch']} is not merged{note}. Run: {command}",
                command=command, **branch))
    return inbox


def summarize(repos: list[dict[str, Any]], inbox: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    v6 = [repo for repo in repos if repo["kind"] == "v6"]
    instances = [repo for repo in v6 if repo["role"] != "template"]  # gate and block are compared with the template
    with_git = [repo["git"] for repo in repos if repo["git"] is not None]
    dirty = [facts for facts in with_git if any(facts[key] for key in ("staged", "unstaged", "untracked"))]
    return {
        "repositories": len(repos),
        "kinds": {kind: sum(repo["kind"] == kind for repo in repos) for kind in KINDS},
        "with_git": len(with_git),
        "dirty": len(dirty),
        "gates": {state: sum(repo["gate"]["status"] == state for repo in instances) for state in GATE_STATES},
        "contracts": {state: sum(repo["contract"]["status"] == state for repo in instances)
                      for state in CONTRACT_STATES},
        "verdicts": {state: sum(repo["verdict"]["verdict"] == state for repo in v6) for state in VERDICTS},
        "size_flagged": sum(bool(repo["sizes"]["flags"]) for repo in v6),
        "notices": sum(repo["notices"]["total"] for repo in v6),
        "inbox": {section: len(items) for section, items in inbox.items()},
    }


def template_facts(ctx: Context) -> dict[str, Any]:
    latest = ctx.index.get("latest")
    latest_entry = next((entry for entry in ctx.index["releases"]
                         if isinstance(entry, dict) and entry.get("release") == latest), {})
    gate_sha = block_sha = None
    with contextlib.suppress(OSError):
        gate_sha = release_mod.sha256_file(ctx.template / release_mod.GATE_PATH)
    with contextlib.suppress(OSError):
        block_sha = release_mod.contract_sha256(release_mod.managed_block_text(ctx.template))
    return {
        "path": str(ctx.template),
        "state_schema": ctx.schema,
        "current_release": ctx.current,
        "latest_release": latest,
        "draft_release": latest if latest_entry.get("status") == "draft" else None,
        "gate_sha256": gate_sha,
        "contract_sha256": block_sha,
    }


def build_report(root: Path, ctx: Context, generated: str) -> dict[str, Any]:
    repos = []
    for path in discover(root):
        kind, payload, problem = classify(path, ctx.schema)
        repos.append(scan_repository(path, payload, kind, problem, ctx, path.resolve() == ctx.template))
    inbox = build_inbox(repos, ctx)
    return {
        "format": FORMAT,
        "generated": generated,
        "today": ctx.today.isoformat(),
        "read_only": True,
        "root": str(root),
        "template": template_facts(ctx),
        "summary": summarize(repos, inbox),
        "inbox": inbox,
        "repositories": repos,
    }


# --- rendering -------------------------------------------------------------------------------


def cell(value: Any) -> str:
    return ("" if value is None else str(value)).replace("|", "\\|").replace("\n", " ")


def table(headers: list[str], rows: list[list[Any]]) -> list[str]:
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join(" --- " for _ in headers) + "|"]
    lines.extend("| " + " | ".join(cell(value) for value in row) + " |" for row in rows)
    return lines


def status_label(info: dict[str, Any]) -> str:
    return f"{info['status']} ({info['release']})" if info["status"] == "behind" and info["release"] else info["status"]


def dirty_label(facts: dict[str, Any] | None) -> str:
    if facts is None:
        return "no git"
    if facts["staged"] is None:
        return "git error"
    parts = [f"{sign}{facts[key]}" for sign, key in (("+", "staged"), ("~", "unstaged"), ("?", "untracked"))
             if facts[key]]
    return " ".join(parts) or "clean"


def render_markdown(report: dict[str, Any]) -> str:
    template, summary = report["template"], report["summary"]
    release_text = template["current_release"] or "none released"
    if template["draft_release"]:
        release_text += f" (draft {template['draft_release']} in progress)"
    stamp = report["generated"] + (f", date set to {report['today']}" if report["generated"][:10] != report["today"] else "")
    lines = [
        "# ProjectState fleet",
        "",
        f"Generated {stamp}; template release {release_text}; root {report['root']}",
        "",
        "Read-only: no repository was modified.",
    ]
    for key, title in (("decisions", "Your decisions"), ("blocked", "Blocked"),
                       ("needs_review", "Needs review"), ("ready_to_merge", "Ready to merge")):
        items = report["inbox"][key]
        lines += ["", f"## {title} ({len(items)})", ""]
        lines += [f"- {item['message']}" for item in items] or ["None."]
    v6 = [repo for repo in report["repositories"] if repo["kind"] == "v6"]
    rows = []
    for repo in v6:
        current, history, sizes = repo["slice"], repo["history"], repo["sizes"]
        churn = (f"{history['state_commits']}/{history['all_commits']}"
                 if history["state_commits"] is not None and history["all_commits"] is not None else "?")
        rows.append([
            repo["name"] + (" (template)" if repo["role"] == "template" else ""),
            status_label(repo["gate"]), status_label(repo["contract"]), current["id"], current["status"],
            current["journey"], current["human_acceptance"],
            "?" if history["age_days"] is None else history["age_days"], churn,
            f"{sizes['startup_tokens']}{'!' if sizes['flags'] else ''}", repo["notices"]["total"],
            dirty_label(repo["git"]),
        ])
    lines += ["", f"## ProjectState v6 repositories ({len(v6)})", ""]
    lines += table(["repository", "gate", "contract", "slice", "status", "journey", "owner", "age days",
                    "STATE churn", "startup tokens", "notices", "dirty"], rows) if rows else ["None."]
    lines += ["", "Dirty: +staged ~unstaged ?untracked. STATE churn: STATE.yaml commits / all commits since the slice "
              "began. A trailing ! on startup tokens marks a size flag (see Summary)."]
    others = [repo for repo in report["repositories"] if repo["kind"] != "v6"]
    lines += ["", f"## v5 and other repositories ({len(others)})", ""]
    lines += table(["repository", "kind", "last commit", "dirty"], [
        [repo["name"], repo["kind"], (repo["git"] or {}).get("last_commit") or "-", dirty_label(repo["git"])]
        for repo in others]) if others else ["None."]
    lines += ["", "## Summary", ""]
    kinds = ", ".join(f"{kind} {summary['kinds'][kind]}" for kind in KINDS)
    lines += [
        f"- Repositories: {summary['repositories']} ({kinds}); {summary['with_git']} with git, {summary['dirty']} dirty.",
        "- v6 gates (template excluded): " + ", ".join(f"{state} {summary['gates'][state]}" for state in GATE_STATES)
        + ".",
        "- v6 contracts (template excluded): "
        + ", ".join(f"{state} {summary['contracts'][state]}" for state in CONTRACT_STATES) + ".",
        "- v6 gate verdicts: " + ", ".join(f"{state} {summary['verdicts'][state]}" for state in VERDICTS) + ".",
        "- Inbox: " + ", ".join(f"{len(report['inbox'][key])} {label}" for key, label in (
            ("decisions", "decisions"), ("blocked", "blocked"), ("needs_review", "to review"),
            ("ready_to_merge", "ready to merge"))) + ".",
        f"- Refresh notices in v6 repositories: {summary['notices']}.",
    ]
    flagged = [(repo["name"], flag) for repo in v6 for flag in repo["sizes"]["flags"]]
    lines.append(f"- Size flags: {len(flagged)}" + ("." if not flagged else ":"))
    lines += [f"  - {name}: {flag}" for name, flag in flagged]
    broken = [(repo["name"], repo["problem"]) for repo in report["repositories"] if repo["kind"] == "v6-invalid"]
    lines.append(f"- Unreadable STATE.yaml: {len(broken)}" + ("." if not broken else ":"))
    lines += [f"  - {name}: {problem}" for name, problem in broken]
    failing = [(repo["name"], repo["git"]["error"]) for repo in report["repositories"]
               if repo["git"] is not None and repo["git"]["error"]]
    lines.append(f"- Git problems: {len(failing)}" + ("." if not failing else ":"))
    lines += [f"  - {name}: {problem}" for name, problem in failing]
    # Repository text is untrusted: never let it drive the terminal that prints the report.
    return CONTROL_CHARS.sub("?", "\n".join(lines) + "\n")


def render_json(report: dict[str, Any]) -> str:
    return json.dumps(report, indent=2, ensure_ascii=False) + "\n"


def summary_line(report: dict[str, Any]) -> str:
    summary = report["summary"]
    kinds = ", ".join(f"{kind} {summary['kinds'][kind]}" for kind in KINDS)
    inbox = summary["inbox"]
    return (f"fleet: {summary['repositories']} repositories ({kinds}); inbox: {inbox['decisions']} decisions, "
            f"{inbox['blocked']} blocked, {inbox['needs_review']} to review, {inbox['ready_to_merge']} ready to merge")


# --- command line ----------------------------------------------------------------------------


def write_atomic(path: Path, text: str) -> None:
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(temporary)
        raise


def is_inside(path: Path, parent: Path) -> bool:
    return path == parent or parent in path.parents


def date_argument(value: str) -> dt.date:
    parsed = parse_date(value)
    if parsed is None:
        raise argparse.ArgumentTypeError(f"not a YYYY-MM-DD date: {value!r}")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Read-only ProjectState fleet doctor: release, drift, size and owner inbox for every repository "
                    "under a root folder. Never writes inside a repository.")
    parser.add_argument("--root", help="Folder whose immediate children are scanned (default: the template's parent)")
    parser.add_argument("--template", help="Template repository holding releases/index.json (default: this one)")
    parser.add_argument("--out", help=f"Directory for fleet.md and fleet.json (default: {DEFAULT_OUT}); "
                                      "must be outside --root")
    parser.add_argument("--stdout", action="store_true", help="Print one report and write nothing")
    parser.add_argument("--format", choices=("md", "json"), default="md", help="Report format for --stdout")
    parser.add_argument("--today", type=date_argument, help="Override today's date (YYYY-MM-DD), for tests")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    template = Path(args.template).expanduser().resolve() if args.template else release_mod.TEMPLATE_ROOT
    root = Path(args.root).expanduser().resolve() if args.root else template.parent
    if not root.is_dir():
        print(f"fleet: --root is not a directory: {root}", file=sys.stderr)
        return 2
    out = Path(args.out or DEFAULT_OUT).expanduser().resolve()
    if (not args.stdout or args.out) and is_inside(out, root):
        print(f"fleet: refusing to write inside the scanned root: --out {out} is inside --root {root}",
              file=sys.stderr)
        return 2
    try:
        index = release_mod.load_index(template)
        current = release_mod.current_release(index)
    except (OSError, ValueError, KeyError) as exc:
        print(f"fleet: cannot read the release index of {template}: {exc}", file=sys.stderr)
        return 2
    ctx = Context(template, index, str(index.get("state_schema") or gate_mod.VERSION),
                  str(current["release"]) if current else None, args.today or dt.date.today())
    report = build_report(root, ctx, dt.datetime.now().astimezone().isoformat(timespec="seconds"))
    if args.stdout:
        sys.stdout.write(render_json(report) if args.format == "json" else render_markdown(report))
        return 0
    try:
        out.mkdir(parents=True, exist_ok=True)
        write_atomic(out / "fleet.md", render_markdown(report))
        write_atomic(out / "fleet.json", render_json(report))
    except OSError as exc:
        print(f"fleet: cannot write the report to {out}: {exc}", file=sys.stderr)
        return 1
    print(out / "fleet.md")
    print(out / "fleet.json")
    print(summary_line(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
