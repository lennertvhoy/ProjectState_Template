# State Driven Development Template Status

**Updated At:** 2026-04-09 20:44 CEST
**Execution Mode:** operating
**Project State:** public_release_ready
**Public URL:** not configured

## Snapshot

- This repository is the public release-ready State Driven Development Template, and `README.md` is the canonical user guide for setup, bootstrap, and day-to-day use.
- This repo is maintained as the template package itself, not as a downstream product repo that should dogfood every workflow ceremony on each small edit.
- The public naming and contract wording have been simplified so the template reads as one clear thing instead of multiple layered labels.
- The template now supports explicit `new` and `adopt` initialization paths, backlog IDs, a canonical final handoff template, and a bootstrap-gate validator.
- The contract now also requires runtime-identity proof for user-facing acceptance, provides an acceptance-freeze ledger/template, and constrains negative-search wording.
- Existing repo adoption preserves the existing README by default, supports `--dry-run`, and installs GitHub assets only when requested.
- Evidence artifacts now have a default placement convention under `docs/evidence/`.

## Immediate Priorities

1. Keep the live contract, generated contract, prompt files, and validator aligned.
2. Preserve adoption safety and bootstrap-gate signal as release guardrails.

## Active Blockers

- None in template state.

## Notes

- `STATUS.md` is intentionally short.
- Use `PROJECT_STATE.yaml` for machine-readable truth.
- Use `PROJECT_DNA.yaml` for stable architecture assumptions.
