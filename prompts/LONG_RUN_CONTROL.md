# Optional long-run control

Read `AGENTS.md`, `PROJECT.md`, and `STATE.yaml` first. Use this workflow only
when the human explicitly selects a long authorized run. It does not replace
the outcome-first core, the primary journey, or human acceptance. A single
agent remains the default; this file only bounds a selected long run.

## When it earns its cost

A long run is appropriate when the authorized envelope contains separable,
dependency-ready work that cannot finish in one short session and the host can
persist a checkpoint without another model turn. Do not add a scheduler,
model-router service, dashboard, or mandatory multi-agent system to the core.
If the host cannot enforce a pre-action decision, observe usage, run bounded
timers, and persist a checkpoint independently, label that capability missing
and stay with short supervised sessions.

## Selected run record (existing fields only)

Record the envelope in existing current state or the selected assignment —
never as new `STATE.yaml` top-level keys (the gate rejects unknown fields).
Keep one authoritative owner per fact; a supporting attempt log is evidence,
not second current state.

```text
Long-run envelope for slice <id>:
Absolute UTC deadline: <YYYY-MM-DDTHH:MM:SSZ; no silent extension>
Finalization boundary: <time reserved for review, integration, proof, handoff>
Authorized work envelope: <outcome, slice, explicit inclusions/exclusions>
Delegation limits: <max workers, separable tasks only, file/runtime ownership>
Usage budget: <measured / estimated / unknown + fallback batch/retry/time caps>
Monitoring obligation: <none | deterministic checks until <time> | event wakes>
Unblock event for any blocked lane: <what makes it actionable again>
Checkpoint location: <evidence path updated during the run>
```

Separate the maximum work window from any monitoring obligation. A deadline is
not a requirement to keep expensive reasoning busy. Explicit monitoring still
needs real coverage, not an early success report.

## Workers and models

Maximum worker count is a ceiling, not a target. Delegate only separable work
with useful proof, bounded context, clear file/runtime ownership, and enough
remaining integration capacity. Workers return deltas and evidence pointers,
not full repository audits. Every worker inherits the same deadline and must
return while integration is still feasible.

Keep model and reasoning choices observable; do not change them without
authority. Compare improved workflow against the current workflow on the same
model first; test cheaper models only on bounded tasks where quality and retry
economics support them. Deterministic health checks, waiting, timestamps, file
hashing, test execution, and log retention must not require a fresh reasoning
cycle per unchanged result — use an already supported, authorized runner or
timer. Wake an agent for a material event or a required decision. Never claim
future monitoring the host cannot provide.

Numeric defaults here are experimental policy choices, not proven optima. Do
not silently apply them to old projects. Do not infer an exact token ceiling
from a subscription percentage, double-count child usage in a parent total, or
claim a hard spending guarantee from estimates.

## Finalization and interruption

At finalization admit no broad new work. Integrate justified increments, run
affected proof, save changes, and produce a durable handoff. Checkpoint
unfinished work without promoting it to validated and without merging merely
to make Git clean. Persist recoverable state throughout: a lost process, quota
refusal, or host failure must not need a final model turn to identify what was
left. An expired deadline at launch creates no silent overnight run. Missing
closure is visible interruption, not successful completion.

## Evidence without context bloat

Keep the canonical summary a current view: outcome, strongest relevant proof,
unresolved failures, retained work/jobs, exact next action. Move history into
linked supporting evidence while preserving failure identity. Ordinary
resumption loads the current view plus only the referenced detail needed for
the next decision — not multi-thousand-line histories, generated/vendor files,
or all worker output. Record UTC event time and observation time separately
where chronology matters. Record resource baseline and delta, not just final
directory size. Restarting a stack mutates runtime even when the verification
command afterward is read-only.
