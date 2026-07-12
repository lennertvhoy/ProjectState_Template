# NEXT_ACTIONS - Active Execution Queue

**Updated At:** 2026-07-12
**Execution Mode:** quality_freeze
**Max Items:** 10

## Active Work

### P1 [BL-OKF-001] Measure OKF task-context value
Owner: integration agent
Next: design benchmark-backed StateIR/StatePack retrieval experiments; do not make OKF installation mandatory yet.
Exit: deterministic task selection, provenance manifests, context-cost measurements, and a justified default-profile decision.

### P0 [BL-STATEDD-INTEGRATION-001] Merged StateDD integration baseline
Owner: integration agent
Next: preserve the merged mainline; retain PR #6 and PR #7 only as superseded historical candidates.
Exit: main remains green and no obsolete candidate branch is merged independently.

## Source candidates

- PR #6 / `bl-max-value-001`: `84a67100fee324f6716a5c966500b0c0eeb59699`; lifecycle/profile/gate/evidence authority.
- PR #7 / `bl-git-isolation-001`: `99f401110d9c5d130e8524d1cca4873649a84cbe`; Git-safety and coding-agent golden-path candidate.
- Neither source PR is independently merge-ready; license ownership and benchmark superiority remain unproven.

## Queue Rules

- Keep this file short.
- List only active, open work.
- Remove completed items immediately.
- Every active item must reference a backlog ID like `[BL-001]`.
- Include owner, next action, and exit criteria when items exist.
