# WORKLOG

**Purpose:** Append-only history for completed work.

## 2026-06-14 - Dynamic CTO tool/model routing added

**Type:** template_prompt_governance
**Status:** COMPLETE
**Git Head:** c76dad7
**Worktree:** dirty before work; pre-existing changes were observed in `LICENSE`, `README.md`, and `security_best_practices_report.md`

### What changed
- Added `prompts/TOOL_MODEL_ROUTING_GUIDE.md` for CTO-lane routing of tools, models, settings, context strategy, and tailored prompts.
- Updated `prompts/CTO_SESSION_PROMPT.md`, `prompts/CODING_AGENT_STARTUP_PROMPT.md`, `AGENTS.md`, `PROJECT_DNA.yaml`, `PROJECT_ADAPTER.yaml`, `PROJECT_STATE.yaml`, and `README.md` to reference the routing behavior.
- Updated `scripts/init_template.py` so new/adopted repos receive the routing guide and state pointers.
- Updated `scripts/check_state_docs.py` and `scripts/test_init_template.py` to validate the new guide and initializer coverage.

### Verification
- `python3 scripts/check_state_docs.py` passed.
- `python3 scripts/test_init_template.py` passed.
- `python3 scripts/check_state_docs.py --bootstrap-gate` failed because the template repo remains in bootstrap with system/repo investigation still false and no real active queue.

### Evidence
- `docs/EVIDENCE_LOG.md` entry `EV-2026-06-14-001`

### Notes
- Specific GPT, DeepSeek, or other provider claims were not encoded as template truth because model catalogs, pricing, context windows, and availability are time-sensitive.
- The routing guide requires current primary-source verification when concrete model facts affect a recommendation.

## 2026-06-14 - Feedback-filtered usability slice added

**Type:** template_usability
**Status:** COMPLETE
**Git Head:** c76dad7
**Worktree:** dirty before work; existing uncommitted changes were preserved

### Feedback evaluated
- Integrated: beginner 5-minute start guide.
- Integrated: dedicated OpenCode startup prompt.
- Integrated: lightweight read-only handoff helper.
- Deferred: large example project suite because it adds maintenance burden and should be designed as a separate slice.
- Deferred: GitHub description/topics/release because it is repository-hosting metadata, not locally verifiable template behavior in this slice.
- Deferred: license FAQ because the license text was already in flux in uncommitted changes and should not be mixed into this workflow usability slice.
- Deferred: automated screenshot/evidence capture because it needs a separate design to avoid false runtime proof.

### What changed
- Added `docs/GETTING_STARTED_5_MIN.md`.
- Added `prompts/OPENCODE_STARTUP_PROMPT.md`.
- Added `scripts/statedd_handoff.py`.
- Updated README navigation, docs/scripts README files, template state pointers, initializer support assets, validator requirements, and initializer regression tests.

### Verification
- `python3 -m py_compile scripts/statedd_handoff.py scripts/init_template.py scripts/check_state_docs.py scripts/test_init_template.py` passed.
- `python3 scripts/check_state_docs.py` passed.
- `python3 scripts/test_init_template.py` passed.
- `python3 scripts/statedd_handoff.py --no-include-listeners --test-command "python3 scripts/check_state_docs.py"` passed and printed repo identity plus validation output.
- `python3 scripts/check_state_docs.py --bootstrap-gate` failed because the template repo remains in bootstrap with system/repo investigation still false and no real active queue.

### Evidence
- `docs/EVIDENCE_LOG.md` entry `EV-2026-06-14-002`

### Notes
- The handoff helper is intentionally read-only and labels runtime facts as `not proven` unless directly captured.
- The repo remains in bootstrap mode.

## 2026-06-14 - License changed to reserve teaching rights

**Type:** license_policy_update
**Status:** COMPLETE
**Git Head:** c76dad7
**Worktree:** dirty before work; existing uncommitted changes were preserved

### What changed
- Replaced the previous license text with a custom `StateDD Free Use License - Teaching Rights Reserved`.
- Added `LICENSE_FAQ.md` with plain-language examples.
- Updated `README.md`, `PROJECT_STATE.yaml`, `PROJECT_DNA.yaml`, and `scripts/init_template.py` so the license and FAQ are part of the new-repo template surface.
- Updated `scripts/check_state_docs.py` and `scripts/test_init_template.py` to validate the license policy and ensure new repos include `LICENSE_FAQ.md`.

### Verification
- `python3 scripts/check_state_docs.py` passed.
- `python3 scripts/test_init_template.py` passed.
- `python3 -m py_compile scripts/init_template.py scripts/check_state_docs.py scripts/test_init_template.py` passed.
- `python3 scripts/check_state_docs.py --bootstrap-gate` failed because the template repo remains in bootstrap with system/repo investigation still false and no real active queue.

### Evidence
- `docs/EVIDENCE_LOG.md` entry `EV-2026-06-14-003`

### Notes
- The policy now permits free use, commercial use, distribution, modification, sublicensing, and selling copies/services that use the Software.
- Teaching, training, coaching, courses, workshops, tutorials, curricula, educational products, and educational services based on the Software or StateDD workflow are reserved rights unless prior written permission is granted.
- This is a custom license draft and should be reviewed by a qualified lawyer before relying on it commercially.

## 2026-06-14 - StateDD v2 executable workflow

**Type:** template_workflow_upgrade
**Status:** COMPLETE
**Git Head:** 0d406e6
**Worktree:** dirty before final commit

### What changed
- Added `scripts/statedd_audit.py` for machine-checkable closure audits.
- Added `scripts/statedd_doctor.py` for fast health summaries.
- Added `prompts/SLICE_CONTRACT_TEMPLATE.md` for formal slice contracts.
- Added `prompts/EVIDENCE_README_TEMPLATE.md` for claim ledgers.
- Added `prompts/SCHEMA_OWNERSHIP_TEMPLATE.md` enforcing canonical schemas, generated examples/prompts, validation tests, `schemaVersion`, and migration policy.
- Added `prompts/SUBAGENT_REVIEW_TEMPLATE.md` for strict subagent output.
- Added `prompts/CTO_REVIEW_CHECKLIST.md` for repeatable CTO review.
- Added `docs/adr/README.md` and `docs/adr/0000-adr-template.md`.
- Added `docs/WORKFLOW_FOR_BEGINNERS.md` with a Mermaid diagram, prompt map, and quality checklist.
- Updated `AGENTS.md` with the Human Override Rule and v2 tool list.
- Updated `prompts/FINAL_HANDOFF_TEMPLATE.md` with four-state closure, release/update gate, and override wording.
- Updated `prompts/CTO_SESSION_PROMPT.md` and `prompts/CODING_AGENT_STARTUP_PROMPT.md` to reference v2 assets.
- Updated `scripts/init_template.py`, `scripts/check_state_docs.py`, `scripts/statedd_handoff.py`, and `scripts/test_init_template.py` to ship and validate v2 assets.
- Updated `.github/workflows/validate.yml` to compile and exercise v2 scripts.
- Updated `README.md`, `docs/GETTING_STARTED_5_MIN.md`, `STATUS.md`, `PROJECT_STATE.yaml`, `PROJECT_DNA.yaml`, `BACKLOG.md`, and `NEXT_ACTIONS.md`.

### Verification
- `python3 -m py_compile scripts/check_state_docs.py scripts/init_template.py scripts/statedd_handoff.py scripts/statedd_audit.py scripts/statedd_doctor.py scripts/test_init_template.py` passed.
- `python3 scripts/check_state_docs.py` passed.
- `python3 scripts/test_init_template.py` passed, including new v2 asset tests and `test_doctor_runs`.
- `python3 scripts/statedd_doctor.py` produced the expected health summary.
- `python3 scripts/statedd_audit.py` on the template root failed only on dirty worktree, as expected during implementation.
- `python3 scripts/statedd_audit.py` on a freshly generated demo repo passed.
- Generated repo smoke test passed.

### Evidence
- `docs/evidence/2026-06-14-statedd-v2-executable-workflow/README.md`
- `docs/EVIDENCE_LOG.md` entry `EV-2026-06-14-004`

### Notes
- The template repo remains in bootstrap mode.
- The SkillSignal-specific canonical schema/export/import loop is a downstream application of the new `SCHEMA_OWNERSHIP_TEMPLATE.md`, not implemented in this slice.
- The Human Override Rule was added explicitly so the workflow stays a strong default, not a prison.
- Subagent review feedback was integrated: fixed `.jpg` suffix detection, expanded override marker checks, hardened `statedd_doctor.py` file reads, added `AGENTS.md` freshness to doctor output, and aligned generated `PROJECT_DNA.yaml` / `PROJECT_ADAPTER.yaml` versions to v4.
