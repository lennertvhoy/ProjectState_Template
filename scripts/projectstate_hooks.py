#!/usr/bin/env python3
"""Keep the owner's own words in front of every session, and offer them once for the durable files.

    python3 scripts/projectstate_hooks.py install --root DIR [--dry-run] [--no-stop] [--host claude|opencode|all]
    python3 scripts/projectstate_hooks.py uninstall --root DIR [--dry-run] [--host claude|opencode|all]
    python3 scripts/projectstate_hooks.py show [--root DIR]
    python3 scripts/projectstate_hooks.py record   # Claude Code UserPromptSubmit hook (reads hook JSON on stdin)
    python3 scripts/projectstate_hooks.py brief    # Claude Code SessionStart hook (prints one context block)
    python3 scripts/projectstate_hooks.py stop     # Claude Code Stop hook (prints at most one block decision)

This is the v2 of ``scripts/projectstate_owner_log.py`` in one self-contained file that gets copied into
instances. It keeps v1's log location and entry format (``.projectstate/owner-log.md`` with
``## <UTC stamp> (session <key>)`` headings; a Claude Code UUID id keeps v1's 8-character key, any other
host's id is kept whole up to 40 characters, see ``session_key``), so logs written by v1 keep working.

What v2 changes. (1) ``record`` replaces each pasted block (Claude Code 2.1.x wraps pastes as
``<pasted_content id="..">..</pasted_content id="..">``, the closing tag repeating the id) with one line
``[pasted text, N characters, not the owner's words: "<first 80 characters, one line>"]``: pastes are usually
reports, logs or web text the owner did not write, and replaying them as the owner's words is a prompt-injection
path. An unclosed paste marker runs to the end of the prompt. The owner's typed words stay verbatim, with v1's
secret redaction, size caps and duplicate suppression. (2) ``brief`` replaces v1's small newest-only window
with a compact block, hard-capped at 6000 characters: the standing words the owner already wrote down
(``## Durable constraints`` in PROJECT.md, then ``.projectstate/standing.md``), the current slice from
STATE.yaml including whether a journey result was recorded by a run or typed by hand, the owner's earlier
words that may set standing rules (framed as context, not a task list), and the owner's most recent requests,
each marked as possibly already done.
(3) ``stop`` notices, once per entry, when this session's words read as standing instructions and are not yet
written down, and asks the agent to file them before it finishes.

"Reads as a standing instruction" comes in two sets, both deterministic and conservative, matching
case-insensitively and on word boundaries over the owner's typed words only (paste summaries excluded).
The BROAD set - always, never, must (not), do not / don't / dont, only, from now on, every time,
whenever, by default, make sure, prefer(s), instead of, rather than, constraint(s), requirement(s),
rule(s) - selects candidates. The brief's standing pool and log trimming then drop the one-off fix and
change requests the broad set admits: an entry carrying a one-off cue (please, just, for now, whichever,
this session, this run, again) is treated as a one-off however rule-shaped its markers look - measured on
a week of realistic prompts, "wrap it instead of truncating please" and "if that happens again just wrap
the line" landed in the standing pool this way and agents implemented them. The STOP set keeps only
directive words - always, never, must (not), from now on, every time, whenever, by default, make sure,
prefer(s), instead of, rather than: nouns like "constraints" also appear in questions ABOUT rules, and a
stop block there derails the session's final message. Session-scoped limits ("not yet", "later",
"only X this session") can still match and are sorted out by the wording of the stop request, not by magic.

``stop`` runs two checks after every turn. Each log entry is offered at most once (stamps in
``.projectstate/offered.json``); there is no per-session limit, because a session spans many owner turns
and words stated in turn 5 must still be offered after turn 1. The block reason ends with a note to
repeat a final line a caller requires (a line starting RESULT or BRIEF), so a blocked turn does not
break a calling harness. And when STATE.yaml and the gate script exist at the root, it runs
``scripts/projectstate_gate.py`` read-only (no shell, 20 s timeout): exit 0 or 1 is silent, exit 2
(invalid records) blocks once per distinct gate output, quoting its first 15 lines and asking the agent
to fix the records it wrote; the output's hash is stored in offered.json. A gate that times out or
cannot run is silent (a note on stderr).

``install`` merges into ``.claude/settings.json`` without removing anything - while replacing v1's hooks,
so recording does not duplicate entries - and copies the opencode plugin to ``.opencode/plugins/``
(plural; 1.18.x also loads the singular ``.opencode/plugin/``, which ``uninstall`` removes as a leftover).
When the instance already carries a copy that differs from this tool's, it is replaced only when its
sha256 matches a released ``hooks_sha256`` (tool) or ``opencode_plugin_sha256`` (plugin) in the release
index beside this tool (``<tool dir>/../releases/index.json``, so a copy running inside an instance
finds none); anything else is a local edit and is refused with exit 2 unless ``--replace-edited`` is
given. Without an index the old behaviour stands and a note is printed.
``uninstall`` removes exactly the hooks and files install added and keeps the log.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

LOG_DIR = ".projectstate"
LOG_NAME = "owner-log.md"
STANDING_NAME = "standing.md"
OFFERED_NAME = "offered.json"
RELEASE_INDEX = Path("releases") / "index.json"
HOOKS_SHA_FIELD = "hooks_sha256"
PLUGIN_SHA_FIELD = "opencode_plugin_sha256"
OPENCODE_PLUGIN_DIR = ".opencode/plugins"
OPENCODE_PLUGIN_LEGACY_DIR = ".opencode/plugin"
OPENCODE_PLUGIN_NAME = "projectstate.js"
OPENCODE_PLUGIN_SOURCE = "projectstate_opencode_plugin.js"
MAX_ENTRY_CHARS = 8000
MAX_LOG_BYTES = 64 * 1024
MIN_PROMPT_CHARS = 3
BRIEF_CHARS = 6000
STANDING_CHARS = 1200
SLICE_CHARS = 1400
POOL_CHARS = 2400
REQUESTS_CHARS = 900
REQUESTS_COUNT = 3
REQUEST_KEEP = 240
ABBRIDGED_KEEP = 280
LINE_KEEP = 300
STOP_REASON_CHARS = 4000
HOOK_MARK = "projectstate_hooks.py"
V1_MARK = "projectstate_owner_log.py"
CLOSED_FOR_HUMAN = ("validated", "ready_for_human")
CLAIMED_JOURNEY = ("passed", "failed", "blocked")
ENTRY_HEAD = re.compile(r"^## (\d{4}-\d{2}-\d{2}T[\d:]+Z) \(session ([^)]*)\)\s*$", re.MULTILINE)
PASTE_OPENER = re.compile(r'<pasted_content\s+id="([^"]+)">')
VERIFIED_LINE = re.compile(r"^-\s+Verified:\s*(\d{4}-\d{2}-\d{2}T[\d:]+Z)\b", re.MULTILINE)
SECTION_HEAD = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
DURABLE_HEAD = re.compile(r"^##\s+durable constraints\s*$", re.IGNORECASE | re.MULTILINE)
BULLET = re.compile(r"^\s*[-*]\s+(.+?)\s*$")
STANDING_MARKERS = re.compile(
    r"\b(?:always|never|must\s+not|must|do\s+not|don't|dont|only|from\s+now\s+on|every\s+time|whenever|"
    r"by\s+default|make\s+sure|prefers?|instead\s+of|rather\s+than|constraints?|requirements?|rules?)\b",
    re.IGNORECASE,
)
STRONG_MARKERS = re.compile(
    r"\b(?:always|never|must\s+not|must|from\s+now\s+on|every\s+time|whenever|by\s+default|make\s+sure|"
    r"prefers?|instead\s+of|rather\s+than)\b",
    re.IGNORECASE,
)
ONEOFF_CUES = re.compile(
    r"\b(?:please|just|for now|whichever|this session|this run|again)\b",
    re.IGNORECASE,
)
REDACTIONS = (
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.DOTALL), "[redacted private key]"),
    (re.compile(r"\b(?:sk-[A-Za-z0-9_-]{16,}|gh[pousr]_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|xox[baprs]-[A-Za-z0-9-]{10,})\b"), "[redacted token]"),
    (re.compile(r"(?i)\b(password|passwd|secret|token|api[_-]?key)(\s*[:=]\s*)\S+"), r"\1\2[redacted]"),
)
HOOKS = {
    "SessionStart": f'python3 "$CLAUDE_PROJECT_DIR"/scripts/{HOOK_MARK} brief',
    "UserPromptSubmit": f'python3 "$CLAUDE_PROJECT_DIR"/scripts/{HOOK_MARK} record',
    "Stop": f'python3 "$CLAUDE_PROJECT_DIR"/scripts/{HOOK_MARK} stop',
}
DECIDE_USAGE = 'python3 scripts/projectstate_decide.py . accept|reject|waive "<owner words>"'
FINAL_LINE_NOTE = ("If your previous final message ended with a line a caller requires (for example a line starting "
                   "RESULT or BRIEF), end this reply with that same line again, unchanged.")
BRIEF_HEADER = ("ProjectState session brief: the owner's standing words, the current slice, and the owner's recent "
                "words from the local log. PROJECT.md, STATE.yaml and evidence/ remain the source of truth.")
STANDING_TITLE = "THE OWNER'S STANDING WORDS (from PROJECT.md ## Durable constraints and .projectstate/standing.md):"
SLICE_TITLE = "CURRENT SLICE (from STATE.yaml):"
WORDS_TITLE = ("THE OWNER'S EARLIER WORDS THAT MAY SET STANDING RULES (from the local log, newest first; "
               "not a request for this session):")
WORDS_SCOPE = ("Context, not a task list: act on a word below only when this session's work touches it, and do not "
               "implement old requests that are not in STATE.yaml's next_action. Constraints and decisions about HOW "
               "things are built stay in force until the owner changes them; a limit on what a past session should do "
               "(scope, 'not now', 'later') applied to that session only.")
REQUESTS_TITLE = ("THE OWNER'S MOST RECENT REQUESTS (earlier sessions may already have done them; check git log "
                  "and STATE.yaml before acting, and follow this session's request):")


# --- shared plumbing --------------------------------------------------------------------------------------------


def find_root(start: Path) -> Path:
    """The nearest ancestor holding STATE.yaml or .git; otherwise ``start`` itself."""
    for candidate in (start, *start.parents):
        if (candidate / "STATE.yaml").is_file() or (candidate / ".git").exists():
            return candidate
    return start


def redact(text: str) -> str:
    for pattern, replacement in REDACTIONS:
        text = pattern.sub(replacement, text)
    return text


def log_path(root: Path) -> Path:
    return root / LOG_DIR / LOG_NAME


def write_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    tmp_path = Path(name)
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
        os.replace(tmp_path, path)
    except BaseException:
        tmp_path.unlink(missing_ok=True)
        raise


def read_text(path: Path) -> str:
    """The file's text, or "" when it is missing, a symlink or unreadable."""
    if path.is_symlink() or not path.is_file():
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def normalize(text: str) -> str:
    return " ".join(text.split()).lower()


SESSION_UUID = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")


def session_key(session_id: str) -> str:
    """The log's session key, shared by record and stop.

    A Claude Code session id is a UUID: keep its first 8 characters, exactly as v1 did, so v1 logs stay
    compatible. Any other host's id is not safe to shorten - OpenCode ids are time-ordered
    (``ses_edf3a6802ffe..``, ``ses_edf3a3765ffe..``) and 8 characters collide across sessions started close
    together - so it is kept whole, capped at 40 characters, with ')' and newlines removed so the entry
    heading still parses. Empty ids become "unknown".
    """
    key = str(session_id or "").replace(")", "").replace("\r", "").replace("\n", "").strip()
    if SESSION_UUID.fullmatch(key):
        return key[:8]
    return key[:40] or "unknown"


def contained(body: str, blob: str) -> bool:
    return bool(blob) and normalize(body) in normalize(blob)


def abbreviate(text: str) -> str:
    if len(text) <= 2 * ABBRIDGED_KEEP + 8:
        return text
    return text[:ABBRIDGED_KEEP] + " [...] " + text[-ABBRIDGED_KEEP:]


def entry_of(text: str) -> list[tuple[str, str, str]]:
    """(timestamp, session, body) for each entry, oldest first."""
    heads = list(ENTRY_HEAD.finditer(text))
    found = []
    for index, head in enumerate(heads):
        end = heads[index + 1].start() if index + 1 < len(heads) else len(text)
        found.append((head.group(1), head.group(2), text[head.end():end].strip()))
    return found


def render_entry(stamp: str, session: str, body: str) -> str:
    return f"## {stamp} (session {session})\n\n{body}\n\n"


# --- recording: pastes are not the owner's words -------------------------------------------------------------------


def paste_note(content: str) -> str:
    preview = re.sub(r"\s+", " ", content[:80]).strip()
    return f"[pasted text, {len(content)} characters, not the owner's words: \"{preview}\"]"


def replace_pastes(text: str) -> str:
    """Replace each pasted block with one summary line; an unclosed marker runs to the end of the text."""
    out: list[str] = []
    position = 0
    for opener in PASTE_OPENER.finditer(text):
        if opener.start() < position:
            continue  # inside a span that is already replaced
        closer = re.compile(rf'</pasted_content(?:\s+id="{re.escape(opener.group(1))}")?>').search(text, opener.end())
        end = closer.start() if closer else len(text)
        out.append(text[position:opener.start()])
        out.append(paste_note(text[opener.end():end]))
        position = closer.end() if closer else len(text)
    out.append(text[position:])
    return "".join(out)


def append_entry(root: Path, prompt: str, session: str, now: dt.datetime | None = None) -> bool:
    """Append one owner prompt; return False when it is too short, repeated or the log cannot be written safely."""
    body = redact(replace_pastes(prompt.strip()))
    if len(body) < MIN_PROMPT_CHARS:
        return False
    if len(body) > MAX_ENTRY_CHARS:
        body = body[:MAX_ENTRY_CHARS] + "\n[truncated]"
    directory = root / LOG_DIR
    if directory.is_symlink() or log_path(root).is_symlink():
        return False
    path = log_path(root)
    existing = read_text(path)
    found = entry_of(existing)
    if found and found[-1][1] == session and found[-1][2] == body:
        return False
    stamp = (now or dt.datetime.now(dt.timezone.utc)).strftime("%Y-%m-%dT%H:%M:%SZ")
    kept = found + [(stamp, session, body)]
    text = "# Owner log\n\nThe owner's words, verbatim and oldest first. Recorded by scripts/projectstate_hooks.py.\n\n"
    rendered = [render_entry(*entry) for entry in kept]
    while len(rendered) > 1 and len((text + "".join(rendered)).encode("utf-8")) > MAX_LOG_BYTES:
        # trim oldest entries that do not read as standing first; standing words go last
        drop = next((index for index, entry in enumerate(kept) if not reads_pool(entry[2])), 0)
        kept.pop(drop)
        rendered = [render_entry(*entry) for entry in kept]
    directory.mkdir(parents=True, exist_ok=True)
    gitignore = directory / ".gitignore"
    if not gitignore.exists():
        gitignore.write_text("*\n", encoding="utf-8")
    write_atomic(path, text + "".join(rendered))
    return True


def reads_standing(body: str) -> bool:
    return bool(STANDING_MARKERS.search(body))


def reads_strong(body: str) -> bool:
    return bool(STRONG_MARKERS.search(body))


def reads_oneoff(body: str) -> bool:
    """A one-off fix or change request: veto cues outweigh standing markers.

    Measured on the durability eval's noise week: requests like "wrap it instead of truncating please"
    or "if that happens again just wrap the line" carry standing markers (instead of, dont) but are
    one-off asks; the cues please / just / for now / whichever / this session / this run / again catch
    them without touching the directive-shaped rules ("always keep the readme short",
    "dont touch journey.py").
    """
    return bool(ONEOFF_CUES.search(body))


def reads_pool(body: str) -> bool:
    """What belongs in the brief's standing pool (and what trimming keeps): standing and not one-off."""
    return reads_standing(body) and not reads_oneoff(body)


# --- the brief: standing words, slice view, earlier words ----------------------------------------------------------


def durable_bullets(project_text: str) -> list[str]:
    """The bullet lines under PROJECT.md's ## Durable constraints, verbatim."""
    head = DURABLE_HEAD.search(project_text)
    if not head:
        return []
    rest = project_text[head.end():]
    stop = SECTION_HEAD.search(rest)
    section = rest[:stop.start()] if stop else rest
    return [match.group(1) for line in section.splitlines() if (match := BULLET.match(line))]


def standing_words(root: Path) -> tuple[list[str], str]:
    """The owner's standing words already written down, as display lines plus one normalized blob."""
    lines = durable_bullets(read_text(root / "PROJECT.md"))
    lines += [line for line in map(str.strip, read_text(root / LOG_DIR / STANDING_NAME).splitlines()) if line]
    seen: set[str] = set()
    out: list[str] = []
    for line in lines:
        key = normalize(line)
        if not key or key in seen:
            continue
        seen.add(key)
        shown = line if len(line) <= LINE_KEEP else line[:LINE_KEEP] + " [...]"
        out.append(f"- {shown}")
    blob_lines: list[str] = []
    used = 0
    for line in out:
        if used + len(line) > STANDING_CHARS:
            break
        blob_lines.append(line)
        used += len(line) + 1
    return blob_lines, normalize("\n".join(blob_lines))


def import_gate():
    """The gate module from the tool's own directory, when it is present."""
    here = str(Path(__file__).resolve().parent)
    if here not in sys.path:
        sys.path.insert(0, here)
    try:
        import projectstate_gate
        return projectstate_gate
    except Exception:
        return None


def commits_since(root: Path, when: str) -> str:
    try:
        done = subprocess.run(
            ["git", "-C", str(root), "rev-list", "--count", f"--since={when}", "HEAD"],
            capture_output=True, text=True, check=True, timeout=10,
        )
        count = int(done.stdout.strip() or "0")
    except Exception:
        return "commit count unavailable"
    return f"{count} commit(s) made since"


def journey_freshness(root: Path, slice_id: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", slice_id) or ".." in slice_id:
        return "journey status was typed by hand, not recorded by a run"
    summary = read_text(root / "evidence" / slice_id / "summary.md")
    match = VERIFIED_LINE.search(summary)
    if not match:
        return "journey status was typed by hand, not recorded by a run"
    return f"journey run recorded {match.group(1)}; {commits_since(root, match.group(1))}"


def slice_section(root: Path) -> str:
    state_path = root / "STATE.yaml"
    if not state_path.is_file():
        return ""
    payload = None
    problem = ""
    try:
        gate = import_gate()
        if gate is None:
            problem = "scripts/projectstate_gate.py is missing next to the tool"
        else:
            payload = gate.parse_state(state_path.read_text(encoding="utf-8"))
    except Exception as error:
        problem = str(error) or error.__class__.__name__
    if problem:
        return f"{SLICE_TITLE}\n- STATE.yaml could not be read: {problem}\n"
    current = payload.get("current_slice") if isinstance(payload, dict) else None
    if not isinstance(current, dict):
        return f"{SLICE_TITLE}\n- STATE.yaml could not be read: no current_slice mapping\n"
    lines: list[str] = []
    slice_id = str(current.get("id") or "?")
    lines.append(f"- slice: {slice_id}")
    objective = str(current.get("objective") or "")
    if objective:
        lines.append(f"- objective: {abbreviate(objective)}")
    status = str(current.get("status") or "?")
    lines.append(f"- status: {status}")
    journey = current.get("primary_journey") if isinstance(current.get("primary_journey"), dict) else {}
    journey_status = str(journey.get("status") or "?")
    journey_line = f"- primary journey: {journey_status}"
    command = str(journey.get("command") or "")
    if command:
        journey_line += f" - `{abbreviate(command)}`"
    if journey_status in CLAIMED_JOURNEY:
        journey_line += f" ({journey_freshness(root, slice_id)})"
    lines.append(journey_line)
    next_action = str(payload.get("next_action") or "") if isinstance(payload, dict) else ""
    if next_action:
        lines.append(f"- next_action: {abbreviate(next_action)}")
    validation = payload.get("validation") if isinstance(payload, dict) else None
    pending = (status in CLOSED_FOR_HUMAN
               and isinstance(validation, dict) and str(validation.get("human_acceptance") or "") == "pending")
    if pending:
        pending_line = "- An owner decision is pending for this slice (accept, reject or waive)."
        if (root / "scripts" / "projectstate_decide.py").is_file():
            pending_line += f" Record it with: {DECIDE_USAGE}"
        lines.append(pending_line)
    body: list[str] = []
    used = 0
    for line in lines:
        if used + len(line) > SLICE_CHARS:
            break
        body.append(line)
        used += len(line) + 1
    return f"{SLICE_TITLE}\n" + "\n".join(body) + "\n"


def shorten(text: str, keep: int) -> str:
    if len(text) <= keep:
        return text
    return text[:keep - len(" [...]")] + " [...]"


def words_sections(root: Path, standing_blob: str) -> tuple[str, str]:
    """The owner's words from the log: standing ones not yet in the files, then the most recent requests.

    The newest-verbatim window is gone: a wall of recent prompts reads like a to-do list and fresh agents
    name an old request as the next action. Standing entries (broad set, not already contained in the
    durable files) come first, newest first; then at most three recent non-standing entries, each cut to
    REQUEST_KEEP characters, explicitly marked as possibly already done.
    """
    found = entry_of(read_text(log_path(root)))
    if not found:
        return "", ""
    pool: list[str] = []
    used = len(WORDS_TITLE) + len(WORDS_SCOPE) + 3
    for index in range(len(found) - 1, -1, -1):
        stamp, _session, body = found[index]
        if not reads_pool(body) or contained(body, standing_blob):
            continue
        block = f"[{stamp}] {body}"
        if used + len(block) + 1 <= POOL_CHARS:
            pool.append(block)
            used += len(block) + 1
            continue
        short = f"[{stamp}] {abbreviate(body)}"
        if used + len(short) + 1 <= POOL_CHARS:
            pool.append(short)
            continue
        break
    requests: list[str] = []
    used = len(REQUESTS_TITLE) + 2
    taken = 0
    for index in range(len(found) - 1, -1, -1):
        if taken >= REQUESTS_COUNT:
            break
        stamp, _session, body = found[index]
        if reads_pool(body):
            continue  # standing entries live in the pool; one-off-vetoed ones belong here
        block = f"[{stamp}] {shorten(body, REQUEST_KEEP)}"
        if used + len(block) + 1 > REQUESTS_CHARS:
            break
        requests.append(block)
        used += len(block) + 1
        taken += 1
    pool_text = f"{WORDS_TITLE}\n{WORDS_SCOPE}\n" + "\n---\n".join(pool) + "\n" if pool else ""
    requests_text = f"{REQUESTS_TITLE}\n" + "\n---\n".join(requests) + "\n" if requests else ""
    return pool_text, requests_text


def brief_text(root: Path) -> str:
    parts = [BRIEF_HEADER]
    standing_lines, standing_blob = standing_words(root)
    if standing_lines:
        parts.append(STANDING_TITLE + "\n" + "\n".join(standing_lines))
    slice_block = slice_section(root)
    if slice_block:
        parts.append(slice_block)
    used = sum(len(part) + 1 for part in parts)
    remaining = BRIEF_CHARS - used
    pool_text, requests_text = words_sections(root, standing_blob)
    pool_room = max(remaining - (len(requests_text) + 1 if requests_text else 0), 0)
    if pool_text and len(pool_text) <= pool_room:
        parts.append(pool_text)
        remaining -= len(pool_text) + 1
    if requests_text and len(requests_text) <= remaining:
        parts.append(requests_text)
    text = "\n".join(parts)
    if len(text) > BRIEF_CHARS:
        text = text[:BRIEF_CHARS - len("\n[truncated]\n")] + "\n[truncated]\n"
    return text


# --- the stop hook: offer this session's standing words once --------------------------------------------------------


def offered_state(root: Path) -> dict:
    data = read_text(root / LOG_DIR / OFFERED_NAME)
    try:
        parsed = json.loads(data) if data else {}
    except ValueError:
        parsed = {}
    if not isinstance(parsed, dict):
        parsed = {}
    stamps = parsed.get("offered")
    sessions = parsed.get("sessions")
    hashes = parsed.get("gate_hashes")
    return {
        "offered": [str(stamp) for stamp in stamps] if isinstance(stamps, list) else [],
        "sessions": {str(key): [str(s) for s in value] for key, value in sessions.items()}
        if isinstance(sessions, dict) else {},
        "gate_hashes": [str(item) for item in hashes] if isinstance(hashes, list) else [],
    }


def save_offered(root: Path, state: dict, session: str, stamps: list[str], gate_hash: str | None = None) -> None:
    state["offered"] = sorted(set(state["offered"]) | set(stamps))
    state["sessions"] = {**state["sessions"], session: sorted(set(state["sessions"].get(session, [])) | set(stamps))}
    if gate_hash:
        state["gate_hashes"] = sorted(set(state["gate_hashes"]) | {gate_hash})
    directory = root / LOG_DIR
    if directory.is_symlink():
        return
    directory.mkdir(parents=True, exist_ok=True)
    write_atomic(root / LOG_DIR / OFFERED_NAME, json.dumps(state, indent=2, sort_keys=True) + "\n")


def standing_target(root: Path) -> tuple[str, str]:
    """Where durable words belong: (already-written text to check, human-readable place)."""
    project = read_text(root / "PROJECT.md")
    if project:
        return durable_bullets_text(project), 'PROJECT.md under "## Durable constraints"'
    return read_text(root / LOG_DIR / STANDING_NAME), f'"{LOG_DIR}/{STANDING_NAME}"'


def durable_bullets_text(project_text: str) -> str:
    return "\n".join(durable_bullets(project_text))


GATE_TIMEOUT_S = 20
GATE_REASON_LINES = 15


def gate_block(root: Path, state: dict) -> dict | None:
    """Run the gate read-only; a dict when it reports invalid records and that output was never blocked."""
    if not (root / "STATE.yaml").is_file() or not (root / "scripts" / "projectstate_gate.py").is_file():
        return None
    try:
        done = subprocess.run(
            [sys.executable, "scripts/projectstate_gate.py"], cwd=root,
            capture_output=True, text=True, timeout=GATE_TIMEOUT_S,
            env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"),
        )
    except (subprocess.TimeoutExpired, OSError) as error:
        print(f"projectstate_hooks: gate skipped: {error}", file=sys.stderr)
        return None
    if done.returncode == 2:
        output = (done.stdout + done.stderr).strip()
    elif done.returncode in (0, 1):
        return None  # honest and valid, or honestly not closure-ready: not the agent's problem at stop
    else:
        print(f"projectstate_hooks: gate skipped: unexpected exit {done.returncode}", file=sys.stderr)
        return None
    digest = hashlib.sha256(output.encode("utf-8")).hexdigest()
    if digest in state["gate_hashes"]:
        return None
    return {"output": output, "hash": digest}


def stop_decision(root: Path, payload: dict) -> str | None:
    """One block decision when the gate reports invalid records or this session's words look standing and
    were never offered; else None. Each entry is offered at most once - there is no per-session limit."""
    if payload.get("stop_hook_active"):
        return None
    session = session_key(str(payload.get("session_id") or ""))
    if not session or session == "unknown":
        return None
    state = offered_state(root)
    gate = gate_block(root, state)
    target, place = standing_target(root)
    mine = [entry for entry in entry_of(read_text(log_path(root))) if entry[1] == session]
    candidates = [
        entry for entry in mine
        if reads_strong(entry[2]) and entry[0] not in state["offered"] and not contained(entry[2], target)
    ]
    if gate is None and not candidates:
        return None
    reasons = []
    if candidates:
        quoted = "\n".join(f'- "{abbreviate(entry[2])}" (owner, {entry[0][:10]})' for entry in candidates)
        reasons.append(
            "The owner said this in the current session. Before you finish: if any of the quoted words below is a "
            "standing constraint or a decision about HOW this project is built or run, add it to "
            f"{place}, verbatim and quoted, each followed by \"(owner, YYYY-MM-DD)\". Leave out one-off requests and "
            "limits on what a past session should do (for example \"not yet\", \"later\", \"only X this session\"). "
            f"Then finish.\n\n{quoted}"
        )
    if gate is not None:
        head = "\n".join(gate["output"].splitlines()[:GATE_REASON_LINES])
        reasons.append(
            "The ProjectState gate reports invalid records (exit 2). Fix the records you wrote before you "
            f"finish; the gate stays read-only. It says:\n{head}"
        )
    reason = "\n\n".join(reasons)
    room = STOP_REASON_CHARS - len(FINAL_LINE_NOTE) - 2
    if len(reason) > room:
        reason = reason[:room - len("\n[truncated]")] + "\n[truncated]"
    reason += "\n\n" + FINAL_LINE_NOTE
    save_offered(root, state, session, [entry[0] for entry in candidates], gate["hash"] if gate else None)
    return json.dumps({"decision": "block", "reason": reason})


# --- hook plumbing --------------------------------------------------------------------------------------------------


def hook_input() -> dict:
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except (ValueError, OSError):
        return {}
    return payload if isinstance(payload, dict) else {}


def hook_root(payload: dict) -> Path:
    return find_root(Path(str(payload.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())).resolve())


def hook_commands(include_stop: bool) -> dict[str, str]:
    return {event: command for event, command in HOOKS.items() if include_stop or event != "Stop"}


def merge_settings(existing: dict, include_stop: bool) -> tuple[dict, list[str], list[str]]:
    """Add this tool's hooks to a Claude Code settings mapping, keeping everything already there.

    v1 owner-log hook entries are replaced so recording does not duplicate entries. Returns the merged
    mapping, the events added for this tool and the events where a v1 hook was replaced.
    """
    merged = json.loads(json.dumps(existing))
    hooks = merged.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        raise ValueError("'hooks' in .claude/settings.json is not an object")
    replaced: list[str] = []
    for event in list(HOOKS):
        groups = hooks.get(event)
        if not isinstance(groups, list):
            continue
        kept_groups: list[dict] = []
        for group in groups:
            if not isinstance(group, dict) or not isinstance(group.get("hooks"), list):
                kept_groups.append(group)
                continue
            inner = group["hooks"]
            keep = [hook for hook in inner
                    if not (isinstance(hook, dict) and V1_MARK in str(hook.get("command", "")))]
            if len(keep) != len(inner):
                replaced.append(event)
            if keep:
                fresh = dict(group)
                fresh["hooks"] = keep
                kept_groups.append(fresh)
        if kept_groups:
            hooks[event] = kept_groups
        else:
            del hooks[event]
    added: list[str] = []
    for event, command in hook_commands(include_stop).items():
        groups = hooks.setdefault(event, [])
        if not isinstance(groups, list):
            raise ValueError(f"hooks.{event} in .claude/settings.json is not a list")
        present = any(HOOK_MARK in str(hook.get("command", "")) for group in groups if isinstance(group, dict)
                      for hook in group.get("hooks", []) if isinstance(hook, dict))
        if not present:
            groups.append({"hooks": [{"type": "command", "command": command}]})
            added.append(event)
    for event in list(hooks):
        if isinstance(hooks[event], list) and not hooks[event]:
            del hooks[event]
    if not hooks:
        merged.pop("hooks", None)
    return merged, added, replaced


def same_file(left: Path, right: Path) -> bool:
    try:
        return left.resolve() == right.resolve()
    except OSError:
        return False


def released_asset_hashes(template_root: Path) -> dict[str, list[str]] | None:
    """Released asset hashes by index field from ``<template root>/releases/index.json``.

    ``template_root`` is the directory above the running tool's own directory, so a copy running
    inside an instance finds no index there: the caller then replaces without a released-version
    check (with a note). An index that exists but cannot be parsed raises ValueError, so the caller
    refuses instead of overwriting on top of an unreadable record. Draft entries authorize nothing.
    """
    path = template_root / RELEASE_INDEX
    if path.is_symlink() or not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        entries = payload.get("releases") if isinstance(payload, dict) else None
        if not isinstance(entries, list):
            raise ValueError("releases is not a list")
    except (OSError, ValueError) as error:
        raise ValueError(f"cannot read {path}: {error}") from error
    hashes: dict[str, list[str]] = {HOOKS_SHA_FIELD: [], PLUGIN_SHA_FIELD: []}
    for entry in entries:
        if not isinstance(entry, dict) or entry.get("status") != "released":
            continue
        for field in hashes:
            value = entry.get(field)
            if isinstance(value, str) and value not in hashes[field]:
                hashes[field].append(value)
    return hashes


def edited_copy_refusal(path: Path, label: str, released: list[str], root: Path) -> str | None:
    """A refusal line when ``path`` matches no released version; None when replacing it is allowed."""
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest in released:
        return None
    return (f"refused: {label} in {root} was edited locally (sha256 {digest[:12]} matches no released version); "
            "review it, then pass --replace-edited to replace it")


def install(root: Path, dry_run: bool, include_stop: bool, host: str, replace_edited: bool = False) -> int:
    own = Path(__file__).resolve()
    tool = root / "scripts" / HOOK_MARK
    settings = root / ".claude" / "settings.json"
    plugin_source = own.parent / OPENCODE_PLUGIN_SOURCE
    plugin_target = root / OPENCODE_PLUGIN_DIR / OPENCODE_PLUGIN_NAME
    want_claude = host in ("claude", "all")
    want_opencode = host in ("opencode", "all")
    if want_claude and ((root / ".claude").is_symlink() or settings.is_symlink()):
        print("refused: .claude/settings.json is reached through a symlink", file=sys.stderr)
        return 2
    if (root / "scripts").is_symlink() or tool.is_symlink():
        print("refused: scripts/ or the tool path is a symlink", file=sys.stderr)
        return 2
    if want_opencode:
        if not plugin_source.is_file():
            print(f"refused: {OPENCODE_PLUGIN_SOURCE} is missing next to this tool; it is needed for --host opencode",
                  file=sys.stderr)
            return 2
        if plugin_target.is_symlink() or plugin_target.parent.is_symlink():
            print("refused: the opencode plugin path is reached through a symlink", file=sys.stderr)
            return 2
    merged = added = replaced = None
    if want_claude:
        try:
            existing = json.loads(settings.read_text(encoding="utf-8")) if settings.is_file() else {}
            if not isinstance(existing, dict):
                raise ValueError("it is not a JSON object")
            merged, added, replaced = merge_settings(existing, include_stop)
        except (ValueError, OSError) as error:
            print(f"refused: cannot merge into {settings}: {error}", file=sys.stderr)
            return 2
    copy_tool = want_claude and (not tool.is_file() or (tool.read_bytes() != own.read_bytes() and not same_file(tool, own)))
    copy_plugin = want_opencode and (not plugin_target.is_file() or plugin_target.read_bytes() != plugin_source.read_bytes())
    # Upgrade safety: an existing copy that differs from this tool's may only be a released older
    # version; anything else is a local edit and needs --replace-edited. No index beside this tool
    # (a copy running outside the template) keeps the old replace behaviour, with a note.
    replacing = (copy_tool and tool.is_file()) or (copy_plugin and plugin_target.is_file())
    try:
        released = released_asset_hashes(own.parent.parent) if replacing else None
    except ValueError as error:
        print(f"refused: {error}", file=sys.stderr)
        return 2
    checked: list[tuple[Path, str, list[str]]] = []
    if copy_tool and tool.is_file():
        checked.append((tool, f"scripts/{HOOK_MARK}", (released or {}).get(HOOKS_SHA_FIELD, [])))
    if copy_plugin and plugin_target.is_file():
        checked.append((plugin_target, f"{OPENCODE_PLUGIN_DIR}/{OPENCODE_PLUGIN_NAME}",
                        (released or {}).get(PLUGIN_SHA_FIELD, [])))
    if checked and released is None:
        print(f"projectstate_hooks: no {RELEASE_INDEX.as_posix()} next to this tool; differing copies are "
              "replaced without a released-version check", file=sys.stderr)
    refusals: list[str] = []
    if not replace_edited and released is not None:
        for path, label, allowed in checked:
            refusal = edited_copy_refusal(path, label, allowed, root)
            if refusal:
                refusals.append(refusal)
    if refusals:
        for refusal in refusals:
            print(refusal, file=sys.stderr)
        return 2
    if not ((merged is not None and (added or replaced)) or copy_tool or copy_plugin):
        print("already installed: hooks and files are in place for host " + host)
        return 0
    if copy_tool:
        print(f"{'would copy' if dry_run else 'copying'} the tool to {tool.relative_to(root)}")
    if merged is not None and added:
        print(f"{'would add' if dry_run else 'adding'} hooks for: {', '.join(added)} in {settings}")
    if merged is not None and replaced:
        print(f"{'would replace' if dry_run else 'replacing'} v1 owner-log hooks for: {', '.join(sorted(set(replaced)))}")
    if copy_plugin:
        print(f"{'would copy' if dry_run else 'copying'} the opencode plugin to {plugin_target.relative_to(root)}")
    if not dry_run:
        if copy_tool:
            tool.parent.mkdir(parents=True, exist_ok=True)
            write_atomic(tool, own.read_text(encoding="utf-8"))
            tool.chmod(0o755)
        if merged is not None and (added or replaced):
            write_atomic(settings, json.dumps(merged, indent=2) + "\n")
        if copy_plugin:
            plugin_target.parent.mkdir(parents=True, exist_ok=True)
            write_atomic(plugin_target, plugin_source.read_text(encoding="utf-8"))
        print("done. Restart the host in this project; owner prompts are recorded to .projectstate/owner-log.md, "
              "sessions start with a brief, and standing words are offered once at stop")
    return 0


def uninstall(root: Path, dry_run: bool, host: str) -> int:
    own = Path(__file__).resolve()
    tool = root / "scripts" / HOOK_MARK
    settings = root / ".claude" / "settings.json"
    removed_any = False
    if host in ("claude", "all"):
        if settings.is_symlink():
            print("refused: .claude/settings.json is reached through a symlink", file=sys.stderr)
            return 2
        if settings.is_file():
            try:
                data = json.loads(settings.read_text(encoding="utf-8"))
                if not isinstance(data, dict):
                    raise ValueError("it is not a JSON object")
            except (ValueError, OSError) as error:
                print(f"refused: cannot read {settings}: {error}", file=sys.stderr)
                return 2
            hooks = data.get("hooks")
            if isinstance(hooks, dict):
                removed: list[str] = []
                fresh_hooks: dict = {}
                for event, groups in hooks.items():
                    if not isinstance(groups, list):
                        fresh_hooks[event] = groups
                        continue
                    kept_groups: list = []
                    for group in groups:
                        if not isinstance(group, dict) or not isinstance(group.get("hooks"), list):
                            kept_groups.append(group)
                            continue
                        inner = group["hooks"]
                        keep = [hook for hook in inner
                                if not (isinstance(hook, dict) and HOOK_MARK in str(hook.get("command", "")))]
                        if len(keep) != len(inner):
                            removed.append(event)
                        if keep:
                            fresh = dict(group)
                            fresh["hooks"] = keep
                            kept_groups.append(fresh)
                    if kept_groups:
                        fresh_hooks[event] = kept_groups
                if removed:
                    print(f"{'would remove' if dry_run else 'removing'} hooks for: {', '.join(sorted(set(removed)))} "
                          f"from {settings}")
                    removed_any = True
                    if not dry_run:
                        if fresh_hooks:
                            data["hooks"] = fresh_hooks
                        else:
                            data.pop("hooks", None)
                        write_atomic(settings, json.dumps(data, indent=2) + "\n")
        if tool.is_symlink():
            print("refused: the tool path is a symlink", file=sys.stderr)
            return 2
        if tool.is_file() and not same_file(tool, own):
            print(f"{'would remove' if dry_run else 'removing'} {tool.relative_to(root)}")
            removed_any = True
            if not dry_run:
                tool.unlink()
    if host in ("opencode", "all"):
        plugin_source = own.parent / OPENCODE_PLUGIN_SOURCE
        for directory in (OPENCODE_PLUGIN_DIR, OPENCODE_PLUGIN_LEGACY_DIR):
            plugin = root / directory / OPENCODE_PLUGIN_NAME
            if plugin.is_symlink():
                print(f"refused: {directory}/{OPENCODE_PLUGIN_NAME} is reached through a symlink", file=sys.stderr)
                return 2
            if plugin.is_file() and not same_file(plugin, plugin_source):
                print(f"{'would remove' if dry_run else 'removing'} {plugin.relative_to(root)}")
                removed_any = True
                if not dry_run:
                    plugin.unlink()
    if not removed_any:
        print("nothing to uninstall for host " + host)
    elif not dry_run:
        print("done. The log in .projectstate/owner-log.md is kept.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Keep the owner's own words in front of every session")
    parser.add_argument("command", choices=("install", "uninstall", "show", "record", "brief", "stop"))
    parser.add_argument("--root", default=".", help="Repository root (install, uninstall and show; default: current directory)")
    parser.add_argument("--dry-run", action="store_true", help="install and uninstall: print what would change and write nothing")
    parser.add_argument("--no-stop", action="store_true", help="install: add only the SessionStart and UserPromptSubmit hooks")
    parser.add_argument("--host", choices=("claude", "opencode", "all"), default="claude",
                        help="Which host to install or uninstall for (default: claude)")
    parser.add_argument("--replace-edited", action="store_true",
                        help="install: replace an existing tool or plugin copy even when it matches no released version")
    args = parser.parse_args(argv)
    try:
        if args.command == "install":
            return install(Path(args.root).resolve(), args.dry_run, not args.no_stop, args.host, args.replace_edited)
        if args.command == "uninstall":
            return uninstall(Path(args.root).resolve(), args.dry_run, args.host)
        if args.command == "show":
            path = log_path(find_root(Path(args.root).resolve()))
            if path.is_file():
                print(path.read_text(encoding="utf-8"), end="")
            return 0
        payload = hook_input()
        root = hook_root(payload)
        if args.command == "record":
            append_entry(root, str(payload.get("prompt") or ""), session_key(str(payload.get("session_id") or "")))
        elif args.command == "brief":
            sys.stdout.write(brief_text(root))
        else:
            decision = stop_decision(root, payload)
            if decision:
                sys.stdout.write(decision + "\n")
    except Exception as error:  # noqa: BLE001 - a hook must never break the owner's session
        if args.command in ("install", "uninstall", "show"):
            print(f"error: {error}", file=sys.stderr)
            return 2
        print(f"projectstate_hooks: {args.command} skipped: {error}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
