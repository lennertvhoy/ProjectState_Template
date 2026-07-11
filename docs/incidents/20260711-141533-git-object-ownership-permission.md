# Incident: Shared Git Object Database Permission Failure Was Not Contained

**Date:** 2026-07-11
**Incident ID:** INC-20260711-141533-GIT-ISOLATION
**Severity:** P0
**Status:** open
**Related backlog:** [BL-GIT-ISOLATION-001]
**Related failure scan:** docs/failure_scans/BL-GIT-ISOLATION-001.md
**Evidence folder:** docs/evidence/2026-07-11-git-isolation-safety

## User/Operator Symptom

- A coding workflow could encounter a Git object-database permission failure after
  another runtime changed ownership or permissions in shared repository metadata.
- Linked worktrees appeared isolated at the working-tree level while still sharing
  the affected Git common directory and object database.
- Existing StateDD startup and closure checks did not identify the unsafe identity,
  ownership, writability, synchronization, or isolation state.

## Observed Event

- Source: user-provided incident assessment on 2026-07-11.
- Timestamp: exact runtime event timestamp is not proven; incident intake began at
  2026-07-11T14:15:33+02:00.
- Transcript/log/artifact: the assessment reports a Git/worktree permission failure
  involving nested object-database ownership. A verbatim originating error log,
  actor, and command are not currently locatable in this repository.

## Cause 1: Initiating Repository Mutation

**Boundary:** external/runtime integration boundary  
**Evidence status:** reported; mechanism not proven

A surrounding runtime reportedly created or changed ownership or permissions of a
nested path in the repository's shared Git object database. StateDD is not proven
to have originated that mutation. Without a durable runtime log, the responsible actor,
command, privilege transition, and exact timestamp remain not proven.

## Cause 2: StateDD Causal Contribution

**Boundary:** workflow integrity  
**Evidence status:** observed in the source at incident intake

StateDD required or recommended linked worktrees while treating their working-tree
separation as the primary isolation boundary. Its executable startup path did not
prove effective UID/GID, runtime/container privilege, Git common-directory identity,
nested metadata ownership, actual writability, repository integrity, or mandatory
synchronization success. It had no independent-clone path, did not latch the session
read-only after a mandatory Git failure, retained automatic force cleanup paths, and
had not ingested this observed event.

This containment failure did not perform the initiating ownership mutation. It made
that external mutation capable of affecting every linked worktree and invisible to
the workflow's mutation and closure decisions.

## Suspected Failure Class

- Initiating event: `integration_boundary` and `security_privacy` (reported).
- StateDD contribution: `workflow`, `state_truth`, and `observability` (observed).
- Severity attaches to the operator-safety workflow failure, not to an unproven
  claim that StateDD ran `chown` or `chmod`.

## Missing Invariant

> A coding session may mutate repository or StateDD state only after one executable
> Git preflight proves the requested repository, effective identity, Git common
> directory, critical metadata ownership and writability, synchronization result,
> repository integrity, and permitted isolation mode. Any failed mandatory Git
> operation makes the session read-only until repaired and explicitly restarted.

## Regression Fixture

- Path: scripts/test_git_safety_check.py
- Status: missing at incident intake; required before mitigation can be claimed.
- Exact-event limit: reproduce the permission-denied object-write failure safely in
  a disposable repository. Do not claim the absent original transcript was recovered.

## Runtime/Live Proof

- Required: yes, for operator/runtime identity and Git metadata safety.
- Artifact: docs/evidence/2026-07-11-git-isolation-safety/git_safety_report.json
- Application runtime/browser proof: not applicable; this template root has no
  application runtime or user-facing route.
- Status: missing

## Adjacent Cases Checked

- Planned checks cover unreadable or unwritable objects, refs, logs, and worktree
  metadata; nested foreign ownership; failed fetch; unknown/mismatched identity;
  privileged containers; clone independence; read-only behavior; stale worktrees;
  forbidden cleanup commands; schema validation; and failed critical Git reads.

## Closure Conditions

- Centralized human/JSON Git safety preflight and schema implemented.
- `normal_branch`, explicit-opt-in `worktree`, independent `clone`, and `read_only`
  decisions are executable and fail closed.
- Containers and independent agents default to full clones; worktree creation is
  disabled by default.
- Mandatory synchronization failure latches read-only without project/state writes.
- No StateDD production path automatically runs permission repair, destructive reset
  or clean, garbage collection, worktree pruning, forced worktree removal, or forced
  branch deletion.
- The incident and adjacent regressions pass locally and on the same pushed PR head.
- GitHub-visible CI and remote closure agree before the incident is closed.

## Residual Risk

- A workflow-level permit cannot make an arbitrary external shell process physically
  read-only. Unless an OS-level read-only mount or sandbox is independently proven,
  read-only enforcement is limited to StateDD-managed mutation entrypoints and agent
  policy.
- The external actor and original permission-changing command remain not proven.
