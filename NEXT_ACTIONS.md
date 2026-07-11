# NEXT_ACTIONS - Active Execution Queue

**Updated At:** 2026-07-11
**Execution Mode:** quality_freeze
**Max Items:** 10

## Active Work

### P1 [BL-OKF-001] Optional OKF knowledge interoperability
Owner: integration agent
Next: run remote-mutation safety preflight, push `bl-okf-001`, open one separate draft PR, and observe branch-head versus merge-candidate CI.
Exit: optional generated profile passes OKF/base-format and StateDD governance checks; minimal/solo/team footprints and startup context remain unchanged.

### P0 [BL-STATEDD-INTEGRATION-001] Superseding StateDD integration
Owner: integration agent
Next: review draft PR #8 with the successful direct branch-head and synthetic merge-candidate CI results; resolve ownership and human-acceptance boundaries before any merge decision.
Exit: authoritative local gates, generated-profile conformance, strict evidence, clean pushed branch, and a draft PR exist with branch-head and merge-candidate CI reported separately.

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
