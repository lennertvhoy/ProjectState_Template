# Evidence: BL-012 evidence pack manifests and redaction gate

**Slice:** [BL-012] Add evidence pack manifests and a redaction gate  
**Date:** 2026-06-23  
**Agent:** coding-agent  
**Branch:** main  
**HEAD:** 59bfeb9

## Claims

- Claim: `schemas/evidence_manifest.schema.json` defines a machine-readable evidence manifest contract.
  Evidence: `schemas/evidence_manifest.schema.json`

- Claim: `scripts/statedd_evidence_pack.py` supports `init`, `check`, `hash`, and `scan` commands.
  Evidence: `command_outputs/statedd_evidence_pack_help.txt`

- Claim: `scripts/test_evidence_pack.py` covers valid/invalid manifest fixtures including missing artifacts, hash mismatches, claims without evidence, unchecked redaction, checked_with_limits, and binary artifacts.
  Evidence: `command_outputs/test_evidence_pack.txt`

- Claim: The redaction scanner flags obvious secret-like patterns but never claims absence of secrets is proven.
  Evidence: `command_outputs/scan_secret_fixture.txt`

- Claim: `scripts/statedd_validate_schema.py`, `scripts/check_state_docs.py`, `scripts/statedd_audit.py`, and `scripts/statedd_doctor.py` recognize evidence manifests.
  Evidence: `command_outputs/validate_check_audit_doctor.txt`

- Claim: New evidence-pack assets are copied to generated and adopted downstream repos.
  Evidence: `command_outputs/test_init_template.txt`

## Verification Log

| Check | Command / Path | Result |
| --- | --- | --- |
| tests | `python3 scripts/test_evidence_pack.py` | pass |
| schema validation | `python3 scripts/statedd_validate_schema.py` | pass |
| hygiene | `python3 scripts/check_state_docs.py` | pass |
| audit | `python3 scripts/statedd_audit.py` | pass (after commit) |
| strict audit | `python3 scripts/statedd_audit.py --strict` | pass (after commit) |
| doctor | `python3 scripts/statedd_doctor.py` | pass |
| evidence manifest | `python3 scripts/statedd_evidence_pack.py check docs/evidence/2026-06-23-evidence-pack-manifests --strict` | pass |
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

- The redaction scanner is conservative and pattern-based; it cannot prove absence of secrets.
- Binary/image artifacts always require manual review.
- Historical evidence folders without `manifest.json` remain acceptable in normal audit mode.
