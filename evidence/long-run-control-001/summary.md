# Evidence: long-run-control-001

## Scope and authorization

The human requested adjusting the ProjectState template from the bounded
long-run implementation brief (2026-09-06) and queueing the refresh across
home Projects so the next coding-agent session performs the semantic update.
No downstream product repair, publish, deploy, or destructive cleanup is
authorized by this slice. Prior persistent-threads work remains staged on
`feat/optional-persistent-threads`; this slice adds to it without committing.

## Primary journey

- Environment: Local Linux workstation; Python 3.14.7; temporary generated projects and existing home Projects checkouts
- Command: `python3 scripts/test_outcome_core.py && python3 scripts/test_long_run_control.py`
- Result: passed
- Exit code: 0

Baseline before edits: `test_outcome_core.py` 20 tests passed; full
`pytest scripts/` passed; `projectstate_gate.py` recorded outcome validated;
`ruff check` passed. After edits: `test_outcome_core.py` 20 passed,
`test_long_run_control.py` 6 passed, full `pytest scripts/` passed with exit
0, `ruff check` passed, `git diff --check` passed.

Traced gap before editing: a fresh `new --profile core` target carries
closure/outcome-precedence rules but no continuation decision, no
critical-path vs blocked-lane rule, no verification ladder, and no bounded
execution/finalization guidance. `STATE.yaml` gate rejects unknown top-level
keys, so a run envelope cannot be a new top-level field without a parser
change — the envelope therefore lives in existing state/assignment fields
plus the optional prompt.

## Secondary checks

- `python3 -m pytest scripts/ -q`: passed, exit 0.
- `python3 scripts/projectstate_gate.py`: recorded outcome validated, exit 0
  (after STATE.yaml moved to this slice and evidence).
- `ruff check scripts/init_template.py scripts/test_outcome_core.py scripts/test_long_run_control.py`: passed.
- `git diff --check`: passed.
- Generated core file set unchanged (six files); optional
  `prompts/LONG_RUN_CONTROL.md` is template-only and not injected by default.
- Gate still rejects `run_budget` top-level key with unsupported-fields exit 2.

## Artifacts

- `scripts/init_template.py`: compact `Continuation decision` section plus
  clarified same-boundary/two-failure rule in the generated contract.
- `prompts/LONG_RUN_CONTROL.md`: optional selected-run record, worker/model,
  finalization, and evidence guidance.
- `scripts/test_long_run_control.py`: 6 behavioral fixture tests.
- `docs/UPGRADING.md`: bounded long-run control refresh section.
- Snapshot bundle: `~/Projects/.projectstate-handoffs/long-run-control-2026-09-06`
  with `core/`, `docs/UPGRADING.md`, `prompts/LONG_RUN_CONTROL.md`,
  `README.md`, `SHA256SUMS`.
- Queue: inherited directive in `~/Projects/AGENTS.md`, project-local
  notices in each downstream `AGENTS.md`, and fabric packages under
  `~/.local/state/project-fabric/queue/<Project>/long-run-control-2026-09-06/`.

## Limitations

- Advisory control only: the template rule can be ignored by an agent; hard
  admission control is not claimed until a real runner refuses inadmissible
  actions. The validator never executes repo text.
- No live billing integration; unobservable model usage is labeled unknown
  with fallback limits. No quota-savings claim; same-model comparison is left
  to future runs.
- Numeric long-run defaults are experimental policy choices, not proven optima.
- Human acceptance and remote delivery remain pending. Downstream semantic
  refresh is queued, not performed here.

## Follow-up — agent session memories advisory (2026-09-12)

Owner-authorized follow-up to this staged integration: the read-order paragraph
in the generated core now lists agent session memories among the optional
references that are never sources of current truth. Changed files:
`scripts/init_template.py` and this repository's `AGENTS.md`. The primary
journey was rerun after the edit: `test_outcome_core.py` 20 passed,
`test_long_run_control.py` 6 passed, full `pytest scripts/` passed, `ruff
check` passed, `git diff --check` passed, gate `RECORDED OUTCOME VALIDATED`.
A freshly generated core project confirms the line is present. Downstream
projects receive it on their next semantic refresh; the queued 2026-09-05/06
snapshots are intentionally unchanged.
