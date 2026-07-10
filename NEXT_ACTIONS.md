# NEXT_ACTIONS - Active Execution Queue

**Updated At:** 2026-07-10
**Execution Mode:** template-maintenance
**Max Items:** 10

## Active Work

### P1 [BL-CONTEXT-001] Generated-Repo Correctness And Context Hygiene
Owner: coding agent
Next: commit and push the locally validated repair, open a stacked PR, wait for GitHub Actions on the final head, and run the remote closure finalizer.
Exit: profile self-gates, evidence, PR body, final pushed head, and GitHub CI all agree

### P1 [BL-PARALLEL-001] Parallel-Agent Remote Closure
Owner: coding agent + human reviewer
Next: push the already implemented local slice, align PR/evidence/CI on one head, and run the remote closure finalizer.
Exit: BL-PARALLEL-001 has GitHub-visible CI success and remote closure agreement

## Queue Rules

- Keep this file short.
- List only active, open work.
- Remove completed items immediately.
- Every active item must reference a backlog ID like `[BL-001]`.
- Include owner, next action, and exit criteria when items exist.
