# Evidence: release-channel-001

## Scope and authorization

Owner-approved CTO plan, 2026-10-06 (review: https://claude.ai/artifact/B33ZdP3MDpGeskmMcNJwNv).
Owner words: "i choose all ur recs" (D1-D6) and "implement each change yourself
... with cheaper sonnet subagents". This slice covers plan items S1-S4 plus the
gate part of S5 and ships as release 6.3.0. A coordinator writes this summary
and `STATE.yaml`; Sonnet workers return changes in their own worktrees.

## Primary journey

- Environment: Local Linux workstation; system Python 3 with PyYAML; real ~/Projects read-only; scratch copies outside ~/Projects
- Command: `python3 scripts/test_release_channel.py --fleet-root ~/Projects`
- Result: not_run
- Exit code: not_run

The journey script does not exist yet (step 4 below).

## Handoff (session stopped 2026-10-06 for quota)

Done and committed on `feat/release-channel-6.3`, which is not pushed:
- S0: branch work landed, D1 acceptance recorded in four slice summaries,
  main fast-forwarded to 6.2.0 (`6b98cc6`), tags v6.0.0-v6.2.0.
- D5: `opencode/` moved to its own local repo `~/Projects/example-project-15`.
  A backup is at `~/.local/state/projectstate/backups/opencode-kit-2026-10-06.tar.gz`.
- D6: `~/Projects/AGENTS.md` replaced by a 12-line note that adds no first action;
  the original is backed up in the same directory.
- Interface: `core/AGENTS.managed.md` (80 lines), `releases/index.json` (6.3.0
  draft), the gate's `RELEASE = "6.3.0"`, and `scripts/projectstate_release.py`
  (marker, hash and index helpers).
- W2 merged: generated AGENTS.md is the managed block plus `## Local rules` and
  `## Owner directives` (100 lines; fresh-core startup 6,410 characters, about
  1.6K tokens). Opt-in text moved to `prompts/`. The root AGENTS.md carries the
  same block.
- Verified with Claude Code 2.1.291: it loads `AGENTS.md` without a CLAUDE.md
  pointer, and it loads a parent folder's `AGENTS.md` from inside another repo.

Stopped mid-task, unreviewed. Each was snapshotted as one WIP commit on its own
branch; the worktrees are under `.claude/worktrees/`. The exact specs are in
`assignments/`.
- W1 gate owner-decision rules and release tool: `worktree-agent-aa755e8cadc8590b1`
  at `d33134e`. Gate edits and a gate test exist. The `check`/`cut` release
  subcommands and `test_release.py` are probably missing.
- W3 fleet doctor: `worktree-agent-ab848de5fe370c81c` at `b214911`
  (`projectstate_fleet.py`, `test_fleet.py`). It was mutation-testing and had not
  run against the real fleet.
- W4 update command: `worktree-agent-af5209d04c55e022a` at `580b92b`
  (`projectstate_update.py`, `test_update.py`, `releases/contract-history.json`).
  It was running tests; the real-copy runs were not reported.

Exact next steps:
1. For each WIP branch, diff against `189f31b`, run its tests, finish any gaps
   from its assignment, then merge it into `feat/release-channel-6.3`. Then run
   `python3 -m pytest scripts/ -q --deselect scripts/test_init_template.py::test_template_root_bootstrap_gate_passes`.
2. Update `docs/UPGRADING.md`: the 6.3.0 refresh is mechanical through
   `projectstate_update.py`; drop the "merge sections from a generated core" text.
   Also update README and CHANGELOG, and add `projectstate_release.py check` to CI.
3. Remove the worker worktrees: `git worktree remove`, then delete their branches.
4. Write `scripts/test_release_channel.py`. It must:
   - generate core, hardened and adopt projects and check block and gate hashes,
     `--version`, startup size of at most 10,000 characters, and an honest gate exit 1;
   - pin StatePort's adapter rule without executing its repo text: STATE.yaml
     `version` must equal `projectstate-template-v6`, PROJECT.md must exist,
     profile must be core or hardened, current_slice must be a mapping, and
     StatePort's `validationCommand` string must be unchanged;
   - run the fleet doctor with `--stdout` on ~/Projects, with a no-write
     audit of per-repo `git status`, `.git/index` mtime, and the hashes of
     STATE.yaml, AGENTS.md and the gate;
   - `git archive` example-project-08 and example-project-05 into scratch, run update dry-run,
     then `--apply`, then apply again (expect a no-op); check that local bytes are
     preserved and that the doctor reports both current.
5. Run the journey and record the results here. Then `projectstate_release.py cut
   --date <today>`, tag v6.3.0, and record the owner decision. The owner's
   "implement each change" can be recorded as `waived`, quoting it.
6. Remaining roadmap, as in the review:
   - S4 pilot: update branches `projectstate/release-6.3.0` in
     `~/Projects/_worktrees/` for example-project-08 and example-project-05 (D3 authorized).
   - S5 `projectstate_decide.py` (accept, reject or waive) with the doctor inbox.
   - S6 rollout: update branches for every active instance; fast-forward only
     where AGENTS.md and the gate are clean; skip dirty ones; add the update and
     fleet commands to `~/Projects/AGENTS.md`.
   - S7 resume eval: five seeded scenarios, with and without the core, run with
     `claude -p --model sonnet`.
   - S8 legacy split: tag `v5-final`. a local machine tool
     cites `projectstate_agent_worktree.py`.
   - S9 domain packs.
7. Log fleet-level changes in the owner's local machine log.

## Secondary checks

At `0b478c0`: `test_outcome_core.py` (29 tests), `test_long_run_control.py` and
`test_improvement_rounds.py` all pass. Full suite and legacy conformance were not
rerun after the W2 merge; the legacy conformance fails while this journey is
not_run, which is expected.

## Artifacts

- `assignments/W1-gate-and-release-tool.md`, `assignments/W3-fleet-doctor.md`,
  `assignments/W4-update-command.md`: the exact worker specs.

## Limitations

- Nothing is pushed or released; 6.3.0 is still a draft.
- The WIP worker code is unreviewed.
- No fleet repository has been modified apart from `~/Projects/AGENTS.md`.
