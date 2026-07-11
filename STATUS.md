# StateDD Template Status

**Updated At:** 2026-07-11 14:15 +02:00
**Execution Mode:** quality_freeze
**Project State:** p0_git_isolation_incident_open
**Public URL:** https://github.com/lennertvhoy/StateDD_Template/releases/tag/v5

## Snapshot

- Repo identifies as `repo_role: template_repository` with `statedd_mode: template-maintenance` and spec version `statedd-template-v5`; generated/adopted downstream repos still start as `repo_role: downstream_project` with `statedd_mode: bootstrap`.
- `statedd-template-v5` is published as GitHub release `v5`; no further release steps are pending.
- A P0 workflow-integrity incident is open: StateDD's worktree workflow did not prove Git common-directory ownership, writability, runtime identity, repository integrity, or synchronization success before mutation.
- The initiating ownership/permission mutation is reported at the external runtime boundary; the responsible actor, command, and timestamp are not proven. StateDD is not claimed to have executed that mutation.
- The observed StateDD contribution is separate: linked worktrees shared the affected object database, default worktree creation remained enabled, mandatory Git failures did not latch read-only, no independent-clone mode existed, and automatic force cleanup remained reachable.
- BL-GIT-ISOLATION-001 supersedes BL-PARALLEL-001 and all unrelated feature work until the safety boundary is repaired and proven on the final pushed head.

## Product Truth

- This repository is a template, not an application product runtime.
- Product-facing template truth is the generated/adopted workflow contract and docs.

## Runtime Truth

- No application runtime exists for the template root.
- Runtime truth requirements apply to downstream projects and generated/adopted repos.

## Current Quality Gate

- Known-bad-event gate: failing for BL-GIT-ISOLATION-001.
- Prior template/profile test results are stale for this incident because they did not exercise Git metadata ownership, real write probes, synchronization failure, or clone independence.

## Open P0/P1 Failures

- [BL-GIT-ISOLATION-001] P0 — unsafe Git metadata/isolation preflight and containment boundary; incident open in `docs/incidents/20260711-141533-git-object-ownership-permission.md`.

## What Is Not Proven

- The actor and exact command that changed Git metadata ownership or permissions.
- The verbatim originating Git error; only the reported failure class is currently available.
- Whether any existing linked worktree is still active in another runtime.
- The repair's local, remote, CI, and user-accepted truth boundaries; implementation has not started at this snapshot.

## Immediate Priorities

1. Keep feature work frozen and ingest BL-GIT-ISOLATION-001 as a durable incident.
2. Add the permission/ownership/synchronization regression suite and centralized fail-closed Git safety preflight.
3. Replace default linked-worktree isolation with normal-branch, explicit worktree, independent-clone, and read-only policy; then obtain final-head CI/remote proof.

## Active Blockers

- Writable StateDD sessions are not safety-proven by the current executable gates.
- New StateDD-managed worktree creation is disabled by policy until the P0 closes.
- BL-PARALLEL-001 remote closure and all unrelated feature work are suspended.

## Notes

- Keep `STATUS.md` short.
- Use `PROJECT_STATE.yaml` for structured truth.
- Use `BACKLOG.md` backlog IDs inside `NEXT_ACTIONS.md` when active items are added.
- Prove runtime identity before accepting user-facing behavior.
