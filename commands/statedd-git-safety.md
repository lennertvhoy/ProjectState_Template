---
alias_for: "projectstate-git-safety"
gate_level: 1
status: "backward-compat (one migration cycle)"
description: "Legacy alias for /projectstate-git-safety; invokes the canonical command."
---

# /statedd-git-safety — Legacy Alias

Backward-compat alias kept for one migration cycle after the StateDD -> ProjectState
rename. Canonical command is [`/projectstate-git-safety`](projectstate-git-safety.md);
invoke that directly for new work. This file exists so existing prompts, docs, and
muscle memory referencing `/statedd-git-safety` continue to route.
