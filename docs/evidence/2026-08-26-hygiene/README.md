# Evidence: Stray duplicate evidence-file removal

**Slice:** [BL-EVIDENCE-HYGIENE-001]
**Date:** 2026-08-26
**Agent:** opencode integration agent (ox-alpha)

## Claims

- Claim: The two stray files under docs/evidence/ removed by this slice were
  byte-identical duplicates of artifacts already committed inside
  docs/evidence/2026-08-26-stateisolation/; removal is pure subtraction with
  no information loss.
  Evidence: `README.md`
  Evidence type: state_update
- Claim: Runtime boundary recorded; no application runtime claimed.
  Evidence: `runtime_identity.json`
  Evidence type: runtime_truth

## Failure Scan

- Required: no
- Path: not applicable; file removal only.

## Worktree Dirty File Classification

| status | path | category | owner/notes |
| --- | --- | --- | --- |
| deleted | docs/evidence/after_fix_hostile_env.txt | intended_slice_work | stray duplicate |
| deleted | docs/evidence/repro_before_fix_golden_path.txt | intended_slice_work | stray duplicate |

## Anti-Brittleness Review

| Question | Answer |
| --- | --- |
| What invariant prevents the failure class? | Evidence lives inside exactly one pack folder; loose files at the evidence root are not canonical. |
| Is the fix typed/schema/state-machine/validator/contract-based? | Byte-hash identity proof before deletion. |
| Which behavior is centralized instead of scattered? | Authoritative copies stay in their slice pack. |
| Which observed examples are covered by general rules? | Any future stray evidence-root file gets the same identity check then removal. |
| What adjacent cases were tested? | Full level-2 aggregate. |
| What brittle pattern was explicitly avoided? | No blind deletion; identity proven first. |
| Did the slice add provider-specific assumptions? | No. |
| If yes, why is that not the authority path? | Not applicable. |

## Verification Log

| Check | Command / Path | Result |
| --- | --- | --- |
| identity proof | sha256 comparison of removed HEAD blobs vs pack copies | identical |
| full level-2 gate | `projectstate_quality_gate.py --gate-level 2 --conformance --verbose` | pass; exit 0 |

## Runtime Identity

- Runtime required: no
- Artifact: `runtime_identity.json`

## Browser Verification

- Browser verification required: no
- Reason: file removal only.
