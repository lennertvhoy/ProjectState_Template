# Incident: Agent Workspaces Reported Released While Directories Accumulated

**Date:** 2026-07-14
**Severity:** P0
**Status:** resolved
**Related backlog:** [BL-WORKSPACE-LIFECYCLE-001]
**Related failure scan:** `docs/failure_scans/BL-WORKSPACE-LIFECYCLE-001.md`
**Evidence folder:** `docs/evidence/2026-07-14-workspace-lifecycle-closure`

## User/Operator Symptom

- The project parent contained nine visible `StateDD_Template-*` clone directories
  plus five linked worktrees in the canonical checkout.
- Several external finish handoffs claimed `isolation_released: true` and
  `recoverable_state_retained: false`, contradicting the directories still on disk.
- The operator had no single inventory showing which copies were active, stale,
  integrated, dirty, or safe to reconcile.

## Observed Event

- Source: direct filesystem, Git topology, reflog, agent-context, patch-ID, and
  external handoff inspection on 2026-07-14.
- Creator provenance: all nine archived clone reflogs identify
  `Hermes Agent <hermes@ff-fedora.local>` and clone creation on 2026-07-10 through
  2026-07-12.
- Recursive chains were proven by agent contexts:
  - canonical → integration clone → OKF clone;
  - golden-path clone → managed duplicate → finish-delete repair clone → CTO
    acceptance clone.
- The archived clone and linked-worktree feature reconciliation is recorded in
  `docs/evidence/2026-07-14-workspace-lifecycle-closure/clone_audit.json`.
- The nine visible clone directories were moved, without deletion, to
  `/home/ff/Documents/Projects/_archive/StateDD_Template-clones-20260714` before
  implementation began.

## Confirmed Root Cause

1. `statedd_agent_worktree.py handoff --release --validated` deleted only a
   worktree reservation ref and explicitly retained the isolation directory.
2. `statedd_finish_slice.py` treated that command's zero exit as physical cleanup
   and unconditionally wrote `isolation_released: true` and
   `recoverable_state_retained: false`.
3. Provisioning accepted arbitrary `--target` paths and did not reject a source
   repository that was itself an agent clone, allowing clone-of-clone recursion.
4. Cleanup was report-only and handoff did not inventory same-origin sibling
   clones, so retained directories were never promoted back into operator-visible
   truth.
5. Tests verified call order and reported booleans, but never asserted that the
   exact original isolation path was absent.
6. A failed finish preflight initially had no truthful cleanup command for its
   clean managed clone; explicit recoverable `abandon` now closes that path
   without claiming post-merge validation.

This was a workflow and state-truth defect, not a Git feature integration gap.

## Suspected Failure Class

- `workflow`
- `state_truth`
- `observability`
- `brittleness`

## Missing Invariant

- Agent workspaces have one centrally managed, non-recursive lifecycle.
- `HANDOFF_COMPLETE` is impossible unless a closed-world release receipt is bound
  to the validated branch, HEAD, and original path and direct inspection proves
  that original path is absent.
- Dirty, malformed, or unproven state is retained without force.

## Regression Fixture

- Path: `scripts/test_agent_worktree.py`, `scripts/test_finish_slice.py`,
  `scripts/test_handoff.py`, `scripts/test_quality_gate.py`, and
  `scripts/test_closure_check.py`
- Status: present_valid; level-2, exact-head PR, merge-candidate, and direct-main
  CI all pass
- Abort-path status: clean abandon quarantine and dirty abandon retention pass
  focused regressions

## Runtime/Live Proof

- Required: no
- Artifact: `docs/evidence/2026-07-14-workspace-lifecycle-closure/runtime_identity.json`
- Status: not_applicable; this repository has no application runtime

## Adjacent Cases Checked

- Nested agent provisioning, arbitrary sibling targets, unmanaged same-origin
  siblings, equivalent Git URL transports/credentials, dirty clone retention,
  clean clone quarantine, clean opted-in worktree removal without force,
  reservation absence, malformed/unproven finish receipts, check functions that
  return false without diagnostics, and incidental evidence selection.

## Closure Conditions

- All archived clone work is proven integrated or intentionally not integrated.
- All workspace lifecycle regressions and full repository/profile gates pass. (met locally)
- Generated downstream profiles contain the inventory dependency and lifecycle
  invariant.
- Exact-head PR, branch-head and merge-candidate CI, merge, direct-main CI, and
  external finish handoff agree.
- The release sidecar proves the repair workspace's original path absent.

## Residual Risk

- Raw `git clone` cannot be globally prohibited outside StateDD. It is detected at
  the next managed start and every handoff when it appears as an immediate
  same-origin sibling.
- The dirty BL-BROWSER-002 worktree remains preserved and is not merged because
  its provider assertions and artifact-redaction behavior require redesign.
- The repair self-verified the new lifecycle: its managed clone was quarantined,
  the exact original active path is absent, and the release receipt is durable.
