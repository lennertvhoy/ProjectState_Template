# Failure Scan: Generated-repo correctness and context hygiene

**Date:** 2026-07-10
**Backlog item:** [BL-CONTEXT-001]
**Author:** coding-agent
**Severity:** P1
**Execution mode impact:** template-maintenance

## What Happened Or Could Happen

- Fresh downstream repos inherit template-maintenance tests, history, fixtures,
  evidence, and broad documentation because initialization copies whole
  directories instead of an explicit runtime asset set.
- A generated repo declares `repo_role: downstream_project`, but copied template
  tests require `repo_role: template_repository`; its own quality gate therefore
  fails after the template test suite mostly passes.
- Duplicate YAML mapping keys are silently overwritten by the schema parser, so
  structurally ambiguous state can pass validation.
- Queue, backlog, active-problem, status, and worklog lifecycle claims can disagree
  while hygiene and efficiency checks still pass.
- A profile may be called `minimal` without a measurable file, byte, or startup
  context boundary.

## How The User Or Operator Would Notice

- `python3 scripts/statedd_quality_gate.py` fails in a fresh generated repo.
- A `minimal` instance still contains hundreds of unrelated files and more than
  one megabyte of workflow material.
- Agents spend context on template history and duplicated state, or act on stale
  queue items that prior work already closed.

## Likely Adjacent Failures

- `adopt` and downstream upgrade paths could keep installing template-only tests.
- A curated bundle could omit a transitive gate dependency and pass only on the
  template maintainer's machine.
- File-count budgets could be gamed by moving the same payload into fewer files;
  byte and estimated-token budgets must be checked independently.
- Compact wording could become opaque, tokenize poorly, or remove a safety rule.
- Lifecycle checks could mistake local implementation for remote/CI closure.

## Previous Tests That Might Miss This

- Initializer tests checked that many template assets existed, not that only
  downstream runtime assets existed.
- CI generated sample repos and ran hygiene/schema checks from the template, but
  did not execute each generated repo's own quality gate.
- Schema tests checked required values but had no duplicate-key adversary.
- Cross-file checks only required a queue ID to appear somewhere in `BACKLOG.md`.

## Global Invariant Needed

- Every profile is produced from an explicit allowlist and emits a machine-readable
  asset manifest; generated repos exclude template tests, fixtures, evidence,
  incidents, release history, and maintenance changelogs.
- Every generated profile passes its own quality gate in isolation.
- YAML duplicate keys fail with an actionable line/key error.
- `PROJECT_STATE.yaml.active_problems` is canonical for open P0/P1 status; active
  queue IDs must be in `BACKLOG.md` `NOW`, closed/terminal IDs cannot remain active.
- Startup files, startup bytes, estimated tokens, managed file count, and managed
  bytes are measured and bounded together; normalized profile tests require
  `minimal` to have the smallest startup payload.

## Adversarial Case

- Input/event: generate all four profiles, inject nested duplicate YAML keys, add
  a CLOSED backlog ID to `NEXT_ACTIONS.md`, and place a terminal worklog ID in NOW.
- Expected protected behavior: each clean profile self-gate passes; each malformed
  state case fails for the general invariant; `minimal` stays within hard footprint
  and context budgets.
- Evidence required: regression outputs, per-profile footprint metrics, generated
  self-gate logs, schema duplicate-key failure, and semantic lifecycle failures.

## Runtime Or Live Proof Required

- Required: no
- Why: this is a generator, validation, and workflow-context slice with no
  application runtime or user-facing screen.
- Artifact: test and gate output plus generated filesystem measurements.

## Post-Deploy Watch Required

- Required: yes
- Duration or trigger: root GitHub Actions on the final pushed head; re-check every
  profile after any future asset-manifest or startup read-order change.
- Artifact: generated-profile matrix in `.github/workflows/validate.yml`.

## Closure Blockers

- Any profile's own quality gate fails.
- Generated output contains template-only tests, fixtures, historical evidence,
  incident records, or changelog history.
- Duplicate YAML keys still parse successfully.
- Semantic lifecycle adversaries pass.
- Footprint metrics are absent, unbounded, or `minimal` is not materially smaller
  than `solo`.
