# Upgrading StateDD

Current StateDD spec version: `statedd-template-v5`

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
python3 scripts/statedd_upgrade.py /path/to/downstream/repo --include-asset-set github
```

- Default mode is dry-run.
- The current profile catalog defines the desired future asset set. The existing
  `STATEDD_ASSETS.json` records historical ownership and installed/base hashes;
  it never prevents a newly introduced profile asset from being offered.
- A missing lock may be inspected read-only only when `--profile` explicitly
  establishes legacy intent. No-lock `--apply` is refused because it cannot prove
  project-truth ownership; use `init_template.py adopt` to establish the first
  complete instance contract. Malformed, duplicate, unsafe, or unsupported locks
  fail before writes.
- `--apply` creates missing assets, replaces only unmodified template-owned
  assets, regenerates the lock last, and rolls back an interrupted operation.
- Locally modified template-owned assets are conflicts. Project-owned truth is
  preserved; a missing required protected file is a blocking conflict.
  `--force-managed` may replace only a historically template-owned modified
  asset; it is not a merge and never overrides project truth.
- Assets removed from the current profile are recorded as retired and reported;
  they are not silently deleted. A successful second run is idempotent.
- The target root, every managed path, and every template source are confined and
  symlink-safe before any mutation begins.
- Profile transitions are not inferred by this release. An existing lock whose
  profile differs from `--profile` fails closed pending an explicit semantic
  migration.
- Optional module sets come from the catalog and may be enabled with repeatable
  `--include-asset-set`. `--include-github-assets` remains a compatibility alias.
- `--report` writes a new external plan sidecar before target mutation. It never
  overwrites an existing path, records `apply_requested`, and deliberately does
  not claim that application succeeded.

## Manual Upgrade Checklist

1. Read the source repo `VERSION`.
2. Run `python3 scripts/statedd_upgrade.py /path/to/repo --dry-run` to see every
   planned action, conflict, and retired asset.
3. Copy or merge reusable assets from the new template.
4. Run the upgraded repository's required gate level from
   `STATEDD_ASSETS.json`: `python3 scripts/statedd_quality_gate.py --gate-level N`.
5. Commit and push normally, then use exact-head remote closure when the claim
   crosses the remote/CI boundary.

## Common Conflicts

- Older repos may only have `repo_mode`. Keep it as a compatibility alias if needed, but make `repo_role` and `statedd_mode` explicit.
- `PROJECT_ADAPTER.yaml` may carry an older adapter version while `PROJECT_STATE.yaml` and `PROJECT_DNA.yaml` have moved forward.
- Existing project `CHANGELOG.md` files may be product history, not StateDD template history. Do not overwrite them during adoption without explicit human approval.
- A copied prompt or script can be newer than the state files. Run the version check before handoff.
- Semantic or three-way migration of customized project truth is not implemented.
  Preserve it and perform an explicit reviewed migration.
