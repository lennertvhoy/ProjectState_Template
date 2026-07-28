---
command: "projectstate-quality-freeze"
gate_level: 2
evidence_max: 8
cheapest_proof: "Quality gate exits 0 and freeze is documented in ACCEPTANCE_FREEZES.md"
escalate_when: "Release requires level 3 with CI proof"
description: "Enter quality freeze mode and run full quality gate"
---

# /projectstate-quality-freeze — Quality Freeze

**When to use:** P0 product behavior broken, critical regression, or CTO mandates freeze.

**Triggers:**
- Human types `/projectstate-quality-freeze`
- `ingest-bad-event` detects P0
- CTO handoff declares freeze

**Procedure:**
1. Set `repo_mode: quality_freeze` in `PROJECT_STATE.yaml`
2. Run `skills/quality-gate/SKILL.md` — full pipeline
3. Block all feature work until freeze condition resolved
4. Document freeze in `docs/ACCEPTANCE_FREEZES.md`
5. Generate handoff with freeze status and required fixes

**Failure cases:**
- Quality gate fails during freeze: fix blocking issue, re-run
- Freeze condition unclear: escalate in handoff
- Cannot set quality_freeze mode: check PROJECT_STATE.yaml permissions

**Exit criteria:** Freeze condition resolved, all gates pass, mode returned to `operating` or `template-maintenance`.