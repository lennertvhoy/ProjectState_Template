#!/usr/bin/env python3
"""Primary journey of the release channel slice (release-channel-001), run for real.

    python3 scripts/test_release_channel.py --fleet-root ~/Projects

A plain script, not a pytest module: it prints one line per check and a short summary, and exits 0
only when every check passed (1 otherwise). It runs this checkout's tools, so a failure means the
slice does not hold in the environment where it must work:

1. Generate core, hardened and adopted projects in a temporary directory and check the managed
   block, the vendored gate, the startup size and the honest first gate result of each.
2. Pin the StatePort adapter contract by reading its fixture (nothing from StatePort is executed).
3. Run the read-only fleet doctor over the real fleet root and prove it wrote nothing.
4. Update copies of two real instances (made with ``git archive``, never the originals) with the
   update command: dry run, apply, apply again; check that nothing but the gate and the managed
   block changed and that the doctor then reports both current.
5. Remove the temporary directories.

Real instances are only read. Everything written lives in a temporary directory outside the fleet.
"""

from __future__ import annotations

import argparse
import datetime as dt
import difflib
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path
from typing import Any, NamedTuple, Sequence


sys.dont_write_bytecode = True  # importing the template's helpers must not leave bytecode beside them
TEMPLATE = Path(__file__).resolve().parents[1]
SCRIPTS = TEMPLATE / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import projectstate_release as rel  # noqa: E402


STATEPORT_ADAPTER = Path("StatePort") / "fixtures" / "template-adapters" / "projectstate.application.yaml"
STATEPORT_VALIDATION = (
    'validationCommand: python3 -c "import pathlib,yaml; root=pathlib.Path(\'.\'); '
    "value=yaml.safe_load((root/'STATE.yaml').read_text()); "
    "assert (root/'PROJECT.md').is_file() and value.get('version') == 'projectstate-template-v6'\""
)
STATEPORT_SCHEMA = "projectstate-template-v6"
STARTUP_FILES = ("AGENTS.md", "PROJECT.md", "STATE.yaml")
STARTUP_BUDGET_CHARS = 10000
AUDITED_FILES = ("STATE.yaml", "AGENTS.md", "scripts/projectstate_gate.py")
UPDATE_COPIES = ("example-project-08", "example-project-05")
GENERATED = (("new-core", "new", "core"), ("new-hardened", "new", "hardened"), ("adopt-core", "adopt", "core"))
README_TEXT = "# Existing product\n\nRun it with `make start`.\n"
GIT_LOCATION_VARIABLES = (
    "GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY", "GIT_COMMON_DIR", "GIT_NAMESPACE",
    "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_PREFIX", "GIT_QUARANTINE_PATH",
)
# Defensive options for the commits this journey makes in its own temporary repositories.
GIT_QUIET = ["-c", "user.name=journey", "-c", "user.email=journey@localhost", "-c", "commit.gpgsign=false",
             "-c", "core.hooksPath=/dev/null"]
VERDICT_RANK = {0: "validated", 1: "not validated", 2: "invalid"}  # a lower exit code is a better verdict
FENCE_OPEN = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
FENCE_CLOSE = re.compile(r"^ {0,3}(`{3,}|~{3,})[ \t]*$")
HEADING = re.compile(r"^ {0,3}(#{1,6})(?:[ \t]+(.*?))?[ \t]*$")
CLOSING_HASHES = re.compile(r"(?:^|[ \t]+)#+[ \t]*$")


class Run(NamedTuple):
    code: int
    out: str
    err: str


class Journey:
    """Counts and prints checks. A check line is PASS or FAIL; INFO lines carry facts, not verdicts."""

    def __init__(self) -> None:
        self.passed = 0
        self.failed = 0
        self.summary: list[str] = []

    def check(self, ok: bool, label: str, detail: str = "") -> bool:
        self.passed += bool(ok)
        self.failed += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {label}" + (f": {detail}" if detail else ""), flush=True)
        return bool(ok)

    def info(self, text: str) -> None:
        print(f"INFO  {text}", flush=True)

    def fact(self, text: str) -> None:
        """A line for the final summary (also printed where it happens)."""
        self.summary.append(text)


# --- processes and files ---------------------------------------------------------------------


def clean_env() -> dict[str, str]:
    env = {key: value for key, value in os.environ.items() if key not in GIT_LOCATION_VARIABLES}
    env.update(PYTHONDONTWRITEBYTECODE="1", GIT_OPTIONAL_LOCKS="0", GIT_TERMINAL_PROMPT="0")
    return env


def run(command: Sequence[object], *, cwd: Path | None = None, timeout: float = 300.0) -> Run:
    """Run one command without a shell; never raises (a timeout is exit 124, a missing program 127)."""
    try:
        done = subprocess.run([str(part) for part in command], cwd=cwd, capture_output=True, text=True,
                              errors="replace", timeout=timeout, env=clean_env(), check=False)
    except subprocess.TimeoutExpired:
        return Run(124, "", f"timed out after {timeout:g}s")
    except OSError as exc:
        return Run(127, "", str(exc))
    return Run(done.returncode, done.stdout, done.stderr)


def tail(text: str, limit: int = 300) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else "..." + text[-limit:]


def sha256_path(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def tree_hashes(root: Path) -> dict[str, str]:
    """sha256 of every file below ``root`` except the git directory; symlinked directories are not followed."""
    result: dict[str, str] = {}
    for current, directories, files in os.walk(root):
        directories[:] = sorted(name for name in directories if name != ".git")
        for name in sorted(files):
            path = Path(current) / name
            result[path.relative_to(root).as_posix()] = sha256_path(path) or "unreadable"
    return result


def is_inside(path: Path, parent: Path) -> bool:
    return path == parent or parent in path.parents


# --- the template under test -----------------------------------------------------------------


class Template(NamedTuple):
    gate_bytes: bytes
    gate_sha: str
    block: str
    contract_sha: str
    release: str
    schema: str
    index: dict[str, Any]
    latest: dict[str, Any]

    @property
    def draft(self) -> bool:
        return self.latest.get("status") == "draft"

    @property
    def version_line(self) -> str:
        return f"projectstate-gate {self.release} (state schema {self.schema})"


def load_template(j: Journey) -> Template | None:
    try:
        index = rel.load_index(TEMPLATE)
        gate_bytes = (TEMPLATE / rel.GATE_PATH).read_bytes()
        block = rel.managed_block_text(TEMPLATE)
    except (OSError, ValueError) as exc:
        j.check(False, "template files are readable", str(exc))
        return None
    release = rel.gate_release(gate_bytes.decode("utf-8", errors="replace"))
    latest = next((item for item in index["releases"] if item.get("release") == index.get("latest")), None)
    if not j.check(release is not None and latest is not None and latest.get("release") == release,
                   "release index latest names the gate RELEASE", f"gate {release}, index latest {index.get('latest')}"):
        return None
    assert release is not None and latest is not None
    return Template(gate_bytes, rel.sha256_bytes(gate_bytes), block, rel.contract_sha256(block), release,
                    str(index.get("state_schema")), index, latest)


# --- step 1: generated projects --------------------------------------------------------------


def make_adopt_target(target: Path) -> Run:
    """A temporary git repository with a README, the way a real adopter starts."""
    target.mkdir(parents=True)
    (target / "README.md").write_text(README_TEXT, encoding="utf-8")
    result = Run(0, "", "")
    for command in (["git", "-c", "init.defaultBranch=main", "init", "-q"], ["git", "add", "README.md"],
                    ["git", *GIT_QUIET, "commit", "-q", "-m", "readme"]):
        result = run(command, cwd=target)
        if result.code != 0:
            break
    return result


def check_generated(j: Journey, label: str, project: Path, tpl: Template) -> None:
    agents = (project / "AGENTS.md").read_text(encoding="utf-8")
    block, problem = rel.extract_managed_block(agents)
    starts, ends = agents.count("projectstate:managed:start"), agents.count("projectstate:managed:end")
    j.check(starts == 1 and ends == 1 and block is not None and problem is None,
            f"{label}: AGENTS.md has exactly one managed block", f"{starts} start and {ends} end markers")
    if block is not None:
        j.check(block.content == tpl.block, f"{label}: managed block equals core/AGENTS.managed.md")
        j.check(block.release == tpl.release, f"{label}: managed block marker release equals the gate RELEASE",
                f"marker {block.release}, gate {tpl.release}")
    gate_path = project / "scripts" / "projectstate_gate.py"
    j.check(gate_path.read_bytes() == tpl.gate_bytes, f"{label}: vendored gate is byte-identical to the template gate")
    version = run([sys.executable, "scripts/projectstate_gate.py", "--version"], cwd=project)
    j.check(version.code == 0 and version.out.strip() == tpl.version_line,
            f"{label}: gate --version prints the release", tail(version.out or version.err))
    total = sum(len((project / name).read_text(encoding="utf-8")) for name in STARTUP_FILES)
    j.check(total <= STARTUP_BUDGET_CHARS, f"{label}: AGENTS.md + PROJECT.md + STATE.yaml total {total} characters",
            f"limit {STARTUP_BUDGET_CHARS}")
    gate = run([sys.executable, "scripts/projectstate_gate.py"], cwd=project)
    j.check(gate.code == 1, f"{label}: project gate exits 1 (an honest unvalidated scaffold), never 2",
            f"exit {gate.code}: {tail(gate.out or gate.err, 120)}")


def check_release_hashes(j: Journey, tpl: Template, projects: dict[str, Path]) -> None:
    checked = run([sys.executable, SCRIPTS / "projectstate_release.py", "check"], cwd=TEMPLATE)
    j.check(checked.code == 0, "release index is consistent (projectstate_release.py check)",
            tail(checked.err or checked.out.splitlines()[0] if checked.out else checked.err))
    expected_gate, expected_contract = tpl.latest.get("gate_sha256"), tpl.latest.get("contract_sha256")
    if tpl.draft:
        j.info(f"draft {tpl.release}: the index records no hashes yet; computed gate_sha256 {tpl.gate_sha}, "
               f"contract_sha256 {tpl.contract_sha}")
        expected_gate, expected_contract = tpl.gate_sha, tpl.contract_sha
    else:
        j.check(expected_gate == tpl.gate_sha, f"release {tpl.release}: index gate_sha256 matches the template gate")
        j.check(expected_contract == tpl.contract_sha,
                f"release {tpl.release}: index contract_sha256 matches the managed block")
    which = "computed (draft)" if tpl.draft else "released"
    for label, project in projects.items():
        block, _ = rel.extract_managed_block((project / "AGENTS.md").read_text(encoding="utf-8"))
        gate_sha = sha256_path(project / "scripts" / "projectstate_gate.py")
        contract_sha = rel.contract_sha256(block.content) if block else None
        j.check(gate_sha == expected_gate and contract_sha == expected_contract,
                f"{label}: gate and block hashes equal the {which} {tpl.release} hashes")
    j.fact(f"template {tpl.release} ({'draft' if tpl.draft else 'released'}): gate sha256 {tpl.gate_sha[:12]}, "
           f"contract sha256 {tpl.contract_sha[:12]}")


def step_generate(j: Journey, workdir: Path, tpl: Template) -> dict[str, Path]:
    projects: dict[str, Path] = {}
    for label, mode, profile in GENERATED:
        target = workdir / label
        if mode == "adopt":
            prepared = make_adopt_target(target)
            if not j.check(prepared.code == 0, f"{label}: temporary git repository with a README",
                           tail(prepared.err or prepared.out)):
                continue
        done = run([sys.executable, SCRIPTS / "init_template.py", mode, "--name", "Journey Demo", "--target", target,
                    "--profile", profile], cwd=TEMPLATE)
        if not j.check(done.code == 0, f"{label}: init_template.py {mode} --profile {profile} exits 0",
                       tail(done.err or done.out)):
            continue
        projects[label] = target
        check_generated(j, label, target, tpl)
        if mode == "adopt":
            j.check((target / "README.md").read_text(encoding="utf-8") == README_TEXT,
                    f"{label}: the existing README is preserved")
    check_release_hashes(j, tpl, projects)
    j.fact(f"generation: {', '.join(projects) or 'nothing'} generated and checked")
    return projects


# --- step 2: the StatePort adapter contract --------------------------------------------------


def step_stateport(j: Journey, fleet_root: Path, projects: dict[str, Path]) -> None:
    adapter = fleet_root / STATEPORT_ADAPTER
    try:
        lines = [line for line in adapter.read_text(encoding="utf-8").splitlines() if line.startswith("validationCommand:")]
    except OSError as exc:
        j.check(False, "StatePort adapter validationCommand is unchanged", f"skipped, cannot read {adapter}: {exc.strerror}")
        lines = None
    if lines is not None:
        j.check(lines == [STATEPORT_VALIDATION], "StatePort adapter validationCommand is unchanged",
                "the one validationCommand line equals the pinned text" if lines == [STATEPORT_VALIDATION]
                else f"found {len(lines)} line(s): {tail(' | '.join(lines), 200)}")
    try:
        import yaml  # test code only: the pinned rule uses yaml.safe_load, exactly as the adapter does
    except ImportError:
        j.check(False, "PyYAML is available to apply the StatePort rule", "install PyYAML")
        return
    held = 0
    for label, project in projects.items():
        try:
            value = yaml.safe_load((project / "STATE.yaml").read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as exc:
            j.check(False, f"{label}: StatePort rule applies", f"STATE.yaml unreadable: {exc}")
            continue
        value = value if isinstance(value, dict) else {}
        rules = {
            f"version is {STATEPORT_SCHEMA}": value.get("version") == STATEPORT_SCHEMA,
            "PROJECT.md exists": (project / "PROJECT.md").is_file(),
            "profile is core or hardened": value.get("profile") in ("core", "hardened"),
            "current_slice is a mapping": isinstance(value.get("current_slice"), dict),
        }
        broken = [rule for rule, ok in rules.items() if not ok]
        held += not broken
        j.check(not broken, f"{label}: StatePort adapter rule holds (yaml.safe_load)",
                "all four conditions" if not broken else "violated: " + ", ".join(broken))
    j.fact(f"StatePort contract: validationCommand {'pinned' if lines == [STATEPORT_VALIDATION] else 'NOT pinned'}; "
           f"rule holds for {held}/{len(projects)} generated projects")


# --- step 3: the fleet doctor on the real fleet ----------------------------------------------


def git_dir_of(repo: Path) -> Path | None:
    dot = repo / ".git"
    if dot.is_dir():
        return dot
    if dot.is_file():  # a linked worktree: the file names the real git directory
        text = dot.read_text(encoding="utf-8", errors="replace").strip()
        if text.startswith("gitdir:"):
            target = Path(text[len("gitdir:"):].strip())
            return target if target.is_absolute() else (repo / target).resolve()
    return None


def audit_repository(repo: Path) -> dict[str, Any]:
    status = run(["git", "--no-pager", "-C", repo, "-c", "core.fsmonitor=false", "status", "--porcelain"], timeout=120)
    git_dir = git_dir_of(repo)
    try:
        mtime = (git_dir / "index").stat().st_mtime_ns if git_dir else None
    except OSError:
        mtime = None
    return {
        "status": status.out if status.code == 0 else f"git status failed ({status.code}): {tail(status.err)}",
        "index_mtime_ns": mtime,
        **{name: sha256_path(repo / name) for name in AUDITED_FILES},
    }


def audit_fleet(root: Path) -> dict[str, dict[str, Any]]:
    children = sorted((child for child in root.iterdir() if child.is_dir() and os.path.lexists(child / ".git")),
                      key=lambda child: child.name.casefold())
    return {child.name: audit_repository(child) for child in children}


def audit_differences(before: dict[str, dict[str, Any]], after: dict[str, dict[str, Any]]) -> list[str]:
    problems: list[str] = []
    for name in sorted(set(before) | set(after)):
        if name not in before or name not in after:
            problems.append(f"{name}: repository {'appeared' if name in after else 'disappeared'}")
            continue
        for key in before[name]:
            if before[name][key] != after[name].get(key):
                problems.append(f"{name}: {key} changed")
    return problems


def verify_report(j: Journey, report: dict[str, Any]) -> None:
    """Every v6 row has a gate and a contract status, and the summary counts agree with the rows."""
    rows, summary = report.get("repositories", []), report.get("summary", {})
    v6 = [row for row in rows if row.get("kind") == "v6"]
    instances = [row for row in v6 if row.get("role") != "template"]
    unreported = [row.get("name") for row in v6 if not all(
        isinstance(row.get(part), dict) and row[part].get("status") for part in ("gate", "contract"))]
    j.check(bool(v6) and not unreported, f"doctor: all {len(v6)} v6 repositories have a gate status and a contract status",
            f"missing for {unreported}" if unreported else "")
    disagreements: list[str] = []

    def agree(label: str, expected: Any, actual: Any) -> None:
        if expected != actual:
            disagreements.append(f"{label}: rows say {expected}, summary says {actual}")

    def distribution(label: str, counted: Counter[str], recorded: Any) -> None:
        recorded = recorded if isinstance(recorded, dict) else {}
        for state in sorted(set(counted) | set(recorded)):
            agree(f"{label}.{state}", counted.get(state, 0), recorded.get(state))

    agree("repositories", len(rows), summary.get("repositories"))
    distribution("kinds", Counter(str(row.get("kind")) for row in rows), summary.get("kinds"))
    with_git = [row["git"] for row in rows if row.get("git") is not None]
    agree("with_git", len(with_git), summary.get("with_git"))
    agree("dirty", sum(any(facts.get(key) for key in ("staged", "unstaged", "untracked")) for facts in with_git),
          summary.get("dirty"))
    distribution("gates", Counter(str(row["gate"].get("status")) for row in instances if isinstance(row.get("gate"), dict)),
                 summary.get("gates"))
    distribution("contracts", Counter(str(row["contract"].get("status")) for row in instances
                                      if isinstance(row.get("contract"), dict)), summary.get("contracts"))
    distribution("verdicts", Counter(str(row.get("verdict", {}).get("verdict")) for row in v6), summary.get("verdicts"))
    agree("size_flagged", sum(bool(row.get("sizes", {}).get("flags")) for row in v6), summary.get("size_flagged"))
    agree("notices", sum(row.get("notices", {}).get("total", 0) for row in v6), summary.get("notices"))
    inbox = report.get("inbox", {})
    distribution("inbox", Counter({section: len(items) for section, items in inbox.items()}), summary.get("inbox"))
    j.check(not disagreements, "doctor: summary counts agree with the repository rows and the inbox",
            "; ".join(disagreements[:4]))
    j.check(report.get("read_only") is True and report.get("format") == "projectstate-fleet/1",
            "doctor: report declares format projectstate-fleet/1 and read_only")


def distribution_text(counts: dict[str, int]) -> str:
    return ", ".join(f"{state} {count}" for state, count in counts.items())


def step_fleet(j: Journey, fleet_root: Path) -> None:
    before = audit_fleet(fleet_root)
    started = time.monotonic()
    done = run([sys.executable, SCRIPTS / "projectstate_fleet.py", "--root", fleet_root, "--stdout", "--format", "json"],
              timeout=900)
    runtime = time.monotonic() - started
    after = audit_fleet(fleet_root)
    differences = audit_differences(before, after)
    j.check(not differences, f"doctor wrote nothing: {len(before)} repositories with .git unchanged",
            "git status, .git/index mtime and sha256 of STATE.yaml, AGENTS.md and the gate"
            if not differences else "; ".join(differences[:6]))
    if not j.check(done.code == 0, "doctor: projectstate_fleet.py --stdout --format json exits 0",
                   f"exit {done.code} in {runtime:.1f}s" + ("" if done.code == 0 else f": {tail(done.err)}")):
        return
    try:
        report = json.loads(done.out)
    except ValueError as exc:
        j.check(False, "doctor: stdout is one JSON document", str(exc))
        return
    verify_report(j, report)
    summary = report.get("summary", {})
    inbox = summary.get("inbox", {})
    j.info(f"doctor gate statuses: {distribution_text(summary.get('gates', {}))}")
    j.info(f"doctor contract statuses: {distribution_text(summary.get('contracts', {}))}")
    j.info(f"doctor inbox items per section: {distribution_text(inbox)}")
    j.info(f"doctor runtime: {runtime:.1f}s for {summary.get('repositories')} repositories")
    j.fact(f"fleet doctor on {fleet_root}: {summary.get('repositories')} repositories "
           f"({distribution_text(summary.get('kinds', {}))}), runtime {runtime:.1f}s")
    j.fact(f"  gates: {distribution_text(summary.get('gates', {}))}")
    j.fact(f"  contracts: {distribution_text(summary.get('contracts', {}))}")
    j.fact(f"  inbox: {distribution_text(inbox)}")
    j.fact(f"  no-write audit: {len(before)} repositories with .git, "
           f"{'nothing changed' if not differences else str(len(differences)) + ' differences'}")


# --- step 4: update on copies of real instances ----------------------------------------------


def split_lines(text: str) -> list[str]:
    parts = text.split("\n")
    lines = [part + "\n" for part in parts[:-1]]
    if parts[-1]:
        lines.append(parts[-1])
    return lines


def split_frontmatter(text: str) -> tuple[str, str]:
    lines = split_lines(text)
    if lines and lines[0].rstrip("\n") == "---":
        for index in range(1, len(lines)):
            if lines[index].rstrip("\n") == "---":
                return "".join(lines[: index + 1]), "".join(lines[index + 1:])
    return "", text


def fence_mask(lines: list[str]) -> list[bool]:
    """True for lines inside a fenced code block (fence lines included)."""
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


def find_heading(lines: list[str], level: int, title: str) -> int | None:
    mask = fence_mask(lines)
    for index, line in enumerate(lines):
        match = None if mask[index] else HEADING.match(line.rstrip("\n"))
        if match and len(match.group(1)) == level and CLOSING_HASHES.sub("", match.group(2) or "").strip() == title:
            return index
    return None


def find_notice(lines: list[str], name: str) -> tuple[int, int] | None:
    mask = fence_mask(lines)
    start = re.compile(rf"^[ \t]*<!--[ \t]*projectstate-{re.escape(name)}:start[ \t]*-->[ \t]*$")
    end = re.compile(rf"^[ \t]*<!--[ \t]*projectstate-{re.escape(name)}:end[ \t]*-->[ \t]*$")
    for first, line in enumerate(lines):
        if mask[first] or not start.match(line.rstrip("\n")):
            continue
        for last in range(first + 1, len(lines)):
            if not mask[last] and end.match(lines[last].rstrip("\n")):
                return first, last
    return None


def project_text(text: str) -> tuple[str, str]:
    """(frontmatter, project-owned text): the file without its frontmatter and without any managed block."""
    frontmatter, rest = split_frontmatter(text)
    block, _ = rel.extract_managed_block(rest)
    return frontmatter, (rest[: block.start] + rest[block.end:]) if block else rest


def account_for_agents(original: str, updated: str, plan: dict[str, Any]) -> tuple[bool, str]:
    """Every non-blank line of the original is kept in order, or lies in a section or notice the plan reports removed.

    Works from the original text and the reported removals only: the notices first, then the sections in the
    order reported, each located by its heading. What is left must equal the project-owned text of the new file.
    """
    old_frontmatter, old_body = project_text(original)
    new_frontmatter, new_body = project_text(updated)
    if new_frontmatter != old_frontmatter:
        return False, "the frontmatter changed"
    lines = split_lines(old_body)
    contract = plan.get("contract") or {}
    for notice in contract.get("removed_notices", []):
        found = find_notice(lines, notice["name"])
        if found is None or found[1] - found[0] + 1 != notice["lines"]:
            return False, f"reported notice projectstate-{notice['name']} is not in the original as reported"
        del lines[found[0]: found[1] + 1]
    for section in contract.get("removed_sections", []):
        start = find_heading(lines, section["level"], section["heading"])
        if start is None:
            return False, f"reported section {section['heading']!r} (level {section['level']}) is not in the original"
        del lines[start: start + section["lines"]]
    expected = [line.rstrip("\n") for line in lines if line.strip()]
    actual = [line.rstrip("\n") for line in split_lines(new_body) if line.strip()]
    if expected == actual:
        return True, f"{len(actual)} non-blank local lines preserved verbatim"
    diff = list(difflib.unified_diff(expected, actual, "original minus reported removals", "updated", lineterm="", n=0))
    return False, "; ".join(diff[2:8]) or "line counts differ"


def verdict_class(root: Path, project: Path) -> int:
    return run([sys.executable, root / "scripts" / "projectstate_gate.py", "--root", project]).code


def update_json(project: Path, *flags: str) -> tuple[Run, dict[str, Any]]:
    done = run([sys.executable, SCRIPTS / "projectstate_update.py", "--target", project, "--json", *flags])
    try:
        payload = json.loads(done.out)
    except ValueError:
        payload = {}
    return done, payload if isinstance(payload, dict) else {}


def needed_flags(plan: dict[str, Any]) -> list[str]:
    """Only the flags this dry run's plan shows are needed."""
    gate, contract = plan.get("gate") or {}, plan.get("contract") or {}
    flags: list[str] = []
    if gate.get("action") == "replace_edited":
        flags.append("--replace-edited-gate")
    if contract.get("action") == "replace_edited":
        flags.append("--replace-edited-contract")
    if contract.get("modified_sections") or contract.get("local_template_headings"):
        flags.append("--accept-modified-sections")
    return flags


def pre_update_revision(source: Path) -> str:
    """HEAD, or the parent of the commit that first added a managed block once the instance is already updated.

    The journey must exercise a real conversion, so an instance that the rollout already brought to a
    managed release is exported as it was just before that update.
    """
    found = run(["git", "-C", str(source), "log", "--reverse", "--format=%H", "-S", "projectstate:managed:start",
                 "--", "AGENTS.md"])
    first = found.out.split()[0] if found.code == 0 and found.out.split() else None
    return f"{first}^" if first else "HEAD"


def export_instance(source: Path, destination: Path) -> Run:
    """git archive of a real instance before any managed update, extracted fresh; the original is only read."""
    destination.mkdir(parents=True)
    revision = pre_update_revision(source)
    if revision != "HEAD":
        print(f"INFO  {source.name}: already updated; exporting its pre-update revision {revision}")
    with tempfile.TemporaryFile() as errors:
        archive = subprocess.Popen(["git", "-C", str(source), "archive", revision], stdout=subprocess.PIPE,
                                   stderr=errors, env=clean_env())
        assert archive.stdout is not None
        untar = subprocess.run(["tar", "-x", "-C", str(destination)], stdin=archive.stdout, capture_output=True,
                               check=False)
        archive.stdout.close()
        code = archive.wait()
        errors.seek(0)
        archive_errors = errors.read().decode("utf-8", errors="replace")
    if code != 0:
        return Run(code, "", f"git archive failed: {archive_errors}")
    return Run(untar.returncode, "", untar.stderr.decode("utf-8", errors="replace"))


def commit_base(project: Path) -> Run:
    for command in (["git", "-c", "init.defaultBranch=main", "init", "-q"], ["git", "add", "-A"],
                    ["git", *GIT_QUIET, "commit", "-q", "-m", "base"]):
        result = run(command, cwd=project)
        if result.code != 0:
            return result
    return Run(0, "", "")


def describe_plan(plan: dict[str, Any]) -> str:
    gate, contract = plan.get("gate") or {}, plan.get("contract") or {}
    sections = Counter(item.get("kind") for item in contract.get("removed_sections", []))
    modified = [item["heading"] for item in contract.get("modified_sections", [])]
    return (f"gate {gate.get('action')} ({gate.get('from_release')} -> {plan.get('release')}), "
            f"contract {contract.get('action')}: removed {sections.get('template', 0)} known template sections, "
            f"{sections.get('refresh', 0)} refresh sections, {len(contract.get('removed_notices', []))} notices, "
            f"{len(modified)} modified sections{' ' + str(modified) if modified else ''}")


def update_one(j: Journey, name: str, source: Path, fleet_copy: Path, tpl: Template) -> dict[str, Any] | None:
    project = fleet_copy / name
    exported = export_instance(source, project)
    if not j.check(exported.code == 0, f"{name}: git archive HEAD copied into the scratch fleet", tail(exported.err)):
        return None
    committed = commit_base(project)
    if not j.check(committed.code == 0, f"{name}: scratch copy committed as a clean base", tail(committed.err)):
        return None
    original = (project / "AGENTS.md").read_text(encoding="utf-8")
    before = tree_hashes(project)
    index_before = sha256_path(project / ".git" / "index")
    verdict_before = verdict_class(TEMPLATE, project)

    dry, plan = update_json(project)
    j.check(dry.code == 0 and plan.get("applied") is False and not plan.get("refused"),
            f"{name}: update dry run exits 0 and plans without refusing",
            f"exit {dry.code}; " + (describe_plan(plan) if plan.get("gate") else tail(dry.err or dry.out)))
    flags = needed_flags(plan)
    j.info(f"{name}: flags needed per the dry run: {' '.join(flags) or '(none)'}")
    flagged = False
    if dry.code == 2 and plan.get("gate") and flags:
        dry, plan = update_json(project, *flags)
        flagged = True
        j.check(dry.code == 0 and not plan.get("refused"), f"{name}: dry run with those flags is accepted",
                tail(" ".join(plan.get("refused", [])) or dry.err))
    j.check(tree_hashes(project) == before, f"{name}: the dry run wrote nothing")
    if dry.code != 0 or not plan.get("gate"):
        return None
    del flagged

    applied, applied_plan = update_json(project, "--apply", *flags)
    j.check(applied.code == 0 and applied_plan.get("applied") is True, f"{name}: update --apply exits 0 and applies",
            f"exit {applied.code}: {tail(applied.err) if applied.code else describe_plan(applied_plan)}")
    j.check(applied_plan.get("gate") == plan.get("gate") and applied_plan.get("contract") == plan.get("contract"),
            f"{name}: the applied report equals the dry-run report")
    after = tree_hashes(project)
    changed = sorted(path for path in set(before) | set(after) if before.get(path) != after.get(path))
    allowed = {"AGENTS.md", "scripts/projectstate_gate.py"}
    untouched = [path for path in before if path in ("PROJECT.md", "STATE.yaml") or path.startswith("evidence/")]
    j.check(set(changed) <= allowed, f"{name}: only AGENTS.md and the gate changed", f"changed {changed}")
    j.check(all(before.get(path) == after.get(path) for path in untouched),
            f"{name}: PROJECT.md, STATE.yaml and evidence/ are byte-identical ({len(untouched)} files)")
    updated = (project / "AGENTS.md").read_text(encoding="utf-8")
    block, problem = rel.extract_managed_block(updated)
    j.check(block is not None and problem is None and block.content == tpl.block and block.release == tpl.release,
            f"{name}: AGENTS.md now carries the template block, marker release {tpl.release}")
    j.check(sha256_path(project / "scripts" / "projectstate_gate.py") == tpl.gate_sha,
            f"{name}: the vendored gate is now byte-identical to the template gate")
    ok, detail = account_for_agents(original, updated, plan)
    j.check(ok, f"{name}: every original line outside the frontmatter and block is preserved or was reported removed", detail)
    version = run([sys.executable, "scripts/projectstate_gate.py", "--version"], cwd=project)
    j.check(version.out.strip() == tpl.version_line, f"{name}: the updated gate prints the release", tail(version.out or version.err))
    verdict_after = verdict_class(TEMPLATE, project)
    j.check(verdict_after <= verdict_before,
            f"{name}: template gate verdict is unchanged or better",
            f"{VERDICT_RANK.get(verdict_before, verdict_before)} -> {VERDICT_RANK.get(verdict_after, verdict_after)}")

    again, again_plan = update_json(project, "--apply", *flags)
    quiet = ((again_plan.get("gate") or {}).get("action") == "none"
             and (again_plan.get("contract") or {}).get("action") == "none")
    j.check(again.code == 0 and again_plan.get("applied") is False and quiet and tree_hashes(project) == after,
            f"{name}: a second --apply changes nothing", f"exit {again.code}")
    j.check(sha256_path(project / ".git" / "index") == index_before, f"{name}: the update never touched the git index")
    return {"name": name, "plan": plan, "flags": flags, "verdicts": (verdict_before, verdict_after),
            "second_apply_noop": again.code == 0 and quiet}


def doctor_rows(fleet_copy: Path, *extra: object) -> dict[str, dict[str, Any]] | None:
    done = run([sys.executable, SCRIPTS / "projectstate_fleet.py", "--root", fleet_copy, "--stdout", "--format", "json",
                *extra])
    try:
        report = json.loads(done.out)
    except ValueError:
        return None
    return {row["name"]: row for row in report.get("repositories", [])} if done.code == 0 else None


def check_current(j: Journey, label: str, rows: dict[str, dict[str, Any]] | None, names: list[str]) -> None:
    for name in names:
        row = (rows or {}).get(name)
        gate = (row or {}).get("gate") or {}
        contract = (row or {}).get("contract") or {}
        j.check(row is not None and gate.get("status") == "current" and contract.get("status") == "current",
                f"{label}: {name} gate and contract are current",
                f"gate {gate.get('status')}, contract {contract.get('status')}")


def step_doctor_on_copies(j: Journey, workdir: Path, fleet_copy: Path, tpl: Template, names: list[str]) -> None:
    rows = doctor_rows(fleet_copy)
    if not tpl.draft:
        check_current(j, "doctor on the updated copies", rows, names)
        return
    # A draft records no hashes yet: the doctor reports a repository carrying the candidate as "draft".
    for name in names:
        row = (rows or {}).get(name) or {}
        gate, contract = row.get("gate") or {}, row.get("contract") or {}
        j.check(gate.get("status") == "draft" and contract.get("status") == "draft",
                f"doctor on the updated copies: {name} reads draft {tpl.release}",
                f"gate {gate.get('status')}, contract {contract.get('status')}")
        j.check(gate.get("sha256") == tpl.gate_sha and contract.get("sha256") == tpl.contract_sha
                and contract.get("declared") == tpl.release,
                f"doctor on the updated copies: {name} carries the computed hashes of draft {tpl.release}",
                f"gate {str(gate.get('sha256'))[:12]}, block {str(contract.get('sha256'))[:12]}, marker {contract.get('declared')}")
    # What the doctor says once the release is cut: cut a scratch copy of the three files the doctor reads.
    scratch = workdir / "cut-template"
    for relative in (rel.GATE_PATH, rel.MANAGED_PATH, rel.INDEX_PATH):
        (scratch / relative).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(TEMPLATE / relative, scratch / relative)
    cut = run([sys.executable, SCRIPTS / "projectstate_release.py", "cut", "--date", dt.date.today().isoformat(),
               "--template", scratch])
    if j.check(cut.code == 0, "scratch template: projectstate_release.py cut fills the draft", tail(cut.err or cut.out)):
        check_current(j, f"doctor after a scratch cut of {tpl.release}",
                      doctor_rows(fleet_copy, "--template", scratch), names)


def step_update(j: Journey, fleet_root: Path, workdir: Path, tpl: Template) -> None:
    fleet_copy = workdir / "fleet"
    fleet_copy.mkdir()
    results: list[dict[str, Any]] = []
    for name in UPDATE_COPIES:
        source = fleet_root / name
        if not j.check(source.is_dir(), f"{name}: real instance found under the fleet root", str(source)):
            continue
        result = update_one(j, name, source, fleet_copy, tpl)
        if result:
            results.append(result)
            j.fact(f"update {name}: flags {' '.join(result['flags']) or '(none)'}; {describe_plan(result['plan'])}; "
                   f"second --apply no-op {'yes' if result['second_apply_noop'] else 'NO'}; verdict "
                   f"{VERDICT_RANK.get(result['verdicts'][0])} -> {VERDICT_RANK.get(result['verdicts'][1])}")
    if results:
        step_doctor_on_copies(j, workdir, fleet_copy, tpl, [item["name"] for item in results])
        j.fact(f"doctor on the updated copies against {'draft' if tpl.draft else 'released'} {tpl.release}: "
               "see the checks above")


# --- main ------------------------------------------------------------------------------------


def run_steps(j: Journey, fleet_root: Path, workdir: Path) -> None:
    tpl = load_template(j)
    steps = [("fleet doctor on the real fleet", lambda: step_fleet(j, fleet_root))]
    projects: dict[str, Path] = {}
    if tpl is not None:
        def generate() -> None:
            projects.update(step_generate(j, workdir / "generated", tpl))
        steps = [("generated projects", generate), ("StatePort contract", lambda: step_stateport(j, fleet_root, projects)),
                 *steps, ("update on copies", lambda: step_update(j, fleet_root, workdir, tpl))]
    for name, step in steps:
        print(f"--- {name}", flush=True)
        try:
            step()
        except Exception as exc:  # a crashed step is a failed journey, not a reason to skip the other steps
            j.check(False, f"{name}: step completed", f"{type(exc).__name__}: {exc}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the release channel primary journey for real.")
    parser.add_argument("--fleet-root", required=True, type=Path,
                        help="Folder whose children are the real repositories (read only), e.g. ~/Projects")
    parser.add_argument("--keep-temp", action="store_true", help="Keep the temporary directory and print its path")
    args = parser.parse_args(argv)
    fleet_root = args.fleet_root.expanduser().resolve()
    j = Journey()
    if not fleet_root.is_dir():
        j.check(False, "fleet root is a directory", str(fleet_root))
        return 1
    workdir = Path(tempfile.mkdtemp(prefix="projectstate-journey-")).resolve()
    started = time.monotonic()
    try:
        if is_inside(workdir, fleet_root):
            j.check(False, "temporary directory is outside the fleet root", f"{workdir} is inside {fleet_root}")
        else:
            print(f"journey: template {TEMPLATE}, fleet root {fleet_root}, scratch {workdir}", flush=True)
            run_steps(j, fleet_root, workdir)
    finally:
        if args.keep_temp:
            print(f"INFO  scratch directory kept: {workdir}")
        else:
            shutil.rmtree(workdir, ignore_errors=True)
            j.check(not workdir.exists(), "temporary directories removed")
    print("--- summary")
    for line in j.summary:
        print(f"  {line}")
    verdict = "PASSED" if j.failed == 0 else "FAILED"
    print(f"RESULT: {verdict}: {j.passed} checks passed, {j.failed} failed, {time.monotonic() - started:.0f}s "
          f"(exit {0 if j.failed == 0 else 1})")
    return 0 if j.failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
