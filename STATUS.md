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
- Runtime proof is now a template capability through `scripts/statedd_runtime_proof.py`, `runtime_identity.json`, audit recognition, doctor status, CI smoke coverage, and init/adopt asset coverage.
- Schema-backed validation is now a template capability through `schemas/`, `scripts/statedd_validate_schema.py`, tests, CI, audit, doctor, hygiene checks, and init/adopt asset coverage.

## Immediate Priorities

1. Add evidence manifests and redaction checks.
2. Add non-destructive downstream upgrade tooling.
3. Add adoption profiles and an interactive bootstrap wizard.

## Active Blockers

- None.

## Notes

- Keep `STATUS.md` short.
- Use `PROJECT_STATE.yaml` for structured truth.
- Use `BACKLOG.md` backlog IDs inside `NEXT_ACTIONS.md` when active items are added.
- Prove runtime identity before accepting user-facing behavior.
