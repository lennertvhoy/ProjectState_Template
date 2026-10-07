#!/usr/bin/env python3
"""Primary journey: run the notes CLI as a subprocess against a fresh NOTES_HOME.

Adds two notes, lists them, and checks their order and content.

    python3 journey.py [--root DIR]    DIR holds notes.py (default: this file's directory)

Exit 0: the journey passed. Exit 1: it failed. Exit 3: it is blocked by a missing input.
"""

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

NOTES = ("write report", "buy milk")


def cli(root: Path, home: str, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(root / "notes.py"), *args],
        capture_output=True,
        text=True,
        env={**os.environ, "NOTES_HOME": home},
        timeout=30,
        check=False,
    )


def last_line(text: str) -> str:
    lines = [line for line in text.strip().splitlines() if line.strip()]
    return lines[-1] if lines else "(no output)"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    root = parser.parse_args().root
    with tempfile.TemporaryDirectory() as home:
        for text in NOTES:
            added = cli(root, home, "add", text)
            if added.returncode != 0:
                print(f"JOURNEY FAILED: add {text!r} exited {added.returncode}: {last_line(added.stderr)}")
                return 1
        listed = cli(root, home, "list")
        if listed.returncode != 0:
            print(f"JOURNEY FAILED: list exited {listed.returncode}: {last_line(listed.stderr)}")
            return 1
        expected = [f"{number}. {text}" for number, text in enumerate(NOTES, start=1)]
        if listed.stdout.splitlines() != expected:
            print(f"JOURNEY FAILED: list printed {listed.stdout.splitlines()!r}, expected {expected!r}")
            return 1
    print("JOURNEY PASSED: two notes added and listed in order")
    return 0


if __name__ == "__main__":
    sys.exit(main())
