# Failure Scan: Outcome-first core redesign

**Date:** 2026-09-04
**Backlog item:** [BL-OUTCOME-CORE-001]
**Author:** coding-agent
**Severity:** P0
**Execution mode impact:** quality_freeze

## What Happened Or Could Happen

- Repository and control-plane checks can pass while the documented product journey fails.
- Agents can preserve a mistaken architecture by expanding the governance that evaluates it.
- A compatibility-minded migration could accidentally leave the old multi-file workflow as the default.

## How The User Or Operator Would Notice

- A generated project contains more coordination artifacts than product files.
- Automated checks are green even though the primary journey is failed or not run.
- A blocked agent changes acceptance or governance instead of simplifying the product path.

## Likely Adjacent Failures

- Strict legacy profiles leak into the new default profile.
- The initializer changes, but adoption, documentation, or tests still teach the old workflow.
- A two-strike rule becomes another arbitrary counter instead of an evidence-backed simplification review.

## Previous Tests That Might Miss This

- Tests that only assert generated file presence or repository-gate success.
- Profile-size checks whose budgets legitimize a large control plane.
- Schema tests that validate shape without checking outcome precedence.

## Global Invariant Needed

- A failed or unrun primary user journey outranks all secondary checks, and the base profile has one canonical state file.

## Adversarial Case

- Input/event: automated tests are recorded as passed while the primary journey is recorded as failed.
- Expected protected behavior: the outcome gate exits nonzero and refuses validated/accepted status.
- Evidence required: focused regression output plus a generated-project end-to-end run.

## Runtime Or Live Proof Required

- Required: yes
- Why: the initializer and generated gate are user-facing workflow behavior.
- Artifact: `evidence/outcome-core-001/summary.md`

## Post-Deploy Watch Required

- Required: no
- Duration or trigger: release is outside this local implementation slice.
- Artifact: not applicable

## Closure Blockers

- Default generation still emits the legacy truth surfaces.
- The generated outcome gate can report success when the primary journey failed.
- The documented profile default disagrees with initializer behavior.
