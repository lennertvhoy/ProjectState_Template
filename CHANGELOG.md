# Changelog

All notable ProjectState template changes are tracked here.

> **Note on naming:** This template was renamed from `StateDD` to `ProjectState`
> on 2026-07-27. Historical entries below retain the prior name for accuracy.
> Backward-compat aliases (script shims, command aliases, schema identifier
> enums, legacy `STATEDD_*` env-var and filename fallbacks) are kept for one
> migration cycle. Canonical identifiers are now `projectstate-template-v6`,
> `PROJECTSTATE_ASSETS.json`, and `scripts/projectstate_*.py`.

## Unreleased

- **BL-OUTCOME-CORE-001: Replaced the default governance stack with an
  outcome-first core.** New and adopted projects now default to `core` and use
  `PROJECT.md`, `STATE.yaml`, `AGENTS.md`, and one slice evidence summary as
  their canonical coordination surface. Added a dependency-free outcome gate
  with primary-journey precedence, two-failure simplification review, and
  exposure-aware risk stop-lines. Added an explicit `hardened` overlay; retained
  v5 profiles only as opt-in compatibility paths. Removed asset locks, line
  budgets, control-head binding, companion commits, and mandatory remote closure
  from the default path.

- **BL-AUTONOMY-001: Integrated the autonomous improvement workflow.** Added
  `skills/improve/SKILL.md` and `/projectstate-improve` as the sanctioned
  multi-slice loop (assess, prioritize, implement vertically, validate,
  falsify, close, repeat) with an explicit autonomy ladder in `AGENTS.md`
  (L0 inspect → L4 human-only), stop conditions, and a final-report contract.
  Fixed subsystem enumeration drift: `git-safety` skill added to `AGENTS.md`,
  `.github/copilot-instructions.md` skill/command lists refreshed and its
  false "auto-generated" claim corrected, root-level reference docs no longer
  described as living under `docs/`, `prompts/AGENTS.md` catalog now lists
  `NEW_PROJECT_FROM_URL.md`, and the beginner-workflow contradiction with
  delegated slice selection removed.
- **BL-RENAME-001: StateDD -> ProjectState rename.** Renamed canonical brand,
  script modules (`scripts/projectstate_*.py`), slash commands
  (`commands/projectstate-*.md`), schemas, version string
  (`projectstate-template-v5`), package name (`projectstate-template`), repo
  display name, and GitHub repository (`StateDD_Template` -> `ProjectState_Template`).
  Backward-compat preserved: legacy `scripts/statedd_*.py` shims re-export the
  canonical modules; `commands/statedd-*.md` alias files point at canonical
  commands; schema `enum` constants accept both `projectstate.*` and `statedd.*`
  identifiers; `STATEDD_ASSETS.json` and `STATEDD_*` env vars are still honored
  via `scripts/projectstate_contracts.py:resolve_assets_manifest` and per-call
  fallbacks. Historical artifacts (evidence, fixtures, WORKLOG, EVIDENCE_LOG,
  dated incident records, BL-STATEDD-INTEGRATION-001 scan id, v4 release notes)
  are intentionally preserved verbatim. Efficiency budgets updated to reflect
  measured post-rename footprint (template_repository, team, regulated profiles).
- BL-WORKSPACE-LIFECYCLE-001: Replaced metadata-only isolation release with a
  verified physical lifecycle: centrally managed non-recursive clone paths,
  same-origin sibling inventory, clean-clone quarantine, no-force clean-worktree
  removal, and a strict release receipt required by `HANDOFF_COMPLETE`.
- Added regressions for nested/arbitrary provisioning, manual sibling clones,
  dirty retention, physical path absence, reservation cleanup, transport-neutral
  origin identity, contradictory finish receipts, fail-closed gate aggregation,
  and non-incidental handoff evidence selection.
- Audited and reversibly archived nine historical sibling clones; all clone work
  is integrated. Preserved the dirty BL-BROWSER-002 prototype for redesign.

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
