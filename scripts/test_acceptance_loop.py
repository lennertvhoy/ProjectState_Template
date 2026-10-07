#!/usr/bin/env python3
"""Primary journey for acceptance-loop-001: the owner's inbox becomes recorded decisions.

Copies three real instances that wait for an owner decision (``git archive HEAD``
into a scratch directory; the originals are only read), runs the exact command
the fleet doctor prints for each with accept, waive and reject, then checks that
the gate accepts every record and that the doctor stops listing the copies.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

import projectstate_gate as gate  # noqa: E402

DECISIONS = ("accept", "waive", "reject")
WORDS = "acceptance-loop journey on a scratch copy; not the owner's real decision"


def run(command: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ, GIT_OPTIONAL_LOCKS="0", GIT_TERMINAL_PROMPT="0")
    return subprocess.run(command, cwd=cwd, capture_output=True, text=True, check=False, env=env)


def doctor(root: Path) -> dict[str, Any]:
    done = run([sys.executable, str(SCRIPTS / "projectstate_fleet.py"), "--root", str(root), "--stdout", "--format", "json"])
    if done.returncode != 0:
        raise SystemExit(f"fleet doctor failed on {root}: {done.stderr.strip()}")
    return json.loads(done.stdout)


def awaiting(report: dict[str, Any]) -> list[str]:
    return [item["repository"] for item in report["inbox"]["decisions"]]


def copy_repository(source: Path, target: Path) -> None:
    target.mkdir(parents=True)
    archive = subprocess.run(["git", "-C", str(source), "archive", "HEAD"], capture_output=True, check=False,
                             env=dict(os.environ, GIT_OPTIONAL_LOCKS="0"))
    if archive.returncode != 0:
        raise RuntimeError(f"git archive failed for {source}")
    subprocess.run(["tar", "-x", "-C", str(target)], input=archive.stdout, check=True)
    for args in (["init", "-q"], ["add", "-A"],
                 ["-c", "user.name=journey", "-c", "user.email=journey@localhost", "commit", "-qm", "base"]):
        if run(["git", *args], cwd=target).returncode != 0:
            raise RuntimeError(f"git {' '.join(args)} failed in {target}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--fleet-root", required=True, help="Folder holding the real instances (read only)")
    args = parser.parse_args(argv)
    fleet = Path(args.fleet_root).resolve()
    failures: list[str] = []

    def check(ok: bool, label: str, detail: str = "") -> None:
        print(f"{'PASS' if ok else 'FAIL'}  {label}{f': {detail}' if detail and not ok else ''}")
        if not ok:
            failures.append(label)

    real = doctor(fleet)
    candidates = awaiting(real)
    print(f"INFO  real inbox lists {len(candidates)} decisions: {', '.join(candidates)}")
    scratch = Path(tempfile.mkdtemp(prefix="projectstate-acceptance-"))
    try:
        copies = scratch / "fleet"
        chosen: list[str] = []
        for name in candidates:
            if len(chosen) == len(DECISIONS):
                break
            target = copies / name
            copy_repository(fleet / name, target)
            if name in awaiting(doctor(copies)):  # HEAD may differ from the working tree; keep only real waits
                chosen.append(name)
            else:
                shutil.rmtree(target)
        check(len(chosen) == len(DECISIONS), "three committed instances wait for a decision", f"found {chosen}")
        before = set(awaiting(doctor(copies)))
        for name, decision in zip(chosen, DECISIONS):
            target = copies / name
            message = next(item["message"] for item in doctor(copies)["inbox"]["decisions"] if item["repository"] == name)
            check(f"projectstate_decide.py {target}" in message, f"{name}: the inbox prints the decide command for this copy")
            done = run([sys.executable, str(SCRIPTS / "projectstate_decide.py"), str(target), decision, WORDS])
            check(done.returncode == 0, f"{name}: decide {decision} exits 0", (done.stderr or done.stdout).strip()[-300:])
            errors, _blockers, _warnings = gate.validate(target)
            check(not errors, f"{name}: the gate accepts the recorded {decision} decision", "; ".join(errors)[:300])
            summary = (target / "evidence" / gate.parse_state((target / "STATE.yaml").read_text())["current_slice"]["id"]
                       / "summary.md").read_text(encoding="utf-8")
            check("## Owner decision" in summary and WORDS in summary, f"{name}: the summary quotes the decision")
            again = run([sys.executable, str(SCRIPTS / "projectstate_decide.py"), str(target), decision, WORDS])
            check(again.returncode == 2, f"{name}: a second decision is refused", again.stdout.strip()[-200:])
        after = set(awaiting(doctor(copies)))
        check(before >= set(chosen) and not (after & set(chosen)), "the doctor stops listing the decided copies",
              f"before {sorted(before)}, after {sorted(after)}")
        print(f"INFO  decided copies: {', '.join(f'{n}={d}' for n, d in zip(chosen, DECISIONS))}")
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    print(f"RESULT: {'PASSED' if not failures else 'FAILED'}: {len(failures)} failed")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
