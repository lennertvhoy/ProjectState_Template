# ADR-0001: Git Common Directory Is the Isolation Safety Boundary

**Status:** accepted
**Date:** 2026-07-11
**Author:** agent implementing the user-directed safety policy

## Context

A surrounding runtime reportedly changed ownership or permissions inside a Git
object database shared by linked worktrees. The actor and command are not proven.
Separately, StateDD's source showed an observed containment failure: it promoted
linked worktrees without proving runtime identity, common-directory ownership,
real writability, fsck, or synchronization, and it retained automatic force
cleanup. Git documents that linked worktrees share repository data other than
per-worktree files such as `HEAD` and `index`.

## Decision

- The Git common directory/object database, not the visible working directory, is
  the isolation authority.
- One trusted local agent may use a normal feature branch after the centralized
  Git safety transaction passes.
- Containers and independent agents use full clones with distinct common
  directories, no alternates, and no hardlinked object files.
- Linked worktrees require explicit trusted-local same-UID/GID opt-in and a safe
  shared-common-directory preflight. They are never the default.
- Any mandatory Git failure selects an externally latched `read_only` StateDD
  session until repair and an explicit restart reruns every check successfully.
- StateDD reports permission anomalies, dirty/stale worktrees, and locks. It never
  automatically repairs ownership/modes or force-removes, prunes, resets, cleans,
  or garbage-collects affected Git state.

## Consequences

Independent agents consume more disk/network because full clones duplicate object
databases. In exchange, an agent/runtime cannot corrupt every peer through shared
objects. Worktree users must make a deliberate trust assertion. Cleanup becomes a
human-controlled operation, so retained paths may accumulate until reviewed.

The JSON permit is workflow enforcement for StateDD-managed mutation. It does not
make an arbitrary external shell physically read-only; that stronger claim requires
separately proven OS sandbox or mount enforcement.

## Alternatives Considered

- Worktrees by default: rejected because their shared common directory is the
  exact blast-radius boundary exposed by the incident.
- Read-only metadata inspection: rejected because access bits and ownership do not
  prove the effective runtime can perform required writes.
- Automatic permission repair or force cleanup: rejected because it can destroy
  evidence, overwrite user intent, or compound an unknown-identity incident.
- Prompt-only sequencing: rejected because failed synchronization must change an
  executable decision and latch state.

## Related

- Backlog item: [BL-GIT-ISOLATION-001]
- Incident: `docs/incidents/20260711-141533-git-object-ownership-permission.md`
- Failure scan: `docs/failure_scans/BL-GIT-ISOLATION-001.md`
- Evidence: `docs/evidence/2026-07-11-git-isolation-safety/`
- Git worktree reference: https://git-scm.com/docs/git-worktree
