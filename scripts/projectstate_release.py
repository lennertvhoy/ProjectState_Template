#!/usr/bin/env python3
"""Release identity for the ProjectState template.

``releases/index.json`` records, for every template release, the sha256 of the
gate and of the managed ``AGENTS.md`` block. Instances carry a vendored gate and
one managed block between markers; the fleet doctor and the update command
compare both with the index. This module holds the shared, dependency-free
helpers; the gate itself stays self-contained and does not import it.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any, NamedTuple


TEMPLATE_ROOT = Path(__file__).resolve().parents[1]
INDEX_FORMAT = "projectstate-release-index/1"
INDEX_PATH = Path("releases") / "index.json"
MANAGED_PATH = Path("core") / "AGENTS.managed.md"
GATE_PATH = Path("scripts") / "projectstate_gate.py"
START_MARKER = re.compile(r"^<!-- projectstate:managed:start release=(\d+\.\d+\.\d+) -->$", re.MULTILINE)
END_MARKER = re.compile(r"^<!-- projectstate:managed:end -->$", re.MULTILINE)
END_LINE = "<!-- projectstate:managed:end -->"
RELEASE_LINE = re.compile(r'^RELEASE = "(\d+\.\d+\.\d+)"$', re.MULTILINE)
SEMVER = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")


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


def managed_block_text(template_root: Path = TEMPLATE_ROOT) -> str:
    """Canonical managed block content: LF newlines, exactly one trailing newline."""
    text = normalize_newlines((template_root / MANAGED_PATH).read_text(encoding="utf-8"))
    return text.rstrip("\n") + "\n"


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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Show ProjectState release hashes")
    parser.add_argument("--template", default=str(TEMPLATE_ROOT), help="Template repository root")
    args = parser.parse_args(argv)
    root = Path(args.template).resolve()
    gate_text = (root / GATE_PATH).read_text(encoding="utf-8")
    print(json.dumps({
        "gate_release": gate_release(gate_text),
        "gate_sha256": sha256_file(root / GATE_PATH),
        "contract_sha256": contract_sha256(managed_block_text(root)),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
