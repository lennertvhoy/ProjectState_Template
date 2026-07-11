# Failure Scan: BL-GIT-ISOLATION-001 Git Metadata Safety Boundary

**Date:** 2026-07-11
**Backlog item:** [BL-GIT-ISOLATION-001]
**Author:** coding-agent
**Severity:** P0
**Execution mode impact:** quality_freeze

## What Happened Or Could Happen

- Reported initiating event: a surrounding runtime changed ownership or permissions
  inside a Git object database shared by linked worktrees. The actor and mechanism
  are not proven.
- Observed StateDD failure: startup and worktree orchestration did not inspect or
  contain that condition before authorizing mutation.
- A read-only Git query could fail or return an incomplete fallback and still look
  like a clean, writable, isolated repository.
- A failed fetch could be followed by state or source edits because synchronization
  was not part of one fail-closed transaction.

## How The User Or Operator Would Notice

- Git object writes fail with a permission or object-database error after work begins.
- One agent's runtime damages Git metadata used by every linked worktree.
- Startup reports clean/no-linked state even though the underlying Git read failed.
- Closure or cleanup attempts compound the incident through forced deletion/pruning.

## Likely Adjacent Failures

- Same-owner metadata is present but a nested directory is unwritable.
- Refs, reflogs, index, or linked-worktree administrative files fail independently
  of `.git/objects`.
- UID/GID is unknown, differs from metadata ownership, or changes across runtimes.
- A root or capability-bearing container writes a host-mounted repository.
- A nominal clone uses alternates or hardlinks and is not strongly independent.
- `git fsck`, `git status`, `git worktree list`, or fetch fails and an empty fallback
  is interpreted as success.
- A write probe leaves residue or the metadata changes between pre- and post-fetch
  scans.
- Stale or dirty worktrees are automatically removed instead of reported.

## Previous Tests That Might Miss This

- Existing worktree tests prove branch/path separation and reservation behavior, but
  not the shared common object database or runtime identity boundary.
- Existing guard tests cover dirty files, detached HEAD, and topology display, but
  not ownership, permissions, fsck, active write probes, or synchronization failure.
- Existing CI smoke tests treat default worktree creation as success.

## Global Invariant Needed

> A coding session may mutate repository or StateDD state only after one executable
> Git preflight proves the requested repository, effective identity, Git common
> directory, critical metadata ownership and writability, synchronization result,
> repository integrity, and permitted isolation mode. Any failed mandatory Git
> operation makes the session read-only until repaired and explicitly restarted.

## Adversarial Case

- Input/event: a disposable repository contains one unwritable or foreign-owned
  nested object-prefix directory, or a mandatory fetch fails.
- Expected protected behavior: writable isolation modes exit nonzero, the effective
  mode is latched `read_only`, and no project or StateDD state file changes.
- Evidence required: schema-valid Git safety JSON, before/after hashes, exact Git
  permission-error reproduction in a temporary repository, and adjacent regressions.

## Runtime Or Live Proof Required

- Required: yes
- Why: the failure crosses effective identity, container privilege, filesystem
  ownership, and Git common-directory boundaries.
- Artifact: docs/evidence/2026-07-11-git-isolation-safety/git_safety_report.json

## Post-Deploy Watch Required

- Required: yes
- Duration or trigger: the latest GitHub Actions run on the final pushed PR head and
  one exact-head remote-closure finalizer run.
- Artifact: docs/evidence/2026-07-11-git-isolation-safety/README.md

## Closure Blockers

- Incident regression and centralized preflight are not yet implemented.
- Default worktree creation and force cleanup remain present at intake.
- Generated profiles and startup prompts do not yet carry the repaired boundary.
- Final-head GitHub-visible CI and remote closure are not yet proven.

