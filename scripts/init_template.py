#!/usr/bin/env python3
"""Initialize or adopt the StateDD template workflow."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


TEMPLATE_ROOT = Path(__file__).resolve().parents[1]
IGNORED_TEMPLATE_NAMES = {".git", ".codex", ".playwright-mcp", "__pycache__", ".cache"}

TEMPLATE_NAME = "State Driven Development Template"
CONTRACT_TITLE = "State Driven Development Template Contract"
TEMPLATE_VERSION = "statedd-template-v4"

TEMPLATE_COPY_ROOT_FILES = {
    Path(".gitignore"),
    Path("AGENTS.md"),
    Path("BACKLOG.md"),
    Path("CHANGELOG.md"),
    Path("LICENSE"),
    Path("LICENSE_FAQ.md"),
    Path("NEXT_ACTIONS.md"),
    Path("PROJECT_ADAPTER.yaml"),
    Path("PROJECT_DNA.yaml"),
    Path("PROJECT_STATE.yaml"),
    Path("README.md"),
    Path("STATUS.md"),
    Path("VERSION"),
    Path("WORKLOG.md"),
}

TEMPLATE_COPY_DIR_NAMES = {".github", "docs", "fixtures", "prompts", "schemas", "scripts"}

SUPPORT_ASSET_PATHS = [
    Path("VERSION"),
    Path("scripts/init_template.py"),
    Path("scripts/check_state_docs.py"),
    Path("scripts/statedd_version_check.py"),
    Path("scripts/statedd_handoff.py"),
    Path("scripts/statedd_audit.py"),
    Path("scripts/statedd_doctor.py"),
    Path("scripts/statedd_runtime_proof.py"),
    Path("scripts/statedd_validate_schema.py"),
    Path("scripts/statedd_evidence_pack.py"),
    Path("scripts/test_init_template.py"),
    Path("scripts/test_runtime_proof.py"),
    Path("scripts/test_schema_validation.py"),
    Path("scripts/test_evidence_pack.py"),
    Path("schemas/project_state.schema.json"),
    Path("schemas/project_dna.schema.json"),
    Path("schemas/project_adapter.schema.json"),
    Path("schemas/runtime_identity.schema.json"),
    Path("schemas/evidence_readme_contract.json"),
    Path("schemas/evidence_manifest.schema.json"),
    Path("schemas/final_handoff_contract.json"),
    Path("schemas/examples/runtime_identity_not_required.json"),
    Path("schemas/tests/README.md"),
    Path("prompts/CTO_SESSION_PROMPT.md"),
    Path("prompts/CODING_AGENT_STARTUP_PROMPT.md"),
    Path("prompts/OPENCODE_STARTUP_PROMPT.md"),
    Path("prompts/BOOTSTRAP_INTAKE_PROMPT.md"),
    Path("prompts/TOOL_MODEL_ROUTING_GUIDE.md"),
    Path("prompts/FINAL_HANDOFF_TEMPLATE.md"),
    Path("prompts/RUNTIME_IDENTITY_CHECKLIST.md"),
    Path("prompts/ACCEPTANCE_FREEZE_TEMPLATE.md"),
    Path("prompts/SLICE_CONTRACT_TEMPLATE.md"),
    Path("prompts/EVIDENCE_README_TEMPLATE.md"),
    Path("prompts/SCHEMA_OWNERSHIP_TEMPLATE.md"),
    Path("prompts/SUBAGENT_REVIEW_TEMPLATE.md"),
    Path("prompts/CTO_REVIEW_CHECKLIST.md"),
    Path("docs/GETTING_STARTED_5_MIN.md"),
    Path("docs/BOOTSTRAP_QUALITY.md"),
    Path("docs/UPGRADING.md"),
    Path("docs/WORKFLOW_FOR_BEGINNERS.md"),
    Path("docs/adr/README.md"),
    Path("docs/adr/0000-adr-template.md"),
]

GITHUB_ASSET_PATHS = [
    Path(".github/workflows/validate.yml"),
    Path(".github/pull_request_template.md"),
    Path(".github/ISSUE_TEMPLATE/config.yml"),
    Path(".github/ISSUE_TEMPLATE/bootstrap-init.md"),
    Path(".github/ISSUE_TEMPLATE/bug-regression.md"),
    Path(".github/ISSUE_TEMPLATE/backlog-item.md"),
    Path(".github/ISSUE_TEMPLATE/architecture-change.md"),
]


@dataclass
class RepoScan:
    canonical_path: str
    branch: str | None
    head: str | None
    top_level_entries: list[str]
    manifests: list[str]
    entrypoints: list[str]
    test_setup: list[str]
    deployment_assumptions: list[str]
    contradictions: list[str]
    project_summary: str
    project_type: str


def render_agents_template(today: str, mode: str) -> str:
    return f"""---
repo_role: downstream_project
statedd_mode: {mode}
repo_mode: {mode}
statedd_version: "{TEMPLATE_VERSION}"
initialized_on: {today}
last_updated: {today}
---

# {CONTRACT_TITLE}

**Purpose:** Stable operating contract for technical projects that use explicit state, evidence, and short active queues.

This repository supports two modes:
- `bootstrap` for discovery and baseline creation
- `operating` for steady-state delivery

## Read Order

Coding agents should start every repo session by reading:
1. `AGENTS.md`
2. `STATUS.md`
3. `PROJECT_STATE.yaml`
4. `PROJECT_DNA.yaml`
5. `NEXT_ACTIONS.md`

Read `BACKLOG.md` and `WORKLOG.md` when planning or reviewing history.

## Universal Rules

These rules apply in all modes:
- no fake completeness
- no unverified claims presented as fact
- user-facing behavior requires direct verification
- user-facing acceptance requires runtime identity proof, not screenshots alone
- negative searches stay negative: use `not found`, `not currently locatable`, or `not proven`
- screenshots or evidence are required for user-visible changes
- active queue stays short
- history belongs in `WORKLOG.md`, not live state files
- structured state must remain machine-checkable
- end each implementation session with a handoff and hygiene check
- `README.md` is the primary user guide for the project

## Current Mode

This repo currently operates in: `{mode}`

## Bootstrap Mode

### When Bootstrap Mode Applies
Use bootstrap mode when:
- the repo is new
- state files do not yet exist
- project truth is unclear
- the user explicitly asks for initialization or re-baselining

### Bootstrap Goal
Establish a truthful operating baseline for the project, including filled state
files and a real backlog, and only then switch the repo to operating mode.

### Bootstrap Procedure
1. Investigate the host system and runtime
2. Investigate the repo structure and implementation reality
3. Ask the user only the minimum strategic questions needed
4. Use the CTO lane for brainstorming, research, contradiction resolution, architecture framing, and backlog shaping
5. Generate and fill the state and governance files truthfully
6. Mark unknowns honestly
7. Create the initial backlog and next-actions queue
8. Update this file to operating mode only when bootstrap is complete
9. Record bootstrap completion in `PROJECT_STATE.yaml` and `WORKLOG.md`

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
- `docs/ACCEPTANCE_FREEZES.md`

Bootstrap is not complete until these files are filled out enough to guide real
implementation and `BACKLOG.md` is more than a placeholder.

### Bootstrap Honesty Rules
If something is not proven, label it as:
- `observed`
- `unknown`
- `reported`
- `assumed`
- `blocked`
- `stale`
- `invalid`

Do not invent architecture or maturity.

## Operating Mode

### Operating Model
The repo now runs in a human-in-the-loop workflow:
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
During initial bootstrap, an initial coding-agent session may come first so it
can read the repo contract, detect `bootstrap` mode, and ask the minimum
strategic questions needed before the CTO loop fully takes over.
Bootstrap should remain a joint CTO + coding-agent phase until the repo truth,
architecture, backlog, and active queue are ready for implementation mode.

A valid CTO handoff should define the verified current state, one coherent scope,
required verification, and the exit condition for the implementation step. If
important context is not preserved in repo state files, the CTO prompt must
restate it explicitly for the next coding-agent session.
In operating mode, the scope should usually be a backlog slice or a very small
set of tightly related backlog items.

When tool or model choice affects quality, cost, speed, context fit, or
verification risk, the CTO lane should recommend a concrete route using
`prompts/TOOL_MODEL_ROUTING_GUIDE.md`. The recommendation should be based on
the user's available tools and the current slice, not a hard-coded vendor
preference. Specific model capability, pricing, context-window, and
availability claims must be verified from current primary sources or marked as
`reported`, `assumed`, or `not proven`.

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
- include the recommended tool/model/settings when the CTO lane selected a route
- forbid overclaiming
- require direct verification
- require runtime identity proof before accepting or investigating user-facing behavior
- require state and doc updates when truth changes
- require screenshots/evidence for user-facing work
- require the coding agent to ask the user to provide a CTO agent if no CTO lane or CTO handoff exists yet for non-trivial work
- require the coding agent to end with one final handoff message suitable for pasting into the CTO lane
- require the coding agent, when starting in unclear bootstrap mode, to ask the minimum strategic questions needed before implementation

If the tool supports subagents or parallel workers and the task clearly benefits,
the CTO lane may encourage using them. This is optional guidance, not a baseline
workflow requirement.

## State Files

- `STATUS.md` = short human truth snapshot
- `PROJECT_STATE.yaml` = structured current truth
- `PROJECT_DNA.yaml` = stable architecture contract
- `PROJECT_ADAPTER.yaml` = optional project-specific vocabulary/runtime adapter
- `NEXT_ACTIONS.md` = active queue only
- `BACKLOG.md` = strategic roadmap with stable backlog IDs
- `WORKLOG.md` = append-only history
- `docs/EVIDENCE_LOG.md` = proof ledger
- `docs/ACCEPTANCE_FREEZES.md` = accepted user-facing milestone ledger

## Handoff Requirements

Every implementation session ends with:
- what changed
- what was directly verified
- repo path
- branch
- what remains partial or risky
- git head
- process or container serving the verified artifact
- port or endpoint used for verification
- whether the running artifact was rebuilt in this slice
- clean worktree status
- evidence references
- absolute file paths for evidence artifacts when available
- next recommended action
- handoff wording suitable for direct paste into the CTO chat

Use `prompts/FINAL_HANDOFF_TEMPLATE.md` when you need a canonical handoff shape.
Use `prompts/RUNTIME_IDENTITY_CHECKLIST.md` before UI acceptance or regression forensics.
Use `prompts/ACCEPTANCE_FREEZE_TEMPLATE.md` after accepting a user-facing milestone.

## Hygiene Rules

- `STATUS.md` <= 120 lines
- `PROJECT_STATE.yaml` <= 900 lines
- `NEXT_ACTIONS.md` active-only
- no roadmap prose in structured state
- no closed history in `STATUS.md`
"""


def render_status(project_name: str, human_timestamp: str, *, summary_lines: list[str], priorities: list[str]) -> str:
    snapshot = "\n".join(f"- {line}" for line in summary_lines)
    priority_block = "\n".join(f"{index}. {line}" for index, line in enumerate(priorities, start=1))
    return f"""# {project_name} Status

**Updated At:** {human_timestamp}
**Execution Mode:** bootstrap
**Project State:** bootstrap_initializing
**Public URL:** not configured

## Snapshot

{snapshot}

## Immediate Priorities

{priority_block}

## Active Blockers

- None yet.

## Notes

- Keep `STATUS.md` short.
- Use `PROJECT_STATE.yaml` for structured truth.
- Use `BACKLOG.md` backlog IDs inside `NEXT_ACTIONS.md` when active items are added.
- Prove runtime identity before accepting user-facing behavior.
"""


def render_project_state(
    project_name: str,
    stamp: str,
    repo_scan: RepoScan,
    *,
    system_investigated: bool,
    repo_investigated: bool,
    unknowns: list[str],
) -> str:
    branch = repo_scan.branch if repo_scan.branch is not None else "null"
    head = repo_scan.head if repo_scan.head is not None else "null"
    top_level_entries = "\n".join(f"      - {entry}" for entry in repo_scan.top_level_entries) or "      []"
    entrypoints = "\n".join(f"      - {entry}" for entry in repo_scan.entrypoints) or "      []"
    manifests = "\n".join(f"      - {entry}" for entry in repo_scan.manifests) or "      []"
    test_setup = "\n".join(f"      - {entry}" for entry in repo_scan.test_setup) or "      []"
    deployment = "\n".join(f"      - {entry}" for entry in repo_scan.deployment_assumptions) or "      []"
    contradictions = "\n".join(f"      - {entry}" for entry in repo_scan.contradictions) or "      []"
    unknowns_block = "\n".join(f"      - {entry}" for entry in unknowns) or "      []"

    python_version = platform.python_version()
    os_label = f"{platform.system()} {platform.release()}"
    shell_name = os.environ.get("SHELL", sys.executable)
    terminal = os.environ.get("TERM", "unknown")
    podman_present = "present" if shutil.which("podman") else "absent"
    docker_present = "present" if shutil.which("docker") else "absent"
    chrome_present = "present" if any(
        shutil.which(binary) for binary in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser")
    ) else "absent"

    return f"""# PROJECT_STATE.yaml - Structured current truth

metadata:
  updated_at: {stamp}
  updated_by: agent
  version: "{TEMPLATE_VERSION}"

workflow:
  repo_role: downstream_project
  statedd_mode: bootstrap
  repo_mode: bootstrap
  bootstrap:
    completed: false
    completed_on: null
    system_investigated: {"true" if system_investigated else "false"}
    repo_investigated: {"true" if repo_investigated else "false"}
    user_intake_complete: false
    unknowns_remaining:
{unknowns_block}

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
    canonical_path: {repo_scan.canonical_path}
    path_status: observed
    branch: {branch}
    head: {head}

  operating_mode:
    status: observed
    mode: bootstrap
    summary: |
      This repository is currently in bootstrap mode. It should not flip to
      operating mode until the baseline state, backlog, queue, and evidence are
      truthfully established.

  project:
    name: {project_name}
    type: {repo_scan.project_type}
    lifecycle_stage: bootstrap
    truth_summary: {repo_scan.project_summary}

  runtime_identity:
    status: unknown
    repo_path: {repo_scan.canonical_path}
    branch: {branch}
    head: {head}
    process_or_container: unknown
    port_or_base_url: unknown
    rebuilt_in_current_slice: unknown
    duplicate_runtimes_checked: false
    notes: |
      Fill this section before accepting user-facing behavior or investigating
      a visual/runtime regression.

  environment:
    status: observed
    host:
      os: {os_label}
      kernel: {platform.version()}
      shell: {shell_name}
      terminal: {terminal}
    package_managers:
      - unknown
    language_runtimes:
      python: {python_version}
    container_tooling:
      podman: {podman_present}
      docker: {docker_present}
    browser_tooling:
      chrome: {chrome_present}
    ports:
      listeners: unknown
      notes: |
        Capture active listeners directly during bootstrap when that matters.

  repository_structure:
    status: observed
    top_level_entries:
{top_level_entries}
    manifests:
{manifests}
    entrypoints:
{entrypoints}
    test_setup:
{test_setup}
    deployment_assumptions:
{deployment}
    contradictions:
{contradictions}

  evidence:
    status: active
    ledger: docs/EVIDENCE_LOG.md
    acceptance_freezes: docs/ACCEPTANCE_FREEZES.md
    artifact_root: docs/evidence
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
      - LICENSE
      - LICENSE_FAQ.md
      - docs/GETTING_STARTED_5_MIN.md
      - docs/EVIDENCE_LOG.md
      - docs/ACCEPTANCE_FREEZES.md
      - prompts/OPENCODE_STARTUP_PROMPT.md
      - prompts/TOOL_MODEL_ROUTING_GUIDE.md
      - scripts/statedd_handoff.py
      - scripts/statedd_runtime_proof.py
    prompt_assets:
      cto_session_prompt: prompts/CTO_SESSION_PROMPT.md
      coding_agent_startup_prompt: prompts/CODING_AGENT_STARTUP_PROMPT.md
      opencode_startup_prompt: prompts/OPENCODE_STARTUP_PROMPT.md
      tool_model_routing_guide:
        status: observed
        path: prompts/TOOL_MODEL_ROUTING_GUIDE.md
        summary: |
          Guides the CTO lane to recommend tools, models, settings, context
          strategy, and tailored prompts based on current user access, task
          risk, budget, and verified provider facts.
    workflow_helpers:
      getting_started_5_min:
        status: observed
        path: docs/GETTING_STARTED_5_MIN.md
      handoff_snapshot:
        status: observed
        path: scripts/statedd_handoff.py
      runtime_proof:
        status: observed
        path: scripts/statedd_runtime_proof.py
        summary: Captures runtime_identity.json proof artifacts for evidence folders.

active_problems: []
"""


def render_project_dna(project_name: str) -> str:
    return f"""# PROJECT_DNA.yaml - Canonical architecture blueprint

version: "{TEMPLATE_VERSION}"
schema_version: "1.0"

product:
  name: "{project_name}"
  one_sentence: "Project using the {TEMPLATE_NAME} workflow."
  description: |
    This repository defines a reusable operating system for technical projects:
    stable rules, structured live state, concise status, active queue, roadmap,
    history, and evidence-led verification.
  is:
    - truth_first
    - evidence_backed
    - machine_checkable
    - history_separated_from_state
    - active_queue_is_short
  is_not:
    - product_specific
    - runtime_status_dump
    - append_only_status_file

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
    acceptance_freezes: docs/ACCEPTANCE_FREEZES.md

  hard_rules:
    - no_fake_completeness
    - no_history_in_live_state
    - evidence_required_for_user_facing_claims
    - runtime_identity_required_for_user_facing_acceptance
    - negative_search_results_do_not_prove_nonexistence
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
    template-maintenance:
      purpose: maintain the StateDD template repository itself
      exit_condition: not used by downstream projects
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
  routing_plane:
    description: Dynamic CTO-lane selection of tools, models, settings, context strategy, and prompt shape.

invariants:
  - "STATUS.md stays short and current."
  - "PROJECT_STATE.yaml stores structured live truth only."
  - "PROJECT_DNA.yaml changes slowly."
  - "NEXT_ACTIONS.md contains open work only."
  - "BACKLOG.md assigns stable backlog IDs."
  - "Accepted user-facing milestones are frozen to source, runtime, and evidence."
  - "WORKLOG.md is append-only."

governance:
  evidence_standard: browser_verification_or_test_output
  evidence_artifact_root: docs/evidence
  acceptance_freeze_log: docs/ACCEPTANCE_FREEZES.md
  adr_root: docs/adr
  license: LICENSE
  license_faq: LICENSE_FAQ.md
  getting_started_guide: docs/GETTING_STARTED_5_MIN.md
  tool_model_routing_guide: prompts/TOOL_MODEL_ROUTING_GUIDE.md
  handoff_snapshot_helper: scripts/statedd_handoff.py
  runtime_proof_helper: scripts/statedd_runtime_proof.py
  runtime_identity_artifact: runtime_identity.json
  hygiene_check: scripts/check_state_docs.py
  bootstrap_gate_check: scripts/check_state_docs.py --bootstrap-gate
  closure_audit: scripts/statedd_audit.py
  health_summary: scripts/statedd_doctor.py
  slice_contract_template: prompts/SLICE_CONTRACT_TEMPLATE.md
  evidence_readme_template: prompts/EVIDENCE_README_TEMPLATE.md
  schema_ownership_template: prompts/SCHEMA_OWNERSHIP_TEMPLATE.md
  subagent_review_template: prompts/SUBAGENT_REVIEW_TEMPLATE.md
  cto_review_checklist: prompts/CTO_REVIEW_CHECKLIST.md
  update_policy:
    status: when_current_truth_changes
    project_state: when_structured_truth_changes
    worklog: when_work_is_completed
    evidence_log: when_user_facing_claims_are_verified

invariants:
  - "STATUS.md stays short and current."
  - "PROJECT_STATE.yaml stores structured live truth only."
  - "PROJECT_DNA.yaml changes slowly."
  - "NEXT_ACTIONS.md contains open work only."
  - "BACKLOG.md assigns stable backlog IDs."
  - "Accepted user-facing milestones are frozen to source, runtime, and evidence."
  - "WORKLOG.md is append-only."
  - "Implemented, validated, closure-grade, and accepted are four distinct states."
  - "Human overrides are recorded, but they do not turn partial work into closure-grade work."
  - "No schema may exist only in prose."
"""


def render_project_adapter(project_name: str) -> str:
    return f"""# PROJECT_ADAPTER.yaml - Optional project-specific adapter

version: "{TEMPLATE_VERSION}"

project:
  name: {project_name}
  short_name: {project_name}
  description: "Optional adapter layer for project-specific vocabulary and runtime details."

vocabulary:
  control_plane_name: "control plane"
  state_plane_name: "state plane"
  evidence_plane_name: "evidence plane"
  runtime_identity_name: "runtime identity"

runtime:
  frontend_port: null
  api_port: null
  public_url: null
  execution_mode: bootstrap
  runtime_identity_surface: null

integrations: []

ai_execution_preferences:
  available_tools: []
  planning_models: []
  coding_models: []
  review_models: []
  default_routing_priority: quality_then_cost
  notes:
    - "Fill this only with user-confirmed or currently verified access."
    - "Keep provider capability and pricing claims out of this file unless freshly verified."

notes:
  - "Populate this file when a real project is attached."
  - "Keep PROJECT_DNA.yaml focused on invariants."
"""


def render_new_next_actions(human_timestamp: str) -> str:
    return f"""# NEXT_ACTIONS - Active Execution Queue

**Updated At:** {human_timestamp}
**Execution Mode:** bootstrap
**Max Items:** 10

## Active Work

No active work yet.

## Queue Rules

- Keep this file short.
- List only active, open work.
- Remove completed items immediately.
- Every active item must reference a backlog ID like `[BL-001]`.
- Include owner, next action, and exit criteria when items exist.
"""


def render_adopt_next_actions(human_timestamp: str) -> str:
    return f"""# NEXT_ACTIONS - Active Execution Queue

**Updated At:** {human_timestamp}
**Execution Mode:** bootstrap
**Max Items:** 10

## Active Work

### P0 [BL-001] Reconcile contradictory inherited claims
Owner: human + coding agent
Next: inspect the inherited docs, manifests, and runtime files and replace unsupported claims with explicit statuses
Exit: `PROJECT_STATE.yaml` records the authoritative product/runtime contradictions and open unknowns

### P0 [BL-002] Capture the real runtime and deployment baseline
Owner: coding agent
Next: verify manifests, entrypoints, tests, and deployment assumptions directly from the repo
Exit: repo structure, entrypoints, and deployment assumptions are filled out truthfully in the state files

### P1 [BL-003] Prepare bootstrap evidence and a CTO-ready handoff
Owner: coding agent
Next: record initial evidence, append bootstrap history, and prepare the first CTO handoff using `prompts/FINAL_HANDOFF_TEMPLATE.md`
Exit: `docs/EVIDENCE_LOG.md` and `WORKLOG.md` explain what bootstrap established and what remains unknown

## Queue Rules

- Keep this file short.
- List only active, open work.
- Remove completed items immediately.
- Every active item must reference a backlog ID like `[BL-001]`.
- Include owner, next action, and exit criteria when items exist.
"""


def render_new_backlog(project_name: str, today: str) -> str:
    return f"""# BACKLOG - Strategic Roadmap

**Product:** {project_name}
**Execution Mode:** bootstrap
**Updated At:** {today}

## Purpose

This backlog tracks medium-term work using stable backlog IDs.
Reference these IDs from `NEXT_ACTIONS.md`.

## NOW

- [BL-001] Establish the project identity, primary user, and first milestone.
- [BL-002] Capture the initial runtime, deployment, and constraint baseline in the state files.

## NEXT

- [BL-003] Prepare the first active queue and bootstrap evidence trail.

## LATER

- [BL-004] Enter operating mode only after the baseline is truthful and the backlog is real.

## WATCHLIST

- Queue bloat.
- Unverified claims.
- Premature operating-mode transition.
"""


def render_adopt_backlog(project_name: str, today: str) -> str:
    return f"""# BACKLOG - Strategic Roadmap

**Product:** {project_name}
**Execution Mode:** bootstrap
**Updated At:** {today}

## Purpose

This backlog tracks the first bootstrap slices for an adopted existing repo.
Reference these IDs from `NEXT_ACTIONS.md`.

## NOW

- [BL-001] Resolve contradictions between inherited docs and the observed repo contents.
- [BL-002] Capture the real runtime stack, entrypoints, and deployment assumptions from the current codebase.
- [BL-003] Replace placeholder bootstrap history with a real evidence-backed baseline.

## NEXT

- [BL-004] Define the first operating-mode backlog slice once bootstrap truth is stable.

## LATER

- [BL-005] Install optional GitHub workflow assets only if they match the adopted repo's needs.

## WATCHLIST

- Silent overwrite of existing project docs.
- Treating inherited claims as facts without direct verification.
- Queue items that are not linked to a backlog ID.
"""


def render_worklog(today: str, mode: str) -> str:
    if mode == "adopt":
        return f"""# WORKLOG

**Purpose:** Append-only history for completed work.

Use this file for dated session notes, verification summaries, and references to evidence artifacts.

## {today} - Bootstrap workflow adopted into existing repo

**Type:** bootstrap_baseline
**Status:** COMPLETE
**Git Head:** unknown
**Worktree:** unknown

### What changed
- Installed the StateDD workflow files without replacing the existing project README by default.
- Captured an initial bootstrap baseline from the current repo structure and documented the active queue using backlog IDs.

### Verification
- Repo structure was inspected directly during adoption.

### Evidence
- `docs/EVIDENCE_LOG.md` entry `EV-{today}-001`
"""

    return """# WORKLOG

**Purpose:** Append-only history for completed work.

Use this file for dated session notes, verification summaries, and references to evidence artifacts.
"""


def render_evidence_log(today: str, mode: str) -> str:
    guidance = """# EVIDENCE_LOG.md

**Purpose:** Structured ledger of proof artifacts for user-facing claims.

## Entry Format

```yaml
- ID: EV-YYYY-MM-DD-001
  File: /absolute/path/to/artifact.png
  Title: short description
  Source/System: browser | api | test | log | screenshot
  Route/Page: optional route or URL
  Action: what was done
  Shows:
    - visible fact 1
    - visible fact 2
  Proves:
    - why the artifact matters
  Type: source-data | chatbot | gap | integration | docs-render-verification
  as_of: 2026-03-18T18:00:00+01:00
  Notes: optional context
```

## Guidance

- Link evidence to the specific claim it supports.
- Prefer durable artifact paths.
- Place saved artifacts under `docs/evidence/YYYY-MM-DD-<slug>/` when possible.
- Add timestamps for anything that may become stale.
"""
    if mode == "adopt":
        return guidance + f"""

## EV-{today}-001: Adopted repo bootstrap baseline captured

- File: PROJECT_STATE.yaml
- File: BACKLOG.md
- File: NEXT_ACTIONS.md
- Title: Existing repo adoption baseline created from observed repo contents
- Source/System: docs
- Action: Installed the workflow files and recorded the first bootstrap baseline from the inherited repository structure and contradictory docs
- Shows:
  - the repo now has explicit bootstrap state, backlog IDs, and an active queue
  - inherited contradictions are tracked as open bootstrap work rather than silently accepted
- Proves:
  - the adopted repo has a non-placeholder bootstrap baseline to continue from
- Type: gap
- as_of: {today}T00:00:00+00:00
"""
    return guidance


def render_acceptance_freezes() -> str:
    return """# ACCEPTANCE_FREEZES.md

**Purpose:** Append-only ledger of accepted user-facing or operator-facing milestones.

Use this when a screen, route, workflow, or other visible milestone is accepted
and must be protected from quiet regression.

## Entry Format

```yaml
- ID: AF-YYYY-MM-DD-001
  Milestone: short milestone name
  Scope: what was accepted
  repo_path: /absolute/path/to/repo
  branch: main
  head: abc1234
  process_or_container: npm dev | docker container name | other
  port_or_base_url: http://localhost:3000
  routes:
    - /
    - /settings
  rebuilt_in_slice: true
  duplicate_runtimes_checked: true
  evidence_refs:
    - EV-YYYY-MM-DD-001
  regression_guard:
    - later work must branch from this accepted lineage
    - route-role changes require explicit backlog scope and new evidence
  Notes: optional
```

## Guidance

- Do not treat screenshots alone as an acceptance freeze.
- Tie the accepted state to repo truth, runtime truth, and evidence truth.
- If a later report conflicts with the freeze, prove runtime identity before drawing conclusions from git history.
"""


def render_readme_section() -> str:
    return f"""
## StateDD Workflow

This repo now uses the {TEMPLATE_NAME} workflow.
The workflow contract lives in `AGENTS.md`, the current truth lives in
`STATUS.md` and `PROJECT_STATE.yaml`, and the canonical handoff shape lives in
`prompts/FINAL_HANDOFF_TEMPLATE.md`.

Keep the existing project README content authoritative for product behavior.
Use the workflow files to run bootstrap and steady-state delivery.
"""


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def path_exists_for_write(path: Path) -> bool:
    return path.exists() or path.is_symlink()


def normalize_managed_relpath(relpath: str | Path) -> Path:
    path = Path(relpath)
    if path.is_absolute() or not path.parts:
        raise SystemExit(f"Unsafe managed path: {relpath}")
    if any(part in {"", ".", ".."} for part in path.parts):
        raise SystemExit(f"Unsafe managed path: {relpath}")
    return path


def reject_symlink_components(root: Path, relpath: Path) -> None:
    current = root
    if current.is_symlink():
        raise SystemExit(f"Refusing to write through symlinked target root: {current}")

    for part in relpath.parts:
        current = current / part
        if current.is_symlink():
            raise SystemExit(f"Refusing to write through symlink inside target: {current}")


def prepare_destination(root: Path, relpath: str | Path) -> Path:
    normalized = normalize_managed_relpath(relpath)
    reject_symlink_components(root, normalized)
    destination = root / normalized
    destination.parent.mkdir(parents=True, exist_ok=True)
    reject_symlink_components(root, normalized)
    return destination


def ensure_directory(root: Path, relpath: Path) -> None:
    normalized = normalize_managed_relpath(relpath)
    reject_symlink_components(root, normalized)
    directory = root / normalized
    directory.mkdir(parents=True, exist_ok=True)
    reject_symlink_components(root, normalized)


def write_file(root: Path, relpath: str | Path, content: str) -> None:
    path = prepare_destination(root, relpath)
    if path.is_dir():
        raise SystemExit(f"Refusing to replace directory with file: {relpath}")
    path.write_text(content, encoding="utf-8")


def copy_file(source: Path, target: Path, relpath: Path) -> None:
    normalized = normalize_managed_relpath(relpath)
    source_path = source / normalized
    if source_path.is_symlink():
        raise SystemExit(f"Refusing to copy symlinked template source: {normalized}")
    destination = prepare_destination(target, normalized)
    shutil.copy2(source_path, destination)


def should_ignore_path(path: Path) -> bool:
    return any(part in IGNORED_TEMPLATE_NAMES for part in path.parts)


def should_copy_template_path(relpath: Path) -> bool:
    if should_ignore_path(relpath):
        return False
    if relpath in TEMPLATE_COPY_ROOT_FILES:
        return True
    return bool(relpath.parts) and relpath.parts[0] in TEMPLATE_COPY_DIR_NAMES


def run_git(args: list[str], cwd: Path) -> str | None:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None
    return completed.stdout.strip() or None


def scan_repo(target: Path) -> RepoScan:
    branch = run_git(["rev-parse", "--abbrev-ref", "HEAD"], target)
    head = run_git(["rev-parse", "--short", "HEAD"], target)

    top_level_entries = sorted(entry.name for entry in target.iterdir() if not should_ignore_path(Path(entry.name)))

    manifest_candidates = [
        "package.json",
        "pyproject.toml",
        "requirements.txt",
        "Pipfile",
        "poetry.lock",
        "docker-compose.yml",
        "compose.yml",
        "Dockerfile",
        "go.mod",
        "Cargo.toml",
        "Gemfile",
        "pnpm-lock.yaml",
        "package-lock.json",
        "yarn.lock",
    ]
    manifests = [name for name in manifest_candidates if (target / name).exists()]

    entrypoints: list[str] = []
    package_json = target / "package.json"
    if package_json.exists() and not package_json.is_symlink():
        try:
            data = json.loads(read_text(package_json))
        except json.JSONDecodeError:
            pass
        else:
            scripts = data.get("scripts", {})
            if "dev" in scripts:
                entrypoints.append("package.json:scripts.dev")
            if "start" in scripts:
                entrypoints.append("package.json:scripts.start")
            if "test" in scripts:
                entrypoints.append("package.json:scripts.test")

    for candidate in (
        "main.py",
        "app.py",
        "server.py",
        "worker.py",
        "server.js",
        "src/main.ts",
        "src/main.tsx",
        "src/main.js",
        "src/index.ts",
        "src/index.tsx",
        "src/index.js",
    ):
        if (target / candidate).exists():
            entrypoints.append(candidate)

    test_setup: list[str] = []
    for candidate in ("tests", "test", "cypress", "playwright.config.ts", "pytest.ini", "tox.ini", "vitest.config.ts"):
        if (target / candidate).exists():
            test_setup.append(candidate)
    if "package.json:scripts.test" in entrypoints:
        test_setup.append("package.json test script present")
    if not test_setup:
        test_setup.append("unknown")

    deployment_assumptions: list[str] = []
    if (target / "docker-compose.yml").exists() or (target / "compose.yml").exists():
        deployment_assumptions.append("docker compose present")
    if (target / "Dockerfile").exists():
        deployment_assumptions.append("dockerfile present")
    if any(path.name.endswith((".yaml", ".yml")) and "k8" in path.name.lower() for path in target.rglob("*")):
        deployment_assumptions.append("kubernetes-like manifest present")
    if not deployment_assumptions:
        deployment_assumptions.append("deployment target not yet proven")

    doc_text = []
    for candidate in ("README.md", "NOTES.txt", "docs/STATUS.md", "docs/ARCHITECTURE.md"):
        path = target / candidate
        if path.exists() and not path.is_symlink():
            doc_text.append(read_text(path).lower())
    docs = "\n".join(doc_text)

    contradictions: list[str] = []
    if "kubernetes" in docs and ("docker compose present" in deployment_assumptions):
        contradictions.append("docs mention kubernetes while docker compose files remain present")
    if "frontend only" in docs and (target / "docker-compose.yml").exists():
        contradictions.append("docs claim frontend-only scope while the repo still contains multi-service runtime files")
    if "production is stable" in docs:
        contradictions.append("stability is reported in inherited docs but not yet directly verified")
    if not contradictions:
        contradictions.append("no contradictions observed yet")

    project_type = "adopted_existing_repo" if top_level_entries else "project_template"
    project_summary = "bootstrap_adoption_baseline" if top_level_entries else "bootstrap_initializing"

    return RepoScan(
        canonical_path=str(target),
        branch=branch,
        head=head,
        top_level_entries=top_level_entries,
        manifests=manifests or ["unknown"],
        entrypoints=entrypoints or ["unknown"],
        test_setup=test_setup,
        deployment_assumptions=deployment_assumptions,
        contradictions=contradictions,
        project_summary=project_summary,
        project_type=project_type,
    )


def find_conflicting_template_paths(template_root: Path, target: Path) -> list[Path]:
    conflicts: list[Path] = []
    for source_path in template_root.rglob("*"):
        if source_path.is_dir():
            continue
        relpath = source_path.relative_to(template_root)
        if not should_copy_template_path(relpath):
            continue
        if path_exists_for_write(target / relpath):
            conflicts.append(relpath)
    return sorted(conflicts)


def copy_template_tree(
    template_root: Path,
    target: Path,
    *,
    overwrite: bool,
    force_overwrite: bool,
    dry_run: bool,
) -> None:
    if target.exists() and not target.is_dir():
        raise SystemExit("Target exists and is not a directory.")

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

    if target != template_root and not dry_run:
        target.mkdir(parents=True, exist_ok=True)
        for source_path in sorted(template_root.rglob("*")):
            relpath = source_path.relative_to(template_root)
            if not should_copy_template_path(relpath):
                continue
            if source_path.is_symlink():
                raise SystemExit(f"Refusing to copy symlinked template source: {relpath}")
            if source_path.is_dir():
                ensure_directory(target, relpath)
            elif source_path.is_file():
                copy_file(template_root, target, relpath)


def plan_asset_actions(
    relpaths: list[Path],
    target: Path,
    *,
    overwrite: bool,
    force_overwrite: bool,
) -> tuple[list[str], list[str]]:
    actions: list[str] = []
    conflicts: list[str] = []
    for relpath in relpaths:
        dest = target / relpath
        if path_exists_for_write(dest):
            if overwrite and force_overwrite:
                actions.append(f"overwrite {relpath}")
            else:
                conflicts.append(str(relpath))
        else:
            actions.append(f"create {relpath}")
    return actions, conflicts


def copy_assets(
    relpaths: list[Path],
    target: Path,
    *,
    overwrite: bool,
    force_overwrite: bool,
    dry_run: bool,
) -> None:
    actions, conflicts = plan_asset_actions(relpaths, target, overwrite=overwrite, force_overwrite=force_overwrite)
    if conflicts and not (overwrite and force_overwrite):
        preview = ", ".join(conflicts[:8])
        if len(conflicts) > 8:
            preview += ", ..."
        raise SystemExit(
            "Adoption would overwrite existing workflow assets: "
            f"{preview}. Re-run with --overwrite --force-overwrite only if replacing them is intentional."
        )

    if dry_run:
        print("Planned support-asset actions:")
        for action in actions:
            print(f"  - {action}")
        if conflicts:
            for relpath in conflicts:
                print(f"  - overwrite {relpath}")
        return

    for relpath in relpaths:
        copy_file(TEMPLATE_ROOT, target, relpath)


def apply_managed_files(
    target: Path,
    managed_files: dict[str, str],
    *,
    overwrite: bool,
    force_overwrite: bool,
    dry_run: bool,
) -> None:
    conflicts = []
    for relpath in managed_files:
        path = target / relpath
        if path_exists_for_write(path) and not overwrite:
            conflicts.append(relpath)
        if path_exists_for_write(path) and overwrite and not force_overwrite and relpath in {
            "AGENTS.md",
            "STATUS.md",
            "PROJECT_STATE.yaml",
            "PROJECT_DNA.yaml",
            "PROJECT_ADAPTER.yaml",
            "NEXT_ACTIONS.md",
            "BACKLOG.md",
            "WORKLOG.md",
            "docs/EVIDENCE_LOG.md",
        }:
            conflicts.append(relpath)

    if conflicts:
        preview = ", ".join(conflicts[:8])
        if len(conflicts) > 8:
            preview += ", ..."
        raise SystemExit(
            "Managed workflow files already exist and would be replaced: "
            f"{preview}. Re-run with --overwrite --force-overwrite only if this is intentional."
        )

    if dry_run:
        print("Planned managed-file writes:")
        for relpath in managed_files:
            print(f"  - write {relpath}")
        return

    for relpath, content in managed_files.items():
        write_file(target, relpath, content)


def maybe_append_readme_link(target: Path, *, dry_run: bool) -> None:
    readme = target / "README.md"
    validate_readme_link_target(target)
    if not readme.exists():
        return
    section = render_readme_section().strip()
    text = read_text(readme)
    if section in text:
        return
    if dry_run:
        print("Planned README action:")
        print("  - append StateDD workflow section to README.md")
        return
    write_file(target, "README.md", text.rstrip() + "\n\n" + section + "\n")


def validate_readme_link_target(target: Path) -> None:
    readme = target / "README.md"
    if readme.is_symlink():
        raise SystemExit("Refusing to append workflow section to symlinked README.md.")


def minimal_cleanup(target: Path, *, dry_run: bool) -> None:
    if dry_run:
        print("Planned minimal cleanup:")
        print("  - remove fixtures/")
        print("  - remove docs/BOOTSTRAP_QUALITY.md")
        return
    shutil.rmtree(target / "fixtures", ignore_errors=True)
    (target / "docs" / "BOOTSTRAP_QUALITY.md").unlink(missing_ok=True)


def build_managed_files_for_new(project_name: str, target: Path, today: str, stamp: str, human_timestamp: str) -> dict[str, str]:
    repo_scan = RepoScan(
        canonical_path=str(target),
        branch=None,
        head=None,
        top_level_entries=[
            ".github",
            ".gitignore",
            "docs",
            "fixtures",
            "prompts",
            "schemas",
            "scripts",
            "AGENTS.md",
            "BACKLOG.md",
            "LICENSE",
            "NEXT_ACTIONS.md",
            "PROJECT_ADAPTER.yaml",
            "PROJECT_DNA.yaml",
            "PROJECT_STATE.yaml",
            "README.md",
            "STATUS.md",
            "WORKLOG.md",
        ],
        manifests=[
            "README.md",
            "docs/GETTING_STARTED_5_MIN.md",
            "scripts/init_template.py",
            "scripts/check_state_docs.py",
            "scripts/statedd_version_check.py",
            "scripts/statedd_handoff.py",
            "scripts/statedd_runtime_proof.py",
            "scripts/statedd_validate_schema.py",
            "scripts/test_init_template.py",
            "scripts/test_runtime_proof.py",
            "scripts/test_schema_validation.py",
        ],
        entrypoints=[
            "scripts/init_template.py",
            "scripts/check_state_docs.py",
            "scripts/statedd_version_check.py",
            "scripts/statedd_handoff.py",
            "scripts/statedd_runtime_proof.py",
            "scripts/statedd_validate_schema.py",
            "scripts/test_init_template.py",
            "scripts/test_runtime_proof.py",
            "scripts/test_schema_validation.py",
        ],
        test_setup=[
            "scripts/check_state_docs.py",
            "scripts/statedd_validate_schema.py",
            "scripts/test_init_template.py",
            "scripts/test_runtime_proof.py",
            "scripts/test_schema_validation.py",
        ],
        deployment_assumptions=["distributed as a git-hosted workflow template"],
        contradictions=["project-specific contradictions not yet investigated"],
        project_summary="bootstrap_initializing",
        project_type="project_template",
    )
    return {
        "AGENTS.md": render_agents_template(today, "bootstrap"),
        "STATUS.md": render_status(
            project_name,
            human_timestamp,
            summary_lines=[
                "Repo initialized in bootstrap mode.",
                "Project-specific truth still needs to be established.",
                "Unknowns remain explicit until proven.",
                "Current work should be tracked through `NEXT_ACTIONS.md`.",
                "Evidence for user-facing claims belongs in `docs/EVIDENCE_LOG.md`.",
            ],
            priorities=[
                "Capture the real project truth.",
                "Fill in the first active queue.",
                "Transition to operating mode once baseline truth exists.",
            ],
        ),
        "PROJECT_STATE.yaml": render_project_state(
            project_name,
            stamp,
            repo_scan,
            system_investigated=False,
            repo_investigated=False,
            unknowns=[
                "product not yet defined",
                "primary user not yet defined",
                "target deployment/runtime not yet defined",
                "first real milestone not yet defined",
            ],
        ),
        "PROJECT_DNA.yaml": render_project_dna(project_name),
        "PROJECT_ADAPTER.yaml": render_project_adapter(project_name),
        "NEXT_ACTIONS.md": render_new_next_actions(human_timestamp),
        "BACKLOG.md": render_new_backlog(project_name, today),
        "WORKLOG.md": render_worklog(today, "new"),
        "docs/EVIDENCE_LOG.md": render_evidence_log(today, "new"),
        "docs/ACCEPTANCE_FREEZES.md": render_acceptance_freezes(),
        "docs/evidence/.gitkeep": "",
        "docs/adr/.gitkeep": "",
    }


def build_managed_files_for_adopt(project_name: str, target: Path, today: str, stamp: str, human_timestamp: str) -> dict[str, str]:
    repo_scan = scan_repo(target)
    return {
        "AGENTS.md": render_agents_template(today, "bootstrap"),
        "STATUS.md": render_status(
            project_name,
            human_timestamp,
            summary_lines=[
                "Existing repo adopted into the bootstrap workflow without replacing the project README by default.",
                "Repo structure, manifests, and inherited docs were inspected directly during adoption.",
                "Contradictions and unknowns remain explicit until they are verified or resolved.",
                "The first active queue now points back to stable backlog IDs.",
            ],
            priorities=[
                "Resolve inherited contradictions and establish authoritative scope.",
                "Capture the real runtime and deployment baseline.",
                "Prepare the first CTO-ready bootstrap handoff.",
            ],
        ),
        "PROJECT_STATE.yaml": render_project_state(
            project_name,
            stamp,
            repo_scan,
            system_investigated=True,
            repo_investigated=True,
            unknowns=[
                "primary user still needs direct confirmation",
                "first milestone still needs direct confirmation",
                "deployment target may differ from inherited docs",
            ],
        ),
        "PROJECT_DNA.yaml": render_project_dna(project_name),
        "PROJECT_ADAPTER.yaml": render_project_adapter(project_name),
        "NEXT_ACTIONS.md": render_adopt_next_actions(human_timestamp),
        "BACKLOG.md": render_adopt_backlog(project_name, today),
        "WORKLOG.md": render_worklog(today, "adopt"),
        "docs/EVIDENCE_LOG.md": render_evidence_log(today, "adopt"),
        "docs/ACCEPTANCE_FREEZES.md": render_acceptance_freezes(),
        "docs/evidence/.gitkeep": "",
        "docs/adr/.gitkeep": "",
    }


def build_subcommand_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Initialize or adopt the StateDD workflow")
    subparsers = parser.add_subparsers(dest="command", required=True)

    new_parser = subparsers.add_parser("new", help="Create a new repo from the template")
    new_parser.add_argument("--name", required=True, help="Project name to stamp into the template")
    new_parser.add_argument("--target", default=".", help="Repo root to initialize")
    new_parser.add_argument("--minimal", action="store_true", help="Remove optional fixtures/examples")
    new_parser.add_argument("--dry-run", action="store_true", help="Preview actions without writing files")
    new_parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow initialization into an existing non-empty target when no template-path collisions are present",
    )
    new_parser.add_argument(
        "--force-overwrite",
        action="store_true",
        help="Allow template files to replace conflicting files in an existing non-empty target",
    )

    adopt_parser = subparsers.add_parser("adopt", help="Install the workflow into an existing repo")
    adopt_parser.add_argument("--name", required=True, help="Project name to stamp into the workflow files")
    adopt_parser.add_argument("--target", default=".", help="Existing repo root to adopt")
    adopt_parser.add_argument("--dry-run", action="store_true", help="Preview actions without writing files")
    adopt_parser.add_argument(
        "--readme-link",
        action="store_true",
        help="Append a short workflow section to the existing README instead of leaving it untouched",
    )
    adopt_parser.add_argument(
        "--install-github-assets",
        action="store_true",
        help="Copy optional GitHub workflow and template assets into the existing repo",
    )
    adopt_parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow replacing existing workflow-managed files in the target",
    )
    adopt_parser.add_argument(
        "--force-overwrite",
        action="store_true",
        help="Actually replace conflicting workflow files when used with --overwrite",
    )
    return parser


def build_legacy_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create a new repo from the StateDD workflow template")
    parser.add_argument("--name", required=True, help="Project name to stamp into the template")
    parser.add_argument("--target", default=".", help="Repo root to initialize")
    parser.add_argument("--minimal", action="store_true", help="Remove optional fixtures/examples")
    parser.add_argument("--dry-run", action="store_true", help="Preview actions without writing files")
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
    return parser


def parse_args(argv: list[str]) -> argparse.Namespace:
    if len(argv) == 1 or argv[1] in {"-h", "--help", "new", "adopt"}:
        return build_subcommand_parser().parse_args(argv[1:])
    namespace = build_legacy_parser().parse_args(argv[1:])
    namespace.command = "new"
    namespace.legacy_mode = True
    return namespace


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv)
    if args.force_overwrite and not args.overwrite:
        raise SystemExit("--force-overwrite requires --overwrite.")

    now = dt.datetime.now(dt.timezone.utc).astimezone()
    today = now.date().isoformat()
    stamp = now.isoformat(timespec="seconds")
    human_timestamp = now.strftime("%Y-%m-%d %H:%M %Z")
    target = Path(args.target).resolve()

    if args.command == "new":
        copy_template_tree(
            TEMPLATE_ROOT,
            target,
            overwrite=args.overwrite,
            force_overwrite=args.force_overwrite,
            dry_run=args.dry_run,
        )
        managed_files = build_managed_files_for_new(args.name, target, today, stamp, human_timestamp)
        apply_managed_files(
            target,
            managed_files,
            overwrite=True,
            force_overwrite=True,
            dry_run=args.dry_run,
        )
        if args.minimal:
            minimal_cleanup(target, dry_run=args.dry_run)

        if args.dry_run:
            print("Dry run complete.")
            return 0

        print(f"Initialized {TEMPLATE_NAME} repo")
        print(f"Target: {target}")
        print("Mode: bootstrap")
        if (target / ".git").exists():
            print("Warning: target contains git metadata. Verify git remote -v before first push.")
        print("Next:")
        print("1. Read docs/GETTING_STARTED_5_MIN.md, then README.md when you need the full guide")
        print("2. Fix git ownership first if needed: remove .git, init your own repo, and verify git remote -v")
        print("3. Start OpenCode with prompts/OPENCODE_STARTUP_PROMPT.md or another coding agent with prompts/CODING_AGENT_STARTUP_PROMPT.md")
        print("4. Let the coding agent read the repo files, detect bootstrap mode, and ask the minimum strategic questions")
        print("5. Then create a CTO chat and paste prompts/CTO_SESSION_PROMPT.md")
        print("6. Use bootstrap to fill the state files and prepare a real backlog before operating mode")
        print(f"7. Run {Path(sys.executable).name} scripts/check_state_docs.py after bootstrap updates")
        print(f"8. Run {Path(sys.executable).name} scripts/statedd_validate_schema.py after state/evidence updates")
        print(f"9. Run {Path(sys.executable).name} scripts/statedd_audit.py before claiming closure-grade")
        print(f"10. Run {Path(sys.executable).name} scripts/statedd_doctor.py for a quick health snapshot")
        print(f"11. Run {Path(sys.executable).name} scripts/check_state_docs.py --bootstrap-gate before flipping to operating")
        return 0

    if not target.exists() or not target.is_dir():
        raise SystemExit("Adoption target must be an existing repo directory.")

    managed_files = build_managed_files_for_adopt(args.name, target, today, stamp, human_timestamp)
    support_paths = list(SUPPORT_ASSET_PATHS)
    if args.install_github_assets:
        support_paths.extend(GITHUB_ASSET_PATHS)
    if args.readme_link:
        validate_readme_link_target(target)

    copy_assets(
        support_paths,
        target,
        overwrite=args.overwrite,
        force_overwrite=args.force_overwrite,
        dry_run=args.dry_run,
    )
    apply_managed_files(
        target,
        managed_files,
        overwrite=args.overwrite,
        force_overwrite=args.force_overwrite,
        dry_run=args.dry_run,
    )
    if args.readme_link:
        maybe_append_readme_link(target, dry_run=args.dry_run)

    if args.dry_run:
        print("Dry run complete.")
        return 0

    print(f"Adopted repo into the {TEMPLATE_NAME} workflow")
    print(f"Target: {target}")
    print("Mode: bootstrap")
    print("README behavior: existing README preserved")
    if args.readme_link:
        print("README behavior: appended workflow section")
    if args.install_github_assets:
        print("GitHub assets: installed")
    else:
        print("GitHub assets: skipped")
    print("Next:")
    print("1. Read docs/GETTING_STARTED_5_MIN.md")
    print("2. Review PROJECT_STATE.yaml, BACKLOG.md, and NEXT_ACTIONS.md against the real repo")
    print("3. Resolve contradictions before treating inherited claims as current truth")
    print("4. Start OpenCode with prompts/OPENCODE_STARTUP_PROMPT.md or another coding agent with the repo contract")
    print("5. Use prompts/FINAL_HANDOFF_TEMPLATE.md or scripts/statedd_handoff.py for the first CTO handoff")
    print(f"6. Run {Path(sys.executable).name} scripts/check_state_docs.py after edits")
    print(f"7. Run {Path(sys.executable).name} scripts/statedd_audit.py before claiming closure-grade")
    print(f"8. Run {Path(sys.executable).name} scripts/statedd_doctor.py for a quick health snapshot")
    print(f"9. Run {Path(sys.executable).name} scripts/check_state_docs.py --bootstrap-gate before flipping to operating")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
