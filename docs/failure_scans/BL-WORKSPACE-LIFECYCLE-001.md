# Failure Scan: Workspace Lifecycle False Cleanup And Clone Proliferation

**Date:** 2026-07-14
**Backlog item:** [BL-WORKSPACE-LIFECYCLE-001]
**Author:** integration coding agent
**Severity:** P0
**Execution mode impact:** quality_freeze

## What Happened Or Could Happen

- A release operation removed metadata but not the isolation directory, while the
  finish state machine reported physical cleanup as complete.
- Existing agent clones could provision more clones, and arbitrary targets placed
  them beside the canonical project.
- Report-only cleanup plus no sibling inventory made accumulation silent.
- A dirty or unique workspace could be deleted if cleanup were generalized without
  exact context, clean-state, and path-binding checks.

## How The User Or Operator Would Notice

- Multiple similarly named repositories appear beside the canonical project.
- Disk use grows after successful slices.
- Finish handoff cleanup fields contradict `git worktree list` or filesystem truth.
- It is unclear which directory owns unique, dirty, or already integrated work.

## Likely Adjacent Failures

- Clone-of-clone and worktree-from-clone recursion.
- Explicit `--target` path escape or sibling placement.
- Equivalent SSH/HTTPS/credential-bearing origin URLs bypassing clone detection.
- Symlinked workspace roots or release paths.
- Dirty/untracked files hidden by a weak porcelain parser.
- Clone quarantine collision or cross-filesystem move.
- Worktree removal succeeding while reservation cleanup fails.
- A malformed release receipt or receipt bound to a different branch/HEAD/path.
- A gate returning false without appending a diagnostic and still being reported
  successful.
- Dirty classification borrowed from an unrelated newest-by-mtime evidence folder.
- Raw/manual clones created outside the managed command path.

## Previous Tests That Might Miss This

- Finish tests asserted only that `release_isolation()` was called after main CI
  and that booleans were written.
- Orchestrator tests explicitly expected cleanup to retain directories.
- No test asserted exact original-path absence after a successful release.
- No test attempted nested provisioning, an arbitrary sibling target, or a manual
  same-origin sibling clone.

## Global Invariant Needed

- Managed workspace creation is centralized, deterministic, outside the project
  parent, and non-recursive.
- A release is a typed physical transition: clean managed clones are atomically
  moved to per-repository quarantine; clean opted-in worktrees are removed through
  normal Git semantics without force; dirty or contradictory state is retained.
- `HANDOFF_COMPLETE` requires a strict receipt plus direct original-path absence.
- Handoff and managed start fail closed on unexpected same-origin sibling clones.

## Adversarial Case

- Input/event: an agent clone with valid context tries to start another clone at a
  user-selected sibling path, then returns a syntactically valid receipt that does
  not prove the original path absent.
- Expected protected behavior: provisioning fails before filesystem mutation;
  finish remains at `MAIN_CI_VERIFIED` and records the release failure.
- Evidence required: filesystem assertions, exact context/path binding, receipt
  schema checks, and an unmanaged-sibling inventory failure.

## Runtime Or Live Proof Required

- Required: no
- Why: the affected behavior is local Git/filesystem orchestration in a template
  repository with no application runtime.
- Artifact: `docs/evidence/2026-07-14-workspace-lifecycle-closure/runtime_identity.json`

## Post-Deploy Watch Required

- Required: yes
- Duration or trigger: the first managed agent slice after merge and the repair
  slice's own final release.
- Artifact: `docs/evidence/2026-07-14-workspace-lifecycle-closure/finish_slice_handoff.json`
  plus `statedd_workspace_inventory.py` output.

## Closure Blockers

- None. Exact-head remote CI, merge, direct-main verification, remote branch
  deletion, and physical original-path absence are proven by the finish receipt.
