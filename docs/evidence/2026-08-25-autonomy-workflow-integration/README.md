# Evidence: Autonomous Improvement Workflow Integration

**Slice:** [BL-AUTONOMY-001] Integrate the autonomous improvement workflow
**Date:** 2026-08-25
**Agent:** opencode integration agent (ox-alpha)
**Branch:** `bl-autonomy-001-improve-workflow`
**Proof head:** 7db9a8caed24f3c5d18990cfe91031a9cfda7e51

## Claims

- Claim: The improve skill (`skills/improve/SKILL.md`) and command
  (`commands/projectstate-improve.md`) exist and pass every structural
  instruction gate (gate_level declared, failure cases present, step caps,
  size budgets, reference corpus).
  Evidence: `quality_gate_output.txt`
  Evidence type: implementation, test
- Claim: `AGENTS.md` carries the L0-L4 Autonomy Ladder while staying within
  its exact 110-line root budget.
  Evidence: `quality_gate_output.txt`, `run_notes.md`
  Evidence type: implementation, test
- Claim: Subsystem enumeration drift is repaired: git-safety skill listed in
  root AGENTS.md; copilot mirror lists refreshed with the false auto-generated
  claim corrected; prompts catalog lists NEW_PROJECT_FROM_URL.md; the
  beginners-doc contradiction with delegated slice selection is qualified.
  Evidence: `run_notes.md`
  Evidence type: state_update
- Claim: Repository mutation was authorized by a writable-grade Git safety
  preflight on the private slice branch before any edit.
  Evidence: `git_safety_report.json`
  Evidence type: implementation
- Claim: The full CI-parity level-2 conformance gate passes with all changes
  in tree (compileall, profile policy/validations, profile-metrics
  reproduction under tiktoken==0.12.0, full pytest suite, ruff, state-doc
  hygiene, schema validation, instruction lint, efficiency budgets).
  Evidence: `quality_gate_output.txt`
  Evidence type: test

## Failure Scan

- Required: no
- Path: not applicable; documentation/workflow-configuration slice with no
  product runtime behavior and no reproduced failure driving it.
- Known bad event considered: an agent invoking `/projectstate-improve` could
  have read contradictory guidance ("the coding agent should not choose the
  next slice") and stalled; prevented by qualifying that line for explicitly
  invoked improve runs.

## Worktree Dirty File Classification

| status | path | category | owner/notes |
| --- | --- | --- | --- |
| modified/new | all files in `git status --short` at verification time | intended_slice_work | BL-AUTONOMY-001 |
| pre-existing dirty WIP | none in canonical checkout | not_applicable | clean start verified by preflight |

## Anti-Brittleness Review

| Question | Answer |
| --- | --- |
| What invariant prevents the failure class? | The Autonomy Ladder conditions autonomous implementation on explicit invocation of `/projectstate-improve`; closure still requires the unchanged executable gates. |
| Is the fix typed/schema/state-machine/validator/contract-based? | Yes: the loop is a contract enforced by existing validators (efficiency, instruction lint, hygiene, quality gate), not by prose trust. |
| Which behavior is centralized instead of scattered? | Selection authority, prioritization formula, stop conditions, and report contract live in one skill referenced by one command. |
| Which observed examples are covered by general rules rather than exact strings? | Any local reversible change class, any external/irreversible action class, and either stop condition are described generically, not as enumerated fixtures. |
| What adjacent cases were tested? | Conflicting-instruction lint against existing "only the user may instruct" invariant; budget edge (AGENTS.md exactly 110 lines); unreferenced-skill detection; manifest strict check. |
| What brittle pattern was explicitly avoided? | No keyword allowlist of "allowed improvements", no duplicated mandate document, no new gate that merely re-proves existing gates. |
| Did the slice add provider-specific assumptions? | No. The workflow is runtime-agnostic markdown plus existing Python gates. |
| If yes, why is that not the authority path? | Not applicable. |

## Verification Log

| Check | Command / Path | Result |
| --- | --- | --- |
| Git safety preflight (writable) | `projectstate_git_safety_check.py --mode normal_branch --sync fetch` | pass; mutation permitted |
| focused lint | `python3 scripts/projectstate_instruction_lint.py --fail-on error` | pass; 0 errors |
| efficiency budgets | `python3 scripts/projectstate_efficiency_check.py --gate-level 2` | pass; 382 files / 2,607,940 bytes |
| full level-2 quality gate | `python3 scripts/projectstate_quality_gate.py --gate-level 2 --conformance --verbose` | pass; exit 0 (see `quality_gate_output.txt`) |
| evidence manifest strict | `projectstate_evidence_pack.py check . --strict` | pass |

## Evidence Pack Manifest

- Manifest: `manifest.json`
- Redaction status: checked with limits; automated scan passed and manual review completed

## Runtime Identity

- Runtime required: no
- Artifact: not applicable
- Endpoint/process ownership: template root has no application runtime; repo
  truth is not runtime truth.

## Browser Verification

- Browser verification required: no
- Provider/artifact: not applicable
- Reason: this slice changes agent-facing workflow contracts and docs only.

## Closure State At Current Worktree

- Implemented: yes, captured at immutable proof head `7db9a8caed24f3c5d18990cfe91031a9cfda7e51`
- Validated locally: yes; authoritative level-2 aggregate passes
- Closure-grade: no — remote closure has not run
- Remote closure: pending (push, PR, exact-head CI, merge, direct-main CI)
- Human product acceptance: pending

## Human Override

- Human override used: no
- Rule overridden: not applicable
- Requested by: not applicable
- Reason accepted: not applicable
- Remaining risk: the delivery decision (commit/push/PR timing) stays with the human per session scope, so this pack intentionally stops at LOCAL_VALIDATED
- Still closure-grade: no, by the Remote Truth Gate

## Risks / What Remains Partial

- Remote closure for BL-AUTONOMY-001 is pending; nothing here proves pushed,
  PR-opened, merged, or CI-verified states.
- Shipping `skills/improve/` and the command to generated downstream repos
  requires a follow-up slice: register both paths in a
  `profiles/catalog.json` asset set, bump its version, and regenerate
  profile metrics against the merged commit.
- `docs/ACCEPTANCE_FREEZES.md` retains two dangling references to a v4
  release-notes filename that never existed under that name; the ledger is
  append-only, so repair was parked with rationale in `run_notes.md`.
