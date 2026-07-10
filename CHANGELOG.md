# Changelog

All notable StateDD template changes are tracked here.

## statedd-template-v5 - Unreleased

- Removed duplicate generated `PROJECT_DNA.yaml` mappings while retaining the full invariant set.
- Made version checks derive template-only requirements from parsed repository role metadata instead of README wording.
- Made upgrade reports distinguish applied upgrades (`dry_run: false`) from dry-run plans (`dry_run: true`).

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
- Added `schemas/examples/schema_prompt_loop/`, a canonical schema/prompt loop example that validates data and generates deterministic prompt material from the same schema.
- Added draft release notes and repository metadata in `docs/RELEASE_NOTES_statedd-template-v4.md`.
- Added acceptance freeze `AF-2026-06-23-002` for the BL-012/013/014 adoption-ready template release.
- BL-007: Simplified the README top half with a beginner-friendly "Start here" and "Start Simple" section.
- BL-007: Added `docs/QUICK_COMMANDS.md` copy-paste command cheat sheet.
- BL-007: Improved `docs/ADOPTION_PROFILES.md` with a decision tree and explicit default recommendation (`solo`).
- BL-007: Polished `docs/GETTING_STARTED_5_MIN.md` so it can be followed without reading the full README first.
- BL-007: Finalized `docs/RELEASE_NOTES_statedd-template-v4.md` as release-candidate ready with a human-permission gate for publishing.
- BL-BROWSER-001: Added provider-agnostic browser verification contract (`schemas/browser_verification.schema.json`, `docs/BROWSER_VERIFICATION.md`, `scripts/statedd_browser_verify.py`, `scripts/test_browser_verification.py`, fixtures, and audit/doctor/CI integration). Kimi WebBridge is a preferred provider when available, not a required dependency; Playwright, agent-native browser tools, existing E2E tests, manual screenshots, and custom tooling are accepted when evidence is durable and honestly scoped.
- BL-QUALITY-001: Added reusable quality firewall guidance (`QUALITY_FIREWALL.md`, `FAILURE_TAXONOMY.md`, `INCIDENT_RESPONSE.md`, `docs/failure_scans/TEMPLATE.md`, `docs/incidents/README.md`, `docs/quality_gates/README.md`), expanded state/evidence/prompt contracts, and wired generated/adopted repo plus upgrade propagation.
- Added acceptance freeze `AF-2026-06-23-004` for BL-007 public usability and release-readiness polish.
- Published `statedd-template-v4` as GitHub release `v4`.

## Earlier History

Earlier dated implementation history lives in `WORKLOG.md`.
