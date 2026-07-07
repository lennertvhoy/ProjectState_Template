# NEXT_ACTIONS - Active Execution Queue

**Updated At:** 2026-07-07
**Execution Mode:** template-maintenance
**Max Items:** 10

## Active Work

### P0 [BL-WORKFLOW-002] Re-validate Worktree Isolation and Anti-Brittleness Guardrails
Owner: coding agent
Next: re-run the full closure sequence for BL-WORKFLOW-002 after the BL-SANITY-002 logic repairs: verify evidence matches final HEAD, push branch if needed, confirm PR/CI green, and run `scripts/statedd_remote_closure_finalizer.py`
Exit: BL-WORKFLOW-002 is closure-grade with GitHub-visible CI success and remote closure agreement

## Queue Rules

- Keep this file short.
- List only active, open work.
- Remove completed items immediately.
- Every active item must reference a backlog ID like `[BL-001]`.
- Include owner, next action, and exit criteria when items exist.
