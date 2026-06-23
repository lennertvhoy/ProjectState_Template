# Evidence: BL-005 canonical schema/prompt example project

**Slice:** BL-005  
**Date:** 2026-06-23  
**Agent:** coding-agent  
**Branch:** main  
**HEAD:** 0c17d4f  

## Claims

- Claim: Feature slice schema defines a small, valid contract.
  Evidence: `schema_prompt_loop/feature_slice.schema.json`, `schema_prompt_loop/valid_slice.json`

- Claim: Valid example passes schema validation.
  Evidence: `schema_prompt_loop/valid_slice.json`, `command_outputs/verification_log.txt`

- Claim: Invalid example fails schema validation with a useful error.
  Evidence: `schema_prompt_loop/invalid_slice.json`, `command_outputs/verification_log.txt`

- Claim: Generated prompt is deterministic and includes required schema fields.
  Evidence: `schema_prompt_loop/generated_prompt.md`, `schema_prompt_loop/generate_prompt.py`, `command_outputs/verification_log.txt`

- Claim: Tests pass and guard against prompt fixture drift.
  Evidence: `schema_prompt_loop/test_schema_prompt_loop.py`, `command_outputs/verification_log.txt`

- Claim: Example is wired into CI.
  Evidence: `command_outputs/verification_log.txt`

## Verification Log

See `command_outputs/verification_log.txt` for the full output of:

- `python3 -m py_compile` on all example scripts
- `python3 schemas/examples/schema_prompt_loop/validate_example.py`
- `python3 schemas/examples/schema_prompt_loop/generate_prompt.py`
- `python3 schemas/examples/schema_prompt_loop/test_schema_prompt_loop.py`
- `python3 scripts/statedd_validate_schema.py`
- `python3 scripts/check_state_docs.py`

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
- Accepted: yes

## Human Override

- Human override used: no

## Risks / What Remains Partial

- The example is intentionally small and educational.
- The generated prompt uses only schema field names and descriptions; it does not paraphrase.
- The example is not a runtime dependency of StateDD.
