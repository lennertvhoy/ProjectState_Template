# Scripts

This directory holds lightweight workflow helpers for the State Driven Development Template.

All setup and usage instructions live in the repository root `README.md`.

## Canonical Scripts

- `init_template.py` - initializes a new repo or adopts the workflow into an existing repo
- `statedd_version_check.py` - verifies that StateDD version-bearing files match `VERSION`
- `check_state_docs.py` - validates the live-state documentation boundaries
- `statedd_handoff.py` - prints a read-only handoff snapshot from local repo state
- `statedd_audit.py` - machine-checkable closure audit (StateDD v2)
- `statedd_doctor.py` - fast StateDD health summary (StateDD v2)
- `statedd_runtime_proof.py` - captures `runtime_identity.json` proof artifacts
- `test_init_template.py` - runs stdlib-only regression tests for initializer safety
- `test_runtime_proof.py` - runs stdlib-only runtime proof regression tests

## Usage

```bash
python3 scripts/init_template.py --help
python3 scripts/statedd_version_check.py
python3 scripts/check_state_docs.py
python3 scripts/statedd_handoff.py
python3 scripts/statedd_doctor.py
python3 scripts/statedd_audit.py
python3 scripts/statedd_runtime_proof.py --no-runtime-required --evidence-dir docs/evidence/<slice>
python3 scripts/test_init_template.py
python3 scripts/test_runtime_proof.py
```

Add project-specific scripts only after a real project is attached to this template.
