# ADR-0006: A journey receipt lives outside the repository that records the journey

**Status:** proposed (awaits the owner)
**Date:** 2026-11-11
**Author:** human-directed agent

## Context

The gate checks records. It reads `STATE.yaml` and the slice summary and reports
whether they agree with each other, and it never runs a journey. A journey status
typed as `passed` and one that a tool watched pass therefore look identical in the
owner's inbox.

`python3 scripts/projectstate_verify.py --run` does record an observed result, but
it edits `STATE.yaml` and the evidence summary. It is a tool of the repository's
writer. A reviewer, the owner, or a fleet check that used it would become a second
writer of the same two files, which is exactly what those files must not have.

Measured before building (2026-11-10, one workstation): nine slices were recorded
as validated and waiting for the owner. An independent read-only review classified
each journey command: six could be re-run locally and safely, one needed a build
toolchain, and two needed an external service. All six were re-run and passed: five
in a temporary clone of the committed HEAD and one, a directory without git, in a file
copy. Three of those repositories had uncommitted work, and their journeys also passed
in the working tree. So no recorded pass was
contradicted by a re-run. The same review found record problems that a re-run does
not see: a slice whose gate fails on uncommitted files, a cited file hash that no
longer matches, a proposal past its own expiry date, and work edited after the
recorded pass. Small numbers, one host.

## Decision

**Receipts live outside the repository.** An independent run writes
`<journeys>/<repository>/<slice>.json`, default
`~/.local/state/projectstate/journeys`, with the output tail beside it as
`<slice>.log`. The tool refuses a receipts folder inside the repository, and a
repository or slice name that cannot be a file name.

**What a receipt holds.** The format string, the repository's directory name and
path, the slice and its status, the journey as recorded, the command and its
sha256, the environment the record names, where the run happened, the HEAD it ran
against, how many paths were uncommitted, the start time, the duration, the exit
code, whether it timed out, the result, a sha256 of the output tail, who or what
ran it (`--by`), and the tool and its release.

**The default run is a clone of HEAD.** Uncommitted work is not part of it and the
working tree is not touched; a directory that is not the top of a git work tree is
copied instead, and the receipt says which of the two, or `--in-place` and the
working tree, was used. Nothing in the repository is edited by this mode, so the
run cannot move a journey's recorded status in either direction.

**The doctor labels each slice.** From the receipt and the repository it prints
`record only`, `run passed`, `run FAILED`, `receipt stale` (the recorded command
changed after the run, so the sha256 no longer matches), or `receipt invalid` (the
file does not name this repository, path and slice, is not JSON, or is not a
regular file). A recorded pass that a receipt contradicts, meaning the journey is
recorded as `passed` and the run failed, is listed under needs review as a
`journey-mismatch` with the command that runs it again.

**The gate and the contract do not change.** The gate keeps checking records, a
repository with no receipt is not worse off, and `record only` is a label, not a
fault. No release hash moves because of this ADR.

## Consequences and limits

- A receipt shows that a tool observed a run. It is not protection against
  someone forging the file; it only makes an observation possible without
  trusting the repository's own prose.
- Running a journey executes repository text, so `--run` stays an explicit choice
  by a person who has read the command. The default mode can run a command that
  was committed long ago and never reviewed.
- Many journeys cannot be re-run locally, because they need an external service or
  a person's judgment, and they stay `record only`.
- A clone does not contain untracked local state, so a journey that needs it has to
  use `--in-place`, and that run includes whatever else is in that working tree.
- Receipts are per machine. A fleet check on another host sees `record only` for
  the same slice, and nothing reconciles the two.
- Reading a receipt can say which commit was verified and how many commits came
  after it, which is information the record alone does not carry.

- The temporary copy keeps a journey's own writes out of the repository, but it is not a sandbox: a command
  that names the repository by absolute path, or follows a symlink that points into it, still reaches it.
- The doctor trusts the receipts directory for the content of a pass. It checks that a receipt belongs to the
  repository, the slice and the recorded command, and that its result agrees with its exit code; it cannot check
  that the run happened.

## Alternatives Considered

- **Requiring a receipt in the gate.** Not chosen: it would make the gate depend on
  state outside the repository, or execute the journey, and most manual journeys
  could never satisfy it, so honest slices would fail.
- **Keeping the observation only in the repository's own slice summary** (the
  existing `--run`, kept as it is). It works for the writer and cannot be used by a
  non-writer, which is the case this ADR is about.
- **Signing receipts.** No key holder exists that an agent on the same machine
  could not use, so a signature would suggest a guarantee the setup cannot make.
