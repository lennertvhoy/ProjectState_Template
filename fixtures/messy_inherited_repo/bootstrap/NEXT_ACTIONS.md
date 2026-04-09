# NEXT_ACTIONS - Active Execution Queue

**Updated At:** 2026-03-18 19:00 CET
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
