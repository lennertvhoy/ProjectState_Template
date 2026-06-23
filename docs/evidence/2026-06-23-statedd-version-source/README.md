# Evidence: StateDD Version Source

**Slice:** [BL-008] Normalize StateDD versioning and release metadata  
**Date:** 2026-06-23  
**Agent:** coding-agent  
**Branch:** main  
**HEAD:** d5ae473c2e4c129978fe5a56b30dae4c044e7f09

## Claims

- Claim: `VERSION` is the canonical StateDD spec-version source.
  Evidence: `VERSION` contains `statedd-template-v4`; `scripts/statedd_version_check.py` reads it as expected.

- Claim: Current version-bearing root files agree on `statedd-template-v4`.
  Evidence: `python3 scripts/statedd_version_check.py` passes.

- Claim: New and adopted repos receive the version assets.
  Evidence: `python3 scripts/test_init_template.py` passes version-asset tests for both `new` and `adopt`.

- Claim: The stale root adapter mismatch was corrected.
  Evidence: `PROJECT_ADAPTER.yaml` now uses `version: "statedd-template-v4"` and the version check passes.

- Claim: Fixture state no longer advertises older StateDD spec identifiers.
  Evidence: fixture `AGENTS.md`, `PROJECT_STATE.yaml`, and `PROJECT_DNA.yaml` files now use `statedd-template-v4`; fixture hygiene checks pass.

## Verification Log

| Check | Command | Result |
| --- | --- | --- |
| py_compile | `python3 -m py_compile scripts/check_state_docs.py scripts/init_template.py scripts/statedd_version_check.py scripts/test_init_template.py` | pass |
| version alignment | `python3 scripts/statedd_version_check.py` | pass |
| hygiene | `python3 scripts/check_state_docs.py` | pass |
| init tests | `python3 scripts/test_init_template.py` | pass |
| fixture hygiene | `python3 scripts/check_state_docs.py fixtures/bootstrap_dry_run/bootstrap` | pass |
| fixture hygiene | `python3 scripts/check_state_docs.py fixtures/bootstrap_dry_run/operating` | pass |
| fixture hygiene | `python3 scripts/check_state_docs.py fixtures/messy_inherited_repo/bootstrap` | pass |
| fixture gate | `python3 scripts/check_state_docs.py --bootstrap-gate fixtures/bootstrap_dry_run/bootstrap` | fail expected: dry-run fixture remains intentionally thin |
| fixture gate | `python3 scripts/check_state_docs.py --bootstrap-gate fixtures/messy_inherited_repo/bootstrap` | pass |
| bootstrap gate | `python3 scripts/check_state_docs.py --bootstrap-gate` | fail expected: bootstrap system/repo investigation remains incomplete |

## Closure State

- Implemented: yes
- Validated: yes
- Closure-grade: partial
- Accepted: no

## Human Override

- Human override used: no

## Risks / What Remains Partial

- GitHub release metadata was not published from this local coding session.
- Template-maintenance mode split is still open as [BL-011].
- Runtime identity proof artifacts, schema validation, evidence manifests, and redaction gates are separate backlog slices.
