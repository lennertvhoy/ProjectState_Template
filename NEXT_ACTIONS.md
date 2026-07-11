# NEXT_ACTIONS - Active Execution Queue

**Updated At:** 2026-07-11
**Execution Mode:** quality_freeze
**Max Items:** 10

## Active Work

### P0 [BL-GIT-ISOLATION-001] Git Metadata Safety Boundary
Owner: coding agent + human reviewer
Next: add the failing permission/identity/synchronization regressions, implement the centralized Git safety preflight and strong clone path, remove automatic force cleanup, and propagate the fail-closed startup contract.
Exit: incident regressions, generated-profile gates, schema validation, final-head GitHub Actions, and remote closure all pass on the same head; only then leave quality freeze.

### P1 [BL-GOLDEN-PATH-001] Coding-agent-first Golden Path
Owner: coding agent
Next: align the landing page, canonical empty-folder prompt, downstream initializer, standing delivery policy, integration-owner workflow, remote-first handoff, and end-to-end regression.
Exit: local initializer/profile/schema checks and the golden-path regression pass; remote/CI closure remains separately labeled until proven.

## Queue Rules

- Keep this file short.
- List only active, open work.
- Remove completed items immediately.
- Every active item must reference a backlog ID like `[BL-001]`.
- Include owner, next action, and exit criteria when items exist.
