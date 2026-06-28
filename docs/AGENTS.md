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
1. **Read before acting** — Consult `FAILURE_TAXONOMY.md` and `QUALITY_FIREWALL.md` before closure
2. **Write to evidence, not docs** — `EVIDENCE_LOG.md` and `docs/incidents/` are append-only; do not edit history
3. **Failure scans are mandatory** — Before risky work, create `docs/failure_scans/<slice-id>.md` from TEMPLATE
4. **ADRs for architecture decisions** — Create `docs/adr/NNN-title.md` for long-lived reasoning
5. **Quality gates are project-specific** — `docs/quality_gates/` is populated per downstream project
6. **Do not bloat docs** — Reference only; procedural detail goes in skills/commands/scripts

## Hygiene
- `docs/incidents/` and `docs/failure_scans/` are append-only
- `EVIDENCE_LOG.md` append-only
- `ACCEPTANCE_FREEZES.md` append-only
- Max 1 ADR per architecture decision
- Cross-link from skills/commands to relevant docs

## Human Override
Explicit human direction overrides doc workflows. Record in handoff.