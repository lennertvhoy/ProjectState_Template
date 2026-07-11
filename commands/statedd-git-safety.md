---
command: "statedd-git-safety"
gate_level: 1
evidence_max: 1
cheapest_proof: "Central preflight exits 0 and its decision matches the requested mode"
escalate_when: "Writable mode is blocked or a read-only latch is active"
description: "Authorize or block repository mutation through one Git safety transaction"
---

# /statedd-git-safety — Git Mutation Preflight

**When to use:** Before any implementation/state mutation in an existing Git repo.

**Procedure (delegates to `skills/git-safety/SKILL.md`):**

1. Select `normal_branch`, `worktree`, `clone`, or `read_only`.
2. Run `python3 scripts/statedd_git_safety_check.py --mode <mode>`.
3. For worktree mode, require both `--worktree-opt-in` and
   `--trusted-local-machine`; containers and independent agents use clones.
4. Treat every nonzero writable-mode result as read-only diagnosis.
5. After repair, rerun with `--restart-session`; it clears the external latch
   only after all ownership, write, fsck, and fetch checks pass.
6. Record JSON output in the slice evidence and validate its schema.

**Never:** automatically run permission repair, destructive reset/clean, garbage
collection, worktree prune, forced worktree removal, or forced branch deletion.

## Failure cases

- Identity/ownership/write/fsck failure: detect it in the JSON report, remain
  read-only, preserve the repo, and attach the report as evidence.
- Fetch failure: keep the external latch active, repair remote access, and rerun
  with `--restart-session`; never continue from stale refs.
- Unsafe worktree request: use an independent clone or obtain explicit
  trusted-local same-identity proof; do not silently fall back to writable mode.

**Exit criteria:** The selected mode is permitted by a schema-valid report, or
the handoff clearly records `read_only` and the blocking evidence.
