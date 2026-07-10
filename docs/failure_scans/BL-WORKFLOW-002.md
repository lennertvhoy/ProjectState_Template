# Failure Scan: BL-WORKFLOW-002 Worktree Isolation + Anti-Brittleness Guardrails

**Date:** 2026-07-03  
**Slice:** BL-WORKFLOW-002  
**Mode:** template-maintenance

## What Could Go Wrong

- The guard becomes cosmetic prompt wording and does not execute before work.
- The guard blocks legitimate local-only experiments with unnecessary bureaucracy.
- Dirty files are reported but not classified clearly enough for the next agent.
- Handoffs still hide upstream divergence or local-only deliverables.
- The brittleness scan is mistaken for proof of quality.
- Anti-brittleness review devolves into keyword scanning rather than invariant review.

## User Or Operator Impact

- A coding agent could waste a slice in the wrong or dirty worktree.
- A reviewer could see local-only claims that are absent from GitHub.
- A brittle one-example fix could pass closure and fail adjacent cases later.

## Adjacent Failures

- Detached HEAD and missing origin must be reported as `not proven`.
- Linked worktrees must be visible in handoffs.
- Dirty evidence files must be classified like any other dirty file.
- Clean scanner output must explicitly avoid claiming absence of brittleness.

## Missing Invariants

- Non-trivial coding-agent slices start only after worktree/source-of-truth proof.
- Dirty worktree state is classified before implementation.
- Non-trivial fixes/features identify the durable invariant and adjacent coverage.

## Proof Needed

- Worktree guard tests for clean, dirty, classified, closure, detached, missing origin, and linked worktree cases.
- Brittleness scanner tests for warning cases and no-proof language.
- Audit marker tests for anti-brittleness evidence in normal and strict modes.
- Initializer and upgrade tests proving downstream propagation.
- State/schema/hygiene checks and final handoff output.
