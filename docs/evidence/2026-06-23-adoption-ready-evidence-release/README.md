# Evidence: Adoption-ready StateDD template release

**Slice:** [BL-012] Add evidence pack manifests and a redaction gate, [BL-013] Add non-destructive downstream upgrade tooling, [BL-014] Add adoption profiles and an interactive bootstrap wizard  
**Date:** 2026-06-23  
**Agent:** coding-agent  
**Branch:** main  
**HEAD:** eba0e42

## Claims

- Claim: `schemas/evidence_manifest.schema.json` defines a machine-readable evidence manifest contract and `scripts/statedd_evidence_pack.py` supports `init`, `check`, `hash`, and `scan` commands.
  Evidence: `schemas/evidence_manifest.schema.json`, `scripts/statedd_evidence_pack.py`, `scripts/test_evidence_pack.py`

- Claim: `scripts/statedd_upgrade.py` provides non-destructive downstream upgrade capability with dry-run-by-default, `--apply`, and `--force-managed` behavior.
  Evidence: `scripts/statedd_upgrade.py`, `scripts/test_upgrade.py`, `docs/UPGRADING.md`

- Claim: `scripts/init_template.py` supports adoption profiles `minimal`, `solo`, `team`, and `regulated` for both `new` and `adopt` subcommands.
  Evidence: `scripts/init_template.py`, `scripts/test_adoption_profiles.py`, `docs/ADOPTION_PROFILES.md`

- Claim: `scripts/statedd_bootstrap_wizard.py` provides an interactive MVP that asks minimum strategic questions and runs the initializer with the chosen profile.
  Evidence: `scripts/statedd_bootstrap_wizard.py`, CI wizard smoke test

- Claim: All new capabilities are wired into documentation hygiene, schema validation, audit, doctor, initializer, and CI without adding external dependencies.
  Evidence: `.github/workflows/validate.yml`, `scripts/check_state_docs.py`, `scripts/statedd_audit.py`, `scripts/statedd_doctor.py`

## Verification Log

| Check | Command / Path | Result |
| --- | --- | --- |
| adoption profile tests | `python3 scripts/test_adoption_profiles.py` | pass |
| evidence pack tests | `python3 scripts/test_evidence_pack.py` | pass |
| upgrade tests | `python3 scripts/test_upgrade.py` | pass |
| initializer tests | `python3 scripts/test_init_template.py` | pass |
| runtime proof tests | `python3 scripts/test_runtime_proof.py` | pass |
| schema validation tests | `python3 scripts/test_schema_validation.py` | pass |
| schema validation | `python3 scripts/statedd_validate_schema.py` | pass |
| hygiene | `python3 scripts/check_state_docs.py` | pass |
| audit | `python3 scripts/statedd_audit.py` | pass |
| strict audit | `python3 scripts/statedd_audit.py --strict` | pass |
| doctor | `python3 scripts/statedd_doctor.py` | pass |
| evidence manifest | `python3 scripts/statedd_evidence_pack.py check docs/evidence/2026-06-23-adoption-ready-evidence-release --strict` | pass |
| runtime identity proof | `scripts/statedd_runtime_proof.py --no-runtime-required` | yes |

## Runtime Identity

- Runtime required: no
- Artifact: `runtime_identity.json`
- Endpoint: not applicable
- Process ownership proven: not applicable
- Known limits: Template root has no application runtime.

## Evidence Pack Manifest

- Manifest: `manifest.json`
- Redaction status: checked_with_limits

## Closure State

- Implemented: yes
- Validated: yes
- Closure-grade: yes
- Accepted: pending

## Human Override

- Human override used: no

## Risks / What Remains Partial

- The bootstrap wizard is an MVP and does not yet replace the need for a CTO lane during bootstrap.
- The upgrade helper copies safe managed assets but does not yet perform semantic merges of customized workflow files.
- The redaction scanner is conservative and pattern-based; it cannot prove absence of secrets.
