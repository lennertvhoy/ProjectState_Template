# Coding Agent Prompt Guide

When delegating implementation:

- require the agent to read `AGENTS.md` first
- require the agent to confirm a CTO lane exists for non-trivial work; if not, it should ask the user to create one with `prompts/CTO_SESSION_PROMPT.md`
- define non-trivial work as multiple-file changes, architecture/workflow changes, user-facing changes, integrations/migrations/state changes, or work likely to take more than one prompt
- assume the coding-agent session is fresh unless the repo state files preserve the needed context
- anchor on verified current truth
- define one coherent scope
- include the current verified state and explicit unknowns when they matter
- include the exit condition for the task
- forbid overclaiming
- require direct verification
- require evidence for user-facing claims
- require state updates when truth changes
- require a clean worktree and handoff at the end
- require the final handoff to be suitable for direct paste into the CTO chat

Minimum useful handoff shape:

1. Current verified truth
2. Scope for this step only
3. Constraints and things to avoid
4. Verification commands or evidence required
5. What to update if truth changes
6. What changed, what remains risky, and the next recommended move
