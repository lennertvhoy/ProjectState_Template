# False Closure Claim Regression Fixture

## Scenario
An agent claims "StateSpec v5 AgentOS architecture is fully implemented" but:
- Local files exist but are not tracked/committed
- Remote (GitHub main) does not contain the claimed deliverables
- No remote truth proof provided

## Expected Behavior
The `statedd_remote_truth_check.py` gate MUST FAIL with:
- Boundary 'remote_contains_head' fails (local HEAD not on remote)
- Boundary 'claimed_files_tracked' fails (files not in git ls-files)
- Closure label: `NOT CLOSURE-GRADE — LOCAL OR UNVERIFIED CLAIM`

## Test Setup
```bash
# Simulate untracked claimed files
touch fake_v5_deliverable.py
# Run remote truth check claiming this file exists
python scripts/statedd_remote_truth_check.py --claim fake_v5_deliverable.py
# Must exit with code 1
```

## Classification
- **Type**: False closure claim / Source-of-truth violation / Template self-contamination
- **Severity**: CRITICAL (template cannot bootstrap if it self-contaminates)
- **Detection**: `statedd_remote_truth_check.py` (Remote Truth Gate)
- **Prevention**: Remote Truth Gate + Truth Boundary invariant in AGENTS.md

## Evidence Expected in Failure
1. `git status --short` shows untracked files
2. `git ls-files <claimed>` returns empty
3. `git ls-remote origin <branch>` shows different SHA or missing
4. Closure label explicitly states `NOT CLOSURE-GRADE`

## Reference
See docs/incidents/INCIDENT-2026-06-28-false-closure-template-self-contamination.md