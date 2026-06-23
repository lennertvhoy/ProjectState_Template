# StateDD Template Status

**Updated At:** 2026-06-23
**Execution Mode:** bootstrap
**Project State:** bootstrap_template_maintenance
**Public URL:** not configured

## Snapshot

- Repo remains in bootstrap mode while the template-maintenance baseline is clarified.
- Canonical StateDD spec version is `statedd-template-v4` from `VERSION`.
- Version alignment is now checked by `scripts/statedd_version_check.py`.
- Root `PROJECT_ADAPTER.yaml` has been normalized from the stale adapter version to v4.
- Runtime proof, schema validation, and template/downstream state split remain open roadmap work.

## Immediate Priorities

1. Resolve the template-maintenance mode split.
2. Add runtime identity proof artifacts.
3. Add schema-backed validation for state and evidence files.

## Active Blockers

- None.

## Notes

- Keep `STATUS.md` short.
- Use `PROJECT_STATE.yaml` for structured truth.
- Use `BACKLOG.md` backlog IDs inside `NEXT_ACTIONS.md` when active items are added.
- Prove runtime identity before accepting user-facing behavior.
