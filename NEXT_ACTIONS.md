# NEXT_ACTIONS - Active Execution Queue

**Updated At:** 2026-06-29
**Execution Mode:** template-maintenance
**Max Items:** 10

## Active Work

### P0 [BL-BROWSER-002] Integrate a concrete browser automation provider
Owner: coding agent
Next: pick a provider (Kimi WebBridge / Playwright / agent-native) and implement a working browser verification path for user-facing changes
Exit: a user-facing slice can produce a real browser verification artifact and `scripts/statedd_browser_verify.py check` passes

## Queue Rules

- Keep this file short.
- List only active, open work.
- Remove completed items immediately.
- Every active item must reference a backlog ID like `[BL-001]`.
- Include owner, next action, and exit criteria when items exist.
