#!/usr/bin/env python3
"""Backward-compat library shim. Canonical module: 'projectstate_contracts'.

Re-exports all public names so existing 'from statedd_contracts import X'
statements keep working for one migration cycle. New code should import
from 'projectstate_contracts' directly.
"""
import sys
from pathlib import Path

try:
    from projectstate_contracts import *  # noqa: F401,F403
except ModuleNotFoundError:  # package-style fallback for pytest
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from projectstate_contracts import *  # noqa: F401,F403
