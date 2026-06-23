# WORKLOG

**Purpose:** Append-only history for completed work.

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
