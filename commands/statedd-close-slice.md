---
alias_for: "projectstate-close-slice"
gate_level: 2
status: "backward-compat (one migration cycle)"
description: "Legacy alias for /projectstate-close-slice; invokes the canonical command."
---

# /statedd-close-slice — Legacy Alias

Backward-compat alias kept for one migration cycle after the StateDD -> ProjectState
rename. Canonical command is [`/projectstate-close-slice`](projectstate-close-slice.md);
invoke that directly for new work. This file exists so existing prompts, docs, and
muscle memory referencing `/statedd-close-slice` continue to route.
