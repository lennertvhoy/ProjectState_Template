# Finish Branch-Deletion Repair Evidence

**Slice:** DEF-FINISH-BRANCH-DELETE-001  
**Date:** 2026-07-12  
**Agent:** integration defect-repair agent  
**Branch:** `fix-finish-branch-delete`  
**HEAD:** bb325e7f46e3a19d2a69f70ead75bf8e5f749b30  
**Proof head:** bb325e7f46e3a19d2a69f70ead75bf8e5f749b30

## Claims

- Claim: GitHub branch deletion uses the documented plural `git/refs` delete
  endpoint while ref reads retain the singular `git/ref` endpoint.
  Evidence: `source_hashes.json`, `verification_summary.json`
- Claim: deletion remains exact-head constrained and is idempotent when the
  branch is already absent.
  Evidence: `verification_summary.json`
- Claim: cleanup remains ordered after post-merge verification and before
  isolation release.
  Evidence: `verification_summary.json`
- Claim: GitHub's transient `UNSTABLE` merge state is boundedly tolerated only
  while a required CI subject is pending; it still blocks after CI is green.
  Evidence: `verification_summary.json`

## Defect Reproduction

The live PR #13 finish run merged and verified direct-main CI, then received
HTTP 404 from `DELETE .../git/ref/heads/<branch>`. The branch still existed and
the documented plural endpoint deleted it successfully. This isolated the
defect to the production adapter path rather than policy, permissions, merge,
CI, or post-merge verification.

## Verification Log

- `ruff check scripts/statedd_finish_slice.py scripts/test_finish_slice.py` — pass
- `python3 -m pytest scripts/test_finish_slice.py -q` — pass (25 tests)
- Provider regression asserts the exact singular-read/plural-delete/singular-read
  request sequence — pass
- Already-absent regression proves cleanup idempotency — pass
- Pending-CI regression proves the command waits through transient `UNSTABLE`
  state and re-applies strict clean-state validation after CI — pass
- Full level-2 closure gate — pending final evidence commit

## Runtime Identity

- Runtime required: no
- Artifact: `runtime_identity.json`
- Reason: the template root has no deployable runtime; provider contract tests,
  GitHub CI, and the live follow-up closure establish this repository behavior.

## Anti-Brittleness Review

- Provider-specific behavior: the adapter is explicitly GitHub-specific and
  uses documented GitHub ref endpoints behind the provider protocol.
- Exact identity guard: deletion still refuses a remote head mismatch.
- Idempotency: an absent ref is success-equivalent and does not trigger a second
  mutation.
- No sleeps, fixture-keyword shortcuts, force operations, or history rewrites
  were added.

## Closure State

The PR body binds this immutable Proof head to the final PR head. Provider-created
merge/default-head/CI identities belong only in the external finish handoff.
This tracked evidence predicts no future merge identity.

## Human Override

- Human override used: no

## Risks / What Remains Partial

- Verified legal copyright owner remains not proven; `LICENSE` is unchanged.
- Human product acceptance remains pending.
- Comparative benchmark superiority remains not proven.
