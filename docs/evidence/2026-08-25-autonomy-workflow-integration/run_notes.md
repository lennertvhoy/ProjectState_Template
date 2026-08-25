# Run Notes — BL-AUTONOMY-001 autonomous improvement workflow integration

**Run:** /projectstate-improve (first production run of the loop being added)
**Branch:** bl-autonomy-001-improve-workflow (from main @ 11e2f87)
**Date:** 2026-08-25

## Source-of-truth pass

- Canonical contract: `AGENTS.md` (constitution), `PROJECT_STATE.yaml` (live
  truth), `PROJECT_DNA.yaml` (slow blueprint), `VERSION` (spec version).
- Reconciled docs against implementation: found subsystem enumerations in
  root `AGENTS.md` and `.github/copilot-instructions.md` that disagreed with
  the actual `skills/` and `commands/` trees (FACT, verified by listing).
- Found `.github/copilot-instructions.md:3` claiming to be auto-generated
  while no generator exists in-repo (FACT); replaced with an honest mirror
  statement.
- Found `docs/ACCEPTANCE_FREEZES.md` referencing a release-notes filename
  that never existed (`RELEASE_NOTES_projectstate-template-v4.md` vs the real
  `RELEASE_NOTES_statedd-template-v4.md`, FACT). NOT repaired: the ledger is
  append-only governance history; recorded here instead.

## Assessment sweep (ranked)

| # | Candidate | Class | Value/confidence | Decision |
|---|-----------|-------|------------------|----------|
| 1 | Integrate autonomous improvement loop (skill + command + ladder hook) | owner mandate, measured improvement | high/high | implemented this slice |
| 2 | Enumeration drift: git-safety skill missing from AGENTS.md; copilot lists stale | doc rot breaking agent routing | high/high | implemented this slice |
| 3 | Beginners-doc contradiction: "agent should not choose next slice" vs delegated improve runs | doc rot causing false conflict | medium/high | implemented this slice |
| 4 | prompts catalog missing NEW_PROJECT_FROM_URL.md | doc rot | medium/high | implemented this slice |
| 5 | ACCEPTANCE_FREEZES dangling v4 release-notes filename | historical ledger cosmetics | low/high | parked: append-only ledger, errata not justified yet |
| 6 | CHANGELOG rename date 2026-07-27 vs merge commit dated 2026-07-28 | unverifiable locally | low/low | parked: PR-open date may legitimately differ |
| 7 | Ship improve skill/command downstream via profiles/catalog.json asset set | capability propagation | medium/high | parked as follow-up: requires catalog version bump plus profile-metrics regeneration against the merged commit; correct second slice |

Labels: items 1–5 FACT (verified by direct inspection); item 6 UNKNOWN.

## Decisions

- Named the workflow `improve` / `/projectstate-improve`: terse verb matching
  existing skills; "evolve" rejected as inviting speculative rewrites.
- No new mode, schema, or gate: autonomy compliance stays behavioral and is
  proven by existing closure gates (Efficiency Invariant).
- The mandate text was distilled into the command/skill rather than stored
  verbatim in `prompts/`, honoring no_duplicate_instruction_files.
- AGENTS.md edits are net-negative in lines: Remote Truth Gate and Truth
  Boundary compressed without semantic loss to admit the Autonomy Ladder.
- Startup prompts left untouched this slice: they are generated into
  downstream repos and would force profile-metrics regeneration; the command
  file already serves as the paste-ready entry point.

## Falsification attempts

- Ran instruction lint hunting for conflicting-instruction ERRORs between the
  new "autonomous inside an invoked run" wording and the existing
  "only the user ... may instruct" invariant: none fired (the ladder is
  conditioned on explicit invocation, same authority channel as any skill).
- Verified AGENTS.md sits exactly at its 110-line budget after edits.
- Verified the new SKILL.md/command satisfy every structural gate: gate_level,
  failure cases, step caps, size budgets, reference corpus.
- Ran the full CI-parity level-2 conformance gate including the complete test
  suite, profile generation for every profile, ruff, hygiene, schemas, and
  metrics reproduction: pass.
