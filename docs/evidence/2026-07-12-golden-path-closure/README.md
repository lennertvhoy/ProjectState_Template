# Evidence: Agent-Owned Golden-Path Closure

**Slice:** [BL-GOLDEN-PATH-CLOSURE-001] Complete agent-owned merge,
post-merge verification, and self-reconciling remote truth  
**Date:** 2026-07-12  
**Agent:** integration coding agent  
**Branch:** `bl-golden-path-closure-001`  
**HEAD:** b46c97a7b643459185f21d7bd0bfd4a8d03017a0  
**Proof head:** b46c97a7b643459185f21d7bd0bfd4a8d03017a0

## Claims

- Claim: Structured bootstrap records one human-confirmed `human_merge` or
  `agent_after_green` policy and never treats a proposal as authority.
  Evidence: `source_hashes.json`, `verification_summary.json`
  Evidence type: implementation, test
- Claim: One typed, idempotent command gates draft readiness, exact-head CI,
  review/thread/merge state, remote closure, expected-head squash merge, direct
  default-branch CI, post-merge proof, cleanup, and external handoff.
  Evidence: `source_hashes.json`, `verification_summary.json`
  Evidence type: implementation, adversarial
- Claim: Tracked proof does not predict provider-created post-merge identities;
  source-tree or stable-patch equivalence binds a squash result externally.
  Evidence: `source_hashes.json`, `verification_summary.json`
  Evidence type: implementation, regression
- Claim: Semantic state checks reject terminal work left active, quality freeze
  without an open P0, and volatile containing-commit coupling.
  Evidence: `verification_summary.json`
  Evidence type: test, state_update
- Claim: The complete generated-team journey reaches agent-owned merge, direct
  main CI, post-merge handoff, remote-branch cleanup, isolation release, zero
  open slice PRs, and zero human Git actions through a deterministic provider fake.
  Evidence: `verification_summary.json`
  Evidence type: product_behavior, test

## Failure Scan

- Required: yes
- Path: `docs/failure_scans/BL-GOLDEN-PATH-CLOSURE-001.md`
- Adjacent failures checked: unconfirmed/manual policy, pending/failed CI,
  changed head, requested changes, unresolved threads, dirty merge state,
  wrong base branch, API failure, main-CI failure, rerun after merge, premature
  cleanup, future identity in tracked evidence, and terminal active state.
- Known bad events covered: the human-only final merge boundary, the future-SHA
  repair loop, and stale canonical current state.

## Worktree Dirty File Classification

| status | path | category | owner/notes |
| --- | --- | --- | --- |
| clean | not applicable | intended slice work committed at proof head | integration agent |
| generated finalization | this evidence folder and `docs/metrics/profile_metrics.json` | generated artifact | allowed proof-to-final metadata only |

## Anti-Brittleness Review

| Question | Answer |
| --- | --- |
| What invariant prevents the failure class? | A confirmed policy gates a typed state machine that re-queries immutable remote truth immediately before each destructive transition. |
| Is the fix typed/schema/state-machine/validator/contract-based? | Yes: policy schema/helpers, provider protocol, finish stages, handoff schema, semantic state validator, and evidence bindings. |
| Which behavior is centralized instead of scattered? | Merge authorization, exact-head checks, CI subject checks, post-merge verification, cleanup ordering, and external handoff persistence. |
| Which observed examples are covered by general rules rather than exact strings? | Policy states, CI observations, review/thread state, PR identity, merge result, default-branch truth, evidence hashes, and terminal backlog semantics. |
| What adjacent cases were tested? | Both policy modes, malformed/unconfirmed policy, all CI failure states, review and merge blockers, head/base movement, API/main-CI failure, idempotent rerun, and cleanup order. |
| What brittle pattern was explicitly avoided? | No fixed sleep as authority, keyword-only state repair, provider auto-merge dependency, ancestry-only squash proof, silent fallback, or future-SHA placeholder. |
| Did the slice add provider-specific assumptions? | The orchestration core is provider-neutral; GitHub behavior is isolated in one adapter and tested against typed fake-provider observations. |
| If yes, why is that not the authority path? | The adapter translates GitHub into the provider protocol; the state machine and policy contract remain the authority. |

## Verification Log

| Check | Command / Path | Result |
| --- | --- | --- |
| compile | `python3 -m compileall -q scripts schemas/examples` | pass |
| lint | `ruff check scripts` | pass |
| script suite | `python3 -m pytest scripts/ -q` | pass |
| schema examples | `python3 -m pytest schemas/examples/ -q` | pass |
| complete journey | `python3 scripts/test_golden_path.py` | pass |
| schema validation | `python3 scripts/statedd_validate_schema.py` | pass |
| state hygiene | `python3 scripts/check_state_docs.py` | pass |
| bootstrap gate | `python3 scripts/check_state_docs.py --bootstrap-gate` | pass |
| instruction lint | `python3 scripts/statedd_instruction_lint.py --fail-on error` | pass with one non-error README routing warning |
| efficiency | `python3 scripts/statedd_efficiency_check.py --gate-level 2` | pass |
| generated profiles | `python3 scripts/statedd_profile_metrics.py --check` | pass; every profile ran its declared conformance gate |
| runtime identity | `runtime_identity.json` | not applicable; clean repo capture |
| product/runtime/browser gates | template root | not applicable |

## Evidence Pack Manifest

- Manifest: `manifest.json`
- Redaction status: checked with limits

## Runtime Identity

- Runtime required: no
- Artifact: `runtime_identity.json`
- Endpoint: not applicable
- Process ownership proven: not applicable
- Known limits: the template root has no deployed application runtime.

## Browser Verification

- Browser verification required: not applicable
- Browser verification artifact: not applicable
- Provider used: not applicable
- Known limits: this slice changes repository scripts/contracts rather than a
  user-facing application runtime; GitHub API and CI are the remote truth boundary.

## Closure State At Tracked Proof

- Implemented: yes
- Validated locally: yes
- Global local quality gates passed: pending final evidence/state commit rerun
- Remote closure: pending
- Human product acceptance: pending

Provider-created merge/default-head/CI identities belong only in the external
finish handoff. This tracked README intentionally contains no future merge identity.

## Human Override

- Human override used: yes
- Rule overridden: the prior universal human-only merge and remote-branch cleanup boundary
- Requested by: human
- Reason accepted: authorize this final slice to prove the confirmed
  `agent_after_green` golden path without routine human Git actions
- Remaining risk: remote PR/CI/merge/default-branch truth is pending until the
  finish command completes
- Still closure-grade at tracked proof: no

## Risks / What Remains Partial

- Verified legal copyright owner is not proven; `LICENSE` is unchanged.
- Human product acceptance is pending.
- Comparative benchmark superiority is not proven.
- Optional StateIR/StatePack and BL-OKF-002 research remain evidence-gated future work.
