# Architecture Decision Records

Some decisions should not live only in `STATE.yaml` or chat history. ADRs keep
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
- Link ADRs from the relevant evidence summary when they justify a decision.

## Records

- [0000](0000-adr-template.md): the template to copy.
- [0001](0001-okf-knowledge-layer.md): OKF as an optional knowledge layer (superseded by 0004).
- [0002](0002-agent-owned-delivery-closure.md): delivery policy once, post-merge identities external (superseded by 0004).
- [0003](0003-outcome-first-core.md): outcome-first core with an opt-in hardened overlay.
- [0004](0004-release-channel-and-legacy-split.md): release channel, and removing v5 from main.
- [0005](0005-host-hooks-keep-the-owners-words.md): the host keeps the owner's words (accepted).
- [0006](0006-journey-receipts-outside-the-repository.md): a journey receipt lives outside the repository (accepted).
- [0007](0007-proof-by-run-moves-on.md): a slice proven by a run moves on, one proven by word waits (accepted).
