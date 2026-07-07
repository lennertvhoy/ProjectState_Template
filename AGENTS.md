---
repo_role: "template_repository"
statedd_mode: "template-maintenance"
repo_mode: "template-maintenance"
statedd_version: "statedd-template-v5"
initialized_on: 2026-04-26
last_updated: 2026-07-07
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
- **Remote Closure Invariant:** A slice is not done until the pushed PR head, PR body, in-repo evidence, closure handoff, and latest GitHub Actions run all agree on the same final head. Local tests are only preflight. Final closure requires GitHub-visible CI success or an explicit `NOT CI-VERIFIED` label.
- **Efficiency Invariant:** StateDD exists to reduce agent confusion and false closure, not to create bureaucracy. Every required file, gate, command, and evidence artifact must justify its cost. Prefer the smallest proof that crosses the relevant truth boundary.
- **Worktree Isolation Invariant:** No non-trivial coding-agent slice may start from an ambiguous or dirty shared worktree unless the dirt is classified and isolated first with `scripts/statedd_worktree_guard.py`.
- **Parallel-Agent Invariant:** Multiple coding agents working concurrently must each use an isolated agent worktree provisioned by `scripts/statedd_agent_worktree.py`. Shared worktrees cannot prove "whose change is whose" at closure; worktree isolation is the default boundary for non-trivial parallel slices.
- **Anti-Brittleness Invariant:** No non-trivial fix or feature slice may pass closure if it only handles observed examples through brittle prompt-, string-, keyword-, fixture-, sleep-, fallback-, or provider-specific behavior without an explicit anti-brittleness review.

## Gate Levels
Use the cheapest gate that honestly proves the current claim.

| Level | Name | When to use | Required proof |
|-------|------|-------------|----------------|
| 0 | Orientation | Starting or resuming | Read `AGENTS.md`, identify mode/current task; no full audit |
| 1 | Edit Loop | Single-file or non-runtime changes | Cheap tests, relevant lint; no evidence bundle unless runtime change |
| 2 | Slice Closure | Closing a slice | Quality gate, closure check, remote truth, evidence type check |
| 3 | Release / Template Migration | Deployment or migration | Full probes, compatibility shims, generated fixture checks, CI proof |

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
- **Skills** → `skills/<name>/SKILL.md` — executable workflows (load via `/skill-name`):
  close-slice, failure-scan, ingest-bad-event, quality-gate, release-gate, runtime-truth
- **Commands** → `commands/statedd-*.md` — slash-command playbooks (invoke via `/statedd-*`):
  statedd-close-slice, statedd-failure-scan, statedd-ingest-bad-event, statedd-quality-freeze, statedd-release-gate, statedd-remote-closure
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
