# Evidence: StateDD v5 Efficiency Layer

**Slice:** BL-EFFICIENCY-001  
**Date:** 2026-06-28  
**Type:** template_maintenance_capability  
**Claim:** StateDD v5 now has a hard Efficiency Invariant, tiered gate levels, an executable efficiency budget, and bloat regression fixture.

## What this proves

- `command_outputs/efficiency_check.txt` — `scripts/statedd_efficiency_check.py --gate-level 2` passes on the template root.
- `command_outputs/test_efficiency_check.txt` — all 10 efficiency checker tests pass.
- `command_outputs/bloat_fixture_check.txt` — the bloat-overcorrection fixture fails the efficiency check as expected (oversized instructions, missing gate levels, bloated queue, oversized evidence bundle).

## Artifacts

- `AGENTS.md` — Efficiency Invariant and Gate Levels added.
- `EFFICIENCY_BUDGET.yaml` — hard budgets for instructions, state, evidence, and gates.
- `scripts/statedd_efficiency_check.py` — executable checker.
- `scripts/test_efficiency_check.py` — regression tests.
- `fixtures/efficiency_bloat_overcorrection/` — bloat regression fixture.
- `scripts/statedd_quality_gate.py` and `scripts/statedd_closure_check.py` — wired to run the efficiency check.
- `commands/statedd-release-gate.md` — includes efficiency check at gate level 3.
- All skills and commands now declare `gate_level`, `evidence_max`, `cheapest_proof`, and `escalate_when`.

## Limits

- Full `statedd_quality_gate.py` and `statedd_closure_check.py` are blocked by pre-existing template-version baseline failures (`init_template.py` still emits `statedd-template-v4`). These are unrelated to the efficiency layer.
- Closure check cannot be closure-grade until the branch is pushed to origin and `runtime_identity.json` is generated for a runtime-required claim.
