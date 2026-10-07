#!/usr/bin/env python3
"""notes: save short notes and list them.

    notes.py add TEXT   save a note
    notes.py list       print the saved notes, oldest first, as "N. TEXT"

Notes are stored as JSON in $NOTES_HOME/notes.json.
"""

import json
import os
import sys
from pathlib import Path


def store_path() -> Path:
    home = os.environ.get("NOTES_HOME")
    if not home:
        raise SystemExit("notes: NOTES_HOME is not set")
    return Path(home) / "notes.json"


def load() -> list[dict]:
    path = store_path()
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def add(text: str) -> dict:
    notes = load()
    note = {"id": len(notes) + 1, "text": text}
    notes.append(note)
    path = store_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(notes, indent=2), encoding="utf-8")
    return note


def render(notes: list[dict]) -> list[str]:
    return [f"{note['id']}. {note['text']}" for note in notes]


def main(argv: list[str]) -> int:
    if len(argv) >= 2 and argv[0] == "add":
        note = add(" ".join(argv[1:]))
        print(f"saved {note['id']}")
        return 0
    if argv == ["list"]:
        for line in render(load()):
            print(line)
        return 0
    print("usage: notes.py add TEXT | notes.py list", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
