# ProjectState Failure Taxonomy

**Purpose:** Standard vocabulary for classifying failures before fixing them.

Use this taxonomy in `docs/failure_scans/`, `docs/incidents/`, backlog items,
and final handoffs.

## Severity

- `P0`: user-facing or operator-facing behavior is currently broken, unsafe, or
  actively misleading. Enter `quality_freeze` or `incident_response`.
- `P1`: important behavior is degraded or fragile, but a safe workaround exists.
- `P2`: quality, maintainability, or documentation issue without immediate user harm.

## Failure Classes

- `product_behavior`: the user-visible or operator-visible flow does the wrong thing.
- `runtime_truth`: the running artifact is stale, misconfigured, duplicated, or not the artifact being claimed.
- `integration_boundary`: an external service, provider, API, webhook, or daemon boundary leaks failure into the product.
- `state_truth`: repo state, docs, handoff, evidence, or runtime state contradicts reality.
- `regression`: a previously fixed or accepted behavior failed again.
- `data_integrity`: user data, canonical data, migrations, or generated state are corrupted or silently changed.
- `security_privacy`: secret, auth, permission, retention, or data exposure failure.
- `observability`: the system failed without logs, metrics, traces, or useful diagnostics.
- `workflow`: ProjectState process allowed premature closure, weak proof, or wrong sequencing.
- `brittleness`: the fix only matches observed prompts, strings, keywords, fixtures, sleeps/timeouts, provider quirks, or silent fallbacks instead of a durable invariant.

## Evidence Status

- `missing`: evidence required but absent.
- `present_unverified`: evidence exists but has not been checked.
- `present_valid`: evidence exists and passed the relevant check.
- `stale`: evidence was valid but may no longer describe current runtime or code.
- `not_applicable`: explicitly out of scope for this slice.

## Closure Language

Use precise closure words:

- `implemented`: the change exists.
- `validated`: targeted checks passed.
- `closure-grade`: quality gates, evidence, state, and risk checks passed.
- `accepted`: human or CTO lane accepted the result.

Never collapse these states into a generic "done."

A feature or fix slice that only handles the observed failing input without a
durable invariant is not `closure-grade`.
