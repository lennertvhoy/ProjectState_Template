# Coding Agent Prompt Guide

When delegating implementation:

- require the agent to read `AGENTS.md` first
- require the agent to confirm a CTO lane exists for non-trivial work; if not, it should ask the user to create one with `prompts/CTO_SESSION_PROMPT.md`
- define non-trivial work as multiple-file changes, architecture/workflow changes, user-facing changes, integrations/migrations/state changes, or work likely to take more than one prompt
- anchor on verified current truth
- define one coherent scope
- forbid overclaiming
- require direct verification
- require evidence for user-facing claims
- require state updates when truth changes
- require a clean worktree and handoff at the end
