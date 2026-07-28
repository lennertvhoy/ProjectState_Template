---
alias_for: "projectstate-quality-freeze"
gate_level: 2
status: "backward-compat (one migration cycle)"
description: "Legacy alias for /projectstate-quality-freeze; invokes the canonical command."
---

# /statedd-quality-freeze — Legacy Alias

Backward-compat alias kept for one migration cycle after the StateDD -> ProjectState
rename. Canonical command is [`/projectstate-quality-freeze`](projectstate-quality-freeze.md);
invoke that directly for new work. This file exists so existing prompts, docs, and
muscle memory referencing `/statedd-quality-freeze` continue to route.
