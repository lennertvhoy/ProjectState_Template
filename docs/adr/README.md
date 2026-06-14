# Architecture Decision Records

Some decisions should not live only in `STATUS.md` or chat history. ADRs keep
long-lived reasoning discoverable while keeping live state files short.

## When To Write An ADR

- Canonical schema owner or import behavior
- Persistence model or major data boundary
- Evidence rules or workflow convention
- No-workaround / no-silent-repair policy
- Major architecture boundary or integration shape

## Format

Use `0000-adr-template.md` as the starting point. Number ADRs sequentially.

## Lifecycle

- ADRs are immutable once accepted. Supersede with a new ADR rather than editing the old one.
- Link ADRs from `PROJECT_DNA.yaml` or relevant evidence READMEs when they justify a decision.
