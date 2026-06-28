---
command: "statedd-close-slice"
description: "Execute the close-slice skill: run quality gates, update state, freeze acceptance"
---

# /statedd-close-slice — Close Implementation Slice

**When to use:** After implementation is complete, before declaring a slice closure-grade.

**Triggers:**
- Human types `/statedd-close-slice`
- CTO handoff requests slice closure
- Quality freeze initiated

**Procedure (delegates to `skills/close-slice/SKILL.md`):**
1. Run `skills/quality-gate/SKILL.md` — full quality gate pipeline
2. If all gates pass:
   - Update `PROJECT_STATE.yaml` with slice completion
   - Update `BACKLOG.md` — mark slice done
   - Append to `WORKLOG.md` — slice summary
   - Update `docs/ACCEPTANCE_FREEZES.md` if user-facing
   - Run `scripts/statedd_handoff.py` for final handoff
3. If any gate fails:
   - Report specific failure
   - Do not close slice
   - Return to implementation

**Required evidence:**
- All quality gate outputs (exit 0)
- Updated state files
- Acceptance freeze entry (if user-facing)
- Handoff text for CTO

**Failure cases:**
- Quality gate fails: fix code/tests, re-run gate
- State update fails: fix YAML/schemas
- Acceptance freeze missing: add entry for user-facing changes
- Handoff generation fails: check handoff script

**Exit criteria:** All gates pass, state updated, handoff ready.