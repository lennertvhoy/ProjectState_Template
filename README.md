# ProjectState Template

ProjectState is a small, repo-based workflow for keeping coding agents aligned
with a real product outcome.

Current template version: `projectstate-template-v6`

The default is deliberately narrow: one human-owned project definition, one
current slice, one primary user journey, and one bounded evidence summary. A
failed user journey always outranks passing secondary checks.

## Status and license

ProjectState Template is released under the [ProjectState Free Use License -
Teaching Rights Reserved](LICENSE). It is free of charge for personal and
commercial use, and permits use, copying, modification, redistribution,
sublicensing and sale, provided the copyright and license notices stay. Teaching,
training, coaching, courses, workshops and tutorials built on the software or the
ProjectState workflow need prior written permission from the copyright holder, so
the project is source-available, not OSI-approved open source. The plain-language
[license FAQ](LICENSE_FAQ.md) explains the intent; the license text is
authoritative.

## Community

Contributions are welcome; see [CONTRIBUTING.md](CONTRIBUTING.md),
[SECURITY.md](SECURITY.md) and [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

## Start

Create a new project. `--target` is an absolute path (the generator refuses a
path with `..` in it), and `new` creates it:

```bash
python3 scripts/init_template.py new --name "Your Project" --target /path/to/your-project
```

Adopt an existing repository without replacing its README:

```bash
python3 scripts/init_template.py adopt --name "Your Project" --target /path/to/your-project --dry-run
python3 scripts/init_template.py adopt --name "Your Project" --target /path/to/your-project
```

Both commands use the `core` profile unless you choose `--profile hardened`.

## The core

| Path | Sole responsibility |
| --- | --- |
| `PROJECT.md` | Human-owned user, outcome, scope, non-goals, and durable constraints |
| `STATE.yaml` | One current slice, its acceptance, journey, blockers, risks, and exact next action |
| `AGENTS.md` | The template's managed contract block, then the project's own local rules and owner directives |
| `evidence/<slice-id>/summary.md` | Commands, environment, results, artifacts, the owner's decision, and unresolved limitations |

`AGENTS.md` is one managed block followed by the project's own text. The block
sits between `<!-- projectstate:managed:start release=X.Y.Z -->` and
`<!-- projectstate:managed:end -->`, and its source is `core/AGENTS.managed.md`.
It holds what is the same for every project: read order, authority, workflow,
owner decisions, outcome precedence, simplification and risk, and boundaries.
Never edit it inside a project; change it in the template and update the
project (see [Releases, fleet and updates](#releases-fleet-and-updates)).
Everything after the end marker belongs to the project. A generated file starts
with `## Local rules` (domain rules, commands, safety limits) and
`## Owner directives` (standing, dated instructions from the owner, such as
`- 2026-10-06, until 2026-12-31: no new dependencies.`).

The generated core also contains `scripts/projectstate_gate.py`, a small
dependency-free checker. It checks recorded contract and evidence consistency,
with the primary journey dominant. `README.md` remains product documentation, not a
second state surface.

The first gate run is expected to fail. A scaffold cannot honestly know the
project's user, outcome, or real journey:

```bash
python3 scripts/projectstate_gate.py
```

Confirm `PROJECT.md`, replace the placeholders in `STATE.yaml`, run the real
journey yourself, record the result, and rerun the gate.

## What “green” means

- `implemented`: the change exists.
- `validated`: the named primary journey passed in the named environment.
- remote/CI/deployed: separately proven only when acceptance crosses that boundary.
- `accepted`: the owner accepted the product result, recorded as an
  [owner decision](#owner-decisions).

Unit tests, repository validators, hashes, clean Git status, or complete metadata
cannot turn a failed, blocked, or unrun primary journey green. Secondary checks
may add blockers; they never reverse the primary result.

The gate reads recorded state and evidence. It never executes a command merely
because repository text contains one. Exit codes are:

| Code | Meaning |
| --- | --- |
| `0` | `RECORDED OUTCOME VALIDATED`: recorded evidence supports validation with no recorded blockers |
| `1` | `OUTCOME NOT VALIDATED`: honest unfinished work, unresolved placeholders, or a blocking finding |
| `2` | `INVALID PROJECTSTATE CORE`: malformed, unsafe, or contradictory records |

The gate rejects recognizable `Not yet defined`, `TODO`, and `TBD` placeholders
in the contract and journey. It cannot judge whether arbitrary prose defines a
good product, verify that a command actually ran, authenticate a human approval,
or enforce checks described only in `HARDENED_POLICY.md`. Those require real
observation and human review; record applicable check failures as blockers.

Soft limits print `WARN:` lines and never change the exit code: an oversized
`STATE.yaml` or `PROJECT.md`, a long project-owned part of `AGENTS.md`, or an
`AGENTS.md` with no managed block. Malformed block markers are an error (exit
`2`). `--version` prints the gate's release.

When installation is in scope, test the distributed artifact in the intended
clean environment. Source tests and a prepared development machine do not prove
that package contents, launchers, or installation work. Keep publication and
rehearsal results in supporting evidence; the primary journey retains its actual
`not_run`, `passed`, `failed`, or `blocked` status.

## Human-owned governance

The human owns the project outcome, non-goals, acceptance criteria, governance,
risk exceptions, and product acceptance. Agents may update observed status,
evidence, blockers, risks, and the next action. They may propose a governance
change, but cannot approve or apply one simply to make their own work pass.

This deliberately removes companion control commits, mutable commit-head
bindings, line budgets, correction counters, and runtime dependence on workflow
files from the default model.

### Owner decisions

When a slice is validated, the owner accepts, rejects, or waives it; passing
checks never stand in for that answer. One command records it (run it from the
template checkout; `--dry-run` prints the planned edits and writes nothing):

```bash
python3 scripts/projectstate_decide.py ../your-project accept "the owner's words"
```

Use `reject` or `waive` in place of `accept`. The command appends
`## Owner decision` (`- Decision:`, `- Date:`, `- Owner words:`, and
`- Recorded by:`) to the slice's evidence summary and sets
`validation.human_acceptance`; `accept` also sets `current_slice.status` to
`accepted`. It then runs the gate on the result, restores both files if the gate
reports an error, and never commits. The gate requires that record whenever the
decision is accepted, rejected, or waived, and treats a record beside a
`pending` decision as a contradiction (exit `2`). `reject` adds a blocker;
`waive` adds none and leaves the slice status alone. A project whose vendored
gate predates release 6.3.0 does not know `waived`; the command warns, and the
project needs the update first. The gate checks records only: the quoted words
are reviewable in Git, but nothing authenticates who ran the command.

## Two-strike simplification

After two evidenced failures at the same delivery boundary, stop extending the
mechanism. Record:

- the assumption being reconsidered;
- one moving part removed or bypassed;
- the smallest real journey to rerun.

The outcome gate blocks further closure until that review exists. This is based
on two concrete failure records, not a general-purpose correction counter.

## Risk handling

The core fails closed for unresolved data-loss, destructive-operation,
privilege-escalation, secrets/private-data exposure, and permission-boundary
risk. Critical or high findings with `reachable` or `unknown` exposure block
regardless of category spelling. Category labels cannot bypass that stop-line.

Other findings are assessed by severity, exposure, consequence, and affected
environment. A vulnerability confined to build tooling or a demonstrably
unreachable component is recorded with an owner and decision; it does not
automatically outweigh a working product journey. Temporary acceptance needs a
named human approver, rationale, and unexpired date.

## Profiles

### `core` — default

Use for ordinary product work. It installs the four canonical artifacts and the
outcome gate. Backlogs, worklogs, ADRs, release ledgers, multi-agent matrices,
and compliance records are optional project choices.

```bash
python3 scripts/init_template.py new --name "Your Project" --target /path/to/your-project --profile core
```

### `hardened` — explicit opt-in

Use only when actual exposure, regulation, or delivery obligations justify the
additional policy. It adds `HARDENED_POLICY.md`; hardened checks may add blockers
but cannot override the primary journey.

```bash
python3 scripts/init_template.py new --name "Your Project" --target /path/to/your-project --profile hardened
```

The earlier v5 profiles, scripts and state files live at tag `v5-final`
(`git worktree add ../projectstate-v5 v5-final`). This repository is v6 only,
and the generator refuses the v5 profile names with exit code 2.

## Runtime independence

ProjectState coordinates work only. Product code must not import, parse, or
require `PROJECT.md`, `STATE.yaml`, `AGENTS.md`, `evidence/`, or its helper script
to start or run. Deleting the coordination layer must not break the application.

## Releases, fleet and updates

Template changes reach existing projects through a release index, a read-only
report, and an update command. None of them edits project-owned text.

**Release identity.** `releases/index.json` lists every release with its date,
tag, the sha256 of its gate and of its managed block, a one-line summary, and
the instance action it needs: `none`, `mechanical` (the update command does it),
or `semantic` (a person merges the change). The block hash is null for releases
that predate the block. `python3 scripts/projectstate_release.py check` compares
the index with the gate, the block, and the local release tags, and exits `2` on
any mismatch; a released entry is frozen. `cut --date YYYY-MM-DD` fills a draft
entry's hashes and marks it released (it never creates the tag), and `hashes`
prints the current ones.

**Fleet doctor.** `python3 scripts/projectstate_fleet.py` is a read-only report
over the repositories directly under a folder (default: the folder that holds
the template). It never writes inside a repository and never runs a
repository's own code. For each v6 repository it shows whether the vendored gate
and managed block match a release (`current`, `behind`, or `draft` for a
candidate that is not cut yet) or match none (`unknown` gate, `edited` block),
the size of the startup reading, the gate's verdict, and the slice; other
repositories are only listed. The report goes to
`~/.local/state/projectstate/fleet.md` and `fleet.json` (`--out` changes the
folder, which must lie outside the scanned one); `--stdout` prints one report and
writes nothing.

The owner inbox at the top of the report lists what needs a person:

- decisions waiting for the owner, each with its exact `projectstate_decide.py`
  command;
- blocked slices;
- items to review: a gate or block that matches no release, expired owner
  directives, risk acceptances about to expire, and a slice replaced while it
  awaited the owner with no recorded decision (a replacement made before the
  repository adopted the managed block is history, counted in
  `summary.silent_replacements_before_rule` of `fleet.json` and not listed);
- an unmerged `projectstate/release-<release>` update branch, with the command
  that merges it.

**Update.** `python3 scripts/projectstate_update.py --target ../your-project` is
a dry run, and `--apply` writes. It replaces the project's vendored gate and its
managed `AGENTS.md` block and nothing else: never `PROJECT.md`, `STATE.yaml`,
`evidence/`, or the project's own `AGENTS.md` text.
[`docs/UPGRADING.md`](docs/UPGRADING.md) explains the report and the refusal
flags.

## Keeping the owner's words

What an owner says in conversation (a constraint, a decision, "do it this way")
lives in no file unless an agent writes it down, and measured agents mostly do
not, even when a rule tells them to. `scripts/projectstate_hooks.py` makes the
host do it, in Claude Code and in OpenCode, with or without the core:

```bash
python3 scripts/projectstate_hooks.py install --root ../your-project --host all   # --dry-run to preview
```

`install` copies the tool into the project's `scripts/`, merges three hooks into
`.claude/settings.json` without removing anything already there, and copies the
OpenCode plugin to `.opencode/plugins/projectstate.js` (`--host claude` or
`--host opencode` for one host; `uninstall` removes the hooks it merged and the files it copied, and can leave an
empty `.claude/settings.json` or `.opencode/plugins/` behind). After a restart:

- **Every owner prompt is logged** verbatim to `.projectstate/owner-log.md`. A
  pasted block is logged as one line saying it is pasted text, not the owner's
  words. Prompts that an orchestrating agent writes to OpenCode subagents are not
  logged. Obvious secrets are redacted on a best-effort basis.
- **Every session starts with a brief** of at most 6,000 characters, built from
  the files and git: the durable constraints in `PROJECT.md`, the current slice
  and whether its journey result was recorded by a run or typed by hand, a pending
  owner decision with the command that records it, the owner's logged words that
  read as standing instructions but are not in the files yet, and the owner's last
  three requests, marked as possibly done. It is repeated after compaction.
- **When the owner gave a standing instruction**, the agent is asked once, as it
  finishes, to copy it verbatim into `## Durable constraints` with the date, and to
  leave one-off requests out. The same hook runs the read-only gate and asks once
  for a fix when the records it wrote are invalid.

The log is local: `.projectstate/` ignores itself in Git because prompts can hold
private data. The hooks never fail a session. The fleet doctor shows each
instance's hooks (`current`, `behind`, `edited`, `v1`, `partial`, `absent`) and
the install command when one is needed; not installing them is fine.
`scripts/projectstate_owner_log.py` is the earlier, measured v1, kept for the evals.

Measured in `evidence/handoff-eval-001/summary.md` ("Follow-up 2"): with 30
realistic owner prompts between the constraints and the session that needed them,
the v2.0 hooks kept the owner's two chat-only constraints in every chain on haiku
and sonnet, with or without the core, and the first session filed them in the
project's files (the shipped v2.2 changes the briefing's framing and was not
measured); the core alone, no core, and v1 did not (v1 only when an agent
happened to open the raw log file).

## What the evidence shows

The measurements are in [`evidence/handoff-eval-001/summary.md`](evidence/handoff-eval-001/summary.md),
"Follow-up 2". Every chain used haiku or sonnet, three repeats per cell, one task.

- **The core alone did not keep the owner's chat-only constraints.** It kept
  neither of the two (0/3 on both models), and on sonnet its mean check score was
  6.33 against 6.00 without it. On sonnet it did stop agents from claiming done
  while a hidden check failed (0 of 3 chains, against 3 of 3 without it); on
  haiku it did not (3 of 3 both ways). It cost more: 2.4x the plain repository on
  sonnet, $0.382 against $0.159 per chain (finding 3).
- **The host hooks kept the constraints.** With the hooks, the core and no-core
  conditions kept both chat-only constraints in 3/3 chains on both models (2/3 in
  one defective lean wording-1 cell) against 0/3 without hooks (finding 1). The
  stop hook filed all three owner constraints 3/3 in both models; without it, 0/3
  (finding 2). Those are the v2.0 hooks. v2.1 regressed on sonnet (1 of 3 chains
  claimed done while a hidden check failed, finding 6); the v2.2 hooks in this
  release answer that and were not measured.
- **Limits.** One task; n=3 per cell (2 for lean wording 2, with two more chains
  lost to 429 errors); haiku and sonnet only; Claude Code headless only; the v2.1
  haiku run incomplete. v2.2 is described but was not measured (findings 6-7,
  Limits).

## Optional material

Add these only when the project needs them:

- `BACKLOG.md` for a real multi-slice roadmap;
- ADRs for durable architectural decisions;
- threat models for meaningful attack surfaces;
- remote CI/review proof when delivery is in scope;
- signing, audit retention, or compliance evidence when obligations require it;
- multi-agent ownership rules when agents actually run concurrently.

The initializer installs no optional tooling; add justified project-specific
tooling in a separately reviewed change.

Opt-in workflows live in `prompts/` and add nothing to the generated core: no
text in `AGENTS.md`, no `STATE.yaml` key, no extra file. Each stays inert until
the owner selects it, and the prompt itself says what to copy and where.

- [Persistent threads](prompts/PERSISTENT_THREADS.md): role prompts and the
  ownership, assignment, recovery, and integration rules for a coordinator with
  workers, copied into the project's local sections. There is no automatic
  thread routing or model selection.
- [Long-run control](prompts/LONG_RUN_CONTROL.md): the continuation decision and
  the selected-run record for a long, explicitly authorized run, copied into
  the project's local sections.
- [Measured improvement rounds](prompts/IMPROVEMENT_ROUNDS.md): for an instance
  that has a measurable outcome, an event-triggered, proposal-only workflow with
  a mechanically enforced stop rule. It is copied in by hand
  (`prompts/IMPROVE_MD_TEMPLATE.md` plus `scripts/projectstate_improve_check.py`)
  and stays inert until the owner sets `enabled: true`. An instance with no
  measure should not use it.

Git history is the default work history. Do not duplicate it into a mandatory
workflow ledger.

## Maintainer notes

Start with the core files above, `core/AGENTS.managed.md`, `releases/index.json`,
`scripts/init_template.py`, `scripts/projectstate_gate.py`, and
`scripts/test_outcome_core.py`.
[The worked example](docs/WORKED_EXAMPLE.md) runs a packaged product through
failure, a handoff read by a new process, recovery, and restart.

Changing the gate or the managed block is a release. Add a draft entry at the
end of `releases/index.json`, set `latest` and the gate's `RELEASE` to its
number, and make the change. `python3 scripts/projectstate_release.py check`
passes on a draft and prints the hashes that `cut --date YYYY-MM-DD` will
record. After `cut`, commit the index and create the tag yourself. Both
validation jobs in CI run `check`.

The design decisions are recorded in `docs/adr/`: the outcome-first core in
`0003-outcome-first-core.md`, the release channel and the removal of v5 from
this repository in `0004-release-channel-and-legacy-split.md`. The v5
implementation lives at tag `v5-final`; this repository's current authority is
`AGENTS.md`, `PROJECT.md`, and `STATE.yaml`.

Run the focused core journey, then the whole suite:

```bash
python3 scripts/test_outcome_core.py
python3 -m pytest scripts/ -q
```

A local pass is not remote delivery, CI verification, release, or human acceptance.
