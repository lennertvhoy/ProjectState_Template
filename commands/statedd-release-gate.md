---
command: "statedd-release-gate"
gate_level: 3
evidence_max: 8
cheapest_proof: "All level 2 gates pass plus CI proof"
escalate_when: "Never; this is the heaviest gate"
description: "Final release gate before deployment"
---

# /statedd-release-gate — Release Gate

**When to use:** Before any deployment, release, or user-facing delivery.

**Triggers:**
- Human types `/statedd-release-gate`
- Release checklist reached
- CTO handoff requests release validation

**Procedure:**
1. Run `skills/quality-gate/SKILL.md` — full pipeline
2. Run `skills/release-gate/SKILL.md` — release-specific gate
3. Run `scripts/statedd_runtime_proof.py` — capture deployment runtime
4. Run `scripts/statedd_runtime_truth_check.py` — verify matches
5. Run `scripts/statedd_evidence_type_check.py` — verify release evidence
6. Run `scripts/statedd_remote_closure_finalizer.py` — verify pushed PR/CI state
7. Verify `docs/ACCEPTANCE_FREEZES.md` has all milestones
8. Generate release handoff with:
   - Version/tag
   - Runtime identity
   - Evidence bundle
   - Rollback plan

**Required evidence:**
- All quality gate outputs
- Remote closure finalizer output
- Deployment runtime proof
- Acceptance freezes for all user-facing changes
- Rollback plan documented

**Failure cases:**
- Quality gate fails: fix blocking issue, re-run
- Runtime proof fails: check deployment endpoint
- Runtime truth mismatch: rebuild and re-verify
- Evidence missing: collect before release
- Remote closure not verified: refresh PR body/evidence, wait for CI, fix failures, re-push, re-run
- Acceptance freezes incomplete: add missing entries

**Exit criteria:** All gates pass, remote closure verified, runtime verified, evidence complete, release handoff ready.
