# Evidence: Improve-run dogfood — rollout truth reconciliation and rot repairs

**Slice:** [BL-IMPROVE-RUN-001] Reconcile rollout truth; repair doc/lint rot
**Date:** 2026-08-26
**Agent:** opencode integration agent (ox-alpha)
**Branch:** `bl-improve-run-001`
**HEAD:** a0c781a3fcdb129cc8cc5bfe48766335d4ead047
**Proof head:** a0c781a3fcdb129cc8cc5bfe48766335d4ead047

## Claims

- Claim: Live truth reconciled after the cross-repo rollout: queue returned to
  a stable empty state; BL-WORKFLOW-CATALOG-001 closed with outcome (2 upgrade
  PRs, 2 transactional non-git upgrades, 52 pickup issues); STATUS extended;
  WORKLOG and EVIDENCE_LOG record the rollout.
  Evidence: `manifest.json`
  Evidence type: state_update
- Claim: docs/AGENTS.md catalog labels root-level reference files correctly;
  QUICK_COMMANDS documents the adopt-first path and /projectstate-improve.
  Evidence: `manifest.json`
  Evidence type: implementation
- Claim: Dead `known_skills` attribute removed from the instruction linter
  without behavior change (defined, never referenced).
  Evidence: `quality_gate_output.txt`
  Evidence type: implementation, test
- Claim: Append-only errata records the nonexistent v4 release-notes filename
  cited by historical acceptance entries.
  Evidence: `manifest.json`
  Evidence type: state_update
- Claim: Runtime boundary recorded; no application runtime claimed.
  Evidence: `runtime_identity.json`
  Evidence type: runtime_truth

## Failure Scan

- Required: no
- Path: not applicable; documentation/state reconciliation with one dead-code
  removal covered by the authoritative suite.
- Known bad event considered: ambient Git-safety latch cross-contaminated the
  golden-path regression via the shared default state root; observed twice
  today. Recorded as a backlog candidate for per-test state-root isolation.

## Worktree Dirty File Classification

| status | path | category | owner/notes |
| --- | --- | --- | --- |
| modified/new | files in `git status --short` at verification time | intended_slice_work | BL-IMPROVE-RUN-001 |

## Anti-Brittleness Review

| Question | Answer |
| --- | --- |
| What invariant prevents the failure class? | Truth-boundary discipline: live state files must mirror executed reality; closure claims need gate evidence. |
| Is the fix typed/schema/state-machine/validator/contract-based? | Yes: hygiene gates validate queue/backlog/status consistency after reconciliation. |
| Which behavior is centralized instead of scattered? | Rollout outcome lives once in BACKLOG CLOSED plus one EV record; queue references nothing stale. |
| Which observed examples are covered by general rules? | Any future rollout closes through the same close-slice path rather than ad-hoc notes. |
| What adjacent cases were tested? | Full level-2 aggregate including instruction lint after dead-code removal. |
| What brittle pattern was explicitly avoided? | No editing of append-only ledger history; errata appended instead. |
| Did the slice add provider-specific assumptions? | No. |
| If yes, why is that not the authority path? | Not applicable. |

## Verification Log

| Check | Command / Path | Result |
| --- | --- | --- |
| full level-2 gate | `projectstate_quality_gate.py --gate-level 2 --conformance` | pass; exit 0 (see `quality_gate_output.txt`) |
| evidence manifest strict | `projectstate_evidence_pack.py check . --strict` | pass |

## Evidence Pack Manifest

- Manifest: `manifest.json`
- Redaction status: checked with limits; automated scan passed and manual review completed

## Runtime Identity

- Runtime required: no
- Artifact: `runtime_identity.json`

## Browser Verification

- Browser verification required: no
- Reason: documentation/state/tooling-only changes.

## Closure State At Current Worktree

- Implemented: yes; captured at immutable proof head `a0c781a3fcdb129cc8cc5bfe48766335d4ead047`
- Validated locally: yes
- Closure-grade: no until remote finalization
- Remote closure: pending
- Human product acceptance: pending

## Human Override

- Human override used: no
- Remaining risk: golden-path regression remains sensitive to an ambient read-only latch from concurrent sessions (backlog candidate).
- Still closure-grade: no, by the Remote Truth Gate

## Risks / What Remains Partial

- Remote closure pending; downstream upgrade PRs (#1 talentlms-content, #2 packettracer-mcp-gui) remain open in their repos by design.
