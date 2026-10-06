# Evidence: improvement-rounds-001

## Scope and authorization

The owner asked to integrate a recursive-self-improvement (RRSI) research
recommendation into the template, then added "use best judgement and intense
research in recursive home folder sweep and online and papers". Selected change:
an optional, opt-in, event-triggered, proposal-only measured-improvement
workflow. Not selected, and not done: any generated-profile change, any
downstream queue or refresh, any scheduler, any lessons-feed generator, and any
edit to the untracked `opencode/` tree (another lane's work). Prior staged slices
(`persistent-threads-001`, `long-run-control-001`) remain staged as found; this
slice's edits are unstaged on top, and nothing was committed, pushed, or staged.

## Primary journey

- Environment: Local Linux workstation; Python 3.13.15; temporary generated core projects
- Command: `python3 scripts/test_outcome_core.py && python3 scripts/test_long_run_control.py && python3 scripts/test_improvement_rounds.py`
- Result: passed
- Exit code: 0

Baseline before edits: `test_outcome_core.py` 21 passed, `test_long_run_control.py`
6 passed, gate validated. After: 21 + 6 + 17 passed. The new tests generate a real
core project, copy the optional asset in, and run enable, start-check, round
record, proposal, stop, sticky trip, re-arm, and adversarial cases (protected
paths, instruction-file growth, forged measure output, malformed or hostile
patches, unsupported fields, symlinks, dirty worktree, token cap).

## Secondary checks

- `python3 -m pytest scripts/ -q`: passed. One existing compatibility test
  (`test_rename_backward_compat.py`) failed first because it demands a legacy
  `statedd_*` shim for every `projectstate_*.py`; the v6 gate was already
  exempt, so the same exemption now covers this new v6-only script.
- Mutation check: seven deliberate breaks of the checker (stop-rule off by one,
  non-sticky trip, protection removed, instruction growth allowed, measure
  cross-check removed, token cap ignored, symlink patches allowed) each made the
  new tests fail; the original was restored and verified byte-identical.
- `ruff check` on the new and touched scripts: passed. `git diff --check`: passed.
- `python3 scripts/projectstate_gate.py`: recorded outcome validated.

## Artifacts

- `prompts/IMPROVEMENT_ROUNDS.md`: when it earns its cost, opt-in steps, what
  the check can and cannot enforce, stop rule, pull-based lessons, evidence base.
- `prompts/IMPROVE_MD_TEMPLATE.md`: human-owned config plus the seven-step round;
  ships `enabled: false`.
- `scripts/projectstate_improve_check.py`: read-only, standard-library checker.
- `scripts/test_improvement_rounds.py`: 17 behavioral tests.
- `README.md`, `docs/UPGRADING.md`: short opt-in notes; no refresh queued.
- `research.md` (this folder): home-folder sweep, source verification, and
  corrections to the pasted write-up.

## Limitations

- No evidence that rounds improve any instance. Only a measure-only baseline on
  a real instance, then measured rounds, can show that; none was run.
- The check is advisory like the gate: an agent can ignore it, and it cannot
  prove the measure was honestly run, that unlisted evaluator dependencies are
  protected, or that a human approved a proposal.
- Several cited results were seen only as search summaries (marked in the guide).
- Human acceptance and remote delivery remain pending.
- Follow-ups for the owner, not done here: model-name refresh in untracked
  `opencode/` (see `research.md`), a machine-level read-only lessons feed, and
  choice of the pilot instances.

## Owner decision

- Decision: accepted
- Date: 2026-10-06
- Owner words: "i choose all ur recs"
- Context: Reply to the CTO review recommendations D1–D6 (https://claude.ai/artifact/B33ZdP3MDpGeskmMcNJwNv).
- Scope: D1: accepted as experimental: kept in the template, never generated, never rolled out.
