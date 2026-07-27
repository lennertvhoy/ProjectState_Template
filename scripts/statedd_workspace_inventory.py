#!/usr/bin/env python3
"""Backward-compat shim. Canonical module is now 'projectstate_workspace_inventory'.

Kept for one migration cycle so existing invocations, CI configs, and
downstream projects that reference 'scripts/statedd_workspace_inventory.py' continue
to work. New code should import from 'projectstate_workspace_inventory'.
"""
import sys
from pathlib import Path

try:
    from projectstate_workspace_inventory import main  # type: ignore
except ModuleNotFoundError:  # package-style fallback for pytest
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from projectstate_workspace_inventory import main  # type: ignore

if __name__ == "__main__":
    raise SystemExit(main())
