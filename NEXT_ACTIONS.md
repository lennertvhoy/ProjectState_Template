# NEXT_ACTIONS - Active Execution Queue

**Updated At:** 2026-06-28
**Execution Mode:** template-maintenance
**Max Items:** 10

## Active Work

### P1 [BL-BROWSER-002] Integrate a concrete browser automation provider using the provider-agnostic contract when a provider is available and permitted
Owner: human product owner + coding agent
Next: do not add a hard dependency; add a concrete provider driver (Kimi WebBridge, Playwright, agent-native, existing E2E, or custom) only when the project/agent has one available and the human permits setup
Exit: user-facing changes can be captured automatically into browser_verification.json artifacts while preserving provider-agnostic audit acceptance

## Queue Rules

- Keep this file short.
- List only active, open work.
- Remove completed items immediately.
- Every active item must reference a backlog ID like `[BL-001]`.
- Include owner, next action, and exit criteria when items exist.
