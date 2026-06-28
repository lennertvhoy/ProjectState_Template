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
1. Gate level: **3**.
2. Run `skills/quality-gate/SKILL.md` — full pipeline.
3. Run `scripts/statedd_efficiency_check.py --gate-level 3` — efficiency budget check.
4. Run `scripts/statedd_runtime_proof.py` — capture deployment runtime.
5. Run `scripts/statedd_runtime_truth_check.py` — verify matches.
6. Run `scripts/statedd_evidence_type_check.py` — verify release evidence.
7. Verify `docs/ACCEPTANCE_FREEZES.md` has all milestones.
8. Generate release handoff with:
   - Version/tag
   - Runtime identity
   - Evidence bundle
   - Rollback plan
   - Gate level used: 3
   - Efficiency budget result

**Required evidence:**
- All quality gate outputs
- Efficiency check output (exit 0)
- Deployment runtime proof
- Acceptance freezes for all user-facing changes
- Rollback plan documented

**Failure cases:**
- Quality gate fails: fix blocking issue, re-run
- Runtime proof fails: check deployment endpoint
- Runtime truth mismatch: rebuild and re-verify
- Evidence missing: collect before release
- Acceptance freezes incomplete: add missing entries

**Exit criteria:** All gates pass, runtime verified, evidence complete, release handoff ready.