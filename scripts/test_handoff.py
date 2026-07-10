#!/usr/bin/env python3
"""Focused regressions for statedd_handoff.py exit semantics."""

from __future__ import annotations

import shlex
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HANDOFF = ROOT / "scripts" / "statedd_handoff.py"


def run_handoff(command: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(HANDOFF),
            "--repo",
            str(ROOT),
            "--no-include-listeners",
            "--test-command",
            command,
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_failed_verification_command_exits_nonzero() -> None:
    command = f"{shlex.quote(sys.executable)} -c \"raise SystemExit(7)\""
    completed = run_handoff(command)
    assert completed.returncode == 1, completed.stdout
    assert "exit: 7" in completed.stdout
    assert "At least one verification command failed." in completed.stdout


def test_successful_verification_command_exits_zero() -> None:
    command = f"{shlex.quote(sys.executable)} -c \"print('ok')\""
    completed = run_handoff(command)
    assert completed.returncode == 0, completed.stdout
    assert "exit: 0" in completed.stdout


def main() -> int:
    tests = [
        test_failed_verification_command_exits_nonzero,
        test_successful_verification_command_exits_zero,
    ]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
