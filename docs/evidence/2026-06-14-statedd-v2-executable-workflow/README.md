# Evidence: StateDD v2 Executable Workflow

**Slice:** [BL-001] Validate the v2 executable workflow implementation  
**Date:** 2026-06-14  
**Agent:** coding-agent  
**Branch:** main  
**HEAD:** d8adcfd4c8047313f22aeda66bc11be22f8e4496

## Claims

- Claim: `scripts/statedd_audit.py` exists and is machine-checkable.
  Evidence: `python3 -m py_compile scripts/statedd_audit.py`

- Claim: `scripts/statedd_doctor.py` exists and prints a health summary.
  Evidence: `python3 -m py_compile scripts/statedd_doctor.py`

- Claim: New v2 prompt/template assets ship with `init_template.py`.
  Evidence: `python3 scripts/test_init_template.py` passes v2 asset tests.

- Claim: `check_state_docs.py` validates v2 assets.
  Evidence: `python3 scripts/check_state_docs.py` passes.

- Claim: Newly generated repos include v2 assets and pass hygiene checks.
  Evidence: `python3 scripts/init_template.py new --name "v2 Demo" --target /tmp/v2demo` followed by `check_state_docs.py` and `statedd_audit.py`.

## Verification Log

| Check | Command | Result |
| --- | --- | --- |
| py_compile | `python3 -m py_compile scripts/check_state_docs.py scripts/init_template.py scripts/statedd_handoff.py scripts/statedd_audit.py scripts/statedd_doctor.py scripts/test_init_template.py` | pass |
| hygiene | `python3 scripts/check_state_docs.py` | pass |
| init tests | `python3 scripts/test_init_template.py` | pass |
| doctor | `python3 scripts/statedd_doctor.py` | pass |
| audit (template root) | `python3 scripts/statedd_audit.py` | fail expected: worktree dirty during implementation |
| audit (generated demo) | `python3 scripts/statedd_audit.py /tmp/v2demo` | pass |

## Closure State

- Implemented: yes
- Validated: yes
- Closure-grade: pending (requires clean worktree and commit)
- Accepted: pending

## Human Override

- Human override used: no

## Risks / What Remains Partial

- The template repo itself remains in bootstrap mode.
- A downstream canonical schema/export/import example is not part of this slice.
