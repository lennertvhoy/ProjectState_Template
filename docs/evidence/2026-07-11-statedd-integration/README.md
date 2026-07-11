# BL-STATEDD-INTEGRATION-001 Evidence

**Date:** 2026-07-11
**Agent:** integration-agent
**Slice:** `BL-STATEDD-INTEGRATION-001`
**HEAD:** 3bacef6880c82d5b188527bfac636147bfb895bf
**Branch:** `bl-statedd-integration-001`
**Proof head:** `437fc01d589a72a42aa75b12357ae49586302f34`
**Final PR head:** intentionally not embedded in tracked evidence; the mutable PR body owns the final head.

## Claims

Claim: PR #6 lifecycle/profile/gate/evidence architecture remains authoritative while PR #7 Git-safety/golden-path capabilities are integrated.
Evidence: `command_outputs/pytest_scripts.txt`, `git_safety_summary.json`

Claim: Every generated profile passes its v2-lock-declared gate and deterministic metrics reproduce.
Evidence: `command_outputs/profile_metrics.txt`, `command_outputs/quality_gate_level_2.txt`

Claim: Root and nested symlink confinement, automatic multi-suite aggregation, unavailable-runner failure, and clone-default isolation are regression-covered.
Evidence: `command_outputs/pytest_scripts.txt`

Claim: The complete structured bootstrap and isolated-agent golden path passes through remote parity and strict evidence.
Evidence: `command_outputs/golden_path.txt`, `command_outputs/evidence_check.txt`

Claim: Template-root runtime is not applicable.
Evidence: `runtime_identity.json`

## Verification Log

| Check | Result |
| --- | --- |
| `python3 -m pytest scripts/ -q` | pass |
| `python3 -m pytest schemas/examples/ -q` | pass |
| `python3 scripts/test_golden_path.py` | pass |
| v2 profile metrics and generated-profile gates | pass |
| `python3 scripts/statedd_quality_gate.py --gate-level 2 --verbose` | pass locally |
| strict evidence manifest | pass |
| branch/remote parity in disposable golden-path remote | pass |
| GitHub branch-head CI | not yet proven |
| PR merge-candidate CI | not yet proven |

## Closure State

- Implemented: yes
- Validated locally: yes
- Pushed: not yet
- PR opened: not yet
- Branch-head CI verified: no
- PR merge-candidate CI verified: no
- Closure-grade: no
- Human accepted: no
- Runtime: not applicable for this template-root docs/scripts slice

## Human Override

- Human override used: no

## Risks / What Remains Partial

- Remote branch, GitHub-visible PR, branch-head CI, merge-candidate CI, and human acceptance remain unproven.
- This evidence bundle records local proof before publication; the final PR head is intentionally owned by the mutable PR body.
- The original checkout repair is reported and preserved outside this clone; it is not closure-grade evidence for this slice.
- Verified copyright owner: not proven.
- Benchmark superiority: not proven.
- Safety evidence is summarized without checkout paths, process arguments, or secrets; automated scanning does not prove absence of secrets.

## Anti-Brittleness Review

- Durable authorities are the declarative profile catalog, v2 lifecycle lock, structured bootstrap schema, centralized quality gate, path-confinement contracts, Git-safety transaction, and explicit CI subject identity.
- The golden path uses structured JSON input and executable state/gate checks; it does not use prompt-string replacement to establish bootstrap truth.

## Worktree Dirty File Classification

| status | path | category | owner/notes |
| --- | --- | --- | --- |
| ?? | `docs/evidence/2026-07-11-statedd-integration/` | generated_artifact | integration evidence pack being finalized |
