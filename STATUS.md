# StateDD Template Status

**Updated At:** 2026-06-23 15:52 +02:00
**Execution Mode:** template-maintenance
**Project State:** template_maintenance_active
**Public URL:** not configured

## Snapshot

- Repo identifies as `repo_role: template_repository` with `statedd_mode: template-maintenance` and spec version `statedd-template-v4`.
- Generated/adopted downstream repos still start as `repo_role: downstream_project` with `statedd_mode: bootstrap`.
- Runtime proof, schema-backed validation, evidence pack manifests, downstream upgrade tooling, and adoption profiles are all template capabilities.
- The interactive bootstrap wizard MVP is available via `scripts/statedd_bootstrap_wizard.py`.
- All new capabilities are tested, documented, and wired into hygiene/audit/CI without external dependencies.
- Worktree is clean and the latest evidence folder is `docs/evidence/2026-06-23-adoption-ready-evidence-release`.

## Immediate Priorities

1. Add a real canonical schema/export/import example project.
2. Publish repository description, topics, and release notes.
3. Use Kimi WebBridge to browser-verify user-facing changes when available.

## Active Blockers

- None.

## Notes

- Keep `STATUS.md` short.
- Use `PROJECT_STATE.yaml` for structured truth.
- Use `BACKLOG.md` backlog IDs inside `NEXT_ACTIONS.md` when active items are added.
- Prove runtime identity before accepting user-facing behavior.
