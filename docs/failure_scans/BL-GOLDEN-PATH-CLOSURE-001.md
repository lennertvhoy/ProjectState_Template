# Failure Scan: Agent-owned golden-path closure

**Date:** 2026-07-12
**Backlog item:** [BL-GOLDEN-PATH-CLOSURE-001]
**Author:** coding-agent
**Severity:** P0
**Execution mode impact:** quality_freeze

## What Happened Or Could Happen

- The executable close path can prove a PR ready but stops before merge and
  returns routine Git operations to the human.
- Tracked evidence can be asked to predict the squash-merge SHA created only
  after the PR branch is committed.
- Canonical live state can remain green while describing merged work as active.
- A concurrent push, review change, pending check, or dirty merge state could be
  accepted if the merge decision is not re-queried against the exact head.

## How The User Or Operator Would Notice

- The user must click Merge, repair post-merge metadata, rerun metrics, reconcile
  state, close stale PRs, delete branches, or run post-merge verification.
- A second metadata PR appears solely to record identities created by the first.
- `STATUS.md`, `PROJECT_STATE.yaml`, or `NEXT_ACTIONS.md` contradict GitHub truth.

## Likely Adjacent Failures

- Confirmed `human_merge` or an unconfirmed policy accidentally permits automation.
- Draft readiness happens before local proof; requested changes or unresolved
  current review threads are ignored.
- Branch-head or merge-candidate CI is pending, failed, stale, or for another SHA.
- API failure deletes the branch or releases isolation, destroying recovery state.
- Main CI fails after merge but the handoff calls the slice verified.
- A rerun attempts a second merge or creates a different external result.
- Provider-specific output strings or fixed sleeps become the workflow authority.

## Previous Tests That Might Miss This

- Remote-finalizer tests stop at an open clean PR and never exercise merge or main CI.
- Post-merge fixtures can pre-fill an impossible future merge identity.
- State tests check syntax and ID presence without terminal remote semantics.
- Happy-path tests do not move the PR head or review state immediately before merge.

## Global Invariant Needed

- A confirmed delivery policy gates a typed, idempotent state machine that re-queries
  immutable remote truth at every destructive boundary. Tracked proof ends at the
  PR tree; GitHub and an external handoff own identities created after merge.

## Adversarial Case

- Input/event: the PR head changes after CI or an unresolved requested-change
  review appears immediately before merge.
- Expected protected behavior: refuse merge, retain branch and isolation state,
  report the exact observed mismatch, and resume safely after repair.
- Evidence required: deterministic fake-provider regression plus exact-head remote
  proof on the real slice PR.

## Runtime Or Live Proof Required

- Required: no
- Why: the template root has no application runtime; GitHub remote and CI truth are
  the applicable operator boundary.
- Artifact: strict tracked evidence plus external remote-closure handoff.

## Post-Deploy Watch Required

- Required: yes
- Duration or trigger: bounded wait until direct default-branch CI completes.
- Artifact: external handoff containing merge commit, default-branch head, CI run,
  evidence reference, and cleanup outcome.

## Closure Blockers

- Policy schema, bootstrap propagation, finish state machine, future-SHA removal,
  semantic state validation, generated-profile proof, exact-head PR CI, self-merge,
  direct main CI, post-merge verification, and clean isolation must all pass.
