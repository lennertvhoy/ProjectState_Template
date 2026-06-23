# Evidence: Schema-Backed Validation

**Slice:** [BL-010] Add schema-backed validation for StateDD state, evidence, runtime proof, and handoff files  
**Date:** 2026-06-23  
**Agent:** coding-agent  
**Branch:** main  
**HEAD:** e3e555df0c058f4404ee2104c41ceef7e37cee4a

## Claims

- Claim: StateDD now has executable schemas/contracts for core state, runtime identity, evidence README, and final handoff files.
  Evidence: `schemas/project_state.schema.json`, `schemas/project_dna.schema.json`, `schemas/project_adapter.schema.json`, `schemas/runtime_identity.schema.json`, `schemas/evidence_readme_contract.json`, and `schemas/final_handoff_contract.json`.

- Claim: `scripts/statedd_validate_schema.py` validates the root repo and fails invalid fixtures with actionable messages.
  Evidence: `python3 scripts/test_schema_validation.py` covers root pass, invalid project state, invalid evidence README, runtime-not-applicable pass, and runtime-required-unreachable fail.

- Claim: Generated and adopted downstream repos receive the schema validation capability.
  Evidence: `python3 scripts/test_init_template.py` and `python3 scripts/test_schema_validation.py` cover `new` and `adopt` paths with schema assets and passing schema validation.

- Claim: Hygiene, audit, doctor, and CI recognize schema validation.
  Evidence: `scripts/check_state_docs.py`, `scripts/statedd_audit.py`, `scripts/statedd_doctor.py`, and `.github/workflows/validate.yml` invoke or report `scripts/statedd_validate_schema.py`.

- Claim: This slice includes only a minimal BL-012 seed and does not implement redaction scanning or full evidence-pack manifests.
  Evidence: `schemas/evidence_readme_contract.json` checks evidence README headings/markers only; no redaction scanner or evidence manifest automation was added.

## Verification Log

| Check | Command / Path | Result |
| --- | --- | --- |
| py_compile | `python3 -m py_compile scripts/check_state_docs.py scripts/init_template.py scripts/statedd_version_check.py scripts/statedd_handoff.py scripts/statedd_audit.py scripts/statedd_doctor.py scripts/statedd_runtime_proof.py scripts/statedd_validate_schema.py scripts/test_init_template.py scripts/test_runtime_proof.py scripts/test_schema_validation.py` | pass |
| schema validation | `python3 scripts/statedd_validate_schema.py` | pass |
| schema validation tests | `python3 scripts/test_schema_validation.py` | pass |
| version alignment | `python3 scripts/statedd_version_check.py` | pass |
| hygiene | `python3 scripts/check_state_docs.py` | pass |
| template gate | `python3 scripts/check_state_docs.py --bootstrap-gate` | pass |
| runtime proof tests | `python3 scripts/test_runtime_proof.py` | pass |
| init tests | `python3 scripts/test_init_template.py` | pass |
| fixture schema validation | `python3 scripts/statedd_validate_schema.py fixtures/bootstrap_dry_run/bootstrap && python3 scripts/statedd_validate_schema.py fixtures/bootstrap_dry_run/operating && python3 scripts/statedd_validate_schema.py fixtures/messy_inherited_repo/bootstrap` | pass |
| audit | `python3 scripts/statedd_audit.py` | pass after implementation commit |
| strict audit | `python3 scripts/statedd_audit.py --strict` | pass after implementation commit |
| doctor | `python3 scripts/statedd_doctor.py` | pass after implementation commit |

## Runtime Identity

- Runtime required: no
- Artifact: `runtime_identity.json`
- Endpoint: not applicable
- Process ownership proven: not applicable
- Known limits: The template root has no application runtime. The artifact was captured during implementation while the worktree was dirty.

## Closure State

- Implemented: yes
- Validated: yes
- Closure-grade: yes
- Accepted: pending

## Human Override

- Human override used: no

## Risks / What Remains Partial

- Redaction scanning and full evidence-pack manifests remain [BL-012].
- Non-destructive downstream upgrade tooling remains [BL-013].
- Adoption profiles and an interactive bootstrap wizard remain [BL-014].
- Browser verification integration, canonical example project, and release metadata remain later backlog work.
