---
command: "statedd-close-slice"
gate_level: 2
evidence_max: 8
cheapest_proof: "Authoritative local quality gate plus exact-head remote finalizer"
escalate_when: "Release gate requires level 3 with CI proof"
description: "Execute the close-slice skill: run quality gates, update state, freeze acceptance"
---

# /statedd-close-slice — Close Implementation Slice

**When to use:** After implementation is complete, before declaring a slice closure-grade.

**Triggers:**
- Human types `/statedd-close-slice`
- CTO handoff requests slice closure
- Quality freeze initiated

**Procedure (delegates to `skills/close-slice/SKILL.md`):**
1. Run `skills/quality-gate/SKILL.md` once through the authoritative quality-gate entrypoint.
2. If the local gate passes:
   - Update `PROJECT_STATE.yaml` to `validated_local_remote_pending` (or an
     equivalent closure-candidate state), never completion
   - Keep the slice active in `BACKLOG.md` until exact-head remote proof exists
   - Append the local validation boundary to `WORKLOG.md` without calling it closed
   - Update `docs/ACCEPTANCE_FREEZES.md` only after actual human acceptance
   - Commit the implementation proof, then commit only state/evidence finalization metadata
   - Push and open/update the PR without merging
   - Wait for CI on the exact final head
   - Run `scripts/statedd_remote_closure_finalizer.py` with the PR and evidence folder
   - Run `scripts/statedd_handoff.py` for the final handoff
   - Treat the external finalizer receipt as exact-head remote truth. Any later
     in-repo `done`/CI-verified state update creates a new head and needs its own CI
     and finalizer proof.
3. If any local or remote gate fails:
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

**Exit criteria:** Local gate and exact-head remote finalizer pass, state/evidence agree, and the handoff reports every truth boundary separately.
