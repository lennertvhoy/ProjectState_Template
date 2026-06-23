# EVIDENCE_LOG.md

**Purpose:** Structured ledger of proof artifacts for user-facing claims.

## Entry Format

```yaml
- ID: EV-YYYY-MM-DD-001
  File: /absolute/path/to/artifact.png
  Title: short description
  Source/System: browser | api | test | log | screenshot
  Route/Page: optional route or URL
  Action: what was done
  Shows:
    - visible fact 1
    - visible fact 2
  Proves:
    - why the artifact matters
  Type: source-data | chatbot | gap | integration | docs-render-verification
  as_of: 2026-03-18T18:00:00+01:00
  Notes: optional context
```

## Guidance

- Link evidence to the specific claim it supports.
- Prefer durable artifact paths.
- Place saved artifacts under `docs/evidence/YYYY-MM-DD-<slug>/` when possible.
- Add timestamps for anything that may become stale.

## EV-2026-06-23-002: Template-maintenance mode split verified

- File: /home/ff/Documents/Projects/StateDD_Template/docs/evidence/2026-06-23-template-maintenance-mode/README.md
- File: /home/ff/Documents/Projects/StateDD_Template/docs/evidence/2026-06-23-template-maintenance-mode/before-check_state_docs.txt
- File: /home/ff/Documents/Projects/StateDD_Template/docs/evidence/2026-06-23-template-maintenance-mode/generated-new-project-state.yaml
- File: /home/ff/Documents/Projects/StateDD_Template/docs/evidence/2026-06-23-template-maintenance-mode/generated-adopt-project-state.yaml
- Title: Root template-maintenance state split from downstream bootstrap state
- Source/System: test
- Action: Added `repo_role` and `statedd_mode`, made checks mode-aware, updated generator output, docs, fixtures, and tests
- Shows:
  - root state declares `repo_role: template_repository` and `statedd_mode: template-maintenance`
  - generated new/adopted repos declare `repo_role: downstream_project` and `statedd_mode: bootstrap`
  - root `python3 scripts/check_state_docs.py --bootstrap-gate` passes after the split
  - generated downstream bootstrap still fails the bootstrap gate until investigation is complete
- Proves:
  - the template root no longer presents itself as a half-bootstrapped downstream project
  - downstream bootstrap safety gates remain intact
- Type: docs-render-verification
- as_of: 2026-06-23T00:00:00+02:00
- Notes: Runtime proof, schema validation, and upgrade tooling remain separate backlog items.

## EV-2026-06-23-001: StateDD version source normalized

- File: /home/ff/Documents/Projects/StateDD_Template/VERSION
- File: /home/ff/Documents/Projects/StateDD_Template/scripts/statedd_version_check.py
- File: /home/ff/Documents/Projects/StateDD_Template/docs/UPGRADING.md
- File: /home/ff/Documents/Projects/StateDD_Template/docs/evidence/2026-06-23-statedd-version-source/README.md
- Title: Canonical StateDD version source and alignment check added
- Source/System: test
- Action: Added version source, changelog, upgrade guidance, alignment script, validator wiring, initializer coverage, and CI command coverage
- Shows:
  - `python3 scripts/statedd_version_check.py` passed
  - `python3 scripts/check_state_docs.py` passed
  - `python3 scripts/test_init_template.py` passed, including generated and adopted version-asset checks
  - fixture hygiene checks passed after fixture spec identifiers were aligned
  - the intentionally thin bootstrap dry-run fixture still fails its bootstrap gate as expected
  - root `PROJECT_ADAPTER.yaml` now matches `statedd-template-v4`
- Proves:
  - current version-bearing files agree on the canonical StateDD spec version
  - generated and adopted repos receive version assets and can run the alignment check
- Type: docs-render-verification
- as_of: 2026-06-23T00:00:00+02:00
- Notes: GitHub release publishing and template/downstream state split remain separate backlog work.

## EV-2026-06-14-001: Tool/model routing template integration verified

- File: /home/ff/Documents/Projects/StateDD_Template/prompts/TOOL_MODEL_ROUTING_GUIDE.md
- File: /home/ff/Documents/Projects/StateDD_Template/prompts/CTO_SESSION_PROMPT.md
- File: /home/ff/Documents/Projects/StateDD_Template/scripts/init_template.py
- File: /home/ff/Documents/Projects/StateDD_Template/scripts/test_init_template.py
- Title: Dynamic CTO-lane tool/model routing guide integrated into template prompts and initializer
- Source/System: test
- Action: Ran `python3 scripts/check_state_docs.py` and `python3 scripts/test_init_template.py`
- Shows:
  - documentation hygiene check passed
  - initializer regression tests passed, including new/adopt routing-guide coverage
  - bootstrap gate still fails for pre-existing incomplete bootstrap baseline conditions
- Proves:
  - the template recognizes the routing guide as a required prompt asset
  - generated and adopted repos include the routing guide
- Type: docs-render-verification
- as_of: 2026-06-14T00:00:00+02:00
- Notes: No external model/provider facts were verified or encoded; routing guide requires current primary-source verification when concrete model claims affect a decision.

## EV-2026-06-14-002: Beginner onboarding and handoff helper integration verified

- File: /home/ff/Documents/Projects/StateDD_Template/docs/GETTING_STARTED_5_MIN.md
- File: /home/ff/Documents/Projects/StateDD_Template/prompts/OPENCODE_STARTUP_PROMPT.md
- File: /home/ff/Documents/Projects/StateDD_Template/scripts/statedd_handoff.py
- File: /home/ff/Documents/Projects/StateDD_Template/scripts/test_init_template.py
- Title: Beginner onboarding, OpenCode startup, and read-only handoff snapshot helper integrated
- Source/System: test
- Action: Ran Python syntax checks, documentation hygiene check, initializer regression tests, handoff helper with validation output, and bootstrap gate
- Shows:
  - `python3 -m py_compile scripts/statedd_handoff.py scripts/init_template.py scripts/check_state_docs.py scripts/test_init_template.py` passed
  - `python3 scripts/check_state_docs.py` passed
  - `python3 scripts/test_init_template.py` passed
  - `python3 scripts/statedd_handoff.py --no-include-listeners --test-command "python3 scripts/check_state_docs.py"` printed repo identity and validation output
  - `python3 scripts/check_state_docs.py --bootstrap-gate` still fails for incomplete bootstrap baseline conditions
- Proves:
  - new and adopted repos include the beginner/OpenCode/handoff assets
  - the handoff helper runs without mutating repo state
  - the repo has not falsely claimed bootstrap completion
- Type: docs-render-verification
- as_of: 2026-06-14T12:57:04+02:00
- Notes: GitHub metadata/release changes, large example projects, license FAQ, and automated screenshot/evidence capture were not implemented in this slice.

## EV-2026-06-14-003: Teaching-rights-reserved license policy integrated

- File: /home/ff/Documents/Projects/StateDD_Template/LICENSE
- File: /home/ff/Documents/Projects/StateDD_Template/LICENSE_FAQ.md
- File: /home/ff/Documents/Projects/StateDD_Template/README.md
- File: /home/ff/Documents/Projects/StateDD_Template/scripts/check_state_docs.py
- File: /home/ff/Documents/Projects/StateDD_Template/scripts/test_init_template.py
- Title: Custom license updated to allow free/commercial use while reserving teaching and training rights
- Source/System: test
- Action: Updated license wording, README note, template copy surface, validator checks, and initializer regression tests
- Shows:
  - `python3 scripts/check_state_docs.py` passed
  - `python3 scripts/test_init_template.py` passed
  - new repos include `LICENSE_FAQ.md`
  - validator checks for commercial/profit permission and teaching-rights reservation
  - `python3 scripts/check_state_docs.py --bootstrap-gate` still fails for incomplete bootstrap baseline conditions
- Proves:
  - the template license surface matches the requested policy at the documentation and initializer level
- Type: docs-render-verification
- as_of: 2026-06-14T13:00:00+02:00
- Notes: This is a custom license draft, not legal advice or lawyer-reviewed text.

## EV-2026-06-14-004: StateDD v2 executable workflow implemented

- File: /home/ff/Documents/Projects/StateDD_Template/scripts/statedd_audit.py
- File: /home/ff/Documents/Projects/StateDD_Template/scripts/statedd_doctor.py
- File: /home/ff/Documents/Projects/StateDD_Template/prompts/SLICE_CONTRACT_TEMPLATE.md
- File: /home/ff/Documents/Projects/StateDD_Template/prompts/EVIDENCE_README_TEMPLATE.md
- File: /home/ff/Documents/Projects/StateDD_Template/prompts/SCHEMA_OWNERSHIP_TEMPLATE.md
- File: /home/ff/Documents/Projects/StateDD_Template/prompts/SUBAGENT_REVIEW_TEMPLATE.md
- File: /home/ff/Documents/Projects/StateDD_Template/prompts/CTO_REVIEW_CHECKLIST.md
- File: /home/ff/Documents/Projects/StateDD_Template/docs/evidence/2026-06-14-statedd-v2-executable-workflow/README.md
- Title: StateDD v2 executable workflow assets added and validated
- Source/System: test
- Action: Added audit, doctor, slice contract, claim ledger, schema ownership, subagent output, CTO checklist, ADR template, human override rule, and wired them into init/validation
- Shows:
  - `python3 scripts/check_state_docs.py` passed
  - `python3 scripts/test_init_template.py` passed, including v2 asset tests
  - `python3 scripts/statedd_doctor.py` produced the expected health summary
  - `python3 scripts/statedd_audit.py` passed on a freshly generated demo repo
- Proves:
  - the template now ships executable audit/doctor commands and v2 prompt assets
  - the initializer and validator recognize and propagate the new assets
- Type: docs-render-verification
- as_of: 2026-06-14T13:40:01+00:00
- Notes: Template repo remains in bootstrap mode. The SkillSignal-specific canonical schema/export/import loop is deferred to a downstream slice.
