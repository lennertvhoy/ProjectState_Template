# Design: StateDD Parallel-Agent Worktree Orchestrator

> **Superseded on 2026-07-11 by ADR-0001 / BL-GIT-ISOLATION-001.** This document
> is retained as design history. Its worktree-default and automatic-cleanup
> decisions are no longer authoritative.

**Date:** 2026-07-07  
**Topic:** BL-PARALLEL-001 — first-class support for multiple coding agents working on the same repository without git-state panic.  
**Decision:** Option C — managed agent worktree orchestrator.

## Problem Statement

StateDD currently assumes a single agent owns the worktree during a slice. When two or more agents run concurrently, existing scripts panic (exit non-zero / report "not proven") because:

- `statedd_worktree_guard.py` sees another agent's uncommitted files as ambiguous dirt.
- `statedd_handoff.py` cannot distinguish the current agent's changes from another agent's changes.
- `statedd_audit.py` fails closure-grade on a dirty worktree even when the dirt belongs to the current slice.
- `statedd_remote_closure_finalizer.py` races when another agent pushes to the same branch between checks.
- `latest_evidence_folder` uses `st_mtime`, which races when agents write evidence concurrently.
- There is no reservation system, so agents can accidentally claim the same branch or worktree path.

## Design Goals

1. **No shared-worktree surprises.** Each non-trivial slice runs in its own git worktree + branch by default.
2. **Reservation integrity.** A branch/worktree cannot be silently double-claimed.
3. **Lock awareness.** Detect git lock contention and either wait or fail with a clear message instead of leaving corrupt state.
4. **Truth-boundary preservation.** Handoff/audit/closure still prove repo identity, branch, HEAD, and remote agreement.
5. **Minimal intrusion.** Existing scripts gain agent-context awareness; the orchestrator composes them rather than replacing them.
6. **Template stays a template.** The implementation is generic git-based isolation, not tied to a specific downstream product.

## Core Concepts

### Agent context

A small JSON file `.statedd/agent.context` lives in the root of each agent worktree:

```json
{
  "schema": "statedd.agent_context.v1",
  "agent_id": "agent-7f3a",
  "slice_id": "BL-BROWSER-002",
  "reservation_ref": "refs/statedd/reservations/bl-browser-002-agent-7f3a-abc12",
  "worktree_path": "/home/ff/Documents/Projects/StateDD_Template/.worktrees/bl-browser-002-agent-7f3a-abc12",
  "branch": "bl-browser-002-agent-7f3a-abc12",
  "base_branch": "main",
  "created_at": "2026-07-07T21:30:00+02:00"
}
```

When existing StateDD scripts detect this file, they treat uncommitted changes in the worktree as *intended slice work* rather than ambiguous shared-worktree dirt.

### Reservation ref

Reservations are stored as lightweight git refs under `refs/statedd/reservations/<branch-name>`. Each ref points to the base commit at reservation time and contains the agent context as ref log message / annotation.

Using git refs keeps reservations:
- Inside the repo (no untracked lock files in the main worktree).
- Atomic to create/delete via `git update-ref`.
- Visible to all worktrees sharing the same `.git/`.

### Worktree naming

```
Branch:  bl-<slice-id>-<agent-short-id>-<nonce>
Path:    <repo-root>/.worktrees/<branch>
```

- `slice-id` keeps branches discoverable per backlog item.
- `agent-short-id` is the first 4 chars of the agent UUID.
- `nonce` is a 5-char base36 timestamp fragment to avoid collisions.

Example: `bl-browser-002-a7f3-abc12`.

## New Component: `scripts/statedd_agent_worktree.py`

A CLI orchestrator with these subcommands:

| Subcommand | Purpose |
|------------|---------|
| `start --slice-id BL-XXX [--agent-id id] [--base branch]` | Create branch, worktree, reservation ref, and agent.context. |
| `guard [--mode start-slice\|closure]` | Run worktree guard inside the agent context. |
| `handoff` | Generate handoff snapshot, validate dirty classification, optionally release reservation. |
| `close --pr N` | Push branch, run closure checks + remote closure finalizer, then remove worktree and reservation on success. |
| `cleanup [--stale-only\|--force branch]` | Remove abandoned worktrees and reservation refs safely. |
| `list` | Show active agent worktrees, branches, reservations, lock files. |

### Start flow

1. Validate arguments and that `git worktree` is available.
2. Compute deterministic branch/worktree name; fail if a reservation ref already exists for that branch.
3. Acquire git locks check (`index.lock`, `config.lock`) with optional `--wait`.
4. Create branch from base: `git branch <branch> <base>`.
5. Create worktree: `git worktree add .worktrees/<branch> <branch>`.
6. Write `.statedd/agent.context` inside the worktree.
7. Write reservation ref: `git update-ref refs/statedd/reservations/<branch> <base-commit>` with agent context in message.
8. Print the worktree path and branch.

### Guard flow

1. Load agent.context.
2. Set `GIT_OPTIONAL_LOCKS=0` for read-only status queries.
3. Run equivalent checks to `statedd_worktree_guard.py`, but in agent context:
   - Dirty files are expected; require classification table in evidence README if not classified.
   - Linked worktrees are expected and listed.
   - Shared/default branch warning is suppressed because the agent branch is private.

### Handoff flow

1. Load agent.context.
2. Run `statedd_handoff.py` from inside the worktree.
3. Verify dirty files are classified as `intended_slice_work` or `generated_artifact`.
4. Optionally release reservation ref (default: keep until `close`).

### Close flow

1. Load agent.context.
2. Push branch to origin.
3. Run `statedd_remote_closure_finalizer.py --pr <N>`.
4. On success, remove reservation ref and worktree.
5. On failure, leave worktree intact for debugging and report path.

### Cleanup flow

1. Enumerate `refs/statedd/reservations/` and `git worktree list`.
2. Identify stale reservations (no corresponding worktree or worktree HEAD merged to default branch).
3. For each stale entry, require `--force` or prompt; remove worktree and ref.

## Changes to Existing Scripts

### `scripts/statedd_worktree_guard.py`

- Accept optional `--agent-context <path>`.
- When agent context is present:
  - Skip "shared/default branch" check.
  - Treat uncommitted files as expected slice work; do not fail on unclassified dirt, but warn and require classification table.
  - Report agent_id and slice_id in output.
- Detect git lock files before any mutating git operation and fail fast with message: `Another git operation holds <lock-file>; use --wait or retry.`

### `scripts/statedd_handoff.py`

- Auto-detect agent.context in current worktree root.
- When in agent context, add fields:
  - `agent_id`, `slice_id`, `worktree_path`, `reservation_ref`.
  - `worktree_owner: self` vs `other` (if another agent.context is found in a sibling worktree).
- Continue to report upstream visibility and remote truth.

### `scripts/statedd_audit.py`

- Accept `--agent-context` / auto-detect.
- In agent context:
  - `worktree_clean` check is relaxed to "dirty files are classified as intended_slice_work or generated_artifact".
  - `changed_files_in_slice` uses the agent branch base (from reservation ref or merge-base) instead of the default branch merge-base when the worktree is dirty.
  - `latest_evidence_folder` accepts an explicit `--evidence-folder` override; if not provided, prefers folders whose `manifest.json` matches the current `slice_id` before falling back to mtime.

### `scripts/statedd_remote_closure_finalizer.py`

- Add `--agent-context` / auto-detect.
- In agent context, verify the PR branch matches the agent branch; reject if another agent pushed to a different branch for the same slice.
- Re-check remote HEAD immediately before declaring closure to catch interleaved pushes.

### `scripts/statedd_closure_check.py`

- Accept `--agent-context` / auto-detect.
- In agent context, skip the "dirty worktree" failure if dirt is classified slice work.

## Changes to CI / Workflows

`.github/workflows/validate.yml`:
- Add a job or step that runs `python3 scripts/statedd_agent_worktree.py --dry-run start --slice-id CI-SMOKE-001` to prove the orchestrator works in a fresh checkout.
- Keep existing single-agent validation path unchanged.

## State and Documentation Updates

- `AGENTS.md`: add Parallel-Agent Invariant — non-trivial slices default to agent worktree isolation.
- `BACKLOG.md`: add `BL-PARALLEL-001`.
- `NEXT_ACTIONS.md`: activate `BL-PARALLEL-001`.
- `PROJECT_STATE.yaml`: add `parallel_agent_support` section.
- `docs/failure_scans/BL-PARALLEL-001.md`: document the shared-worktree panic class and mitigations.
- `skills/close-slice/SKILL.md`: update to use `statedd_agent_worktree.py start/close`.
- `prompts/CODING_AGENT_STARTUP_PROMPT.md`: mention worktree orchestrator for parallel slices.

## Testing Strategy

New `scripts/test_agent_worktree.py` with fixtures under `fixtures/parallel_agent_worktree/`:

1. `test_start_creates_worktree_and_reservation`
2. `test_double_reserve_same_branch_fails`
3. `test_guard_passes_in_agent_worktree_with_dirty_files`
4. `test_lock_detection_reports_concurrent_git_operation`
5. `test_handoff_includes_agent_context`
6. `test_close_removes_worktree_and_reservation`
7. `test_cleanup_removes_stale_worktree`
8. `test_existing_audit_passes_in_agent_context`

Regression tests must also prove the existing single-agent path still works when no agent.context is present.

## Anti-Brittleness Review

- The orchestrator must not assume a specific agent platform (Claude Code, Kimi, etc.). It uses git primitives only.
- Lock detection must not delete lock files; it only reports and optionally waits.
- Reservation refs must be cleaned up on both success and failure paths to avoid orphan refs.
- Worktree removal must verify the worktree path is under `<repo-root>/.worktrees/` to prevent accidental deletion.
- The design does not introduce provider-specific behavior, keyword buckets, or brittle prompt strings.

## Migration / Adoption

- Existing single-agent workflows continue unchanged.
- Agent worktree is opt-in via `statedd_agent_worktree.py start` but becomes the recommended default in `skills/close-slice/`.
- Downstream repos that adopt the template receive `scripts/statedd_agent_worktree.py` through `init_template.py` and `statedd_upgrade.py`.

## Open Questions Resolved

- **Why git refs for reservations instead of files?** Refs are atomic, repo-local, and avoid untracked-file races in the main worktree.
- **Why not fix shared-worktree mode instead?** Shared worktrees cannot reliably prove "whose change is whose" at closure; worktree isolation is the simpler and stronger boundary.
- **Why keep agent.context inside the worktree?** It gives every existing script a single file to detect agent mode without passing flags through every call chain.

## Success Criteria

1. Two agents can run `statedd_agent_worktree.py start` for different slices and not collide.
2. An agent can leave dirty files in its worktree and still pass `statedd_audit.py --strict`.
3. `statedd_handoff.py` in an agent worktree reports the correct agent_id, slice_id, and branch.
4. `statedd_remote_closure_finalizer.py` detects if another agent interleaved a push and reports it clearly.
5. All existing single-agent tests continue to pass.
6. CI includes a smoke test of the orchestrator.
