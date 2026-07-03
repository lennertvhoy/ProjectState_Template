# Evidence: Worktree Isolation + Anti-Brittleness Guardrails

**Slice:** [BL-WORKFLOW-002] Worktree Isolation + Anti-Brittleness Guardrails  
**Date:** 2026-07-03  
**Agent:** coding-agent  
**Branch:** bl-workflow-002-worktree-brittleness  
**HEAD:** 71dd70d565da2394cd92604bd41b1d10b9e33483

## Claims

- Claim: StateDD now detects dirty or ambiguous worktree state before non-trivial slice implementation.
  Evidence: `command_outputs/worktree_guard_start_slice.txt`, `scripts/statedd_worktree_guard.py`, `scripts/test_worktree_guard.py`
  Evidence type: implementation | test | state_update

- Claim: StateDD handoffs now expose worktree topology and upstream visibility.
  Evidence: `scripts/statedd_handoff.py`, `prompts/FINAL_HANDOFF_TEMPLATE.md`, `command_outputs/check_state_docs.txt`
  Evidence type: implementation | state_update

- Claim: StateDD now has a reusable anti-brittleness gate for non-trivial fix/feature slices.
  Evidence: `ANTI_BRITTLENESS_GUARD.md`, `docs/quality_gates/ANTI_BRITTLENESS_GATE.md`, `scripts/statedd_brittleness_check.py`, `command_outputs/test_brittleness_check.txt`
  Evidence type: implementation | test | adversarial

- Claim: Downstream adoption and upgrade include the new managed assets.
  Evidence: `scripts/init_template.py`, `scripts/statedd_upgrade.py`, `command_outputs/test_init_template.txt`, `command_outputs/test_upgrade.txt`
  Evidence type: implementation | test

- Claim: The new gates are validated by focused regression tests.
  Evidence: `command_outputs/test_worktree_guard.txt`, `command_outputs/test_brittleness_check.txt`, `command_outputs/schema_validation.txt`
  Evidence type: test

## Failure Scan

- Required: yes
- Path: `docs/failure_scans/BL-WORKFLOW-002.md`
- Adjacent failures checked: dirty unclassified files, dirty classified files, closure dirty worktree, detached HEAD, missing origin, linked worktrees, exact prompt strings, large keyword buckets, fixture-only tests.
- Known bad events covered: local-only files claimed in a dirty shared worktree; brittle observed-example-only fixes.

## Worktree Dirty File Classification

| status | path | category | owner/notes |
| --- | --- | --- | --- |
| clean | not applicable | safe_to_discard_after_proof | Final validation should run from a committed clean worktree. |

## Anti-Brittleness Review

| Question | Answer |
| --- | --- |
| What invariant prevents the failure class? | Non-trivial slices must prove worktree/source-of-truth state before edits, and non-trivial fixes/features must name a durable invariant before closure. |
| Is the fix typed/schema/state-machine/validator/contract-based? | The worktree guard is an executable validator; the anti-brittleness gate is a reusable contract backed by audit marker checks and an advisory scanner. |
| Which behavior is centralized instead of scattered? | Worktree/source-of-truth inspection is centralized in `scripts/statedd_worktree_guard.py`; brittleness review questions are centralized in `ANTI_BRITTLENESS_GUARD.md` and `docs/quality_gates/ANTI_BRITTLENESS_GATE.md`. |
| Which observed examples are covered by general rules rather than exact strings? | Dirty shared worktree, local-only claims, detached HEAD, missing origin, linked worktrees, exact prompt strings, keyword buckets, sleeps/timeouts, silent fallbacks, and fixture-only tests are handled as categories. |
| What adjacent cases were tested? | Clean repo, dirty repo, classified dirty repo, dirty closure, detached HEAD, missing origin, linked worktree, large keyword buckets, exact prompt string, many `.includes(...)`, sleep/timeouts, fixture-only test shape, and clean-scan no-proof wording. |
| What brittle pattern was explicitly avoided? | The scanner is advisory only and cannot be the authority path; closure requires the structured anti-brittleness review. |
| Did the slice add keyword buckets, regex branches, exact prompt handling, fixture-only behavior, sleeps/timeouts, global mutable state, silent fallback, or provider-specific assumptions? | No authority path uses those patterns. The scanner only detects such patterns in diffs and reports warnings. |
| If yes, why is that not the authority path? | Not applicable for implementation authority; warnings route reviewers back to the anti-brittleness gate. |

## Verification Log

| Check | Command / Path | Result |
| --- | --- | --- |
| worktree guard tests | `python3 scripts/test_worktree_guard.py` | pass |
| brittleness tests | `python3 scripts/test_brittleness_check.py` | pass |
| hygiene | `python3 scripts/check_state_docs.py` | pass |
| schema validation | `python3 scripts/statedd_validate_schema.py` | pass |
| initializer propagation | `python3 scripts/test_init_template.py` | pass |
| upgrade propagation | `python3 scripts/test_upgrade.py` | pass |
| worktree guard preflight | `python3 scripts/statedd_worktree_guard.py --mode start-slice` | pass |
| handoff/audit | `python3 scripts/statedd_handoff.py --run-audit` | pass |
| audit | `python3 scripts/statedd_audit.py` | pass |
| diff whitespace | `git diff --check` | pass |

## Evidence Pack Manifest

- Manifest: `manifest.json`
- Redaction status: checked_with_limits

## Runtime Identity

- Runtime required: no
- Artifact: `runtime_identity.json`
- Endpoint: not applicable
- Process ownership proven: not applicable
- Known limits: Template root has no application runtime.

## Browser Verification

- Browser verification required: not applicable
- Browser verification artifact: not applicable
- Provider used: not applicable
- Fallbacks considered: not applicable
- Known browser verification limits: No user-facing runtime behavior changed in this template-maintenance slice.

## Closure State

- Implemented: yes
- Validated: pending
- Global quality gates passed: pending
- Closure-grade: pending PR/CI/remote closure
- Accepted: pending

## Human Override

- Human override used: no

## Risks / What Remains Partial

- GitHub-visible PR, CI, and remote closure remain pending until the branch is pushed.
- Downstream repos do not receive these guardrails until they generate from or upgrade to this template revision.
