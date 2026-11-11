#!/usr/bin/env python3
"""Primary journey for proof-by-run-001: a slice proven by a run moves on, one proven by word waits.

Everything runs through the real command lines, in scratch projects made by ``init_template.py new``:

1. A new project carries the gate, the journey-recording tool and a contract that names the tool.
2. The project's own ``projectstate_verify.py --run`` records a passing journey, marks the slice
   ``validated`` and prints the gate's verdict, which names the run.
3. The fleet doctor lists that slice as an open decision that blocks nothing; after the next slice
   follows it stays listed, with the command for it, until a decision is recorded on it.
4. A journey typed by hand is named as such by the gate, waits in "Your decisions", cannot be accepted
   by a delegate, and replacing it without the owner's decision is still reported for review.
5. ``projectstate_update.py`` brings a 6.4.0 instance to this release: gate, journey tool and contract
   block, with the gate's exit code unchanged. This step reads the v6.4.0 tag of this repository.

    python3 scripts/test_proof_by_run.py

Exit 0 when every check holds, 1 otherwise. Nothing outside a temporary directory is written.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent
sys.path.insert(0, str(SCRIPTS))

import projectstate_release as rel  # noqa: E402

OLD_TAG = "v6.4.0"
OLD_RELEASE = "6.4.0"
JOURNEY = """python3 -c "print('hello')\""""
ENVIRONMENT = "Local Python 3"
DELEGATING_WORDS = "journey on a scratch copy: you make the choices"
PROJECT = (
    "# Demo\n\n## User\n\nA person who runs the demo.\n\n## Outcome\n\nThe demo prints its greeting.\n\n"
    "## Scope\n\n- The greeting.\n\n## Non-goals\n\n- Anything else.\n\n## Durable constraints\n\n- None.\n"
)
PLACEHOLDERS = (
    ('description: "Not yet defined — derive the smallest end-to-end user journey from PROJECT.md."',
     'description: "Print the greeting."'),
    ('command: "Not yet defined — record the exact human-authorized command."', f"command: '{JOURNEY}'"),
    ('environment: "Not yet defined — record the representative environment."', f'environment: "{ENVIRONMENT}"'),
    ('blockers:\n  - "Primary user and product outcome require human confirmation."\n', "blockers: []\n"),
)


def run(command: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ, GIT_OPTIONAL_LOCKS="0", GIT_TERMINAL_PROMPT="0", PYTHONDONTWRITEBYTECODE="1",
               GIT_AUTHOR_NAME="Journey", GIT_AUTHOR_EMAIL="journey@example.invalid",
               GIT_COMMITTER_NAME="Journey", GIT_COMMITTER_EMAIL="journey@example.invalid")
    return subprocess.run(command, cwd=cwd, capture_output=True, text=True, check=False, env=env)


def tool(name: str, *args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return run([sys.executable, str(SCRIPTS / name), *args], cwd=cwd)


def commit(repo: Path, message: str) -> None:
    for args in (["add", "-A"], ["-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null", "commit", "-q", "-m", message]):
        done = run(["git", "-C", str(repo), "-c", "gc.auto=0", "-c", "maintenance.auto=false", *args])
        if done.returncode != 0:
            raise SystemExit(f"git {args[0]} failed in {repo}: {done.stderr.strip()}")


def new_project(target: Path) -> None:
    done = tool("init_template.py", "new", "--name", target.name, "--target", str(target))
    if done.returncode != 0:
        raise SystemExit(f"init_template.py new failed: {done.stdout}{done.stderr}")
    state = target / "STATE.yaml"
    text = state.read_text(encoding="utf-8")
    for old, new in PLACEHOLDERS:
        if text.count(old) != 1:
            raise SystemExit(f"the generated STATE.yaml no longer holds the placeholder {old!r}")
        text = text.replace(old, new)
    state.write_text(text, encoding="utf-8")
    # The owner's part: a generated PROJECT.md holds placeholders, and the gate blocks on them.
    (target / "PROJECT.md").write_text(PROJECT, encoding="utf-8")
    commit(target, "define the outcome and the journey")


def type_result_by_hand(target: Path) -> None:
    """What an agent without the tool does: type the passed result into both records."""
    state = target / "STATE.yaml"
    text = state.read_text(encoding="utf-8")
    text = text.replace("  status: planned\n", "  status: validated\n").replace("    status: not_run\n", "    status: passed\n")
    state.write_text(text.replace("  primary_journey: not_run\n", "  primary_journey: passed\n"), encoding="utf-8")
    summary = target / "evidence" / "bootstrap-001" / "summary.md"
    text = summary.read_text(encoding="utf-8")
    for old, new in (("- Environment: not recorded", f"- Environment: {ENVIRONMENT}"),
                     ("- Command: not recorded", f"- Command: `{JOURNEY}`"),
                     ("- Result: not run", "- Result: passed"), ("- Exit code: not recorded", "- Exit code: 0")):
        text = text.replace(old, new)
    summary.write_text(text, encoding="utf-8")


def follow_with_next_slice(target: Path) -> None:
    """Replace the current slice with a new one, as an agent starting the next slice does."""
    state = target / "STATE.yaml"
    text = state.read_text(encoding="utf-8").replace("bootstrap-001", "next-002")
    text = text.replace("  status: validated\n", "  status: planned\n").replace("    status: passed\n", "    status: not_run\n")
    state.write_text(text.replace("  primary_journey: passed\n", "  primary_journey: not_run\n"), encoding="utf-8")
    summary = target / "evidence" / "next-002" / "summary.md"
    summary.parent.mkdir()
    summary.write_text("# Evidence: next-002\n\n## Primary journey\n\n- Result: not run\n\n## Secondary checks\n\n- None.\n\n"
                       "## Artifacts\n\n- None recorded.\n\n## Limitations\n\n- None.\n", encoding="utf-8")
    commit(target, "start next-002")


def doctor(root: Path) -> dict[str, Any]:
    done = tool("projectstate_fleet.py", "--root", str(root), "--template", str(ROOT), "--stdout", "--format", "json",
                "--journeys", str(root.parent / "no-journeys"))
    if done.returncode != 0:
        raise SystemExit(f"fleet doctor failed on {root}: {done.stderr.strip()}")
    return json.loads(done.stdout)


def listed(report: dict[str, Any], section: str, name: str, kind: str | None = None) -> list[dict[str, Any]]:
    return [item for item in report["inbox"][section]
            if item["repository"] == name and (kind is None or item["kind"] == kind)]


def gate_of(target: Path) -> subprocess.CompletedProcess[str]:
    return run([sys.executable, str(target / "scripts" / "projectstate_gate.py"), "--root", str(target)])


def old_release_files() -> tuple[bytes, str] | None:
    """The gate and managed block of the previous release, read from its tag; None when the tag is not here."""
    gate = subprocess.run(["git", "-C", str(ROOT), "show", f"{OLD_TAG}:{rel.GATE_PATH.as_posix()}"],
                          capture_output=True, check=False)
    block = subprocess.run(["git", "-C", str(ROOT), "show", f"{OLD_TAG}:{rel.MANAGED_PATH.as_posix()}"],
                           capture_output=True, check=False)
    if gate.returncode != 0 or block.returncode != 0:
        return None
    return gate.stdout, block.stdout.decode("utf-8")


def downgrade(target: Path, gate: bytes, block: str) -> None:
    """Make ``target`` what an instance of the previous release is: its gate, its block, no journey tool."""
    (target / rel.GATE_PATH).write_bytes(gate)
    (target / rel.VERIFY_PATH).unlink()
    agents = target / "AGENTS.md"
    text = agents.read_text(encoding="utf-8")
    found, problem = rel.extract_managed_block(text)
    if found is None:
        raise SystemExit(f"the generated AGENTS.md has no managed block: {problem}")
    agents.write_text(text[:found.start] + rel.render_managed_block(OLD_RELEASE, block) + text[found.end:], encoding="utf-8")


def main() -> int:
    failures: list[str] = []

    def check(ok: bool, label: str, detail: str = "") -> None:
        print(f"{'ok  ' if ok else 'FAIL'} {label}" + (f": {detail}" if detail and not ok else ""))
        if not ok:
            failures.append(label)

    release = rel.gate_release((ROOT / rel.GATE_PATH).read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory(prefix="projectstate-proof-") as tmp:
        fleet = Path(tmp) / "fleet"
        fleet.mkdir()

        # 1 and 2: a new project, its journey recorded by its own copy of the tool
        ran = fleet / "ran"
        new_project(ran)
        block, _ = rel.extract_managed_block((ran / "AGENTS.md").read_text(encoding="utf-8"))
        check((ran / rel.GATE_PATH).is_file() and (ran / rel.VERIFY_PATH).is_file(),
              "a new project carries the gate and the journey tool")
        check(block is not None and block.release == release and rel.VERIFY_PATH.as_posix() in block.content,
              "its contract block is this release and names the journey tool")
        recorded = run([sys.executable, str(ran / rel.VERIFY_PATH), "--run"], cwd=ran)
        check(recorded.returncode == 0 and "slice status set from planned to validated" in recorded.stdout,
              "the project's own tool records the passing journey and marks the slice validated", recorded.stdout + recorded.stderr)
        check("RECORDED OUTCOME VALIDATED" in recorded.stdout and "recorded as passed by a run" in recorded.stdout,
              "the tool prints the gate's verdict, which names the run", recorded.stdout)
        verdict = gate_of(ran)
        check(verdict.returncode == 0 and "the next slice may start meanwhile" in verdict.stdout,
              "the project's gate exits 0 and says the next slice may start", verdict.stdout)
        commit(ran, "record the journey")

        # 3: an open decision that blocks nothing, listed until it is decided
        report = doctor(fleet)
        check(len(listed(report, "open_decisions", "ran")) == 1 and not listed(report, "decisions", "ran"),
              "the fleet doctor lists the slice as an open decision, not as one that waits")
        follow_with_next_slice(ran)
        report = doctor(fleet)
        open_items = listed(report, "open_decisions", "ran")
        check(len(open_items) == 1 and open_items[0].get("slice") == "bootstrap-001"
              and not listed(report, "needs_review", "ran", "silent-replacement"),
              "after the next slice follows, the earlier one stays listed and is not a violation", json.dumps(open_items))
        decided = tool("projectstate_decide.py", str(ran), "accept", DELEGATING_WORDS, "--slice", "bootstrap-001", "--delegated")
        summary = (ran / "evidence" / "bootstrap-001" / "summary.md").read_text(encoding="utf-8")
        check(decided.returncode == 0 and "- Decided by: delegate" in summary and f'"{DELEGATING_WORDS}"' in summary,
              "a delegate may accept the earlier slice, and the record says who decided", decided.stdout + decided.stderr)
        check(not listed(doctor(fleet), "open_decisions", "ran"), "the decided slice is no longer listed")
        check(gate_of(ran).returncode == 1, "the project's gate now reports the new slice honestly (journey not run)")

        # 4: typed by hand
        typed = fleet / "typed"
        new_project(typed)
        type_result_by_hand(typed)
        commit(typed, "type the result by hand")
        verdict = gate_of(typed)
        check(verdict.returncode == 0 and "typed by hand" in verdict.stdout and "waits for the answer" in verdict.stdout,
              "the gate names a hand-typed record and says the slice waits", verdict.stdout)
        report = doctor(fleet)
        check(len(listed(report, "decisions", "typed")) == 1 and not listed(report, "open_decisions", "typed"),
              "the fleet doctor lists the hand-typed slice under your decisions")
        before = (typed / "STATE.yaml").read_bytes(), (typed / "evidence" / "bootstrap-001" / "summary.md").read_bytes()
        refused = tool("projectstate_decide.py", str(typed), "accept", DELEGATING_WORDS, "--delegated")
        after = (typed / "STATE.yaml").read_bytes(), (typed / "evidence" / "bootstrap-001" / "summary.md").read_bytes()
        check(refused.returncode == 2 and "a delegate accepts only what a run" in refused.stderr and before == after,
              "a delegate cannot accept the hand-typed slice, and nothing is written", refused.stderr)
        follow_with_next_slice(typed)
        report = doctor(fleet)
        check(len(listed(report, "needs_review", "typed", "silent-replacement")) == 1
              and not listed(report, "open_decisions", "typed"),
              "replacing the hand-typed slice without a decision is reported for review")

        # 5: the update from the previous release
        old_files = old_release_files()
        if old_files is None:
            check(False, f"the update step can read the {OLD_TAG} tag", "fetch the release tags of this repository")
        else:
            old = fleet / "old"
            new_project(old)
            type_result_by_hand(old)
            downgrade(old, *old_files)
            commit(old, f"an instance of {OLD_RELEASE}")
            before_code = gate_of(old).returncode
            needed = tool("projectstate_update.py", "--target", str(old), "--template", str(ROOT), "--check")
            check(needed.returncode == 1, f"the update command sees that the {OLD_RELEASE} instance is behind", needed.stdout)
            applied = tool("projectstate_update.py", "--target", str(old), "--template", str(ROOT), "--apply")
            block, _ = rel.extract_managed_block((old / "AGENTS.md").read_text(encoding="utf-8"))
            check(applied.returncode == 0
                  and (old / rel.GATE_PATH).read_bytes() == (ROOT / rel.GATE_PATH).read_bytes()
                  and (old / rel.VERIFY_PATH).read_bytes() == (ROOT / rel.VERIFY_PATH).read_bytes()
                  and block is not None and block.release == release and rel.VERIFY_PATH.as_posix() in block.content,
                  "the update installs this release's gate, journey tool and contract block", applied.stdout + applied.stderr)
            changed = run(["git", "-C", str(old), "status", "--porcelain"]).stdout.split("\n")
            names = sorted(line[3:] for line in changed if line.strip())
            check(names == ["AGENTS.md", rel.GATE_PATH.as_posix(), rel.VERIFY_PATH.as_posix()],
                  "the update wrote those three files and nothing else", str(names))
            check(gate_of(old).returncode == before_code == 0, "the gate's exit code is unchanged by the update")
            check(tool("projectstate_update.py", "--target", str(old), "--template", str(ROOT), "--check").returncode == 0,
                  "a second check finds the instance up to date")

    print(f"\n{'PASSED' if not failures else 'FAILED'}: {len(failures)} failed check(s)")
    return 1 if failures else 0


def test_the_proof_by_run_journey_passes() -> None:
    """The same journey under pytest; without the previous release's tag (a source archive) it is skipped."""
    if old_release_files() is None:
        import pytest
        pytest.skip(f"tag {OLD_TAG} is not in this checkout")
    assert main() == 0


if __name__ == "__main__":
    raise SystemExit(main())
