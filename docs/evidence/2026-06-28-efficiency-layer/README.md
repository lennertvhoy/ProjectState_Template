# Evidence: StateDD v5 Efficiency Invariant and gate levels

**Slice:** [BL-EFFICIENCY-001] Add the StateDD v5 Efficiency Invariant: tiered gate levels, EFFICIENCY_BUDGET.yaml, scripts/statedd_efficiency_check.py, bloat regression fixture, and gate wiring.  
**Date:** 2026-06-28  
**Agent:** coding-agent  
**Branch:** efficiency-layer  
**HEAD:** 43ac1297550cf606d87c413db65c7323cb975b29

## Claims

- Claim: StateDD v5 has a hard Efficiency Invariant and tiered gate levels in the root constitution.
  Evidence: `AGENTS.md`
  Evidence type: state_update

- Claim: Instruction, state, evidence, and gate budgets are declared in a single machine-checkable file.
  Evidence: `EFFICIENCY_BUDGET.yaml`
  Evidence type: implementation

- Claim: An executable checker enforces the budget and fails on bloat overcorrection.
  Evidence: `scripts/statedd_efficiency_check.py`, `scripts/test_efficiency_check.py`, `command_outputs/efficiency_check.txt`, `command_outputs/test_efficiency_check.txt`
  Evidence type: test

- Claim: A regression fixture proves the checker catches the "fix false closure by adding excessive files/rules" failure mode.
  Evidence: `fixtures/efficiency_bloat_overcorrection/`, `command_outputs/bloat_fixture_check.txt`
  Evidence type: test

- Claim: Quality, closure, and release gates run the efficiency check at the correct gate level.
  Evidence: `scripts/statedd_quality_gate.py`, `scripts/statedd_closure_check.py`, `commands/statedd-release-gate.md`
  Evidence type: implementation

- Claim: Every skill and command declares its gate level, evidence maximum, cheapest proof, and escalation rule.
  Evidence: `skills/*/SKILL.md`, `commands/*.md`
  Evidence type: implementation

## Verification Log

| Check | Command / Path | Result |
| --- | --- | --- |
| efficiency check root gate level 2 | `python scripts/statedd_efficiency_check.py --gate-level 2` | pass |
| efficiency checker tests | `python -m pytest scripts/test_efficiency_check.py -v` | 10 passed |
| bloat fixture regression | `python scripts/statedd_efficiency_check.py --gate-level 2 --root fixtures/efficiency_bloat_overcorrection` | fail as expected |
| closure check with remote truth | `python scripts/statedd_closure_check.py --gate-level 2 --claimed-files ...` | closure-grade, GitHub-verified |
| remote truth | `python scripts/statedd_remote_truth_check.py --claim ...` | pass |

## Closure State

- Implemented: yes
- Validated: yes
- Global quality gates passed: efficiency check passes; full quality gate blocked by pre-existing v4/v5 baseline failures in `init_template.py`
- Closure-grade: yes after final commit and remote truth verification
- Accepted: pending

## Human Override

- Human override used: no

## Risks / What Remains Partial

- Full `statedd_quality_gate.py` is blocked by pre-existing template-version baseline failures (`init_template.py` still emits `statedd-template-v4`). These failures are unrelated to the efficiency layer.
- `runtime_identity.json` was generated with `--no-runtime-required` because this slice changes docs, scripts, and templates only.
