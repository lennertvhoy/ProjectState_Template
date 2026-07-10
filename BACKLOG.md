# BACKLOG - Strategic Roadmap

**Product:** StateDD_Template
**Execution Mode:** template-maintenance
**Delivery State:** stabilization
**Updated At:** 2026-07-10

## Purpose

This backlog converts the 2026-07-10 upstream audit into dependency-ordered,
bounded slices. `NEXT_ACTIONS.md` may activate only work listed here. Audit
claims remain `reported` until reproduced; a draft PR is source material, not
proof that its claims are correct.

## NOW

- [BL-CORE-001] Eliminate false closure and generator corruption.
  **Priority:** P0 release blocker. Start from freshly fetched `main` in a new isolated worktree; do not append this work to draft PR #4.
  **Scope:** `scripts/statedd_remote_truth_check.py`, `scripts/statedd_closure_check.py`, `scripts/statedd_remote_closure_finalizer.py`, `scripts/statedd_audit.py`, `scripts/statedd_post_merge_verify.py`, `scripts/statedd_handoff.py`, `scripts/statedd_quality_gate.py`, `scripts/statedd_runtime_truth_check.py`, `scripts/statedd_evidence_type_check.py`, `scripts/statedd_validate_schema.py`, duplicate-key repair in `scripts/init_template.py`, `scripts/statedd_version_check.py`, `CHANGELOG.md`, upgrade-report `dry_run` truth, public runtime-evidence privacy, and only directly required tests, schemas, CI, and state updates.
  **Non-goals:** parallel-agent orchestration, browser integration, broad instruction rewrites, new evidence architecture beyond correctness, managed updates, toolpacks/model routing, or the full `statedd` package migration.
  **Required method:** add a failing regression for each condition before or with its repair; use semantic/structured checks rather than exact prose, keyword, fixture-only, provider-specific, or mtime behavior. The slice contract must map every changed production file to its negative and positive tests.
  **Checkpoint order:** (1) Git and every closure consumer; (2) gate configuration and handoff exit semantics; (3) runtime/evidence alignment and privacy; (4) generator, version, and upgrade-report truth; (5) CI discovery and clean-after-test proof. Finish and keep each checkpoint green before continuing.
  **Acceptance:**
  1. At closure, any staged change, unstaged change, or untracked file fails every closure path. Production code uses no filename/keyword heuristic; any unavoidable temporary exception is an exact checked-in allowlist with negative tests.
  2. Exact local, upstream, and remote head equality is required; ahead, behind, diverged, or missing-upstream states fail.
  3. GitHub verification requires a successful current-head required CI run; missing, pending, stale-head, or omitted checks do not pass.
  4. Missing required tests or linters produce `NOT_CONFIGURED` or failure, never `PASS`.
  5. A failed handoff verification command produces a non-zero process exit.
  6. Runtime and evidence consumers share one validated artifact contract for the current slice.
  7. Evidence selection is bound to slice identity and head, not filesystem mtime or global historical keywords.
  8. Generated and validated YAML rejects duplicate mapping keys; downstream DNA retains every invariant block.
  9. Parsed repository role drives version checks; `VERSION`, `CHANGELOG.md`, and current template assets agree on v5.
  10. Applied upgrades report `dry_run: false`; dry runs report `dry_run: true`.
  11. Public artifact generators redact or normalize absolute home paths, hostnames, PIDs, command lines, private URLs, and similar machine identity; the tracked-evidence scanner rejects any sensitive value that remains.
  12. CI discovers every regression test and runs negative tests for each corrected false-pass path without leaving the repository dirty.
  **Exit:** one focused PR is green on its exact pushed head, required receipts agree with that head, the PR is merged, and post-merge verification succeeds. Until then the slice is not closure-grade.

## NEXT

- [BL-UPSTREAM-001] Add the canonical managed-asset manifest, downstream lockfile, and release-manifest schemas.
  **Depends:** BL-CORE-001. **Scope:** one ownership/update-policy source consumed by initializer and upgrader; managed hashes and correct plan/apply reporting. **Exit:** duplicated managed-path lists are removed or generated, downstream truth is never overwritten, and repeated install planning is deterministic.

- [BL-GIT-001] Add a strict push-completeness verifier.
  **Depends:** BL-UPSTREAM-001. **Scope:** porcelain-v2 parsing, expected root/remote/branch, staged/unstaged/untracked/ignored classification, upstream equality, manifest deliverables, and receipt freshness. **Exit:** failure injection covers every dirty/diverged/missing-deliverable state and only one closure success token exists.

- [BL-CI-001] Rebuild CI around discovery, reproducible generation, and failure injection.
  **Depends:** BL-GIT-001. **Scope:** pytest discovery, Ruff, supported Python matrix, generated no-diff checks, clean-after-test assertion, and negative boundary suites. **Exit:** new tests cannot fall outside CI, two generated instances are equivalent, and test execution leaves no unexplained diff.

- [BL-FIXTURE-001] Build a deterministic, privacy-safe lived-in downstream laboratory.
  **Depends:** BL-UPSTREAM-001 and BL-CI-001. **Scope:** large generic and StudyDD-shaped synthetic fixtures with state growth, old schemas, drift, interrupted writes, ignored canonical-looking files, and partial commits. **Exit:** same seed is identical and every injected failure reaches its expected gate without personal data.

- [BL-CORE-002] Create the shared `statedd` package foundation.
  **Depends:** BL-CI-001. **Scope:** common models, errors, explicit repo-root handling, Git/GitHub clients, evidence selection, result enums, and thin compatibility wrappers. **Non-goal:** closure state transitions. **Exit:** wrapper/CLI parity passes and duplicate helpers are removed.

- [BL-ADAPTER-001] Make `PROJECT_ADAPTER.yaml` the exact executable gate plan.
  **Depends:** BL-CORE-002. **Scope:** argv arrays, required flags, timeouts, gate levels, project-aware commands, and explicit `PASS`, `FAIL`, `NOT_CONFIGURED`, `NOT_APPLICABLE`, `BLOCKED`, and override results. **Exit:** ecosystem guessing and shell command strings are rejected.

- [BL-SCHEMA-001] Replace custom parsing and string rendering with strict schemas and declarative generation.
  **Depends:** BL-CORE-002 and BL-UPSTREAM-001. **Scope:** duplicate-rejecting YAML, full JSON Schema, structured render sources, compiled instruction surfaces, and render/no-diff gates. **Exit:** every declared artifact validates and `render --all` is idempotent.

- [BL-EVIDENCE-001] Add a slice-bound claim ledger, privacy profiles, and immutable receipt models.
  **Depends:** BL-SCHEMA-001 and BL-GIT-001. **Scope:** slice/head-bound claims, artifact hashes, public/private/local-only profiles, and ignored local or CI receipts. **Exit:** wrong-slice evidence, global keyword search, mtime selection, and public machine identity all fail.

- [BL-CLOSURE-001] Replace the closure stack with one explicit state machine and remote receipt.
  **Depends:** BL-ADAPTER-001 and BL-EVIDENCE-001. **Scope:** transitions from active through post-merge verified, with compatibility wrappers unable to elevate state. **Exit:** PR prose needs no self-referential final SHA and only an exact-head automated receipt can establish remote closure.

- [BL-PARALLEL-001] Finish parallel-agent worktrees as a deterministic lifecycle.
  **Depends:** BL-CLOSURE-001. **Scope:** extract focused code from PR #4, fetched bases, explicit lifecycle states, remote reservations, and lossless close/abort. **Exit:** dirty removal is blocked, ownership works across clones, and remote recovery is proven before cleanup.

## LATER

- [BL-TRUST-001] Define prompt-injection and instruction-trust boundaries.
  **Depends:** BL-SCHEMA-001. **Exit:** one canonical trust contract classifies instruction/data surfaces, the scanner quarantines suspicious imported content deterministically, and fixtures cover false positives and bypass attempts.

- [BL-UPSTREAM-002] Open validated downstream upgrade PRs from immutable releases.
  **Depends:** BL-CLOSURE-001 and BL-FIXTURE-001. **Scope:** pull-based check/plan/apply/verify, release channels, SHA-pinned reusable workflow callers, upgrade branches/PR reports, and optional patch-only auto-merge policy. **Exit:** updates are idempotent, release inputs are immutable, and downstream-owned state is preserved.

- [BL-INCIDENT-001] Export redacted real failures into upstream regression fixtures.
  **Depends:** BL-TRUST-001, BL-EVIDENCE-001, and BL-FIXTURE-001. **Exit:** public exports contain no private markers and deterministically reproduce the expected generic failure.

- [BL-COMPAT-001] Add StateDD-to-StudyDD candidate/stable release-train testing.
  **Depends:** BL-UPSTREAM-002 and BL-FIXTURE-001. **Machine exit:** synthetic compatibility and semantic upgrade comparison pass with exact-head receipts. **Private promotion condition:** a private canary may be reviewed separately, never blocks public CI, never enters public evidence, and is never destructively updated.

- [BL-TOOLS-001] Add generic toolpack and semantic agent-role contracts.
  **Depends:** BL-TRUST-001 and BL-SCHEMA-001. **Scope:** tool-native rendering, canonical trust propagation, single-writer/subagent partition policy, permissions, and profile commands. **Exit:** one generic role source renders tool assets and each pack writes only manifest-owned paths.

- [BL-MODEL-001] Add versioned semantic model routing with freshness and fallback receipts.
  **Depends:** BL-TOOLS-001. **Exit:** transient model IDs exist only in tool maps, generated assets, and the lockfile; the actual fallback model is recorded.

- [BL-CODEX-001] Add the Codex-native toolpack.
  **Depends:** BL-MODEL-001 and BL-UPSTREAM-002. **Exit:** project agents, skills, permissions, worktree settings, and advisory CI render and validate without changing user-home configuration.

- [BL-EXPLAIN-001] Add deterministic StateDD provenance and `explain` commands.
  **Depends:** BL-CLOSURE-001. **Exit:** gate and closure decisions enumerate canonical inputs, exclusions, rule versions, and receipts.

- [BL-OVERRIDE-001] Add typed, scoped, expiring human overrides.
  **Depends:** BL-CLOSURE-001 and BL-SCHEMA-001. **Exit:** overrides validate scope/expiry and can never manufacture verified truth.

- [BL-PERF-001] Record local-only operational telemetry and enforce measured gate budgets.
  **Depends:** BL-ADAPTER-001 and BL-OVERRIDE-001. **Exit:** duration/cache/input metrics contain no content and budget overruns fail without a valid typed override.

- [BL-BROWSER-002] Integrate a concrete browser provider after closure stabilization.
  **Depends:** BL-CLOSURE-001 and BL-TRUST-001. **Exit:** provider-specific proof satisfies the generic browser/runtime contract on exact source identity without becoming a hard dependency.

- [BL-ARCH-001] Separate engines from templates and make structured state canonical for the next major version.
  **Depends:** BL-COMPAT-001 and BL-CLOSURE-001. **Exit:** migrations are deterministic, Markdown views are generated, wrappers have a timed deprecation, and downstream compatibility passes.

- [BL-FLEET-001] Define a privacy-minimal private fleet registry contract.
  **Depends:** BL-UPSTREAM-002. **Scope:** the public repo ships only schema, redacted example, and update-status aggregation logic; repository inventory and operational records live in a separate private system. **Exit:** synthetic fixtures prove version/update visibility without learner data, private URLs, local paths, or evidence content.

## DOWNSTREAM HANDOFFS

These items target `StudyDD_Template`, not this repository. StateDD owns only the
generic contracts and compatibility gates they depend on.

- [BL-STUDY-EXPLAIN-001] **Target:** StudyDD_Template; never activate here. Add full learning-state provenance and `explain next/skill/readiness/review` commands after BL-EXPLAIN-001.
- [BL-STUDY-ALGO-001] **Target:** StudyDD_Template; never activate here. Add versioned learning algorithms, shadow comparisons, and invariant-based promotion after BL-COMPAT-001.
- [BL-STUDY-GRADE-001] **Target:** StudyDD_Template; never activate here. Add blind grading and uncertainty holds after BL-TRUST-001.
- [BL-STUDY-SOURCE-001] **Target:** StudyDD_Template; never activate here. Add section-level authoritative-source drift monitoring after BL-INCIDENT-001.
- [BL-STUDY-EVIDENCE-001] **Target:** StudyDD_Template; never activate here. Separate practice, repair, assessment, retention, transfer, and timed evidence in downstream projections.
- [BL-STUDY-PLAN-001] **Target:** StudyDD_Template; never activate here. Add explainable deterministic next-action utility planning after downstream provenance exists.

## CLOSED

- [BL-SANITY-001] StateDD repo coherence and efficiency repair merged to `main`; later audit findings supersede its closure-stack confidence, not its historical changes.
- [BL-REMOTE-CLOSURE-001] Historical remote-closure implementation; its current correctness claim is superseded by BL-CORE-001.
- [BL-QUALITY-001] Historical quality-firewall contract; enforcement strength is under stabilization review.
- [BL-BROWSER-001] Provider-agnostic browser verification contract.
- [BL-007] Public usability and release-readiness polish.
- [BL-005] Canonical schema/export/import example.
- [BL-012] Evidence pack manifests and redaction gate.
- [BL-013] Non-destructive downstream upgrade tooling.
- [BL-014] Adoption profiles and bootstrap wizard.

## WATCHLIST

- Draft PR #4 remains unmerged source material; its historical proof heads are not current closure evidence.
- Browser, parallel-agent, updater, toolpack, model-routing, and architectural work must not bypass BL-CORE-001 dependencies.
- StudyDD-only learning features must not be implemented in the StateDD repository.
- Negative findings remain `reported` until reproduced; absence of reproduction is not disproof.
- Public state and evidence must not contain developer-machine identity or private downstream data.
