# Evidence: outcome-core-001

## Primary journey

- Environment: Linux 7.1.9-arch1-2 x86_64; Python 3.14.7
- Command: `python3 scripts/test_outcome_core.py`
- Result: passed
- Exit code: 0

## Secondary checks

- Focused tests: 12 passed; default generation, adoption, dry-run safety, journey precedence,
  non-execution of recorded commands, symlink confinement, governance-field
  rejection, explicit human-acceptance enforcement, simplification, and risk
  exposure were exercised.
- Full compatibility and schema suite: `python3 -m pytest scripts/ schemas/examples -q` passed,
  including the root outcome-closure assertion.
- Static analysis: Ruff passed for the new gate and regressions.
- Legacy Level-2 conformance: passed; it explicitly reported profile metrics
  and fixed budgets as noncanonical compatibility evidence, not closure gates.

## Artifacts

- Generated core projects contained only `AGENTS.md`, `PROJECT.md`, `STATE.yaml`,
  `evidence/bootstrap-001/summary.md`, product `README.md`, and the outcome gate.
- Informational footprint from the same checkout: core generated 6 files / 29,908
  bytes; the v5 `minimal` compatibility profile generated 41 files / 424,972
  bytes. These measurements are evidence, not fixed acceptance budgets.
- Initial generated gate returned `OUTCOME NOT VALIDATED`; the same generated
  project passed only after its project contract, real journey result, evidence,
  and blocker state were updated.
- Anti-brittleness review: closure depends on typed state and path/result
  invariants, not prompt keywords, provider names, sleeps, or observed fixture text.

## Limitations

- Human product acceptance is pending.
- Remote branch, pull request, CI, merge, and release state are not proven by this local evidence.
- v5 profiles and root snapshots remain only for deliberate compatibility; their
  later removal is not part of this slice.
