# Evidence: Safe downstream closure controls

**Slice:** [BL-TEMPLATE-DOWNSTREAM-CLOSURE-001] Add safe profile migration and managed clone resume
**Date:** 2026-08-29
**Agent:** opencode integration agent (agent-opencode)
**Branch:** `bl-bl-template-downstream-closure-001-agen-pscab`
**HEAD:** 949e412dac6c166c61eb4d7c73e362066e9f1456 (proof tree)
Proof head: 949e412dac6c166c61eb4d7c73e362066e9f1456

## Claims

- Claim: Managed clone resume requires an explicit branch, reads the exact remote
  branch head, optionally enforces an expected full SHA, and keeps independent
  clone isolation without mutating the source repository.
  Evidence: `pytest_output.txt`, `quality_gate_output.txt`
  Evidence type: implementation, test
- Claim: Explicit forward profile migration is transactional, preserves project
  truth, updates both canonical profile fields, records `upgrade_history`, and
  rejects downgrade or metadata-conflict paths without writes.
  Evidence: `pytest_output.txt`, `schema_validation_output.txt`
  Evidence type: implementation, test, schema
- Claim: Generated profiles remain within their measured footprint budgets and
  all applicable repository/profile quality contracts pass.
  Evidence: `quality_gate_output.txt`, `profile_metrics_check.txt`
  Evidence type: test, conformance
- Claim: The template root has no application runtime; this slice is tooling and
  contract work only.
  Evidence: `README.md`
  Evidence type: runtime_boundary

## Failure Scan

- Required: no
- Path: not applicable; deterministic tooling, schema, migration, and clone
  lifecycle regressions are covered by the repository suite.
- Known environmental issue: the default `/tmp` quota was exhausted during the
  first full-suite attempt; the verified rerun used
  `TMPDIR=/home/ff/.cache/projectstate-tests`.

## Worktree Dirty File Classification

| status | path | category | owner/notes |
| --- | --- | --- | --- |
| modified/new | finalization files listed in the closing commit | intended_slice_work | BL-TEMPLATE-DOWNSTREAM-CLOSURE-001 |

## Anti-Brittleness Review

| Question | Answer |
| --- | --- |
| What invariant prevents the failure class? | A resume branch and optional exact head are explicit inputs; profile metadata, manifest profile, and asset ownership must agree before mutation. |
| Is the fix typed/schema/state-machine/validator/contract-based? | Yes: branch/ref validation, transactional preflight, schema fields, metadata agreement validation, and migration history are enforced contracts. |
| Which behavior is centralized instead of scattered? | Profile transition policy is centralized in the upgrader; clone resume identity is centralized in the managed clone orchestrator. |
| Which observed examples are covered by general rules? | Any known forward profile transition, any valid remote branch name, and any full expected Git SHA use the same validators. |
| What adjacent cases were tested? | Missing branch, invalid head, downgrade, manifest/metadata mismatch, project-truth preservation, generated profile conformance, and idempotent upgrade behavior. |
| What brittle pattern was explicitly avoided? | No string-wide project rewrite, guessed branch selection, force overwrite, or partial write on a rejected migration. |
| Did the slice add provider-specific assumptions? | No. |
| If yes, why is that not the authority path? | Not applicable. |

## Verification Log

| Check | Command / Path | Result |
| --- | --- | --- |
| full test suite | `TMPDIR=/home/ff/.cache/projectstate-tests python3 -m pytest -q` | pass; all tests passed |
| schema validation | `python3 scripts/projectstate_validate_schema.py .` | pass |
| documentation/state validation | `python3 scripts/check_state_docs.py .` | pass |
| profile metrics | `python3 scripts/projectstate_profile_metrics.py --output docs/metrics/profile_metrics.json --template-commit 949e412dac6c166c61eb4d7c73e362066e9f1456` | pass; regenerated from proof head |
| quality gate | `python3 scripts/projectstate_quality_gate.py --gate-level 2` | pass; exit 0 |
| evidence manifest | `python3 scripts/projectstate_evidence_pack.py check ... --strict` | pass |

## Evidence Pack Manifest

- Manifest: `manifest.json`
- Redaction status: checked with limits; automated scan passed and manual review completed

## Runtime Identity

- Runtime required: no
- Reason: template tooling and repository contract changes only.

## Browser Verification

- Browser verification required: no
- Reason: no user-facing application runtime changed.

## Closure State

- Implemented: yes; captured at immutable proof head `949e412dac6c166c61eb4d7c73e362066e9f1456`
- Validated locally: yes; authoritative Level-2 gate passed
- Closure-grade: no until remote finalization
- Remote closure: pending
- Human product acceptance: pending

## Human Override

- Human override used: no

## Risks / What Remains Partial

- Remote PR creation, exact-head CI, review state, merge, and post-merge verification remain pending.
- The default `/tmp` disk-quota condition remains an environment constraint; verified commands use the alternate cache-backed temporary directory.
