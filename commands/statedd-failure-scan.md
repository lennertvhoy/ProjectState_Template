---
alias_for: "projectstate-failure-scan"
gate_level: 1
status: "backward-compat (one migration cycle)"
description: "Legacy alias for /projectstate-failure-scan; invokes the canonical command."
---

# /statedd-failure-scan — Legacy Alias

Backward-compat alias kept for one migration cycle after the StateDD -> ProjectState
rename. Canonical command is [`/projectstate-failure-scan`](projectstate-failure-scan.md);
invoke that directly for new work. This file exists so existing prompts, docs, and
muscle memory referencing `/statedd-failure-scan` continue to route.
