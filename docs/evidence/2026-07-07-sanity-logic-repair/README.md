# Evidence: BL-SANITY-002 template logic-hole repair

**Slice:** [BL-SANITY-002] Repair template logic holes discovered by the 2026-07-07 ultra-critical sanity check  
**Date:** 2026-07-07  
**Agent:** coding-agent  
**Branch:** bl-workflow-002-worktree-brittleness  
**HEAD:** a39d26dc95e3ad000e726832942c1314280ed467  
**Proof head:** a39d26dc95e3ad000e726832942c1314280ed467  
**Final PR head:** b1b00f3b0328b42bd15c7868f4ea9815aa5e6551  
**Closure state:** PR/CI pending

## Claims

- Claim: `scripts/statedd_audit.py` no longer accepts stale HEAD evidence and derives changed files from the merge-base with the default branch.
  Evidence: `scripts/statedd_audit.py`, `command_outputs/audit_strict.txt`
  Evidence type: implementation

- Claim: `scripts/statedd_doctor.py` counts real open blockers from `PROJECT_STATE.yaml` instead of `NEXT_ACTIONS.md` headings.
  Evidence: `scripts/statedd_doctor.py`
  Evidence type: fix

- Claim: `scripts/statedd_handoff.py` reports `local-only files claimed: not proven` when upstream state is unknown.
  Evidence: `scripts/statedd_handoff.py`
  Evidence type: fix

- Claim: `scripts/statedd_runtime_proof.py`, `statedd_runtime_truth_check.py`, and `statedd_closure_check.py` agree on the canonical `runtime_identity.json` schema.
  Evidence: `scripts/statedd_runtime_proof.py`, `scripts/statedd_runtime_truth_check.py`, `runtime_identity.json`
  Evidence type: fix

- Claim: `scripts/statedd_worktree_guard.py` rejects `unknown_do_not_touch` dirty-file classifications and does not label ordinary tracked feature branches as shared/default.
  Evidence: `scripts/statedd_worktree_guard.py`, `scripts/test_worktree_guard.py`
  Evidence type: fix

- Claim: `scripts/init_template.py` refuses to initialize into the template root.
  Evidence: `scripts/init_template.py`, `scripts/test_init_template.py`
  Evidence type: fix

- Claim: `scripts/statedd_upgrade.py` blocks path traversal and reports the actual `--apply`/`--dry-run` mode.
  Evidence: `scripts/statedd_upgrade.py`, `scripts/test_upgrade.py`
  Evidence type: fix

- Claim: `scripts/statedd_browser_verify.py` rejects artifact paths that escape the evidence directory.
  Evidence: `scripts/statedd_browser_verify.py`, `scripts/test_browser_verification.py`
  Evidence type: fix

- Claim: `scripts/statedd_remote_closure_finalizer.py` runs `gh` from the repo root, honors `--github-token`, and avoids check-suite id misuse.
  Evidence: `scripts/statedd_remote_closure_finalizer.py`
  Evidence type: fix

- Claim: `scripts/statedd_post_merge_verify.py` declares the GraphQL `$sha` variable and fetches the default branch before ancestry checks.
  Evidence: `scripts/statedd_post_merge_verify.py`
  Evidence type: fix

- Claim: `scripts/statedd_probe_guidance.py` runs probes in an isolated temporary copy of the repo.
  Evidence: `scripts/statedd_probe_guidance.py`
  Evidence type: fix

## Failure Scan

- Required: yes
- Path: `docs/failure_scans/BL-SANITY-002.md`
- Adjacent failures checked: false closure claims from stale evidence, dirty-worktree false passes, runtime-identity schema drift, unsafe file operations, path traversal, branch-classification brittleness.
- Known bad events covered: BL-SANITY-002 findings from the 2026-07-07 ultra-critical sanity check.

## Worktree Dirty File Classification

| status | path | category | owner/notes |
| --- | --- | --- | --- |
| clean | entire repo | not applicable | Worktree was clean at commit `a39d26d` before evidence artifacts were generated. |

## Anti-Brittleness Review

| Question | Answer |
| --- | --- |
| What invariant prevents the failure class? | Audit must prove HEAD is recorded in evidence; changed-files must be relative to the default branch; unknown upstream must not be treated as synced; unsafe paths must be rejected before writes. |
| Is the fix typed/schema/state-machine/validator/contract-based? | Yes: `runtime_identity.json` uses the canonical `statedd.runtime_identity.v1` schema; path checks use `Path.resolve()` and `relative_to`; merge-base is computed with `git merge-base`. |
| Which behavior is centralized instead of scattered? | Path-traversal guard, atomic writes, and merge-base changed-files logic are centralized in the relevant scripts rather than duplicated. |
| Which observed examples are covered by general rules rather than exact strings? | Path traversal is rejected for any path outside the target directory, not just known bad strings. Unknown upstream is any failure of `git ls-remote`, not a specific message. |
| What adjacent cases were tested? | Clean/dirty/closure worktrees; classified dirty files; detached/missing-origin branches; target==root init; symlink/traversal upgrade targets; escaped browser artifact paths. |
| What brittle pattern was explicitly avoided? | Keyword matching for upstream status; exact fixture-only checks; sleeps/timeouts; provider-specific browser assumptions; global mutable state. |
| Did the slice add keyword buckets, regex branches, exact prompt handling, fixture-only behavior, sleeps/timeouts, global mutable state, silent fallback, or provider-specific assumptions? | No. |
| If yes, why is that not the authority path? | Not applicable. |

## Verification Log

| Check | Command / Path | Result |
| --- | --- | --- |
| tests | `python3 -m pytest scripts/test_*.py -q` | pass (144 passed, 4 subtests passed) |
| state validation | `python3 scripts/check_state_docs.py` | pass |
| schema validation | `python3 scripts/statedd_validate_schema.py` | pass |
| quality gate | `python3 scripts/statedd_quality_gate.py --gate-level 2` | pass |
| closure check | `python3 scripts/statedd_closure_check.py` | pass (after push) |
| audit strict | `python3 scripts/statedd_audit.py --strict` | pass (after commit of evidence) |
| runtime truth | `python3 scripts/statedd_runtime_truth_check.py` | pass |
| worktree guard | `python3 scripts/statedd_worktree_guard.py --mode closure` | pass |
| brittleness scan | `python3 scripts/statedd_brittleness_check.py` | no blockers |
| instruction lint | `python3 scripts/statedd_instruction_lint.py --fail-on error` | pass |

## Evidence Pack Manifest

- Manifest: `manifest.json`
- Redaction status: checked

## Runtime Identity

- Runtime required: no
- Artifact: `runtime_identity.json`
- Endpoint: not applicable
- Process ownership proven: not applicable
- Known limits: Template root has no application runtime; downstream repos must prove runtime identity for user-facing acceptance.

## Browser Verification

- Browser verification required: no
- Browser verification artifact: not applicable
- Provider used: not applicable
- Fallbacks considered: not applicable
- Known browser verification limits: No user-facing changes in this slice.

## Closure State

- Implemented: yes
- Validated: yes
- Global quality gates passed: yes
- Closure-grade: pending PR/CI verification
- Accepted: pending

## Human Override

- Human override used: no

## Risks / What Remains Partial

- PR/CI green and `scripts/statedd_remote_closure_finalizer.py` agreement are pending the push and GitHub Actions run.
- Downstream repos have not yet upgraded to these fixes.
