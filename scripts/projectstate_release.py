#!/usr/bin/env python3
"""Release identity for the ProjectState template.

``releases/index.json`` records, for every template release, the sha256 of the
gate and of the managed ``AGENTS.md`` block. Instances carry a vendored gate and
one managed block between markers; the fleet doctor and the update command
compare both with the index. This module holds the shared, dependency-free
helpers; the gate itself stays self-contained and does not import it.

Command line (every subcommand takes ``--template DIR``, default: this repository):

``check`` (the default)
    Validate ``releases/index.json`` against the gate, the managed block, the opt-in host
    hooks assets and, read-only, the local release tags. Exit 0 when consistent, otherwise
    2 with one line per problem.
``cut --date YYYY-MM-DD``
    Fill the hashes of the draft that is the latest entry, mark it released and rewrite
    the index atomically. Refused when the latest entry is already released. It never
    creates a tag.
``hashes``
    Print the computed gate, managed-block and host-hooks-asset hashes as JSON.

Besides ``gate_sha256`` and ``contract_sha256``, an entry may record ``hooks_sha256``
(the sha256 of ``scripts/projectstate_hooks.py``) and ``opencode_plugin_sha256`` (the
sha256 of ``scripts/projectstate_opencode_plugin.js``). The host hooks are an opt-in
asset, so both fields are optional keys: null or absent is fine for a draft and for
releases before 6.4.0, and required (with the files present) from 6.4.0 on.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, NamedTuple


TEMPLATE_ROOT = Path(__file__).resolve().parents[1]
INDEX_FORMAT = "projectstate-release-index/1"
INDEX_PATH = Path("releases") / "index.json"
MANAGED_PATH = Path("core") / "AGENTS.managed.md"
GATE_PATH = Path("scripts") / "projectstate_gate.py"
HOOKS_PATH = Path("scripts") / "projectstate_hooks.py"
OPENCODE_PLUGIN_PATH = Path("scripts") / "projectstate_opencode_plugin.js"
START_MARKER = re.compile(r"^<!-- projectstate:managed:start release=(\d+\.\d+\.\d+) -->$", re.MULTILINE)
END_MARKER = re.compile(r"^<!-- projectstate:managed:end -->$", re.MULTILINE)
END_LINE = "<!-- projectstate:managed:end -->"
RELEASE_LINE = re.compile(r'^RELEASE = "(\d+\.\d+\.\d+)"$', re.MULTILINE)
VERSION_LINE = re.compile(r'^VERSION = "([^"\n]+)"$', re.MULTILINE)
SEMVER = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")

# Index validation. The patterns are ASCII-only on purpose: a release number or hash that merely looks
# like one (other digit scripts, uppercase hex, a trailing newline) must not pass.
INDEX_KEYS = ("release", "date", "tag", "status", "gate_sha256", "contract_sha256", "instance_action", "summary")
STATUSES = ("released", "draft")
INSTANCE_ACTIONS = ("none", "mechanical", "semantic")
RELEASE_TEXT = r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)"
STRICT_RELEASE = re.compile(RELEASE_TEXT)
STRICT_TAG = re.compile(f"v{RELEASE_TEXT}")
SHA256_HEX = re.compile(r"[0-9a-f]{64}")
ISO_DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
FIRST_CONTRACT_RELEASE = (6, 3, 0)  # releases before this one predate the managed block and record no contract hash
FIRST_HOOKS_RELEASE = (6, 4, 0)  # releases before this one predate the opt-in host hooks and record no hashes
# (index field, file, needs the managed-block normalization) for every hash an entry can record.
HASHED_FILES: tuple[tuple[str, Path, bool], ...] = (
    ("gate_sha256", GATE_PATH, False),
    ("contract_sha256", MANAGED_PATH, True),
    ("hooks_sha256", HOOKS_PATH, False),
    ("opencode_plugin_sha256", OPENCODE_PLUGIN_PATH, False),
)
# The opt-in host hooks assets: optional index keys, recorded from 6.4.0 on.
HOOKS_ASSET_FILES: tuple[tuple[str, Path], ...] = (("hooks_sha256", HOOKS_PATH),
                                                   ("opencode_plugin_sha256", OPENCODE_PLUGIN_PATH))
COMMANDS = ("check", "cut", "hashes")
GIT_TIMEOUT_SECONDS = 30
GIT_LOCATION_VARIABLES = (
    "GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY", "GIT_COMMON_DIR", "GIT_NAMESPACE",
)


class ManagedBlock(NamedTuple):
    """A managed block found in an AGENTS.md text (offsets index the LF-normalized text)."""

    release: str
    content: str
    start: int
    end: int


def normalize_newlines(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def asset_sha256(root: Path, path: Path) -> str | None:
    """sha256 of a template file, or None when it is absent (the host hooks are an opt-in asset)."""
    try:
        return sha256_bytes((root / path).read_bytes())
    except OSError:
        return None


def semver_key(release: str) -> tuple[int, int, int]:
    match = SEMVER.fullmatch(release)
    if not match:
        raise ValueError(f"not a release number: {release!r}")
    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate key {key!r} in release index")
        result[key] = value
    return result


def load_index(template_root: Path = TEMPLATE_ROOT) -> dict[str, Any]:
    text = (template_root / INDEX_PATH).read_text(encoding="utf-8")
    payload = json.loads(text, object_pairs_hook=_reject_duplicate_keys)
    if not isinstance(payload, dict) or payload.get("format") != INDEX_FORMAT:
        raise ValueError(f"{INDEX_PATH} must be a {INDEX_FORMAT} object")
    if not isinstance(payload.get("releases"), list):
        raise ValueError(f"{INDEX_PATH} must list releases")
    return payload


def gate_release(gate_text: str) -> str | None:
    match = RELEASE_LINE.search(gate_text)
    return match.group(1) if match else None


def gate_version(gate_text: str) -> str | None:
    """The state schema (``VERSION``) the gate declares."""
    match = VERSION_LINE.search(gate_text)
    return match.group(1) if match else None


def canonical_block(text: str) -> str:
    """Managed block content as an AGENTS.md carries it: LF newlines, exactly one trailing newline."""
    return normalize_newlines(text).rstrip("\n") + "\n"


def managed_block_text(template_root: Path = TEMPLATE_ROOT) -> str:
    """Canonical managed block content: LF newlines, exactly one trailing newline."""
    return canonical_block((template_root / MANAGED_PATH).read_text(encoding="utf-8"))


def contract_sha256(block_text: str) -> str:
    return sha256_text(normalize_newlines(block_text))


def render_managed_block(release: str, block_text: str) -> str:
    semver_key(release)
    body = normalize_newlines(block_text).rstrip("\n") + "\n"
    return f"<!-- projectstate:managed:start release={release} -->\n{body}{END_LINE}\n"


def extract_managed_block(agents_text: str) -> tuple[ManagedBlock | None, str | None]:
    """Return (block, None), (None, None) when absent, or (None, error) when malformed."""
    text = normalize_newlines(agents_text)
    starts = list(START_MARKER.finditer(text))
    ends = list(END_MARKER.finditer(text))
    if not starts and not ends:
        if "projectstate:managed:" in text:
            return None, "malformed managed block markers"
        return None, None
    if len(starts) != 1 or len(ends) != 1 or ends[0].start() <= starts[0].end():
        return None, "malformed managed block markers"
    start, end = starts[0], ends[0]
    content = text[start.end() + 1 : end.start()]
    return ManagedBlock(start.group(1), content, start.start(), end.end()), None


def released(index: dict[str, Any]) -> list[dict[str, Any]]:
    entries = [entry for entry in index["releases"] if isinstance(entry, dict) and entry.get("status") == "released"]
    return sorted(entries, key=lambda entry: semver_key(str(entry["release"])))


def current_release(index: dict[str, Any]) -> dict[str, Any] | None:
    """Highest release whose status is ``released`` (a draft is never current)."""
    entries = released(index)
    return entries[-1] if entries else None


def releases_matching(index: dict[str, Any], field: str, sha: str) -> list[str]:
    """Released versions whose ``field`` (gate_sha256 or contract_sha256) equals ``sha``."""
    return [str(entry["release"]) for entry in released(index) if entry.get(field) == sha]


def parse_iso_date(text: Any) -> dt.date | None:
    """A strict YYYY-MM-DD calendar date, or None (no other ISO forms, no other digit scripts)."""
    if not isinstance(text, str) or not ISO_DATE.fullmatch(text):
        return None
    try:
        return dt.date.fromisoformat(text)
    except ValueError:
        return None


# --- Index validation ---------------------------------------------------------------------


def read_index_file(root: Path) -> tuple[Any, list[str]]:
    """Parse releases/index.json leniently, so every problem can be reported; (None, problems) when unusable."""
    try:
        text = (root / INDEX_PATH).read_text(encoding="utf-8")
        return json.loads(text, object_pairs_hook=_reject_duplicate_keys), []
    except (OSError, ValueError, RecursionError) as exc:
        return None, [f"{INDEX_PATH.as_posix()} is unusable: {exc}"]


def read_gate(root: Path) -> tuple[bytes | None, list[str]]:
    try:
        return (root / GATE_PATH).read_bytes(), []
    except OSError as exc:
        return None, [f"cannot read {GATE_PATH.as_posix()}: {exc}"]


def entry_problems(entry: Any, position: int, is_last: bool) -> list[str]:
    """Problems with one releases[] entry taken on its own (order across entries is checked elsewhere)."""
    release = entry.get("release") if isinstance(entry, dict) else None
    label = f"releases[{position}] ({release})" if isinstance(release, str) else f"releases[{position}]"
    if not isinstance(entry, dict):
        return [f"{label} must be an object"]
    problems: list[str] = []
    missing = [key for key in INDEX_KEYS if key not in entry]
    hook_fields = {field for field, _path in HOOKS_ASSET_FILES}
    unknown = sorted(str(key) for key in entry if key not in INDEX_KEYS and key not in hook_fields)
    if missing:
        problems.append(f"{label} is missing keys {missing}")
    if unknown:
        problems.append(f"{label} has unsupported keys {unknown}")
    release_key = None
    if "release" in entry:
        if isinstance(release, str) and STRICT_RELEASE.fullmatch(release):
            release_key = semver_key(release)
        else:
            problems.append(f"{label}: release must be a MAJOR.MINOR.PATCH number")
    if "tag" in entry:
        tag = entry["tag"]
        if not isinstance(tag, str) or not STRICT_TAG.fullmatch(tag):
            problems.append(f"{label}: tag must be v<release>")
        elif release_key is not None and tag != f"v{release}":
            problems.append(f"{label}: tag {tag} must be v{release}")
    status = entry.get("status")
    if "status" in entry:
        if status not in STATUSES:
            problems.append(f"{label}: status must be one of {list(STATUSES)}")
        elif status == "draft" and not is_last:
            problems.append(f"{label}: only the last entry may be a draft")
    if "date" in entry:
        date = entry["date"]
        if date is None:
            if status == "released":
                problems.append(f"{label}: a released entry needs a date")
        elif parse_iso_date(date) is None:
            problems.append(f"{label}: date must be YYYY-MM-DD or null")
    draft = status == "draft"
    predates_contract = release_key is not None and release_key < FIRST_CONTRACT_RELEASE
    needs_hooks = status == "released" and release_key is not None and release_key >= FIRST_HOOKS_RELEASE
    for field, may_be_null, allowed in (
        ("gate_sha256", draft, "only a draft may leave it null"),
        ("contract_sha256", draft or predates_contract, "only a draft or a release before 6.3.0 may leave it null"),
    ):
        if field not in entry:
            continue
        value = entry[field]
        if value is None:
            if not may_be_null:
                problems.append(f"{label}: {field} is null; {allowed}")
        elif not isinstance(value, str) or not SHA256_HEX.fullmatch(value):
            problems.append(f"{label}: {field} must be 64 lowercase hex characters or null")
    for field, _path in HOOKS_ASSET_FILES:
        if field not in entry:
            if needs_hooks:
                problems.append(f"{label}: {field} is missing; a release from 6.4.0 on records the hash of the "
                                "opt-in host hooks asset")
            continue
        value = entry[field]
        if value is None:
            if needs_hooks:
                problems.append(f"{label}: {field} is null; only a draft or a release before 6.4.0 may leave it null")
        elif not isinstance(value, str) or not SHA256_HEX.fullmatch(value):
            problems.append(f"{label}: {field} must be 64 lowercase hex characters or null")
    if "instance_action" in entry and entry["instance_action"] not in INSTANCE_ACTIONS:
        problems.append(f"{label}: instance_action must be one of {list(INSTANCE_ACTIONS)}")
    if "summary" in entry and (not isinstance(entry["summary"], str) or not entry["summary"].strip()):
        problems.append(f"{label}: summary must be non-empty text")
    return problems


def index_problems(payload: Any, gate_text: str | None) -> list[str]:
    """Structure and cross-entry problems of a parsed index; the gate text supplies VERSION and RELEASE."""
    if not isinstance(payload, dict):
        return [f"{INDEX_PATH.as_posix()} must be a JSON object"]
    problems: list[str] = []
    if payload.get("format") != INDEX_FORMAT:
        problems.append(f"format must be {INDEX_FORMAT!r}")
    schema, latest = payload.get("state_schema"), payload.get("latest")
    if not isinstance(latest, str) or not STRICT_RELEASE.fullmatch(latest):
        problems.append("latest must be a MAJOR.MINOR.PATCH release number")
    if gate_text is not None:
        gate_schema, gate_rel = gate_version(gate_text), gate_release(gate_text)
        if gate_schema is None:
            problems.append(f"{GATE_PATH.as_posix()} declares no VERSION")
        elif schema != gate_schema:
            problems.append(f"state_schema {schema!r} does not equal the gate VERSION {gate_schema!r}")
        if gate_rel is None:
            problems.append(f"{GATE_PATH.as_posix()} declares no RELEASE")
        elif latest != gate_rel:
            problems.append(f"latest {latest!r} does not equal the gate RELEASE {gate_rel!r}")
    entries = payload.get("releases")
    if not isinstance(entries, list) or not entries:
        return [*problems, "releases must be a non-empty list"]
    seen_releases: set[str] = set()
    seen_tags: set[str] = set()
    highest: tuple[int, int, int] | None = None
    for position, entry in enumerate(entries):
        problems.extend(entry_problems(entry, position, position == len(entries) - 1))
        if not isinstance(entry, dict):
            continue
        release, tag = entry.get("release"), entry.get("tag")
        if isinstance(tag, str):
            if tag in seen_tags:
                problems.append(f"releases[{position}]: duplicate tag {tag}")
            seen_tags.add(tag)
        if not isinstance(release, str) or not STRICT_RELEASE.fullmatch(release):
            continue
        key = semver_key(release)
        if release in seen_releases:
            problems.append(f"releases[{position}]: duplicate release {release}")
        elif highest is not None and key <= highest:
            problems.append(f"releases[{position}]: releases must ascend, but {release} follows "
                            f"{'.'.join(map(str, highest))}")
        seen_releases.add(release)
        highest = key if highest is None else max(highest, key)
    last = entries[-1]
    if isinstance(last, dict) and isinstance(latest, str) and last.get("release") != latest:
        problems.append(f"latest {latest!r} is not the last entry ({last.get('release')!r})")
    return problems


def hash_mismatches(entry: dict[str, Any], computed: dict[str, str | None]) -> list[str]:
    """A released latest entry must record exactly the hashes of the files it ships.

    ``computed`` holds the hashes that could be read (None: an opt-in asset file is absent);
    fields the caller could not compute at all are absent from it and are not re-reported.
    """
    problems: list[str] = []
    release = entry.get("release")
    for field, path, _normalized in HASHED_FILES:
        recorded = entry.get(field)
        if field not in computed or not isinstance(recorded, str):
            continue
        actual = computed[field]
        if actual is None:
            problems.append(f"release {release}: {path.as_posix()} is missing, but the entry records a {field}")
        elif recorded != actual:
            problems.append(f"release {release}: {field} {recorded[:12]} does not match {path.as_posix()} "
                            f"({actual[:12]}); a released entry is frozen, so restore the file or cut a new release")
    return problems


def run_git(root: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    """One read-only git command in ``root`` that never climbs out of it into an enclosing repository.

    The return code is -1 when git is missing or the command times out."""
    env = {key: value for key, value in os.environ.items() if key not in GIT_LOCATION_VARIABLES}
    env.update(GIT_OPTIONAL_LOCKS="0", GIT_TERMINAL_PROMPT="0", GIT_CEILING_DIRECTORIES=str(root.parent))
    try:
        return subprocess.run(
            ["git", "--no-pager", "-C", str(root), *args],
            capture_output=True, stdin=subprocess.DEVNULL, env=env, timeout=GIT_TIMEOUT_SECONDS, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return subprocess.CompletedProcess(args, -1, b"", b"")


def compare_with_tags(root: Path, entries: list[Any]) -> tuple[list[str], list[str]]:
    """Compare each released entry's hashes with the files at its local tag; skip what git cannot answer."""
    problems: list[str] = []
    notes: list[str] = []
    for entry in entries:
        if not isinstance(entry, dict) or entry.get("status") != "released":
            continue
        tag, release = entry.get("tag"), entry.get("release")
        if not isinstance(tag, str) or not STRICT_TAG.fullmatch(tag):
            continue  # reported as an index problem; never hand an unvalidated name to git
        found = run_git(root, "rev-parse", "--verify", "--quiet", f"refs/tags/{tag}^{{commit}}")
        if found.returncode == 1:
            notes.append(f"tag {tag} not found locally; not compared")
            continue
        if found.returncode != 0:
            notes.append("git is not available here, or this is not a git repository; release tags were not compared")
            break
        matched: list[str] = []
        for field, path, is_block in HASHED_FILES:
            recorded = entry.get(field)
            if not isinstance(recorded, str):
                continue
            blob = run_git(root, "cat-file", "blob", f"refs/tags/{tag}:{path.as_posix()}")
            if blob.returncode != 0:
                problems.append(f"tag {tag} has no {path.as_posix()}, but release {release} records a {field}")
                continue
            actual = (contract_sha256(canonical_block(blob.stdout.decode("utf-8", errors="replace")))
                      if is_block else sha256_bytes(blob.stdout))
            if actual == recorded:
                matched.append(field.removesuffix("_sha256"))
            else:
                problems.append(f"release {release}: {field} {recorded[:12]} does not match {path.as_posix()} "
                                f"at tag {tag} ({actual[:12]})")
        if matched:
            notes.append(f"tag {tag}: {' and '.join(matched)} hash matches")
    return problems, notes


def check_template(root: Path) -> tuple[list[str], list[str]]:
    """(problems, notes) for the release index of ``root``; no problems means the index is consistent."""
    notes: list[str] = []
    payload, problems = read_index_file(root)
    gate_bytes, gate_problems = read_gate(root)
    problems.extend(gate_problems)
    if payload is None:
        return problems, notes
    gate_text = gate_bytes.decode("utf-8", errors="replace") if gate_bytes is not None else None
    problems.extend(index_problems(payload, gate_text))
    entries = payload.get("releases") if isinstance(payload, dict) else None
    if not isinstance(entries, list) or not entries:
        return problems, notes
    latest = entries[-1]
    if isinstance(latest, dict) and gate_bytes is not None:
        status = latest.get("status")
        computed: dict[str, str | None] = {"gate_sha256": sha256_bytes(gate_bytes)}
        # The managed block matters for a draft (its hash is about to be recorded) and for a release that
        # records one; a release from before the managed block existed has neither.
        if status == "draft" or (status == "released" and isinstance(latest.get("contract_sha256"), str)):
            try:
                computed["contract_sha256"] = contract_sha256(managed_block_text(root))
            except (OSError, UnicodeDecodeError) as exc:
                problems.append(f"cannot read {MANAGED_PATH.as_posix()}: {exc}")
        # The opt-in host hooks assets matter for a draft and for a release that records them; an absent
        # file records as None and is reported by hash_mismatches against an entry that claims the hash.
        if status == "draft" or (status == "released"
                                 and any(isinstance(latest.get(field), str) for field, _path in HOOKS_ASSET_FILES)):
            for field, path in HOOKS_ASSET_FILES:
                computed[field] = asset_sha256(root, path)
        if status == "released":
            problems.extend(hash_mismatches(latest, computed))
        elif status == "draft":
            notes.append(f"draft {latest.get('release')} records no hashes yet; `cut` will record these computed ones:")
            for field, _path, _normalized in HASHED_FILES:
                if computed.get(field) is not None:
                    notes.append(f"  {field}: {computed[field]}")
    tag_problems, tag_notes = compare_with_tags(root, entries)
    problems.extend(tag_problems)
    notes.extend(tag_notes)
    if not problems:
        notes.insert(0, f"release index OK: {len(entries)} releases, latest {entries[-1]['release']} "
                        f"({entries[-1]['status']})")
    return problems, notes


def run_check(root: Path) -> int:
    problems, notes = check_template(root)
    for problem in problems:
        print(f"release check: {problem}", file=sys.stderr)
    if not problems:
        for note in notes:
            print(note)
    return 2 if problems else 0


# --- cut and hashes -----------------------------------------------------------------------


def index_text(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"


def write_atomic(path: Path, text: str) -> None:
    """Write beside the target, then os.replace; the original survives any failure."""
    mode = stat.S_IMODE(path.stat().st_mode)
    handle, tmp_path = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(tmp_path, mode)
        os.replace(tmp_path, path)
    except BaseException:
        try:
            os.unlink(tmp_path)
        except FileNotFoundError:
            pass
        raise


def refuse(command: str, reasons: list[str]) -> int:
    for reason in reasons:
        print(f"release {command}: refused: {reason}", file=sys.stderr)
    return 2


def run_cut(root: Path, date_text: str) -> int:
    """Record the computed hashes, the date and status released on the draft that is the latest entry."""
    if parse_iso_date(date_text) is None:
        return refuse("cut", [f"--date must be a valid YYYY-MM-DD date, not {date_text!r}"])
    payload, problems = read_index_file(root)
    gate_bytes, gate_problems = read_gate(root)
    problems.extend(gate_problems)
    if payload is not None and gate_bytes is not None:
        problems.extend(index_problems(payload, gate_bytes.decode("utf-8", errors="replace")))
    if problems:
        return refuse("cut", [*problems, "fix these (see `check`) before cutting a release"])
    entry = payload["releases"][-1]
    if entry["status"] != "draft":
        return refuse("cut", [f"latest release {entry['release']} is already released; cut only fills a draft, "
                              "so add a draft entry for the next release first"])
    index_path = root / INDEX_PATH
    if index_path.is_symlink() or not index_path.is_file():
        return refuse("cut", [f"{INDEX_PATH.as_posix()} is not a regular file; refusing to rewrite it"])
    try:
        contract_sha = contract_sha256(managed_block_text(root))
    except (OSError, UnicodeDecodeError) as exc:
        return refuse("cut", [f"cannot read {MANAGED_PATH.as_posix()}: {exc}"])
    computed: dict[str, str | None] = {"gate_sha256": sha256_bytes(gate_bytes), "contract_sha256": contract_sha}
    for field, path in HOOKS_ASSET_FILES:
        value = asset_sha256(root, path)
        if value is None:
            return refuse("cut", [f"cannot read {path.as_posix()}: a release from 6.4.0 on records the hash of the "
                                  "opt-in host hooks asset, so both asset files must be present"])
        computed[field] = value
    entry.update(date=date_text, status="released", **computed)
    try:
        write_atomic(index_path, index_text(payload))
    except OSError as exc:
        return refuse("cut", [f"cannot rewrite {INDEX_PATH.as_posix()}: {exc}"])
    print(f"cut release {entry['release']} on {date_text}")
    for field, _path, _normalized in HASHED_FILES:
        print(f"  {field}: {computed[field]}")
    print(f"rewrote {INDEX_PATH.as_posix()}; commit it, then create the tag {entry['tag']} yourself "
          "(this command never creates tags)")
    return 0


def run_hashes(root: Path) -> int:
    try:
        gate_bytes = (root / GATE_PATH).read_bytes()
        contract_sha = contract_sha256(managed_block_text(root))
    except (OSError, UnicodeDecodeError) as exc:
        print(f"release hashes: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({
        "gate_release": gate_release(gate_bytes.decode("utf-8", errors="replace")),
        "gate_sha256": sha256_bytes(gate_bytes),
        "contract_sha256": contract_sha,
        **{field: asset_sha256(root, path) for field, path in HOOKS_ASSET_FILES},
    }, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--template", default=str(TEMPLATE_ROOT), help="Template repository root (default: this repository)")
    parser = argparse.ArgumentParser(
        description="Check, cut and show ProjectState release identity. Without a subcommand, runs check.")
    commands = parser.add_subparsers(dest="command", required=True, metavar="{check,cut,hashes}")
    commands.add_parser("check", parents=[common], help="Validate releases/index.json (default); exit 2 on any problem")
    cut = commands.add_parser(
        "cut", parents=[common], help="Fill the draft latest entry with the current hashes and mark it released")
    cut.add_argument("--date", required=True, metavar="YYYY-MM-DD", help="Release date to record")
    commands.add_parser("hashes", parents=[common], help="Print the computed gate and managed-block hashes as JSON")
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if not arguments or (arguments[0] not in COMMANDS and arguments[0] not in ("-h", "--help")):
        arguments.insert(0, "check")  # check is the default subcommand, also before options such as --template
    args = build_parser().parse_args(arguments)
    root = Path(args.template).expanduser().resolve()
    if args.command == "cut":
        return run_cut(root, args.date)
    if args.command == "hashes":
        return run_hashes(root)
    return run_check(root)


if __name__ == "__main__":
    raise SystemExit(main())
