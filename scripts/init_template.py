#!/usr/bin/env python3
"""Initialize a new repo from the truth-first template."""

from __future__ import annotations

import argparse
import datetime as dt
import shutil
import sys
from pathlib import Path


TEMPLATE_ROOT = Path(__file__).resolve().parents[1]

MANAGED_FILES = {
    "AGENTS.md": """---
repo_mode: bootstrap
initialized_on: {today}
last_updated: {today}
---

# Truth-First Project Operating System

**Purpose:** Stable operating contract for technical projects that use explicit state, evidence, and short active queues.

This repository supports two modes:
- `bootstrap` for discovery and baseline creation
- `operating` for steady-state delivery

## Read Order

Start every session by reading:
1. `AGENTS.md`
2. `STATUS.md`
3. `PROJECT_STATE.yaml`
4. `PROJECT_DNA.yaml`
5. `NEXT_ACTIONS.md`

Read `BACKLOG.md` and `WORKLOG.md` when planning or reviewing history.

## Universal Rules

- no fake completeness
- no unverified claims presented as fact
- user-facing behavior requires direct verification
- screenshots or evidence are required for user-visible changes
- active queue stays short
- history belongs in `WORKLOG.md`, not live state files
- structured state must remain machine-checkable
- end each implementation session with a handoff and hygiene check

## Current Mode

This repo currently operates in: `bootstrap`

## Bootstrap Mode

### Bootstrap Goal
Establish a truthful operating baseline for the project and then switch the repo to operating mode.

### Bootstrap Procedure
1. Investigate the host system and runtime
2. Investigate the repo structure and implementation reality
3. Ask the user only the minimum strategic questions needed
4. Generate initial state and governance files
5. Mark unknowns honestly
6. Create the initial backlog and next-actions queue
7. Update this file to operating mode
8. Record bootstrap completion in `PROJECT_STATE.yaml` and `WORKLOG.md`

### Bootstrap Honesty Rules
If something is not proven, label it as:
- `observed`
- `unknown`
- `reported`
- `assumed`
- `blocked`
- `stale`
- `invalid`

## Operating Mode

### Operating Model
The repo runs in a human-in-the-loop workflow:
- CEO / human provides current state, requirements, priorities, and agent handoffs
- CTO / product-architecture lead reconstructs truth, judges quality, chooses the next best move, and writes the next coding-agent prompt when appropriate
- coding agent implements one coherent step with verification and evidence

## State Files

- `STATUS.md` = short human truth snapshot
- `PROJECT_STATE.yaml` = structured current truth
- `PROJECT_DNA.yaml` = stable architecture contract
- `PROJECT_ADAPTER.yaml` = optional project-specific vocabulary/runtime adapter
- `NEXT_ACTIONS.md` = active queue only
- `BACKLOG.md` = strategic roadmap
- `WORKLOG.md` = append-only history
- `docs/EVIDENCE_LOG.md` = proof ledger

## Hygiene Rules

- `STATUS.md` <= 120 lines
- `PROJECT_STATE.yaml` <= 900 lines
- `NEXT_ACTIONS.md` active-only
- no roadmap prose in structured state
- no closed history in `STATUS.md`
""",
    "STATUS.md": """# Truth-First Workflow Status

**Updated At:** {human_timestamp}
**Execution Mode:** bootstrap
**Project State:** bootstrap_initializing
**Public URL:** not configured

## Snapshot

- Repo initialized in bootstrap mode.
- Project-specific truth still needs to be established.
- Unknowns remain explicit until proven.
- Current work should be tracked through `NEXT_ACTIONS.md`.
- Evidence for user-facing claims belongs in `docs/EVIDENCE_LOG.md`.

## Immediate Priorities

1. Capture the real project truth.
2. Fill in the first active queue.
3. Transition to operating mode once baseline truth exists.

## Active Blockers

- None yet.

## Notes

- Keep `STATUS.md` short.
- Use `PROJECT_STATE.yaml` for structured truth.
""",
    "PROJECT_STATE.yaml": """# PROJECT_STATE.yaml - Structured current truth

metadata:
  updated_at: {stamp}
  updated_by: agent
  version: "truth-first-template-v2"

workflow:
  repo_mode: bootstrap
  bootstrap:
    completed: false
    completed_on: null
    system_investigated: false
    repo_investigated: false
    user_intake_complete: false
    unknowns_remaining:
      - product not yet defined
      - primary user not yet defined
      - target deployment/runtime not yet defined
      - first real milestone not yet defined

verification_labels:
  observed: verified directly in the current session
  unknown: not yet determined from currently available evidence
  reported: supported by prior evidence, not re-verified
  blocked: verification attempted but prevented
  assumed: temporary working assumption
  stale: previously verified but no longer fresh
  invalid: known false or superseded

current_state:
  repository:
    canonical_path: {repo}
    path_status: observed
    branch: null
    head: null
  operating_mode:
    status: observed
    mode: bootstrap
    summary: |
      This repository has been initialized from the truth-first template.
      It remains in bootstrap mode until the real project baseline is established.
  project:
    name: {project_name}
    type: project_template
    lifecycle_stage: bootstrap
    truth_summary: bootstrap_initializing
  runtime:
    status: unconfigured
    services: []
    public_url: null
    notes: |
      Add project-specific runtime details only after a real project is attached.
  evidence:
    status: active
    ledger: docs/EVIDENCE_LOG.md
    standard: browser_verification_or_test_output_for_user_facing_claims
  documentation:
    status: observed
    live_docs:
      - README.md
      - AGENTS.md
      - STATUS.md
      - PROJECT_STATE.yaml
      - PROJECT_DNA.yaml
      - PROJECT_ADAPTER.yaml
      - DESIGN.md
      - NEXT_ACTIONS.md
      - BACKLOG.md
      - WORKLOG.md
      - docs/EVIDENCE_LOG.md

active_problems: []
""",
    "PROJECT_DNA.yaml": """# PROJECT_DNA.yaml - Canonical architecture blueprint

version: "truth-first-template-v2"
schema_version: "1.0"

product:
  name: {project_name}
  one_sentence: "Truth-first project workflow template for technical delivery."
  description: |
    This repository defines a reusable operating system for technical projects:
    stable rules, structured live state, concise status, active queue, roadmap,
    history, and evidence-led verification.

truth_rules:
  contract_files:
    agents: AGENTS.md
    status: STATUS.md
    project_state: PROJECT_STATE.yaml
    project_dna: PROJECT_DNA.yaml
    project_adapter: PROJECT_ADAPTER.yaml
    design_system: DESIGN.md
    next_actions: NEXT_ACTIONS.md
    backlog: BACKLOG.md
    worklog: WORKLOG.md
    evidence_log: docs/EVIDENCE_LOG.md
  repo_modes:
    bootstrap:
      purpose: discover truth and establish baseline state
      exit_condition: baseline completed and mode flipped to operating
    operating:
      purpose: steady-state human-in-the-loop delivery
      exit_condition: none
""",
    "PROJECT_ADAPTER.yaml": """# PROJECT_ADAPTER.yaml - Optional project-specific adapter

version: "truth-first-template-v2"

project:
  name: {project_name}
  short_name: {project_name}
  description: "Optional adapter layer for project-specific vocabulary and runtime details."

vocabulary:
  control_plane_name: "control plane"
  state_plane_name: "state plane"
  evidence_plane_name: "evidence plane"

runtime:
  frontend_port: null
  api_port: null
  public_url: null
  execution_mode: bootstrap

integrations: []

notes:
  - "Populate this file when a real project is attached."
  - "Keep PROJECT_DNA.yaml focused on invariants."
""",
    "NEXT_ACTIONS.md": """# NEXT_ACTIONS - Active Execution Queue

**Updated At:** {human_timestamp}
**Execution Mode:** bootstrap
**Max Items:** 10

## Active Work

No active work yet.

## Queue Rules

- Active items only.
- Keep the queue short.
""",
    "BACKLOG.md": """# BACKLOG - Strategic Roadmap

**Product:** {project_name}
**Execution Mode:** bootstrap
**Updated At:** {today}

## NOW

- Establish baseline truth.

## NEXT

- Transition to operating mode.

## LATER

- Add project-specific roadmap items.
""",
    "WORKLOG.md": """# WORKLOG

**Purpose:** Append-only history for completed work.
""",
    "docs/EVIDENCE_LOG.md": """# EVIDENCE_LOG.md

**Purpose:** Structured ledger of proof artifacts for user-facing claims.
""",
}


def write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def ignore_template_copy(_, names: list[str]) -> set[str]:
    ignored = {".git", ".codex", ".playwright-mcp", "__pycache__", ".cache"}
    return {name for name in names if name in ignored}


def copy_template_tree(template_root: Path, target: Path, *, overwrite: bool) -> None:
    if target != template_root:
        try:
            target.relative_to(template_root)
        except ValueError:
            pass
        else:
            raise SystemExit("Refusing to initialize into a nested path inside the template checkout.")

    if target.exists() and any(target.iterdir()) and target != template_root and not overwrite:
        raise SystemExit(
            "Target exists and is not empty. Re-run with --overwrite or choose an empty directory."
        )

    if target != template_root:
        shutil.copytree(
            template_root,
            target,
            dirs_exist_ok=True,
            ignore=ignore_template_copy,
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize a truth-first template repo")
    parser.add_argument("--name", required=True, help="Project name to stamp into the template")
    parser.add_argument("--target", default=".", help="Repo root to initialize")
    parser.add_argument("--minimal", action="store_true", help="Remove optional fixtures/examples")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing files")
    args = parser.parse_args()

    target = Path(args.target).resolve()
    now = dt.datetime.now(dt.timezone.utc).astimezone()
    today = now.date().isoformat()
    stamp = now.isoformat(timespec="seconds")
    human_timestamp = now.strftime("%Y-%m-%d %H:%M %Z")

    values = {
        "project_name": args.name,
        "repo": str(target),
        "today": today,
        "stamp": stamp,
        "human_timestamp": human_timestamp,
    }

    copy_template_tree(TEMPLATE_ROOT, target, overwrite=args.overwrite)

    for relpath, template in MANAGED_FILES.items():
        write_file(target / relpath, template.format(**values))

    if args.minimal:
        shutil.rmtree(target / "fixtures", ignore_errors=True)
        (target / "docs" / "BOOTSTRAP_QUALITY.md").unlink(missing_ok=True)

    print("Initialized truth-first template repo")
    print(f"Target: {target}")
    print("Mode: bootstrap")
    print("Next:")
    print("1. Read README.md")
    print("2. Review AGENTS.md")
    print("3. Fill in PROJECT_ADAPTER.yaml if needed")
    print(f"4. Run {Path(sys.executable).name} scripts/check_state_docs.py")
    print("5. Switch repo_mode to operating when baseline truth is established")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
