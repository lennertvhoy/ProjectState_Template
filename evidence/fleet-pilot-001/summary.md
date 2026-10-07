# Evidence: fleet-pilot-001

## Scope and authorization

Plan item S4: prove the 6.3.0 mechanical update in two live instances before
any wider rollout. The owner authorized writes in example-project-08 and example-project-05
(decision D3, owner words "i choose all ur recs", 2026-10-06). Each update was
made on a private branch in a separate worktree under `~/Projects/_worktrees/`,
committed there, and then fast-forwarded into the project's checked-out branch.
Only AGENTS.md and `scripts/projectstate_gate.py` changed; in both repositories
those two files were clean beforehand. Nothing was pushed.

## Primary journey

- Environment: local Linux workstation; live checkouts ~/Projects/example-project-08 (main) and ~/Projects/example-project-05 (feat/github-drive-career-evidence-20260910)
- Command: `python3 scripts/projectstate_update.py --target ~/Projects/example-project-08 --check && python3 scripts/projectstate_update.py --target ~/Projects/example-project-05 --check`
- Result: passed
- Exit code: 0

`--check` exits 0 only when the gate and the managed block already match the
current release, and it writes nothing. The fleet doctor then reported both
repositories as gate current 6.3.0 and contract current 6.3.0.

## Secondary checks

| Repository | Dry run | Gate verdict before and after | Commit |
| --- | --- | --- | --- |
| example-project-08 | gate 6.2.0 to 6.3.0; 9 known template sections converted; 0 modified; local bytes preserved | not validated, then not validated (slice `camera-001` is planned) | main `03ca505` |
| example-project-05 | the same plan | validated, then validated | `b5d464c` on its feature branch |

- Each project's own gate reports `projectstate-gate 6.3.0`.
- example-project-05's five project sections follow the managed block unchanged.
- Startup reading at chars/4: example-project-08 about 2.4K tokens (it was 5.2K
  including the old parent directive); example-project-05 about 5.5K (it was 8.3K).
- The doctor's totals moved from 18 behind to 16 behind and 2 current.
- The temporary worktrees and the `projectstate/release-6.3.0` branches were
  removed after the fast-forward.

## Artifacts

- Dry-run plans:
  `/tmp/claude-1000/-home-ff-Projects-ProjectState-Template/51f4f4f2-a372-4736-818f-8e07f9525100/scratchpad/pilot-*-dry.json`
  (session scratch, not kept).
- The update commits named above in each repository.

## Limitations

- example-project-05's other uncommitted work (about 67 files) was left untouched.
  Its owning session should know that AGENTS.md changed underneath it.
- The pilots prove conversion of the standard layout only. StatePort's edited
  gate and nonstandard AGENTS.md layouts are rollout cases.

## Owner decision

- Decision: waived
- Date: 2026-10-07
- Owner words: "youve got enough usage to implement each change yourself, do that but do it with cheaper sonnet subagents"
- Context: Roadmap item S4 under owner decision D3. Final acceptance is requested at the end of the roadmap.
