# ADR-0003: Outcome-first core with an opt-in hardened overlay

**Status:** accepted
**Date:** 2026-09-04
**Author:** human-directed agent

## Context

ProjectState's earlier default combined current state, status prose, queues,
architecture state, history, evidence ledgers, Git closure machinery, and fixed
budgets. Those controls could all agree while a real user journey failed. They
also gave an implementing agent too many ways to amend the machinery judging its
own work.

## Decision

The default profile is `core`. Its canonical coordination surface is:

- `PROJECT.md` for the human-owned user, outcome, scope, non-goals, and durable constraints;
- `STATE.yaml` for one current slice, its primary journey, blockers, risks, and exact next action;
- `AGENTS.md` for authority, stop-lines, and workflow;
- `evidence/<slice-id>/summary.md` for bounded proof and limitations.

One dependency-free outcome gate validates this surface. It makes the primary
journey dominant, requires simplification after two evidenced failures at the
same boundary, and applies exposure-aware risk stop-lines. It never executes a
command merely because repository text names it.

`hardened` is explicit opt-in policy. Legacy v5 profiles remain available only
as compatibility profiles during migration; they are not the recommendation or
the default.

## Consequences

- New and adopted repos start with materially less coordination state.
- An initial project honestly fails outcome closure until its primary journey has run.
- Product-specific backlog, history, ADR, signing, compliance, and remote-delivery machinery are added only when justified.
- Existing profile consumers can migrate deliberately instead of receiving a destructive rewrite.
- The template repository temporarily retains legacy assets for compatibility, but they are noncanonical for the new core.

## Alternatives Considered

- Soften the old profiles: rejected because overlapping truth surfaces and self-referential gates would remain.
- Delete all legacy machinery immediately: rejected because downstream upgrades need an explicit migration boundary.
- Execute the journey command from `STATE.yaml`: rejected because repository content cannot authorize command execution.

## Related

- Backlog item: [BL-OUTCOME-CORE-001]
- Evidence: `evidence/outcome-core-001/summary.md`
