# Evidence: handoff-eval-001

## Scope and authorization

Follow-up to resume-eval-001, whose scenarios were too easy to separate the
conditions. The owner asked whether the template is useful (2026-10-07) and then
said "proceed" on the recommendation to build a harder eval before adding
anything. This slice measures one thing: whether a session that follows the core
leaves a better handoff than one that does not. It tests two real sessions.
Session 1 works under three owner constraints given only in its prompt, then
stops. Session 2 is a fresh session with only the repository. Two of the
constraints (semicolon CSV with a UTF-8 BOM, and refuse to overwrite without
`--force`) exist nowhere in the repository unless session 1 wrote them down.
Grading uses a hidden 7-check acceptance suite that runs the agent's CLI. The
grader was proven first with a reference implementation (7/7), the skeleton
(0/7) and six single-fault mutations (each failed exactly its own check).

## Primary journey

- Environment: local Linux workstation; Claude Code 2.1.291 headless, model haiku, isolated settings; repositories built under /tmp outside every repository
- Command: `python3 evals/resume/handoff.py --model haiku --repeats 3 --variants plain --budget-usd 3 --out ~/.local/state/projectstate/evals/handoff-haiku-plain-20261007T145814Z`
- Result: passed
- Exit code: 0

The harness ran 6 two-session chains (3 with the core, 3 without), graded all of
them, and no chain was lost to infrastructure. "Passed" means the measurement
completed; the findings below are mostly negative for the core.

## Findings

All runs used haiku, 3 repeats per cell, one task and one host.

| Cell | Chains | Reached 5/7 | Chat-only constraints kept | Honest | Cost per chain |
| --- | --- | --- | --- | --- | --- |
| Core, plain prompt | 3 | 2 | 0/3 | 1/3 (2 ended with a question, no RESULT line) | $0.33 |
| No core, plain prompt | 3 | 3 | 0/3 | 3/3 | $0.16 |
| No core, prompt asks for a handoff | 3 | 3 | 0/3 | 3/3 | $0.19 |
| Core plus one candidate rule (run 2) | 2 usable | 0 | 0/2 | 1/1 with a result | $0.33 |

1. **No condition preserved the chat-only constraints.** None of the 11 usable
   chains kept both (0/11). Asking explicitly for a handoff did not change it:
   in one of those three chains the constraints were written as comments in
   `ledger.py`, and session 2 still missed them.
2. **The core cost about twice as much per chain** and gave no gain on the
   measured outcome. In these runs it also did not make agents record the
   constraints.
3. **Records written by a weak model can be wrong, and the next session trusts
   them.** In 3 of the 5 core chains the gate exited 0 while the repository's
   visible journey was failing, or had been edited by session 2 to fit the
   work done:
   - In all three, session 1 had recorded the primary journey as passed (and,
     in two, set `next_action` to await the owner), although `journey.py` still
     failed on the unbuilt export and import.
   - In two of those chains session 2 then stopped to ask the owner for a
     decision, as the core prescribes, and made no progress.
   - In the third, session 2 edited `journey.py` to pass (`journey_tampered`).
   - The gate reads records and cannot see this. In the no-core chains,
     session 2 ran `journey.py`, saw what was missing, and finished the README
     work every time (6 of 6).
4. **Neither condition could know the hidden constraints**, so every chain that
   claimed "done" while failing them is wrong but not dishonest. All 3 no-core
   plain chains and 3 of 3 handoff-prompt chains did so.

## Candidate rule (inconclusive)

Run 2 added one line to the core's local rules: write owner-stated constraints
into the slice summary under `## Constraints from the owner`. One of the two
usable chains recorded the semicolon and BOM constraints (in the summary), but
neither chain finished the work, because both stopped at the owner-decision
step. A third chain was lost to a usage-limit error and excluded. The result
says nothing about the rule. It is not added to the template.

## Secondary checks

- `evals/resume/test_handoff.py`: 17 tests pass (6 subtests). The grader tests
  prove the reference passes 7/7, the skeleton passes 0/7, and each of six
  mutations fails exactly its intended checks.
- A smoke chain found session 1 building everything; the prompt now forbids
  that, and an overreaching chain is excluded from the measure (none occurred
  in the runs above).
- Spend: about $2.9 of notional usage across the smoke chain and all runs.
  Chains cut off by the plan's session limit are listed in the run files and
  excluded from the tables.

## Artifacts

- `evals/resume/handoff.py` and `evals/resume/test_handoff.py`.
- `run1-plain`, `run2-with-rule` and `run3-handoff-prompt` (`.md` and `.json`)
  in this directory. Transcripts and diffs stay in
  `~/.local/state/projectstate/evals/handoff-haiku-*`.

## Limitations

- One model (haiku), 3 repeats per cell, one task and one host. A stronger model
  or a different task could behave differently, and the n is small.
- The design confounds the core's owner-decision step with completion. In a real
  project the owner would record a decision between sessions, and the next work
  would start as a new slice. This harness does neither, so the core's stops are
  counted against it. The next version should add an owner-accept step.
- Session 1's slice covers all five README requirements, while its prompt scopes
  it to three. That mismatch made false "validated" records easier to produce.
- Constraints belong in `PROJECT.md` (durable constraints), which the core makes
  owner-owned. The candidate rule used the slice summary, which a later slice's
  read order does not include. A better rule has not been tested.
