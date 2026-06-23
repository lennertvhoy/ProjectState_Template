# Upgrading StateDD

Current StateDD spec version: `statedd-template-v4`

Use this guide when bringing an existing StateDD repo forward without overwriting local project truth.

## Upgrade Rules

- Treat `VERSION` as the canonical StateDD template version.
- Add `repo_role` and `statedd_mode` when upgrading older StateDD state files.
- Use `repo_role: template_repository` and `statedd_mode: template-maintenance` only for the StateDD template repository itself.
- Use `repo_role: downstream_project` and `statedd_mode: bootstrap` for generated or adopted project repositories until their baseline is proven.
- Preserve project-specific `PROJECT_STATE.yaml`, `STATUS.md`, `BACKLOG.md`, `NEXT_ACTIONS.md`, and `WORKLOG.md` content unless the human explicitly approves a replacement.
- Upgrade reusable workflow assets first: `scripts/`, `prompts/`, `docs/`, and `.github/` files.
- Align version-bearing state files only after checking whether their project-specific fields are still true.
- Record the upgrade in `WORKLOG.md` and link any verification in `docs/EVIDENCE_LOG.md`.

## Manual Upgrade Checklist

1. Read the source repo `VERSION`.
2. Copy or merge reusable assets from the new template.
3. Run `python3 scripts/statedd_version_check.py`.
4. Run `python3 scripts/check_state_docs.py`.
5. Run `python3 scripts/test_init_template.py` if the repo keeps initializer tests.
6. Do not claim closure-grade unless audit and evidence requirements are met.

## Common Conflicts

- Older repos may only have `repo_mode`. Keep it as a compatibility alias if needed, but make `repo_role` and `statedd_mode` explicit.
- `PROJECT_ADAPTER.yaml` may carry an older adapter version while `PROJECT_STATE.yaml` and `PROJECT_DNA.yaml` have moved forward.
- Existing project `CHANGELOG.md` files may be product history, not StateDD template history. Do not overwrite them during adoption without explicit human approval.
- A copied prompt or script can be newer than the state files. Run the version check before handoff.
