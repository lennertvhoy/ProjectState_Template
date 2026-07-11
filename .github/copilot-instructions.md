# GitHub Copilot Instructions — StateDD Template

This file is auto-generated from the StateDD constitutional contract. The authoritative source is **AGENTS.md**.

## Repository Role
- `repo_role: template_repository` — This is the StateDD template repository
- Downstream repos use `repo_role: downstream_project`

## Agent Behavior

### Read Order
Read `AGENTS.md` first and follow its declared task-scoped read order. This file
is only a compatibility summary and does not define a second read order.

### Invariants (Non-Negotiable)
- No fake completeness — unverified claims = false
- User-facing behavior requires runtime identity proof (not screenshots alone)
- Browser verification required for user-facing closure
- Negative searches stay negative: `not found`, `not currently locatable`, `not proven`
- Active queue stays short (`NEXT_ACTIONS.md` only)
- History → `WORKLOG.md` only; live state files stay machine-checkable
- End every session: handoff + hygiene check (`scripts/statedd_handoff.py`, `scripts/check_state_docs.py`)
- Implemented ≠ Validated ≠ Closure-grade ≠ Accepted
- Handoffs are claims until verified by evidence or independent gate
- Quality gates are executable, not prose (`scripts/statedd_quality_gate.py`)

### Modes
| Mode | Purpose |
|------|---------|
| `template-maintenance` | Maintain this template repo (root only) |
| `bootstrap` | Discover truth, establish baseline (downstream initial) |
| `operating` | Steady-state delivery (downstream steady) |

**Downstream repos never use `template-maintenance`.**

### Subsystems (Load on Demand)
- **Skills** → `skills/<name>/SKILL.md` — executable workflows (invoke via `/skill-name`)
- **Commands** → `commands/statedd-*.md` — slash-command playbooks (invoke via `/statedd-*`)
- **Gates** → `scripts/statedd_*_gate.py`, `scripts/statedd_*_check.py` — executable quality gates
- **Docs** → `docs/` — reference (FAILURE_TAXONOMY, QUALITY_FIREWALL, INCIDENT_RESPONSE)
- **Schemas** → `schemas/` — machine-checkable contracts (YAML/JSON)
- **Prompts** → `prompts/` — CTO/agent startup prompts, templates

### Human Override
Strong defaults, not a prison. Explicit human override = proceed, record tradeoff, mark `override-approved` in handoff.

### Hygiene Limits
- `STATUS.md` ≤ 120 lines
- `PROJECT_STATE.yaml` ≤ 900 lines
- `NEXT_ACTIONS.md` active only
- No roadmap prose in structured state
- No closed history in `STATUS.md`

### Handoff Requirements (Every Session)
Run `scripts/statedd_handoff.py` and include: changes, verification, repo path, branch, partial/risky items, git head, serving process/port, rebuild status, clean worktree, evidence refs, absolute evidence paths, next action, CTO-pasteable handoff text.

## Skills Available
- `/close-slice` — Execute full slice closure
- `/ingest-bad-event` — Record and handle failures
- `/failure-scan` — Pre-mortem failure scan
- `/runtime-truth` — Capture and verify runtime identity
- `/quality-gate` — Execute full quality gate pipeline

## Commands Available
- `/statedd-close-slice`
- `/statedd-ingest-bad-event`
- `/statedd-failure-scan`
- `/statedd-quality-freeze`
- `/statedd-release-gate`

## Quality Gates (Must Pass Before Closure)
- `scripts/statedd_quality_gate.py` — Tests, static analysis, state, evidence
- `scripts/statedd_instruction_lint.py` — Config smell detection
- `scripts/statedd_closure_check.py` — Closure criteria validation
- `scripts/statedd_runtime_truth_check.py` — Runtime identity verification
- `scripts/statedd_evidence_type_check.py` — Evidence type validation
- `scripts/check_state_docs.py` — Doc hygiene and bootstrap gate

See `AGENTS.md` for full constitutional contract.
