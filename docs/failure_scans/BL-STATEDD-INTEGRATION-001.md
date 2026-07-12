# Failure Scan: StateDD lifecycle and Git-safety integration

**Date:** 2026-07-11
**Backlog item:** [BL-STATEDD-INTEGRATION-001]
**Author:** coding-agent
**Severity:** P0
**Execution mode impact:** quality_freeze

## What Happened Or Could Happen

- PR #6 and PR #7 are divergent sibling implementations with overlapping files.
- Porting PR #7 wholesale can reintroduce false-positive test gating, root-symlink escapes, hard-coded profiles, v1 manifests, and stale CI claims.
- Integrating only PR #6 can omit centralized Git safety and the agent-first coding path.

## How The User Or Operator Would Notice

- A passing quality gate could hide a failing test ecosystem.
- Initialization could write through a symlinked target root.
- Generated downstream repos could drift from the declarative profile catalog.
- A green PR workflow could validate a synthetic merge ref while the branch head differs.
- An agent could receive a misleading handoff or share mutable Git state.

## Likely Adjacent Failures

- stale state files and evidence refer to an obsolete head or CI subject;
- bootstrap tests prove Git plumbing but not canonical project truth, backlog, or gates;
- strict evidence omits the actual integration proof head;
- unavailable declared runners are treated as warnings.

## Previous Tests That Might Miss This

- PR #7's first-success quality gate;
- merge-candidate CI without direct branch-head identity assertion;
- golden-path isolation checks without bootstrap completion;
- profile tests that inspect hard-coded lists instead of catalog and v2 lock behavior.

## Global Invariant Needed

- Integration must preserve one declarative lifecycle/profile authority, one automatic multi-suite quality gate, fail-closed path confinement, and explicit Git/CI subject identity boundaries.

## Adversarial Case

- Input/event: integrate PR #7 changes whose files overlap PR #6's repaired architecture.
- Expected protected behavior: selectively port compatible capabilities and retain every PR #6 invariant.
- Evidence required: focused regressions, full local gate output, generated-profile matrix, strict evidence manifest, and exact branch/remote/CI subject records.

## Runtime Or Live Proof Required

- Required: no
- Why: the template root has no application runtime; repository and generated-workflow behavior are proven by executable tests and evidence.
- Artifact: local test outputs and strict integration evidence.

## Post-Deploy Watch Required

- Required: no
- Duration or trigger: not applicable to the template root; observe GitHub Actions after the final push if available.
- Artifact: branch-head versus PR merge-candidate CI record.

## Closure Blockers

- local gates incomplete;
- evidence and state do not yet reflect the final integration head;
- remote push, PR, exact branch-head CI, merge-candidate CI, license owner, and human acceptance are unproven.
