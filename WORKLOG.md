# WORKLOG

**Purpose:** Append-only history for completed work.

## 2026-07-10 - BL-CONTEXT-001 remote closure candidate

**Type:** template_maintenance_closure
**Status:** CLOSURE_CANDIDATE
**Git Head:** proof head 8840a3c2bed468b6440705c031dcc0015df807d1 on PR #5; final state commit follows
**Worktree:** isolated agent worktree
**Gate Level:** 2; proof head passed both push and pull-request GitHub Actions runs

### Verification
- GitHub Actions runs `29120524026` and `29120525510` both passed on proof head `8840a3c`.
- The initial CI failure on `aea07bd` correctly exposed a fixture queue/backlog contradiction; the fixture was repaired without weakening the new semantic gate.
- The final state commit must pass GitHub Actions and `scripts/statedd_remote_closure_finalizer.py --pr 5` before any closure-grade handoff.

### Evidence
- `docs/evidence/2026-07-10-context-generator-hygiene/README.md`
- PR #5: https://github.com/lennertvhoy/StateDD_Template/pull/5

### Notes
- This entry records a closure candidate, not pre-emptive CI truth for the following state-only commit.

## 2026-07-10 - Generated-repo correctness and context hygiene (BL-CONTEXT-001)

**Type:** template_maintenance_repair
**Status:** VALIDATED_LOCAL_ONLY
**Git Head:** proof base 976a3f0e2a38ba7bf096a300db16b95b65bd53f4 on branch bl-bl-context-001-code-a1daa; final commit pending
**Worktree:** isolated agent worktree; classified slice dirt
**Gate Level:** 2 local validation; remote push/PR/CI closure pending

### What changed
- Replaced broad directory copying with explicit profile asset allowlists and a schema-backed `STATEDD_ASSETS.json` emitted into every generated/adopted repo.
- Excluded template tests, fixtures, maintenance evidence/history, incidents, changelog, release material, and the initializer from downstream instances and upgrades.
- Made `minimal` core-gates-only and moved repository inventory out of mandatory startup state; compacted generated AGENTS, PROJECT_STATE, PROJECT_DNA, README, and startup prompt without opaque abbreviations.
- Made duplicate YAML keys fatal at root/nested levels and reused the strict parser for efficiency budgets.
- Added startup file/byte/estimated-token and profile file/byte budgets, with measurements printed by the efficiency gate.
- Made PROJECT_STATE active problems canonical for STATUS P0/P1 failures and enforced semantic backlog NOW/CLOSED, queue, and terminal worklog agreement.
- Made the quality gate select declared project tests/static analysis rather than treating globally installed tools or absent tests as failures.
- Fixed the worktree guard so leading Git porcelain status columns and hidden paths are preserved.

### Verification
- `python3 -m pytest scripts/ -q` passed after final local state updates (164 tests, 4 subtests).
- Each `minimal`, `solo`, `team`, and `regulated` generated repo passed its own quality gate.
- `python3 scripts/statedd_quality_gate.py --gate-level 2` passed.
- Schema, state/bootstrap, version, runtime-truth, evidence-type, instruction, efficiency, and brittleness gates passed locally.
- `minimal`: 29 files / 145,995 bytes / about 2,082 estimated startup tokens.
- `solo`: 62 files / 411,582 bytes / about 2,056 estimated startup tokens.

### Evidence
- `docs/failure_scans/BL-CONTEXT-001.md`
- `docs/evidence/2026-07-10-context-generator-hygiene/README.md`
- `docs/evidence/2026-07-10-context-generator-hygiene/manifest.json`
- `docs/evidence/2026-07-10-context-generator-hygiene/runtime_identity.json`

### Notes
- Local behavior is validated, but the slice remains in BACKLOG NOW and active state until the pushed PR head and GitHub Actions agree.
- Ultra-terse/caveman model context is not canonical; compact/modular/ephemeral representations remain benchmark variants.

## 2026-07-07 - Parallel-Agent Worktree Orchestrator (BL-PARALLEL-001)

**Type:** template_maintenance_feature
**Status:** LOCAL_CLOSURE_GRADE
**Git Head:** 0e0af8f96ac211871c2f03663fed154ddf00899e on branch bl-workflow-002-worktree-brittleness
**Worktree:** clean
**Gate Level:** 2 (slice closure) / local closure verified; remote closure pending push/PR/CI

### What changed
- Added `scripts/statedd_agent_worktree.py` orchestrator with `start`, `guard`, `handoff`, `close`, `cleanup`, and `list` subcommands.
- Provisions isolated per-agent branches, worktrees under `.worktrees/`, and atomic reservation refs under `refs/statedd/reservations/`.
- Detects git lock contention (`index.lock`, `config.lock`) and fails fast with bounded optional `--wait` polling; never deletes lock files.
- Enforces safe worktree removal only under `<repo-root>/.worktrees/`.
- Made `scripts/statedd_worktree_guard.py` agent-context-aware via `--agent-context` / auto-detect `.statedd/agent.context`; suppressed shared/default branch check and relaxed unclassified-dirt handling in agent context.
- Made `scripts/statedd_handoff.py` report `agent_id`, `slice_id`, `worktree_path`, `reservation_ref`, and `worktree_owner` when in an agent worktree.
- Made `scripts/statedd_audit.py` agent-context-aware: relaxed `worktree_clean` for classified slice dirt, `changed_files_in_slice` diffs from the agent branch base, and `latest_evidence_folder` prefers matching `slice_id`.
- Made `scripts/statedd_closure_check.py` skip the dirty-worktree failure when dirt is classified slice work in agent context.
- Made `scripts/statedd_remote_closure_finalizer.py` reject PR branch mismatches and re-check remote HEAD before declaring closure to catch interleaved pushes.
- Added `scripts/test_agent_worktree.py` with 8 regression tests covering start, double-reservation, guard, lock detection, handoff, close, cleanup, and audit-in-agent-context.
- Updated `.github/workflows/validate.yml` to compile and run the new test file and run a dry-run smoke test.
- Propagated the new assets through `scripts/init_template.py` and `scripts/statedd_upgrade.py`.
- Updated state/docs: `AGENTS.md` Parallel-Agent Invariant, `BACKLOG.md`, `NEXT_ACTIONS.md`, `PROJECT_STATE.yaml`, `docs/failure_scans/BL-PARALLEL-001.md`, `skills/close-slice/SKILL.md`, `prompts/CODING_AGENT_STARTUP_PROMPT.md`.

### Verification
- `python3 scripts/check_state_docs.py` passed.
- `python3 scripts/statedd_validate_schema.py` passed.
- `python3 -m pytest scripts/ -q` passed: 152 passed, 4 subtests passed.
- `python3 scripts/test_init_template.py` passed.
- `python3 scripts/statedd_efficiency_check.py --gate-level 2` passed.
- `python3 scripts/statedd_evidence_pack.py check docs/evidence/2026-07-07-parallel-agent-worktree` passed.
- `python3 scripts/statedd_audit.py --strict` passed with `AUDIT RESULT: PASS — closure-grade`.
- `python3 scripts/statedd_doctor.py` reports `Closure grade: pass` and `Evidence manifest: valid`.

### Evidence
- `docs/failure_scans/BL-PARALLEL-001.md`
- `docs/evidence/2026-07-07-parallel-agent-worktree/README.md`
- `docs/evidence/2026-07-07-parallel-agent-worktree/manifest.json`
- `docs/evidence/2026-07-07-parallel-agent-worktree/runtime_identity.json`

### Notes
- Local commit `0e0af8f` is ahead of remote `dadf4ad` on `bl-workflow-002-worktree-brittleness`.
- Remote closure (push, PR, GitHub Actions, `statedd_remote_closure_finalizer.py`) is pending explicit approval for the outward-facing push.

## 2026-07-07 - Template logic-hole repair (BL-SANITY-002)

**Type:** template_maintenance_repair
**Status:** CLOSURE_GRADE_CI_VERIFIED
**Git Head:** bdb621cce6499d0114d02ef4f1b25946a9d05874 on branch bl-workflow-002-worktree-brittleness
**Worktree:** clean
**Gate Level:** 2 (slice closure) / remote closure verified

### What changed
- Integrated BL-SANITY-002 into `BACKLOG.md`, `NEXT_ACTIONS.md`, `STATUS.md`, `PROJECT_STATE.yaml`, `docs/EVIDENCE_LOG.md`, and `docs/failure_scans/BL-SANITY-002.md`.
- Hardened `scripts/statedd_audit.py` to require the current HEAD in evidence (or an explicit proof/final split) and to compute changed files from the merge-base with the default branch instead of the last commit.
- Fixed `scripts/statedd_doctor.py` to count real open blockers from `PROJECT_STATE.yaml` instead of `NEXT_ACTIONS.md` headings.
- Fixed `scripts/statedd_handoff.py` to report `local-only files claimed: not proven` when upstream state is unknown.
- Hardened `scripts/statedd_worktree_guard.py` to reject `unknown_do_not_touch` classifications and to stop labeling ordinary tracked feature branches as shared/default.
- Added legacy compatibility fields to `scripts/statedd_runtime_proof.py` so `statedd_runtime_truth_check.py` and `statedd_closure_check.py` accept the canonical `runtime_identity.json`; tightened endpoint reachability to HTTP 2xx/3xx; made artifact writes atomic.
- Fixed `statedd_runtime_truth_check.py` to capture the full git HEAD instead of a 12-character prefix.
- Hardened `scripts/init_template.py` to refuse `new --target <template-root>`.
- Hardened `scripts/statedd_upgrade.py` with target-path traversal guards and fixed the JSON report to reflect the actual `--apply`/`--dry-run` mode.
- Hardened `scripts/statedd_browser_verify.py` to reject artifact paths that escape the evidence directory.
- Fixed `scripts/statedd_remote_closure_finalizer.py` to run `gh` from the repo root, honor `--github-token` via the `GH_TOKEN` environment variable, and avoid using the check-suite databaseId as a workflow run id.
- Fixed `scripts/statedd_post_merge_verify.py` to declare the `$sha` GraphQL variable and to fetch the default branch before checking merge ancestry.
- Hardened `scripts/statedd_probe_guidance.py` to run probes in an isolated temporary copy of the repo instead of polluting the original worktree.
- Added regression tests for the above in `scripts/test_worktree_guard.py`, `scripts/test_init_template.py`, `scripts/test_upgrade.py`, and `scripts/test_browser_verification.py`.

### Verification
- `python3 scripts/check_state_docs.py` passed.
- `python3 scripts/statedd_validate_schema.py` passed.
- `python3 -m pytest scripts/test_*.py -q` passed: 144 passed, 4 subtests passed.
- `python3 scripts/test_init_template.py` passed.
- `python3 scripts/test_upgrade.py` passed.
- `python3 scripts/test_browser_verification.py` passed.
- `python3 scripts/statedd_doctor.py` reports `Open blockers: 1` (BL-SANITY-002 active problem) and `Closure grade: fail` because the worktree is dirty and the latest evidence README records the pre-repair HEAD.

### Evidence
- `docs/EVIDENCE_LOG.md` entries `EV-2026-07-07-001` and `EV-2026-07-07-002`
- `docs/failure_scans/BL-SANITY-002.md`
- `docs/evidence/2026-07-07-sanity-logic-repair/README.md`
- `docs/evidence/2026-07-07-sanity-logic-repair/manifest.json`
- `docs/evidence/2026-07-07-sanity-logic-repair/runtime_identity.json`
- PR #4: https://github.com/lennertvhoy/StateDD_Template/pull/4
- GitHub Actions run: https://github.com/lennertvhoy/StateDD_Template/actions/runs/28889982468

### Notes
- State files updated: BL-SANITY-002 moved to CLOSED in BACKLOG.md, NEXT_ACTIONS.md now tracks BL-WORKFLOW-002 re-validation, STATUS.md open failures cleared.
- Closure sequence completed: evidence folder committed and pushed, PR #4 opened, GitHub Actions docs check SUCCESS, `scripts/statedd_remote_closure_finalizer.py --pr 4` passed with closure label `CI verified`.
- PR #4 is pending human review/merge acceptance; BL-WORKFLOW-002 should be re-validated after BL-SANITY-002 merges.

## 2026-07-03 / 2026-07-07 - Worktree isolation and anti-brittleness guardrails (BL-WORKFLOW-002)

**Type:** template_maintenance_capability
**Status:** CLOSURE_GRADE_CI_VERIFIED
**Git Head:** 0c2a13639894cd799506a9a5e94ecb1f3a070ffe on branch bl-workflow-002-worktree-brittleness
**Worktree:** clean
**Gate Level:** 2 (slice closure) / remote closure verified

### What changed
- Added `scripts/statedd_worktree_guard.py` and regression tests for pre-slice, classification, and closure worktree checks.
- Added `ANTI_BRITTLENESS_GUARD.md`, `docs/quality_gates/ANTI_BRITTLENESS_GATE.md`, `scripts/statedd_brittleness_check.py`, and audit marker checks.
- Updated startup prompts, slice contract, evidence README, CTO review, final handoff, audit, handoff helper, initializer, upgrade helper, asset registries, schemas, CI, and state docs.
- Re-validated the slice after BL-SANITY-002 logic repairs and updated evidence to final PR head `0c2a136`.

### Verification
- `python3 scripts/test_worktree_guard.py` passed.
- `python3 scripts/test_brittleness_check.py` passed.
- `python3 scripts/check_state_docs.py` passed.
- `python3 scripts/statedd_validate_schema.py` passed.
- `python3 scripts/test_init_template.py` passed.
- `python3 scripts/test_upgrade.py` passed.
- `python3 scripts/statedd_worktree_guard.py --mode start-slice` passed on clean commit `0c2a136`.
- `python3 scripts/statedd_audit.py --strict` passed on clean commit `0c2a136`.
- `python3 scripts/statedd_quality_gate.py --gate-level 2` passed.
- `python3 scripts/statedd_closure_check.py` passed.
- `python3 scripts/statedd_runtime_truth_check.py` passed.
- `python3 scripts/statedd_evidence_type_check.py` passed.
- `python3 -m pytest scripts/test_*.py -q` passed: 144 passed, 4 subtests passed.
- `python3 scripts/statedd_remote_closure_finalizer.py --pr 4 --verbose` passed with closure label `CI verified`.

### Evidence
- `docs/EVIDENCE_LOG.md` entry `EV-2026-07-03-001`
- `docs/evidence/2026-07-03-worktree-and-brittleness-guardrails/README.md`
- `docs/evidence/2026-07-03-worktree-and-brittleness-guardrails/command_outputs/`
- `docs/evidence/2026-07-03-worktree-and-brittleness-guardrails/runtime_identity.json`
- `docs/evidence/2026-07-03-worktree-and-brittleness-guardrails/manifest.json`
- PR #4: https://github.com/lennertvhoy/StateDD_Template/pull/4

### Notes
- Closure sequence completed: evidence folder committed and pushed, PR #4 updated, GitHub Actions docs check SUCCESS, `scripts/statedd_remote_closure_finalizer.py --pr 4 --verbose` passed with closure label `CI verified`.
- PR #4 is pending human review/merge acceptance; BL-BROWSER-002 can resume after merge.

## 2026-06-29 - StateDD repo coherence and efficiency repair (BL-SANITY-001)

**Type:** template_maintenance_capability  
**Status:** COMPLETE  
**Git Head:** main at b884f3cef5da340942be3a130b548193bb7e2827  
**Worktree:** clean  
**Gate Level:** 2 (slice closure)  

### What changed
- Reconciled the efficiency layer from the open PR #2 as a minimal salvage:
  - Added `EFFICIENCY_BUDGET.yaml` with hard limits on instruction size, state queues, evidence bundles, and gate runtimes.
  - Added `scripts/statedd_efficiency_check.py` to enforce the budget.
  - Added `scripts/test_efficiency_check.py` with regression tests.
  - Added `fixtures/efficiency_bloat_overcorrection/` regression fixture proving the checker fails on bloat overcorrection.
  - Wired the efficiency check into `scripts/statedd_quality_gate.py` and `scripts/statedd_closure_check.py`.
  - Added `gate_level`, `evidence_max`, `cheapest_proof`, and `escalate_when` metadata to all skills and commands.
  - Added the Efficiency Invariant and Gate Levels to `AGENTS.md`.
- Added backlog structure validation to `scripts/check_state_docs.py`:
  - Fails on duplicate second-level sections such as repeated `## CLOSED`.
  - Fails on duplicate backlog IDs unless explicitly allowed in a history-only section.
  - Added `scripts/test_check_state_docs.py` regression coverage.
- Repaired `BACKLOG.md` to remove duplicate `## CLOSED` sections and duplicate BL-005.
- Repaired remote closure evidence for BL-REMOTE-CLOSURE-001 to match the actual merge commit `ba52e09...`.
- Added `scripts/statedd_post_merge_verify.py` and `scripts/test_post_merge_verify.py` to prove default-branch truth after a PR merges.
- Updated `.github/workflows/validate.yml` to compile and run the new efficiency and sanity checks.
- Updated truth files to reflect BL-SANITY-001 as closed and BL-BROWSER-002 as active.

### Verification
- `python3 -m pytest -q` → 132 passed, 4 subtests passed.
- `python3 scripts/check_state_docs.py --bootstrap-gate` passes.
- `python3 scripts/statedd_validate_schema.py` passes.
- `python3 scripts/statedd_efficiency_check.py --gate-level 2` passes.
- `python3 scripts/statedd_evidence_pack.py check docs/evidence/2026-06-29-sanity-repair --strict` passes.
- GitHub Actions `Validate Template Docs` workflow passes on main at 4396610.

### Evidence
- `docs/EVIDENCE_LOG.md` entry `EV-2026-06-29-002`
- `docs/evidence/2026-06-29-sanity-repair/README.md`
- `docs/evidence/2026-06-29-sanity-repair/runtime_identity.json`
- `docs/evidence/2026-06-29-sanity-repair/manifest.json`

### Notes
- Merged directly to main; PR #2 closed as superseded.
- BL-BROWSER-002 is now the active slice.

## 2026-06-28 - Quality firewall template hardening (BL-QUALITY-001)

**Type:** template_maintenance_capability
**Status:** COMPLETE
**Git Head:** 5dd388fc888fe8e6057046d7c94fc50cffb07da6 before final commit
**Worktree:** dirty during evidence capture

### What changed
- Added reusable quality firewall, failure taxonomy, incident response, failure scan, incident, and quality gate docs.
- Updated the root contract/state/backlog/evidence taxonomy to distinguish product truth, runtime truth, adversarial proof, known bad events, post-deploy evidence, and handoff claims.
- Updated generated downstream templates, schema support, prompt templates, initializer tests, and upgrade tests so new/adopted/upgraded repos receive the generic quality firewall assets.

### Verification
- `python3 scripts/check_state_docs.py` passed.
- `python3 scripts/statedd_validate_schema.py` passed.
- `python3 scripts/test_init_template.py` passed.
- `python3 scripts/test_upgrade.py` passed.
- `python3 scripts/statedd_evidence_pack.py check docs/evidence/2026-06-28-quality-firewall-template --strict` passed.

### Evidence
- `docs/EVIDENCE_LOG.md` entry `EV-2026-06-28-001`
- `docs/evidence/2026-06-28-quality-firewall-template/README.md`

## 2026-06-23 - Public usability and release-readiness polish (BL-007)

**Type:** template_maintenance_docs
**Status:** COMPLETE
**Git Head:** 6a417c1 before closure commit
**Worktree:** clean after final commit

### What changed
- Rewrote the top half of `README.md` for fast comprehension: "Start here" with copy-paste commands, default `solo` profile, agent paste prompt, and "Start Simple" guidance.
- Added `docs/QUICK_COMMANDS.md` with copy-pasteable commands for new repo, adopt, upgrade, daily checks, closure audit, evidence/runtime proof, handoff helper, and bootstrap gate.
- Improved `docs/ADOPTION_PROFILES.md` with a decision tree and explicit "Default recommendation: `solo`".
- Polished `docs/GETTING_STARTED_5_MIN.md` so a beginner can follow it without reading the full README first; linked to `docs/QUICK_COMMANDS.md` and `docs/ADOPTION_PROFILES.md`.
- Finalized `docs/RELEASE_NOTES_statedd-template-v4.md` as release-candidate ready with a clear note that GitHub release publishing requires explicit human permission.
- Created `docs/evidence/2026-06-23-release-readiness-polish/` with README claim ledger, `runtime_identity.json`, `manifest.json`, and `command_outputs/verification_log.txt`.
- Updated `BACKLOG.md`, `NEXT_ACTIONS.md`, `STATUS.md`, `PROJECT_STATE.yaml`, `CHANGELOG.md`, and `docs/EVIDENCE_LOG.md`.
- Did not implement BL-WB-001, browser automation, OCR, external dependencies, or GitHub release publishing.

### Verification
- `python3 -m py_compile` passed for all listed Python scripts.
- `python3 scripts/statedd_version_check.py` passed.
- `python3 scripts/statedd_validate_schema.py` passed.
- `python3 scripts/check_state_docs.py` passed.
- `python3 scripts/check_state_docs.py --bootstrap-gate` passed.
- `python3 scripts/test_runtime_proof.py` passed.
- `python3 scripts/test_schema_validation.py` passed.
- `python3 scripts/test_evidence_pack.py` passed.
- `python3 scripts/test_upgrade.py` passed.
- `python3 scripts/test_adoption_profiles.py` passed.
- `python3 scripts/test_init_template.py` passed.
- `python3 schemas/examples/schema_prompt_loop/validate_example.py` passed.
- `python3 schemas/examples/schema_prompt_loop/generate_prompt.py` passed.
- `python3 schemas/examples/schema_prompt_loop/test_schema_prompt_loop.py` passed.
- `python3 scripts/statedd_audit.py` passed.
- `python3 scripts/statedd_audit.py --strict` passed after final commit.
- `python3 scripts/statedd_doctor.py` passed.
- `python3 scripts/statedd_evidence_pack.py check docs/evidence/2026-06-23-release-readiness-polish --strict` passed.
- `git diff --check` passed.

### Evidence
- `docs/evidence/2026-06-23-release-readiness-polish/README.md`
- `docs/evidence/2026-06-23-release-readiness-polish/runtime_identity.json`
- `docs/evidence/2026-06-23-release-readiness-polish/manifest.json`
- `docs/evidence/2026-06-23-release-readiness-polish/command_outputs/verification_log.txt`
- `docs/EVIDENCE_LOG.md` entry `EV-2026-06-23-008`

### Notes
- BL-007 is closure-grade but not yet accepted; acceptance is pending human product owner review.
- GitHub release publishing is intentionally deferred until explicitly permitted.

## 2026-06-23 - Provider-agnostic browser verification contract (BL-BROWSER-001)

**Type:** template_maintenance_capability
**Status:** COMPLETE
**Git Head:** eb0cd886e900c2e35ddb8123b9fd599631335f89
**Worktree:** clean after final commit

### What changed
- Renamed the old `BL-WB-001` Kimi-WebBridge-specific backlog item to `BL-BROWSER-001` and documented provider-agnostic browser verification across `BACKLOG.md`, `NEXT_ACTIONS.md`, `STATUS.md`, `PROJECT_STATE.yaml`, `AGENTS.md`, `README.md`, `docs/QUICK_COMMANDS.md`, `docs/RELEASE_NOTES_statedd-template-v4.md`, `docs/ACCEPTANCE_FREEZES.md`, and `CHANGELOG.md`.
- Added acceptance freeze `AF-2026-06-23-004` for BL-007 public usability and release-readiness polish.
- Added `schemas/browser_verification.schema.json` defining `statedd.browser_verification.v1`.
- Added `docs/BROWSER_VERIFICATION.md` documenting the provider-agnostic contract, fallback chain, and audit behavior.
- Added `scripts/statedd_browser_verify.py` with `init`, `check`, `hash`, and `summarize` subcommands.
- Added `scripts/test_browser_verification.py` with regression tests proving Kimi WebBridge, Playwright, agent-native, existing E2E, custom, and manual providers are accepted, no single provider is required, strict mode rejects weak proof, and docs/scripts-only slices remain not applicable.
- Added `fixtures/browser_verification/` with valid/invalid/not-applicable examples.
- Integrated browser verification into `scripts/statedd_validate_schema.py`, `scripts/statedd_audit.py`, `scripts/statedd_doctor.py`, `scripts/check_state_docs.py`, `prompts/EVIDENCE_README_TEMPLATE.md`, `prompts/FINAL_HANDOFF_TEMPLATE.md`, and `.github/workflows/validate.yml`.
- Created `docs/evidence/2026-06-23-provider-agnostic-browser-verification/` with README claim ledger, `runtime_identity.json`, `browser_verification.json`, `manifest.json`, and `command_outputs/verification_log.txt`.
- Did not implement Kimi WebBridge, Playwright, or any browser automation driver as a hard dependency; did not install browsers or add OCR.

### Verification
- `python3 -m py_compile` passed for all listed Python scripts.
- `python3 scripts/statedd_version_check.py` passed.
- `python3 scripts/statedd_validate_schema.py` passed.
- `python3 scripts/check_state_docs.py` passed.
- `python3 scripts/check_state_docs.py --bootstrap-gate` passed.
- `python3 scripts/test_runtime_proof.py` passed.
- `python3 scripts/test_schema_validation.py` passed.
- `python3 scripts/test_evidence_pack.py` passed.
- `python3 scripts/test_upgrade.py` passed.
- `python3 scripts/test_adoption_profiles.py` passed.
- `python3 scripts/test_init_template.py` passed.
- `python3 scripts/test_browser_verification.py` passed.
- `python3 scripts/statedd_audit.py` passed.
- `python3 scripts/statedd_audit.py --strict` passed.
- `python3 scripts/statedd_doctor.py` passed.
- `python3 scripts/statedd_evidence_pack.py check docs/evidence/2026-06-23-provider-agnostic-browser-verification --strict` passed.
- `python3 scripts/statedd_browser_verify.py check docs/evidence/2026-06-23-provider-agnostic-browser-verification --strict` passed.
- `git diff --check` passed.

### Evidence
- `docs/evidence/2026-06-23-provider-agnostic-browser-verification/README.md`
- `docs/evidence/2026-06-23-provider-agnostic-browser-verification/runtime_identity.json`
- `docs/evidence/2026-06-23-provider-agnostic-browser-verification/browser_verification.json`
- `docs/evidence/2026-06-23-provider-agnostic-browser-verification/manifest.json`
- `docs/evidence/2026-06-23-provider-agnostic-browser-verification/command_outputs/verification_log.txt`
- `docs/EVIDENCE_LOG.md` entry `EV-2026-06-23-009`
- `docs/ACCEPTANCE_FREEZES.md` entry `AF-2026-06-23-005`

### Notes
- BL-BROWSER-001 is closure-grade and accepted.
- BL-BROWSER-002 concrete provider integration remains next in the active queue.
- GitHub release publishing remains deferred until explicitly permitted.

## 2026-06-23 - Publish statedd-template-v4 release and clean up

**Type:** release
**Status:** COMPLETE
**Git Head:** 2a9afd47b22d67704e097c93bbb2ca6d16fd08e1
**Worktree:** clean; feature worktree and branch removed

### What changed
- Published GitHub release `v4` for `statedd-template-v4` using `docs/RELEASE_NOTES_statedd-template-v4.md`.
- Removed the `feature/provider-agnostic-browser-verification` worktree and branch after confirming all commits are on `main`.
- Updated `STATUS.md`, `PROJECT_STATE.yaml`, `CHANGELOG.md` to reflect the published release and clean state.

### Verification
- `git tag -a v4` and `git push origin v4` succeeded.
- `gh release create v4` produced https://github.com/lennertvhoy/StateDD_Template/releases/tag/v4.
- `git worktree remove`, `git worktree prune`, and `git branch -d feature/provider-agnostic-browser-verification` succeeded.
- `git status --short` shows clean `main`.

### Notes
- BL-BROWSER-002 remains the only backlog item and is not a release blocker.

## 2026-06-23 - Closure evidence hardening (BL-015)

**Type:** closure_evidence_hardening
**Status:** COMPLETE
**Git Head:** ddc190f before fix; 2a728fe after fix
**Worktree:** clean after final commit

### What changed
- Fixed `docs/evidence/2026-06-23-adoption-ready-evidence-release/README.md` to record `Human override used: yes` with scope/rationale.
- Populated `docs/evidence/2026-06-23-adoption-ready-evidence-release/manifest.json` with non-empty claims C1-C5 and artifacts (README.md, runtime_identity.json, manifest.json).
- Added `manifest_status` enum (`complete`/`skeleton`/`legacy`) to `schemas/evidence_manifest.schema.json`.
- Tightened `scripts/statedd_evidence_pack.py --strict` to reject empty `claims`/`artifacts` unless `manifest_status` is `skeleton` or `legacy`, and to reject `manual_review: required` without `known_limits`.
- Made `scripts/statedd_evidence_pack.py hash` skip `manifest.json` because a manifest cannot hash itself.
- Added regression tests in `scripts/test_evidence_pack.py`.
- Updated `docs/EVIDENCE_LOG.md` with `EV-2026-06-23-006`.

### Verification
- `python3 scripts/test_evidence_pack.py` passed.
- `python3 scripts/statedd_evidence_pack.py check docs/evidence/2026-06-23-adoption-ready-evidence-release --strict` passed.
- `python3 scripts/check_state_docs.py` passed.
- `python3 scripts/statedd_validate_schema.py` passed.
- `python3 scripts/statedd_audit.py --strict` passed after final commit.
- `python3 scripts/statedd_doctor.py` passed after final commit.

### Evidence
- `docs/evidence/2026-06-23-adoption-ready-evidence-release/README.md`
- `docs/evidence/2026-06-23-adoption-ready-evidence-release/manifest.json`
- `docs/EVIDENCE_LOG.md` entry `EV-2026-06-23-006`

### Notes
- This is a post-closure hardening slice; no new features were added.
- The human override status is now consistent across handoff, WORKLOG, EVIDENCE_LOG, and evidence README.

## 2026-06-23 - Adoption-ready template release (BL-012/013/014)

**Type:** template_maintenance_release
**Status:** COMPLETE
**Git Head:** eba0e42 before closure commit; 9fb756b after closure commit
**Worktree:** clean after final commit

### What changed
- Added evidence pack manifests and a redaction gate (`schemas/evidence_manifest.schema.json`, `scripts/statedd_evidence_pack.py`, `scripts/test_evidence_pack.py`).
- Added non-destructive downstream upgrade tooling (`scripts/statedd_upgrade.py`, `scripts/test_upgrade.py`, `docs/UPGRADING.md`).
- Added adoption profiles `minimal`, `solo`, `team`, `regulated` to `scripts/init_template.py` and `docs/ADOPTION_PROFILES.md`.
- Added interactive bootstrap wizard MVP (`scripts/statedd_bootstrap_wizard.py`) with `--answers` and `--dry-run` modes.
- Added `scripts/test_adoption_profiles.py` and wired profile/wizard tests into `.github/workflows/validate.yml`.
- Updated `scripts/check_state_docs.py` to skip optional deep-reference docs for the `minimal` profile.
- Fixed `scripts/statedd_audit.py` so `manifest.json` is not treated as a browser artifact.
- Updated `BACKLOG.md`, `NEXT_ACTIONS.md`, `STATUS.md`, `PROJECT_STATE.yaml`, `CHANGELOG.md`, `docs/EVIDENCE_LOG.md`, and created `docs/evidence/2026-06-23-adoption-ready-evidence-release/`.
- Pushed four commits to `origin/main`.

### Verification
- `python3 scripts/test_evidence_pack.py` passed.
- `python3 scripts/test_upgrade.py` passed.
- `python3 scripts/test_adoption_profiles.py` passed.
- `python3 scripts/test_init_template.py` passed.
- `python3 scripts/test_runtime_proof.py` passed.
- `python3 scripts/test_schema_validation.py` passed.
- `python3 scripts/statedd_validate_schema.py` passed.
- `python3 scripts/check_state_docs.py` passed.
- `python3 scripts/statedd_audit.py --strict` passed after closure commit.
- `python3 scripts/statedd_doctor.py` passed after closure commit.
- `python3 scripts/statedd_evidence_pack.py check docs/evidence/2026-06-23-adoption-ready-evidence-release --strict` passed.

### Evidence
- `docs/evidence/2026-06-23-adoption-ready-evidence-release/README.md`
- `docs/evidence/2026-06-23-adoption-ready-evidence-release/runtime_identity.json`
- `docs/evidence/2026-06-23-adoption-ready-evidence-release/manifest.json`
- `docs/EVIDENCE_LOG.md` entry `EV-2026-06-23-005`

### Notes
- Work was executed directly on `main` per explicit human override.
- Next recommended slices are BL-005 example project, BL-007 release metadata, and BL-WB-001 browser automation.

## 2026-06-23 - Schema-backed validation integrated

**Type:** template_validation_hardening
**Status:** COMPLETE
**Git Head:** e3e555df0c058f4404ee2104c41ceef7e37cee4a before implementation commit
**Worktree:** clean before work; dirty during implementation and evidence capture; clean required after final commit

### What changed
- Added executable schemas/contracts under `schemas/` for `PROJECT_STATE.yaml`, `PROJECT_DNA.yaml`, `PROJECT_ADAPTER.yaml`, `runtime_identity.json`, evidence README files, and final handoff template markers.
- Added `scripts/statedd_validate_schema.py`, a stdlib-only validator with a StateDD YAML parser and focused JSON Schema subset.
- Added `scripts/test_schema_validation.py` plus valid/invalid schema fixtures covering invalid project state, invalid evidence README, runtime not applicable, and runtime required but unreachable.
- Wired schema validation into `scripts/check_state_docs.py`, `scripts/statedd_audit.py`, `scripts/statedd_doctor.py`, `.github/workflows/validate.yml`, `scripts/init_template.py`, and initializer regression tests.
- Updated README, scripts docs, getting-started docs, upgrade docs, evidence template, state files, backlog, and active queue.

### Verification
- `python3 -m py_compile scripts/check_state_docs.py scripts/init_template.py scripts/statedd_version_check.py scripts/statedd_handoff.py scripts/statedd_audit.py scripts/statedd_doctor.py scripts/statedd_runtime_proof.py scripts/statedd_validate_schema.py scripts/test_init_template.py scripts/test_runtime_proof.py scripts/test_schema_validation.py` passed.
- `python3 scripts/statedd_validate_schema.py` passed.
- `python3 scripts/test_schema_validation.py` passed.
- `python3 scripts/statedd_version_check.py` passed.
- `python3 scripts/check_state_docs.py` passed.
- `python3 scripts/check_state_docs.py --bootstrap-gate` passed.
- `python3 scripts/test_runtime_proof.py` passed.
- `python3 scripts/test_init_template.py` passed.
- Fixture schema validation passed for `fixtures/bootstrap_dry_run/bootstrap`, `fixtures/bootstrap_dry_run/operating`, and `fixtures/messy_inherited_repo/bootstrap`.
- `python3 scripts/statedd_audit.py` passed after implementation commit.
- `python3 scripts/statedd_audit.py --strict` passed after implementation commit.
- `python3 scripts/statedd_doctor.py` passed after implementation commit.

### Evidence
- `docs/evidence/2026-06-23-schema-backed-validation/README.md`
- `docs/evidence/2026-06-23-schema-backed-validation/runtime_identity.json`
- `docs/EVIDENCE_LOG.md` entry `EV-2026-06-23-004`

### Notes
- The evidence README contract is a minimal BL-012 seed only.
- Redaction scanning, full evidence-pack manifests, downstream upgrade tooling, adoption profiles/wizard UX, browser automation, canonical example project, and release metadata were intentionally out of scope.
- The template root has no application runtime, so its runtime identity artifact records `runtime.required=false`.

## 2026-06-23 - Runtime proof hardening and integration

**Type:** template_runtime_evidence
**Status:** COMPLETE
**Git Head:** starts at 7ba2a9e72da3860ebb42ba00c614a5a75228c2b3; final implementation commit recorded in git history and handoff
**Worktree:** clean before work; clean after implementation commit and final hygiene rerun

### What changed
- Hardened `scripts/statedd_runtime_proof.py` so remote endpoints do not trigger local process ownership detection by default.
- Added explicit `--expect-local` / `--local-process-proof` override for cases where the user intentionally wants local process proof for a non-local-looking URL.
- Added `scripts/test_runtime_proof.py` covering localhost, 127.0.0.1, remote skip for default 443, and explicit override.
- Wired `scripts/statedd_runtime_proof.py` into new and adopted repo initialization, with regression assertions in `scripts/test_init_template.py`.
- Added CI compile coverage, runtime proof unit coverage, and a docs-only `runtime_identity.json` smoke parse.
- Updated audit and doctor to recognize `runtime_identity.json`; strict audit can fail missing/malformed/schema-invalid runtime identity evidence and unreachable required endpoints.
- Updated evidence and final handoff templates to name the runtime identity artifact directly.
- Stale-labeled root `PROJECT_STATE.yaml` historical git snapshot data instead of presenting stale HEAD/worktree values as live current truth.

### Verification
- `python3 -m py_compile scripts/check_state_docs.py scripts/init_template.py scripts/statedd_version_check.py scripts/statedd_handoff.py scripts/statedd_audit.py scripts/statedd_doctor.py scripts/statedd_runtime_proof.py scripts/test_init_template.py scripts/test_runtime_proof.py` passed.
- `python3 scripts/test_runtime_proof.py` passed.
- `python3 scripts/test_init_template.py` passed.
- `python3 scripts/statedd_version_check.py` passed.
- `python3 scripts/check_state_docs.py` passed.
- `python3 scripts/check_state_docs.py --bootstrap-gate` passed.
- `python3 -m json.tool docs/evidence/2026-06-23-runtime-proof-integration/runtime_identity.json` passed.
- `python3 scripts/statedd_audit.py` passed after implementation commit.
- `python3 scripts/statedd_audit.py --strict` passed after implementation commit.
- `python3 scripts/statedd_doctor.py` passed after implementation commit.

### Evidence
- `docs/evidence/2026-06-23-runtime-proof-integration/README.md`
- `docs/evidence/2026-06-23-runtime-proof-integration/runtime_identity.json`
- `docs/EVIDENCE_LOG.md` entry `EV-2026-06-23-003`

### Notes
- JSON schema files, evidence manifests, redaction checks, Docker/container process ownership, browser automation, release metadata, and downstream upgrade automation were intentionally out of scope.
- The template root has no application runtime, so its runtime identity artifact records `runtime.required=false`.
- [BL-010] schema-backed validation is the next active slice.

## 2026-06-23 - Template-maintenance mode split

**Type:** template_state_governance
**Status:** COMPLETE
**Git Head:** d79e1da53a294079f7e4cc9e7edd83b78deb89fa
**Worktree:** clean before work; clean after implementation commit and audit

### What changed
- Added explicit `repo_role` and `statedd_mode` semantics for template root versus downstream repositories.
- Updated root `AGENTS.md`, `PROJECT_STATE.yaml`, `PROJECT_DNA.yaml`, `PROJECT_ADAPTER.yaml`, and `STATUS.md` so the template root is `repo_role: template_repository` and `statedd_mode: template-maintenance`.
- Updated `scripts/init_template.py` so generated and adopted repos start as `repo_role: downstream_project` and `statedd_mode: bootstrap`.
- Made `scripts/check_state_docs.py`, `scripts/statedd_audit.py`, and `scripts/statedd_doctor.py` mode-aware.
- Updated initializer tests and fixtures to cover template-maintenance and downstream bootstrap behavior.
- Updated `README.md`, `docs/GETTING_STARTED_5_MIN.md`, and `docs/UPGRADING.md` with the role/mode distinction.

### Verification
- `python3 -m py_compile scripts/check_state_docs.py scripts/init_template.py scripts/statedd_version_check.py scripts/statedd_handoff.py scripts/statedd_audit.py scripts/statedd_doctor.py scripts/test_init_template.py` passed.
- `python3 scripts/statedd_version_check.py` passed.
- `python3 scripts/check_state_docs.py` passed.
- `python3 scripts/check_state_docs.py --bootstrap-gate` passed for the root template-maintenance repo.
- `python3 scripts/test_init_template.py` passed, including root template-maintenance and generated downstream bootstrap tests.
- Fixture hygiene checks passed for `fixtures/bootstrap_dry_run/bootstrap`, `fixtures/bootstrap_dry_run/operating`, and `fixtures/messy_inherited_repo/bootstrap`.
- `python3 scripts/check_state_docs.py --bootstrap-gate fixtures/bootstrap_dry_run/bootstrap` failed as expected for the intentionally thin dry-run fixture.
- `python3 scripts/check_state_docs.py --bootstrap-gate fixtures/messy_inherited_repo/bootstrap` passed.
- `python3 scripts/statedd_audit.py` passed on a clean worktree after commit `d79e1da`.
- `python3 scripts/statedd_doctor.py` reported closure grade pass after commit `d79e1da`.

### Evidence
- `docs/evidence/2026-06-23-template-maintenance-mode/README.md`
- `docs/EVIDENCE_LOG.md` entry `EV-2026-06-23-002`

### Notes
- Runtime identity proof artifacts were not added; they remain [BL-009].
- Schema-backed validation was not added; it remains [BL-010].

## 2026-06-23 - StateDD version source normalized

**Type:** template_version_governance
**Status:** COMPLETE
**Git Head:** d5ae473c2e4c129978fe5a56b30dae4c044e7f09
**Worktree:** clean before work; dirty after local edits pending handoff

### What changed
- Added `VERSION` as the canonical StateDD spec-version source.
- Added `CHANGELOG.md`, `docs/UPGRADING.md`, and `scripts/statedd_version_check.py`.
- Wired the version check into `scripts/check_state_docs.py`, `scripts/test_init_template.py`, `.github/workflows/validate.yml`, and `scripts/init_template.py`.
- Normalized root `PROJECT_ADAPTER.yaml` from the stale adapter version to `statedd-template-v4`.
- Aligned fixture `AGENTS.md`, `PROJECT_STATE.yaml`, and `PROJECT_DNA.yaml` version identifiers to `statedd-template-v4`.
- Added CTO-review backlog slices for versioning, runtime proof, schema validation, template-maintenance split, and evidence/redaction hardening.
- Updated `STATUS.md`, `PROJECT_STATE.yaml`, `PROJECT_DNA.yaml`, `BACKLOG.md`, and `NEXT_ACTIONS.md` to reflect current template-maintenance truth.

### Verification
- `python3 -m py_compile scripts/check_state_docs.py scripts/init_template.py scripts/statedd_version_check.py scripts/test_init_template.py` passed.
- `python3 scripts/statedd_version_check.py` passed.
- `python3 scripts/check_state_docs.py` passed.
- `python3 scripts/test_init_template.py` passed.
- Fixture hygiene checks passed for `fixtures/bootstrap_dry_run/bootstrap`, `fixtures/bootstrap_dry_run/operating`, and `fixtures/messy_inherited_repo/bootstrap`.
- `python3 scripts/check_state_docs.py --bootstrap-gate fixtures/bootstrap_dry_run/bootstrap` failed as expected for the intentionally thin dry-run fixture.
- `python3 scripts/check_state_docs.py --bootstrap-gate fixtures/messy_inherited_repo/bootstrap` passed.
- `python3 scripts/check_state_docs.py --bootstrap-gate` still fails because root bootstrap system/repo investigation remains incomplete.

### Evidence
- `docs/evidence/2026-06-23-statedd-version-source/README.md`
- `docs/EVIDENCE_LOG.md` entry `EV-2026-06-23-001`

### Notes
- GitHub release publishing was not performed from this local session.
- [BL-011] is the next recommended slice because root template-maintenance truth is still mixed with generated downstream-project truth.

## 2026-06-14 - Dynamic CTO tool/model routing added

**Type:** template_prompt_governance
**Status:** COMPLETE
**Git Head:** c76dad7
**Worktree:** dirty before work; pre-existing changes were observed in `LICENSE`, `README.md`, and `security_best_practices_report.md`

### What changed
- Added `prompts/TOOL_MODEL_ROUTING_GUIDE.md` for CTO-lane routing of tools, models, settings, context strategy, and tailored prompts.
- Updated `prompts/CTO_SESSION_PROMPT.md`, `prompts/CODING_AGENT_STARTUP_PROMPT.md`, `AGENTS.md`, `PROJECT_DNA.yaml`, `PROJECT_ADAPTER.yaml`, `PROJECT_STATE.yaml`, and `README.md` to reference the routing behavior.
- Updated `scripts/init_template.py` so new/adopted repos receive the routing guide and state pointers.
- Updated `scripts/check_state_docs.py` and `scripts/test_init_template.py` to validate the new guide and initializer coverage.

### Verification
- `python3 scripts/check_state_docs.py` passed.
- `python3 scripts/test_init_template.py` passed.
- `python3 scripts/check_state_docs.py --bootstrap-gate` failed because the template repo remains in bootstrap with system/repo investigation still false and no real active queue.

### Evidence
- `docs/EVIDENCE_LOG.md` entry `EV-2026-06-14-001`

### Notes
- Specific GPT, DeepSeek, or other provider claims were not encoded as template truth because model catalogs, pricing, context windows, and availability are time-sensitive.
- The routing guide requires current primary-source verification when concrete model facts affect a recommendation.

## 2026-06-14 - Feedback-filtered usability slice added

**Type:** template_usability
**Status:** COMPLETE
**Git Head:** c76dad7
**Worktree:** dirty before work; existing uncommitted changes were preserved

### Feedback evaluated
- Integrated: beginner 5-minute start guide.
- Integrated: dedicated OpenCode startup prompt.
- Integrated: lightweight read-only handoff helper.
- Deferred: large example project suite because it adds maintenance burden and should be designed as a separate slice.
- Deferred: GitHub description/topics/release because it is repository-hosting metadata, not locally verifiable template behavior in this slice.
- Deferred: license FAQ because the license text was already in flux in uncommitted changes and should not be mixed into this workflow usability slice.
- Deferred: automated screenshot/evidence capture because it needs a separate design to avoid false runtime proof.

### What changed
- Added `docs/GETTING_STARTED_5_MIN.md`.
- Added `prompts/OPENCODE_STARTUP_PROMPT.md`.
- Added `scripts/statedd_handoff.py`.
- Updated README navigation, docs/scripts README files, template state pointers, initializer support assets, validator requirements, and initializer regression tests.

### Verification
- `python3 -m py_compile scripts/statedd_handoff.py scripts/init_template.py scripts/check_state_docs.py scripts/test_init_template.py` passed.
- `python3 scripts/check_state_docs.py` passed.
- `python3 scripts/test_init_template.py` passed.
- `python3 scripts/statedd_handoff.py --no-include-listeners --test-command "python3 scripts/check_state_docs.py"` passed and printed repo identity plus validation output.
- `python3 scripts/check_state_docs.py --bootstrap-gate` failed because the template repo remains in bootstrap with system/repo investigation still false and no real active queue.

### Evidence
- `docs/EVIDENCE_LOG.md` entry `EV-2026-06-14-002`

### Notes
- The handoff helper is intentionally read-only and labels runtime facts as `not proven` unless directly captured.
- The repo remains in bootstrap mode.

## 2026-06-14 - License changed to reserve teaching rights

**Type:** license_policy_update
**Status:** COMPLETE
**Git Head:** c76dad7
**Worktree:** dirty before work; existing uncommitted changes were preserved

### What changed
- Replaced the previous license text with a custom `StateDD Free Use License - Teaching Rights Reserved`.
- Added `LICENSE_FAQ.md` with plain-language examples.
- Updated `README.md`, `PROJECT_STATE.yaml`, `PROJECT_DNA.yaml`, and `scripts/init_template.py` so the license and FAQ are part of the new-repo template surface.
- Updated `scripts/check_state_docs.py` and `scripts/test_init_template.py` to validate the license policy and ensure new repos include `LICENSE_FAQ.md`.

### Verification
- `python3 scripts/check_state_docs.py` passed.
- `python3 scripts/test_init_template.py` passed.
- `python3 -m py_compile scripts/init_template.py scripts/check_state_docs.py scripts/test_init_template.py` passed.
- `python3 scripts/check_state_docs.py --bootstrap-gate` failed because the template repo remains in bootstrap with system/repo investigation still false and no real active queue.

### Evidence
- `docs/EVIDENCE_LOG.md` entry `EV-2026-06-14-003`

### Notes
- The policy now permits free use, commercial use, distribution, modification, sublicensing, and selling copies/services that use the Software.
- Teaching, training, coaching, courses, workshops, tutorials, curricula, educational products, and educational services based on the Software or StateDD workflow are reserved rights unless prior written permission is granted.
- This is a custom license draft and should be reviewed by a qualified lawyer before relying on it commercially.

## 2026-06-23 - BL-005 canonical schema/prompt example and BL-007 release-prep draft

**Type:** template_workflow_upgrade
**Status:** COMPLETE
**Git Head:** 0c17d4f
**Worktree:** clean

### What changed
- Added acceptance freeze `AF-2026-06-23-002` for the BL-012/013/014 adoption-ready template release, pinning accepted HEAD to `9f940ddd5c00f11896df6ab5b14bfe0dfe18bf8f`.
- Added `schemas/examples/schema_prompt_loop/`, a stdlib-only canonical example of StateDD's schema-driven loop.
  - `feature_slice.schema.json` defines a small "feature slice" contract.
  - `valid_slice.json` passes schema validation.
  - `invalid_slice.json` fails schema validation with a useful error.
  - `generate_prompt.py` generates a deterministic prompt/checklist from the schema.
  - `generated_prompt.md` is a checked-in fixture; the test fails if it drifts.
  - `validate_example.py` and `test_schema_prompt_loop.py` exercise the loop.
- Linked the schema/prompt example from `README.md` and `docs/GETTING_STARTED_5_MIN.md`.
- Wired the example into `.github/workflows/validate.yml` for compilation and test coverage.
- Added draft release notes and repository metadata in `docs/RELEASE_NOTES_statedd-template-v4.md`.
- Updated `BACKLOG.md`, `NEXT_ACTIONS.md`, `STATUS.md`, `PROJECT_STATE.yaml`, and `CHANGELOG.md`.

### Verification
- `python3 -m py_compile schemas/examples/schema_prompt_loop/*.py` passed.
- `python3 schemas/examples/schema_prompt_loop/validate_example.py` passed.
- `python3 schemas/examples/schema_prompt_loop/generate_prompt.py` passed.
- `python3 schemas/examples/schema_prompt_loop/test_schema_prompt_loop.py` passed.
- `python3 scripts/statedd_validate_schema.py` passed.
- `python3 scripts/test_init_template.py` passed.
- `python3 scripts/check_state_docs.py` passed.
- `python3 scripts/check_state_docs.py --bootstrap-gate` passed.
- `python3 scripts/statedd_audit.py --strict` passed after each commit.
- `python3 scripts/statedd_doctor.py` passed.

### Evidence
- `docs/evidence/2026-06-23-canonical-schema-prompt-example/README.md`
- `docs/evidence/2026-06-23-canonical-schema-prompt-example/manifest.json`
- `docs/EVIDENCE_LOG.md` entry `EV-2026-06-23-007`

### Notes
- BL-005 is accepted and frozen as `AF-2026-06-23-003`.
- BL-007 remains a draft; no GitHub release was published.
- The next backlog item is `BL-WB-001` Kimi WebBridge browser verification.

## 2026-06-14 - StateDD v2 executable workflow

**Type:** template_workflow_upgrade
**Status:** COMPLETE
**Git Head:** 0d406e6
**Worktree:** dirty before final commit

### What changed
- Added `scripts/statedd_audit.py` for machine-checkable closure audits.
- Added `scripts/statedd_doctor.py` for fast health summaries.
- Added `prompts/SLICE_CONTRACT_TEMPLATE.md` for formal slice contracts.
- Added `prompts/EVIDENCE_README_TEMPLATE.md` for claim ledgers.
- Added `prompts/SCHEMA_OWNERSHIP_TEMPLATE.md` enforcing canonical schemas, generated examples/prompts, validation tests, `schemaVersion`, and migration policy.
- Added `prompts/SUBAGENT_REVIEW_TEMPLATE.md` for strict subagent output.
- Added `prompts/CTO_REVIEW_CHECKLIST.md` for repeatable CTO review.
- Added `docs/adr/README.md` and `docs/adr/0000-adr-template.md`.
- Added `docs/WORKFLOW_FOR_BEGINNERS.md` with a Mermaid diagram, prompt map, and quality checklist.
- Updated `AGENTS.md` with the Human Override Rule and v2 tool list.
- Updated `prompts/FINAL_HANDOFF_TEMPLATE.md` with four-state closure, release/update gate, and override wording.
- Updated `prompts/CTO_SESSION_PROMPT.md` and `prompts/CODING_AGENT_STARTUP_PROMPT.md` to reference v2 assets.
- Updated `scripts/init_template.py`, `scripts/check_state_docs.py`, `scripts/statedd_handoff.py`, and `scripts/test_init_template.py` to ship and validate v2 assets.
- Updated `.github/workflows/validate.yml` to compile and exercise v2 scripts.
- Updated `README.md`, `docs/GETTING_STARTED_5_MIN.md`, `STATUS.md`, `PROJECT_STATE.yaml`, `PROJECT_DNA.yaml`, `BACKLOG.md`, and `NEXT_ACTIONS.md`.

### Verification
- `python3 -m py_compile scripts/check_state_docs.py scripts/init_template.py scripts/statedd_handoff.py scripts/statedd_audit.py scripts/statedd_doctor.py scripts/test_init_template.py` passed.
- `python3 scripts/check_state_docs.py` passed.
- `python3 scripts/test_init_template.py` passed, including new v2 asset tests and `test_doctor_runs`.
- `python3 scripts/statedd_doctor.py` produced the expected health summary.
- `python3 scripts/statedd_audit.py` on the template root failed only on dirty worktree, as expected during implementation.
- `python3 scripts/statedd_audit.py` on a freshly generated demo repo passed.
- Generated repo smoke test passed.

### Evidence
- `docs/evidence/2026-06-14-statedd-v2-executable-workflow/README.md`
- `docs/EVIDENCE_LOG.md` entry `EV-2026-06-14-004`

### Notes
- The template repo remains in bootstrap mode.
- The SkillSignal-specific canonical schema/export/import loop is a downstream application of the new `SCHEMA_OWNERSHIP_TEMPLATE.md`, not implemented in this slice.
- The Human Override Rule was added explicitly so the workflow stays a strong default, not a prison.
- Subagent review feedback was integrated: fixed `.jpg` suffix detection, expanded override marker checks, hardened `statedd_doctor.py` file reads, added `AGENTS.md` freshness to doctor output, and aligned generated `PROJECT_DNA.yaml` / `PROJECT_ADAPTER.yaml` versions to v4.

## 2026-07-11 - BL-MAX-VALUE-001 local implementation proof

**Type:** correctness_and_lifecycle_repair
**Status:** LOCALLY_VALIDATED_REMOTE_PENDING
**Git Head:** ae851d05aa8113c3cde90d122d1723be123d9e37
**Worktree:** isolated; finalization metadata pending commit

### What changed
- Replaced historical-manifest-driven upgrades with current-catalog desired state,
  strict ownership validation, transactional writes/rollback, and idempotent reruns.
- Made the quality gate automatically discover and aggregate applicable suites;
  CI invokes that single authority path instead of enumerating test files.
- Hardened initializer/upgrade/evidence/runtime paths against absolute, traversal,
  root/nested symlink, unsafe-source, and outside-root behavior.
- Added reproducible proof-head profile/context metrics and strict runtime identity
  v2 records without absolute checkout paths or raw process arguments.
- Strengthened exact-head remote closure, agent worktree attribution, evidence
  contracts, architecture review, and the controlled benchmark specification.

### Verification
- `python3 -m pytest scripts/ -q`: 289 passed, 4 subtests passed.
- `python3 -m pytest schemas/examples/ -q`: 5 passed.
- Canonical profile metrics reproduce against `ae851d05`.
- `python3 scripts/statedd_quality_gate.py --gate-level 2` passed.
- Strict evidence and runtime-not-applicable truth checks passed locally.

### Evidence
- `docs/evidence/2026-07-11-maximum-value-correctness/README.md`
- `docs/evidence/2026-07-11-maximum-value-correctness/manifest.json`
- `docs/metrics/profile_metrics.json`
- `docs/EVIDENCE_LOG.md` entry `EV-2026-07-11-002`

### Notes
- This is local implementation/evidence truth only. Remote branch, PR, exact-head
  CI, finalizer agreement, merge, and human acceptance remain unproven.
## 2026-07-11 - Open BL-STATEDD-INTEGRATION-001

**Type:** integration_slice_opening
**Status:** OPEN
**Git Head:** 84a67100fee324f6716a5c966500b0c0eeb59699
**Worktree:** clean before state-opening edit

### What changed
- Opened one superseding integration slice from PR #6's exact head.
- Recorded PR #6 as the lifecycle/profile/gate/evidence authority and PR #7 as the Git-safety and coding-agent golden-path source candidate.
- Preserved the original checkout outside this clone and recorded its local repair as reported, not closure-grade truth.
- Added the mandatory integration failure scan and kept license ownership and benchmark superiority unproven.

### Verification
- Fresh full clone has an independent Git common directory.
- Clone-mode Git-safety preflight passed with zero ownership mismatches, fsck pass, synchronization pass, and write probe pass.
- Branch `bl-statedd-integration-001` points to PR #6 head before state-opening edits.

### Next
- Commit this state opening, then port PR #7 semantically without downgrading PR #6 architecture.

## 2026-07-11 - Locally validate BL-STATEDD-INTEGRATION-001

**Type:** integration_slice_local_validation
**Status:** VALIDATED_LOCALLY_REMOTE_PENDING
**Git Head:** 2644f438d40e38f87adc3ca52e678452233430d3
**Proof Head:** 437fc01d589a72a42aa75b12357ae49586302f34
**Worktree:** clean before publication

### What changed
- Ported PR #7 Git-safety, mutation permits, clone-default agent isolation,
  agent-first startup workflow, delivery policy, and structured golden-path
  regression onto PR #6's declarative profile/lifecycle/gate/evidence base.
- Repaired the confirmed quality-gate aggregation, root-symlink, profile-lock,
  CI-subject, and bootstrap-coverage regressions.
- Added structured bootstrap application, complete isolation/integration proof,
  v2 profile conformance, strict evidence, and local finalizer boundaries.

### Verification
- `python3 -m pytest scripts/ -q`: 312 tests passed.
- `python3 -m pytest schemas/examples/ -q`: 5 tests passed.
- `python3 scripts/test_golden_path.py`: passed.
- `python3 scripts/statedd_quality_gate.py --gate-level 2 --verbose`: passed.
- `python3 scripts/statedd_audit.py --strict --evidence-folder docs/evidence/2026-07-11-statedd-integration`: passed.
- All profile metrics reproduce from the recorded proof head; strict evidence and runtime-not-applicable checks pass.

### Evidence
- `docs/evidence/2026-07-11-statedd-integration/README.md`
- `docs/evidence/2026-07-11-statedd-integration/manifest.json`
- `docs/metrics/profile_metrics.json`
- `docs/EVIDENCE_LOG.md` entry `EV-2026-07-11-003`

### Next
- Run remote-mutation safety preflight, push the branch, open one draft PR, and observe automatic CI without reruns.

## 2026-07-11 - Open BL-OKF-001

**Type:** architecture_slice_opening
**Status:** OPEN
**Git Head:** b9712a514d25b799a35a10bac35e00fc713a620e
**Worktree:** clean before state-opening edit

### What changed
- Opened a separate OKF interoperability slice from the published PR #8 head.
- Preserved StateDD as the canonical operational-state authority and kept PR #8 narrow.
- Recorded OKF v0.1 as a pinned draft upstream specification and limited this slice to the optional contained knowledge layer.
- Recorded the user-directed override to proceed while the PR #8 draft remains unsettled.

### Next
- Implement the optional `knowledge_okf` module, contained scaffold, validator, provenance extension, and staleness checks.

## 2026-07-11 - Locally validate BL-OKF-001

**Type:** architecture_slice_local_validation
**Status:** VALIDATED_LOCALLY_REMOTE_PENDING
**Git Head:** 1210947c1ed551e47fd700318f4e9254ba42f0a5
**Proof Head:** 1e434d4e5b2dae2e91146d81c5eb430cc0d6e21d
**Worktree:** clean before publication

### What changed
- Added the optional `knowledge_okf` asset set with explicit `new` and `adopt` selection.
- Added the contained OKF v0.1 scaffold, standard-library-only validator, StateDD extension schema, source-hash staleness checks, and permissive base-format behavior.
- Preserved ordinary profile assets and startup context; the optional module is not installed unless selected.

### Verification
- `python3 -m pytest scripts/ -q`: passed.
- `python3 -m pytest schemas/examples/ -q`: 5 passed.
- `python3 scripts/test_okf_validate.py`: 10 passed.
- Explicit minimal `knowledge_okf` generation and level-1 conformance: passed.
- `python3 scripts/statedd_quality_gate.py --gate-level 2 --verbose`: passed.
- `python3 scripts/statedd_audit.py --strict --evidence-folder docs/evidence/2026-07-11-okf-interoperability`: passed.
- Strict evidence pack, schema validation, state hygiene, and efficiency checks: passed.

### Evidence
- `docs/evidence/2026-07-11-okf-interoperability/README.md`
- `docs/evidence/2026-07-11-okf-interoperability/manifest.json`
- `docs/metrics/profile_metrics.json`
- `docs/EVIDENCE_LOG.md` entry `EV-2026-07-11-004`

### Next
- Run remote-mutation safety preflight, push the branch, open one separate draft PR, and observe automatic CI without reruns.

## 2026-07-11 - Publish and remotely validate BL-OKF-001

**Type:** architecture_slice_remote_validation
**Status:** PUSHED_DRAFT_PR_CI_PASSING
**Proof Head:** 98c53265c36649d3c58b0e61a8e8d7ecba8beb48
**Final PR Head:** e8500374dbcdf4518f1ee420fdc79c366fc3ac3b
**Branch:** bl-okf-001
**PR:** https://github.com/lennertvhoy/StateDD_Template/pull/9

### What changed
- Corrected the template footprint budget after CI measured the final committed tree at 2,173,706 bytes.
- Refreshed reproducible profile metrics and advanced the proof head after the source/configuration correction.
- Published one separate draft PR; PR #8, PR #6, and PR #7 remain unchanged and unmerged.

### Verification
- Direct branch-head CI passed for final head; run `29164232824`.
- Synthetic PR merge-candidate CI passed; run `29164234097`.
- Remote closure finalizer proved local/remote/PR/CI/merge agreement and stopped only because PR #9 remains draft.
- Worktree clean and remote branch contains local HEAD `e8500374dbcdf4518f1ee420fdc79c366fc3ac3b`.

### Next
- Human review of draft PR #9; keep unmerged until scope, ownership, and evidence-gated promotion are accepted.

## 2026-07-12 - Promote integrated golden path to main

**Type:** mainline_promotion
**Status:** MERGED_MAIN_CI_PASSING

- Merged PR #8 as `f92d2610a5d2616b71ee40a4e5358cf3f45cc6a2`.
- Merged PR #9 as `840ebaa69b95c1ecda1c2113d53011e4e3dde77d`.
- Merged PR #10 as `886710edc9032465302f8bc6c390fe470f1fde3d` to refresh profile metrics after squash history.
- Main branch-head validation passed in run `29184051017`.
- PR #6 and PR #7 remain superseded draft source candidates and were not merged independently.
