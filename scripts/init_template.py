#!/usr/bin/env python3
"""Initialize a new repo from the truth-first template."""

from __future__ import annotations

import argparse
import datetime as dt
import shutil
from pathlib import Path


CORE_FILES = {
    "AGENTS.md": """---
repo_mode: bootstrap
initialized_on: {today}
last_updated: {today}
---

# Truth-First Project Operating System

This repository supports two modes:
- `bootstrap` for discovery and baseline creation
- `operating` for steady-state delivery

## Current Mode

This repo currently operates in: `bootstrap`

## Bootstrap Goal

Establish a truthful operating baseline for the project and then switch the repo to operating mode.
""",
    "STATUS.md": """# Truth-First Workflow Status

**Updated At:** {today} 18:00 CET
**Execution Mode:** bootstrap

## Snapshot

- Repo initialized in bootstrap mode.
- Project-specific truth still needs to be established.
- Unknowns remain explicit until proven.

## Immediate Priorities

1. Capture the real project truth.
2. Fill in the first active queue.
3. Transition to operating mode once baseline truth exists.
""",
    "PROJECT_STATE.yaml": """# PROJECT_STATE.yaml - Structured current truth

metadata:
  updated_at: {stamp}
  updated_by: agent
  version: "truth-first-template-v1"

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

current_state:
  repository:
    canonical_path: {repo}
    path_status: observed
    branch: bootstrap
    head: null
  operating_mode:
    status: observed
    mode: bootstrap
  project:
    name: {project_name}
    type: project_template
    lifecycle_stage: bootstrap
  evidence:
    status: active
    ledger: docs/EVIDENCE_LOG.md

active_problems: []
""",
    "PROJECT_DNA.yaml": """# PROJECT_DNA.yaml - Canonical architecture blueprint

version: "truth-first-template-v1"
schema_version: "1.0"

product:
  name: {project_name}
  one_sentence: "Truth-first project workflow template for technical delivery."

truth_rules:
  repo_modes:
    bootstrap:
      purpose: discover truth and establish baseline state
      exit_condition: baseline completed and mode flipped to operating
    operating:
      purpose: steady-state human-in-the-loop delivery
      exit_condition: none
""",
    "PROJECT_ADAPTER.yaml": """# PROJECT_ADAPTER.yaml - Optional project-specific adapter

version: "truth-first-template-v1"

project:
  name: {project_name}
  short_name: {project_name}

runtime:
  frontend_port: null
  api_port: null
  public_url: null
  execution_mode: bootstrap

integrations: []
""",
    "NEXT_ACTIONS.md": """# NEXT_ACTIONS - Active Execution Queue

**Updated At:** {today} 18:00 CET
**Execution Mode:** bootstrap

## Active Work

No active work yet.

## Queue Rules

- Active items only.
- Keep the queue short.
""",
    "BACKLOG.md": """# BACKLOG - Strategic Roadmap

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
    "docs/BOOTSTRAP_QUALITY.md": """# Bootstrap Quality Rubric

- Did bootstrap separate observed facts from assumptions?
- Did it avoid fantasy architecture?
- Did it preserve unknowns explicitly?
- Did it keep the active queue short?
""",
    "LICENSE": """MIT License

Copyright (c) {year} The Project Authors
""",
}


def write_file(path: Path, content: str, *, overwrite: bool) -> None:
    if path.exists() and not overwrite:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize a truth-first template repo")
    parser.add_argument("--name", required=True, help="Project name to stamp into the template")
    parser.add_argument("--target", default=".", help="Repo root to initialize")
    parser.add_argument("--minimal", action="store_true", help="Remove optional fixtures/examples")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing files")
    args = parser.parse_args()

    target = Path(args.target).resolve()
    today = dt.date.today().isoformat()
    stamp = f"{today}T00:00:00+01:00"

    values = {
        "project_name": args.name,
        "repo": str(target),
        "today": today,
        "year": today[:4],
        "stamp": stamp,
    }

    for relpath, template in CORE_FILES.items():
        write_file(target / relpath, template.format(**values), overwrite=args.overwrite)

    if args.minimal:
        shutil.rmtree(target / "fixtures", ignore_errors=True)
        (target / "docs" / "BOOTSTRAP_QUALITY.md").unlink(missing_ok=True)

    print("Initialized truth-first template repo")
    print(f"Target: {target}")
    print("Mode: bootstrap")
    print("Next:")
    print("1. Review AGENTS.md")
    print("2. Fill in PROJECT_ADAPTER.yaml if needed")
    print("3. Run python scripts/check_state_docs.py")
    print("4. Switch repo_mode to operating when baseline truth is established")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
