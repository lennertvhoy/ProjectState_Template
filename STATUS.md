# StateDD Template Status

**Updated At:** 2026-06-23
**Execution Mode:** template-maintenance
**Project State:** template_maintenance_active
**Public URL:** not configured

## Snapshot

- Repo now identifies as `repo_role: template_repository` with `statedd_mode: template-maintenance`.
- Canonical StateDD spec version is `statedd-template-v4` from `VERSION`.
- Version alignment is now checked by `scripts/statedd_version_check.py`.
- Generated and adopted downstream repos still start as `repo_role: downstream_project` with `statedd_mode: bootstrap`.
- Runtime proof and schema validation remain open roadmap work.

## Immediate Priorities

1. Add runtime identity proof artifacts.
2. Add schema-backed validation for state and evidence files.
3. Add evidence manifests and redaction checks.

## Active Blockers

- None.

## Notes

- Keep `STATUS.md` short.
- Use `PROJECT_STATE.yaml` for structured truth.
- Use `BACKLOG.md` backlog IDs inside `NEXT_ACTIONS.md` when active items are added.
- Prove runtime identity before accepting user-facing behavior.
