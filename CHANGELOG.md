# Changelog

All notable StateDD template changes are tracked here.

## statedd-template-v4 - 2026-06-23

- Added `VERSION` as the canonical StateDD template spec-version source.
- Added `scripts/statedd_version_check.py` to fail when current version-bearing files disagree.
- Added `docs/UPGRADING.md` for downstream upgrade guidance.
- Normalized the root adapter version to match the rest of the template state.
- Wired version alignment into documentation hygiene, initializer regression tests, and CI.
- Added `schemas/evidence_manifest.schema.json` and `scripts/statedd_evidence_pack.py` for evidence folder manifests, hash verification, and redaction scanning.
- Added `scripts/test_evidence_pack.py` and wired evidence pack checks into hygiene, audit, doctor, initializer, and CI.
- Added `scripts/statedd_upgrade.py` for non-destructive downstream upgrades with dry-run-by-default, `--apply`, and `--force-managed` modes.
- Added `scripts/test_upgrade.py` and wired upgrade tooling into initializer, doctor, `docs/UPGRADING.md`, and CI.
- Added adoption profiles (`minimal`, `solo`, `team`, `regulated`) to `scripts/init_template.py` for `new` and `adopt` subcommands.
- Added `docs/ADOPTION_PROFILES.md` and profile-specific rendering into generated `AGENTS.md`, `STATUS.md`, `PROJECT_STATE.yaml`, `PROJECT_ADAPTER.yaml`, and `BACKLOG.md`.
- Added `scripts/statedd_bootstrap_wizard.py` MVP with interactive and `--answers` modes.
- Added `scripts/test_adoption_profiles.py` and wired profile/wizard tests into CI.
- Updated `scripts/check_state_docs.py` to skip optional deep-reference docs when the minimal profile is used.

## Earlier History

Earlier dated implementation history lives in `WORKLOG.md`.
