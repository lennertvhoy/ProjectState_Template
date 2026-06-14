# WORKLOG

**Purpose:** Append-only history for completed work.

Use this file for dated session notes, verification summaries, and references to evidence artifacts.

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
- Deferred: license FAQ because the license text is already in flux in uncommitted changes and should not be mixed into this workflow usability slice.
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
