# StateDD Incident Response

**Purpose:** Turn bad observed behavior into durable product protection.

Use this when a user reports a bad live event, a regression is observed, or a
global quality invariant fails.

## Incident Workflow

1. **Intake:** Record what happened and what the user/operator experienced.
2. **Severity:** Classify as `P0`, `P1`, or `P2`.
3. **Mode:** For P0, set `current_state.execution_mode` to `quality_freeze` or
   `incident_response` in `PROJECT_STATE.yaml`.
4. **Failure scan:** Create `docs/failure_scans/<backlog-id>.md`.
5. **Incident note:** Create `docs/incidents/YYYYMMDD-HHMMSS-<slug>.md`.
6. **Fixture:** Add a bad-event fixture under the project-appropriate test fixture path.
7. **Invariant:** Define the project-level behavior that must never fail again.
8. **Failing proof:** Add a failing test or quality check first where practical.
9. **Fix:** Repair the underlying class of failure.
10. **Adversarial proof:** Test likely adjacent failures.
11. **Runtime proof:** Capture runtime/live proof when the failure involves a running system.
12. **Post-deploy watch:** Check the behavior remains good after deploy or daemon restart.
13. **Closure:** Leave the incident open until the quality gates pass or a human override records the remaining risk.

## Incident Note Template

```markdown
# Incident: <short title>

**Date:** YYYY-MM-DD
**Severity:** P0 | P1 | P2
**Status:** open | mitigated | fixed | closed | override-approved
**Related backlog:** [BL-XXX]
**Related failure scan:** docs/failure_scans/BL-XXX.md
**Evidence folder:** docs/evidence/YYYY-MM-DD-slug

## User/Operator Symptom

- ...

## Observed Event

- Source:
- Timestamp:
- Transcript/log/artifact:

## Cause 1: Initiating Event

- Boundary: product/runtime/external
- Evidence status: observed | reported | not proven
- Actor/mechanism/timestamp:

## Cause 2: Workflow Or Containment Contribution

- Boundary: StateDD/product control
- Evidence status: observed | reported | not proven
- Explain separately; do not attribute the initiating event without evidence.

## Suspected Failure Class

- product_behavior | runtime_truth | integration_boundary | state_truth | regression | data_integrity | security_privacy | observability | workflow | brittleness

## Missing Invariant

- ...

## Regression Fixture

- Path:
- Status: missing | present_unverified | present_valid

## Runtime/Live Proof

- Required: yes | no
- Artifact:
- Status: missing | present_unverified | present_valid | stale | not_applicable

## Adjacent Cases Checked

- ...

## Closure Conditions

- ...

## Residual Risk

- ...
```
