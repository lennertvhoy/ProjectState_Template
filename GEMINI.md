# GEMINI.md — StateDD Agent Instructions

This file is a compatibility shim for Gemini CLI. The authoritative agent contract is in **AGENTS.md**.

## Quick Reference
- **Read first:** `AGENTS.md` (constitutional contract)
- **Skills:** Load via `/skill-name` (e.g., `/close-slice`)
- **Commands:** Invoke via `/statedd-*` (e.g., `/statedd-close-slice`)
- **Quality gates:** Run `scripts/statedd_quality_gate.py` before closure
- **Handoff:** End every session with `scripts/statedd_handoff.py`

## Mode
This repo operates in `template-maintenance` mode (see AGENTS.md).

## Key Invariants
- No fake completeness
- Browser verification required for user-facing closure
- Negative searches stay negative
- End every session: handoff + hygiene check
- Quality gates are executable, not prose

See `AGENTS.md` for full contract.