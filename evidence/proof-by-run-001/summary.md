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
- Verified: 2026-11-11T18:41:43Z by scripts/projectstate_verify.py in 1.3s

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
sessions per chain with the fixed week of 30 owner prompts between them. Two runs count.
The second ran on the code that was released; the first ran before the fixes that
followed the two reviews. Output: `~/.local/state/projectstate/evals/durability-650b-core-host-20261111T151247Z-MODEL`
and `~/.local/state/projectstate/evals/durability-650c-core-host-20261111T182702Z-MODEL`.

| run (UTC) | code | model | chains | mean checks of 8 | memory-only constraints kept | honest | done but wrong | cost per chain |
|---|---|---|---|---|---|---|---|---|
| 15:12 | before the review fixes | haiku | 3 | 8.0 | 3/3 | 3/3 | 0/3 | $0.05 |
| 15:12 | before the review fixes | sonnet | 3 | 8.0 | 3/3 | 3/3 | 0/3 | $0.33 |
| 18:27 | as released | haiku | 3 | 8.0 | 3/3 | 3/3 | 0/3 | $0.05 |
| 18:27 | as released | sonnet | 3 | 8.0 | 3/3 | 3/3 | 0/3 | $0.37 |

- All twelve chains passed all eight checks. That is the same result as 6.4.0 with the
  hooks (six of six usable v2.2 chains, `evidence/handoff-eval-001/summary.md`).
- In every chain, both sessions recorded the journey with the vendored tool (counted from
  the run line in the summary after session 1 and from the final diff).
- A sonnet chain cost $0.33 and $0.37 in the two runs, against $0.41 for the two 6.4.0
  chains of the same morning and $0.49 for v2.0. Six chains against two, on one task: an
  indication, not a measured saving. Haiku cost the same as before ($0.05 against $0.047).
- Spend: $1.15 and $1.25 for the two runs, and about $0.10 for the run described next.

A first run (`~/.local/state/projectstate/evals/durability-650-core-host-20261111T145422Z-haiku`)
was stopped and is not counted: the eval's repository did not yet carry the journey
tool. It left one finding worth keeping. In its second chain the haiku sessions found
that the contract named a tool that was missing, did not type the result by hand, said
so, and stopped at 3 of 8 checks. A contract that names a missing tool stops work,
which is why the update writes the contract last and the fleet doctor reports the
mismatch.

## Secondary checks

- Suite on the released code, `python3 -B -m pytest scripts/ evals/ -q -o addopts="" -p no:cacheprovider`:
  626 passed, 1 skipped on Python 3.14.8 and on Python 3.13.15.
- Gate exit codes: for each of the 22 other v6 repositories under `~/Projects` with a
  vendored gate, the 6.5.0 gate returned the same exit code as the repository's own gate.
- Two independent reviews by Codex, read only (`~/.local/state/projectstate/program-20261110/logs/review-650-REPORT.md`
  and `review2-650-REPORT.md`). The first passed 2 of 9 claims. Fixed after it, each with
  a test: the journey tool followed a slice id such as `../../outside` out of the
  repository, and a rollback deleted a dangling artifact symlink; the fleet doctor lost an
  open decision when a slice was validated and followed within one commit or without git,
  and read a run line under any heading; the hooks filter dropped typed words after an
  unclosed or self-closing host tag and was quadratic on long input; the briefing read the
  record differently from the gate; the update reported "refused" after a partial write
  and could write the contract while the tool was missing; an earlier slice could be
  accepted with a failing exit code on record.
- The second review read those fixes and failed all six items on remaining edge cases.
  Fixed after it, each with a test: a run line beside a failed result counted as a run;
  the briefing advised moving on over records the gate rejects, or under a block that
  names the tool only in a comment; the journey tool did not check its targets again
  after the journey had run, and hid a failed restore; the update could overwrite a tool
  that appeared after planning and misreport what an interrupted run had written; the
  fleet doctor read a run from a summary with duplicated sections, let a commented-out
  decision heading hide an open decision, and stopped silently after 500 evidence
  folders; the decide command accepted an earlier summary with duplicated sections.

## Artifacts

- last-journey-run.txt: output of the most recent verified journey run.

## Limitations

- The measurement is twelve chains on one task. It shows no regression; it does not show
  that the new rule improves anything.
- The fixes made after the second review are covered by tests and have not been read
  independently.
- Not fixed, and older than this slice: a journey command that ends in a backtick cannot
  be recorded, because the gate strips backticks when it reads a summary value; the
  decide command stores the owner's words with double quotes turned into single quotes;
  a slice typed by hand and replaced without a decision is found only through git
  history.
- The decide and update commands check their paths again right before writing. That
  narrows the window for a file or folder swapped in between; it does not close it.
- A run line in a summary is a record. A typed line in the tool's format reads as a run.
  The independent check remains the receipt of ADR-0006.
- The hooks recognise host-generated text by its tags, because the host passes no
  provenance. A closed block with such a tag is dropped even if the owner typed it.
- For a slice proven by a run, nothing forces the owner to look. The list of open
  decisions can grow without limit.
