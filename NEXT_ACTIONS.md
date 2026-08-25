# NEXT_ACTIONS - Active Execution Queue

**Updated At:** 2026-08-25
**Execution Mode:** template-maintenance
**Max Items:** 10

## Active Work

### P1 [BL-WORKFLOW-CATALOG-001] Roll the workflows asset-set upgrade across managed downstream repos

Catalog, budgets, and metrics are merged on this branch; remaining work is
running `projectstate_upgrade.py` dry-run/apply per managed repo and opening
upgrade PRs that each repo's next agent session completes after CI.

## Queue Rules

- Keep this file short.
- List only active, open work.
- Remove completed items immediately.
- Every active item must reference a backlog ID like `[BL-001]`.
- Future research and compatibility work stays in `BACKLOG.md` until selected.
