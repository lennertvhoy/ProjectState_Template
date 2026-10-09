#!/usr/bin/env python3
"""Run the slice's primary journey and record what happened, so the state files are observed, not asserted.

    python3 scripts/projectstate_verify.py [--root DIR] [--run] [--timeout SECONDS]

An agent that types ``Result: passed`` into the records can be wrong, and the next session (or the owner) then
steers by a false anchor. This command runs the journey command recorded in ``STATE.yaml`` and writes the outcome
itself: ``current_slice.primary_journey.status`` and ``validation.primary_journey`` (passed on exit 0, otherwise
failed), and ``Command``, ``Environment``, ``Result``, ``Exit code`` and ``Verified`` in the evidence summary, plus
``last-journey-run.txt`` with the output tail. STATE.yaml is edited in place so quoting and comments survive.

Without ``--run`` it only prints what it would execute. The command is run through ``bash -c`` from the repository
root with the caller's environment: running it is exactly as trusted as typing it yourself, so use ``--run`` only in a
repository whose recorded command you would run. A failed journey downgrades a ``validated`` or ``ready_for_human``
slice to ``implementing``. An ``accepted`` slice is never altered (the command reports the failure and exits 2: tell
the owner). If the gate reports any new error after the edit, every file is restored byte for byte.

Exit codes: 0 journey passed and recorded; 1 journey failed and recorded; 2 refused, or rolled back, nothing recorded.
This is not the gate: the gate stays read-only and never executes anything.
"""

from __future__ import annotations

import argparse
import copy
import datetime as dt
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, NamedTuple

try:
    import projectstate_gate as gatelib
except ModuleNotFoundError:  # pragma: no cover - pytest package import path
    from scripts import projectstate_gate as gatelib

RECORDED_BY = "scripts/projectstate_verify.py"
ARTIFACT = "last-journey-run.txt"
DEFAULT_TIMEOUT = 900
TAIL_LINES = 60
TAIL_BYTES = 6000
CLOSED_BEFORE_PASS = ("validated", "ready_for_human")
PLACEHOLDER = re.compile(r"not yet defined|^\s*(todo|tbd)\b", re.IGNORECASE)
KEY_LINE = re.compile(r"^(?P<key>[A-Za-z0-9_.-]+):(?P<rest>.*)$")
VALUE_LINE = re.compile(
    r"^(?P<head>[ ]*[A-Za-z0-9_.-]+:[ \t]*)"
    r"(?P<token>\"[^\"\\]*\"|'[^']*'|[^\s\"'#][^\s#]*)"
    r"(?P<tail>[ \t]*|[ \t]+#.*)$"
)
SECTION = re.compile(r"^##\s+(.+?)\s*$")


class Refused(Exception):
    def __init__(self, reasons: list[str]) -> None:
        super().__init__("; ".join(reasons))
        self.reasons = reasons


class Entry(NamedTuple):
    index: int
    indent: int
    key: str


class Outcome(NamedTuple):
    code: int
    seconds: float
    timed_out: bool
    tail: str


# --- reading the instance ---------------------------------------------------------------------------------------


def regular(root: Path, relative: str) -> Path:
    """A file inside ``root`` reached without a symlink; refuse anything else."""
    current = root
    for part in Path(relative).parts:
        current = current / part
        if current.is_symlink():
            raise Refused([f"{relative} is reached through a symlink; refusing to read or write it"])
    if not current.is_file():
        raise Refused([f"{relative} is missing or not a regular file"])
    return current


def journey_of(payload: dict[str, Any]) -> tuple[str, str, str, str]:
    try:
        current = payload["current_slice"]
        journey = current["primary_journey"]
        slice_id, status = str(current["id"]), str(current["status"])
        command, environment = str(journey["command"]).strip(), str(journey["environment"]).strip()
    except (KeyError, TypeError) as error:
        raise Refused([f"STATE.yaml has no usable current_slice.primary_journey ({error})"]) from error
    if not command or PLACEHOLDER.search(command):
        raise Refused(["the primary journey command is empty or still a placeholder; record the real command first"])
    return slice_id, status, command, environment


# --- running the journey ------------------------------------------------------------------------------------------


def run_journey(command: str, root: Path, timeout: float) -> Outcome:
    shell = "bash" if shutil.which("bash") else "sh"
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    started = dt.datetime.now(dt.timezone.utc)
    try:
        process = subprocess.Popen(
            [shell, "-c", command], cwd=root, env=env, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, errors="replace", start_new_session=True,
        )
    except OSError as error:
        return Outcome(127, 0.0, False, f"cannot start {shell}: {error}")
    timed_out = False
    try:
        output, _ = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        output, _ = process.communicate()
    seconds = (dt.datetime.now(dt.timezone.utc) - started).total_seconds()
    tail = "\n".join(output.splitlines()[-TAIL_LINES:])[-TAIL_BYTES:]
    code = 124 if timed_out else process.returncode
    return Outcome(code, seconds, timed_out, tail)


# --- editing STATE.yaml in place ----------------------------------------------------------------------------------


def entries_of(lines: list[str]) -> list[Entry]:
    found: list[Entry] = []
    for index, raw in enumerate(lines):
        body = raw.splitlines()[0] if raw.splitlines() else ""
        if not body.strip() or body.lstrip().startswith("#"):
            continue
        stripped = body.lstrip(" ")
        match = KEY_LINE.match(stripped)
        found.append(Entry(index, len(body) - len(stripped), match["key"] if match else ""))
    return found


def locate(entries: list[Entry], path: tuple[str, ...]) -> Entry:
    """The line holding the nested key ``path`` in a plain block mapping."""
    scope = entries
    current: Entry | None = None
    for key in path:
        top = scope[0].indent if scope else 0
        matches = [entry for entry in scope if entry.indent == top and entry.key == key]
        if len(matches) != 1:
            raise Refused([f"cannot edit STATE.yaml in place: expected one '{key}:' line at its level, found {len(matches)}"])
        current = matches[0]
        start = scope.index(current) + 1
        block: list[Entry] = []
        for entry in scope[start:]:
            if entry.indent <= current.indent:
                break
            block.append(entry)
        scope = block
    assert current is not None
    return current


def retarget(body: str, new: str, label: str) -> str:
    match = VALUE_LINE.match(body)
    if match is None:
        raise Refused([f"cannot edit {label} in place: unsupported line {body.strip()!r}"])
    token = match["token"]
    quote = token[0] if token[0] in "\"'" else ""
    return f"{match['head']}{quote}{new}{quote}{match['tail']}"


def edit_state(text: str, payload: dict[str, Any], status: str, downgrade: bool) -> str:
    lines = text.splitlines(keepends=True)
    entries = entries_of(lines)
    changes: list[tuple[tuple[str, ...], str]] = [
        (("current_slice", "primary_journey", "status"), status),
        (("validation", "primary_journey"), status),
    ]
    expected = copy.deepcopy(payload)
    expected["current_slice"]["primary_journey"]["status"] = status
    expected["validation"]["primary_journey"] = status
    if downgrade:
        changes.append((("current_slice", "status"), "implementing"))
        expected["current_slice"]["status"] = "implementing"
    for path, new in changes:
        entry = locate(entries, path)
        body = lines[entry.index].splitlines()[0]
        lines[entry.index] = retarget(body, new, ".".join(path)) + lines[entry.index][len(body):]
    new_text = "".join(lines)
    try:
        reparsed = gatelib.parse_state(new_text)
    except gatelib.StateSyntaxError as error:
        raise Refused([f"the edited STATE.yaml no longer parses ({error}); nothing was written"]) from error
    if reparsed != expected:
        raise Refused(["the edited STATE.yaml differs in more than the journey fields; nothing was written"])
    return new_text


# --- editing the evidence summary ---------------------------------------------------------------------------------


def edit_summary(text: str, command: str, environment: str, result: str, outcome: Outcome, when: str) -> str:
    newline = "\r\n" if "\r\n" in text and "\n" not in text.replace("\r\n", "") else "\n"
    lines = text.replace("\r\n", "\n").split("\n")
    heads = [(i, SECTION.match(line)) for i, line in enumerate(lines)]
    heads = [(i, m.group(1).strip().lower()) for i, m in heads if m]
    names = [name for _, name in heads]
    if names.count("primary journey") != 1 or "artifacts" not in names:
        raise Refused(["the evidence summary needs one '## Primary journey' and one '## Artifacts' section"])
    start = next(i for i, name in heads if name == "primary journey")
    end = next((i for i, _ in heads if i > start), len(lines))
    wanted = {
        "Environment": environment,
        "Command": f"`{command}`",
        "Result": result,
        "Exit code": str(outcome.code),
        "Verified": f"{when} by {RECORDED_BY} in {outcome.seconds:.1f}s" + (" (timed out)" if outcome.timed_out else ""),
    }
    section = [line for line in lines[start + 1:end]]
    for label, value in wanted.items():
        pattern = re.compile(rf"^-\s+{re.escape(label)}:", re.IGNORECASE)
        hits = [i for i, line in enumerate(section) if pattern.match(line)]
        replacement = f"- {label}: {value}"
        if hits:
            section[hits[0]] = replacement
            for extra in reversed(hits[1:]):
                del section[extra]
        else:
            insert_at = max((i for i, line in enumerate(section) if line.strip()), default=-1) + 1
            section.insert(insert_at, replacement)
    lines[start + 1:end] = section
    lines = add_artifact_line(lines)
    return "\n".join(lines).replace("\n", newline)


def add_artifact_line(lines: list[str]) -> list[str]:
    """Name the run output under ## Artifacts (once), dropping the scaffold's '- None recorded.' placeholder."""
    heads = [(i, m.group(1).strip().lower()) for i, m in ((i, SECTION.match(line)) for i, line in enumerate(lines)) if m]
    start = next(i for i, name in heads if name == "artifacts")
    stop = next((i for i, _ in heads if i > start), len(lines))
    body = [line for line in lines[start + 1:stop] if line.strip() and line.strip() != "- None recorded."]
    if not any(ARTIFACT in line for line in body):
        body.append(f"- {ARTIFACT}: output of the most recent verified journey run.")
    return lines[:start + 1] + ["", *body, ""] + lines[stop:]


# --- writing -------------------------------------------------------------------------------------------------------


def write_atomic(path: Path, data: bytes, mode: int) -> None:
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


def artifact_text(command: str, outcome: Outcome, when: str) -> str:
    status = "timed out" if outcome.timed_out else f"exit code {outcome.code}"
    return f"# {RECORDED_BY}\n# command: {command}\n# finished: {when}\n# {status} after {outcome.seconds:.1f}s\n\n{outcome.tail}\n"


def record(root: Path, args: argparse.Namespace) -> int:
    state_path = regular(root, "STATE.yaml")
    state_text = state_path.read_bytes().decode("utf-8")
    try:
        payload = gatelib.parse_state(state_text)
    except gatelib.StateSyntaxError as error:
        raise Refused([f"STATE.yaml does not parse: {error}"]) from error
    slice_id, status, command, environment = journey_of(payload)
    summary_path = regular(root, f"evidence/{slice_id}/summary.md")
    print(f"slice {slice_id} ({status})\n  command:     {command}\n  environment: {environment}\n  run from:    {root}")
    if not args.run:
        print("dry run: nothing executed. Re-run with --run to execute the command and record the result.")
        return 0
    before_errors, _blockers, _warn = gatelib.validate(root)
    outcome = run_journey(command, root, args.timeout)
    passed = outcome.code == 0
    if not passed and status == "accepted":
        print(f"the journey FAILED (exit {outcome.code}) but the slice is accepted; nothing recorded. Tell the owner.", file=sys.stderr)
        return 2
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    new_state = edit_state(state_text, payload, "passed" if passed else "failed", downgrade=(not passed and status in CLOSED_BEFORE_PASS))
    summary_old = summary_path.read_bytes()
    new_summary = edit_summary(summary_old.decode("utf-8"), command, environment, "passed" if passed else "failed", outcome, now)
    artifact_path = summary_path.parent / ARTIFACT
    artifact_old = artifact_path.read_bytes() if artifact_path.is_file() else None
    originals = [(state_path, state_text.encode("utf-8"), state_path.stat().st_mode & 0o777),
                 (summary_path, summary_old, summary_path.stat().st_mode & 0o777)]

    def restore() -> None:
        for path, original, mode in originals:
            write_atomic(path, original, mode)
        if artifact_old is None:
            artifact_path.unlink(missing_ok=True)
        else:
            write_atomic(artifact_path, artifact_old, 0o644)

    try:
        write_atomic(state_path, new_state.encode("utf-8"), originals[0][2])
        write_atomic(summary_path, new_summary.encode("utf-8"), originals[1][2])
        write_atomic(artifact_path, artifact_text(command, outcome, now).encode("utf-8"), 0o644)
        after_errors, _blockers, _warn = gatelib.validate(root)
        added = [error for error in after_errors if error not in before_errors]
        if added:
            raise Refused([f"the gate reports new errors after recording: {'; '.join(added)}"])
    except Refused:
        restore()
        raise
    except OSError as error:
        restore()
        raise Refused([f"write failed ({error}); everything was restored"]) from error
    verdict = "PASSED" if passed else ("TIMED OUT" if outcome.timed_out else f"FAILED (exit {outcome.code})")
    print(f"journey {verdict} in {outcome.seconds:.1f}s; recorded in STATE.yaml and evidence/{slice_id}/summary.md")
    if not passed and status in CLOSED_BEFORE_PASS:
        print(f"slice status downgraded from {status} to implementing")
    if not passed:
        print("--- output tail ---\n" + "\n".join(outcome.tail.splitlines()[-15:]))
    return 0 if passed else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the primary journey and record the observed result")
    parser.add_argument("--root", default=".", help="Repository root (default: current directory)")
    parser.add_argument("--run", action="store_true", help="Execute the recorded command (without it, only print the plan)")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT, help="Seconds before the journey is killed")
    args = parser.parse_args(argv)
    try:
        return record(Path(args.root).resolve(), args)
    except Refused as error:
        for reason in error.reasons:
            print(f"refused: {reason}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
