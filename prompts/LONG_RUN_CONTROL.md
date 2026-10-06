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

## Copy into the project's local sections when the owner selects this workflow

Copy the text below into the project's `AGENTS.md`, under its local sections,
only when the owner selects a long run. The template's managed contract block
does not carry it, and a project that has not selected this workflow should not
have it. Preserve project-specific rules when merging, and keep one copy.

```markdown
## Continuation decision (separate from closure)

Closure (`scripts/projectstate_gate.py`, exit 0/1/2) judges recorded outcome
only. Before the next unit of work, make a separate continuation decision at
each action boundary: before delegating, before an expensive test/build/
rehearsal, after a failure cluster or completed increment, and when a
deadline/budget warning appears.

Name the unchanged acceptance criterion, release dependency, or safety boundary
addressed; the material information or behavior change expected; why this is the
smallest sufficient check or change; what changed since any equivalent attempt
(source, artifact, environment, fixture, or hypothesis); and whether
prerequisites and remaining budget allow completion or safe checkpointing
including integration and reporting.

Dispositions are continue, replan, wait/monitor, finalize, or stop. A passed
gate never authorizes unfinished work to continue. This rule is advisory unless
the actual runner refuses inadmissible actions; the validator never executes
commands found in repository text.

Protect the critical path: prefer dependency-ready work by its relation to the
authorized outcome; safety stop-lines first. A primary blocker does not forbid
genuinely independent authorized work, but secondary polishing must not consume
a slot needed for a now-runnable primary dependency. Do not poll an unchanged
blocked lane to satisfy a quota; name the event that makes it actionable again.
Bound one working increment and its integration proof; do not open competing
active slices or silently narrow acceptance. A new defect, a ruled-out
hypothesis, or a newly isolated external prerequisite is progress of its
category, not shipped progress.

Verify at the right level: focused reproducer, then affected integration, then
installed/release proof when the change or acceptance crosses that boundary. A
full rerun needs an invalidation reason; reuse prior evidence only for the same
source/artifact/environment and scope. A changed candidate or
security-sensitive restore may require a new end-to-end rehearsal. In a safe
batch, collect independent failures without aborting everything at the first
error; keep isolation and fail-fast where state is shared or destructive.
Fixture fixes must preserve the invariant and be explained; single-test passes
across different revisions are not a combined pass. Keep unrun and blocked cases
explicit.

For an explicitly selected long run, record one absolute UTC deadline, the
finalization boundary, the work envelope, delegation limits, and the usage
budget in existing state/assignment fields — never as new STATE.yaml top-level
keys the gate rejects. Separate the maximum work window from any monitoring
obligation. Reserve integration and handoff capacity; workers inherit the
deadline and return while integration is still feasible. At finalization admit
no broad new work; checkpoint honestly without promoting it to validated.
Missing closure is interruption, not success. When model usage is unobservable,
label it unknown and use authorized fallback limits on batches, retries, and
elapsed time; do not invent ceilings or claim savings without a same-model
comparison. Keep the evidence summary a current view with linked detail, not a
full history dump; never omit safety and authority instructions to save
context. See `prompts/LONG_RUN_CONTROL.md` in the template when a long run is
selected; it is optional and is not part of the default six-file core.
```
