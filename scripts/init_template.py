#!/usr/bin/env python3
"""Initialize a new repo from the State-Driven Development Template."""

from __future__ import annotations

import argparse
import datetime as dt
import shutil
import sys
from pathlib import Path


TEMPLATE_ROOT = Path(__file__).resolve().parents[1]
IGNORED_TEMPLATE_NAMES = {".git", ".codex", ".playwright-mcp", "__pycache__", ".cache"}

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
- `README.md` is the primary user guide for this published template

## Current Mode

This repo currently operates in: `bootstrap`

## Bootstrap Mode

### When Bootstrap Mode Applies
Use bootstrap mode when:
- the repo is new
- state files do not yet exist
- project truth is unclear
- the user explicitly asks for initialization or re-baselining

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

### Required System Investigation
Inspect and record, when relevant:
- OS, distro, kernel
- shell and terminal environment
- package manager(s)
- language/runtime versions
- container/runtime tooling
- browser/debug tooling
- active ports and services
- git branch, head, and worktree state

### Required Repo Investigation
Inspect and record:
- top-level structure
- app/service boundaries
- main manifests and config files
- likely entrypoints
- test setup
- deployment assumptions
- contradictions between code and docs

### Bootstrap Output Files
Create or initialize:
- `AGENTS.md`
- `STATUS.md`
- `PROJECT_STATE.yaml`
- `PROJECT_DNA.yaml`
- `PROJECT_ADAPTER.yaml`
- `NEXT_ACTIONS.md`
- `BACKLOG.md`
- `WORKLOG.md`
- `docs/EVIDENCE_LOG.md`

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
- CTO / product-architecture lead reconstructs truth from user-relayed handoffs and pasted context, judges quality, chooses the next best move, and writes the next coding-agent prompt when appropriate
- coding agent implements one coherent step with verification and evidence, then ends with a final handoff for the CTO lane

The CTO role can be handled by ChatGPT, Claude, Gemini, or another separate AI chat.
Use `prompts/CTO_SESSION_PROMPT.md` as the startup prompt for that chat.
Assume the CTO lane does not have direct repo access unless the human pastes
state, screenshots, or other context into that chat.

Use the CTO lane for all non-trivial work. Non-trivial means any task involving
multiple files, architecture changes, user-facing behavior, integrations,
migrations, state-structure changes, or work likely to take more than one prompt.
Each non-trivial loop should normally start a fresh coding-agent session.

### CTO Review Standard
Every handoff must be reviewed for:
- contradictions
- overclaims
- missing proof
- brittle logic
- wrong sequencing
- architectural drift
- weak product prioritization

### Coding-Agent Standard
Implementation prompts must:
- require reading `AGENTS.md` first
- anchor on current verified truth
- define one coherent scope
- forbid overclaiming
- require direct verification
- require state and doc updates when truth changes
- require screenshots/evidence for user-facing work
- require the coding agent to ask the user to provide a CTO agent if no CTO lane or CTO handoff exists yet for non-trivial work
- require the coding agent to end with one final handoff message suitable for pasting into the CTO lane

A valid CTO handoff should define the verified current state, one coherent scope,
required verification, and the exit condition for the implementation step. If
important context is not preserved in repo state files, the CTO prompt must
restate it explicitly for the next coding-agent session.

## State Files

- `STATUS.md` = short human truth snapshot
- `PROJECT_STATE.yaml` = structured current truth
- `PROJECT_DNA.yaml` = stable architecture contract
- `PROJECT_ADAPTER.yaml` = optional project-specific vocabulary/runtime adapter
- `NEXT_ACTIONS.md` = active queue only
- `BACKLOG.md` = strategic roadmap
- `WORKLOG.md` = append-only history
- `docs/EVIDENCE_LOG.md` = proof ledger

## Handoff Requirements

Every implementation session ends with:
- what changed
- what was directly verified
- what remains partial or risky
- git head
- clean worktree status
- evidence references
- next recommended action
- handoff wording suitable for direct paste into the CTO chat

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
  version: "state-driven-development-template-v2"

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
      This repository has been initialized from the State-Driven Development Template.
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
    primary_user_guide: README.md
    live_docs:
      - README.md
      - AGENTS.md
      - STATUS.md
      - PROJECT_STATE.yaml
      - PROJECT_DNA.yaml
      - PROJECT_ADAPTER.yaml
      - NEXT_ACTIONS.md
      - BACKLOG.md
      - WORKLOG.md
      - docs/EVIDENCE_LOG.md

active_problems: []
""",
    "PROJECT_DNA.yaml": """# PROJECT_DNA.yaml - Canonical architecture blueprint

version: "state-driven-development-template-v2"
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
    next_actions: NEXT_ACTIONS.md
    backlog: BACKLOG.md
    worklog: WORKLOG.md
    evidence_log: docs/EVIDENCE_LOG.md
  hard_rules:
    - no_fake_completeness
    - no_history_in_live_state
    - evidence_required_for_user_facing_claims
    - clean_worktree_required_at_handoff
    - active_queue_remains_short
  claim_states:
    observed: verified directly now
    unknown: not yet determined from available evidence
    reported: supported by prior evidence
    blocked: verification currently prevented
    assumed: provisional working assumption
    stale: previously verified but aged out
    invalid: known false or superseded
  repo_modes:
    bootstrap:
      purpose: discover truth and establish baseline state
      exit_condition: baseline completed and mode flipped to operating
    operating:
      purpose: steady-state human-in-the-loop delivery
      exit_condition: none

architecture:
  control_plane:
    description: Human and agent workflow coordination.
  state_plane:
    description: Structured current truth in PROJECT_STATE.yaml.
  evidence_plane:
    description: Artifact-backed proof for claims and verification.
  history_plane:
    description: Append-only record of completed work in WORKLOG.md.

invariants:
  - "STATUS.md stays short and current."
  - "PROJECT_STATE.yaml stores structured live truth only."
  - "PROJECT_DNA.yaml changes slowly."
  - "NEXT_ACTIONS.md contains open work only."
  - "WORKLOG.md is append-only."

governance:
  evidence_standard: browser_verification_or_test_output
  hygiene_check: scripts/check_state_docs.py
  update_policy:
    status: when_current_truth_changes
    project_state: when_structured_truth_changes
    worklog: when_work_is_completed
    evidence_log: when_user_facing_claims_are_verified
""",
    "PROJECT_ADAPTER.yaml": """# PROJECT_ADAPTER.yaml - Optional project-specific adapter

version: "state-driven-development-template-v2"

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
    return {name for name in names if name in IGNORED_TEMPLATE_NAMES}


def should_ignore_path(path: Path) -> bool:
    return any(part in IGNORED_TEMPLATE_NAMES for part in path.parts)


def find_conflicting_template_paths(template_root: Path, target: Path) -> list[Path]:
    conflicts: list[Path] = []
    for source_path in template_root.rglob("*"):
        if source_path.is_dir():
            continue
        relpath = source_path.relative_to(template_root)
        if should_ignore_path(relpath):
            continue
        if (target / relpath).exists():
            conflicts.append(relpath)
    return sorted(conflicts)


def copy_template_tree(
    template_root: Path,
    target: Path,
    *,
    overwrite: bool,
    force_overwrite: bool,
) -> None:
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

    if target.exists() and any(target.iterdir()) and target != template_root and overwrite and not force_overwrite:
        conflicts = find_conflicting_template_paths(template_root, target)
        if conflicts:
            preview = ", ".join(str(path) for path in conflicts[:8])
            if len(conflicts) > 8:
                preview += ", ..."
            raise SystemExit(
                "Target contains files that would be overwritten by the template: "
                f"{preview}. Review/back up those files first, then re-run with "
                "--force-overwrite only if replacing them is intentional."
            )

    if target != template_root:
        shutil.copytree(
            template_root,
            target,
            dirs_exist_ok=True,
            ignore=ignore_template_copy,
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize a State-Driven Development Template repo")
    parser.add_argument("--name", required=True, help="Project name to stamp into the template")
    parser.add_argument("--target", default=".", help="Repo root to initialize")
    parser.add_argument("--minimal", action="store_true", help="Remove optional fixtures/examples")
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow initialization into an existing non-empty target when no template-path collisions are present",
    )
    parser.add_argument(
        "--force-overwrite",
        action="store_true",
        help="Allow template files to replace conflicting files in an existing non-empty target",
    )
    args = parser.parse_args()

    if args.force_overwrite and not args.overwrite:
        raise SystemExit("--force-overwrite requires --overwrite.")

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

    copy_template_tree(
        TEMPLATE_ROOT,
        target,
        overwrite=args.overwrite,
        force_overwrite=args.force_overwrite,
    )

    for relpath, template in MANAGED_FILES.items():
        write_file(target / relpath, template.format(**values))

    if args.minimal:
        shutil.rmtree(target / "fixtures", ignore_errors=True)
        (target / "docs" / "BOOTSTRAP_QUALITY.md").unlink(missing_ok=True)

    print("Initialized State-Driven Development Template repo")
    print(f"Target: {target}")
    print("Mode: bootstrap")
    if (target / ".git").exists():
        print("Warning: target contains git metadata. Verify git remote -v before first push.")
    print("Important: if this repo came from a direct clone/copy, remove .git and create your own remote before pushing.")
    print("Next:")
    print("1. Read README.md")
    print("2. Fix git ownership first if needed: remove .git, init your own repo, and verify git remote -v")
    print("3. Start the coding agent with the startup prompt from README.md")
    print("4. Let the coding agent read the repo files, detect bootstrap mode, and ask the minimum strategic questions")
    print("5. Then create a CTO chat and paste prompts/CTO_SESSION_PROMPT.md")
    print(f"6. Run {Path(sys.executable).name} scripts/check_state_docs.py after bootstrap updates")
    print("7. Switch repo_mode to operating when baseline truth is established")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
