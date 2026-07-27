#!/usr/bin/env python3
"""Backward-compat library shim. Canonical module: 'projectstate_git_safety_session'.

Re-exports all public names so existing 'from statedd_git_safety_session import X'
statements keep working for one migration cycle. New code should import
from 'projectstate_git_safety_session' directly.
"""
import sys
from pathlib import Path

try:
    from projectstate_git_safety_session import *  # noqa: F401,F403
except ModuleNotFoundError:  # package-style fallback for pytest
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from projectstate_git_safety_session import *  # noqa: F401,F403
