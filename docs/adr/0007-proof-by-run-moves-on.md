# ADR-0007: A slice proven by a run moves on; one proven by word waits for the owner

**Status:** accepted (2026-11-11; the owner approved the proposal with "proceed optimally", and the coordinating agent wrote this record)
**Date:** 2026-11-11
**Author:** human-directed agent

## Context

Three observations from 2026-11-10 and 2026-11-11, on the owner's own fleet and
on the template's evals (`evidence/handoff-eval-001/summary.md`).

- **Most validated slices rested on a typed word.** Of 23 slices in the fleet, 6
  had a journey that a tool had re-run and 17 had only their own record. The gate
  could not tell them apart, and neither could the owner's inbox.
- **The owner checkpoint was not being used as designed.** The contract said a
  validated slice waits until the owner accepts, rejects or waives it. Ten slices
  were waiting. The owner cleared all ten by handing the choice to an agent in
  one sentence. In the first handoff eval the same rule stopped every core chain
  at the decision step when no owner answered.
- **The contract's cost is bookkeeping.** On sonnet the core cost 2.4 times a
  plain repository for the same result, and 94 to 99% of that overhead was
  hand-editing `STATE.yaml` and the slice summary, repeated gate runs and the
  read order.

ADR-0005 left a lean contract as an eval candidate, and ADR-0006 added receipts
for a run by someone who is not the repository's writer. Neither changed what an
agent inside a project is told to do.

## Decision

**The journey tool is part of the core.** `scripts/projectstate_verify.py` is
vendored beside the gate. The release index records its hash (`verify_sha256`,
required from 6.5.0), the update command installs and replaces it like the gate,
the fleet doctor compares it, and `init_template.py` copies it into a new
project. The managed contract tells agents to record the journey with
`projectstate_verify.py --run` and never to type a journey status, result or
exit code, except for a journey that cannot be a command.

**The tool writes what its run shows.** A passed journey sets a `planned`,
`implementing` or `implemented` slice to `validated`, because that is what the
word means; when the gate still lists a blocker, the status stays and the tool
says why. It then prints the gate's verdict. The lean candidate's first wording
left this status to the agent, and 5 of 6 chains forgot it.

**The gate says how the journey was recorded.** Its verdict names a record made
by a run, with the time, or says that it was typed by hand. It gains no new
error and no new blocker: on the 23 repositories of the owner's fleet its exit
code is the same as that of each repository's own gate.

**Proof by run moves on. Proof by word waits.** While the owner has not decided:

- a slice whose journey a run recorded as passed may be followed by the next
  slice. Its decision stays open. The fleet doctor lists it under "Open
  decisions that block nothing" until a decision is recorded, and
  `projectstate_decide.py --slice ID` records one on a slice that is no longer
  current, writing only that slice's summary;
- a slice whose journey was typed by hand waits, as before, and replacing it
  without the owner's decision is still reported for review.

**A delegated choice is recorded as one.** When the owner hands the choice to an
agent, the record quotes the delegating words and adds `- Decided by: delegate`
(`projectstate_decide.py --delegated`). A delegate accepts only what a run
recorded as passed; anything else it waives, rejects or leaves to the owner.

**The read order follows the briefing.** With a host briefing in context, an
agent reads `PROJECT.md` and `STATE.yaml` only for detail or before changing
them. Without one, the read order is as before.

**Not changed.** The `STATE.yaml` schema and its version string (StatePort's
importer matches the string literally). The gate stays read-only, offline and
standard-library only, and it still never runs anything.

## Consequences

- An instance vendors a second file, and the update command writes three things
  instead of two. A contract block that names the tool while the file is missing
  is reported by the fleet doctor.
- `validated` no longer depends on an agent remembering to type it, and a slice
  cannot be marked validated by the tool while a blocker is open.
- The run line in a summary is a record like any other. A typed line in the
  tool's format reads as a run. The check by someone else remains the receipt of
  ADR-0006, which lives outside the repository.
- For a slice proven by a run, nothing forces the owner to look at it. Whether
  the journey was the right one to run is then checked only when the owner reads
  the open decisions. The list can grow without limit.
- A journey that cannot be a command (a person's eyes, a system this machine
  cannot reach) is where the owner's attention is still required. That is the
  intended split.
- This is a semantic release: an agent in every updated instance records
  journeys differently and may start the next slice earlier than before.
- The ten delegated decisions recorded on 2026-11-11 predate the
  `- Decided by:` line. They carry a `- Note:` instead and are not rewritten.
- Measured before the release on the durability eval; the result is in
  `evidence/proof-by-run-001/summary.md`.

## Alternatives Considered

- **A gate error for a journey typed by hand.** It would turn the gate red in
  every instance whose current slice was recorded the old way, at the moment of
  the update, and force a re-run or a written excuse for work already decided.
- **A standing delegation in `PROJECT.md`.** The owner would have to opt in per
  project, and an agent would then record acceptances the owner never saw.
  Leaving the decision open says less and is true.
- **A field in `STATE.yaml` for the kind of proof.** A schema change for every
  instance, for older vendored gates and for StatePort's importer, to hold a fact
  the slice summary already records.
- **Keeping the decide command to the current slice.** An open decision on an
  earlier slice could then be listed forever and never closed.
- **Receipts as the only proof by run.** They need the template checkout and a
  second actor. The agent doing the work would still type its own result.
