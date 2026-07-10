# NEXT_ACTIONS - Active Execution Queue

**Updated At:** 2026-07-10
**Execution Mode:** template-maintenance
**Delivery State:** stabilization
**Max Items:** 5

## Active Work

### P0 [BL-CORE-001] Eliminate false closure and generator corruption
Owner: one coding agent in an isolated worktree; independent read-only reviewer before closure
Next: review the integrated diff, create exact-head evidence after final edits, commit/push the isolated branch, and open one focused PR
Scope: remote-truth, handoff exit, configured gate semantics, runtime/evidence contract alignment, duplicate-key rejection, version detection/changelog alignment, public runtime-evidence privacy, upgrade-report truth, and directly required CI failure-injection coverage
Non-goals: parallel-agent orchestration, browser-provider integration, broad instruction rewrites, managed updater/toolpacks/model routing, or the full package migration
Exit: all BL-CORE-001 acceptance criteria in `BACKLOG.md` pass on the exact pushed head; current-head CI, PR state, remote equality, and post-merge verification agree
Closure label until exit: `NOT CLOSURE-GRADE - LOCAL OR UNVERIFIED CLAIM`

## Queue Rules

- Keep this file short and list only active work.
- Every active item must reference a stable backlog ID.
- Do not start later work while BL-CORE-001 is open.
- A green command is evidence only for the condition it actually proves.
