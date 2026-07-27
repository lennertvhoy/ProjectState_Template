# BL-PARALLEL-001 — Shared-Worktree Panic with Concurrent Agents

**Failure class:** Concurrent coding agents collide on the same git worktree/branch.

**Symptoms**

- `projectstate_worktree_guard.py` reports another agent's uncommitted files as ambiguous dirt.
- `projectstate_handoff.py` cannot distinguish the current agent's changes from another agent's changes.
- `projectstate_audit.py` fails closure-grade on a dirty worktree even when the dirt belongs to the current slice.
- `projectstate_remote_closure_finalizer.py` races when another agent pushes to the same branch between checks.
- Two agents accidentally check out or claim the same branch name.
- Evidence folder selection by `st_mtime` picks up artifacts written by a different agent.

**Root cause**

ProjectState's single-agent assumptions break down when multiple agents share the default
worktree or branch. Git cannot reliably attribute uncommitted changes to a specific
agent, and there is no reservation system to prevent branch/worktree collisions.

**Mitigation**

- Use `scripts/projectstate_agent_worktree.py start --slice-id BL-XXX` to provision a
  private branch + worktree + reservation ref for each non-trivial slice.
- Existing scripts auto-detect `.projectstate/agent.context` and relax single-agent
  checks accordingly.
- Reservation refs under `refs/projectstate/reservations/` prevent silent double-claiming.
- Git lock detection (`index.lock`, `config.lock`) fails fast with a clear message
  instead of leaving corrupt state.
- Run `scripts/projectstate_agent_worktree.py list` to inspect active agent worktrees,
  reservations, and lock files.
- Run `scripts/projectstate_agent_worktree.py cleanup --stale-only` to find abandoned
  reservations, then `cleanup --force <branch>` to remove them.

**Detection**

- Multiple linked worktrees under `.worktrees/` with different `agent.context` files.
- Reservation refs exist but the corresponding worktree is missing or merged.
- CI or agent logs show "Another git operation holds ..." or "Reservation ref already exists".

**References**

- Design spec: `docs/superpowers/specs/2026-07-07-parallel-agent-worktree-orchestrator-design.md`
- Orchestrator: `scripts/projectstate_agent_worktree.py`
- Constitution: `AGENTS.md` Parallel-Agent Invariant
