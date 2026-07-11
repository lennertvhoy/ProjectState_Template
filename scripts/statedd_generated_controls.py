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
select profiles and permissions, and review evidence. Coding agents read
`AGENTS.md`, operate the StateDD scripts and skills, maintain repository truth,
and produce the handoff.

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
complete. For a slice, use the executable quality gate:

```bash
python3 scripts/statedd_quality_gate.py --gate-level 2 --verbose
```

User-facing closure also requires runtime identity and browser evidence. End
every session with current state, verification results, risks, absolute evidence
paths, and the next action using `scripts/statedd_handoff.py`. A remote push is
never implied by a context file or a local permit; it requires the explicit
remote-mutation path and operator authorization.
"""
