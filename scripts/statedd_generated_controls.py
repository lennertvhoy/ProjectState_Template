#!/usr/bin/env python3
"""Deterministic generated controls shared by initialization and upgrades."""

from __future__ import annotations


def render_coding_agent_startup_prompt() -> str:
    return """# Coding Agent Start

Read `AGENTS.md` and its declared read order. Treat `PROJECT_STATE.yaml` as
canonical current truth, keep `NEXT_ACTIONS.md` open-only, and load backlog,
history, inventory, or evidence only when the task needs them.

In bootstrap, investigate before implementing and keep unknowns explicit. For
implementation, take one coherent slice, verify the relevant truth boundary,
update live state, and end with a precise handoff.
"""


def render_downstream_workflow(required_gate_level: int) -> str:
    return f"""name: StateDD

on:
  push:
  pull_request:

permissions:
  contents: read

jobs:
  validate:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5
      - uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065
        with:
          python-version: "3.13"
      - run: python3 scripts/statedd_quality_gate.py --gate-level {required_gate_level} --conformance
"""
