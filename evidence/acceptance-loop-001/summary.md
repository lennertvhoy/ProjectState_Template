# Evidence: acceptance-loop-001

## Scope and authorization

Plan item S5: make the owner's decision a single command. Before this, no v6
instance had ever recorded an acceptance. Owner-approved CTO plan (owner words
"i choose all ur recs", 2026-10-06). The decide command was written by Sonnet
worker W6 (merged in `b5f0658`); the coordinator wrote this
journey and the doctor's rule-adoption fix.

## Primary journey

- Environment: local Linux workstation; real ~/Projects read-only; scratch copies via git archive outside ~/Projects
- Command: `python3 scripts/test_acceptance_loop.py --fleet-root ~/Projects`
- Result: passed
- Exit code: 0

The doctor's real inbox listed 8 decisions. Three committed instances that wait
for a decision were copied with `git archive`. In each copy the exact command
from the inbox recorded one decision: example-project-05 accept, example-project-26
waive, example-project-14 reject. example-project-13 was skipped because its STATE.yaml was
never committed. For each copy:
- the gate accepted the recorded decision with no errors;
- the summary quoted it under `## Owner decision`;
- a second decision was refused.

The doctor then stopped listing all three. The real instances were only read.

## Secondary checks

- `scripts/test_decide.py`: 70 tests passed (164 subtests). They cover the
  refusals, quoting, dry run, rollback on gate errors, and dirty-tree refusal.
- Doctor fix: slice replacements made before a repository adopted the managed
  block (and with it the owner-decision rule) count as history, not review. The
  real inbox went from 20 review items to 2 (StatePort and example-project-37 have
  edited gates). The 18 earlier replacements remain in the data and in
  `summary.silent_replacements_before_rule`. Regression test added;
  `test_fleet.py` passes 37 tests.

## Artifacts

- `scripts/projectstate_decide.py` with `scripts/test_decide.py`.
- `scripts/test_acceptance_loop.py` (this journey).
- `scripts/projectstate_fleet.py`, which adds `rule_since` per repository.

## Limitations

- The plan's human half is open. The owner has not yet cleared the real queue
  of 8 decisions; the doctor's inbox prints the exact command for each.
- The gate cannot authenticate who ran the command. The record quotes the
  owner's words and is reviewable in Git.

## Owner decision

- Decision: waived
- Date: 2026-10-07
- Owner words: "youve got enough usage to implement each change yourself, do that but do it with cheaper sonnet subagents"
- Context: Roadmap item S5. Final acceptance is requested at the end of the roadmap.
