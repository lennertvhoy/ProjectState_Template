# Scripts

This directory holds lightweight workflow helpers for the State Driven Development Template.

All setup and usage instructions live in the repository root `README.md`.

## Canonical Scripts

- `init_template.py` - initializes a new repo or adopts the workflow into an existing repo
- `projectstate_version_check.py` - verifies that ProjectState version-bearing files match `VERSION`
- `check_state_docs.py` - validates the live-state documentation boundaries
- `projectstate_handoff.py` - prints a read-only handoff snapshot from local repo state
- `projectstate_audit.py` - machine-checkable closure audit (ProjectState v2)
- `projectstate_doctor.py` - fast ProjectState health summary (ProjectState v2)
- `projectstate_worktree_guard.py` - pre-slice/closure worktree isolation and dirty-file classification guard
- `projectstate_brittleness_check.py` - advisory anti-brittleness heuristic scan
- `projectstate_runtime_proof.py` - captures `runtime_identity.json` proof artifacts
- `projectstate_runtime_truth_check.py` - re-probes an explicit v2 runtime artifact against current Git/runtime truth
- `projectstate_validate_schema.py` - validates ProjectState state, evidence, runtime, and handoff contracts
- `test_init_template.py` - runs stdlib-only regression tests for initializer safety
- `test_worktree_guard.py` - runs stdlib-only worktree guard regression tests
- `test_brittleness_check.py` - runs stdlib-only brittleness scan and audit marker regression tests
- `test_runtime_proof.py` - runs stdlib-only runtime proof regression tests
- `test_runtime_truth_check.py` - runs stdlib-only runtime truth regression tests
- `test_schema_validation.py` - runs stdlib-only schema validation regression tests

## Usage

```bash
python3 scripts/init_template.py --help
python3 scripts/projectstate_version_check.py
python3 scripts/check_state_docs.py
python3 scripts/projectstate_handoff.py
python3 scripts/projectstate_doctor.py
python3 scripts/projectstate_audit.py
python3 scripts/projectstate_worktree_guard.py --mode start-slice
python3 scripts/projectstate_brittleness_check.py
python3 scripts/projectstate_runtime_proof.py --no-runtime-required --evidence-dir docs/evidence/<slice>
python3 scripts/projectstate_runtime_truth_check.py --artifact docs/evidence/<slice>/runtime_identity.json
python3 scripts/projectstate_validate_schema.py
python3 scripts/test_init_template.py
python3 scripts/test_worktree_guard.py
python3 scripts/test_brittleness_check.py
python3 scripts/test_runtime_proof.py
python3 scripts/test_runtime_truth_check.py
python3 scripts/test_schema_validation.py
```

Add project-specific scripts only after a real project is attached to this template.
