# State Drive Development Template Status

**Updated At:** 2026-04-09 20:12 CEST
**Execution Mode:** operating
**Project State:** public_release_ready
**Public URL:** not configured

## Snapshot

- This repository is the public release-ready State Drive Development Template (`StateDD_Template`) for a truth-first AI-assisted workflow.
- `README.md` is the canonical user guide and now distinguishes the template name from the operating-model name.
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
