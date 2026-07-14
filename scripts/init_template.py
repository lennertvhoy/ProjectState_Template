#!/usr/bin/env python3
"""Initialize or adopt the StateDD template workflow."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from contextlib import contextmanager, nullcontext
from dataclasses import dataclass
from pathlib import Path

try:
    from statedd_contracts import (
        ContractError,
        UnsafePathError,
        confined_path,
        load_profile_catalog,
        normalize_relative_path,
        regular_source_path,
        resolve_profile,
        safe_root_path,
    )
    from statedd_generated_controls import (
        recommended_merge_mode,
        render_coding_agent_startup_prompt as render_coding_agent_control,
        render_downstream_workflow as render_workflow_control,
        render_proposed_delivery_policy,
    )
    from statedd_validate_schema import load_schema, validate_json_schema
except ModuleNotFoundError:  # pragma: no cover - pytest package import path
    from scripts.statedd_contracts import (
        ContractError,
        UnsafePathError,
        confined_path,
        load_profile_catalog,
        normalize_relative_path,
        regular_source_path,
        resolve_profile,
        safe_root_path,
    )
    from scripts.statedd_generated_controls import (
        recommended_merge_mode,
        render_coding_agent_startup_prompt as render_coding_agent_control,
        render_downstream_workflow as render_workflow_control,
        render_proposed_delivery_policy,
    )
    from scripts.statedd_validate_schema import load_schema, validate_json_schema


TEMPLATE_ROOT = Path(__file__).resolve().parents[1]
IGNORED_TEMPLATE_NAMES = {".git", ".codex", ".playwright-mcp", "__pycache__", ".cache"}

TEMPLATE_NAME = "State Driven Development Template"
CONTRACT_TITLE = "State Driven Development Template Contract"
TEMPLATE_VERSION = "statedd-template-v5"
try:
    PROFILE_CATALOG = load_profile_catalog(TEMPLATE_ROOT)
except ContractError as exc:  # fail before any target write
    raise SystemExit(f"Invalid StateDD profile catalog: {exc}") from exc
VALID_PROFILES = set(PROFILE_CATALOG["profiles"])
OPTIONAL_ASSET_SETS = sorted(
    set_id
    for set_id, definition in PROFILE_CATALOG["asset_sets"].items()
    if definition.get("optional") is True
)
try:
    _version_file = regular_source_path(TEMPLATE_ROOT, "VERSION").read_text(encoding="utf-8").strip()
except (UnsafePathError, OSError, UnicodeDecodeError) as exc:
    raise SystemExit(f"Invalid StateDD template VERSION source: {exc}") from exc
if len({TEMPLATE_VERSION, PROFILE_CATALOG["template_version"], _version_file}) != 1:
    raise SystemExit(
        "StateDD template version mismatch across init constant, profiles/catalog.json, and VERSION"
    )


def current_time() -> dt.datetime:
    """Return reproducible UTC time when SOURCE_DATE_EPOCH is configured."""
    raw = os.environ.get("SOURCE_DATE_EPOCH")
    if raw is None:
        return dt.datetime.now(dt.timezone.utc).astimezone()
    try:
        epoch = int(raw)
    except ValueError as exc:
        raise SystemExit("SOURCE_DATE_EPOCH must be an integer Unix timestamp") from exc
    return dt.datetime.fromtimestamp(epoch, tz=dt.timezone.utc)


def validate_profile(profile: str) -> str:
    if profile not in VALID_PROFILES:
        raise SystemExit(f"Unknown profile {profile!r}; expected one of {VALID_PROFILES}")
    return profile


def profile_summary(profile: str) -> str:
    summaries = {
        "minimal": "Smallest useful StateDD footprint; no fake completeness; keeps the bootstrap gate.",
        "solo": "Standard single-developer workflow with evidence template, runtime proof, and schema validation.",
        "team": "Stricter handoff/evidence/audit defaults and PR/review-friendly documentation.",
        "regulated": "Strict audit defaults; runtime proof expected for user-facing work; evidence manifest/redaction gate expected; acceptance freeze guidance emphasized.",
    }
    return summaries[profile]


def profile_agents_note(profile: str) -> str:
    if profile == "minimal":
        return """## Profile

`minimal`: core state and gates only; add optional proof helpers when needed."""
    if profile == "team":
        return """## Profile

`team`: non-trivial slices use isolated worktrees, a claim ledger, review, and
remote CI agreement before closure-grade."""
    if profile == "regulated":
        return """## Profile

`regulated`: runtime/user-facing acceptance requires runtime identity; evidence
manifests record redaction; accepted milestones are frozen; overrides record scope,
rationale, and residual risk."""
    return """## Profile

`solo`: keep one short queue and use evidence, runtime proof, and slice gates in
proportion to the claim."""


def assets_for_profile(profile: str, *, optional_asset_sets: tuple[str, ...] = ()) -> list[Path]:
    return list(
        resolve_profile(
            PROFILE_CATALOG,
            validate_profile(profile),
            optional_asset_sets=optional_asset_sets,
        ).assets
    )


def profile_gate_level(profile: str) -> int:
    return resolve_profile(PROFILE_CATALOG, validate_profile(profile)).required_gate_level


OPTIONAL_GITHUB_ASSET_PATHS = [
    normalize_relative_path(path)
    for path in PROFILE_CATALOG["asset_sets"]["github"]["assets"]
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


def render_agents_template(today: str, mode: str, profile: str = "team") -> str:
    return f"""---
repo_role: downstream_project
statedd_mode: {mode}
repo_mode: {mode}
statedd_version: "{TEMPLATE_VERSION}"
initialized_on: {today}
last_updated: {today}
---

# {CONTRACT_TITLE}

**Purpose:** Small, stable truth contract for AI-assisted delivery.

## Task-Scoped Read Order

1. Always read `AGENTS.md`.
2. For orientation or resumption, read `STATUS.md`, `NEXT_ACTIONS.md`, and the
   active-slice fields in canonical `PROJECT_STATE.yaml`.
3. Read `PROJECT_DNA.yaml` for architecture, invariants, or unfamiliar changes.
4. Read the nearest nested `AGENTS.md` before working in a subtree.

Load backlog, history, evidence, and inventory only when the task needs planning,
history, proof, or repository detail. Generated context packs are disposable
views and never replace canonical readable state.

## Rules

- Unverified claims are false; negative searches mean `not found` or `not proven`.
- `PROJECT_STATE.yaml` is canonical current truth; `STATUS.md` is its human view.
- `NEXT_ACTIONS.md` contains open work only; history goes to `WORKLOG.md`.
- Implemented, validated, closure-grade, and accepted are distinct states.
- Repo, commit, remote, CI, runtime, and user-accepted truth require separate proof.
- User-facing closure requires runtime identity plus browser verification; a
  screenshot alone is insufficient and no browser provider is mandatory.
- P0 product failure enters `quality_freeze` or `incident_response`.
- Non-trivial work starts from classified, isolated worktree state and names the
  invariant that prevents brittle example-only fixes.
- Repository or StateDD mutation starts only after
  `scripts/statedd_git_safety_check.py` permits `normal_branch`, `worktree`, or
  `clone`; containers and independent agents use full clones.
- One integration agent owns each slice branch; subagents return bounded commits,
  do not edit global StateDD truth, and do not push the final slice.
- Agent clones are created only through `scripts/statedd_agent_worktree.py` under
  the per-user managed workspace root. Agent workspaces cannot provision nested
  agents, arbitrary isolation targets are forbidden, and every handoff inventories
  unexpected same-origin sibling clones.
- The human confirms `delivery_policy.merge.mode` once during bootstrap. A
  proposed or pending policy grants no merge authority, and an agent never
  silently changes a confirmed mode.
- Confirmed `human_merge` stops automation before merge. Confirmed
  `agent_after_green` lets the integration agent squash-merge only the exact
  verified PR head, verify direct-main CI, write an external final handoff, and
  delete the remote slice branch only after post-merge verification through
  `scripts/statedd_finish_slice.py`.
- `HANDOFF_COMPLETE` requires a closed-world release receipt proving the original
  isolation path is absent. Clean clones are quarantined outside the project
  parent; clean opted-in worktrees are removed without force; dirty or unproven
  state is retained.
- Force-push, shared-history rewrite, and CI-unavailable automatic merge remain
  forbidden; final product acceptance remains human.
- End implementation sessions with state hygiene, relevant gates, and a handoff.

## Current Mode: `{mode}`

In `bootstrap`, investigate system/repo truth, record unknowns, create a real
backlog and queue, then run `python3 scripts/check_state_docs.py --bootstrap-gate`.
Switch to `operating` only after that gate passes. In `operating`, execute one
coherent backlog slice at a time and keep live state current.

{profile_agents_note(profile)}

## Gates And Handoff

- Edit loop: relevant tests plus `python3 scripts/check_state_docs.py`.
- Slice closure: `python3 scripts/statedd_quality_gate.py --gate-level 2` plus
  runtime/evidence/remote gates applicable to the claim.
- Report changes, verification, repo/branch/HEAD, runtime process/endpoint/rebuild,
  worktree cleanliness, evidence paths, residual risk, and next action.
"""


def render_status(project_name: str, human_timestamp: str, *, summary_lines: list[str], priorities: list[str], profile: str = "team") -> str:
    snapshot = "\n".join(f"- {line}" for line in summary_lines)
    priority_block = "\n".join(f"{index}. {line}" for index, line in enumerate(priorities, start=1))
    return f"""# {project_name} Status

**Updated At:** {human_timestamp}
**Execution Mode:** bootstrap
**Project State:** bootstrap_initializing
**Public URL:** not configured
**Profile:** {profile}

## Snapshot

{snapshot}

## Immediate Priorities

{priority_block}

## Active Blockers

- None yet.

## Product Truth

- Not proven yet during bootstrap.

## Runtime Truth

- Not proven yet during bootstrap.

## Current Quality Gate

- Product quality gate: not_run.
- Runtime truth gate: not_run.
- Known bad events gate: not_run.

## Open P0/P1 Failures

- None recorded yet.

## What Is Not Proven

- Product behavior, runtime identity, deployment shape, and global quality invariants remain unproven until bootstrap fills `PROJECT_STATE.yaml`.

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
    profile: str = "team",
) -> str:
    branch = json.dumps(repo_scan.branch) if repo_scan.branch is not None else "null"
    head = json.dumps(repo_scan.head) if repo_scan.head is not None else "null"
    unknowns_block = "\n".join(f"      - {json.dumps(entry)}" for entry in unknowns) or "      []"
    runtime_helper = "not_installed_in_minimal_profile" if profile == "minimal" else "scripts/statedd_runtime_proof.py"
    delivery_policy = render_proposed_delivery_policy(profile)

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

{delivery_policy}

verification_labels:
  observed: verified directly in the current session
  unknown: not yet determined from currently available evidence
  reported: supported by prior evidence, not re-verified
  blocked: verification attempted but prevented
  assumed: temporary working assumption
  stale: previously verified but no longer fresh
  invalid: known false or superseded

current_state:
  execution_mode:
    status: observed
    mode: bootstrap

  quality_gates:
    status: not_run
    product_quality_gate: not_run
    runtime_truth_gate: not_run
    live_canary_gate: not_applicable
    redteam_gate: not_run
    known_bad_events_gate: not_run
    git_safety_gate:
      status: not_run
      script: scripts/statedd_git_safety_check.py
      effective_mode: read_only_until_preflight

  runtime_truth:
    status: unknown
    repo_truth_is_not_runtime_truth_rule: active

  known_bad_events:
    status: none_recorded

  open_p0_failures: []

  closure_blockers: []

  residual_risks: []

  repository:
    canonical_path: {json.dumps(repo_scan.canonical_path)}
    path_status: observed
    branch: {branch}
    head: {head}
    inventory: docs/BOOTSTRAP_INVENTORY.yaml

  operating_mode:
    status: observed
    mode: bootstrap

  project:
    name: {json.dumps(project_name)}
    type: {json.dumps(repo_scan.project_type)}
    lifecycle_stage: bootstrap
    truth_summary: {json.dumps(repo_scan.project_summary)}
    profile: {profile}
    profile_summary: {json.dumps(profile_summary(profile))}

  runtime_identity:
    status: unknown
    artifact_contract: runtime_identity.json
    helper: {runtime_helper}

  evidence:
    status: active
    ledger: docs/EVIDENCE_LOG.md
    acceptance_freezes: docs/ACCEPTANCE_FREEZES.md
    artifact_root: docs/evidence
    standard: browser_verification_or_test_output_for_user_facing_claims

active_problems: []
"""


def render_bootstrap_inventory(repo_scan: RepoScan, stamp: str) -> str:
    def block(items: list[str]) -> str:
        if not items:
            return " []"
        return "\n" + "\n".join(f"    - {json.dumps(item)}" for item in items)

    return f"""# BOOTSTRAP_INVENTORY.yaml - Repo detail loaded only when needed

metadata:
  captured_at: {stamp}
  status: observed

repository:
  top_level_entries:{block(repo_scan.top_level_entries)}
  manifests:{block(repo_scan.manifests)}
  entrypoints:{block(repo_scan.entrypoints)}
  test_setup:{block(repo_scan.test_setup)}
  deployment_assumptions:{block(repo_scan.deployment_assumptions)}
  contradictions:{block(repo_scan.contradictions)}
"""


def render_project_dna(project_name: str) -> str:
    return f"""# PROJECT_DNA.yaml - Canonical architecture blueprint

version: "{TEMPLATE_VERSION}"
schema_version: "1.0"

product:
  name: {json.dumps(project_name)}
  one_sentence: "Project using the {TEMPLATE_NAME} workflow."

truth_rules:
  contract_files:
    agents: AGENTS.md
    status: STATUS.md
    project_state: PROJECT_STATE.yaml
    project_dna: PROJECT_DNA.yaml
    next_actions: NEXT_ACTIONS.md
    backlog: BACKLOG.md
    worklog: WORKLOG.md

  hard_rules:
    - no_fake_completeness
    - no_history_in_live_state
    - evidence_required_for_user_facing_claims
    - runtime_identity_required_for_user_facing_acceptance
    - quality_gates_required_for_user_or_operator_facing_closure
    - bad_events_become_incidents_and_regression_fixtures
    - repo_truth_and_runtime_truth_are_separate
    - handoffs_are_claims_not_verified_truth
    - negative_search_results_do_not_prove_nonexistence
    - active_queue_remains_short

architecture:
  state: PROJECT_STATE.yaml is canonical current truth
  evidence: artifacts prove claims across truth boundaries
  history: WORKLOG.md records completed work

invariants:
  - "STATUS.md stays short and current."
  - "PROJECT_STATE.yaml stores structured live truth only."
  - "PROJECT_DNA.yaml changes slowly."
  - "NEXT_ACTIONS.md contains open work only."
  - "BACKLOG.md assigns stable backlog IDs."
  - "Accepted user-facing milestones are frozen to source, runtime, and evidence."
  - "WORKLOG.md is append-only."
  - "Implemented, validated, closure-grade, and accepted are distinct states."
  - "A slice cannot close only because its own checklist passed."
  - "P0 product behavior failures trigger quality_freeze or incident_response until the freeze condition is addressed."
  - "Non-trivial fixes name and test a durable anti-brittleness invariant."

governance:
  hygiene_check: scripts/check_state_docs.py
  schema_validation: scripts/statedd_validate_schema.py
  quality_gate: scripts/statedd_quality_gate.py
"""


def render_project_adapter(project_name: str, profile: str = "team") -> str:
    return f"""# PROJECT_ADAPTER.yaml - Optional project-specific adapter

version: "{TEMPLATE_VERSION}"

project:
  name: {json.dumps(project_name)}
  short_name: {json.dumps(project_name)}
  description: "Optional adapter layer for project-specific vocabulary and runtime details."
  profile: {profile}
  repo_role: downstream_project
  statedd_mode: bootstrap

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


def render_new_next_actions(human_timestamp: str, profile: str = "team") -> str:
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


def render_adopt_next_actions(human_timestamp: str, profile: str = "team") -> str:
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


def render_new_backlog(project_name: str, today: str, profile: str = "team") -> str:
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

## Profile

Initialized with profile: `{profile}` — {profile_summary(profile)}

## WATCHLIST

- Queue bloat.
- Unverified claims.
- Premature operating-mode transition.
- No feature backlog item may be selected while `execution_mode` is `quality_freeze`, unless it directly closes the freeze condition.
- Closure evidence must prove product/runtime truth where applicable, not only command execution or handoff claims.
"""


def render_adopt_backlog(project_name: str, today: str, profile: str = "team") -> str:
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

## Profile

Adopted with profile: `{profile}` — {profile_summary(profile)}

## WATCHLIST

- Silent overwrite of existing project docs.
- Treating inherited claims as facts without direct verification.
- Queue items that are not linked to a backlog ID.
- No feature backlog item may be selected while `execution_mode` is `quality_freeze`, unless it directly closes the freeze condition.
- Closure evidence must prove product/runtime truth where applicable, not only command execution or handoff claims.
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
  Type: implementation | test | product_behavior | runtime_truth | adversarial | known_bad_event | post_deploy | security_privacy | state_update | docs-render-verification
  as_of: 2026-03-18T18:00:00+01:00
  Notes: optional context
```

## Guidance

- Link evidence to the specific claim it supports.
- Prefer durable artifact paths.
- Place saved artifacts under `docs/evidence/YYYY-MM-DD-<slug>/` when possible.
- Add timestamps for anything that may become stale.
- Treat handoffs as claims; link them to evidence or gate results before accepting closure.
- For user-facing or operator-facing work, prefer product behavior, runtime truth, adversarial, known bad event, and post-deploy evidence over command output alone.
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


def render_downstream_readme(project_name: str, profile: str) -> str:
    proposed_merge_mode = recommended_merge_mode(profile)
    return f"""# {project_name}

This repository uses StateDD `{TEMPLATE_VERSION}` with the `{profile}` profile.
StateDD files coordinate current truth, a short queue, evidence, and executable
gates; they do not define this project's product behavior.

## Start

1. Read `AGENTS.md` and follow its declared task-scoped read order.
2. Replace bootstrap unknowns with observed project/runtime truth.
3. Review the proposed `{proposed_merge_mode}` merge mode and explicitly confirm
   either `human_merge` or `agent_after_green` once during structured bootstrap.
   A pending proposal is not merge authorization.
4. Create a real queue linked to `BACKLOG.md`.
5. Run `python3 scripts/check_state_docs.py --bootstrap-gate` before switching
   from `bootstrap` to `operating`.

## Daily Checks

```bash
python3 scripts/check_state_docs.py
python3 scripts/statedd_validate_schema.py
python3 scripts/statedd_quality_gate.py --gate-level 1
```

## Git Safety

Before editing an existing repository, run one fail-closed preflight:

```bash
python3 scripts/statedd_git_safety_check.py --mode normal_branch
```

Use full clones for containers or independent agents. Linked worktrees require
explicit trusted-local same-identity opt-in. A failed writable preflight means
diagnosis only until repair and an explicit `--restart-session` succeed.

## Delivery Policy

`human_merge` keeps merge as a human operation. Confirmed `agent_after_green`
lets the coding agent own exact-head squash merge and post-merge verification
after every configured review, evidence, remote-closure, and CI condition passes.
The agent never infers a CI-unavailable override, changes the confirmed mode, or
deletes the remote slice branch before verified main closure. Final product
acceptance remains human in either mode.

`STATEDD_ASSETS.json` records the exact workflow files installed for this
profile. Template-maintenance tests, fixtures, evidence, incidents, and release
history are intentionally excluded.
"""


def render_coding_agent_startup_prompt() -> str:
    return render_coding_agent_control()


def render_downstream_workflow(profile: str = "team") -> str:
    return render_workflow_control(profile_gate_level(profile))


PROJECT_TRUTH_ASSETS = {
    "AGENTS.md",
    "STATUS.md",
    "PROJECT_STATE.yaml",
    "PROJECT_DNA.yaml",
    "PROJECT_ADAPTER.yaml",
    "NEXT_ACTIONS.md",
    "BACKLOG.md",
    "README.md",
}
APPEND_ONLY_ASSETS = {
    "WORKLOG.md",
    "docs/EVIDENCE_LOG.md",
    "docs/ACCEPTANCE_FREEZES.md",
}
GENERATED_CONTROL_ASSETS = {
    ".github/workflows/statedd-validate.yml",
    "prompts/CODING_AGENT_STARTUP_PROMPT.md",
    "STATEDD_ASSETS.json",
}
SCHEMA_BY_ASSET = {
    "PROJECT_STATE.yaml": "schemas/project_state.schema.json",
    "PROJECT_DNA.yaml": "schemas/project_dna.schema.json",
    "PROJECT_ADAPTER.yaml": "schemas/project_adapter.schema.json",
    "STATEDD_ASSETS.json": "schemas/statedd_assets.schema.json",
}


def _sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _lifecycle_record(
    path: str,
    *,
    lifecycle_class: str,
    content_hash: str | None,
    desired_by: list[str],
    generated_by: str,
) -> dict[str, object]:
    defaults = PROFILE_CATALOG["lifecycle_defaults"][lifecycle_class]
    return {
        "path": path,
        **defaults,
        "schema": SCHEMA_BY_ASSET.get(path),
        "generated_by": generated_by,
        "desired_by": sorted(desired_by),
        "base_sha256": content_hash,
        "installed_sha256": content_hash,
    }


def add_asset_manifest(
    managed_files: dict[str, str],
    asset_paths: list[Path],
    *,
    profile: str,
    generation_mode: str,
    optional_asset_sets: tuple[str, ...] = (),
) -> None:
    manifest_path = "STATEDD_ASSETS.json"
    overlap = {path.as_posix() for path in asset_paths} & set(managed_files)
    if overlap:
        raise SystemExit(
            f"Profile copy assets overlap generated/project-owned paths: {sorted(overlap)}"
        )
    resolved = resolve_profile(
        PROFILE_CATALOG,
        profile,
        optional_asset_sets=optional_asset_sets,
    )
    asset_set_by_path: dict[str, list[str]] = {}
    for set_id in PROFILE_CATALOG["asset_sets"]:
        for raw in PROFILE_CATALOG["asset_sets"][set_id]["assets"]:
            asset_set_by_path.setdefault(raw, []).append(set_id)

    records: list[dict[str, object]] = []
    for path in asset_paths:
        rel = path.as_posix()
        source = regular_source_path(TEMPLATE_ROOT, path)
        records.append(
            _lifecycle_record(
                rel,
                lifecycle_class="template_asset",
                content_hash=_sha256_bytes(source.read_bytes()),
                desired_by=asset_set_by_path.get(rel, []),
                generated_by=f"copy:{rel}",
            )
        )
    for rel, content in managed_files.items():
        if rel == manifest_path:
            continue
        if rel in APPEND_ONLY_ASSETS:
            lifecycle_class = "append_only"
        elif rel in GENERATED_CONTROL_ASSETS:
            lifecycle_class = "generated"
        else:
            lifecycle_class = "project_truth"
        records.append(
            _lifecycle_record(
                rel,
                lifecycle_class=lifecycle_class,
                content_hash=_sha256_bytes(content.encode("utf-8")),
                desired_by=[f"profile:{profile}"],
                generated_by=f"scripts/init_template.py:{generation_mode}",
            )
        )
    records.append(
        _lifecycle_record(
            manifest_path,
            lifecycle_class="generated",
            content_hash=None,
            desired_by=[f"profile:{profile}"],
            generated_by="scripts/init_template.py:add_asset_manifest",
        )
    )
    records.sort(key=lambda record: str(record["path"]))
    catalog_path = TEMPLATE_ROOT / "profiles" / "catalog.json"
    payload = {
        "schema": "statedd.runtime_assets.v2",
        "template_version": TEMPLATE_VERSION,
        "template_commit": clean_git_head(TEMPLATE_ROOT),
        "catalog": {
            "schema": PROFILE_CATALOG["schema"],
            "version": PROFILE_CATALOG["catalog_version"],
            "sha256": _sha256_bytes(catalog_path.read_bytes()),
        },
        "profile": profile,
        "profile_dependencies": list(resolved.profile_dependencies),
        "asset_sets": list(resolved.asset_sets),
        "capabilities": list(resolved.capabilities),
        "validations": list(resolved.validations),
        "required_gate_level": resolved.required_gate_level,
        "generation_mode": generation_mode,
        "managed_assets": records,
        "retired_assets": [],
        "upgrade_history": [],
        "excluded_classes": [
            "template_tests",
            "fixtures",
            "template_evidence",
            "incident_history",
            "release_history",
            "maintenance_changelog",
        ],
    }
    schema = load_schema(TEMPLATE_ROOT / "schemas" / "statedd_assets.schema.json")
    issues = validate_json_schema(payload, schema)
    if issues:
        details = "; ".join(f"{issue.path}: {issue.message}" for issue in issues[:8])
        raise SystemExit(f"Generated STATEDD_ASSETS.json violates its schema: {details}")
    paths = [str(record["path"]) for record in records]
    if len(paths) != len(set(paths)):
        raise SystemExit("Generated STATEDD_ASSETS.json contains duplicate managed paths")
    managed_files[manifest_path] = json.dumps(payload, indent=2, sort_keys=True) + "\n"


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
    try:
        return normalize_relative_path(relpath)
    except UnsafePathError as exc:
        raise SystemExit(str(exc)) from exc


def reject_symlink_components(root: Path, relpath: Path) -> None:
    try:
        confined_path(root, relpath)
    except UnsafePathError as exc:
        raise SystemExit(str(exc)) from exc


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


def atomic_replace_bytes(path: Path, content: bytes, *, mode: int) -> None:
    """Replace one destination inode atomically without mutating hard-link peers."""
    descriptor, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(tmp_path, mode)
        os.replace(tmp_path, path)
        # Persist the directory entry where the platform permits directory fsync.
        try:
            directory_fd = os.open(path.parent, os.O_RDONLY)
        except OSError:
            directory_fd = None
        if directory_fd is not None:
            try:
                os.fsync(directory_fd)
            except OSError:
                pass
            finally:
                os.close(directory_fd)
    finally:
        tmp_path.unlink(missing_ok=True)


def write_file(root: Path, relpath: str | Path, content: str) -> None:
    path = prepare_destination(root, relpath)
    if path.is_dir():
        raise SystemExit(f"Refusing to replace directory with file: {relpath}")
    mode = path.stat().st_mode & 0o777 if path.exists() else 0o644
    atomic_replace_bytes(path, content.encode("utf-8"), mode=mode)


def copy_file(source: Path, target: Path, relpath: Path) -> None:
    normalized = normalize_managed_relpath(relpath)
    try:
        source_path = regular_source_path(source, normalized)
    except UnsafePathError as exc:
        raise SystemExit(str(exc)) from exc
    destination = prepare_destination(target, normalized)
    source_stat = source_path.stat()
    atomic_replace_bytes(
        destination,
        source_path.read_bytes(),
        mode=source_stat.st_mode & 0o777,
    )


def should_ignore_path(path: Path) -> bool:
    return any(part in IGNORED_TEMPLATE_NAMES for part in path.parts)


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


def clean_git_head(root: Path) -> str | None:
    """Return HEAD only when it honestly identifies every working-tree source byte."""
    try:
        status = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=all"],
            cwd=root,
            capture_output=True,
            text=True,
            check=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None
    if status.stdout.strip():
        return None
    return run_git(["rev-parse", "HEAD"], root)


def initialize_fresh_git(target: Path) -> None:
    """Initialize a downstream repository on a fresh main branch."""
    git_metadata = target / ".git"
    if path_exists_for_write(git_metadata):
        raise SystemExit(
            "Refusing to initialize a new project over existing Git metadata. "
            "Use an empty target or the `adopt` command."
        )
    try:
        completed = subprocess.run(
            ["git", "init", "-b", "main"],
            cwd=target,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise SystemExit(f"Git is required to initialize a fresh downstream repository: {exc}") from exc
    if completed.returncode != 0:
        raise SystemExit(
            "Fresh Git initialization failed: "
            f"{completed.stderr.strip() or completed.stdout.strip() or 'unknown error'}"
        )


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
    try:
        package_json = confined_path(target, "package.json")
    except UnsafePathError:
        package_json = None
    if package_json is not None and package_json.is_file() and not package_json.is_symlink():
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
        try:
            path = confined_path(target, candidate)
        except UnsafePathError:
            continue
        if path.is_file() and not path.is_symlink():
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
        canonical_path=".",
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


def find_conflicting_template_paths(target: Path, asset_paths: list[Path]) -> list[Path]:
    return sorted(relpath for relpath in asset_paths if path_exists_for_write(target / relpath))


def preflight_materialization(
    source_root: Path,
    target: Path,
    asset_paths: list[Path],
    managed_paths: list[Path],
) -> None:
    """Validate every source and destination before the first materialization write."""
    def validate_destination_parents(destination: Path, relpath: Path) -> None:
        current = target
        for part in relpath.parts[:-1]:
            current = current / part
            if current.exists() and not current.is_dir():
                raise SystemExit(
                    f"Refusing managed asset beneath non-directory destination parent: {current}"
                )

    for relpath in asset_paths:
        try:
            regular_source_path(source_root, relpath)
            destination = confined_path(target, relpath)
        except UnsafePathError as exc:
            raise SystemExit(str(exc)) from exc
        validate_destination_parents(destination, relpath)
        if destination.exists() and not destination.is_file():
            raise SystemExit(f"Refusing non-file destination for managed asset: {relpath}")
    for relpath in managed_paths:
        try:
            destination = confined_path(target, relpath)
        except UnsafePathError as exc:
            raise SystemExit(str(exc)) from exc
        validate_destination_parents(destination, relpath)
        if destination.exists() and not destination.is_file():
            raise SystemExit(f"Refusing non-file destination for managed asset: {relpath}")


def _restore_file_bytes(path: Path, content: bytes, mode: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.rollback.", dir=path.parent)
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(tmp_path, mode)
        os.replace(tmp_path, path)
    finally:
        tmp_path.unlink(missing_ok=True)


@contextmanager
def materialization_transaction(target: Path, relpaths: list[Path]):
    """Rollback all template/managed writes if any materialization step fails."""
    normalized = sorted(
        {normalize_managed_relpath(path) for path in relpaths},
        key=lambda path: path.as_posix(),
    )
    target_existed = target.exists()
    snapshots: dict[Path, tuple[bytes, int] | None] = {}
    parent_existed: dict[Path, bool] = {}
    for relpath in normalized:
        destination = confined_path(target, relpath)
        if os.path.lexists(destination):
            if destination.is_symlink() or not destination.is_file():
                raise SystemExit(f"Refusing non-file destination for managed asset: {relpath}")
            snapshots[destination] = (
                destination.read_bytes(),
                destination.stat().st_mode & 0o777,
            )
        else:
            snapshots[destination] = None
        current = destination.parent
        while current != target.parent and current != target:
            parent_existed.setdefault(current, current.exists())
            current = current.parent

    try:
        yield
    except BaseException:
        rollback_errors: list[str] = []
        for destination, snapshot in reversed(list(snapshots.items())):
            try:
                if snapshot is None:
                    if destination.is_file() and not destination.is_symlink():
                        destination.unlink()
                else:
                    _restore_file_bytes(destination, snapshot[0], snapshot[1])
            except OSError as exc:
                rollback_errors.append(f"{destination}: {exc}")
        for directory, existed in sorted(
            parent_existed.items(), key=lambda item: len(item[0].parts), reverse=True
        ):
            if existed:
                continue
            try:
                directory.rmdir()
            except OSError:
                pass
        if not target_existed:
            try:
                target.rmdir()
            except OSError:
                pass
        if rollback_errors:
            raise RuntimeError(f"initializer failed and rollback was incomplete: {rollback_errors}")
        raise
def copy_template_tree(
    template_root: Path,
    target: Path,
    asset_paths: list[Path],
    *,
    managed_paths: list[Path],
    overwrite: bool,
    force_overwrite: bool,
    dry_run: bool,
) -> None:
    preflight_materialization(template_root, target, asset_paths, managed_paths)
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
        conflicts = find_conflicting_template_paths(target, [*asset_paths, *managed_paths])
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
        for relpath in asset_paths:
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
    managed_paths: list[Path] | None = None,
    overwrite: bool,
    force_overwrite: bool,
    dry_run: bool,
) -> None:
    preflight_materialization(TEMPLATE_ROOT, target, relpaths, managed_paths or [])
    actions, conflicts = plan_asset_actions(relpaths, target, overwrite=overwrite, force_overwrite=force_overwrite)
    if managed_paths:
        _, managed_conflicts = plan_asset_actions(
            managed_paths,
            target,
            overwrite=overwrite,
            force_overwrite=force_overwrite,
        )
        conflicts.extend(managed_conflicts)
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
    for relpath in managed_files:
        try:
            confined_path(target, relpath)
        except UnsafePathError as exc:
            raise SystemExit(str(exc)) from exc
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


def build_managed_files_for_new(project_name: str, target: Path, today: str, stamp: str, human_timestamp: str, profile: str = "team") -> dict[str, str]:
    asset_paths = assets_for_profile(profile)
    top_level_entries = sorted(
        {path.parts[0] for path in asset_paths}
        | {
            ".github",
            "AGENTS.md",
            "BACKLOG.md",
            "NEXT_ACTIONS.md",
            "PROJECT_ADAPTER.yaml",
            "PROJECT_DNA.yaml",
            "PROJECT_STATE.yaml",
            "README.md",
            "STATUS.md",
            "STATEDD_ASSETS.json",
            "WORKLOG.md",
            "docs",
            "prompts",
        }
    )
    repo_scan = RepoScan(
        canonical_path=".",
        branch=None,
        head=None,
        top_level_entries=top_level_entries,
        manifests=["README.md", "STATEDD_ASSETS.json", "VERSION"],
        entrypoints=[
            "scripts/check_state_docs.py",
            "scripts/statedd_version_check.py",
            "scripts/statedd_validate_schema.py",
            "scripts/statedd_quality_gate.py",
        ],
        test_setup=[
            "project test setup not yet discovered",
        ],
        deployment_assumptions=["deployment target not yet proven"],
        contradictions=["project-specific contradictions not yet investigated"],
        project_summary="bootstrap_initializing",
        project_type="project_template",
    )
    return {
        "AGENTS.md": render_agents_template(today, "bootstrap", profile=profile),
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
            profile=profile,
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
            profile=profile,
        ),
        "PROJECT_DNA.yaml": render_project_dna(project_name),
        "PROJECT_ADAPTER.yaml": render_project_adapter(project_name, profile=profile),
        "README.md": render_downstream_readme(project_name, profile),
        "NEXT_ACTIONS.md": render_new_next_actions(human_timestamp, profile=profile),
        "BACKLOG.md": render_new_backlog(project_name, today, profile=profile),
        "WORKLOG.md": render_worklog(today, "new"),
        "docs/EVIDENCE_LOG.md": render_evidence_log(today, "new"),
        "docs/ACCEPTANCE_FREEZES.md": render_acceptance_freezes(),
        "docs/BOOTSTRAP_INVENTORY.yaml": render_bootstrap_inventory(repo_scan, stamp),
        "docs/evidence/.gitkeep": "",
        "prompts/CODING_AGENT_STARTUP_PROMPT.md": render_coding_agent_startup_prompt(),
        ".github/workflows/statedd-validate.yml": render_downstream_workflow(profile),
    }


def build_managed_files_for_adopt(project_name: str, target: Path, today: str, stamp: str, human_timestamp: str, profile: str = "team") -> dict[str, str]:
    repo_scan = scan_repo(target)
    return {
        "AGENTS.md": render_agents_template(today, "bootstrap", profile=profile),
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
            profile=profile,
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
            profile=profile,
        ),
        "PROJECT_DNA.yaml": render_project_dna(project_name),
        "PROJECT_ADAPTER.yaml": render_project_adapter(project_name, profile=profile),
        "NEXT_ACTIONS.md": render_adopt_next_actions(human_timestamp, profile=profile),
        "BACKLOG.md": render_adopt_backlog(project_name, today, profile=profile),
        "WORKLOG.md": render_worklog(today, "adopt"),
        "docs/EVIDENCE_LOG.md": render_evidence_log(today, "adopt"),
        "docs/ACCEPTANCE_FREEZES.md": render_acceptance_freezes(),
        "docs/BOOTSTRAP_INVENTORY.yaml": render_bootstrap_inventory(repo_scan, stamp),
        "docs/evidence/.gitkeep": "",
        "prompts/CODING_AGENT_STARTUP_PROMPT.md": render_coding_agent_startup_prompt(),
    }


def build_subcommand_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Initialize or adopt the StateDD workflow")
    subparsers = parser.add_subparsers(dest="command", required=True)

    new_parser = subparsers.add_parser("new", help="Create a new repo from the template")
    new_parser.add_argument("--name", required=True, help="Project name to stamp into the template")
    new_parser.add_argument("--target", default=".", help="Repo root to initialize")
    new_parser.add_argument("--profile", default="team", choices=sorted(VALID_PROFILES), help="Adoption profile: minimal, solo, team, or regulated")
    new_parser.add_argument(
        "--asset-set",
        action="append",
        default=[],
        choices=OPTIONAL_ASSET_SETS,
        help="Install an optional catalog asset set; repeat for multiple sets",
    )
    new_parser.add_argument("--minimal", action="store_true", help="Use the core-gates-only footprint (legacy alias for --profile minimal)")
    new_parser.add_argument("--dry-run", action="store_true", help="Preview actions without writing files")
    new_parser.add_argument(
        "--init-git",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Initialize a fresh downstream Git repository on main (default: enabled)",
    )
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
    adopt_parser.add_argument("--profile", default="team", choices=sorted(VALID_PROFILES), help="Adoption profile: minimal, solo, team, or regulated")
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
        "--asset-set",
        action="append",
        default=[],
        choices=OPTIONAL_ASSET_SETS,
        help="Install an optional catalog asset set; repeat for multiple sets",
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
    parser.add_argument("--profile", default="team", choices=sorted(VALID_PROFILES), help="Adoption profile: minimal, solo, team, or regulated")
    parser.add_argument(
        "--asset-set",
        action="append",
        default=[],
        choices=OPTIONAL_ASSET_SETS,
        help="Install an optional catalog asset set; repeat for multiple sets",
    )
    parser.add_argument("--minimal", action="store_true", help="Use the core-gates-only footprint")
    parser.add_argument("--dry-run", action="store_true", help="Preview actions without writing files")
    parser.add_argument(
        "--init-git",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Initialize a fresh downstream Git repository on main (default: enabled)",
    )
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

    now = current_time()
    today = now.date().isoformat()
    stamp = now.isoformat(timespec="seconds")
    human_timestamp = now.strftime("%Y-%m-%d %H:%M %Z")
    profile = validate_profile("minimal" if getattr(args, "minimal", False) else args.profile)
    optional_asset_sets = tuple(sorted(set(getattr(args, "asset_set", []))))
    try:
        target = safe_root_path(
            args.target,
            must_exist=args.command == "adopt",
        )
    except UnsafePathError as exc:
        raise SystemExit(str(exc)) from exc

    if args.command == "new":
        if target == TEMPLATE_ROOT:
            raise SystemExit(
                "Refusing to initialize into the template root itself. "
                "Choose a different target directory."
            )
        asset_paths = assets_for_profile(profile, optional_asset_sets=optional_asset_sets)
        managed_files = build_managed_files_for_new(args.name, target, today, stamp, human_timestamp, profile=profile)
        add_asset_manifest(
            managed_files,
            asset_paths,
            profile=profile,
            generation_mode="new",
            optional_asset_sets=optional_asset_sets,
        )
        transaction = (
            nullcontext()
            if args.dry_run
            else materialization_transaction(
                target, [*asset_paths, *(Path(path) for path in managed_files)]
            )
        )
        with transaction:
            copy_template_tree(
                TEMPLATE_ROOT,
                target,
                asset_paths,
                managed_paths=[Path(path) for path in managed_files],
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

        if args.dry_run:
            print("Dry run complete.")
            return 0

        if getattr(args, "init_git", True):
            initialize_fresh_git(target)

        print(f"Initialized {TEMPLATE_NAME} repo")
        print(f"Target: {target}")
        print("Mode: bootstrap")
        print(f"Profile: {profile} ({len(asset_paths) + len(managed_files)} declared assets)")
        if (target / ".git").is_dir():
            print("Fresh Git repository: main (template history was not inherited)")
        print("Next:")
        print("1. Read README.md and AGENTS.md")
        print("2. Fill bootstrap truth and create a real backlog-linked queue")
        print(f"3. Run {Path(sys.executable).name} scripts/statedd_quality_gate.py --gate-level 1")
        print(f"4. Run {Path(sys.executable).name} scripts/check_state_docs.py --bootstrap-gate before operating mode")
        return 0

    if not target.exists() or not target.is_dir():
        raise SystemExit("Adoption target must be an existing repo directory.")

    managed_files = build_managed_files_for_adopt(args.name, target, today, stamp, human_timestamp, profile=profile)
    resolved_profile = resolve_profile(PROFILE_CATALOG, profile)
    selected_optional_sets = set(args.asset_set)
    if args.install_github_assets:
        if "github" not in PROFILE_CATALOG["asset_sets"] or PROFILE_CATALOG["asset_sets"]["github"].get("optional") is not True:
            raise SystemExit("legacy --install-github-assets alias is unavailable in this catalog")
        selected_optional_sets.add("github")
    optional_asset_sets = tuple(sorted(selected_optional_sets))
    support_paths = assets_for_profile(profile, optional_asset_sets=optional_asset_sets)
    if selected_optional_sets or "remote_closure_contract" in resolved_profile.validations:
        managed_files[".github/workflows/statedd-validate.yml"] = render_downstream_workflow(profile)
    add_asset_manifest(
        managed_files,
        support_paths,
        profile=profile,
        generation_mode="adopt",
        optional_asset_sets=optional_asset_sets,
    )
    if args.readme_link:
        validate_readme_link_target(target)

    transaction_paths = [*support_paths, *(Path(path) for path in managed_files)]
    if args.readme_link:
        transaction_paths.append(Path("README.md"))
    transaction = (
        nullcontext()
        if args.dry_run
        else materialization_transaction(target, transaction_paths)
    )
    with transaction:
        copy_assets(
            support_paths,
            target,
            managed_paths=[Path(path) for path in managed_files],
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
    print(f"Profile: {profile} ({len(support_paths) + len(managed_files)} declared assets)")
    print("README behavior: existing README preserved")
    if args.readme_link:
        print("README behavior: appended workflow section")
    if selected_optional_sets:
        print(f"Optional asset sets: installed {', '.join(sorted(selected_optional_sets))}")
    else:
        print("Optional asset sets: skipped")
    print("Next:")
    print("1. Read AGENTS.md and review PROJECT_STATE.yaml against the real repo")
    print("2. Resolve inherited contradictions and fill the backlog-linked queue")
    print(f"3. Run {Path(sys.executable).name} scripts/statedd_quality_gate.py --gate-level 1")
    print(f"4. Run {Path(sys.executable).name} scripts/check_state_docs.py --bootstrap-gate before operating mode")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
