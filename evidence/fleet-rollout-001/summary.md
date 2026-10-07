# Evidence: fleet-rollout-001

## Scope and authorization

Plan item S6: update every active v6 instance to release 6.3.0, remove stale
refresh notices, and point `~/Projects/AGENTS.md` at the update and fleet
commands. Owner-approved CTO plan (owner words "i choose all ur recs",
2026-10-06). Policy:
- An update always lands on a private branch first.
- A branch is fast-forwarded only when the update was purely mechanical and the
  project's AGENTS.md and gate were clean.
- A project whose AGENTS.md or gate has uncommitted edits by another session is
  left alone.
- Conversions that need judgment get a reviewed branch for the owner or the
  project's session to merge.

## Primary journey

- Environment: local Linux workstation; real ~/Projects, read only for the check
- Command: `python3 scripts/projectstate_fleet.py --root ~/Projects --stdout --format json`
- Result: blocked
- Exit code: 0

The doctor ran. The approved proof is that it reports every active v6 instance
on the current release, and that is not met yet:

| Group | Count | Repositories |
| --- | --- | --- |
| Current (gate and contract 6.3.0) | 8 | example-project-08, example-project-05, example-project-21, example-project-23, example-project-35, example-project-14, Demo, example-project-39 |
| Branch ready to fast-forward (owner) | 4 | example-project-22 `d0b6fdd`, StatePort `01846c3d`, example-project-34 `1850447`, example-project-20 `00e4178` |
| Left alone: another session's uncommitted AGENTS.md or gate edits | 6 | example-project-38, example-project-19, example-project-26, example-project-13, StatePort-Site, example-project-31 |
| Secondary checkouts sharing refs, following their primary | 2 | example-project-37 (StatePort), example-project-40 (StatePort-Site) |

## Secondary checks

- Every applied update left the project's gate verdict class unchanged, and
  each project's `projectstate_update.py --check` exits 0.
- Dry-run survey first. Conversion results:
  - 9 known template sections per instance were removed (6 in example-project-35).
  - Stale refresh notices were removed in StatePort, example-project-36
    and example-project-38' plan.
- Judgment conversions (Sonnet worker W9) kept project rules from modified
  template sections verbatim under "## Project rules from the earlier contract"
  and dropped only reworded template text.
  - StatePort's locally edited gate (blocker warning 300 instead of 600
    characters) was replaced. The commit message proposes the stricter limit
    upstream.
- The non-git Demo and example-project-39 were updated in place. Backups are
  in `~/.local/state/projectstate/backups/`.
- `~/Projects/AGENTS.md` now names the update and fleet commands and adds no
  first action.
- Doctor fix during the rollout: only fast-forwardable update branches are
  listed as ready, so example-project-37's shared ref is no longer misreported.
- Fleet-level changes are logged in the owner's local machine log (2026-10-07 entry).

## Artifacts

- Commits per repository, as listed above and in the machine log entry.
- Nothing is pushed.

## Limitations

- StatePort has an active interactive session. Its branch was not merged for
  that reason, and because its conversion involved judgment.
- StatePort's local "SHORT TRACK ... (overrides conflicting workflow text
  below)" heading now sits below the managed block. Its owner should reword it.
- StatePort's expired overnight directive (until 2026-09-06) was kept as an
  owner directive.
- Notices removed from example-project-36 and StatePort asked for a
  journey rerun after refreshing. The update is mechanical and gate verdicts are
  unchanged, but those journeys were not rerun.
