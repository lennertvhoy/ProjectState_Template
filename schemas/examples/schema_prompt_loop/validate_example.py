#!/usr/bin/env python3
"""Validate the feature slice example files against the local schema.

This script stays stdlib-only and reuses scripts/statedd_validate_schema.py.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
VALIDATOR = ROOT / "scripts" / "statedd_validate_schema.py"
SCHEMA = Path(__file__).resolve().parent / "feature_slice.schema.json"
VALID = Path(__file__).resolve().parent / "valid_slice.json"
INVALID = Path(__file__).resolve().parent / "invalid_slice.json"


def validate(path: Path, *, expect_success: bool) -> None:
    completed = subprocess.run(
        [sys.executable, str(VALIDATOR), "--file", str(path), "--schema", str(SCHEMA)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    label = "PASS" if completed.returncode == 0 else "FAIL"
    print(f"{label}: {path.name}")
    if completed.returncode == 0 and not expect_success:
        print(f"  Expected failure but validation passed for {path.name}")
        sys.exit(1)
    if completed.returncode != 0 and expect_success:
        print(f"  Expected success but validation failed for {path.name}")
        print(completed.stdout)
        print(completed.stderr)
        sys.exit(1)
    if not expect_success:
        # Surface the useful error so the example is instructive.
        output = f"{completed.stdout}\n{completed.stderr}".strip()
        if "missing required property" not in output.lower():
            print("  Warning: expected 'missing required property' in failure output")
        reason = "unknown"
        for line in output.splitlines():
            if line.strip().startswith("-"):
                reason = line.strip()
                break
        print(f"  Reason: {reason}")


def main() -> int:
    if not VALIDATOR.exists():
        print(f"Missing validator: {VALIDATOR}")
        return 1
    if not SCHEMA.exists():
        print(f"Missing schema: {SCHEMA}")
        return 1

    print("Validating feature slice example files...")
    validate(VALID, expect_success=True)
    validate(INVALID, expect_success=False)
    print("Example validation complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
