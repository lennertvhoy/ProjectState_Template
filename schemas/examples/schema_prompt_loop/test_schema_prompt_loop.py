#!/usr/bin/env python3
"""Regression tests for the schema/prompt loop example.

Stays stdlib-only and fails if the checked-in prompt fixture drifts from the
schema or if the examples stop behaving as documented.
"""

from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
EXAMPLE_DIR = Path(__file__).resolve().parent
VALIDATOR = ROOT / "scripts" / "statedd_validate_schema.py"
SCHEMA = EXAMPLE_DIR / "feature_slice.schema.json"
VALID = EXAMPLE_DIR / "valid_slice.json"
INVALID = EXAMPLE_DIR / "invalid_slice.json"
GENERATOR = EXAMPLE_DIR / "generate_prompt.py"
FIXTURE = EXAMPLE_DIR / "generated_prompt.md"


def run_validator(path: Path, *, expect_success: bool) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        [sys.executable, str(VALIDATOR), "--file", str(path), "--schema", str(SCHEMA)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if expect_success and completed.returncode != 0:
        raise AssertionError(
            f"Expected {path.name} to pass validation:\n{completed.stdout}\n{completed.stderr}"
        )
    if not expect_success and completed.returncode == 0:
        raise AssertionError(f"Expected {path.name} to fail validation, but it passed")
    return completed


def run_generate_prompt() -> str:
    completed = subprocess.run(
        [sys.executable, str(GENERATOR), "--stdout"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise AssertionError(
            f"generate_prompt.py failed:\n{completed.stdout}\n{completed.stderr}"
        )
    return completed.stdout


def load_schema_required_fields() -> list[str]:
    import json

    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    required = schema.get("required", [])
    properties = schema.get("properties", {})
    return [name for name in required if name in properties]


def assert_stdlib_only(path: Path) -> None:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name not in sys.stdlib_module_names:
                    raise AssertionError(f"{path.name} imports non-stdlib module: {alias.name}")
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module.split(".")[0] not in sys.stdlib_module_names:
                raise AssertionError(f"{path.name} imports from non-stdlib module: {module}")


def test_valid_slice_passes() -> None:
    run_validator(VALID, expect_success=True)


def test_invalid_slice_fails() -> None:
    completed = run_validator(INVALID, expect_success=False)
    output = f"{completed.stdout}\n{completed.stderr}"
    if "missing required property" not in output.lower():
        raise AssertionError("Expected 'missing required property' in failure output")


def test_generated_prompt_includes_required_fields() -> None:
    prompt = run_generate_prompt()
    for field in load_schema_required_fields():
        if field not in prompt:
            raise AssertionError(f"Generated prompt missing required field: {field}")


def test_generated_prompt_fixture_is_up_to_date() -> None:
    if not FIXTURE.exists():
        raise AssertionError(f"Missing prompt fixture: {FIXTURE}")
    current = FIXTURE.read_text(encoding="utf-8")
    generated = run_generate_prompt()
    if current != generated:
        raise AssertionError(
            "generated_prompt.md is out of sync with the schema. "
            "Run: python3 schemas/examples/schema_prompt_loop/generate_prompt.py"
        )


def test_example_scripts_use_stdlib_only() -> None:
    for script in (EXAMPLE_DIR / "validate_example.py", EXAMPLE_DIR / "generate_prompt.py", EXAMPLE_DIR / "test_schema_prompt_loop.py"):
        assert_stdlib_only(script)


def main() -> int:
    tests = [
        test_valid_slice_passes,
        test_invalid_slice_fails,
        test_generated_prompt_includes_required_fields,
        test_generated_prompt_fixture_is_up_to_date,
        test_example_scripts_use_stdlib_only,
    ]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
