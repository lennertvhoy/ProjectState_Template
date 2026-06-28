---
repo_role: "template_repository"
statedd_mode: "template-maintenance"
repo_mode: "template-maintenance"
statedd_version: "statedd-template-v5"
initialized_on: 2026-04-26
last_updated: 2026-06-28
project: "StateDD_Template"
---

# StateDD v5 — Agent Operating System Constitution

**Purpose:** Minimal constitutional contract for AI agents. Procedural detail lives in `skills/`, `commands/`, and executable gates in `scripts/`.

## Agent Read Order
1. `AGENTS.md` (this file)
2. `STATUS.md`
3. `PROJECT_STATE.yaml`
4. `PROJECT_DNA.yaml`
5. `NEXT_ACTIONS.md`
6. Nearest nested `AGENTS.md` in working directory (nearest wins)

## Invariants (Non-Negotiable)
- No fake completeness — unverified claims = false
- User-facing behavior requires runtime identity proof (not screenshots alone)
- Browser verification required for user-facing closure (Kimi WebBridge preferred; Playwright/fallback: Playwright, agent-native tools, manual)
- Negative searches stay negative: `not found`, `not currently locatable`, `not proven`
- Active queue stays short (`NEXT_ACTIONS.md` only)
- History → `WORKLOG.md` only; live state files stay machine-checkable
- End every session: handoff + hygiene check (`scripts/statedd_handoff.py`, `scripts/check_state_docs.py`)
- Implemented ≠ Validated ≠ Closure-grade ≠ Accepted
- Handoffs are claims until verified by evidence or independent gate
- Quality gates are executable, not prose (`scripts/statedd_quality_gate.py`)
- **Remote Truth Gate:** No implementation may be called complete unless:
  1. Repo identity proven with `pwd` + `git remote -v`
  2. Branch proven with `git branch --show-current`
  3. Changed files proven tracked with `git status --short` and `git ls-files`
  4. Final commit SHA proven with `git rev-parse HEAD`
  5. Remote contains that SHA with `git ls-remote origin <branch>`
  6. GitHub-visible files match claimed deliverables
  7. Final handoff states: `local-only` / `pushed` / `PR opened` / `merged` / `CI verified`
  Without this, every handoff must be labeled: `NOT CLOSURE-GRADE — LOCAL OR UNVERIFIED CLAIM`

## Truth Boundary
The agent must always distinguish:
- Sandbox truth
- Local worktree truth
- Git index truth
- Local commit truth
- Remote branch truth
- GitHub main truth
- CI truth
- Runtime truth
- User-accepted truth

**Invariant:** No state transition may cross a truth boundary without proof.

## Modes
| Mode | Purpose | Repo Role |
|------|---------|-----------|
| `template-maintenance` | Maintain this template repo | Root template repo only |
| `bootstrap` | Discover truth, establish baseline | Downstream repos (initial) |
| `operating` | Steady-state delivery | Downstream repos (steady) |

Downstream repos **never** use `template-maintenance`.

## Subsystems (Load on Demand)
- **Skills** → `skills/<name>/SKILL.md` — executable workflows (load via `/skill-name`)
- **Commands** → `commands/statedd-*.md` — slash-command playbooks (invoke via `/statedd-*`)
- **Gates** → `scripts/statedd_*_gate.py`, `scripts/statedd_*_check.py` — executable quality gates
- **Docs** → `docs/` — reference (FAILURE_TAXONOMY, QUALITY_FIREWALL, INCIDENT_RESPONSE, failure_scans/, quality_gates/, adr/)
- **Schemas** → `schemas/` — machine-checkable contracts (YAML/JSON schemas)
- **Prompts** → `prompts/` — CTO/agent startup prompts, templates

## Human Override
Strong defaults, not a prison. Explicit human override = proceed, record tradeoff, mark `override-approved` in handoff. Decline only if destructive, illegal, unsafe, unrecoverable, or corrupts project truth.

## Hygiene Limits
- `STATUS.md` ≤ 120 lines
- `PROJECT_STATE.yaml` ≤ 900 lines
- `NEXT_ACTIONS.md` active only
- No roadmap prose in structured state
- No closed history in `STATUS.md`

## Handoff Requirements (Every Session)
Run `scripts/statedd_handoff.py` and include: changes, verification, repo path, branch, partial/risky items, git head, serving process/port, rebuild status, clean worktree, evidence refs, absolute evidence paths, next action, CTO-pasteable handoff text.