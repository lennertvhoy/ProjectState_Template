---
alias_for: "projectstate-remote-closure"
gate_level: 2
status: "backward-compat (one migration cycle)"
description: "Legacy alias for /projectstate-remote-closure; invokes the canonical command."
---

# /statedd-remote-closure — Legacy Alias

Backward-compat alias kept for one migration cycle after the StateDD -> ProjectState
rename. Canonical command is [`/projectstate-remote-closure`](projectstate-remote-closure.md);
invoke that directly for new work. This file exists so existing prompts, docs, and
muscle memory referencing `/statedd-remote-closure` continue to route.
