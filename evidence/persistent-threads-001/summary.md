# Evidence: persistent-threads-001

## Scope and authorization

The human requested integration if valuable and staging a next-session template
update across the home Projects folder. The selected change is optional thread
instructions and prompts, preserving the minimal default and human governance.
Downstream work queues a semantic refresh; it does not claim projects migrated.

## Primary journey

- Environment: Local Linux workstation; Python 3.14.7; temporary generated projects and existing home Projects checkouts
- Command: `python3 scripts/test_outcome_core.py`
- Result: passed
- Exit code: 0

Baseline before edits: 20 tests passed, including default new/adopt, the
adversarial packaged-product failure/recovery, and profile isolation.

## Limitations

Real-agent thread replacement, host routing, and token savings are unproven.
Human acceptance and remote delivery remain pending. Existing project changes
must be preserved; the template started clean on main and uses the private
branch `feat/optional-persistent-threads`.

## Secondary checks

- `python3 /tmp/verify-projectstate-thread-rollout.py`: passed. Generated new and
  adopt for core and hardened include the optional rules without prompt-file
  dependencies; adoption preserves the product README. Source snapshot hashes,
  21 staged notices, and exact preservation of prior AGENTS.md bytes passed.
- `ruff check scripts/init_template.py scripts/test_outcome_core.py`: passed.
- `git diff --check`: passed.
- First closure gate check found an environment-label mismatch between STATE.yaml
  and this summary; aligned the label with the environment actually used.
- Initial `python3 -m pytest scripts/ -q` failed one root-bootstrap check because
  this new summary lacked required headings. Product/generation tests passed.
  The evidence headings are now corrected; full rerun passed with exit 0.
- Rollout verification initially found a trailing blank line in the newly staged
  example-project-38 notice. Corrected only that index blob; rerun passed.

## Artifacts

- `prompts/PERSISTENT_THREADS.md`: optional role prompts and recoverable task
  packet; generated AGENTS.md carries the standalone compact rules.
- `rollout.json`: project-by-project staging disposition and preservation hashes.
- Local reference source: `~/Projects/.projectstate-handoffs/persistent-threads-2026-09-05`.
  Contains a generated six-file core, migration guide, optional prompts, and
  SHA256SUMS. It is a local review source, not a published release.
- `~/Projects/AGENTS.md`: inherited first-task directive for all projects.
- Temporary rollout/verification commands:
  `python3 /tmp/queue-projectstate-threads.py` and
  `python3 /tmp/verify-projectstate-thread-rollout.py`. These are one-off local
  operations, not installed template tooling. The rollout command refuses to
  overwrite its existing source bundle; it should not be replayed as an updater.

## Downstream disposition

24 visible sibling directory entries were assessed: 21 Git repositories have
only the newly inserted notice staged; example-project-07 has a written notice
and no Git repository. example-project-06 retains its previous local files
and is covered by the updated inherited queue: its required Git preflight failed
because no remote exists, including after a fresh preflight attempt. No remote
was invented or safety boundary bypassed. The example-project-33
folder is recovery evidence and was left untouched; the parent directive covers
future work without turning evidence into a project.

Applicable Git preflights permitted local mutations for example-project-09,
example-project-11, example-project-14, example-project-16, example-project-20, example-project-31,
and example-project-32. Command pattern:
`python3 scripts/projectstate_git_safety_check.py --repo ~/Projects/<project> --mode worktree --worktree-opt-in --trusted-local-machine --format json`.
Existing worktrees/branches were retained for these bounded notice edits. All
other indexed paths were verified unchanged. Existing unstaged AGENTS.md changes
were excluded from staging, including earlier migration notices.

This proves local template generation and queue placement, not execution of
future coding-agent sessions or completion of the downstream semantic migrations.

## Final validation and staging

- `python3 scripts/test_outcome_core.py`: 20 tests passed after generator changes.
- `python3 -m pytest scripts/ -q`: complete rerun passed, exit 0.
- `python3 scripts/projectstate_gate.py`: recorded outcome validated, exit 0.
- `ruff check scripts/init_template.py scripts/test_outcome_core.py`: passed.
- Template changes staged on `feat/optional-persistent-threads`; no commit, push,
  deployment, automatic thread routing, or downstream migration is claimed.
- The missing example-project-06 remote blocks its local staging, not queue
  delivery: the inherited user directive supplies its exact first task.
