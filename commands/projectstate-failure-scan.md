---
command: "statedd-failure-scan"
gate_level: 1
evidence_max: 2
cheapest_proof: "Copy template, fill failure modes, log reference to EVIDENCE_LOG.md"
escalate_when: "Slice closure requires level 2"
description: "Run a pre-mortem failure scan for risky work"
---

# /statedd-failure-scan — Run Failure Scan

**When to use:** Before any non-trivial slice, architecture change, migration, or when CTO flags risk.

**Triggers:**
- Human types `/statedd-failure-scan`
- CTO handoff requests scan
- Starting new slice from backlog

**Procedure (delegates to `skills/failure-scan/SKILL.md`):**
1. Create scan from `docs/failure_scans/TEMPLATE.md` to `docs/failure_scans/<slice-id>.md`
2. Identify adjacent failure modes, cascading risks, rollback scenarios, unknowns
3. Map each mode to `FAILURE_TAXONOMY.md` classes
4. Define mitigations: detection, prevention, rollback, evidence needed
5. Log in `docs/EVIDENCE_LOG.md`
6. Add review to `NEXT_ACTIONS.md`

**Required inputs:** Slice ID, architecture context, recent incidents.

**Failure cases:**
- Template missing: copy from TEMPLATE.md
- No adjacent failures: record 'none identified'
- Unknown risks: mark as 'unknown' with mitigation 'monitor'

**Exit criteria:** Scan complete per template, all modes classified, mitigations defined, logged.