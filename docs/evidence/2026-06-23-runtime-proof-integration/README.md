# Evidence: Runtime Proof Integration

**Slice:** [BL-009] Harden and integrate runtime identity proof  
**Date:** 2026-06-23  
**Agent:** coding-agent  
**Branch:** main  
**HEAD:** 7ba2a9e72da3860ebb42ba00c614a5a75228c2b3

## Claims

- Claim: Remote URLs no longer trigger local process ownership detection unless explicitly overridden.
  Evidence: `python3 scripts/test_runtime_proof.py` covers localhost, 127.0.0.1, remote skip for `https://example.com`, and explicit `--expect-local` override behavior.

- Claim: Generated and adopted downstream repos receive `scripts/statedd_runtime_proof.py`.
  Evidence: `python3 scripts/test_init_template.py` includes `test_new_includes_runtime_proof_asset` and `test_adopt_installs_runtime_proof_asset`.

- Claim: CI validates runtime proof syntax and a docs-only JSON smoke artifact.
  Evidence: `.github/workflows/validate.yml` compiles `scripts/statedd_runtime_proof.py`, runs `scripts/test_runtime_proof.py`, writes `runtime_identity.json`, and parses it with `python3 -m json.tool`.

- Claim: Audit, doctor, evidence, and handoff surfaces recognize `runtime_identity.json`.
  Evidence: `scripts/statedd_audit.py`, `scripts/statedd_doctor.py`, `prompts/EVIDENCE_README_TEMPLATE.md`, and `prompts/FINAL_HANDOFF_TEMPLATE.md`.

- Claim: Root `PROJECT_STATE.yaml` no longer presents stale git HEAD/worktree data as live current truth.
  Evidence: `PROJECT_STATE.yaml` now stores historical git data under `git_snapshot.status: stale` and directs live git truth to git/audit/doctor/handoff/evidence artifacts.

## Verification Log

| Check | Command / Path | Result |
| --- | --- | --- |
| py_compile | `python3 -m py_compile scripts/check_state_docs.py scripts/init_template.py scripts/statedd_version_check.py scripts/statedd_handoff.py scripts/statedd_audit.py scripts/statedd_doctor.py scripts/statedd_runtime_proof.py scripts/test_init_template.py scripts/test_runtime_proof.py` | pass |
| runtime proof tests | `python3 scripts/test_runtime_proof.py` | pass |
| init tests | `python3 scripts/test_init_template.py` | pass |
| version alignment | `python3 scripts/statedd_version_check.py` | pass |
| hygiene | `python3 scripts/check_state_docs.py` | pass |
| template gate | `python3 scripts/check_state_docs.py --bootstrap-gate` | pass |
| runtime identity proof | `docs/evidence/2026-06-23-runtime-proof-integration/runtime_identity.json` | pass, runtime not required |
| runtime identity JSON parse | `python3 -m json.tool docs/evidence/2026-06-23-runtime-proof-integration/runtime_identity.json` | pass |
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

- JSON schema files, evidence manifests, redaction checks, Docker/container process ownership, browser automation, release metadata, and downstream upgrade automation remain intentionally out of scope.
