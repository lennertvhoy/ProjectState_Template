# Upgrading to the outcome-first core

Current template version: `projectstate-template-v6`

This is a semantic migration, not a file refresh. The v5 state surfaces may
contain useful project truth, so do not delete them before extracting it.

## Safe migration

1. Create a private migration branch from a clean, current checkout.
2. Read the existing project documents and identify:
   - the primary user and observable outcome;
   - durable scope, non-goals, and constraints;
   - the one slice actually in progress;
   - its acceptance criteria and smallest real journey;
   - open blockers, risks, and the exact next action.
3. Generate a fresh core instance in a temporary directory:

   ```bash
   python3 scripts/init_template.py new --name "Your Project" --profile core --target /tmp/your-projectstate-core --no-init-git
   ```

4. Transfer only the extracted truth into `PROJECT.md`, `STATE.yaml`, and the
   current evidence summary.
5. Run the real primary journey and `python3 scripts/projectstate_gate.py`.
6. Keep old files for review until the new core has been accepted. Remove or
   archive them in one explicit migration change; do not maintain both models as
   live truth.

## Mapping

| v5 material | v6 destination |
| --- | --- |
| product/user/scope across DNA, status, or state | `PROJECT.md` |
| active slice, blockers, risks, next action | `STATE.yaml` |
| current command results and limitations | `evidence/<slice-id>/summary.md` |
| closed worklog entries | Git history; retain separately only if legally needed |
| backlog | optional `BACKLOG.md` if the project genuinely needs one |
| release/remote/compliance controls | explicit `hardened` or project-specific policy |
| control-head bindings, counters, fixed line budgets | no migration; retire them |

Do not translate a green v5 repository gate into a passed primary journey. Rerun
the journey in a representative environment.

## Existing automated upgrader

`scripts/projectstate_upgrade.py` remains a v5 compatibility tool. It can safely
refresh assets inside a locked v5 profile, but it does not perform this semantic
migration and must not claim that it does. The v6 core intentionally has no asset
lock or self-updating governance.

## Compatibility profiles

`minimal`, `solo`, `team`, and `regulated` remain selectable for existing
consumers during the migration window. New projects default to `core`.
Compatibility-profile maintenance does not change the v6 project outcome or
acceptance criteria.

## Truth at handoff

Report local implementation, primary-journey validation, remote branch, CI,
deployment, and human acceptance separately. A local migration can be complete
without being pushed; it must say so.

For an existing v6 core, review and copy the updated `scripts/projectstate_gate.py`
from a fresh temporary core; preserve the project's contract, state, and evidence.
The corrected gate blocks reachable or unknown-exposure high/critical findings
regardless of category, recognizes unresolved contract placeholders, and rejects
ambiguous primary evidence and symlinked inputs. Exit codes remain `0`, `1`, `2`;
success now prints `RECORDED OUTCOME VALIDATED`. Prefer exit codes in automation.

If a downstream gate added statuses such as `publicly_verified`, retain that
progress in the evidence summary and restore the primary journey's actual
execution status. Do not mark a target-environment journey passed because a
different environment or a publication step succeeded.

## Bounded long-run control refresh (2026-09-06)

For this revision, generate a temporary core and semantically merge its
`Continuation decision (separate from closure)` section into the project's
`AGENTS.md`. Preserve all project-specific rules, outcome, acceptance, state,
and evidence. This section is advisory unless the actual runner refuses
inadmissible actions; a passed outcome gate never authorizes unfinished work
to continue.

Key points to carry across: decide continue/replan/wait-monitor/finalize/stop
before delegating, before expensive tests/builds/rehearsals, after failure
clusters or completed increments, and on deadline/budget warnings; protect the
critical path without polling an unchanged blocked lane; treat renaming as no
fresh retry and prior simplification review as no indefinite permission; verify
reproducer → affected integration → installed/release proof with an
invalidation reason for full reruns; record any selected long-run envelope
(deadline, finalization boundary, work limits, usage budget) in existing state
or assignment fields, never as new `STATE.yaml` top-level keys.

The optional `prompts/LONG_RUN_CONTROL.md` in the template holds the
selected-run record format, worker/finalization rules, and unknown-usage
fallback. Read or copy it only when the human explicitly selects a long run.
It is not a canonical artifact and is not needed at startup. Do not paste
unsupported run fields into `STATE.yaml`; the gate still rejects unknown
top-level keys. Do not claim quota savings without a same-model comparison.

A queued refresh is complete only after the instructions are updated, project
truth is preserved, the real primary journey is rerun, and the resulting
evidence is recorded. If blocked, retain the notice and record the exact
blocker and next action.

## Optional persistent-thread refresh (2026-09-05)

For this revision, generate a temporary core and semantically merge its
`Optional persistent threads` section into the project's `AGENTS.md`. Preserve
all project-specific rules, outcome, acceptance, state, and evidence. This small
section is inert until the human selects the workflow; installing it does not
authorize launching threads, choosing paid models, or running parallel work.

The optional `prompts/PERSISTENT_THREADS.md` in the template contains role prompts
and an assignment/return format. Read or copy it only when the workflow is
selected. It is not a fifth canonical artifact and is not needed at startup.
Existing model-routing guidance remains optional. Do not import the historical
v5 worktree orchestrator, reservation ledger, or automatic upgrade machinery.

A queued refresh is complete only after the instructions and applicable gate
are updated, project truth is preserved, the real primary journey is rerun, and
the resulting evidence is recorded. If blocked, retain the notice and record the
exact blocker and next action; do not repeatedly scaffold or overwrite files on
resume. Preserve the pending product task and return to it after setup.

## Optional measured improvement rounds (2026-10-06)

No refresh is required and none is queued. The generated core, `AGENTS.md`, and
`STATE.yaml` are unchanged, and existing instances need nothing from this
revision. It is an opt-in asset for an instance that has a deterministic,
repeatable measure of its own outcome.

To opt in, copy `prompts/IMPROVE_MD_TEMPLATE.md` to `IMPROVE.md` and
`scripts/projectstate_improve_check.py` to the same path in the instance, then
follow `prompts/IMPROVEMENT_ROUNDS.md`. The template ships `enabled: false`; the
owner records the measure, its baseline, the evaluator files under `protected`,
the stop rule, and a hard token cap before enabling it. Do not paste its fields
into `STATE.yaml` (the gate still rejects unknown top-level keys), do not widen
the agent's scope beyond the instance, and do not let a round apply its own
proposal. Do not add the `AGENTS.md` trigger line unless the owner wants it.

The workflow is not validated as beneficial. Record a measure-only baseline on
one real instance before enabling proposals, and disable it when the stop rule
trips rather than re-arming it by habit.
