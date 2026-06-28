---
command: "statedd-release-gate"
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
2. Run `scripts/statedd_runtime_proof.py` — capture deployment runtime
3. Run `scripts/statedd_runtime_truth_check.py` — verify matches
4. Run `scripts/statedd_evidence_type_check.py` — verify release evidence
5. Verify `docs/ACCEPTANCE_FREEZES.md` has all milestones
6. Generate release handoff with:
   - Version/tag
   - Runtime identity
   - Evidence bundle
   - Rollback plan

**Required evidence:**
- All quality gate outputs
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