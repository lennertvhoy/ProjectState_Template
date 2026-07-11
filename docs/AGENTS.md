---
scope: "docs"
purpose: "StateDD reference documentation, failure taxonomy, quality gates, incidents"
---

# Docs Agent Instructions

## Scope
This directory holds reference documentation for StateDD: failure taxonomy, quality firewall, incident response, failure scans, quality gates, and ADRs. These are **read-only reference** for agents — not executable.

## Document Catalog
| File | Purpose |
|------|---------|
| `FAILURE_TAXONOMY.md` | Severity/class vocabulary for bad events |
| `QUALITY_FIREWALL.md` | Reusable closure-gate contract |
| `INCIDENT_RESPONSE.md` | Standard bad-event ingestion workflow |
| `failure_scans/TEMPLATE.md` | Pre-mortem template for risky work |
| `quality_gates/README.md` | Downstream project-specific gate index |
| `adr/` | Architecture Decision Records |
| `EVIDENCE_LOG.md` | Append-only proof ledger |
| `ACCEPTANCE_FREEZES.md` | Accepted user-facing milestones |
| `BROWSER_VERIFICATION.md` | Browser verification standards |
| `UPGRADING.md` | Version upgrade guide |
| `WORKFLOW_FOR_BEGINNERS.md` | New user onboarding |
| `ADOPTION_PROFILES.md` | Project adoption patterns |
| `BOOTSTRAP_QUALITY.md` | Bootstrap quality standards |
| `GETTING_STARTED_5_MIN.md` | Quick start |
| `QUICK_COMMANDS.md` | Command reference |

## Agent Rules for Docs

Read `AGENTS.md` first and follow its declared task-scoped read order. Consult
the relevant reference only when the active task requires it. Write evidence to
the append-only ledgers, create failure scans before risky work, use ADRs for
long-lived architecture decisions, and keep executable procedure in
skills/commands/scripts.

## Hygiene
- `docs/incidents/` and `docs/failure_scans/` are append-only
- `EVIDENCE_LOG.md` append-only
- `ACCEPTANCE_FREEZES.md` append-only
- Max 1 ADR per architecture decision
- Cross-link from skills/commands to relevant docs

## Human Override
Explicit human direction overrides doc workflows. Record in handoff.
