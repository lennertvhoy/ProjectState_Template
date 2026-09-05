# Evidence: outcome-core-001

## Primary journey

- Environment: Linux 7.1.9-arch1-2 x86_64; Python 3.14.7
- Command: `python3 scripts/test_outcome_core.py`
- Result: passed
- Exit code: 0

Default generation and adoption preserve the minimal core. The packaged-product
example actually executes a note-saving CLI: source succeeds, a clean archive
fails on a missing resource, a new interpreter reads the saved failure and next
action, the packaging filter is removed, and the rebuilt archive saves and
restores a note across processes. It also runs with ProjectState files hidden.

## Secondary checks

- Focused regressions: 20 passed, including category-independent reachable-risk
  blocking, bounded risk exceptions, unresolved contract/journey placeholders,
  human rejection, primary-only evidence, malformed status types, symlink
  confinement, non-execution of recorded commands, and profile isolation.
- Before the fixes, the added gate regressions produced 49 failed assertions.
  Afterward all pass; the toy product's expected packaging failure also ran.
- Full compatibility/schema suite: `python3 -m pytest scripts/ schemas/examples -q`
  passed with exit 0.
- Static analysis: `ruff check scripts/projectstate_gate.py scripts/test_outcome_core.py scripts/init_template.py`
  passed with exit 0.
- Legacy conformance: `python3 scripts/projectstate_quality_gate.py --gate-level 2 --conformance --verbose`
  passed with exit 0, including compilation, script/schema tests, repository-wide
  Ruff, state/schema validation, instruction lint, and whitespace checks. Legacy
  metrics and fixed budgets were explicitly reported as noncanonical.
- CI configuration parsed successfully; both jobs execute the focused journey
  before the recorded-evidence gate. Remote CI has not run for this change.

## Artifacts

- `scripts/test_outcome_core.py`: executable packaged-product lesson and gate
  regressions. Synthetic record-consistency fixtures are explicitly identified;
  they are separate from the product-executing example.
- `docs/WORKED_EXAMPLE.md`: teaching walkthrough and limits of its evidence.
- Generated core still has six files: `AGENTS.md`, `PROJECT.md`, `STATE.yaml`,
  `evidence/bootstrap-001/summary.md`, product `README.md`, and the outcome gate.
  Hardened adds only its explicit policy; v5 truth files stay out of both profiles.
- The example's archive, failure output, and recovery output are created in a
  temporary workspace and removed after assertions. Rerun the command to reproduce.

## Limitations

- Human product acceptance is pending.
- The gate validates recorded consistency; it cannot authenticate an approver,
  verify arbitrary prose or command execution, or enforce prose-only hardened policy.
- The handoff test uses a new interpreter, not a new AI agent. It establishes
  recoverable on-disk state, not agent effectiveness or no-template superiority.
- This is local Linux/Python evidence. Windows/WSL, remote branch, PR, CI, merge,
  release, and downstream project migration have not been exercised here.
- Existing v5 scripts and snapshots remain compatibility material. The optional
  maintainer path and worked example make the current core easier to find.
