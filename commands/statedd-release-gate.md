---
alias_for: "projectstate-release-gate"
gate_level: 3
status: "backward-compat (one migration cycle)"
description: "Legacy alias for /projectstate-release-gate; invokes the canonical command."
---

# /statedd-release-gate — Legacy Alias

Backward-compat alias kept for one migration cycle after the StateDD -> ProjectState
rename. Canonical command is [`/projectstate-release-gate`](projectstate-release-gate.md);
invoke that directly for new work. This file exists so existing prompts, docs, and
muscle memory referencing `/statedd-release-gate` continue to route.
