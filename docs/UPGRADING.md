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

## Assisted Upgrade With `statedd_upgrade.py`

The template now ships `scripts/statedd_upgrade.py` for non-destructive downstream upgrades.

```bash
python3 scripts/statedd_upgrade.py /path/to/downstream/repo
python3 scripts/statedd_upgrade.py /path/to/downstream/repo --apply
python3 scripts/statedd_upgrade.py /path/to/downstream/repo --apply --force-managed
```

- Default mode is dry-run.
- `--apply` copies only safe missing managed assets.
- `--force-managed` may replace outdated safe template assets; it never overwrites project-truth files.
- Project-truth files such as `PROJECT_STATE.yaml`, `BACKLOG.md`, `NEXT_ACTIONS.md`, `WORKLOG.md`,
  `docs/EVIDENCE_LOG.md`, `docs/ACCEPTANCE_FREEZES.md`, `README.md`, and `CHANGELOG.md` are always
  reported as manual actions.

## Manual Upgrade Checklist

1. Read the source repo `VERSION`.
2. Run `python3 scripts/statedd_upgrade.py --dry-run` to see what would change.
3. Copy or merge reusable assets from the new template.
4. Run `python3 scripts/statedd_version_check.py`.
5. Run `python3 scripts/check_state_docs.py`.
6. Run `python3 scripts/statedd_validate_schema.py`.
7. Run `python3 scripts/test_init_template.py` if the repo keeps initializer tests.
8. Do not claim closure-grade unless audit and evidence requirements are met.

## Common Conflicts

- Older repos may only have `repo_mode`. Keep it as a compatibility alias if needed, but make `repo_role` and `statedd_mode` explicit.
- `PROJECT_ADAPTER.yaml` may carry an older adapter version while `PROJECT_STATE.yaml` and `PROJECT_DNA.yaml` have moved forward.
- Existing project `CHANGELOG.md` files may be product history, not StateDD template history. Do not overwrite them during adoption without explicit human approval.
- A copied prompt or script can be newer than the state files. Run the version check before handoff.
