# Evidence: Workflows asset set ships the improve workflow downstream

**Slice:** [BL-WORKFLOW-CATALOG-001] Ship improve workflow via catalog
**Date:** 2026-08-25
**Agent:** opencode integration agent (ox-alpha)
**Branch:** `bl-workflows-catalog-001`
**HEAD:** 67a4f53a153502b4a24b8acd0db715d569fb2593
**Proof head:** 67a4f53a153502b4a24b8acd0db715d569fb2593

## Claims

- Claim: A non-optional `workflows` asset set carries `skills/improve/SKILL.md`
  and `commands/projectstate-improve.md`, resolved by all four profiles.
  Evidence: `resolution.json`
  Evidence type: implementation, test
- Claim: Generated downstream gates stay within declared context budgets with
  the two additional workflow files installed (minimal/solo/team/regulated).
  Evidence: `resolution.json`
  Evidence type: test, generated_fixture
- Claim: The full CI-parity level-2 conformance gate passes at the proof tree,
  including profile generation for every profile and metrics reproduction.
  Evidence: `quality_gate_output.txt`, `runtime_identity.json`
  Evidence type: test

## Failure Scan

- Required: no
- Path: not applicable; declarative catalog/budget change with generated-fixture
  coverage in the authoritative gate.
- Known bad event considered: downstream footprint overflow after shipping new
  assets; prevented by measured budget bumps recorded in EFFICIENCY_BUDGET.yaml.

## Worktree Dirty File Classification

| status | path | category | owner/notes |
| --- | --- | --- | --- |
| modified/new | files in `git status --short` at verification time | intended_slice_work | BL-WORKFLOW-CATALOG-001 |

## Anti-Brittleness Review

| Question | Answer |
| --- | --- |
| What invariant prevents the failure class? | Catalog validation enforces schema, unique path ownership, dependency/capability closure; profile gates enforce budgets at generation time. |
| Is the fix typed/schema/state-machine/validator/contract-based? | Yes: profile_catalog.schema.json plus contract tests plus per-profile generated-repo gates. |
| Which behavior is centralized instead of scattered? | Asset shipping lives only in profiles/catalog.json; budgets only in EFFICIENCY_BUDGET.yaml. |
| Which observed examples are covered by general rules? | Any future asset added to the set inherits the same validation and budget enforcement. |
| What adjacent cases were tested? | All four profiles generate and pass their gates; contract tests updated for resolved composition. |
| What brittle pattern was explicitly avoided? | No hardcoded file lists outside the catalog; no per-repo manual copying. |
| Did the slice add provider-specific assumptions? | No. |
| If yes, why is that not the authority path? | Not applicable. |

## Verification Log

| Check | Command / Path | Result |
| --- | --- | --- |
| resolution check | `init_template.assets_for_profile` for all profiles | pass; improve shipped to minimal/solo/team/regulated |
| init/upgrade suites | `pytest scripts/test_init_template.py scripts/test_upgrade.py scripts/test_contracts.py -q` | pass |
| full level-2 gate | `projectstate_quality_gate.py --gate-level 2 --conformance` | pass; exit 0 (see `quality_gate_output.txt`) |
| evidence manifest strict | `projectstate_evidence_pack.py check . --strict` | pass |

## Evidence Pack Manifest

- Manifest: `manifest.json`
- Redaction status: checked with limits; automated scan passed and manual review completed

## Runtime Identity

- Runtime required: no
- Artifact: `runtime_identity.json`

## Browser Verification

- Browser verification required: no
- Reason: template/catalog tooling change with no user-facing UI.

## Closure State At Current Worktree

- Implemented: yes; captured at immutable proof head `67a4f53a153502b4a24b8acd0db715d569fb2593`
- Validated locally: yes
- Closure-grade: no until remote finalization
- Remote closure: pending
- Human product acceptance: pending

## Human Override

- Human override used: no
- Remaining risk: downstream repos receive the workflow files but their generated AGENTS.md does not enumerate them; discovery happens via this repo's docs and the rollout queue item.
- Still closure-grade: no, by the Remote Truth Gate

## Risks / What Remains Partial

- Rollout of the upgrade across managed downstream repos remains open work
  tracked under BL-WORKFLOW-CATALOG-001 in NEXT_ACTIONS/BACKLOG.
