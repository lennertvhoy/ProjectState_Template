#!/usr/bin/env python3
"""Generate a deterministic prompt/checklist from feature_slice.schema.json.

The output is derived directly from the schema so that docs, prompts, and
examples cannot drift from the canonical contract without a test failure.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


SCHEMA = Path(__file__).resolve().parent / "feature_slice.schema.json"
DEFAULT_OUTPUT = Path(__file__).resolve().parent / "generated_prompt.md"


def load_schema(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def required_fields(schema: dict) -> list[tuple[str, dict]]:
    required = schema.get("required", [])
    properties = schema.get("properties", {})
    # Preserve schema property order; required fields first.
    items: list[tuple[str, dict]] = []
    for name in required:
        if name in properties:
            items.append((name, properties[name]))
    return items


def optional_fields(schema: dict) -> list[tuple[str, dict]]:
    required = set(schema.get("required", []))
    properties = schema.get("properties", {})
    return [(name, prop) for name, prop in properties.items() if name not in required]


def field_description(prop: dict) -> str:
    return prop.get("description", "No description provided.")


def generate_prompt(schema: dict) -> str:
    title = schema.get("title", "Feature slice contract")
    description = schema.get("description", "")

    lines: list[str] = []
    lines.append(f"# {title}")
    lines.append("")
    if description:
        lines.append(description)
        lines.append("")
    lines.append(
        "This prompt is generated from `feature_slice.schema.json`. "
        "Regenerate it with `python3 schemas/examples/schema_prompt_loop/generate_prompt.py`."
    )
    lines.append("")

    lines.append("## Required fields")
    lines.append("")
    for name, prop in required_fields(schema):
        lines.append(f"- **{name}**: {field_description(prop)}")
    lines.append("")

    lines.append("## Optional fields")
    lines.append("")
    for name, prop in optional_fields(schema):
        lines.append(f"- **{name}**: {field_description(prop)}")
    lines.append("")

    lines.append("## Acceptance checklist")
    lines.append("")
    lines.append("Before accepting a feature slice, confirm:")
    lines.append("")
    for name, _ in required_fields(schema):
        lines.append(f"- [ ] `{name}` is present and valid.")
    lines.append("")

    return "\n".join(lines) + "\n"


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a prompt from feature_slice.schema.json")
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT),
        help=f"Output file (default: {DEFAULT_OUTPUT.name})",
    )
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="Print to stdout instead of writing a file",
    )
    return parser.parse_args(argv[1:])


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv)
    schema = load_schema(SCHEMA)
    prompt = generate_prompt(schema)

    if args.stdout:
        print(prompt, end="")
        return 0

    output = Path(args.output)
    output.write_text(prompt, encoding="utf-8")
    print(f"Wrote generated prompt to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
