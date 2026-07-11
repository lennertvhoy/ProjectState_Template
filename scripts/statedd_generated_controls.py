#!/usr/bin/env python3
"""Render generated coding-agent controls from one canonical source.

Downstream startup prompts are derived from this module.  The repository copy
is checked for byte-for-byte equality so prompt drift cannot create a second
coding-agent authority.
"""

from __future__ import annotations


def render_coding_agent_startup_prompt() -> str:
    return """# Coding Agent Startup Prompt

StateDD is an agent-operated repository workflow. Humans provide project intent,
priorities, permissions, feedback, and final acceptance. Coding agents read
`AGENTS.md`, initialize and maintain repository truth, execute slices, validate
results, integrate subagents, commit and push changes, and produce the handoff.

Read `AGENTS.md` first and follow its declared read order. Do not copy a second
read order from this prompt. Load `skills/`, `commands/`, and `docs/` only when
the active task requires them.

Before any repository or StateDD mutation, run the centralized Git safety
preflight for the selected isolation mode. A failed writable preflight means
read-only diagnosis until repair and an explicit restart succeeds:

```bash
python3 scripts/statedd_git_safety_check.py --mode normal_branch
```

Use a full clone for containers or independent agents. Linked worktrees require
explicit trusted-local, same-identity opt-in. Keep local, remote, GitHub, CI,
runtime, and human-accepted truth separate; never call an unverified claim
complete. For parallel work, one integration agent owns the slice branch;
subagents return commits and verification summaries, do not edit global StateDD
files, and do not push the final branch. The integration agent combines commits,
resolves conflicts, updates global truth once, runs the whole-project gate, and
pushes the final branch. For a slice, use the executable quality gate:

```bash
python3 scripts/statedd_quality_gate.py --gate-level 2 --verbose
```

User-facing closure also requires runtime identity and browser evidence. Confirm
the standing `delivery_policy` in `PROJECT_STATE.yaml` once during bootstrap;
after that, do not re-ask for routine commits, slice pushes, or pull requests.
Merge-to-main, force-push, history rewrite, and remote-branch deletion remain
explicit human boundaries. End every session with current state, verification
results, risks, absolute evidence paths, and the next action using
`scripts/statedd_handoff.py`.
"""
