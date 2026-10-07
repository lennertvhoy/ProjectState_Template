# Evidence: legacy-split-001

## Scope and authorization

Plan item S8 under owner decision D4: main becomes v6 only, and the v5
compatibility profiles, scripts, schemas, fixtures, commands, skills and
historical evidence stay available at tag `v5-final` (0f34205). Implemented by
Sonnet worker W10; integrated and verified by the coordinator. The doctor shows
14 v5-only repositories. The one active among them (example-project-04)
vendors its own scripts and does not run this template's v5 tooling.

## Primary journey

- Environment: local Linux workstation; fresh local clone of feat/release-channel-6.3 in the session scratchpad; system Python 3
- Command: `git clone -q --branch feat/release-channel-6.3 ~/Projects/ProjectState_Template <scratchpad>/fresh-clone && cd <scratchpad>/fresh-clone && python3 scripts/test_outcome_core.py && python3 -m pytest scripts/ evals/ -q`
- Result: passed
- Exit code: 0

In the fresh clone, the core journey exited 0 and pytest exited 0
(379 passed, 713 subtests).

## Secondary checks

- Size: tracked files went from 546 to 86. Python went from 47,020 to about
  12,300 lines. `scripts/init_template.py` went from 2,254 to 643 lines.
- Generator equivalence: W10 compared 80 scenarios against a pristine extract
  of 0f34205 (new and adopt, core and hardened, dry runs, conflicts, forced
  overwrite, symlinks, hard links, template-root and nested targets, the
  no-subcommand form). Exit codes, output and every resulting file's bytes and
  mode matched. Two intended differences: the "Mode: bootstrap" and "Optional
  asset sets" lines are gone, and a symlinked destination now gets a one-line
  refusal instead of a traceback (exit 1 in both). sha256 digests from the old
  generator are pinned in `test_outcome_core.py`, and 26 temporary mutations
  were all caught.
- Legacy profile names (minimal, solo, team, regulated) now exit 2 and point to
  `git worktree add ../projectstate-v5 v5-final`.
- Both journeys pass after the split:
  - `test_release_channel.py` passes 77 checks. Updated instances are exported
    at their pre-update revision.
  - `test_acceptance_loop.py` passes.
- `projectstate_release.py check` passes, and tag v6.3.0's gate and contract
  hashes match.
- CI is v6 only: the core journey, release check, pytest, gate, and a clean
  checkout. It installs pytest only.
- `docs/adr/0004-release-channel-and-legacy-split.md` records the decisions.
- A local architecture-map tool lost a dead evidence path to the
  removed v5 orchestrator. Its tests pass (53), and the change is logged in
  the owner's local machine log.

## Artifacts

- Merge of W10's seven commits (deletions, generator rewrite, tests, CI, docs,
  ADR, tidy).
- Tag `v5-final` for the removed material.

## Limitations

- README and GETTING_STARTED examples now use absolute target paths, because
  the generator refuses `--target ../x`. That safety rule predates this change.
- `pyproject.toml` `testpaths` and the ruff excludes were adjusted for deleted
  directories.

## Owner decision

- Decision: waived
- Date: 2026-10-07
- Owner words: "youve got enough usage to implement each change yourself, do that but do it with cheaper sonnet subagents"
- Context: Roadmap item S8 under owner decision D4. Final acceptance of the roadmap is requested at the end.
