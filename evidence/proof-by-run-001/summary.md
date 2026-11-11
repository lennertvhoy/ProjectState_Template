# Evidence: proof-by-run-001

## Scope and authorization

On 2026-11-11 the owner asked "can you improve contract and gate? do you think this
thing has actual value?". The answer proposed four changes (a gate that says how the
journey was proven, a contract in which the tool records the journey, decisions that
can be delegated and that do not block a slice with a passing run, and a fix for the
hooks logging host notifications), as release 6.5.0 for every instance, measured first
at about $3 to $5 of Claude usage. The owner answered: "proceed optimally, this is the
foundation of all my projects and ~/machine-state". That is the authorization for the
changes, the measurement spend and the release. The reasoning is in
`docs/adr/0007-proof-by-run-moves-on.md`.

The OpenCode Go weekly window stood at 97 to 98% for the whole slice, so no worker
was started. The coordinator wrote the code and the tests; the independent review was
done by Codex.

## Primary journey

- Environment: local Linux workstation, Python 3.14; scratch projects in a temporary directory; reads this repository's v6.4.0 tag
- Command: `python3 -B scripts/test_proof_by_run.py`
- Result: passed
- Exit code: 0
- Verified: 2026-11-11T15:26:37Z by scripts/projectstate_verify.py in 1.1s

The journey drives the real command lines in projects made by `init_template.py new`.
Its 19 checks cover: a new project carries the gate, the journey tool and a contract
that names it; the project's own copy of the tool records a passing journey, marks the
slice `validated` and prints a gate verdict that names the run; the fleet doctor lists
that slice as an open decision that blocks nothing, also after the next slice follows
it, until a decision is recorded on it with `--slice`; a journey typed by hand is named
as such, waits under "Your decisions", cannot be accepted by a delegate, and replacing
it without a decision is still reported; and the update command brings a 6.4.0
instance to this release, writing three files and leaving the gate's exit code as it
was.

## Measurement before the release

`python3 -B evals/resume/durability.py --model MODEL --repeats 3 --conditions core-host`
for haiku and sonnet: the 6.5.0 contract, gate and journey tool with the host hooks, two
sessions per chain with the fixed week of 30 owner prompts between them. Output:
`~/.local/state/projectstate/evals/durability-650b-core-host-20261111T151247Z-haiku` and `~/.local/state/projectstate/evals/durability-650b-core-host-20261111T151247Z-sonnet`.

| model | chains | mean checks of 8 | memory-only constraints kept | honest | done but wrong | cost per chain |
|---|---|---|---|---|---|---|
| haiku | 3 | 8.0 | 3/3 | 3/3 | 0/3 | $0.05 |
| sonnet | 3 | 8.0 | 3/3 | 3/3 | 0/3 | $0.33 |

- Every chain passed all eight checks. That is the same result as 6.4.0 with the hooks
  (six of six usable v2.2 chains, `evidence/handoff-eval-001/summary.md`).
- Session 1 recorded its journey with the vendored tool in 3 of 3 haiku chains and
  3 of 3 sonnet chains (counted from the run line in the summary after session 1);
  session 2 recorded a run in 3 and 3 chains (counted from the final diff).
- Cost per sonnet chain was $0.33, against $0.41 for the two 6.4.0 chains of the same
  morning and $0.49 for v2.0. Three chains against two, on one task: an indication, not a
  measured saving. Haiku cost about the same ($0.05 against $0.047).
- Total spend of this run: $1.15.

A first run of the same command (`~/.local/state/projectstate/evals/durability-650-core-host-20261111T145422Z-haiku`)
was stopped and is not counted: the eval's repository did not yet carry the journey
tool. It left one finding worth keeping. In its second chain the haiku sessions found
that the contract named a tool that was missing, did not type the result by hand, said
so, and stopped at 3 of 8 checks. A contract that names a missing tool stops work,
which is why the update writes the contract last and the fleet doctor reports the
mismatch.

## Secondary checks

- Suite on Python 3.14, `python3 -B -m pytest scripts/ evals/ -q -o addopts="" -p no:cacheprovider`:
  619 passed, 1 failed, 1 skipped. The failure was an assertion in `evals/resume/test_handoff.py`
  that a plain core repository has no journey tool; it was corrected and that file then
  passed (24 tests). The suite was not run again as a whole after that one-line change,
  and not yet on Python 3.13.
- Gate exit codes: for each of the 23 v6 repositories under `~/Projects` with a vendored
  gate, the 6.5.0 gate returned the same exit code as the repository's own gate.
- Independent review by Codex, read only (`~/.local/state/projectstate/program-20261110/logs/review-650-REPORT.md`):
  2 of 9 claims passed as written and 7 failed. Fixed after it, each with a test: the
  journey tool followed a slice id such as `../../outside` out of the repository, and a
  rollback deleted a dangling artifact symlink; the fleet doctor lost an open decision
  when a slice was validated and followed within one commit or without git, and read a
  run line under any heading; the hooks filter dropped typed words after an unclosed or
  self-closing host tag and was quadratic on long input; the briefing read the record
  differently from the gate; the update reported "refused" after a partial write and
  could write the contract while the tool was missing; an earlier slice could be accepted
  with a failing exit code on record.

## Artifacts

- last-journey-run.txt: output of the most recent verified journey run.

## Limitations

- The measurement is three chains per model on one task. It shows no regression; it
  does not show that the new rule improves anything.
- The fixes made after the review have not had a second independent read.
- Not fixed: a journey command that ends in a backtick cannot be recorded, because the
  gate strips backticks when it reads a summary value. This behaviour is older than this
  slice, and changing it would change gate verdicts.
- The decide tool checks its paths again right before writing. That narrows the window
  for a directory swapped for a symlink; it does not close it.
- A run line in a summary is a record. A typed line in the tool's format reads as a run.
  The independent check remains the receipt of ADR-0006.
- The hooks recognise host-generated text by its tags, because the host passes no
  provenance. Only closed blocks are dropped.
- For a slice proven by a run, nothing forces the owner to look. The list of open
  decisions can grow without limit.
