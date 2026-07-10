# Quality Gates

This directory defines project-specific quality gates and global invariants.

The template supplies the workflow, but each downstream project must define what
"the product is still good" means for its own domain.

## Recommended Gate Set

- `product_quality_gate`: core user/operator flows behave correctly.
- `runtime_truth_gate`: the running artifact matches the repo/config being claimed.
- `live_canary_gate`: live or deployment-adjacent proof passes when applicable.
- `redteam_gate`: adversarial or adjacent-failure checks pass.
- `known_bad_events_gate`: prior bad events remain fixed by fixture or durable check.
- `anti_brittleness_gate`: non-trivial fixes/features are backed by a durable invariant, not exact observed examples.

Valid statuses:

- `passing`
- `failing`
- `not_run`
- `not_applicable`

## Example Template

```yaml
quality_gates:
  product_quality_gate:
    status: not_run
    command: null
    evidence: null
  runtime_truth_gate:
    status: not_run
    command: python3 scripts/statedd_runtime_proof.py ...
    evidence: null
  live_canary_gate:
    status: not_applicable
    command: null
    evidence: null
  redteam_gate:
    status: not_run
    command: null
    evidence: null
  known_bad_events_gate:
    status: not_run
    command: null
    evidence: null
  anti_brittleness_gate:
    status: not_run
    command: python3 scripts/statedd_brittleness_check.py
    evidence: docs/quality_gates/ANTI_BRITTLENESS_GATE.md
```

During `quality_freeze`, no feature backlog item should be selected unless it
directly closes the failing gate or freeze condition.
