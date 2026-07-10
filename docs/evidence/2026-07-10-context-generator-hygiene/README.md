# Evidence: Generated-Repo Correctness And Context Hygiene

**Slice:** [BL-CONTEXT-001] Generated-repo correctness and context hygiene
**Date:** 2026-07-10
**Agent:** coding-agent
**Branch:** bl-bl-context-001-code-a1daa
**HEAD:** pending final state commit
**Proof head:** 8840a3c2bed468b6440705c031dcc0015df807d1
**Final PR head:** not yet pushed

## Claims

- Claim: Every generated profile passes its own quality gate without receiving template-maintenance tests.
  Evidence: `scripts/test_adoption_profiles.py`, `.github/workflows/validate.yml`, `command_outputs/verification.txt`
  Evidence type: test

- Claim: Profile output is an explicit schema-backed allowlist that excludes fixtures, template history, incidents, evidence, changelog, release material, and template tests.
  Evidence: `scripts/init_template.py`, `schemas/statedd_assets.schema.json`, `scripts/test_init_template.py`
  Evidence type: implementation | test

- Claim: `minimal` is materially smaller than `solo`, has the smallest normalized startup payload of every profile, and startup/footprint files, bytes, and estimated tokens have enforced budgets.
  Evidence: `EFFICIENCY_BUDGET.yaml`, `scripts/statedd_efficiency_check.py`, `scripts/test_efficiency_check.py`, `scripts/test_adoption_profiles.py`
  Evidence type: implementation | test

- Claim: Duplicate YAML mapping keys fail at root and nested levels rather than silently overwriting state.
  Evidence: `scripts/statedd_validate_schema.py`, `scripts/test_schema_validation.py`
  Evidence type: adversarial | test

- Claim: Active problems are canonical for STATUS P0/P1 failures, queue IDs must be in backlog NOW, and terminal worklog IDs cannot remain active.
  Evidence: `scripts/check_state_docs.py`, `scripts/test_check_state_docs.py`
  Evidence type: state_update | adversarial | test

- Claim: Ephemeral StateDD agent context does not make an otherwise clean isolated worktree fail closure.
  Evidence: `.gitignore`, `scripts/test_agent_worktree.py`
  Evidence type: implementation | test

## Failure Scan

- Required: yes
- Path: `docs/failure_scans/BL-CONTEXT-001.md`
- Adjacent failures checked: profile dependency omissions, upgrade recontamination, duplicate nested keys, footprint gaming, lifecycle false positives, and opaque compression.
- Known bad events covered: fresh downstream self-gate failure after 99 passing copied tests; oversized pseudo-minimal profile; duplicate generated `invariants`; stale queue/problem/history disagreement.

## Worktree Dirty File Classification

| status | path | category | owner/notes |
| --- | --- | --- | --- |
| M | `.gitignore` | intended_slice_work | ignore ephemeral StateDD agent context in template and generated repositories |
| M | `.github/workflows/validate.yml` | intended_slice_work | generated-profile self-gate matrix |
| M | `BACKLOG.md` | intended_slice_work | active slice and corrected parallel-closure state |
| M | `EFFICIENCY_BUDGET.yaml` | intended_slice_work | startup and footprint budgets |
| M | `NEXT_ACTIONS.md` | intended_slice_work | active slice queue |
| M | `PROJECT_STATE.yaml` | intended_slice_work | canonical active problem truth |
| M | `README.md` | intended_slice_work | explicit generated asset boundary |
| M | `STATUS.md` | intended_slice_work | open P1 and current gate truth |
| M | `WORKLOG.md` | intended_slice_work | append-only local validation record |
| M | `docs/ADOPTION_PROFILES.md` | intended_slice_work | corrected profile contract |
| M | `docs/EVIDENCE_LOG.md` | intended_slice_work | baseline evidence entry |
| M | `fixtures/bootstrap_dry_run/bootstrap/NEXT_ACTIONS.md` | intended_slice_work | remove queued transition not in backlog NOW |
| M | `scripts/AGENTS.md` | intended_slice_work | executable catalog updates |
| M | `scripts/check_state_docs.py` | intended_slice_work | semantic lifecycle validator |
| M | `scripts/init_template.py` | intended_slice_work | allowlisted generator and compact state |
| M | `scripts/statedd_efficiency_check.py` | intended_slice_work | context/footprint metrics and strict budget parsing |
| M | `scripts/statedd_quality_gate.py` | intended_slice_work | project test/config detection |
| M | `scripts/statedd_upgrade.py` | intended_slice_work | manifest-scoped upgrades without tests/history |
| M | `scripts/statedd_validate_schema.py` | intended_slice_work | strict duplicate YAML keys |
| M | `scripts/statedd_version_check.py` | intended_slice_work | downstream no longer requires initializer |
| M | `scripts/statedd_worktree_guard.py` | intended_slice_work | preserve Git porcelain leading status columns |
| M | `scripts/test_adoption_profiles.py` | intended_slice_work | profile self-gates and footprint matrix |
| M | `scripts/test_agent_worktree.py` | intended_slice_work | ephemeral context cleanliness regression |
| M | `scripts/test_check_state_docs.py` | intended_slice_work | lifecycle adversaries |
| M | `scripts/test_efficiency_check.py` | intended_slice_work | metric/budget adversaries |
| M | `scripts/test_init_template.py` | intended_slice_work | manifest/exclusion regressions |
| M | `scripts/test_schema_validation.py` | intended_slice_work | duplicate-key adversaries |
| M | `scripts/test_upgrade.py` | intended_slice_work | upgrade exclusion regression |
| M | `scripts/test_worktree_guard.py` | intended_slice_work | hidden-path porcelain regression |
| ?? | `.statedd/agent.context` | generated_artifact | isolated worktree ownership context; never commit |
| ?? | `docs/evidence/2026-07-10-context-generator-hygiene/README.md` | generated_artifact | slice evidence ledger |
| ?? | `docs/evidence/2026-07-10-context-generator-hygiene/manifest.json` | generated_artifact | evidence manifest |
| ?? | `docs/evidence/2026-07-10-context-generator-hygiene/runtime_identity.json` | generated_artifact | no-runtime-required proof |
| ?? | `docs/evidence/2026-07-10-context-generator-hygiene/command_outputs/verification.txt` | generated_artifact | compact verification transcript |
| ?? | `docs/failure_scans/BL-CONTEXT-001.md` | generated_artifact | pre-mortem and adjacent failures |
| ?? | `schemas/statedd_assets.schema.json` | intended_slice_work | generated asset manifest contract |

## Anti-Brittleness Review

| Question | Answer |
| --- | --- |
| What invariant prevents the failure class? | Profiles are explicit allowlists with a validated emitted manifest; every profile self-gates; strict parsers reject duplicate keys; lifecycle sets must agree semantically. |
| Is the fix typed/schema/state-machine/validator/contract-based? | Yes: JSON Schema plus manifest validation, strict YAML mapping validation, budget contracts, and lifecycle set validation. |
| Which behavior is centralized instead of scattered? | Profile assets are centralized in `PROFILE_ASSET_PATHS`; YAML parsing is shared by schema and efficiency checks; cross-file lifecycle authority is centralized in `check_cross_file_rules`. |
| Which observed examples are covered by general rules rather than exact strings? | Any repeated mapping key, any declared profile asset, any queue/backlog ID, any P0/P1 active problem, and any exact terminal worklog state use general validators. |
| What adjacent cases were tested? | Root/nested duplicate keys, missing/duplicate/unsafe manifest paths, all profiles, normalized startup-context ordering, legacy minimal alias, adoption, profile budgets, CLOSED queue IDs, STATUS disagreement, and terminal worklog IDs. |
| What brittle pattern was explicitly avoided? | No observed-file deletion list, copied-directory cleanup, token-obscuring abbreviations, installed-tool guessing, fixture-only authority, sleeps, silent success fallback, or provider-specific behavior. |
| Did the slice add keyword buckets, regex branches, exact prompt handling, fixture-only behavior, sleeps/timeouts, global mutable state, silent fallback, or provider-specific assumptions? | Structured Markdown headings/IDs use bounded regex extraction, but strict YAML/schema data and lifecycle sets remain the authority. No provider or timing behavior was added. |
| If yes, why is that not the authority path? | Regex only extracts the existing Markdown view format; closure decisions compare extracted IDs with canonical parsed state and explicit terminal enums. |

## Verification Log

| Check | Command / Path | Result |
| --- | --- | --- |
| full script suite | `python3 -m pytest scripts/ -q` | pass after closure-context fix: 164 tests, 4 subtests |
| generated profile self-gates | `python3 scripts/test_adoption_profiles.py` | pass: all profiles self-gate; normalized `minimal` startup is strictly smallest |
| schema validation | `python3 scripts/statedd_validate_schema.py` | pass |
| state semantics/hygiene | `python3 scripts/check_state_docs.py --bootstrap-gate` | pass |
| context/footprint budget | `python3 scripts/statedd_efficiency_check.py --gate-level 2` | pass |
| evidence manifest | `python3 scripts/statedd_evidence_pack.py check docs/evidence/2026-07-10-context-generator-hygiene --strict` | pass after final rehash |
| worktree guard | `python3 scripts/statedd_worktree_guard.py --mode start-slice` | pass in isolated agent worktree; dirt now classified here |
| agent worktree regression | `python3 scripts/test_agent_worktree.py` | pass: context exists, is ignored, and worktree remains clean |
| brittleness scan | `python3 scripts/statedd_brittleness_check.py --base 976a3f0...` | pass: 0 heuristic warnings; manual review complete |
| audit | `python3 scripts/statedd_audit.py --strict` | pass: 37 checks; all five dirty files classified before final commit |
| runtime identity proof | `runtime_identity.json` | valid; runtime not applicable |
| product quality gate | generated profile quality gates | pass |
| runtime truth gate | not applicable | template root has no application runtime |
| redteam/adversarial gate | duplicate YAML, footprint, manifest, lifecycle regressions | pass |
| known bad events gate | baseline failure reproduced then protected by regressions | pass |
| GitHub Actions proof head | runs `29120524026`, `29120525510` on `8840a3c` | pass |

GitHub CI initially falsified closure by finding the bootstrap fixture queued
BL-004 while its backlog placed BL-004 in NEXT. The fixture queue was corrected;
the semantic validator was not weakened.

## Evidence Pack Manifest

- Manifest: `manifest.json`
- Redaction status: checked with automated-scan limits; manual review completed

## Runtime Identity

- Runtime required: no
- Artifact: `runtime_identity.json`
- Endpoint: not applicable
- Process ownership proven: not applicable
- Known limits: template-maintenance scripts/docs slice; no application runtime exists.

## Browser Verification

- Browser verification required: not applicable
- Browser verification artifact: not applicable
- Provider used: not applicable
- Fallbacks considered: not applicable
- Known browser verification limits: no user-facing runtime or rendered UI changed.

## Closure State

- Implemented: yes
- Validated: yes, locally
- Global quality gates passed: yes locally; remote CI pending
- Closure-grade: conditional on GitHub Actions and the remote closure finalizer passing on the final state commit
- Accepted: pending

## Human Override

- Human override used: no

## Risks / What Remains Partial

- Compact, modular, ephemeral, and ultra-terse model-facing context remain benchmark variants; canonical state was not rewritten into ambiguous abbreviations.
- Human acceptance/merge remain pending after remote closure.
