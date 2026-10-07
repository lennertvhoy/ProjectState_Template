# ADR-0004: Release channel, and removing v5 from main

**Status:** accepted
**Date:** 2026-10-07
**Author:** human-directed agent

## Context

By release 6.2.0 every instance carried its own copy of the template's contract
inside its `AGENTS.md`, next to a vendored gate. Bringing an instance up to date
was a judgment merge by whichever session worked in that repository, and nothing
showed which instances were current. When release 6.3.0 was cut (see
`evidence/release-channel-001/summary.md`), 18 of 21 v6 gates were behind, 2
matched no release, and 20 `AGENTS.md` files carried no managed block. The state
schema string `projectstate-template-v6` had not changed across four releases
that changed the gate and the contract, so it could not tell a current instance
from a stale one. Separately, the doctor counts 18 slices that were replaced
while they waited for the owner, with no recorded decision; recording a decision
meant hand-editing two files.

This repository also still carried the whole v5 line as compatibility material:
four profiles, 95 scripts and tests, schemas, fixtures, a profile catalog, slash
commands, skills, state files, ledgers, and a legacy quality gate that ran in CI.
That was 470 of 546 tracked files. The fleet doctor on 2026-10-07 found 44
repositories, 14 of them v5. One of the 14 has changed since August
(`example-project-04`, 2026-10-05); it neither vendors nor runs this
template's v5 scripts, and its CI is `cargo` and `npm` only. The other thirteen
last changed on or before 2026-08-29; nine of them carry their own copies of v5
scripts and four carry none. The v5 profile names were also still selectable, and
agents were told in prose not to use them.

## Decision

**Two identifiers, kept apart.** The state schema (`projectstate-template-v6`: the
`VERSION` file, the gate's `VERSION`, `STATE.yaml` `version:`, and
`releases/index.json` `state_schema`) says what format the state is in and changes
only when that format changes incompatibly. The release number (`6.3.0`, the
gate's `RELEASE`) names one gate plus one managed block and changes whenever
either changes. `releases/index.json` records for each release its date, tag,
`gate_sha256`, `contract_sha256` (null before 6.3.0), the instance action (`none`,
`mechanical`, or `semantic`), and a summary. A released entry is frozen.
`projectstate_release.py check` compares the index with the gate, the block, and
the local tags and exits 2 on any mismatch; `cut --date` fills a draft's hashes
and never creates a tag. An instance's release is read from the hashes of its own
files, never from a string it could edit.

**One managed block.** `core/AGENTS.managed.md` is the only source of the
template-owned part of an instance's `AGENTS.md`. An instance carries it once,
between `<!-- projectstate:managed:start release=X.Y.Z -->` and
`<!-- projectstate:managed:end -->`, stamped with the gate's release.
Everything after the end marker belongs to the project (`## Local rules` and
`## Owner directives`). The opt-in workflows (continuation decision, persistent
threads, improvement rounds) left the generated contract and live in `prompts/`;
they add nothing to a project until the owner selects one.

**A locked evaluator.** The gate judges outcome claims, so an agent must not be
able to change it in the repository it is judged in without anyone noticing. The
gate and the block are locked by hash. The fleet doctor, a read-only report that
never writes in a repository and never runs a repository's code, compares each
instance's vendored gate and block with the index: `current`, `behind`, `draft`
(a candidate not cut yet), or matching no release (`unknown` gate, `edited`
block, listed for review). The lock detects; it does not prevent. A repository
can still be edited, and the doctor makes that visible across the whole fleet.

**A mechanical, pull-based update.** `projectstate_update.py --target DIR`
replaces exactly two things, the vendored gate and the managed block, and nothing
else: never `PROJECT.md`, `STATE.yaml`, `evidence/`, or the project's own
`AGENTS.md` text. It is a dry run by default (`--apply` writes atomically,
`--check` serves automation); any refusal means zero writes, and flags clear only
the refusals a person can judge (an edited gate, an edited block, modified template
sections, uncommitted changes). It converts an older `AGENTS.md` by recognizing
the texts earlier releases generated (`releases/contract-history.json`) and keeps
local text byte for byte. It never commits. It is pull-based: a person or the
instance's own session runs it from a template checkout; the template does not
push into instances and an instance does not update itself. The doctor lists a
fast-forwardable `projectstate/release-<release>` branch as ready to merge.

**One command for the owner's answer.** `projectstate_decide.py TARGET
{accept,reject,waive} "OWNER WORDS"` appends the `## Owner decision` record to
the slice summary and sets `validation.human_acceptance` (and the slice status
for `accept`). It refuses unless the slice is waiting for the owner, runs the gate
on the result, restores both files if the gate reports an error, and never
commits. The gate requires that record for every decided acceptance and treats a
record beside `pending` as a contradiction. The gate checks records only; nothing
authenticates who ran the command. The doctor prints the exact command for each
slice that waits.

**v5 leaves main.** This repository is v6 only. The v5 profiles (`minimal`,
`solo`, `team`, `regulated`), scripts and `statedd_*` shims, schemas, fixtures,
catalog, commands, skills, state files, ledgers, and the legacy quality gate and
its CI job are removed from the tree. They stay at tag `v5-final`, the commit of
release 6.3.0 (`git worktree add ../projectstate-v5 v5-final`). The generator
refuses the four profile names with exit code 2 and that pointer. The old
automatic upgrader goes with them; the v5-to-v6 semantic migration stays in
`docs/UPGRADING.md`. This supersedes the part of ADR-0003 that kept the v5
profiles and assets on main as compatibility material for a migration window.

## Consequences

- The template is what it ships: one generator, one gate, the release, fleet,
  update, and decide tools, and their tests. CI runs only v6 checks and installs
  only pytest.
- A change to what a new project receives is now a visible act. Tests pin core
  and hardened output to digests recorded from 6.3.0 and require the legacy
  profile names to be refused. Changing the gate or the block is a release.
- Agents can no longer select a v5 profile by mistake, and nothing on main needs
  v5 maintenance. Anyone who needs v5 tooling works from the tag, and fixes there
  are not made on main.
- Costs: the lock is detection, so a project that edits its gate is found only
  when the doctor runs. Converting an old `AGENTS.md` depends on the recorded
  history of earlier generated text. Two identifiers must be kept in step by the
  release check. The template's own gate step in CI is red while its current slice
  is not validated, which is intended.

## Alternatives Considered

- One version string for everything: rejected because it conflates the state
  format with the template text and forces a state migration for a text-only change.
- Self-updating instances or scheduled cross-repository writes: rejected because
  the evaluator must not be its own updater and unattended changes to other
  repositories need explicit authority; pull keeps the owner in the loop.
- Marker-free contract text diffed by heading, as in 6.2.0: rejected because every
  update stayed a hand merge and edited template sections stayed invisible.
- Hashing the whole `AGENTS.md` or the whole repository: rejected because project
  text changes legitimately.
- Importing the gate from a shared package or the template at run time: rejected
  because product and instance must not depend on ProjectState code; vendoring a
  hash-locked copy keeps each instance self-contained.
- Preventing edits with file modes, hooks, or CODEOWNERS as the lock: rejected as
  the primary mechanism because the same agent can bypass them and they tie it to
  one host; a fleet-level hash check works everywhere. They can be added later.
- Keeping v5 on main: rejected because 470 of 546 files, two test suites, and a CI
  job served fourteen repositories of which one is active and does not use them.
- A `v5` branch: rejected because a branch invites fixes and cherry-picks and so
  becomes a second line of development; a tag freezes it.
- A separate v5 repository: rejected because the history is already here and a
  second repository is more to host and keep in step.
- Deleting v5 without a tag: rejected because the migration guide needs a stable
  pointer and the tag costs nothing.
- Accepting the v5 profile names with a warning, or mapping them to `core` or
  `hardened`: rejected because they encoded workflows that no longer exist, so a
  mapping would mislead; an exit 2 with the pointer is the honest answer.

## Related

- Owner decisions D1 to D6 (2026-10-06, "i choose all ur recs"): D4 is the legacy
  split, plan item S8.
- ADR-0003 (the outcome-first core): partly superseded as stated above.
- Evidence: `evidence/release-channel-001/summary.md`,
  `evidence/fleet-rollout-001/summary.md`, `evidence/acceptance-loop-001/summary.md`
