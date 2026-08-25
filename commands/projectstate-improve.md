---
command: "projectstate-improve"
gate_level: 2
evidence_max: 1
cheapest_proof: "Each implemented slice has passing level-2 gate evidence plus a final improvement ledger separating implemented, validated, unvalidated, and blocked work"
escalate_when: "Work would leave the autonomy ladder, or stop condition B (genuine blocker) is reached"
description: "Run the autonomous improvement, repair, and evolution loop inside ProjectState authority bounds"
---

# /projectstate-improve — Autonomous Improvement Loop

**When to use:** When the human or CTO lane delegates a bounded improvement run:
repair defects, close validation gaps, fix documentation rot, remove developer
friction, complete implied capabilities, or simplify — continuing across slices
while high-confidence, high-value candidates remain.

**Triggers:**

- An "improve / repair / harden this repository" mandate with local reversible scope
- Post-closure re-inspection that surfaced another ranked candidate
- Resuming an interrupted improve run from its WORKLOG entry

**Procedure (delegates to `skills/improve/SKILL.md`):**

1. Preflight: doctor, Git safety on a private slice branch, freeze scope,
   ladder limits recorded.
2. Source-of-truth pass; reconcile documentation against implementation.
3. Assessment sweep; rank candidates by value x confidence x reach x risk
   reduction divided by cost and complexity; label FACT versus ASSUMPTION.
4. Select the top eligible candidate; bind a stable BL ID; write the slice
   contract and, for risky work, a failure scan.
5. Implement the complete vertical slice; prefer subtraction; protect
   unrelated work.
6. Validate narrowest first, then broader gates; then attempt falsification.
7. Close via `/projectstate-close-slice`; loop back to step 4 while ranked
   candidates remain.
8. Stop at meaningful local closure or a genuine blocker; emit the final
   report via `scripts/projectstate_handoff.py`.

**Autonomy ladder enforced during this command:**

- L0 inspect/report/orient: always allowed.
- L1 local reversible inspectable changes (fixes, tests, refactors, docs, DX):
  autonomous inside this explicitly invoked run; record decisions; ordinary
  engineering judgment needs no permission request.
- L2 branch/commit/push/PR/merge: confirmed delivery policy only.
- L3 spending money, publishing, deleting unique external data, contacting
  people, rotating credentials, deploying: prepare up to the boundary and name
  the exact action requiring human authorization.
- L4 force-push, history rewrite, delivery-mode change, product acceptance,
  canonical-truth rewrite: human only.

**Never:** bypass or weaken a gate to reach green, reset or discard unrelated or
dirty work, expand into speculative features, silently cross a truth boundary,
or perform L3/L4 actions without explicit authorization.

## Failure cases

- Gate failure mid-loop: repair the cause and rerun the same gate; partial work
  stays honestly partial.
- Genuine blocker: record claim state `blocked`, finish everything possible,
  hand off naming the exact external action required.
- Scope creep: park the candidate in BACKLOG with ranking rationale instead of
  implementing it.

**Required evidence:**

- Per-slice evidence pack including quality gate output
- Run notes with the ranked candidate list and decision records
- Final handoff separating implemented / validated / unvalidated / blocked

**Exit criteria:** The run stopped at meaningful local closure or an honestly
recorded blocker; every closure-grade claim has matching gate evidence; queue
and state files reflect the true remaining work.
