---
command: "statedd-quality-freeze"
gate_level: 2
evidence_max: 8
cheapest_proof: "PROJECT_STATE execution mode and active P0/P1 truth agree; blocking gate is explicit"
escalate_when: "Release requires level 3 with CI proof"
description: "Enter quality freeze mode and run full quality gate"
---

# /statedd-quality-freeze — Quality Freeze

**When to use:** P0 product behavior broken, critical regression, or CTO mandates freeze.

**Triggers:**
- Human types `/statedd-quality-freeze`
- `ingest-bad-event` detects P0
- CTO handoff declares freeze

**Procedure:**
1. Keep `workflow.repo_mode` unchanged and set `current_state.execution_mode.mode: quality_freeze` in `PROJECT_STATE.yaml`
2. Run `skills/quality-gate/SKILL.md` — full pipeline
3. Block all feature work until freeze condition resolved
4. Record the active incident in canonical state, backlog, queue, and evidence; use `docs/ACCEPTANCE_FREEZES.md` only for accepted milestones
5. Generate handoff with freeze status and required fixes

**Failure cases:**
- Quality gate fails during freeze: fix blocking issue, re-run
- Freeze condition unclear: escalate in handoff
- Cannot set quality_freeze execution mode after a permitted Git preflight: remain read-only and report the blocker

**Exit criteria:** Freeze condition resolved, all gates pass, mode returned to `operating` or `template-maintenance`.
