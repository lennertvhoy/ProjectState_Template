# Upgrading ProjectState

Current template version: `projectstate-template-v6`

## Release 6.3.0: managed contract and mechanical updates

Release 6.3.0 splits an instance's `AGENTS.md` into a template-owned part and a
project-owned part. The template's contract is one managed block between
`<!-- projectstate:managed:start release=X.Y.Z -->` and
`<!-- projectstate:managed:end -->`; everything after the end marker belongs to
the project. `scripts/projectstate_update.py` brings an instance to the
template's current release by replacing exactly two things: the vendored
`scripts/projectstate_gate.py` and that block.

`releases/index.json` records what each release asks of an instance
(`instance_action`): `none`, `mechanical` (this command does it), or `semantic`
(a person merges the change, as in the v5 migration below). Release 6.3.0 is
`mechanical`. The command does not read that field, so check it for any newer
release before updating. It updates only instances whose `STATE.yaml` declares
`projectstate-template-v6`; a v5 repository needs the semantic migration further
down, and the template repository itself is refused.

### Update an instance

1. Start from a clean checkout on a private branch, or in a separate worktree
   if the checkout has other uncommitted work:

   ```bash
   git switch -c projectstate/release-6.3.0
   ```

2. Run the dry run. It writes nothing (adjust the path to your template checkout):

   ```bash
   python3 ~/Projects/ProjectState_Template/scripts/projectstate_update.py --target .
   ```

3. Read the report, as described below, and resolve anything it refuses.
4. Apply the update:

   ```bash
   python3 ~/Projects/ProjectState_Template/scripts/projectstate_update.py --target . --apply
   ```

5. Rerun the project's primary journey and `python3 scripts/projectstate_gate.py`,
   read `git diff`, and commit `AGENTS.md` and the gate together. The command
   never commits and never creates branches.
6. Merge the branch (`git merge --ff-only projectstate/release-6.3.0`). The fleet
   doctor lists a local `projectstate/release-<release>` branch that HEAD does not
   contain under "Ready to merge", with this command. Undoing the update means
   dropping the branch, because only two files changed.

### Read the report

The report has one line group for the gate and one for `AGENTS.md`:

- `Gate scripts/projectstate_gate.py`: `replace` (the file is a released gate),
  `install` (it was missing), `none` (already current), or `replace_edited`.
- `Contract AGENTS.md`: `convert` (the first time: no managed block yet),
  `replace` (an older block), `clean` (only refresh text is removed), `create`
  (no `AGENTS.md`: a managed block plus empty `## Local rules` and
  `## Owner directives` is written), `none`, or `replace_edited`.

Under the contract line:

- `remove refresh notice` and `remove refresh section`: text left by the
  2026-09-05 and 2026-09-06 refreshes below, namely
  `<!-- projectstate-NAME:start -->` ... `<!-- projectstate-NAME:end -->` blocks
  and sections headed "Required first action" or "Latest required refresh". The
  block makes them unnecessary, so they are removed and listed.
- `replace N template sections of known text`: sections whose text matches what
  an earlier release generated (6.0.0 through 6.2.0, kept in
  `releases/contract-history.json`). They are dropped because the block now
  carries the contract. That includes `Continuation decision (separate from
  closure)` and `Optional persistent threads`, which release 6.3.0 moved out of
  the generated contract into the opt-in prompts `prompts/LONG_RUN_CONTROL.md`
  and `prompts/PERSISTENT_THREADS.md`. They were inert until the owner selected
  the workflow; if this project selected one, copy its block from that prompt
  into a local section in the same change.
- `modified template section`: a section with a template heading (`Read order`,
  `Authority`, `Workflow`, `Boundaries`, and so on) whose text matches no
  released text, usually because someone added a project rule to it. This needs
  a person. The report shows a diff against the closest known text.
  Move each project rule into a local section (any heading that is not a
  template heading), commit, and repeat the dry run: the section then matches
  known text and is replaced. If nothing in it is worth keeping, pass
  `--accept-modified-sections`.
- `possible template text in local sections`: a level-3 heading inside a local
  section that is named like a template section, such as `### Workflow`. The
  command cannot tell a copy from the project's own section, so it refuses;
  `--accept-modified-sections` keeps these headings as local text.
- `local text: N bytes preserved`: every other block of `AGENTS.md` follows the
  managed block byte for byte, in its original order. The command checks this
  before it writes.

### Refusals and flags

On any refusal the command writes nothing, and the dry run exits `2` exactly
when `--apply` with the same flags would refuse. Four flags clear the refusals
that a person can judge. A flag says that you have read the report; it does not
make the change safe.

| Flag | The command refuses because | The flag | What it costs |
| --- | --- | --- | --- |
| `--replace-edited-gate` | The vendored gate's sha256 matches no released gate: it was edited, or it came from elsewhere. The report shows the diff. | Replaces it with the current release's gate. | The local edits, which then survive only in Git history. A gate that its own project edits weakens the check on that project; propose the change to the template instead. If the edit added statuses such as `publicly_verified`, see "Truth at handoff" below. |
| `--replace-edited-contract` | The managed block's text matches no released block, so someone edited it. The report shows the diff. | Replaces the block with the current one. | The edit, kept only in Git history. Project rules belong after the end marker. |
| `--accept-modified-sections` | A template-named section matches no released text, or a local section holds a level-3 heading named like a template section. | Removes the modified sections and keeps the look-alike local headings as local text. | Any project rule still inside a removed section; the flag moves nothing for you. A dry run with the flag prints the full removed text and still writes nothing, and `--json` always carries it. |
| `--allow-dirty` | `AGENTS.md` or the gate has uncommitted changes and the update would write, or git cannot report its status. | Skips that check. | The update overwrites those working-tree files, so uncommitted edits are lost. |

Other refusals have no flag because the command cannot make them safe: a target
that is not a `projectstate-template-v6` instance or is the template itself, a
symlinked `AGENTS.md`, `scripts` directory, or gate, an `AGENTS.md` that is not
UTF-8 or uses CR or CRLF line endings (convert it to LF first, so local text can
be kept byte for byte), malformed managed block markers, an `AGENTS.md` that
declares `repo_role: template_repository`, and a template whose gate release
differs from its index.

### What the command touches

It replaces the gate and the managed block, nothing else. It never writes
`PROJECT.md`, `STATE.yaml`, `evidence/`, or the project's own `AGENTS.md` text,
and it reads `STATE.yaml` only for its version. The only git it runs against the
instance is read-only. It does not run the journey or judge the project, so the
rerun in the last step is yours.

`--apply` writes the gate first and `AGENTS.md` second, each atomically (a
temporary file renamed over the original). If a write fails, rerun `--apply` to
finish. A second `--apply` on an updated instance changes nothing, and it does
not refuse on the uncommitted result of the first, because the clean-tree check
applies only when the update would write. `--check` writes nothing and exits `1`
when a change is needed, which suits automation; `--json` prints the plan as
JSON. Exit codes: `0` (dry run complete, applied, or already current), `1` (only
with `--check`, change needed), `2` (refused or invalid).

### After the update

A newer gate can reject records an older gate accepted, and the update never
edits `STATE.yaml` or evidence to fix that, so read the gate's output. Release
6.3.0 adds one rule and some warnings. The rule: a `validation.human_acceptance`
of `accepted`, `rejected`, or `waived` needs a matching `## Owner decision`
section in the slice summary, with `- Decision:` (equal to `human_acceptance`),
`- Date:` (YYYY-MM-DD, not in the future), and `- Owner words:` (the owner's
words in quotes; an empty one is rejected) lines.
The warnings, which never change the exit code: an oversized `STATE.yaml` or
`PROJECT.md`, a long project-owned part of `AGENTS.md`, or an `AGENTS.md` with no
managed block. If the owner made a decision earlier without that record, add the
section to the slice summary by hand and quote the words the owner actually gave;
never invent them. `projectstate_decide.py` records only pending decisions.
Earlier releases tightened the gate as well; the changelog lists them. The fleet
doctor (`projectstate_fleet.py`) then reports the instance's gate and block as
`current`.

## Migrating from v5 to the outcome-first core

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
lock or self-updating governance. For a v6 instance use
`scripts/projectstate_update.py` (the 6.3.0 section above), which a person runs
from the template; an instance never updates itself.

## Compatibility profiles

`minimal`, `solo`, `team`, and `regulated` remain selectable for existing
consumers during the migration window. New projects default to `core`.
Compatibility-profile maintenance does not change the v6 project outcome or
acceptance criteria.

## Truth at handoff

Report local implementation, primary-journey validation, remote branch, CI,
deployment, and human acceptance separately. A local migration can be complete
without being pushed; it must say so.

*Superseded by release 6.3.0 for existing v6 instances: the update command installs the current gate, so do not copy one by hand. The next paragraph is kept as history.*

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

*Superseded by release 6.3.0: the update command removes this notice, and the rules now live in `prompts/LONG_RUN_CONTROL.md`. Kept as history.*

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

*Superseded by release 6.3.0: the update command removes this notice, and the rules now live in `prompts/PERSISTENT_THREADS.md`. Kept as history.*

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
