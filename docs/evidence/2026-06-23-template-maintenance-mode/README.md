# Evidence: Template-Maintenance Mode Split

**Slice:** [BL-011] Split template-maintenance state from downstream-project state  
**Date:** 2026-06-23  
**Agent:** coding-agent  
**Branch:** main  
**HEAD:** e9f1c731ec9760fedfe84dfb1979ab93ee05c9fd

## Claims

- Claim: Root repo now identifies as template-maintenance, not downstream bootstrap.
  Evidence: `PROJECT_STATE.yaml` declares `repo_role: template_repository` and `statedd_mode: template-maintenance`; `python3 scripts/check_state_docs.py --bootstrap-gate` passes.

- Claim: Generated downstream repos still start in bootstrap.
  Evidence: `generated-new-project-state.yaml`, `generated-adopt-project-state.yaml`, `generated-new-agents.md`, and `generated-adopt-agents.md` all declare `repo_role: downstream_project` and `statedd_mode: bootstrap`.

- Claim: Audit, doctor, and hygiene scripts distinguish template-maintenance from downstream bootstrap.
  Evidence: `scripts/check_state_docs.py`, `scripts/statedd_doctor.py`, and `scripts/statedd_audit.py` now report or validate repo role/mode; `python3 scripts/test_init_template.py` covers template root and generated downstream behavior.

- Claim: The previous version source-of-truth remains intact.
  Evidence: `python3 scripts/statedd_version_check.py` passes.

## Verification Log

| Check | Command | Result |
| --- | --- | --- |
| before root gate | `python3 scripts/check_state_docs.py --bootstrap-gate` before BL-011 | fail expected: downstream investigation fields were still false |
| py_compile | `python3 -m py_compile scripts/check_state_docs.py scripts/init_template.py scripts/statedd_version_check.py scripts/statedd_handoff.py scripts/statedd_audit.py scripts/statedd_doctor.py scripts/test_init_template.py` | pass |
| version alignment | `python3 scripts/statedd_version_check.py` | pass |
| hygiene | `python3 scripts/check_state_docs.py` | pass |
| root template gate | `python3 scripts/check_state_docs.py --bootstrap-gate` | pass |
| init tests | `python3 scripts/test_init_template.py` | pass |
| fixture hygiene | `python3 scripts/check_state_docs.py fixtures/bootstrap_dry_run/bootstrap` | pass |
| fixture hygiene | `python3 scripts/check_state_docs.py fixtures/bootstrap_dry_run/operating` | pass |
| fixture hygiene | `python3 scripts/check_state_docs.py fixtures/messy_inherited_repo/bootstrap` | pass |
| fixture gate | `python3 scripts/check_state_docs.py --bootstrap-gate fixtures/bootstrap_dry_run/bootstrap` | fail expected: intentionally thin dry-run fixture |
| fixture gate | `python3 scripts/check_state_docs.py --bootstrap-gate fixtures/messy_inherited_repo/bootstrap` | pass |
| clean audit | `python3 scripts/statedd_audit.py` after commit `d79e1da` | pass |
| clean doctor | `python3 scripts/statedd_doctor.py` after commit `d79e1da` | pass |

## Closure State

- Implemented: yes
- Validated: yes
- Closure-grade: yes
- Accepted: no

## Human Override

- Human override used: no

## Risks / What Remains Partial

- Runtime identity proof artifacts are intentionally deferred to [BL-009].
- Schema-backed validation is intentionally deferred to [BL-010].
- Full downstream upgrade tooling is intentionally deferred to [BL-013].
- The generated PROJECT_STATE evidence files contain temporary generation paths; they are proof of initializer output shape, not durable runtime references.
