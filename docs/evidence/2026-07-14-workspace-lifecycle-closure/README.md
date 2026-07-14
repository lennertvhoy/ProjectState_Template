# Evidence: Managed Workspace Lifecycle Closure

**Slice:** [BL-WORKSPACE-LIFECYCLE-001] Repair false isolation release and clone proliferation  
**Date:** 2026-07-14  
**Agent:** integration coding agent  
**Branch:** `fix/workspace-lifecycle-closure`  
**HEAD:** pending immutable proof commit  
**Proof head:** pending immutable proof commit

## Claims

- Claim: Every archived clone and linked worktree was inspected, and clone work is
  integrated while only bounded audit safeguards are selected from remaining
  worktrees.
  Evidence: `clone_audit.json`
  Evidence type: investigation, state_update
- Claim: Managed clone creation is centralized outside the project parent and
  rejects nested sources, arbitrary targets, and unmanaged same-origin siblings.
  Evidence: `verification_summary.json`, source under `scripts/`
  Evidence type: implementation, adversarial
- Claim: Finish cannot reach `HANDOFF_COMPLETE` unless a strict release receipt
  proves the exact original isolation path absent.
  Evidence: `verification_summary.json`, source under `scripts/`
  Evidence type: implementation, regression
- Claim: Dirty state is retained; a clean clone is quarantined recoverably and a
  clean opted-in worktree is removed without force with reservation absence.
  Evidence: `verification_summary.json`
  Evidence type: product_behavior, test
- Claim: Generated downstream profiles inherit the inventory dependency and the
  managed workspace lifecycle contract.
  Evidence: `verification_summary.json`
  Evidence type: generated_fixture, test

## Failure Scan

- Required: yes
- Path: `docs/failure_scans/BL-WORKSPACE-LIFECYCLE-001.md`
- Incident: `docs/incidents/2026-07-14-workspace-lifecycle-false-cleanup.md`
- Known bad event: metadata-only release reported as physical cleanup while clone
  directories remained and recursively spawned additional clones.

## Worktree Dirty File Classification

| status | path | category | owner/notes |
| --- | --- | --- | --- |
| modified/new | files listed by `git status --short` | intended_slice_work | BL-WORKSPACE-LIFECYCLE-001 |
| preserved external WIP | `.worktrees/bl-bl-browser-002-code-g3trh` in canonical checkout | pre_existing_unrelated | retained; not edited or merged |

## Anti-Brittleness Review

| Question | Answer |
| --- | --- |
| What invariant prevents the failure class? | One managed non-recursive workspace lifecycle; release requires exact context/branch/HEAD/path binding plus physical original-path absence. |
| Is the fix typed/schema/state-machine/validator/contract-based? | Yes: normalized origin identity, deterministic workspace root, strict agent context, closed-world release receipt, v2 finish handoff schema, and finish-stage checks. |
| Which behavior is centralized instead of scattered? | Workspace path selection, clone inventory, recursion rejection, release disposition, and finish receipt validation. |
| Which observed examples are covered by general rules rather than exact strings? | Any immediate same-origin sibling, any managed nested source, any non-default target, any dirty workspace, and any contradictory receipt. |
| What adjacent cases were tested? | SSH/HTTPS/credential URL equivalence, manual siblings, nested provisioning, arbitrary targets, clean/dirty clone release, worktree release/reservation, false receipts, false-without-diagnostic checks, and unrelated evidence. |
| What brittle pattern was explicitly avoided? | No directory-name allowlist, fixed observed clone list, force deletion, sleep-based cleanup, success-by-exit-code alone, or newest-by-mtime closure evidence. |
| Did the slice add provider-specific assumptions? | No. The lifecycle is local Git/filesystem behavior and remote identity normalization is transport-neutral. |
| If yes, why is that not the authority path? | Not applicable. |

## Verification Log

| Check | Command / Path | Result |
| --- | --- | --- |
| focused lifecycle suite | `python3 -m pytest -q scripts/test_agent_worktree.py scripts/test_finish_slice.py scripts/test_handoff.py scripts/test_quality_gate.py scripts/test_closure_check.py` | pass locally |
| full script suite | `python3 -m pytest scripts/ -q` | pending |
| generated profiles | `python3 scripts/statedd_profile_metrics.py --check` | pending regeneration and validation |
| level-2 quality gate | `python3 scripts/statedd_quality_gate.py --gate-level 2 ...` | pending |
| remote closure | exact-head PR/CI/merge/main verification | pending |

## Evidence Pack Manifest

- Manifest: `manifest.json` (pending generation after immutable proof commit)
- Redaction status: manual review pending final artifact generation

## Runtime Identity

- Runtime required: no
- Artifact: `runtime_identity.json` (pending final capture)
- Endpoint/process ownership: not applicable; template root has no application runtime

## Browser Verification

- Browser verification required: no
- Provider/artifact: not applicable
- Reason: this slice changes local Git/filesystem workflow scripts and contracts.

## Closure State At Current Worktree

- Implemented: yes
- Validated locally: focused suite only
- Closure-grade: no
- Remote closure: pending
- Human product acceptance: pending

## Human Override

- Human override used: no
- Rule overridden: not applicable
- Requested by: not applicable
- Reason accepted: not applicable
- Remaining risk: full local and remote closure boundaries remain pending
- Still closure-grade: no

## Risks / What Remains Partial

- Full repository/profile gates, immutable proof hashes, PR CI, merge, direct-main
  CI, and the repair workspace's own release receipt remain pending.
- Raw external `git clone` cannot be prevented globally; managed starts and
  handoffs detect immediate same-origin siblings and refuse silently clean status.
- BL-BROWSER-002 dirty WIP remains preserved and intentionally unintegrated.
