# Evidence: Maximum-Value Correctness And Lifecycle Repair

**Slice:** [BL-MAX-VALUE-001] Maximum-Value Correctness And Lifecycle Repair
**Date:** 2026-07-11
**Agent:** codex-root-max
**Branch:** bl-max-value-001
**HEAD:** ae851d05aa8113c3cde90d122d1723be123d9e37
**Proof HEAD:** ae851d05aa8113c3cde90d122d1723be123d9e37

## Claims

- Claim: Profile upgrades derive desired assets from the current catalog while
  treating old locks as validated historical ownership; malformed, modified,
  removed, symlinked, traversal, and interrupted cases fail closed or roll back.
  Evidence: `command_outputs/pytest_scripts.txt`
  Evidence type: adversarial

- Claim: The authoritative quality gate automatically discovers every
  applicable suite, aggregates failures, and is the single local and CI entrypoint.
  Evidence: `command_outputs/pytest_scripts.txt`,
  `command_outputs/pytest_schema_examples.txt`
  Evidence type: test

- Claim: Runtime identity v2 omits absolute checkout identity and raw process
  arguments; strict runtime re-probing rejects dirty drift, unsafe artifacts,
  endpoint/process mismatch, implicit remote probes, and legacy closure proof.
  Evidence: `runtime_identity.json`, `command_outputs/runtime_truth_check.txt`,
  `command_outputs/pytest_scripts.txt`
  Evidence type: security_privacy

- Claim: Canonical profile/context metrics reproduce against the immutable proof
  commit and do not drift when unrelated evidence makes the worktree dirty.
  Evidence: `command_outputs/profile_metrics_check.txt`,
  `command_outputs/pytest_scripts.txt`
  Evidence type: implementation

- Claim: The exact-head remote finalizer and evidence contracts prevent local,
  pushed-branch, PR-body, CI-run, and merge-state truth from being conflated.
  Evidence: `command_outputs/pytest_scripts.txt`,
  `command_outputs/schema_validation.txt`
  Evidence type: adversarial

- Claim: The repair is schema-valid, diff-clean, and reviewed against brittle
  example-only behavior.
  Evidence: `command_outputs/schema_validation.txt`,
  `command_outputs/diff_check.txt`, `command_outputs/brittleness_check.txt`
  Evidence type: test

## Failure Scan

- Required: yes
- Path: `docs/failure_scans/BL-MAX-VALUE-001.md`
- Adjacent failures checked: malformed lifecycle locks, missing future assets,
  modified/removed assets, write rollback, runner availability, symlink escape,
  duplicate runtime ownership, stale proof, dirty-source metric drift, and exact-head mismatch
- Known bad events covered: unresolved correctness findings recorded against merged PR #5

## Worktree Dirty File Classification

| status | path | category | owner/notes |
| --- | --- | --- | --- |
| ?? | `docs/metrics/` | generated_artifact | Canonical metrics directory measured from proof HEAD |
| ?? | `docs/evidence/2026-07-11-maximum-value-correctness/` | generated_artifact | Typed evidence and captured command outputs |
| M | `docs/evidence/2026-07-11-maximum-value-correctness/README.md` | generated_artifact | Proof/final-head split and exact dirt classification |
| M | `docs/evidence/2026-07-11-maximum-value-correctness/manifest.json` | generated_artifact | Hash refresh for the tracked evidence README |
| M | `STATUS.md` | intended_slice_work | Final local/remote truth boundary update |
| M | `PROJECT_STATE.yaml` | intended_slice_work | Structured proof-head and gate-state update |
| M | `NEXT_ACTIONS.md` | intended_slice_work | Keep only the remaining publication action |
| M | `WORKLOG.md` | intended_slice_work | Append-only implementation history |
| M | `docs/EVIDENCE_LOG.md` | intended_slice_work | Append-only evidence ledger reference |

## Anti-Brittleness Review

| Question | Answer |
| --- | --- |
| What invariant prevents the failure class? | Every lifecycle transition is schema-valid, path-confined, preflighted, transactional, and derived from the current catalog; every truth transition is bound to an explicit proof head and artifact. |
| Is the fix typed/schema/state-machine/validator/contract-based? | Yes. Catalog, asset lock, runtime identity, evidence manifest, metrics, and agent context have executable contracts and semantic gates. |
| Which behavior is centralized instead of scattered? | Profile resolution and lifecycle ownership are centralized in the catalog/contracts; local validation is centralized in the quality gate; remote closure is centralized in the finalizer. |
| Which observed examples are covered by general rules rather than exact strings? | Absolute/traversal/symlink paths, duplicate keys, malformed locks, arbitrary future assets, any declared runner, any listener PID set, and any post-proof path are handled by typed/path/state rules. |
| What adjacent cases were tested? | Old and malformed locks, modifications/removals, rollback/idempotence, nested symlinks, multiple suites and missing runners, dirty same-HEAD runtime proof, process/port mismatch, remote opt-in, v1 rejection, and dirty metric generation. |
| What brittle pattern was explicitly avoided? | No prompt/keyword dispatch, fixture-name allowlist, sleep-based synchronization, provider-specific browser dependency, mtime evidence authority, or silent fallback establishes proof. |
| Did the slice add keyword buckets, regex branches, exact prompt handling, fixture-only behavior, sleeps/timeouts, global mutable state, silent fallback, or provider-specific assumptions? | No authority path uses those patterns. Regex is limited to typed format validation and advisory linting; subprocess timeouts bound tools rather than establish success. |
| If yes, why is that not the authority path? | Not applicable to the authority path. |

## Verification Log

| Check | Command / Path | Result |
| --- | --- | --- |
| automatically discovered script tests | `python3 -m pytest scripts/ -q` | pass: 289 tests, 4 subtests |
| schema examples | `python3 -m pytest schemas/examples/ -q` | pass: 5 tests |
| canonical metrics | `python3 scripts/statedd_profile_metrics.py --output docs/metrics/profile_metrics.json --template-commit ae851d05aa8113c3cde90d122d1723be123d9e37 --check` | pass: reproducible |
| schema validation | `python3 scripts/statedd_validate_schema.py` | pass |
| state hygiene | `python3 scripts/check_state_docs.py` | pass |
| runtime truth | `python3 scripts/statedd_runtime_truth_check.py --artifact docs/evidence/2026-07-11-maximum-value-correctness/runtime_identity.json` | pass: runtime not applicable |
| diff whitespace | `git diff --check HEAD` | pass |
| brittleness scan | `python3 scripts/statedd_brittleness_check.py` | pass: 0 heuristic warnings; manual review above |
| level-2 quality gate | `python3 scripts/statedd_quality_gate.py --gate-level 2` | pass |
| evidence manifest | `python3 scripts/statedd_evidence_pack.py check docs/evidence/2026-07-11-maximum-value-correctness --strict` | pass |
| worktree guard | `python3 scripts/statedd_worktree_guard.py --mode closure` | pending finalization commit |
| local audit | `python3 scripts/statedd_audit.py --strict --evidence-folder docs/evidence/2026-07-11-maximum-value-correctness` | pass: 42 checks, local readiness only |
| GitHub Actions | exact pushed PR head | not yet run |
| remote finalizer | `scripts/statedd_remote_closure_finalizer.py` | not yet run |

## Evidence Pack Manifest

- Manifest: `manifest.json`
- Redaction status: checked_with_limits; automated scan passed and manual review completed

## Runtime Identity

- Runtime required: no
- Artifact: `runtime_identity.json`
- Endpoint: not applicable; template root has no application runtime
- Process ownership proven: not applicable
- Known limits: This artifact proves runtime non-applicability and local proof-head identity, not remote branch, PR, CI, merge, or acceptance truth.

## Browser Verification

- Browser verification required: no
- Browser verification artifact: not applicable
- Provider used: not applicable
- Fallbacks considered: not applicable
- Known browser verification limits: No user-facing application behavior changed in the template root.

## Closure State

- Implemented: yes
- Validated: local focused and automatically discovered suites passed
- Global quality gates passed: yes locally at level 2
- Closure-grade: no; branch is not pushed and CI/remote finalizer have not run
- Accepted: pending
- Final PR head: intentionally not embedded in tracked evidence; the exact final
  head belongs in the mutable PR body after publication.

## Human Override

- Human override used: no

## Risks / What Remains Partial

- Remote branch publication, pull-request state, exact-head GitHub Actions, and
  remote finalizer agreement are not yet proven.
- Windows/macOS behavior remains unproven; Linux is the validated execution platform.
- Controlled evidence that StateDD outperforms a simpler workflow remains a future benchmark, not a claim of this slice.
