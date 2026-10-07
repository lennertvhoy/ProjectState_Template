#!/usr/bin/env python3
"""Record the owner's decision on the current slice with one command.

    python3 scripts/projectstate_decide.py TARGET {accept,reject,waive} "OWNER WORDS"
        [--date YYYY-MM-DD] [--slice ID] [--dry-run] [--allow-dirty]

The fleet doctor prints this command for every validated slice that waits for the owner, so
recording a decision no longer means hand-editing STATE.yaml. The command appends an
``## Owner decision`` record (decision, date, the owner's words) to the slice's evidence summary
and changes exactly two things in STATE.yaml, edited in place so quoting and comments survive:
``validation.human_acceptance`` and, for ``accept``, ``current_slice.status``. It never commits.

It refuses with exit 2 and a reason, writing nothing, unless the instance is in the state the
gate describes for a pending decision: ``STATE.yaml`` parses with the template gate and has its
schema version; the decision is still ``pending`` (a recorded decision is never overwritten); the
slice status and journey allow the decision (accept: validated or ready_for_human with a passed
journey; waive: validated or ready_for_human; reject: any status but accepted); the owner's words
and date are usable; the slice summary is a regular file reached without a symlink and has no
``## Owner decision`` yet; the gate reports no errors; and, inside a git work tree, STATE.yaml and
the summary have no uncommitted changes (``--allow-dirty`` skips only that last check).

Both files are written atomically, then the template gate validates the result in-process. Any gate
error restores both files byte for byte and exits 2. The gate checks records only: this command
cannot tell who typed the owner's words, and it runs no instance code (only read-only ``git``).
"""

from __future__ import annotations

import argparse
import copy
import datetime as dt
import os
import re
import stat
import subprocess
import sys
import tempfile
import unicodedata
from pathlib import Path, PurePosixPath
from typing import Any, NamedTuple

try:
    import projectstate_gate as gatelib
except ModuleNotFoundError:  # pragma: no cover - pytest package import path
    from scripts import projectstate_gate as gatelib


DECISIONS = {"accept": "accepted", "reject": "rejected", "waive": "waived"}
AWAITING_STATUSES = ("validated", "ready_for_human")
STATE_NAME = "STATE.yaml"
RECORDED_BY = "scripts/projectstate_decide.py"
GIT_TIMEOUT_SECONDS = 30
SLICE_ID = re.compile(r"[a-z0-9][a-z0-9-]*")
DATE_TEXT = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
KEY_LINE = re.compile(r"^(?P<key>[A-Za-z0-9_.-]+):(?P<rest>.*)$")
# `key: value` with a plain, "double" or 'single' quoted scalar and an optional trailing comment.
VALUE_LINE = re.compile(
    r"^(?P<head>[ ]*[A-Za-z0-9_.-]+:[ \t]*)"
    r"(?P<token>\"[^\"\\]*\"|'[^']*'|[^\s\"'#][^\s#]*)"
    r"(?P<tail>[ \t]*|[ \t]+#.*)$"
)
GIT_LOCATION_VARIABLES = (
    "GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY", "GIT_COMMON_DIR", "GIT_NAMESPACE",
)


class Refused(Exception):
    """The decision cannot be recorded; the reasons say why and the files are as they were."""

    def __init__(self, reasons: list[str]) -> None:
        super().__init__("; ".join(reasons))
        self.reasons = reasons


class Edit(NamedTuple):
    number: int  # 1-based line number in STATE.yaml
    old: str
    new: str


class Entry(NamedTuple):
    """One significant line of STATE.yaml: comments and blank lines are skipped, as the gate skips them."""

    index: int  # position in the physical line list
    indent: int
    key: str  # empty for lines that are not `key:` lines
    rest: str


class Plan(NamedTuple):
    target: Path
    decision: str
    slice_id: str
    date: str
    state_path: Path
    state_old: bytes
    state_new: bytes
    state_mode: int
    edits: list[Edit]
    summary_rel: str
    summary_path: Path
    summary_old: bytes
    summary_new: bytes
    summary_mode: int
    section: str
    warnings: list[str]


# --- Preconditions -------------------------------------------------------------------------


def mapping_at(value: Any, *path: str) -> Any:
    for key in path:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


def local_file(target: Path, relative: PurePosixPath) -> Path:
    """The regular file ``target/relative``; refused when any component below the target is a symlink."""
    current = target
    try:
        for part in relative.parts:
            current = current / part
            if current.is_symlink():
                raise Refused([f"{relative} is symlinked at {part!r}; refusing to read or write through a symlink"])
        if not current.is_file():
            raise Refused([f"{relative} is missing or not a regular file"])
    except OSError as exc:
        raise Refused([f"cannot inspect {relative}: {exc}"]) from exc
    return current


def read_file(path: Path, label: str) -> tuple[bytes, str]:
    try:
        data = path.read_bytes()
        return data, data.decode("utf-8")
    except OSError as exc:
        raise Refused([f"cannot read {label}: {exc}"]) from exc
    except UnicodeDecodeError as exc:
        raise Refused([f"{label} is not valid UTF-8: {exc}"]) from exc


def owner_words(raw: str) -> str:
    """The owner's words as one line that fits inside the record's double quotes."""
    words = " ".join(raw.split())  # every run of whitespace, newlines included, becomes one space
    if not any(char != " " and char not in gatelib.QUOTE_CHARS for char in words):
        raise Refused(["owner words are empty; record what the owner said (quotes and spaces do not count)"])
    if any(unicodedata.category(char) == "Cc" for char in words):
        raise Refused(["owner words contain control characters; they are recorded verbatim, so they are refused"])
    try:
        words.encode("utf-8")
    except UnicodeEncodeError:
        raise Refused(["owner words are not valid UTF-8 text"]) from None
    return words.replace('"', "'")


def decision_date(raw: str | None) -> str:
    today = dt.date.today()
    if raw is None:
        return today.isoformat()
    try:
        when = dt.date.fromisoformat(raw) if DATE_TEXT.fullmatch(raw) else None
    except ValueError:
        when = None
    if when is None:
        raise Refused([f"--date must be a real calendar date as YYYY-MM-DD, not {raw!r}"])
    if when > today:
        raise Refused([f"--date {raw} is in the future (today is {today.isoformat()})"])
    return when.isoformat()


def has_owner_decision(summary: str) -> bool:
    """Whether the summary has an ``## Owner decision`` section by the gate's own heading rule."""
    visible = re.sub(r"<!--.*?-->", "", summary, flags=re.DOTALL)
    return any(
        match.group(1).strip().lower() == "owner decision"
        for match in re.finditer(r"^##\s+(.+?)\s*$", visible, re.MULTILINE)
    )


def git_env() -> dict[str, str]:
    env = {key: value for key, value in os.environ.items() if key not in GIT_LOCATION_VARIABLES}
    env.update(GIT_OPTIONAL_LOCKS="0", GIT_TERMINAL_PROMPT="0", LC_ALL="C")
    return env


def run_git(target: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """One read-only git command in ``target`` (no pager, no fsmonitor daemon, no optional locks)."""
    return subprocess.run(
        ["git", "--no-pager", "-C", str(target), "-c", "core.fsmonitor=false", *args],
        capture_output=True, text=True, errors="replace", check=False, env=git_env(), stdin=subprocess.DEVNULL,
        timeout=GIT_TIMEOUT_SECONDS,
    )


def check_clean(target: Path, relatives: list[str]) -> None:
    """Refuse when git reports changes to the files this command writes; read-only git only."""
    skip = "use --allow-dirty to skip the check"
    try:
        inside = run_git(target, "rev-parse", "--is-inside-work-tree")
    except FileNotFoundError:
        return  # without git there is no work tree to protect
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise Refused([f"cannot inspect git status ({exc}); {skip}"]) from exc
    if inside.returncode != 0:
        if "not a git repository" in inside.stderr:
            return
        raise Refused([f"cannot inspect git status ({inside.stderr.strip()}); {skip}"])
    if inside.stdout.strip() != "true":
        return
    try:
        status = run_git(target, "status", "--porcelain", "--", *relatives)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise Refused([f"cannot inspect git status ({exc}); {skip}"]) from exc
    if status.returncode != 0:
        raise Refused([f"git status failed ({status.stderr.strip()}); {skip}"])
    dirty = [line.strip() for line in status.stdout.splitlines() if line.strip()]
    if dirty:
        raise Refused([
            f"uncommitted changes in {' or '.join(relatives)} ({'; '.join(dirty)}); "
            "commit or stash them first, or pass --allow-dirty"
        ])


def gate_report(target: Path) -> tuple[list[str], list[str]]:
    """Errors and blockers from the template gate; a crash in the gate counts as an error."""
    try:
        errors, blockers, _ = gatelib.validate(target)
    except Exception as exc:  # a decision must never be left half recorded because the gate failed
        return [f"the gate failed: {exc!r}"], []
    return list(errors), list(blockers)


def stale_gate_warning(target: Path, decision: str) -> str | None:
    """`waived` is new in 6.3.0: a vendored gate that predates it calls the recorded state invalid."""
    if decision != "waived":
        return None
    relative = PurePosixPath("scripts") / "projectstate_gate.py"
    try:
        text = local_file(target, relative).read_text(encoding="utf-8")
    except (Refused, OSError, UnicodeDecodeError):
        return None
    if '"waived"' in text:
        return None
    return (f"{relative} in the target predates 'waived' (template release 6.3.0); its own gate will report "
            "validation.human_acceptance invalid until the instance is updated with projectstate_update.py")


# --- Planning the edits --------------------------------------------------------------------


def mapping_entries(lines: list[str]) -> list[Entry]:
    entries: list[Entry] = []
    for index, raw in enumerate(lines):
        body = raw.splitlines()[0]
        if not body.strip() or body.lstrip().startswith("#"):
            continue
        stripped = body.lstrip(" ")
        match = KEY_LINE.match(stripped)
        entries.append(Entry(index, len(body) - len(stripped),
                             match["key"] if match else "", match["rest"] if match else ""))
    return entries


def find_entry(entries: list[Entry], parent: str, key: str) -> Entry:
    """The ``key:`` line directly under the top-level block mapping ``parent:``."""
    top = entries[0].indent
    parents = [number for number, entry in enumerate(entries) if entry.indent == top and entry.key == parent]
    if len(parents) != 1 or not re.fullmatch(r"\s*(?:#.*)?", entries[parents[0]].rest):
        raise Refused([f"cannot edit STATE.yaml in place: {parent!r} is not a plain top-level block mapping"])
    block: list[Entry] = []
    for entry in entries[parents[0] + 1:]:
        if entry.indent <= top:
            break
        block.append(entry)
    inner = block[0].indent if block else top
    found = [entry for entry in block if entry.indent == inner and entry.key == key]
    if len(found) != 1:
        raise Refused([f"cannot edit STATE.yaml in place: expected one '{key}:' line directly under "
                       f"'{parent}:', found {len(found)}"])
    return found[0]


def retarget(body: str, old: str, new: str, label: str) -> str:
    """``body`` with its scalar value ``old`` replaced by ``new``, keeping the quote style and any comment."""
    match = VALUE_LINE.match(body)
    if match is None:
        raise Refused([f"cannot edit {label} in place: unsupported line {body.strip()!r}"])
    token = match["token"]
    quote = token[0] if token[0] in "\"'" else ""
    if token[len(quote):len(token) - len(quote)] != old:
        raise Refused([f"cannot edit {label} in place: the line does not hold the plain value {old!r}"])
    return f"{match['head']}{quote}{new}{quote}{match['tail']}"


def edit_state(text: str, payload: dict[str, Any], decision: str, status: str) -> tuple[str, list[Edit]]:
    """STATE.yaml text with the decision lines changed in place, verified against the parsed original."""
    lines = text.splitlines(keepends=True)
    entries = mapping_entries(lines)
    changes = [("validation", "human_acceptance", "pending", decision)]
    if decision == "accepted":
        changes.append(("current_slice", "status", status, "accepted"))
    edits: list[Edit] = []
    for parent, key, old, new in changes:
        entry = find_entry(entries, parent, key)
        body = lines[entry.index].splitlines()[0]
        ending = lines[entry.index][len(body):]
        changed = retarget(body, old, new, f"{parent}.{key}")
        edits.append(Edit(entry.index + 1, body, changed))
        lines[entry.index] = changed + ending
    new_text = "".join(lines)
    expected = copy.deepcopy(payload)
    expected["validation"]["human_acceptance"] = decision
    if decision == "accepted":
        expected["current_slice"]["status"] = "accepted"
    try:
        reparsed = gatelib.parse_state(new_text)
    except gatelib.StateSyntaxError as exc:
        raise Refused([f"the edited STATE.yaml no longer parses ({exc}); nothing was written"]) from exc
    if reparsed != expected:
        raise Refused(["the edited STATE.yaml differs from the original in more than the decision fields; "
                       "nothing was written"])
    return new_text, sorted(edits)


def line_ending(text: str) -> str:
    """CRLF only when every line break of the file is CRLF; otherwise LF."""
    return "\r\n" if "\r\n" in text and "\n" not in text.replace("\r\n", "") else "\n"


def owner_section(decision: str, date: str, words: str, newline: str) -> str:
    lines = [
        "## Owner decision",
        "",
        f"- Decision: {decision}",
        f"- Date: {date}",
        f'- Owner words: "{words}"',
        f"- Recorded by: {RECORDED_BY}",
    ]
    return "".join(line + newline for line in lines)


def append_section(text: str, section: str, newline: str) -> str:
    """``text`` untouched, then one blank line (added only when missing), then the section."""
    breaks = text[len(text.rstrip("\r\n")):].count("\n")
    return text + newline * max(0, 2 - breaks) + section


def build_plan(args: argparse.Namespace) -> Plan:
    """Check every precondition and compute both new files. Nothing is written."""
    decision = DECISIONS[args.decision]
    target = Path(args.target).expanduser()
    if not target.is_dir():
        raise Refused([f"target is not a directory: {args.target}"])
    target = target.resolve()

    state_path = local_file(target, PurePosixPath(STATE_NAME))
    state_old, state_text = read_file(state_path, STATE_NAME)
    try:
        payload = gatelib.parse_state(state_text)
    except gatelib.StateSyntaxError as exc:
        raise Refused([f"cannot parse {STATE_NAME}: {exc}"]) from exc
    version = payload.get("version")
    if version != gatelib.VERSION:
        raise Refused([f"{STATE_NAME} version is {version!r}, not {gatelib.VERSION!r}"])
    slice_id = mapping_at(payload, "current_slice", "id")
    status = mapping_at(payload, "current_slice", "status")
    journey = mapping_at(payload, "current_slice", "primary_journey", "status")
    human = mapping_at(payload, "validation", "human_acceptance")
    if not isinstance(slice_id, str) or not SLICE_ID.fullmatch(slice_id):
        raise Refused(["current_slice.id must be lowercase letters, digits, and hyphens"])
    if not isinstance(status, str):
        raise Refused(["current_slice.status must be text"])
    if args.slice_id is not None and args.slice_id != slice_id:
        raise Refused([f"--slice {args.slice_id!r} is not the current slice {slice_id!r}"])
    if human != "pending":
        raise Refused([f"validation.human_acceptance is {human!r}, not pending; "
                       "a recorded decision is never overwritten"])
    if decision in {"accepted", "waived"} and status not in AWAITING_STATUSES:
        raise Refused([f"{args.decision} needs current_slice.status validated or ready_for_human, not {status!r}"])
    if decision == "accepted" and journey != "passed":
        raise Refused([f"accept needs the primary journey to be passed, not {journey!r}"])
    if decision == "rejected" and status == "accepted":
        raise Refused(["reject is refused: current_slice.status is already accepted"])
    words = owner_words(args.words)
    date = decision_date(args.date)

    summary_rel = PurePosixPath("evidence") / slice_id / "summary.md"
    evidence = mapping_at(payload, "current_slice", "primary_journey", "evidence")
    if evidence != summary_rel.as_posix():
        raise Refused([f"current_slice.primary_journey.evidence must be {summary_rel.as_posix()}, not {evidence!r}"])
    summary_path = local_file(target, summary_rel)
    summary_old, summary_text = read_file(summary_path, summary_rel.as_posix())
    if has_owner_decision(summary_text):
        raise Refused([f"{summary_rel} already has an ## Owner decision section; it is never overwritten"])
    if not args.allow_dirty:
        check_clean(target, [STATE_NAME, summary_rel.as_posix()])
    errors, _ = gate_report(target)
    if errors:
        raise Refused(["the gate already reports errors in this repository, so no decision is recorded on top "
                       "of them; nothing was changed", *[f"gate error: {error}" for error in errors]])

    state_new_text, edits = edit_state(state_text, payload, decision, status)
    newline = line_ending(summary_text)
    section = owner_section(decision, date, words, newline)
    summary_new = append_section(summary_text, section, newline).encode("utf-8")
    warning = stale_gate_warning(target, decision)
    return Plan(
        target, decision, slice_id, date,
        state_path, state_old, state_new_text.encode("utf-8"), stat.S_IMODE(state_path.stat().st_mode), edits,
        summary_rel.as_posix(), summary_path, summary_old, summary_new, stat.S_IMODE(summary_path.stat().st_mode),
        section, [warning] if warning else [],
    )


# --- Writing -------------------------------------------------------------------------------


def write_atomic(path: Path, data: bytes, mode: int) -> None:
    """Write beside the target, then os.replace; the original survives any failure."""
    handle, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(tmp_path, mode)
        os.replace(tmp_path, path)
    except BaseException:
        tmp_path.unlink(missing_ok=True)
        raise


def restore(plan: Plan) -> list[str]:
    """Put both files back exactly as they were read; return what could not be restored."""
    failed: list[str] = []
    for path, original, mode in (
        (plan.state_path, plan.state_old, plan.state_mode),
        (plan.summary_path, plan.summary_old, plan.summary_mode),
    ):
        try:
            if not path.is_file() or path.read_bytes() != original:
                write_atomic(path, original, mode)
            if path.read_bytes() != original:
                failed.append(f"{path.name} still differs from the original")
        except OSError as exc:
            failed.append(f"{path.name}: {exc}")
    return failed


def restore_note(failed: list[str]) -> list[str]:
    if failed:
        return ["RESTORE FAILED, inspect the working tree (git diff) before anything else:", *failed]
    return ["both files were restored byte for byte"]


def write_decision(plan: Plan) -> list[str]:
    """Write both files, validate the result with the gate, and undo everything on any error.

    Returns the gate's remaining blockers (empty when the recorded outcome is validated).
    """
    for path, original in ((plan.state_path, plan.state_old), (plan.summary_path, plan.summary_old)):
        try:
            unchanged = not path.is_symlink() and path.read_bytes() == original
        except OSError:
            unchanged = False
        if not unchanged:
            raise Refused([f"{path.name} changed while the decision was being prepared; nothing was written"])
    try:
        write_atomic(plan.summary_path, plan.summary_new, plan.summary_mode)
        write_atomic(plan.state_path, plan.state_new, plan.state_mode)
        errors, blockers = gate_report(plan.target)
    except BaseException as exc:
        failed = restore(plan)
        if isinstance(exc, OSError):
            raise Refused([f"write failed: {exc}", *restore_note(failed)]) from exc
        raise
    if errors:
        raise Refused(["the gate rejects the recorded decision", *[f"gate error: {error}" for error in errors],
                       *restore_note(restore(plan))])
    return blockers


# --- Reporting -----------------------------------------------------------------------------


def render_plan(plan: Plan) -> list[str]:
    lines = ["dry run: nothing was written"]
    for edit in plan.edits:
        lines += [f"{STATE_NAME} line {edit.number}:", f"-{edit.old}", f"+{edit.new}"]
    lines += [f"{plan.summary_rel}: append, after one blank line:", *plan.section.splitlines()]
    return lines


def render_result(plan: Plan, blockers: list[str]) -> list[str]:
    fields = ["validation.human_acceptance"] + (["current_slice.status"] if plan.decision == "accepted" else [])
    outcome = f"outcome not validated: {blockers[0]}" if blockers else "recorded outcome validated"
    return [
        f"recorded: {plan.decision} for slice {plan.slice_id} on {plan.date}",
        f"{STATE_NAME}: {' and '.join(fields)} set to {plan.decision}",
        f"{plan.summary_rel}: ## Owner decision appended",
        f"gate: no errors ({outcome})",
        "the fleet doctor will stop listing this slice in your decisions",
        "nothing was committed: review with git diff, then commit these two files",
    ]


# --- Command line --------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="projectstate_decide.py",
        description="Record the owner's accept, reject or waive decision on the current validated slice. "
                    "Edits STATE.yaml in place and appends '## Owner decision' to the slice summary; never commits.",
    )
    parser.add_argument("target", metavar="TARGET", help="Repository root of the ProjectState instance")
    parser.add_argument("decision", choices=list(DECISIONS), help="What the owner decided")
    parser.add_argument("words", metavar="OWNER_WORDS", help="What the owner said, in the owner's words")
    parser.add_argument("--date", metavar="YYYY-MM-DD",
                        help="Date of the decision (default: today; never in the future)")
    parser.add_argument("--slice", dest="slice_id", metavar="ID", help="Refuse unless this is the current slice id")
    parser.add_argument("--dry-run", action="store_true", help="Print the planned changes and write nothing")
    parser.add_argument("--allow-dirty", action="store_true",
                        help="Skip the git check for uncommitted changes to STATE.yaml and the slice summary")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        plan = build_plan(args)
        for warning in plan.warnings:
            print(f"warning: {warning}", file=sys.stderr)
        if args.dry_run:
            print("\n".join(render_plan(plan)))
            return 0
        blockers = write_decision(plan)
    except Refused as exc:
        for reason in exc.reasons:
            print(f"refused: {reason}", file=sys.stderr)
        return 2
    print("\n".join(render_result(plan, blockers)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
