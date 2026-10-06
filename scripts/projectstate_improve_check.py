#!/usr/bin/env python3
"""Mechanical guards for optional measured improvement rounds.

Read-only and standard-library only. It never executes the measure command,
applies a patch, or authenticates a human decision. It checks recorded files:
``IMPROVE.md`` (human-owned configuration) and ``evidence/improve-NNN/`` round
records. The stop rule and protected paths live here, not in prose, because a
loop that polices its own measure is the failure this helper exists to prevent.

Exit 0: a round may start, or the named round record is valid.
Exit 1: refused (disabled, stop rule tripped, dirty worktree, or a proposal that
        touches protected paths, grows an instruction file, or exceeds its cap).
Exit 2: configuration or round records are invalid or unreadable.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import re
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

CONFIG_FILE = "IMPROVE.md"
ROUND_DIR = re.compile(r"improve-(\d{3})")
INSTANCE_TYPES = {"project", "study", "guide", "other"}
DIRECTIONS = {"higher", "lower"}
CLOSURES = {"validated", "ready_for_human", "accepted"}
DECISIONS = {"none", "proposed", "approved", "applied", "rejected"}
INSTRUCTION_FILES = {"agents.md", "claude.md", "gemini.md"}
# The loop may propose changes to almost anything except what judges it.
FIXED_PROTECTED = (
    "PROJECT.md",
    "STATE.yaml",
    "IMPROVE.md",
    "scripts/projectstate_gate.py",
    "scripts/projectstate_improve_check.py",
    "evidence/",
    ".git/",
    ".github/",
)
CONFIG_KEYS = {
    "enabled", "instance_type", "measure_name", "measure_command", "measure_direction",
    "baseline_value", "baseline_observed_on", "min_gain", "stop_after_rounds",
    "first_counted_round", "round_token_cap", "model", "protected", "signals", "lessons_file",
}
REQUIRED_WHEN_ENABLED = (
    "instance_type", "measure_name", "measure_command", "measure_direction", "baseline_value",
    "baseline_observed_on", "min_gain", "stop_after_rounds", "round_token_cap",
)
ROUND_KEYS = {
    "round", "slice", "closure", "measure_value", "measure_raw", "proposal", "tokens_used", "decision",
}
MAX_TEXT_BYTES = 256 * 1024
MAX_PATCH_BYTES = 1024 * 1024
NUMBER = re.compile(r"-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?")
HUNK = re.compile(r"^@@ -\d+(?:,(\d+))? \+\d+(?:,(\d+))? @@")


class Invalid(ValueError):
    """Configuration or round records are unreadable or inconsistent."""


class PatchError(ValueError):
    """A proposal cannot be verified, so it is refused."""


@dataclass(frozen=True)
class Config:
    instance_type: str
    measure_name: str
    measure_command: str
    direction: str
    baseline: float
    min_gain: float
    stop_after: int
    first_counted: int
    token_cap: int
    protected: tuple[str, ...]
    signals: tuple[str, ...]
    lessons_file: str | None


@dataclass(frozen=True)
class Round:
    number: int
    path: Path
    data: dict[str, Any]


def _clean_rel(raw: str, *, allow_dir: bool = False) -> str:
    text = raw.strip()
    if not text or "\\" in text or "\x00" in text or text.startswith(("/", '"')):
        raise Invalid(f"unsafe relative path {raw!r}")
    parts = PurePosixPath(text).parts
    if not parts or ".." in parts or "." in parts:
        raise Invalid(f"unsafe relative path {raw!r}")
    clean = PurePosixPath(*parts).as_posix()
    if allow_dir and text.endswith("/"):
        clean += "/"
    return clean


def _local(root: Path, rel: str) -> Path:
    """Resolve a relative path under root, refusing symlinks anywhere on it."""
    current = root
    for part in PurePosixPath(rel).parts:
        current = current / part
        if current.is_symlink():
            raise Invalid(f"{rel}: symlinks are not allowed")
    return current


def _read(root: Path, rel: str, limit: int = MAX_TEXT_BYTES) -> str:
    path = _local(root, rel)
    if not path.is_file():
        raise Invalid(f"{rel}: missing or not a regular file")
    if path.stat().st_size > limit:
        raise Invalid(f"{rel}: larger than {limit} bytes")
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise Invalid(f"{rel}: cannot read: {exc}") from exc


def _strip_comment(value: str) -> str:
    match = re.search(r"\s#", value)
    return (value[: match.start()] if match else value).strip()


def parse_front_matter(text: str) -> dict[str, str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise Invalid(f"{CONFIG_FILE} must start with a '---' front matter block")
    values: dict[str, str] = {}
    for number, raw in enumerate(lines[1:], start=2):
        if raw.strip() == "---":
            return values
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        key, sep, rest = raw.partition(":")
        key = key.strip()
        if not sep or not re.fullmatch(r"[a-z_]+", key):
            raise Invalid(f"{CONFIG_FILE} line {number}: expected key: value")
        if key in values:
            raise Invalid(f"{CONFIG_FILE} line {number}: duplicate key {key!r}")
        if key not in CONFIG_KEYS:
            raise Invalid(f"{CONFIG_FILE} line {number}: unsupported field {key!r}")
        values[key] = _strip_comment(rest)
    raise Invalid(f"{CONFIG_FILE}: front matter is not closed with '---'")


def _number(values: dict[str, str], key: str) -> float:
    try:
        value = float(values[key])
    except ValueError as exc:
        raise Invalid(f"{key}: expected a number") from exc
    if not math.isfinite(value):
        raise Invalid(f"{key}: must be finite")
    return value


def _integer(values: dict[str, str], key: str, low: int, high: int, default: int | None = None) -> int:
    if key not in values and default is not None:
        return default
    if not re.fullmatch(r"\d+", values.get(key, "")):
        raise Invalid(f"{key}: expected a whole number")
    value = int(values[key])
    if not low <= value <= high:
        raise Invalid(f"{key}: must be between {low} and {high}")
    return value


def _path_list(raw: str, *, allow_dir: bool) -> tuple[str, ...]:
    return tuple(_clean_rel(item, allow_dir=allow_dir) for item in raw.split(",") if item.strip())


def covered_by(path: str, entries: tuple[str, ...]) -> str | None:
    folded = path.casefold()
    for entry in entries:
        target = entry.casefold()
        if target.endswith("/") and folded.startswith(target):
            return entry
        if folded == target:
            return entry
    return None


def validate_config(root: Path, values: dict[str, str]) -> Config:
    missing = [key for key in REQUIRED_WHEN_ENABLED if not values.get(key)]
    if missing:
        raise Invalid(f"{CONFIG_FILE}: enabled configuration needs {missing}; no measure means no loop")
    if values["instance_type"] not in INSTANCE_TYPES:
        raise Invalid(f"instance_type: expected one of {sorted(INSTANCE_TYPES)}")
    if values["measure_direction"] not in DIRECTIONS:
        raise Invalid(f"measure_direction: expected one of {sorted(DIRECTIONS)}")
    if not re.fullmatch(r"[A-Za-z0-9_.-]{1,64}", values["measure_name"]):
        raise Invalid("measure_name: use 1-64 letters, digits, '_', '.', '-'")
    try:
        dt.date.fromisoformat(values["baseline_observed_on"])
    except ValueError as exc:
        raise Invalid("baseline_observed_on: expected YYYY-MM-DD") from exc
    min_gain = _number(values, "min_gain")
    if min_gain <= 0:
        raise Invalid("min_gain: must be greater than zero")
    protected = _path_list(values.get("protected", ""), allow_dir=True)
    try:
        command = shlex.split(values["measure_command"])
    except ValueError as exc:
        raise Invalid(f"measure_command: cannot be tokenized: {exc}") from exc
    for token in command:
        try:
            rel = _clean_rel(token)
        except Invalid:
            continue
        candidate = root / rel
        if candidate.is_file() and not covered_by(rel, FIXED_PROTECTED + protected):
            raise Invalid(f"measure_command uses {rel}; list it in protected so the loop cannot edit its own measure")
    lessons = values.get("lessons_file") or None
    if lessons and not Path(lessons).is_absolute():
        raise Invalid("lessons_file: must be an absolute path to a read-only file outside the repository")
    return Config(
        instance_type=values["instance_type"],
        measure_name=values["measure_name"],
        measure_command=values["measure_command"],
        direction=values["measure_direction"],
        baseline=_number(values, "baseline_value"),
        min_gain=min_gain,
        stop_after=_integer(values, "stop_after_rounds", 1, 10),
        first_counted=_integer(values, "first_counted_round", 1, 999, default=1),
        token_cap=_integer(values, "round_token_cap", 1, 10_000_000),
        protected=protected,
        signals=_path_list(values.get("signals", ""), allow_dir=False),
        lessons_file=lessons,
    )


def _no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise Invalid(f"duplicate key {key!r}")
        result[key] = value
    return result


def _reject_constant(name: str) -> Any:
    raise Invalid(f"non-finite number {name} is not allowed")


def load_rounds(root: Path) -> list[Round]:
    evidence = _local(root, "evidence")
    if not evidence.is_dir():
        return []
    rounds: list[Round] = []
    for entry in sorted(evidence.iterdir()):
        match = ROUND_DIR.fullmatch(entry.name)
        if not match:
            continue
        number = int(match.group(1))
        rel = f"evidence/{entry.name}/round.json"
        if entry.is_symlink() or not entry.is_dir():
            raise Invalid(f"evidence/{entry.name}: must be a real directory")
        try:
            data = json.loads(_read(root, rel), object_pairs_hook=_no_duplicates, parse_constant=_reject_constant)
        except Invalid as exc:
            raise Invalid(f"{rel}: {exc}") from exc
        except ValueError as exc:
            raise Invalid(f"{rel}: invalid JSON: {exc}") from exc
        if not isinstance(data, dict):
            raise Invalid(f"{rel}: expected a JSON object")
        unsupported = sorted(set(data) - ROUND_KEYS)
        missing = sorted(ROUND_KEYS - set(data))
        if unsupported or missing:
            raise Invalid(f"{rel}: unsupported fields {unsupported}, missing fields {missing}")
        rounds.append(Round(number, entry, data))
    return rounds


def _validate_round(root: Path, item: Round) -> list[str]:
    """Return consistency problems for one round record and its raw measure output."""
    problems: list[str] = []
    name, data = item.path.name, item.data
    if data["round"] != item.number or isinstance(data["round"], bool):
        problems.append(f"{name}: 'round' must equal the directory number")
    if not isinstance(data["slice"], str) or not re.fullmatch(r"[A-Za-z0-9._-]{1,80}", data["slice"]):
        problems.append(f"{name}: 'slice' must name the closed slice")
    if data["closure"] not in CLOSURES:
        problems.append(f"{name}: 'closure' must be one of {sorted(CLOSURES)}; a round follows a closed slice")
    value = data["measure_value"]
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        problems.append(f"{name}: 'measure_value' must be a finite number")
        value = None
    if data["decision"] not in DECISIONS:
        problems.append(f"{name}: 'decision' must be one of {sorted(DECISIONS)}")
    if data["proposal"] not in (None, "proposal.patch"):
        problems.append(f"{name}: 'proposal' must be null or 'proposal.patch'")
    elif (data["proposal"] is None) != (data["decision"] == "none"):
        problems.append(f"{name}: 'decision' is 'none' exactly when there is no proposal")
    tokens = data["tokens_used"]
    if tokens is not None and (isinstance(tokens, bool) or not isinstance(tokens, int) or tokens < 0):
        problems.append(f"{name}: 'tokens_used' must be null (unknown) or a whole number")
    for artifact in ("summary.md", "measure.txt"):
        try:
            if not _read(root, f"evidence/{name}/{artifact}").strip():
                problems.append(f"{name}/{artifact}: empty")
        except Invalid as exc:
            problems.append(str(exc))
    raw = data["measure_raw"]
    if value is not None and isinstance(raw, str) and raw.strip():
        try:
            lines = {line.strip() for line in _read(root, f"evidence/{name}/measure.txt").splitlines()}
        except Invalid:
            lines = set()
        if raw.strip() not in lines:
            problems.append(f"{name}: 'measure_raw' is not a line of measure.txt (record the tool output verbatim)")
        elif not any(abs(float(tok) - value) <= 1e-9 for tok in NUMBER.findall(raw)):
            problems.append(f"{name}: 'measure_value' {value} does not appear in 'measure_raw'")
    elif value is not None:
        problems.append(f"{name}: 'measure_raw' must quote the measure output")
    return problems


def _gain(config: Config, value: float, best: float) -> float:
    return value - best if config.direction == "higher" else best - value


def stop_state(config: Config, rounds: list[Round]) -> tuple[float, int, bool]:
    """Return (best value, consecutive flat rounds, tripped). Tripping is sticky."""
    best, flat = config.baseline, 0
    for item in rounds:
        if item.number < config.first_counted:
            continue
        if _gain(config, float(item.data["measure_value"]), best) >= config.min_gain - 1e-12:
            best, flat = float(item.data["measure_value"]), 0
        else:
            flat += 1
        if flat >= config.stop_after:
            return best, flat, True
    return best, flat, False


def _patch_path(raw: str) -> str:
    text = raw.split("\t", 1)[0].strip()
    if text.startswith('"'):
        raise PatchError("quoted paths are not supported; use plain ASCII file names")
    if text.startswith(("a/", "b/")):
        text = text[2:]
    try:
        return _clean_rel(text)
    except Invalid as exc:
        raise PatchError(str(exc)) from exc


def parse_patch(text: str) -> dict[str, list[int]]:
    """Return {path: [added, removed]} for every path a unified diff touches."""
    touched: dict[str, list[int]] = {}
    current: list[int] | None = None
    old_left = new_left = 0
    for line in text.splitlines():
        if old_left or new_left:
            if line.startswith("\\"):
                continue
            tag = line[:1]
            if tag in (" ", ""):
                old_left, new_left = old_left - 1, new_left - 1
            elif tag == "-":
                old_left -= 1
                current[1] += 1  # type: ignore[index]
            elif tag == "+":
                new_left -= 1
                current[0] += 1  # type: ignore[index]
            else:
                raise PatchError("malformed hunk line")
            if old_left < 0 or new_left < 0:
                raise PatchError("hunk is longer than its header declares")
            continue
        if line.startswith("\\"):
            continue
        if line.startswith("diff --git "):
            match = re.fullmatch(r"diff --git a/(.*) b/(.*)", line)
            if not match:
                raise PatchError("unsupported diff header")
            old, new = _patch_path(match.group(1)), _patch_path(match.group(2))
            touched.setdefault(old, [0, 0])
            current = touched.setdefault(new, [0, 0])
        elif line.startswith(("rename from ", "rename to ", "copy from ", "copy to ")):
            touched.setdefault(_patch_path(line.split(" ", 2)[2]), [0, 0])
        elif line.startswith(("--- ", "+++ ")):
            raw = line[4:]
            if raw.split("\t", 1)[0].strip() != "/dev/null":
                path = _patch_path(raw)
                if line.startswith("+++ ") or path not in touched:
                    current = touched.setdefault(path, [0, 0])
        elif line.startswith("@@"):
            match = HUNK.match(line)
            if not match or current is None:
                raise PatchError("malformed hunk header")
            old_left = int(match.group(1)) if match.group(1) is not None else 1
            new_left = int(match.group(2)) if match.group(2) is not None else 1
        elif line.startswith(("Binary files ", "GIT binary patch")):
            raise PatchError("binary changes cannot be reviewed")
        elif re.search(r"\b120000\b", line) and line.startswith(("new file mode", "old mode", "new mode", "index ")):
            raise PatchError("symlink changes are not allowed")
    if old_left or new_left:
        raise PatchError("truncated hunk")
    if not touched:
        raise PatchError("empty proposal")
    return touched


def check_proposal(root: Path, item: Round, config: Config) -> list[str]:
    refusals: list[str] = []
    if item.data["proposal"] is None:
        return refusals
    rel = f"evidence/{item.path.name}/proposal.patch"
    try:
        touched = parse_patch(_read(root, rel, MAX_PATCH_BYTES))
    except Invalid as exc:
        return [str(exc)]
    except PatchError as exc:
        return [f"{rel}: {exc}"]
    for path, (added, removed) in sorted(touched.items()):
        hit = covered_by(path, FIXED_PROTECTED + config.protected)
        if hit:
            refusals.append(f"{rel}: touches protected path {path} (protected: {hit})")
        elif PurePosixPath(path).name.casefold() in INSTRUCTION_FILES and added >= removed:
            refusals.append(
                f"{rel}: {path} must shrink (+{added}/-{removed}); context files that add instructions cost more without proven benefit"
            )
    return refusals


def _git_clean(root: Path) -> tuple[bool, str]:
    try:
        done = subprocess.run(
            ["git", "-C", str(root), "status", "--porcelain", "--untracked-files=normal"],
            capture_output=True, text=True, check=False, timeout=30,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise Invalid(f"--require-clean needs git: {exc}") from exc
    if done.returncode != 0:
        raise Invalid("--require-clean needs a git worktree")
    changed = [line for line in done.stdout.splitlines() if line.strip()]
    return not changed, f"{len(changed)} uncommitted path(s)"


def run(root: Path, round_number: int | None, require_clean: bool) -> dict[str, Any]:
    result: dict[str, Any] = {"status": "", "exit": 0, "invalid": [], "refused": [], "notes": []}
    try:
        if not (root / CONFIG_FILE).exists() and not (root / CONFIG_FILE).is_symlink():
            result.update(status=f"DISABLED: no {CONFIG_FILE}; improvement rounds were not selected", exit=1)
            return result
        values = parse_front_matter(_read(root, CONFIG_FILE))
        enabled = values.get("enabled", "false").lower()
        if enabled not in {"true", "false"}:
            raise Invalid("enabled: expected true or false")
        if enabled == "false":
            result.update(status="DISABLED: IMPROVE.md has enabled: false (owner-controlled)", exit=1)
            return result
        config = validate_config(root, values)
        rounds = load_rounds(root)
        seen: dict[str, str] = {}
        for item in rounds:
            result["invalid"].extend(_validate_round(root, item))
            slice_id = str(item.data["slice"])
            if slice_id in seen:
                result["invalid"].append(f"{item.path.name}: slice {slice_id} already has {seen[slice_id]}; one round per closed slice")
            seen[slice_id] = item.path.name
        if result["invalid"]:
            raise Invalid("; ".join(result["invalid"]))
        if round_number is not None and round_number not in {item.number for item in rounds}:
            raise Invalid(f"evidence/improve-{round_number:03d}: no such round record")
        history = [item for item in rounds if round_number is None or item.number < round_number]
        best, flat, tripped = stop_state(config, history)
        if tripped:
            result["refused"].append(
                f"stop rule: {config.stop_after} consecutive rounds without a gain of {config.min_gain} "
                f"in {config.measure_name} (best {best}); loop is disabled until the owner re-arms it "
                f"(raise first_counted_round and reset the baseline in {CONFIG_FILE})"
            )
        if require_clean:
            clean, detail = _git_clean(root)
            if not clean:
                result["refused"].append(f"worktree is not clean ({detail}); an improvement round never writes into dirty work")
        if round_number is None:
            nxt = max((item.number for item in rounds), default=0) + 1
            result["status"] = "ROUND MAY START" if not result["refused"] else "ROUND REFUSED"
            result["notes"].append(f"next round: improve-{nxt:03d}; best {best}; flat rounds {flat}/{config.stop_after}")
        else:
            item = next(entry for entry in rounds if entry.number == round_number)
            result["refused"].extend(check_proposal(root, item, config))
            tokens = item.data["tokens_used"]
            if tokens is None:
                result["notes"].append("token usage unknown; not invented")
            elif tokens > config.token_cap:
                result["refused"].append(f"tokens_used {tokens} exceeds round_token_cap {config.token_cap}")
            after = stop_state(config, [entry for entry in rounds if entry.number <= round_number])
            result["notes"].append(f"after this round: best {after[0]}; flat rounds {after[1]}/{config.stop_after}")
            if after[2]:
                result["notes"].append("stop rule trips on this round; no further rounds until the owner re-arms")
            result["status"] = "ROUND RECORD VALID" if not result["refused"] else "ROUND REFUSED"
        if config.lessons_file and not Path(config.lessons_file).is_file():
            result["notes"].append("lessons_file not found; continue without it")
        result["exit"] = 1 if result["refused"] else 0
    except Invalid as exc:
        result.update(status=f"INVALID: {exc}", exit=2)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--root", default=".", help="repository root (default: current directory)")
    parser.add_argument("--round", type=int, help="validate this evidence/improve-NNN round record")
    parser.add_argument("--require-clean", action="store_true", help="refuse to start on a dirty git worktree")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args()
    result = run(Path(args.root).resolve(), args.round, args.require_clean)
    if args.format == "json":
        print(json.dumps(result, indent=2))
    else:
        print(result["status"])
        for line in result["refused"]:
            print(f"- refused: {line}")
        for line in result["notes"]:
            print(f"- note: {line}")
        print("- this check never executes the measure command or authenticates human approval")
    return int(result["exit"])


if __name__ == "__main__":
    sys.exit(main())
