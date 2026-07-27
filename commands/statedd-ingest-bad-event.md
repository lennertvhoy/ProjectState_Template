---
alias_for: "projectstate-ingest-bad-event"
gate_level: 1
status: "backward-compat (one migration cycle)"
description: "Legacy alias for /projectstate-ingest-bad-event; invokes the canonical command."
---

# /statedd-ingest-bad-event — Legacy Alias

Backward-compat alias kept for one migration cycle after the StateDD -> ProjectState
rename. Canonical command is [`/projectstate-ingest-bad-event`](projectstate-ingest-bad-event.md);
invoke that directly for new work. This file exists so existing prompts, docs, and
muscle memory referencing `/statedd-ingest-bad-event` continue to route.
