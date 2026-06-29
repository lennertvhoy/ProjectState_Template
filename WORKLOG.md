# WORKLOG

**Purpose:** Append-only history for completed work.

## 2026-06-29 - StateDD repo coherence and efficiency repair (BL-SANITY-001)

**Type:** template_maintenance_capability  
**Status:** COMPLETE  
**Git Head:** main at 6f9cc99e7fe3bb5be7c67bc422536e80c26835e6  
**Worktree:** clean  
**Gate Level:** 2 (slice closure)  

### What changed
- Reconciled the efficiency layer from the open PR #2 as a minimal salvage:
  - Added `EFFICIENCY_BUDGET.yaml` with hard limits on instruction size, state queues, evidence bundles, and gate runtimes.
  - Added `scripts/statedd_efficiency_check.py` to enforce the budget.
  - Added `scripts/test_efficiency_check.py` with regression tests.
  - Added `fixtures/efficiency_bloat_overcorrection/` regression fixture proving the checker fails on bloat overcorrection.
  - Wired the efficiency check into `scripts/statedd_quality_gate.py` and `scripts/statedd_closure_check.py`.
  - Added `gate_level`, `evidence_max`, `cheapest_proof`, and `escalate_when` metadata to all skills and commands.
  - Added the Efficiency Invariant and Gate Levels to `AGENTS.md`.
- Added backlog structure validation to `scripts/check_state_docs.py`:
  - Fails on duplicate second-level sections such as repeated `## CLOSED`.
  - Fails on duplicate backlog IDs unless explicitly allowed in a history-only section.
  - Added `scripts/test_check_state_docs.py` regression coverage.
- Repaired `BACKLOG.md` to remove duplicate `## CLOSED` sections and duplicate BL-005.
- Repaired remote closure evidence for BL-REMOTE-CLOSURE-001 to match the actual merge commit `ba52e09...`.
- Added `scripts/statedd_post_merge_verify.py` and `scripts/test_post_merge_verify.py` to prove default-branch truth after a PR merges.
- Updated `.github/workflows/validate.yml` to compile and run the new efficiency and sanity checks.
- Updated truth files to reflect BL-SANITY-001 as closed and BL-BROWSER-002 as active.

### Verification
- `python3 -m pytest -q` → 132 passed, 4 subtests passed.
- `python3 scripts/check_state_docs.py --bootstrap-gate` passes.
- `python3 scripts/statedd_validate_schema.py` passes.
- `python3 scripts/statedd_efficiency_check.py --gate-level 2` passes.
- `python3 scripts/statedd_evidence_pack.py check docs/evidence/2026-06-29-sanity-repair --strict` passes.

### Evidence
- `docs/EVIDENCE_LOG.md` entry `EV-2026-06-29-002`
- `docs/evidence/2026-06-29-sanity-repair/README.md`
- `docs/evidence/2026-06-29-sanity-repair/runtime_identity.json`
- `docs/evidence/2026-06-29-sanity-repair/manifest.json`

### Notes
- Merged directly to main; PR #2 closed as superseded.
- BL-BROWSER-002 is now the active slice.

## 2026-06-28 - Quality firewall template hardening (BL-QUALITY-001)

**Type:** template_maintenance_capability
**Status:** COMPLETE
**Git Head:** 5dd388fc888fe8e6057046d7c94fc50cffb07da6 before final commit
**Worktree:** dirty during evidence capture

### What changed
- Added reusable quality firewall, failure taxonomy, incident response, failure scan, incident, and quality gate docs.
- Updated the root contract/state/backlog/evidence taxonomy to distinguish product truth, runtime truth, adversarial proof, known bad events, post-deploy evidence, and handoff claims.
- Updated generated downstream templates, schema support, prompt templates, initializer tests, and upgrade tests so new/adopted/upgraded repos receive the generic quality firewall assets.

### Verification
- `python3 scripts/check_state_docs.py` passed.
- `python3 scripts/statedd_validate_schema.py` passed.
- `python3 scripts/test_init_template.py` passed.
- `python3 scripts/test_upgrade.py` passed.
- `python3 scripts/statedd_evidence_pack.py check docs/evidence/2026-06-28-quality-firewall-template --strict` passed.

### Evidence
- `docs/EVIDENCE_LOG.md` entry `EV-2026-06-28-001`
- `docs/evidence/2026-06-28-quality-firewall-template/README.md`

## 2026-06-23 - Public usability and release-readiness polish (BL-007)

**Type:** template_maintenance_docs
**Status:** COMPLETE
**Git Head:** 6a417c1 before closure commit
**Worktree:** clean after final commit

### What changed
- Rewrote the top half of `README.md` for fast comprehension: "Start here" with copy-paste commands, default `solo` profile, agent paste prompt, and "Start Simple" guidance.
- Added `docs/QUICK_COMMANDS.md` with copy-pasteable commands for new repo, adopt, upgrade, daily checks, closure audit, evidence/runtime proof, handoff helper, and bootstrap gate.
- Improved `docs/ADOPTION_PROFILES.md` with a decision tree and explicit "Default recommendation: `solo`".
- Polished `docs/GETTING_STARTED_5_MIN.md` so a beginner can follow it without reading the full README first; linked to `docs/QUICK_COMMANDS.md` and `docs/ADOPTION_PROFILES.md`.
- Finalized `docs/RELEASE_NOTES_statedd-template-v4.md` as release-candidate ready with a clear note that GitHub release publishing requires explicit human permission.
- Created `docs/evidence/2026-06-23-release-readiness-polish/` with README claim ledger, `runtime_identity.json`, `manifest.json`, and `command_outputs/verification_log.txt`.
- Updated `BACKLOG.md`, `NEXT_ACTIONS.md`, `STATUS.md`, `PROJECT_STATE.yaml`, `CHANGELOG.md`, and `docs/EVIDENCE_LOG.md`.
- Did not implement BL-WB-001, browser automation, OCR, external dependencies, or GitHub release publishing.

### Verification
- `python3 -m py_compile` passed for all listed Python scripts.
- `python3 scripts/statedd_version_check.py` passed.
- `python3 scripts/statedd_validate_schema.py` passed.
- `python3 scripts/check_state_docs.py` passed.
- `python3 scripts/check_state_docs.py --bootstrap-gate` passed.
- `python3 scripts/test_runtime_proof.py` passed.
- `python3 scripts/test_schema_validation.py` passed.
- `python3 scripts/test_evidence_pack.py` passed.
- `python3 scripts/test_upgrade.py` passed.
- `python3 scripts/test_adoption_profiles.py` passed.
- `python3 scripts/test_init_template.py` passed.
- `python3 schemas/examples/schema_prompt_loop/validate_example.py` passed.
- `python3 schemas/examples/schema_prompt_loop/generate_prompt.py` passed.
- `python3 schemas/examples/schema_prompt_loop/test_schema_prompt_loop.py` passed.
- `python3 scripts/statedd_audit.py` passed.
- `python3 scripts/statedd_audit.py --strict` passed after final commit.
- `python3 scripts/statedd_doctor.py` passed.
- `python3 scripts/statedd_evidence_pack.py check docs/evidence/2026-06-23-release-readiness-polish --strict` passed.
- `git diff --check` passed.

### Evidence
- `docs/evidence/2026-06-23-release-readiness-polish/README.md`
- `docs/evidence/2026-06-23-release-readiness-polish/runtime_identity.json`
- `docs/evidence/2026-06-23-release-readiness-polish/manifest.json`
- `docs/evidence/2026-06-23-release-readiness-polish/command_outputs/verification_log.txt`
- `docs/EVIDENCE_LOG.md` entry `EV-2026-06-23-008`

### Notes
- BL-007 is closure-grade but not yet accepted; acceptance is pending human product owner review.
- GitHub release publishing is intentionally deferred until explicitly permitted.

## 2026-06-23 - Provider-agnostic browser verification contract (BL-BROWSER-001)

**Type:** template_maintenance_capability
**Status:** COMPLETE
**Git Head:** eb0cd886e900c2e35ddb8123b9fd599631335f89
**Worktree:** clean after final commit

### What changed
- Renamed the old `BL-WB-001` Kimi-WebBridge-specific backlog item to `BL-BROWSER-001` and documented provider-agnostic browser verification across `BACKLOG.md`, `NEXT_ACTIONS.md`, `STATUS.md`, `PROJECT_STATE.yaml`, `AGENTS.md`, `README.md`, `docs/QUICK_COMMANDS.md`, `docs/RELEASE_NOTES_statedd-template-v4.md`, `docs/ACCEPTANCE_FREEZES.md`, and `CHANGELOG.md`.
- Added acceptance freeze `AF-2026-06-23-004` for BL-007 public usability and release-readiness polish.
- Added `schemas/browser_verification.schema.json` defining `statedd.browser_verification.v1`.
- Added `docs/BROWSER_VERIFICATION.md` documenting the provider-agnostic contract, fallback chain, and audit behavior.
- Added `scripts/statedd_browser_verify.py` with `init`, `check`, `hash`, and `summarize` subcommands.
- Added `scripts/test_browser_verification.py` with regression tests proving Kimi WebBridge, Playwright, agent-native, existing E2E, custom, and manual providers are accepted, no single provider is required, strict mode rejects weak proof, and docs/scripts-only slices remain not applicable.
- Added `fixtures/browser_verification/` with valid/invalid/not-applicable examples.
- Integrated browser verification into `scripts/statedd_validate_schema.py`, `scripts/statedd_audit.py`, `scripts/statedd_doctor.py`, `scripts/check_state_docs.py`, `prompts/EVIDENCE_README_TEMPLATE.md`, `prompts/FINAL_HANDOFF_TEMPLATE.md`, and `.github/workflows/validate.yml`.
- Created `docs/evidence/2026-06-23-provider-agnostic-browser-verification/` with README claim ledger, `runtime_identity.json`, `browser_verification.json`, `manifest.json`, and `command_outputs/verification_log.txt`.
- Did not implement Kimi WebBridge, Playwright, or any browser automation driver as a hard dependency; did not install browsers or add OCR.

### Verification
- `python3 -m py_compile` passed for all listed Python scripts.
- `python3 scripts/statedd_version_check.py` passed.
- `python3 scripts/statedd_validate_schema.py` passed.
- `python3 scripts/check_state_docs.py` passed.
- `python3 scripts/check_state_docs.py --bootstrap-gate` passed.
- `python3 scripts/test_runtime_proof.py` passed.
- `python3 scripts/test_schema_validation.py` passed.
- `python3 scripts/test_evidence_pack.py` passed.
- `python3 scripts/test_upgrade.py` passed.
- `python3 scripts/test_adoption_profiles.py` passed.
- `python3 scripts/test_init_template.py` passed.
- `python3 scripts/test_browser_verification.py` passed.
- `python3 scripts/statedd_audit.py` passed.
- `python3 scripts/statedd_audit.py --strict` passed.
- `python3 scripts/statedd_doctor.py` passed.
- `python3 scripts/statedd_evidence_pack.py check docs/evidence/2026-06-23-provider-agnostic-browser-verification --strict` passed.
- `python3 scripts/statedd_browser_verify.py check docs/evidence/2026-06-23-provider-agnostic-browser-verification --strict` passed.
- `git diff --check` passed.

### Evidence
- `docs/evidence/2026-06-23-provider-agnostic-browser-verification/README.md`
- `docs/evidence/2026-06-23-provider-agnostic-browser-verification/runtime_identity.json`
- `docs/evidence/2026-06-23-provider-agnostic-browser-verification/browser_verification.json`
- `docs/evidence/2026-06-23-provider-agnostic-browser-verification/manifest.json`
- `docs/evidence/2026-06-23-provider-agnostic-browser-verification/command_outputs/verification_log.txt`
- `docs/EVIDENCE_LOG.md` entry `EV-2026-06-23-009`
- `docs/ACCEPTANCE_FREEZES.md` entry `AF-2026-06-23-005`

### Notes
- BL-BROWSER-001 is closure-grade and accepted.
- BL-BROWSER-002 concrete provider integration remains next in the active queue.
- GitHub release publishing remains deferred until explicitly permitted.

## 2026-06-23 - Publish statedd-template-v4 release and clean up

**Type:** release
**Status:** COMPLETE
**Git Head:** 2a9afd47b22d67704e097c93bbb2ca6d16fd08e1
**Worktree:** clean; feature worktree and branch removed

### What changed
- Published GitHub release `v4` for `statedd-template-v4` using `docs/RELEASE_NOTES_statedd-template-v4.md`.
- Removed the `feature/provider-agnostic-browser-verification` worktree and branch after confirming all commits are on `main`.
- Updated `STATUS.md`, `PROJECT_STATE.yaml`, `CHANGELOG.md` to reflect the published release and clean state.

### Verification
- `git tag -a v4` and `git push origin v4` succeeded.
- `gh release create v4` produced https://github.com/lennertvhoy/StateDD_Template/releases/tag/v4.
- `git worktree remove`, `git worktree prune`, and `git branch -d feature/provider-agnostic-browser-verification` succeeded.
- `git status --short` shows clean `main`.

### Notes
- BL-BROWSER-002 remains the only backlog item and is not a release blocker.

## 2026-06-23 - Closure evidence hardening (BL-015)

**Type:** closure_evidence_hardening
**Status:** COMPLETE
**Git Head:** ddc190f before fix; 2a728fe after fix
**Worktree:** clean after final commit

### What changed
- Fixed `docs/evidence/2026-06-23-adoption-ready-evidence-release/README.md` to record `Human override used: yes` with scope/rationale.
- Populated `docs/evidence/2026-06-23-adoption-ready-evidence-release/manifest.json` with non-empty claims C1-C5 and artifacts (README.md, runtime_identity.json, manifest.json).
- Added `manifest_status` enum (`complete`/`skeleton`/`legacy`) to `schemas/evidence_manifest.schema.json`.
- Tightened `scripts/statedd_evidence_pack.py --strict` to reject empty `claims`/`artifacts` unless `manifest_status` is `skeleton` or `legacy`, and to reject `manual_review: required` without `known_limits`.
- Made `scripts/statedd_evidence_pack.py hash` skip `manifest.json` because a manifest cannot hash itself.
- Added regression tests in `scripts/test_evidence_pack.py`.
- Updated `docs/EVIDENCE_LOG.md` with `EV-2026-06-23-006`.

### Verification
- `python3 scripts/test_evidence_pack.py` passed.
- `python3 scripts/statedd_evidence_pack.py check docs/evidence/2026-06-23-adoption-ready-evidence-release --strict` passed.
- `python3 scripts/check_state_docs.py` passed.
- `python3 scripts/statedd_validate_schema.py` passed.
- `python3 scripts/statedd_audit.py --strict` passed after final commit.
- `python3 scripts/statedd_doctor.py` passed after final commit.

### Evidence
- `docs/evidence/2026-06-23-adoption-ready-evidence-release/README.md`
- `docs/evidence/2026-06-23-adoption-ready-evidence-release/manifest.json`
- `docs/EVIDENCE_LOG.md` entry `EV-2026-06-23-006`

### Notes
- This is a post-closure hardening slice; no new features were added.
- The human override status is now consistent across handoff, WORKLOG, EVIDENCE_LOG, and evidence README.

## 2026-06-23 - Adoption-ready template release (BL-012/013/014)

**Type:** template_maintenance_release
**Status:** COMPLETE
**Git Head:** eba0e42 before closure commit; 9fb756b after closure commit
**Worktree:** clean after final commit

### What changed
- Added evidence pack manifests and a redaction gate (`schemas/evidence_manifest.schema.json`, `scripts/statedd_evidence_pack.py`, `scripts/test_evidence_pack.py`).
- Added non-destructive downstream upgrade tooling (`scripts/statedd_upgrade.py`, `scripts/test_upgrade.py`, `docs/UPGRADING.md`).
- Added adoption profiles `minimal`, `solo`, `team`, `regulated` to `scripts/init_template.py` and `docs/ADOPTION_PROFILES.md`.
- Added interactive bootstrap wizard MVP (`scripts/statedd_bootstrap_wizard.py`) with `--answers` and `--dry-run` modes.
- Added `scripts/test_adoption_profiles.py` and wired profile/wizard tests into `.github/workflows/validate.yml`.
- Updated `scripts/check_state_docs.py` to skip optional deep-reference docs for the `minimal` profile.
- Fixed `scripts/statedd_audit.py` so `manifest.json` is not treated as a browser artifact.
- Updated `BACKLOG.md`, `NEXT_ACTIONS.md`, `STATUS.md`, `PROJECT_STATE.yaml`, `CHANGELOG.md`, `docs/EVIDENCE_LOG.md`, and created `docs/evidence/2026-06-23-adoption-ready-evidence-release/`.
- Pushed four commits to `origin/main`.

### Verification
- `python3 scripts/test_evidence_pack.py` passed.
- `python3 scripts/test_upgrade.py` passed.
- `python3 scripts/test_adoption_profiles.py` passed.
- `python3 scripts/test_init_template.py` passed.
- `python3 scripts/test_runtime_proof.py` passed.
- `python3 scripts/test_schema_validation.py` passed.
- `python3 scripts/statedd_validate_schema.py` passed.
- `python3 scripts/check_state_docs.py` passed.
- `python3 scripts/statedd_audit.py --strict` passed after closure commit.
- `python3 scripts/statedd_doctor.py` passed after closure commit.
- `python3 scripts/statedd_evidence_pack.py check docs/evidence/2026-06-23-adoption-ready-evidence-release --strict` passed.

### Evidence
- `docs/evidence/2026-06-23-adoption-ready-evidence-release/README.md`
- `docs/evidence/2026-06-23-adoption-ready-evidence-release/runtime_identity.json`
- `docs/evidence/2026-06-23-adoption-ready-evidence-release/manifest.json`
- `docs/EVIDENCE_LOG.md` entry `EV-2026-06-23-005`

### Notes
- Work was executed directly on `main` per explicit human override.
- Next recommended slices are BL-005 example project, BL-007 release metadata, and BL-WB-001 browser automation.

## 2026-06-23 - Schema-backed validation integrated

**Type:** template_validation_hardening
**Status:** COMPLETE
**Git Head:** e3e555df0c058f4404ee2104c41ceef7e37cee4a before implementation commit
**Worktree:** clean before work; dirty during implementation and evidence capture; clean required after final commit

### What changed
- Added executable schemas/contracts under `schemas/` for `PROJECT_STATE.yaml`, `PROJECT_DNA.yaml`, `PROJECT_ADAPTER.yaml`, `runtime_identity.json`, evidence README files, and final handoff template markers.
- Added `scripts/statedd_validate_schema.py`, a stdlib-only validator with a StateDD YAML parser and focused JSON Schema subset.
- Added `scripts/test_schema_validation.py` plus valid/invalid schema fixtures covering invalid project state, invalid evidence README, runtime not applicable, and runtime required but unreachable.
- Wired schema validation into `scripts/check_state_docs.py`, `scripts/statedd_audit.py`, `scripts/statedd_doctor.py`, `.github/workflows/validate.yml`, `scripts/init_template.py`, and initializer regression tests.
- Updated README, scripts docs, getting-started docs, upgrade docs, evidence template, state files, backlog, and active queue.

### Verification
- `python3 -m py_compile scripts/check_state_docs.py scripts/init_template.py scripts/statedd_version_check.py scripts/statedd_handoff.py scripts/statedd_audit.py scripts/statedd_doctor.py scripts/statedd_runtime_proof.py scripts/statedd_validate_schema.py scripts/test_init_template.py scripts/test_runtime_proof.py scripts/test_schema_validation.py` passed.
- `python3 scripts/statedd_validate_schema.py` passed.
- `python3 scripts/test_schema_validation.py` passed.
- `python3 scripts/statedd_version_check.py` passed.
- `python3 scripts/check_state_docs.py` passed.
- `python3 scripts/check_state_docs.py --bootstrap-gate` passed.
- `python3 scripts/test_runtime_proof.py` passed.
- `python3 scripts/test_init_template.py` passed.
- Fixture schema validation passed for `fixtures/bootstrap_dry_run/bootstrap`, `fixtures/bootstrap_dry_run/operating`, and `fixtures/messy_inherited_repo/bootstrap`.
- `python3 scripts/statedd_audit.py` passed after implementation commit.
- `python3 scripts/statedd_audit.py --strict` passed after implementation commit.
- `python3 scripts/statedd_doctor.py` passed after implementation commit.

### Evidence
- `docs/evidence/2026-06-23-schema-backed-validation/README.md`
- `docs/evidence/2026-06-23-schema-backed-validation/runtime_identity.json`
- `docs/EVIDENCE_LOG.md` entry `EV-2026-06-23-004`

### Notes
- The evidence README contract is a minimal BL-012 seed only.
- Redaction scanning, full evidence-pack manifests, downstream upgrade tooling, adoption profiles/wizard UX, browser automation, canonical example project, and release metadata were intentionally out of scope.
- The template root has no application runtime, so its runtime identity artifact records `runtime.required=false`.

## 2026-06-23 - Runtime proof hardening and integration

**Type:** template_runtime_evidence
**Status:** COMPLETE
**Git Head:** starts at 7ba2a9e72da3860ebb42ba00c614a5a75228c2b3; final implementation commit recorded in git history and handoff
**Worktree:** clean before work; clean after implementation commit and final hygiene rerun

### What changed
- Hardened `scripts/statedd_runtime_proof.py` so remote endpoints do not trigger local process ownership detection by default.
- Added explicit `--expect-local` / `--local-process-proof` override for cases where the user intentionally wants local process proof for a non-local-looking URL.
- Added `scripts/test_runtime_proof.py` covering localhost, 127.0.0.1, remote skip for default 443, and explicit override.
- Wired `scripts/statedd_runtime_proof.py` into new and adopted repo initialization, with regression assertions in `scripts/test_init_template.py`.
- Added CI compile coverage, runtime proof unit coverage, and a docs-only `runtime_identity.json` smoke parse.
- Updated audit and doctor to recognize `runtime_identity.json`; strict audit can fail missing/malformed/schema-invalid runtime identity evidence and unreachable required endpoints.
- Updated evidence and final handoff templates to name the runtime identity artifact directly.
- Stale-labeled root `PROJECT_STATE.yaml` historical git snapshot data instead of presenting stale HEAD/worktree values as live current truth.

### Verification
- `python3 -m py_compile scripts/check_state_docs.py scripts/init_template.py scripts/statedd_version_check.py scripts/statedd_handoff.py scripts/statedd_audit.py scripts/statedd_doctor.py scripts/statedd_runtime_proof.py scripts/test_init_template.py scripts/test_runtime_proof.py` passed.
- `python3 scripts/test_runtime_proof.py` passed.
- `python3 scripts/test_init_template.py` passed.
- `python3 scripts/statedd_version_check.py` passed.
- `python3 scripts/check_state_docs.py` passed.
- `python3 scripts/check_state_docs.py --bootstrap-gate` passed.
- `python3 -m json.tool docs/evidence/2026-06-23-runtime-proof-integration/runtime_identity.json` passed.
- `python3 scripts/statedd_audit.py` passed after implementation commit.
- `python3 scripts/statedd_audit.py --strict` passed after implementation commit.
- `python3 scripts/statedd_doctor.py` passed after implementation commit.

### Evidence
- `docs/evidence/2026-06-23-runtime-proof-integration/README.md`
- `docs/evidence/2026-06-23-runtime-proof-integration/runtime_identity.json`
- `docs/EVIDENCE_LOG.md` entry `EV-2026-06-23-003`

### Notes
- JSON schema files, evidence manifests, redaction checks, Docker/container process ownership, browser automation, release metadata, and downstream upgrade automation were intentionally out of scope.
- The template root has no application runtime, so its runtime identity artifact records `runtime.required=false`.
- [BL-010] schema-backed validation is the next active slice.

## 2026-06-23 - Template-maintenance mode split

**Type:** template_state_governance
**Status:** COMPLETE
**Git Head:** d79e1da53a294079f7e4cc9e7edd83b78deb89fa
**Worktree:** clean before work; clean after implementation commit and audit

### What changed
- Added explicit `repo_role` and `statedd_mode` semantics for template root versus downstream repositories.
- Updated root `AGENTS.md`, `PROJECT_STATE.yaml`, `PROJECT_DNA.yaml`, `PROJECT_ADAPTER.yaml`, and `STATUS.md` so the template root is `repo_role: template_repository` and `statedd_mode: template-maintenance`.
- Updated `scripts/init_template.py` so generated and adopted repos start as `repo_role: downstream_project` and `statedd_mode: bootstrap`.
- Made `scripts/check_state_docs.py`, `scripts/statedd_audit.py`, and `scripts/statedd_doctor.py` mode-aware.
- Updated initializer tests and fixtures to cover template-maintenance and downstream bootstrap behavior.
- Updated `README.md`, `docs/GETTING_STARTED_5_MIN.md`, and `docs/UPGRADING.md` with the role/mode distinction.

### Verification
- `python3 -m py_compile scripts/check_state_docs.py scripts/init_template.py scripts/statedd_version_check.py scripts/statedd_handoff.py scripts/statedd_audit.py scripts/statedd_doctor.py scripts/test_init_template.py` passed.
- `python3 scripts/statedd_version_check.py` passed.
- `python3 scripts/check_state_docs.py` passed.
- `python3 scripts/check_state_docs.py --bootstrap-gate` passed for the root template-maintenance repo.
- `python3 scripts/test_init_template.py` passed, including root template-maintenance and generated downstream bootstrap tests.
- Fixture hygiene checks passed for `fixtures/bootstrap_dry_run/bootstrap`, `fixtures/bootstrap_dry_run/operating`, and `fixtures/messy_inherited_repo/bootstrap`.
- `python3 scripts/check_state_docs.py --bootstrap-gate fixtures/bootstrap_dry_run/bootstrap` failed as expected for the intentionally thin dry-run fixture.
- `python3 scripts/check_state_docs.py --bootstrap-gate fixtures/messy_inherited_repo/bootstrap` passed.
- `python3 scripts/statedd_audit.py` passed on a clean worktree after commit `d79e1da`.
- `python3 scripts/statedd_doctor.py` reported closure grade pass after commit `d79e1da`.

### Evidence
- `docs/evidence/2026-06-23-template-maintenance-mode/README.md`
- `docs/EVIDENCE_LOG.md` entry `EV-2026-06-23-002`

### Notes
- Runtime identity proof artifacts were not added; they remain [BL-009].
- Schema-backed validation was not added; it remains [BL-010].

## 2026-06-23 - StateDD version source normalized

**Type:** template_version_governance
**Status:** COMPLETE
**Git Head:** d5ae473c2e4c129978fe5a56b30dae4c044e7f09
**Worktree:** clean before work; dirty after local edits pending handoff

### What changed
- Added `VERSION` as the canonical StateDD spec-version source.
- Added `CHANGELOG.md`, `docs/UPGRADING.md`, and `scripts/statedd_version_check.py`.
- Wired the version check into `scripts/check_state_docs.py`, `scripts/test_init_template.py`, `.github/workflows/validate.yml`, and `scripts/init_template.py`.
- Normalized root `PROJECT_ADAPTER.yaml` from the stale adapter version to `statedd-template-v4`.
- Aligned fixture `AGENTS.md`, `PROJECT_STATE.yaml`, and `PROJECT_DNA.yaml` version identifiers to `statedd-template-v4`.
- Added CTO-review backlog slices for versioning, runtime proof, schema validation, template-maintenance split, and evidence/redaction hardening.
- Updated `STATUS.md`, `PROJECT_STATE.yaml`, `PROJECT_DNA.yaml`, `BACKLOG.md`, and `NEXT_ACTIONS.md` to reflect current template-maintenance truth.

### Verification
- `python3 -m py_compile scripts/check_state_docs.py scripts/init_template.py scripts/statedd_version_check.py scripts/test_init_template.py` passed.
- `python3 scripts/statedd_version_check.py` passed.
- `python3 scripts/check_state_docs.py` passed.
- `python3 scripts/test_init_template.py` passed.
- Fixture hygiene checks passed for `fixtures/bootstrap_dry_run/bootstrap`, `fixtures/bootstrap_dry_run/operating`, and `fixtures/messy_inherited_repo/bootstrap`.
- `python3 scripts/check_state_docs.py --bootstrap-gate fixtures/bootstrap_dry_run/bootstrap` failed as expected for the intentionally thin dry-run fixture.
- `python3 scripts/check_state_docs.py --bootstrap-gate fixtures/messy_inherited_repo/bootstrap` passed.
- `python3 scripts/check_state_docs.py --bootstrap-gate` still fails because root bootstrap system/repo investigation remains incomplete.

### Evidence
- `docs/evidence/2026-06-23-statedd-version-source/README.md`
- `docs/EVIDENCE_LOG.md` entry `EV-2026-06-23-001`

### Notes
- GitHub release publishing was not performed from this local session.
- [BL-011] is the next recommended slice because root template-maintenance truth is still mixed with generated downstream-project truth.

## 2026-06-14 - Dynamic CTO tool/model routing added

**Type:** template_prompt_governance
**Status:** COMPLETE
**Git Head:** c76dad7
**Worktree:** dirty before work; pre-existing changes were observed in `LICENSE`, `README.md`, and `security_best_practices_report.md`

### What changed
- Added `prompts/TOOL_MODEL_ROUTING_GUIDE.md` for CTO-lane routing of tools, models, settings, context strategy, and tailored prompts.
- Updated `prompts/CTO_SESSION_PROMPT.md`, `prompts/CODING_AGENT_STARTUP_PROMPT.md`, `AGENTS.md`, `PROJECT_DNA.yaml`, `PROJECT_ADAPTER.yaml`, `PROJECT_STATE.yaml`, and `README.md` to reference the routing behavior.
- Updated `scripts/init_template.py` so new/adopted repos receive the routing guide and state pointers.
- Updated `scripts/check_state_docs.py` and `scripts/test_init_template.py` to validate the new guide and initializer coverage.

### Verification
- `python3 scripts/check_state_docs.py` passed.
- `python3 scripts/test_init_template.py` passed.
- `python3 scripts/check_state_docs.py --bootstrap-gate` failed because the template repo remains in bootstrap with system/repo investigation still false and no real active queue.

### Evidence
- `docs/EVIDENCE_LOG.md` entry `EV-2026-06-14-001`

### Notes
- Specific GPT, DeepSeek, or other provider claims were not encoded as template truth because model catalogs, pricing, context windows, and availability are time-sensitive.
- The routing guide requires current primary-source verification when concrete model facts affect a recommendation.

## 2026-06-14 - Feedback-filtered usability slice added

**Type:** template_usability
**Status:** COMPLETE
**Git Head:** c76dad7
**Worktree:** dirty before work; existing uncommitted changes were preserved

### Feedback evaluated
- Integrated: beginner 5-minute start guide.
- Integrated: dedicated OpenCode startup prompt.
- Integrated: lightweight read-only handoff helper.
- Deferred: large example project suite because it adds maintenance burden and should be designed as a separate slice.
- Deferred: GitHub description/topics/release because it is repository-hosting metadata, not locally verifiable template behavior in this slice.
- Deferred: license FAQ because the license text was already in flux in uncommitted changes and should not be mixed into this workflow usability slice.
- Deferred: automated screenshot/evidence capture because it needs a separate design to avoid false runtime proof.

### What changed
- Added `docs/GETTING_STARTED_5_MIN.md`.
- Added `prompts/OPENCODE_STARTUP_PROMPT.md`.
- Added `scripts/statedd_handoff.py`.
- Updated README navigation, docs/scripts README files, template state pointers, initializer support assets, validator requirements, and initializer regression tests.

### Verification
- `python3 -m py_compile scripts/statedd_handoff.py scripts/init_template.py scripts/check_state_docs.py scripts/test_init_template.py` passed.
- `python3 scripts/check_state_docs.py` passed.
- `python3 scripts/test_init_template.py` passed.
- `python3 scripts/statedd_handoff.py --no-include-listeners --test-command "python3 scripts/check_state_docs.py"` passed and printed repo identity plus validation output.
- `python3 scripts/check_state_docs.py --bootstrap-gate` failed because the template repo remains in bootstrap with system/repo investigation still false and no real active queue.

### Evidence
- `docs/EVIDENCE_LOG.md` entry `EV-2026-06-14-002`

### Notes
- The handoff helper is intentionally read-only and labels runtime facts as `not proven` unless directly captured.
- The repo remains in bootstrap mode.

## 2026-06-14 - License changed to reserve teaching rights

**Type:** license_policy_update
**Status:** COMPLETE
**Git Head:** c76dad7
**Worktree:** dirty before work; existing uncommitted changes were preserved

### What changed
- Replaced the previous license text with a custom `StateDD Free Use License - Teaching Rights Reserved`.
- Added `LICENSE_FAQ.md` with plain-language examples.
- Updated `README.md`, `PROJECT_STATE.yaml`, `PROJECT_DNA.yaml`, and `scripts/init_template.py` so the license and FAQ are part of the new-repo template surface.
- Updated `scripts/check_state_docs.py` and `scripts/test_init_template.py` to validate the license policy and ensure new repos include `LICENSE_FAQ.md`.

### Verification
- `python3 scripts/check_state_docs.py` passed.
- `python3 scripts/test_init_template.py` passed.
- `python3 -m py_compile scripts/init_template.py scripts/check_state_docs.py scripts/test_init_template.py` passed.
- `python3 scripts/check_state_docs.py --bootstrap-gate` failed because the template repo remains in bootstrap with system/repo investigation still false and no real active queue.

### Evidence
- `docs/EVIDENCE_LOG.md` entry `EV-2026-06-14-003`

### Notes
- The policy now permits free use, commercial use, distribution, modification, sublicensing, and selling copies/services that use the Software.
- Teaching, training, coaching, courses, workshops, tutorials, curricula, educational products, and educational services based on the Software or StateDD workflow are reserved rights unless prior written permission is granted.
- This is a custom license draft and should be reviewed by a qualified lawyer before relying on it commercially.

## 2026-06-23 - BL-005 canonical schema/prompt example and BL-007 release-prep draft

**Type:** template_workflow_upgrade
**Status:** COMPLETE
**Git Head:** 0c17d4f
**Worktree:** clean

### What changed
- Added acceptance freeze `AF-2026-06-23-002` for the BL-012/013/014 adoption-ready template release, pinning accepted HEAD to `9f940ddd5c00f11896df6ab5b14bfe0dfe18bf8f`.
- Added `schemas/examples/schema_prompt_loop/`, a stdlib-only canonical example of StateDD's schema-driven loop.
  - `feature_slice.schema.json` defines a small "feature slice" contract.
  - `valid_slice.json` passes schema validation.
  - `invalid_slice.json` fails schema validation with a useful error.
  - `generate_prompt.py` generates a deterministic prompt/checklist from the schema.
  - `generated_prompt.md` is a checked-in fixture; the test fails if it drifts.
  - `validate_example.py` and `test_schema_prompt_loop.py` exercise the loop.
- Linked the schema/prompt example from `README.md` and `docs/GETTING_STARTED_5_MIN.md`.
- Wired the example into `.github/workflows/validate.yml` for compilation and test coverage.
- Added draft release notes and repository metadata in `docs/RELEASE_NOTES_statedd-template-v4.md`.
- Updated `BACKLOG.md`, `NEXT_ACTIONS.md`, `STATUS.md`, `PROJECT_STATE.yaml`, and `CHANGELOG.md`.

### Verification
- `python3 -m py_compile schemas/examples/schema_prompt_loop/*.py` passed.
- `python3 schemas/examples/schema_prompt_loop/validate_example.py` passed.
- `python3 schemas/examples/schema_prompt_loop/generate_prompt.py` passed.
- `python3 schemas/examples/schema_prompt_loop/test_schema_prompt_loop.py` passed.
- `python3 scripts/statedd_validate_schema.py` passed.
- `python3 scripts/test_init_template.py` passed.
- `python3 scripts/check_state_docs.py` passed.
- `python3 scripts/check_state_docs.py --bootstrap-gate` passed.
- `python3 scripts/statedd_audit.py --strict` passed after each commit.
- `python3 scripts/statedd_doctor.py` passed.

### Evidence
- `docs/evidence/2026-06-23-canonical-schema-prompt-example/README.md`
- `docs/evidence/2026-06-23-canonical-schema-prompt-example/manifest.json`
- `docs/EVIDENCE_LOG.md` entry `EV-2026-06-23-007`

### Notes
- BL-005 is accepted and frozen as `AF-2026-06-23-003`.
- BL-007 remains a draft; no GitHub release was published.
- The next backlog item is `BL-WB-001` Kimi WebBridge browser verification.

## 2026-06-14 - StateDD v2 executable workflow

**Type:** template_workflow_upgrade
**Status:** COMPLETE
**Git Head:** 0d406e6
**Worktree:** dirty before final commit

### What changed
- Added `scripts/statedd_audit.py` for machine-checkable closure audits.
- Added `scripts/statedd_doctor.py` for fast health summaries.
- Added `prompts/SLICE_CONTRACT_TEMPLATE.md` for formal slice contracts.
- Added `prompts/EVIDENCE_README_TEMPLATE.md` for claim ledgers.
- Added `prompts/SCHEMA_OWNERSHIP_TEMPLATE.md` enforcing canonical schemas, generated examples/prompts, validation tests, `schemaVersion`, and migration policy.
- Added `prompts/SUBAGENT_REVIEW_TEMPLATE.md` for strict subagent output.
- Added `prompts/CTO_REVIEW_CHECKLIST.md` for repeatable CTO review.
- Added `docs/adr/README.md` and `docs/adr/0000-adr-template.md`.
- Added `docs/WORKFLOW_FOR_BEGINNERS.md` with a Mermaid diagram, prompt map, and quality checklist.
- Updated `AGENTS.md` with the Human Override Rule and v2 tool list.
- Updated `prompts/FINAL_HANDOFF_TEMPLATE.md` with four-state closure, release/update gate, and override wording.
- Updated `prompts/CTO_SESSION_PROMPT.md` and `prompts/CODING_AGENT_STARTUP_PROMPT.md` to reference v2 assets.
- Updated `scripts/init_template.py`, `scripts/check_state_docs.py`, `scripts/statedd_handoff.py`, and `scripts/test_init_template.py` to ship and validate v2 assets.
- Updated `.github/workflows/validate.yml` to compile and exercise v2 scripts.
- Updated `README.md`, `docs/GETTING_STARTED_5_MIN.md`, `STATUS.md`, `PROJECT_STATE.yaml`, `PROJECT_DNA.yaml`, `BACKLOG.md`, and `NEXT_ACTIONS.md`.

### Verification
- `python3 -m py_compile scripts/check_state_docs.py scripts/init_template.py scripts/statedd_handoff.py scripts/statedd_audit.py scripts/statedd_doctor.py scripts/test_init_template.py` passed.
- `python3 scripts/check_state_docs.py` passed.
- `python3 scripts/test_init_template.py` passed, including new v2 asset tests and `test_doctor_runs`.
- `python3 scripts/statedd_doctor.py` produced the expected health summary.
- `python3 scripts/statedd_audit.py` on the template root failed only on dirty worktree, as expected during implementation.
- `python3 scripts/statedd_audit.py` on a freshly generated demo repo passed.
- Generated repo smoke test passed.

### Evidence
- `docs/evidence/2026-06-14-statedd-v2-executable-workflow/README.md`
- `docs/EVIDENCE_LOG.md` entry `EV-2026-06-14-004`

### Notes
- The template repo remains in bootstrap mode.
- The SkillSignal-specific canonical schema/export/import loop is a downstream application of the new `SCHEMA_OWNERSHIP_TEMPLATE.md`, not implemented in this slice.
- The Human Override Rule was added explicitly so the workflow stays a strong default, not a prison.
- Subagent review feedback was integrated: fixed `.jpg` suffix detection, expanded override marker checks, hardened `statedd_doctor.py` file reads, added `AGENTS.md` freshness to doctor output, and aligned generated `PROJECT_DNA.yaml` / `PROJECT_ADAPTER.yaml` versions to v4.
