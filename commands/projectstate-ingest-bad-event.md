---
command: "statedd-ingest-bad-event"
gate_level: 1
evidence_max: 3
cheapest_proof: "Incident file + failure scan + backlog entry + handoff all exist"
escalate_when: "P0 triggers level 2 quality freeze"
description: "Ingest a bad event as a durable incident with failure scan"
---

# /statedd-ingest-bad-event — Ingest Bad Event

**When to use:** Any unhandled error, crash, bug report, or mysterious behavior.

**Triggers:**
- Human types `/statedd-ingest-bad-event`
- Agent observes unhandled failure
- Test reveals regression not in backlog

**Procedure (delegates to `skills/ingest-bad-event/SKILL.md`):**
1. Prompt for event details (what, when, where, symptoms)
2. Create incident in `docs/incidents/YYYYMMDD-HHMMSS-<slug>.md`
3. Classify severity per `FAILURE_TAXONOMY.md`
4. Create failure scan in `docs/failure_scans/<incident-id>.md`
5. Add to `BACKLOG.md` with `BL-<id>`
6. Update `docs/EVIDENCE_LOG.md`
7. If P0: set `quality_freeze` in `PROJECT_STATE.yaml`
8. Generate handoff with next steps

**Required inputs:** Event description, symptoms, severity guess.

**Failure cases:**
- Incident file creation fails: check permissions/path, create parent dirs
- Severity unclear: default to P2, escalate in handoff
- No adjacent failures: record 'none identified' in scan

**Exit criteria:** Incident recorded, failure scan complete, backlog updated, handoff ready.