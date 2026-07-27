#!/usr/bin/env python3
"""Backward-compat shim. Canonical module is now 'projectstate_doctor'.

Kept for one migration cycle so existing invocations, CI configs, and
downstream projects that reference 'scripts/statedd_doctor.py' continue
to work. New code should import from 'projectstate_doctor'.
"""
import sys
from pathlib import Path

try:
    from projectstate_doctor import main  # type: ignore
except ModuleNotFoundError:  # package-style fallback for pytest
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from projectstate_doctor import main  # type: ignore

if __name__ == "__main__":
    raise SystemExit(main())
