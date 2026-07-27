# Failure Scan: Maximum-Value Correctness And Lifecycle Repair

**Date:** 2026-07-11
**Backlog item:** [BL-MAX-VALUE-001]
**Author:** coding-agent
**Severity:** P0
**Execution mode impact:** quality_freeze for lifecycle and closure claims; template-maintenance repair may continue

## What Happened Or Could Happen

- PR #5 merged after an owner review identified unresolved upgrade, test, CI,
  path-confinement, metrics, and closure-truth failures.
- An old asset manifest can suppress newly introduced template assets, while a
  malformed manifest can broaden behavior instead of failing closed.
- A quality gate can report success after only one applicable suite, and CI can
  stay green when a newly added test is absent from a manual list.
- Symlink resolution or unsafe managed paths can redirect writes outside the
  requested target. Interrupted multi-file upgrades can leave files and the
  ownership manifest describing different states.
- Duplicated profile measurements and closure claims can drift across state,
  evidence, PR text, and CI.

## Failure Classes And Mitigations

| Failure | Severity / class | Detection and prevention | Rollback and evidence |
|---|---|---|---|
| Historical manifest treated as future desired state | P0 `data_integrity`, `regression` | Derive desired assets from the current profile/module graph; use the old manifest only as validated ownership/base evidence | No writes on plan failure; old-manifest-plus-new-asset integration test |
| Malformed or unsafe manifest broadens the plan | P0 `security_privacy`, `brittleness` | Strict schema/semantic validation; reject absolute paths, traversal, duplicates, symlinks, and unknown ownership states | Fail before mutation; malformed/path property tests |
| Local modifications or removals are overwritten/deleted | P0 `data_integrity` | Hash/base comparison and explicit merge strategies; report removals without silent deletion | Preserve original bytes; modified/removed-asset tests |
| Interrupted apply leaves mixed generations | P0 `data_integrity`, `observability` | Complete preflight, stage writes, rollback replaced files on failure, and publish the new manifest last with atomic replacement | Injected-failure test proves byte-for-byte restoration; idempotent rerun proof |
| Applicable test suites are skipped | P0 `workflow`, `regression` | Discover all declared/applicable suites, run all, aggregate results, and fail on an unavailable declared runner | Multi-suite pass/fail and unavailable-runner tests with actionable output |
| CI omits newly added tests | P1 `workflow`, `observability` | One documented authoritative suite using automatic discovery; focused smoke tests only for distinct integration boundaries | CI workflow inspection plus clean-clone run |
| Target or nested symlink escapes confinement | P0 `security_privacy`, `data_integrity` | Inspect the requested path before canonicalization; enforce relative managed paths and no symlink components/source symlinks | Root/nested/source symlink and traversal tests prove zero outside-root writes |
| Metrics/evidence/PR claims disagree | P1 `state_truth`, `workflow` | Generate one machine-readable metrics artifact with provenance; reference it from human views | Exact-head artifact hash, evidence check, PR/CI/finalizer agreement |
| Concision work removes decision-critical truth | P1 `state_truth`, `brittleness` | Keep readable canonical ProjectState authoritative; benchmark selection separately from rendering | Round-trip/source-link checks in a later StateIR/StatePack slice |
| New controls cost more than the risk prevented | P1 `workflow` | Keep one lifecycle engine, one authoritative validation entrypoint, and risk-tiered gates; reject speculative abstractions | Architecture review records deletions, non-goals, and measured context/process cost |

## How The User Or Operator Would Notice

- A downstream upgrade omits a new required gate or asset, overwrites a local
  customization, reports success with a stale manifest, or changes files after
  a failed command.
- CI is green while a local secondary test suite fails or its runner is absent.
- Generated profiles disagree with documented measurements or fail their own
  gate after a clean generation.
- A handoff says closure-grade while the pushed head, PR body, evidence, or
  latest workflow run names another commit.

## Likely Adjacent Failures

- Profile dependencies claim a capability whose script, schema, prompt, or
  validation asset is absent.
- Case-insensitive paths, Windows separators, executable bits, line endings,
  or Git porcelain parsing behave differently from Linux.
- Source repository symlinks, hard links, duplicate normalized paths, or a
  target replaced between preflight and apply bypass confinement.
- A rollback restores managed files but not their modes, directories, or
  manifest; a second run is therefore not idempotent.
- A generated metrics timestamp makes deterministic output impossible or a
  tokenizer fallback is presented as an actual model count.

## Previous Tests That Might Miss This

- Example-only tests where the old and current asset sets are identical.
- One Python suite passing before a failing npm, Make, or Cargo suite is reached.
- CI steps that enumerate known test filenames.
- Nested-symlink checks that call `resolve()` before examining the requested
  target root.
- Happy-path apply tests without injected interruption, modified files, removed
  assets, malformed manifests, or a second-run comparison.

## Global Invariant Needed

Every upgrade must be a confined, fully preflighted transition from validated
historical ownership to the current declared profile/module graph. Ambiguity
causes zero writes. All applicable declared validators run. Generated metrics
and context are non-authoritative derivatives tied to one source revision.
Closure crosses no Git, CI, runtime, or acceptance boundary without exact-head
proof.

## Adversarial Case

- Input/event: An older downstream manifest lacks a newly required asset, names
  a removed asset, contains a locally modified managed file, and is upgraded
  through a symlinked root while one declared test runner is unavailable and an
  injected write fails midway.
- Expected protected behavior: Unsafe root and manifest states fail before any
  write. On a safe root, the plan offers the new asset, preserves the modified
  file, reports the removal, fails for the unavailable runner, and restores all
  original bytes after the injected failure. A successful rerun updates the
  manifest last; the following run is a no-op.
- Evidence required: Temporary-repository integration tests, before/after tree
  hashes, aggregated gate output, canonical metrics artifact, and exact-head CI.

## Runtime Or Live Proof Required

- Required: no
- Why: The template root has no application runtime; behavior is filesystem,
  Git, generated-profile, and CI lifecycle behavior.
- Artifact: Clean-clone/profile generation, temporary-repository integration
  outputs, evidence manifest, and GitHub Actions on the exact PR head.

## Post-Deploy Watch Required

- Required: yes
- Duration or trigger: Exact-head push and pull-request workflows must finish;
  no merge is authorized in this slice.
- Artifact: GitHub Actions URLs and remote closure finalizer output tied to the
  pushed head.

## Closure Blockers

- All immediate PR #5 review blockers need regression proof on the merged-main
  lineage.
- Canonical metrics, evidence, state, PR body, remote branch, and CI must agree.
- The complete authoritative suite, generated-profile gates, lifecycle
  integration tests, anti-brittleness review, hygiene checks, and handoff must
  pass.
- Human acceptance remains separate and unproven.
