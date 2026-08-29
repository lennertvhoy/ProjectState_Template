# EVIDENCE_LOG.md

**Purpose:** Structured ledger of proof artifacts for user-facing claims.

## Entry Format

```yaml
- ID: EV-YYYY-MM-DD-001
  File: /absolute/path/to/artifact.png
  Title: short description
  Source/System: browser | api | test | log | screenshot
  Route/Page: optional route or URL
  Action: what was done
  Shows:
    - visible fact 1
    - visible fact 2
  Proves:
    - why the artifact matters
  Type: implementation | test | product_behavior | runtime_truth | adversarial | known_bad_event | post_deploy | security_privacy | state_update | docs-render-verification
  as_of: 2026-03-18T18:00:00+01:00
  Notes: optional context
```

## Guidance

- Link evidence to the specific claim it supports.
- Prefer durable artifact paths.
- Place saved artifacts under `docs/evidence/YYYY-MM-DD-<slug>/` when possible.
- Add timestamps for anything that may become stale.
- Treat handoffs as claims; link them to evidence or gate results before accepting closure.
- For user-facing or operator-facing work, prefer product behavior, runtime truth, adversarial, known bad event, and post-deploy evidence over command output alone.

## EV-2026-07-11-004: Optional OKF interoperability foundation

- File: docs/evidence/2026-07-11-okf-interoperability/README.md
- File: docs/evidence/2026-07-11-okf-interoperability/manifest.json
- File: docs/metrics/profile_metrics.json
- Title: BL-OKF-001 optional OKF v0.1 knowledge layer
- Source/System: test | state_update
- Action: Added optional OKF asset selection, contained scaffold, dependency-free validator, StateDD authority/provenance extension, source staleness checks, and conformance tests without changing ordinary profiles.
- Shows:
  - base OKF permissiveness for unknown types, unknown extension keys, broken links, and missing indexes
  - strict StateDD governance for canonical, derived, and reference concepts
  - explicit optional profile installation and footprint budget conformance
  - local level-2 quality, audit, schema, hygiene, and strict evidence success
- Proves:
  - local implementation and validation truth for BL-OKF-001
- Type: test
- as_of: 2026-07-11T20:40:00+02:00
- Notes: OKF v0.1 is pinned to upstream commit `ee67a5ca27044ebe7c38385f5b6cffc2305a9c1a`; remote publication and acceptance remain unproven.

## EV-2026-07-11-003: Integrated lifecycle and Git-safety slice

- File: docs/evidence/2026-07-11-statedd-integration/README.md
- File: docs/evidence/2026-07-11-statedd-integration/manifest.json
- File: docs/metrics/profile_metrics.json
- Title: BL-STATEDD-INTEGRATION-001 local integration evidence
- Source/System: test | log | state_update
- Action: Integrated the PR #6 correctness architecture with the PR #7 Git-safety and coding-agent workflow, then ran the authoritative local gates and strict evidence checks.
- Shows:
  - declarative profile and v2 lifecycle authorities remain active
  - centralized Git-safety and clone-default agent isolation are regression-covered
  - structured bootstrap, isolated-agent integration, profile conformance, and strict evidence pass locally
  - remote branch, GitHub PR, CI, license ownership, benchmark superiority, and human acceptance remain unproven
- Proves:
  - local implementation and validation truth for the integration slice
- Type: test
- as_of: 2026-07-11T18:30:00+02:00
- Notes: Proof head is immutable in the evidence README; the final PR head is mutable remote handoff authority.

## EV-2026-07-07-001: Template logic-hole repair failure scan (BL-SANITY-002)

- File: /home/ff/Documents/Projects/StateDD_Template/docs/failure_scans/BL-SANITY-002.md
- File: /home/ff/Documents/Projects/StateDD_Template/STATUS.md
- File: /home/ff/Documents/Projects/StateDD_Template/NEXT_ACTIONS.md
- File: /home/ff/Documents/Projects/StateDD_Template/BACKLOG.md
- File: /home/ff/Documents/Projects/StateDD_Template/PROJECT_STATE.yaml
- Title: BL-SANITY-002 failure scan and state integration
- Source/System: code review
- Action: Performed an ultra-critical sanity check, identified critical logic holes, integrated BL-SANITY-002 into backlog/state, and produced a failure scan with mitigations.
- Shows:
  - `scripts/statedd_audit.py`, `scripts/statedd_doctor.py`, `scripts/statedd_handoff.py` have false-pass paths
  - `scripts/statedd_runtime_proof.py` and its consumers disagree on `runtime_identity.json` schema
  - `scripts/statedd_worktree_guard.py` and `scripts/statedd_brittleness_check.py` have weak guards
  - `scripts/init_template.py`, `scripts/statedd_upgrade.py`, `scripts/statedd_browser_verify.py`, `scripts/statedd_remote_closure_finalizer.py`, `scripts/statedd_post_merge_verify.py`, `scripts/statedd_probe_guidance.py` have unsafe or brittle behavior
- Proves:
  - The failures are recorded as active P0 problems and linked to a backlog item with a failure scan
- Type: known_bad_event
- as_of: 2026-07-07T19:25:00+02:00
- Notes: Implementation repairs completed in BL-SANITY-002; see EV-2026-07-07-002 for closure evidence.

## EV-2026-07-07-002: Template logic-hole repair closure evidence (BL-SANITY-002)

- File: /home/ff/Documents/Projects/StateDD_Template/docs/evidence/2026-07-07-sanity-logic-repair/README.md
- File: /home/ff/Documents/Projects/StateDD_Template/docs/evidence/2026-07-07-sanity-logic-repair/runtime_identity.json
- File: /home/ff/Documents/Projects/StateDD_Template/docs/evidence/2026-07-07-sanity-logic-repair/manifest.json
- File: /home/ff/Documents/Projects/StateDD_Template/docs/failure_scans/BL-SANITY-002.md
- Title: BL-SANITY-002 template logic-hole repair and regression tests
- Source/System: test
- Action: Repaired the critical logic holes discovered by the 2026-07-07 ultra-critical sanity check and added regression tests; ran the full StateDD gate suite.
- Shows:
  - `python3 scripts/check_state_docs.py` passes
  - `python3 scripts/statedd_validate_schema.py` passes
  - `python3 scripts/statedd_quality_gate.py --gate-level 2` passes
  - `python3 scripts/statedd_audit.py --strict` passes on the clean worktree
  - `python3 scripts/statedd_closure_check.py` passes
  - `python3 scripts/statedd_runtime_truth_check.py` passes
  - `python3 -m pytest scripts/test_*.py -q` passes: 144 passed, 4 subtests passed
- Proves:
  - The identified false-pass, schema-mismatch, worktree/brittleness, and unsafe-file-operation holes are fixed
  - The fixes are guarded by regression tests
- Type: test
- as_of: 2026-07-07T20:40:00+02:00
- Notes: Closure-grade and CI-verified on PR #4 (head 38ac9279ab18cde22e4967acddf2f1c531132574, run 28889982468); merge pending human acceptance.

## EV-2026-07-03-001: Worktree isolation and anti-brittleness guardrails (BL-WORKFLOW-002)

- File: /home/ff/Documents/Projects/StateDD_Template/docs/evidence/2026-07-03-worktree-and-brittleness-guardrails/README.md
- File: /home/ff/Documents/Projects/StateDD_Template/docs/evidence/2026-07-03-worktree-and-brittleness-guardrails/incident_analysis.md
- File: /home/ff/Documents/Projects/StateDD_Template/docs/evidence/2026-07-03-worktree-and-brittleness-guardrails/anti_brittleness_gate_design.md
- File: /home/ff/Documents/Projects/StateDD_Template/scripts/statedd_worktree_guard.py
- File: /home/ff/Documents/Projects/StateDD_Template/scripts/test_worktree_guard.py
- File: /home/ff/Documents/Projects/StateDD_Template/scripts/statedd_brittleness_check.py
- File: /home/ff/Documents/Projects/StateDD_Template/scripts/test_brittleness_check.py
- File: /home/ff/Documents/Projects/StateDD_Template/ANTI_BRITTLENESS_GUARD.md
- File: /home/ff/Documents/Projects/StateDD_Template/docs/quality_gates/ANTI_BRITTLENESS_GATE.md
- Title: BL-WORKFLOW-002 worktree isolation and anti-brittleness guardrails
- Source/System: test
- Action: Added pre-slice worktree/source-of-truth guardrails, dirty-file classification, upstream/topology handoff fields, anti-brittleness review contract, advisory brittleness scanner, audit marker checks, and downstream propagation.
- Shows:
  - `python3 scripts/test_worktree_guard.py` covers clean, dirty, classified, closure, detached, missing-origin, and linked-worktree cases
  - `python3 scripts/test_brittleness_check.py` covers advisory warnings and audit anti-brittleness markers
  - `python3 scripts/test_init_template.py` and `python3 scripts/test_upgrade.py` cover downstream propagation
  - `python3 scripts/check_state_docs.py` and `python3 scripts/statedd_validate_schema.py` validate updated template docs/contracts
- Proves:
  - StateDD now moves dirty/ambiguous worktree detection before non-trivial implementation
  - Closure handoffs expose worktree topology and upstream/GitHub visibility
  - Non-trivial fix/feature closure requires anti-brittleness review rather than only example-specific behavior
- Type: test
- as_of: 2026-07-07T21:05:00+02:00
- Notes: Re-validated after BL-SANITY-002 logic repairs; evidence README, manifest, and runtime_identity.json updated to final PR head 0c2a136. Closure-grade and CI-verified on PR #4; merge pending human acceptance.

## EV-2026-06-29-002: StateDD repo coherence and efficiency repair (BL-SANITY-001)

- File: /home/ff/Documents/Projects/StateDD_Template/docs/evidence/2026-06-29-sanity-repair/README.md
- File: /home/ff/Documents/Projects/StateDD_Template/docs/evidence/2026-06-29-sanity-repair/runtime_identity.json
- File: /home/ff/Documents/Projects/StateDD_Template/docs/evidence/2026-06-29-sanity-repair/manifest.json
- File: /home/ff/Documents/Projects/StateDD_Template/EFFICIENCY_BUDGET.yaml
- File: /home/ff/Documents/Projects/StateDD_Template/scripts/statedd_efficiency_check.py
- File: /home/ff/Documents/Projects/StateDD_Template/scripts/test_efficiency_check.py
- File: /home/ff/Documents/Projects/StateDD_Template/scripts/statedd_post_merge_verify.py
- File: /home/ff/Documents/Projects/StateDD_Template/scripts/test_post_merge_verify.py
- File: /home/ff/Documents/Projects/StateDD_Template/scripts/test_check_state_docs.py
- File: /home/ff/Documents/Projects/StateDD_Template/fixtures/efficiency_bloat_overcorrection/
- Title: BL-SANITY-001 repo coherence and efficiency repair
- Source/System: test
- Action: Salvaged the efficiency layer from PR #2, added backlog structure validation, repaired truth files, repaired remote closure evidence, added a post-merge verifier, and updated CI.
- Shows:
  - `python3 scripts/statedd_efficiency_check.py --gate-level 2` passes
  - `python3 scripts/test_efficiency_check.py` passes
  - `python3 scripts/test_check_state_docs.py` passes
  - `python3 scripts/test_post_merge_verify.py` passes
  - `python3 scripts/check_state_docs.py --bootstrap-gate` passes
  - `python3 scripts/statedd_validate_schema.py` passes
  - `python3 -m pytest -q` → 132 passed, 4 subtests passed
- Proves:
  - StateDD now enforces an Efficiency Invariant and tiered gate levels
  - BACKLOG.md cannot silently accumulate duplicate sections or duplicate IDs
  - Remote closure evidence matches the merge commit recorded by GitHub
  - A post-merge verifier can prove default-branch truth after a PR merges
- Type: test
- as_of: 2026-06-29T11:45:00+02:00
- Notes: Closure-grade. Merged directly to main (4396610). PR #2 closed as superseded. GitHub Actions validate workflow passing. BL-BROWSER-002 is now active.

## EV-2026-06-28-001: StateDD quality firewall template hardening (BL-QUALITY-001)

- File: /home/ff/Documents/Projects/StateDD_Template/docs/evidence/2026-06-28-quality-firewall-template/README.md
- File: /home/ff/Documents/Projects/StateDD_Template/docs/evidence/2026-06-28-quality-firewall-template/runtime_identity.json
- File: /home/ff/Documents/Projects/StateDD_Template/docs/evidence/2026-06-28-quality-firewall-template/manifest.json
- File: /home/ff/Documents/Projects/StateDD_Template/docs/evidence/2026-06-28-quality-firewall-template/command_outputs/check_state_docs.txt
- File: /home/ff/Documents/Projects/StateDD_Template/docs/evidence/2026-06-28-quality-firewall-template/command_outputs/schema_validation.txt
- File: /home/ff/Documents/Projects/StateDD_Template/docs/evidence/2026-06-28-quality-firewall-template/command_outputs/test_init_template.txt
- File: /home/ff/Documents/Projects/StateDD_Template/docs/evidence/2026-06-28-quality-firewall-template/command_outputs/test_upgrade.txt
- Title: BL-QUALITY-001 reusable quality firewall contract
- Source/System: test
- Action: Added generic quality firewall docs, failure taxonomy, incident response, failure scan and quality gate templates, state fields, schema support, generated downstream propagation, upgrade propagation, and prompt/evidence handoff updates.
- Shows:
  - `python3 scripts/check_state_docs.py` passes
  - `python3 scripts/statedd_validate_schema.py` passes
  - `python3 scripts/test_init_template.py` passes and covers generated/adopted quality firewall assets
  - `python3 scripts/test_upgrade.py` passes and covers upgrade propagation
  - `python3 scripts/statedd_evidence_pack.py check docs/evidence/2026-06-28-quality-firewall-template --strict` passes
- Proves:
  - StateDD now includes a reusable failure-discovery layer without making any project-specific bot invariant canonical
  - downstream generated/adopted repos receive quality firewall guidance and structured quality gate/runtime truth scaffolding
- Type: test
- as_of: 2026-06-28T10:02:35+02:00
- Notes: Runtime/browser proof is not applicable for the template root. Downstream projects must adapt the generic gates to their own product domain.

## EV-2026-06-23-009: Provider-agnostic browser verification contract (BL-BROWSER-001)

- File: /home/ff/Documents/Projects/StateDD_Template/docs/evidence/2026-06-23-provider-agnostic-browser-verification/README.md
- File: /home/ff/Documents/Projects/StateDD_Template/docs/evidence/2026-06-23-provider-agnostic-browser-verification/runtime_identity.json
- File: /home/ff/Documents/Projects/StateDD_Template/docs/evidence/2026-06-23-provider-agnostic-browser-verification/browser_verification.json
- File: /home/ff/Documents/Projects/StateDD_Template/docs/evidence/2026-06-23-provider-agnostic-browser-verification/manifest.json
- File: /home/ff/Documents/Projects/StateDD_Template/docs/evidence/2026-06-23-provider-agnostic-browser-verification/command_outputs/verification_log.txt
- File: /home/ff/Documents/Projects/StateDD_Template/schemas/browser_verification.schema.json
- File: /home/ff/Documents/Projects/StateDD_Template/docs/BROWSER_VERIFICATION.md
- File: /home/ff/Documents/Projects/StateDD_Template/scripts/statedd_browser_verify.py
- File: /home/ff/Documents/Projects/StateDD_Template/scripts/test_browser_verification.py
- Title: BL-BROWSER-001 provider-agnostic browser verification contract
- Source/System: test
- Action: Implemented the provider-agnostic browser verification contract, helper script, schema, tests, fixtures, audit/doctor/CI integration, and governance/acceptance updates.
- Shows:
  - `python3 scripts/test_browser_verification.py` passes for Kimi WebBridge, Playwright, agent-native, existing E2E, custom, and manual providers
  - `python3 scripts/test_browser_verification.py` proves no single provider is required and strict mode rejects weak proof
  - `python3 scripts/statedd_audit.py --strict` passes with the new evidence folder
  - `python3 scripts/statedd_browser_verify.py check docs/evidence/2026-06-23-provider-agnostic-browser-verification --strict` passes
  - `python3 scripts/statedd_evidence_pack.py check docs/evidence/2026-06-23-provider-agnostic-browser-verification --strict` passes
  - BL-WB-001 was renamed to BL-BROWSER-001 across governance files
- Proves:
  - StateDD requires browser-verification evidence for user-facing closure, not a specific browser automation provider
  - Kimi WebBridge is a preferred provider when available, not a required dependency
- Type: docs-render-verification
- as_of: 2026-06-23T17:25:00+02:00
- Notes: Closure-grade and accepted. BL-BROWSER-002 concrete provider integration is next.

## EV-2026-06-23-008: Public usability and release-readiness polish (BL-007)

- File: /home/ff/Documents/Projects/StateDD_Template/docs/evidence/2026-06-23-release-readiness-polish/README.md
- File: /home/ff/Documents/Projects/StateDD_Template/docs/evidence/2026-06-23-release-readiness-polish/runtime_identity.json
- File: /home/ff/Documents/Projects/StateDD_Template/docs/evidence/2026-06-23-release-readiness-polish/manifest.json
- File: /home/ff/Documents/Projects/StateDD_Template/docs/evidence/2026-06-23-release-readiness-polish/command_outputs/verification_log.txt
- File: /home/ff/Documents/Projects/StateDD_Template/README.md
- File: /home/ff/Documents/Projects/StateDD_Template/docs/QUICK_COMMANDS.md
- File: /home/ff/Documents/Projects/StateDD_Template/docs/ADOPTION_PROFILES.md
- File: /home/ff/Documents/Projects/StateDD_Template/docs/GETTING_STARTED_5_MIN.md
- File: /home/ff/Documents/Projects/StateDD_Template/docs/RELEASE_NOTES_statedd-template-v4.md
- Title: BL-007 public usability and release-readiness polish
- Source/System: test
- Action: Simplified README top half, added quick commands cheat sheet, improved adoption profile chooser, polished 5-minute guide, finalized release notes as release-candidate ready, and updated state/history files.
- Shows:
  - `python3 scripts/check_state_docs.py` passes after all doc changes
  - `python3 scripts/statedd_audit.py --strict` passes
  - `python3 scripts/statedd_evidence_pack.py check docs/evidence/2026-06-23-release-readiness-polish --strict` passes
  - README opens with a 60-second "Start here" path
  - `docs/ADOPTION_PROFILES.md` explicitly recommends `--profile solo`
  - `docs/RELEASE_NOTES_statedd-template-v4.md` states publishing requires explicit human permission
- Proves:
  - StateDD is easier to choose, start, and explain than before
  - release notes are ready for human review and permission-gated publishing
- Type: docs-render-verification
- as_of: 2026-06-23T16:49:00+02:00
- Notes: Closure-grade; acceptance pending human review. BL-WB-001 remains next in queue.

## EV-2026-06-23-007: Canonical schema/prompt example project (BL-005)

- File: /home/ff/Documents/Projects/StateDD_Template/docs/evidence/2026-06-23-canonical-schema-prompt-example/README.md
- File: /home/ff/Documents/Projects/StateDD_Template/docs/evidence/2026-06-23-canonical-schema-prompt-example/manifest.json
- File: /home/ff/Documents/Projects/StateDD_Template/schemas/examples/schema_prompt_loop/feature_slice.schema.json
- File: /home/ff/Documents/Projects/StateDD_Template/schemas/examples/schema_prompt_loop/valid_slice.json
- File: /home/ff/Documents/Projects/StateDD_Template/schemas/examples/schema_prompt_loop/invalid_slice.json
- File: /home/ff/Documents/Projects/StateDD_Template/schemas/examples/schema_prompt_loop/validate_example.py
- File: /home/ff/Documents/Projects/StateDD_Template/schemas/examples/schema_prompt_loop/generate_prompt.py
- File: /home/ff/Documents/Projects/StateDD_Template/schemas/examples/schema_prompt_loop/test_schema_prompt_loop.py
- Title: BL-005 canonical schema/export/import example project
- Source/System: test
- Action: Implemented a stdlib-only schema/prompt loop example under `schemas/examples/schema_prompt_loop/`, validated it, wired it into CI, and created a closure evidence pack.
- Shows:
  - `python3 schemas/examples/schema_prompt_loop/validate_example.py` passes for valid_slice.json and fails for invalid_slice.json with a useful error
  - `python3 schemas/examples/schema_prompt_loop/generate_prompt.py` produces deterministic output
  - `python3 schemas/examples/schema_prompt_loop/test_schema_prompt_loop.py` passes, including the fixture-drift guard
  - `.github/workflows/validate.yml` compiles and runs the example
  - the example uses no external dependencies
- Proves:
  - StateDD ships a concrete, tested demonstration of schema-driven prompt generation
  - the schema, examples, and generated prompt stay synchronized by test
- Type: docs-render-verification
- as_of: 2026-06-23T16:34:00+02:00
- Notes: The example is intentionally small and educational. It is not a runtime dependency of StateDD.

## EV-2026-06-23-006: Closure evidence hardening (BL-015)

- File: /home/ff/Documents/Projects/StateDD_Template/docs/evidence/2026-06-23-adoption-ready-evidence-release/README.md
- File: /home/ff/Documents/Projects/StateDD_Template/docs/evidence/2026-06-23-adoption-ready-evidence-release/manifest.json
- File: /home/ff/Documents/Projects/StateDD_Template/scripts/statedd_evidence_pack.py
- File: /home/ff/Documents/Projects/StateDD_Template/scripts/test_evidence_pack.py
- File: /home/ff/Documents/Projects/StateDD_Template/schemas/evidence_manifest.schema.json
- Title: BL-015 closure evidence hardening cleanup
- Source/System: test
- Action: Fixed the human override flag in the closure evidence README, populated the closure manifest with non-empty claims and artifacts, added manifest_status to the schema, tightened --strict to reject empty claims/artifacts unless skeleton/legacy, and added regression tests.
- Shows:
  - closure evidence README now records `Human override used: yes` with scope and rationale
  - closure manifest.json contains claims C1-C5 and artifacts with hashes/redaction status
  - `python3 scripts/statedd_evidence_pack.py check docs/evidence/2026-06-23-adoption-ready-evidence-release --strict` passes
  - new tests cover empty claims/artifacts strict failure, skeleton exception, and required manual_review without known_limits
- Proves:
  - the final BL-012/013/014 evidence pack demonstrates the claim/artifact model it introduced
  - human override status is consistent across handoff, WORKLOG, EVIDENCE_LOG, and evidence README
- Type: docs-render-verification
- as_of: 2026-06-23T15:58:00+02:00
- Notes: This is a post-closure hardening slice; no new features were added.

## EV-2026-06-23-005: Adoption-ready template release verified

- File: /home/ff/Documents/Projects/StateDD_Template/docs/evidence/2026-06-23-adoption-ready-evidence-release/README.md
- File: /home/ff/Documents/Projects/StateDD_Template/docs/evidence/2026-06-23-adoption-ready-evidence-release/runtime_identity.json
- File: /home/ff/Documents/Projects/StateDD_Template/docs/evidence/2026-06-23-adoption-ready-evidence-release/manifest.json
- Title: BL-012/013/014 closure evidence pack manifests, upgrade tooling, adoption profiles, and bootstrap wizard
- Source/System: test
- Action: Implemented the three backlog items, ran the full test suite, updated state/docs/changelog, and created a closure evidence folder with a valid manifest.
- Shows:
  - `python3 scripts/test_evidence_pack.py` passed
  - `python3 scripts/test_upgrade.py` passed
  - `python3 scripts/test_adoption_profiles.py` passed
  - `python3 scripts/statedd_audit.py --strict` passed
  - `python3 scripts/check_state_docs.py` passed
  - `python3 scripts/statedd_evidence_pack.py check docs/evidence/2026-06-23-adoption-ready-evidence-release --strict` passed
- Proves:
  - evidence pack manifests, downstream upgrade tooling, adoption profiles, and the bootstrap wizard are implemented, validated, and closure-grade
- Type: docs-render-verification
- as_of: 2026-06-23T15:52:51+02:00
- Notes: Next slices are BL-005 example project, BL-007 release metadata, and BL-WB-001 browser automation.

## EV-2026-06-23-004: Schema-backed validation integrated

- File: /home/ff/Documents/Projects/StateDD_Template/docs/evidence/2026-06-23-schema-backed-validation/README.md
- File: /home/ff/Documents/Projects/StateDD_Template/docs/evidence/2026-06-23-schema-backed-validation/runtime_identity.json
- File: /home/ff/Documents/Projects/StateDD_Template/scripts/statedd_validate_schema.py
- File: /home/ff/Documents/Projects/StateDD_Template/scripts/test_schema_validation.py
- File: /home/ff/Documents/Projects/StateDD_Template/schemas/project_state.schema.json
- File: /home/ff/Documents/Projects/StateDD_Template/schemas/runtime_identity.schema.json
- Title: Schema-backed validation added for StateDD state, evidence, runtime proof, and handoff contracts
- Source/System: test
- Action: Added executable schemas/contracts, stdlib-only validator, valid/invalid fixtures, initializer coverage, CI coverage, and hygiene/audit/doctor integration.
- Shows:
  - root schema validation passes
  - invalid project state and evidence README fixtures fail with actionable messages
  - runtime-not-applicable passes and runtime-required-unreachable fails
  - generated and adopted repos include schema validation assets
  - audit, doctor, hygiene checks, and CI recognize schema validation
- Proves:
  - BL-010 is implemented as a reusable downstream template capability
  - the BL-012 seed is limited to evidence README contract validation, not redaction or full manifest automation
- Type: docs-render-verification
- as_of: 2026-06-23T15:18:34+02:00
- Notes: Redaction scanning, full evidence-pack manifests, downstream upgrade tooling, adoption profiles, wizard UX, browser automation, example project, and release metadata were intentionally not added in this slice.

## EV-2026-06-23-003: Runtime proof integrated into template contract

- File: /home/ff/Documents/Projects/StateDD_Template/docs/evidence/2026-06-23-runtime-proof-integration/README.md
- File: /home/ff/Documents/Projects/StateDD_Template/docs/evidence/2026-06-23-runtime-proof-integration/runtime_identity.json
- File: /home/ff/Documents/Projects/StateDD_Template/scripts/statedd_runtime_proof.py
- File: /home/ff/Documents/Projects/StateDD_Template/scripts/test_runtime_proof.py
- Title: Runtime identity proof hardened and wired into template output, CI, audit, and doctor
- Source/System: test
- Action: Fixed remote URL process ownership handling, added runtime proof tests, shipped the helper to new/adopted repos, added CI smoke coverage, and exposed runtime_identity.json in audit/doctor/templates.
- Shows:
  - remote URLs record local process ownership as not applicable unless `--expect-local` / `--local-process-proof` is used
  - localhost and 127.0.0.1 URLs still attempt local process ownership detection
  - generated and adopted repos include `scripts/statedd_runtime_proof.py`
  - CI compiles and smoke-tests the runtime proof helper
  - audit and doctor recognize `runtime_identity.json`
  - root `PROJECT_STATE.yaml` stale-labels historical git snapshot data instead of presenting it as live HEAD/worktree truth
- Proves:
  - runtime proof is now a downstream template capability, not only a root maintenance script
  - strict audit can enforce runtime_identity.json when runtime/user-facing evidence requires it
- Type: docs-render-verification
- as_of: 2026-06-23T14:57:50+02:00
- Notes: JSON schema files, evidence manifests, redaction checks, Docker/container process ownership, browser automation, release metadata, and downstream upgrade automation were intentionally not added in this slice.

## EV-2026-06-23-002: Template-maintenance mode split verified

- File: /home/ff/Documents/Projects/StateDD_Template/docs/evidence/2026-06-23-template-maintenance-mode/README.md
- File: /home/ff/Documents/Projects/StateDD_Template/docs/evidence/2026-06-23-template-maintenance-mode/before-check_state_docs.txt
- File: /home/ff/Documents/Projects/StateDD_Template/docs/evidence/2026-06-23-template-maintenance-mode/generated-new-project-state.yaml
- File: /home/ff/Documents/Projects/StateDD_Template/docs/evidence/2026-06-23-template-maintenance-mode/generated-adopt-project-state.yaml
- Title: Root template-maintenance state split from downstream bootstrap state
- Source/System: test
- Action: Added `repo_role` and `statedd_mode`, made checks mode-aware, updated generator output, docs, fixtures, and tests
- Shows:
  - root state declares `repo_role: template_repository` and `statedd_mode: template-maintenance`
  - generated new/adopted repos declare `repo_role: downstream_project` and `statedd_mode: bootstrap`
  - root `python3 scripts/check_state_docs.py --bootstrap-gate` passes after the split
  - generated downstream bootstrap still fails the bootstrap gate until investigation is complete
- Proves:
  - the template root no longer presents itself as a half-bootstrapped downstream project
  - downstream bootstrap safety gates remain intact
- Type: docs-render-verification
- as_of: 2026-06-23T00:00:00+02:00
- Notes: Runtime proof, schema validation, and upgrade tooling remain separate backlog items.

## EV-2026-06-23-001: StateDD version source normalized

- File: /home/ff/Documents/Projects/StateDD_Template/VERSION
- File: /home/ff/Documents/Projects/StateDD_Template/scripts/statedd_version_check.py
- File: /home/ff/Documents/Projects/StateDD_Template/docs/UPGRADING.md
- File: /home/ff/Documents/Projects/StateDD_Template/docs/evidence/2026-06-23-statedd-version-source/README.md
- Title: Canonical StateDD version source and alignment check added
- Source/System: test
- Action: Added version source, changelog, upgrade guidance, alignment script, validator wiring, initializer coverage, and CI command coverage
- Shows:
  - `python3 scripts/statedd_version_check.py` passed
  - `python3 scripts/check_state_docs.py` passed
  - `python3 scripts/test_init_template.py` passed, including generated and adopted version-asset checks
  - fixture hygiene checks passed after fixture spec identifiers were aligned
  - the intentionally thin bootstrap dry-run fixture still fails its bootstrap gate as expected
  - root `PROJECT_ADAPTER.yaml` now matches `statedd-template-v4`
- Proves:
  - current version-bearing files agree on the canonical StateDD spec version
  - generated and adopted repos receive version assets and can run the alignment check
- Type: docs-render-verification
- as_of: 2026-06-23T00:00:00+02:00
- Notes: GitHub release publishing and template/downstream state split remain separate backlog work.

## EV-2026-06-14-001: Tool/model routing template integration verified

- File: /home/ff/Documents/Projects/StateDD_Template/prompts/TOOL_MODEL_ROUTING_GUIDE.md
- File: /home/ff/Documents/Projects/StateDD_Template/prompts/CTO_SESSION_PROMPT.md
- File: /home/ff/Documents/Projects/StateDD_Template/scripts/init_template.py
- File: /home/ff/Documents/Projects/StateDD_Template/scripts/test_init_template.py
- Title: Dynamic CTO-lane tool/model routing guide integrated into template prompts and initializer
- Source/System: test
- Action: Ran `python3 scripts/check_state_docs.py` and `python3 scripts/test_init_template.py`
- Shows:
  - documentation hygiene check passed
  - initializer regression tests passed, including new/adopt routing-guide coverage
  - bootstrap gate still fails for pre-existing incomplete bootstrap baseline conditions
- Proves:
  - the template recognizes the routing guide as a required prompt asset
  - generated and adopted repos include the routing guide
- Type: docs-render-verification
- as_of: 2026-06-14T00:00:00+02:00
- Notes: No external model/provider facts were verified or encoded; routing guide requires current primary-source verification when concrete model claims affect a decision.

## EV-2026-06-14-002: Beginner onboarding and handoff helper integration verified

- File: /home/ff/Documents/Projects/StateDD_Template/docs/GETTING_STARTED_5_MIN.md
- File: /home/ff/Documents/Projects/StateDD_Template/prompts/OPENCODE_STARTUP_PROMPT.md
- File: /home/ff/Documents/Projects/StateDD_Template/scripts/statedd_handoff.py
- File: /home/ff/Documents/Projects/StateDD_Template/scripts/test_init_template.py
- Title: Beginner onboarding, OpenCode startup, and read-only handoff snapshot helper integrated
- Source/System: test
- Action: Ran Python syntax checks, documentation hygiene check, initializer regression tests, handoff helper with validation output, and bootstrap gate
- Shows:
  - `python3 -m py_compile scripts/statedd_handoff.py scripts/init_template.py scripts/check_state_docs.py scripts/test_init_template.py` passed
  - `python3 scripts/check_state_docs.py` passed
  - `python3 scripts/test_init_template.py` passed
  - `python3 scripts/statedd_handoff.py --no-include-listeners --test-command "python3 scripts/check_state_docs.py"` printed repo identity and validation output
  - `python3 scripts/check_state_docs.py --bootstrap-gate` still fails for incomplete bootstrap baseline conditions
- Proves:
  - new and adopted repos include the beginner/OpenCode/handoff assets
  - the handoff helper runs without mutating repo state
  - the repo has not falsely claimed bootstrap completion
- Type: docs-render-verification
- as_of: 2026-06-14T12:57:04+02:00
- Notes: GitHub metadata/release changes, large example projects, license FAQ, and automated screenshot/evidence capture were not implemented in this slice.

## EV-2026-06-14-003: Teaching-rights-reserved license policy integrated

- File: /home/ff/Documents/Projects/StateDD_Template/LICENSE
- File: /home/ff/Documents/Projects/StateDD_Template/LICENSE_FAQ.md
- File: /home/ff/Documents/Projects/StateDD_Template/README.md
- File: /home/ff/Documents/Projects/StateDD_Template/scripts/check_state_docs.py
- File: /home/ff/Documents/Projects/StateDD_Template/scripts/test_init_template.py
- Title: Custom license updated to allow free/commercial use while reserving teaching and training rights
- Source/System: test
- Action: Updated license wording, README note, template copy surface, validator checks, and initializer regression tests
- Shows:
  - `python3 scripts/check_state_docs.py` passed
  - `python3 scripts/test_init_template.py` passed
  - new repos include `LICENSE_FAQ.md`
  - validator checks for commercial/profit permission and teaching-rights reservation
  - `python3 scripts/check_state_docs.py --bootstrap-gate` still fails for incomplete bootstrap baseline conditions
- Proves:
  - the template license surface matches the requested policy at the documentation and initializer level
- Type: docs-render-verification
- as_of: 2026-06-14T13:00:00+02:00
- Notes: This is a custom license draft, not legal advice or lawyer-reviewed text.

## EV-2026-06-14-004: StateDD v2 executable workflow implemented

- File: /home/ff/Documents/Projects/StateDD_Template/scripts/statedd_audit.py
- File: /home/ff/Documents/Projects/StateDD_Template/scripts/statedd_doctor.py
- File: /home/ff/Documents/Projects/StateDD_Template/prompts/SLICE_CONTRACT_TEMPLATE.md
- File: /home/ff/Documents/Projects/StateDD_Template/prompts/EVIDENCE_README_TEMPLATE.md
- File: /home/ff/Documents/Projects/StateDD_Template/prompts/SCHEMA_OWNERSHIP_TEMPLATE.md
- File: /home/ff/Documents/Projects/StateDD_Template/prompts/SUBAGENT_REVIEW_TEMPLATE.md
- File: /home/ff/Documents/Projects/StateDD_Template/prompts/CTO_REVIEW_CHECKLIST.md
- File: /home/ff/Documents/Projects/StateDD_Template/docs/evidence/2026-06-14-statedd-v2-executable-workflow/README.md
- Title: StateDD v2 executable workflow assets added and validated
- Source/System: test
- Action: Added audit, doctor, slice contract, claim ledger, schema ownership, subagent output, CTO checklist, ADR template, human override rule, and wired them into init/validation
- Shows:
  - `python3 scripts/check_state_docs.py` passed
  - `python3 scripts/test_init_template.py` passed, including v2 asset tests
  - `python3 scripts/statedd_doctor.py` produced the expected health summary
  - `python3 scripts/statedd_audit.py` passed on a freshly generated demo repo
- Proves:
  - the template now ships executable audit/doctor commands and v2 prompt assets
  - the initializer and validator recognize and propagate the new assets
- Type: docs-render-verification
- as_of: 2026-06-14T13:40:01+00:00
- Notes: Template repo remains in bootstrap mode. The SkillSignal-specific canonical schema/export/import loop is deferred to a downstream slice.

## EV-2026-06-29-001: Remote CI/CD Closure Finalizer (BL-REMOTE-CLOSURE-001)

- File: /home/ff/Documents/Projects/StateDD_Template/docs/evidence/2026-06-29-remote-closure/README.md
- File: /home/ff/Documents/Projects/StateDD_Template/docs/evidence/2026-06-29-remote-closure/runtime_identity.json
- File: /home/ff/Documents/Projects/StateDD_Template/docs/evidence/2026-06-29-remote-closure/manifest.json
- Title: GitHub-backed remote closure finalizer implemented and verified
- Source/System: test
- Action: Added scripts/statedd_remote_closure_finalizer.py, regression tests, AGENTS.md invariant, skill/command wiring, and CI step; fixed bootstrap fixture versions and CI tmpdir bug
- Shows:
  - `python3 scripts/test_remote_closure_finalizer.py` passed
  - `python3 scripts/check_state_docs.py --bootstrap-gate` passed
  - `python3 scripts/statedd_validate_schema.py` passed
  - GitHub Actions `Validate Template Docs` passed on PR #3
  - `python3 scripts/statedd_remote_closure_finalizer.py --pr 3` exited 0
- Proves:
  - the template can now enforce a Remote Closure Invariant across local HEAD, pushed branch, PR head, PR body, evidence, Actions status, and mergeStateStatus
  - closure-grade handoffs require GitHub-visible CI success and a clean merge state
- Type: implementation
- as_of: 2026-06-29T10:22:31+02:00
- Notes: Final PR head recorded in evidence and PR body.

## EV-2026-07-07-003: Parallel-Agent Worktree Orchestrator (BL-PARALLEL-001)

- File: /home/ff/Documents/Projects/StateDD_Template/docs/failure_scans/BL-PARALLEL-001.md
- File: /home/ff/Documents/Projects/StateDD_Template/docs/evidence/2026-07-07-parallel-agent-worktree/README.md
- File: /home/ff/Documents/Projects/StateDD_Template/docs/evidence/2026-07-07-parallel-agent-worktree/manifest.json
- File: /home/ff/Documents/Projects/StateDD_Template/docs/evidence/2026-07-07-parallel-agent-worktree/runtime_identity.json
- Title: First-class concurrent-agent worktree isolation
- Source/System: test
- Action: Implemented scripts/statedd_agent_worktree.py, updated existing scripts for agent-context awareness, added regression tests and CI smoke test, and updated state/docs/skills/prompts.
- Shows:
  - `python3 -m pytest scripts/test_agent_worktree.py -v` passed (8 tests)
  - `python3 -m pytest scripts/ -q` passed (152 passed, 4 subtests passed)
  - `python3 scripts/statedd_audit.py --strict` passed with closure-grade
  - `python3 scripts/statedd_doctor.py` reports `Closure grade: pass`
- Proves:
  - Multiple coding agents can provision isolated branches/worktrees without collision
  - Existing StateDD gates recognize agent context and adjust single-agent checks
  - Git lock contention is reported, not ignored or corrupted
- Type: implementation
- as_of: 2026-07-07T22:45:00+02:00
- Notes: Local closure verified; remote push/PR/CI pending explicit approval.

## EV-2026-07-10-001: Generated-repo correctness baseline and failure scan (BL-CONTEXT-001)

- File: /home/ff/Documents/Projects/StateDD_Template/.worktrees/bl-bl-context-001-code-a1daa/docs/failure_scans/BL-CONTEXT-001.md
- Title: Fresh profile footprint and self-gate contradiction captured before repair
- Source/System: test
- Action: Generated all four profiles, measured their file/byte/startup payload, ran a fresh solo repo's own quality gate, and classified adjacent failure modes.
- Shows:
  - `minimal` starts at 212 files and 1,146,498 bytes
  - `solo`, `team`, and `regulated` start at 286 files and about 1.2 MB
  - fresh `solo` fails after 99 passing tests because copied template tests require `repo_role: template_repository`
  - fresh `solo` also fails its copied efficiency budget because generated `AGENTS.md` has 270 lines against a limit of 110
- Proves:
  - broad template copying does not produce an internally self-validating downstream repo
  - profile names are not sufficient without enforced context and footprint measurements
- Type: known_bad_event
- as_of: 2026-07-10T21:00:00+02:00
- Notes: Baseline evidence only; repair and closure verification are pending.

## EV-2026-07-10-002: Generated-repo correctness repair locally validated (BL-CONTEXT-001)

- File: /home/ff/Documents/Projects/StateDD_Template/.worktrees/bl-bl-context-001-code-a1daa/docs/evidence/2026-07-10-context-generator-hygiene/README.md
- File: /home/ff/Documents/Projects/StateDD_Template/.worktrees/bl-bl-context-001-code-a1daa/docs/evidence/2026-07-10-context-generator-hygiene/manifest.json
- File: /home/ff/Documents/Projects/StateDD_Template/.worktrees/bl-bl-context-001-code-a1daa/docs/evidence/2026-07-10-context-generator-hygiene/runtime_identity.json
- Title: Explicit downstream asset boundary, strict state, and measurable profile budgets
- Source/System: test
- Action: Replaced broad copying with profile manifests, removed template-only payload, added profile self-gates and budgets, rejected duplicate YAML, and enforced semantic lifecycle agreement.
- Shows:
  - every generated profile passes its own quality gate
  - `minimal` is 29 files and 145,995 bytes versus `solo` at 62 files and 411,582 bytes
  - generated startup context is about 2,100 estimated tokens instead of the roughly 6,700-token baseline
  - duplicate-key, manifest, footprint, lifecycle, upgrade-exclusion, and hidden Git-path adversaries pass
- Proves:
  - downstream instances are internally self-validating without inheriting template-maintenance state
  - context/footprint claims are executable budgets rather than profile labels
- Type: test
- as_of: 2026-07-10T22:03:00+02:00
- Notes: Local validation only; remote branch, PR, and CI truth are pending.

## EV-2026-07-10-003: BL-CONTEXT-001 CI-verified proof head and closure candidate

- File: /home/ff/Documents/Projects/StateDD_Template/.worktrees/bl-bl-context-001-code-a1daa/docs/evidence/2026-07-10-context-generator-hygiene/README.md
- Title: GitHub Actions validates the generator/context repair proof head
- Source/System: ci
- Action: Pushed PR #5, used the semantic gate to catch and repair a fixture lifecycle contradiction, and reran both push and PR workflows on proof head `8840a3c`.
- Shows:
  - GitHub Actions runs `29120524026` and `29120525510` passed on `8840a3c`
  - the PR head, evidence proof head, and implementation under test agree
  - final state truth is carried in a following metadata commit and requires a second CI/finalizer pass
- Proves:
  - the implementation crosses the GitHub-visible CI truth boundary at proof head `8840a3c`
- Type: post_deploy
- as_of: 2026-07-10T22:18:00+02:00
- Notes: The final closure label is not claimed by this entry; the remote closure finalizer remains authoritative for the final state head.

## EV-2026-07-11-001: Merged correctness blockers and failure scan (BL-MAX-VALUE-001)

- File: /home/ff/Documents/Projects/StateDD_Template/docs/failure_scans/BL-MAX-VALUE-001.md
- Title: Upgrade, validation, path-confinement, context, and closure risks reopened after PR #5 merge
- Source/System: GitHub review and local repository inspection
- Action: Verified PR #4 and PR #5 merge truth, confirmed that PR #5 merged after an owner review recorded unresolved blockers, reopened the failures in canonical state, and completed the pre-implementation failure scan.
- Shows:
  - PR #4 merged as `a0ac268d186d9ec71ffefab6970dc1d40add5b06`
  - PR #5 merged as `c2fe7b25625cc855a47deff721251cdb5d4141b2`
  - unresolved upgrade, test aggregation, CI enumeration, root-symlink, metrics, and exact-head closure risks are classified with prevention and rollback requirements
- Proves:
  - BL-MAX-VALUE-001 starts from recorded remote truth and an explicit pre-mortem rather than retrofitting state after implementation
- Type: known_bad_event
- as_of: 2026-07-11T09:13:22+02:00
- Notes: This is orientation and risk evidence only; no implementation or closure claim is made.

## EV-2026-07-11-002: Maximum-value correctness repair locally validated (BL-MAX-VALUE-001)

- File: docs/evidence/2026-07-11-maximum-value-correctness/README.md
- File: docs/evidence/2026-07-11-maximum-value-correctness/manifest.json
- File: docs/evidence/2026-07-11-maximum-value-correctness/runtime_identity.json
- File: docs/metrics/profile_metrics.json
- Title: Lifecycle, gate, path, metrics, runtime, and closure-truth repair
- Source/System: test and local executable gates
- Action: Repaired the reopened PR #5 correctness blockers, added adjacent-case
  regressions, measured the immutable implementation proof, and built strict typed evidence.
- Shows:
  - 289 automatically discovered script tests plus 4 subtests pass
  - 5 schema-example tests pass
  - all generated profiles pass their required conformance gates
  - canonical metrics reproduce against proof head `ae851d05aa8113c3cde90d122d1723be123d9e37`
  - the level-2 quality gate, strict evidence pack, and runtime-not-applicable check pass locally
- Proves:
  - the repaired implementation and local proof artifacts satisfy the executable
    slice contracts on Linux at the recorded proof head
- Type: test
- as_of: 2026-07-11T14:50:00+02:00
- Notes: Remote branch, PR, exact-head CI, finalizer, merge, and human acceptance are not proven.

## EV-2026-07-12-001: Agent-owned golden-path closure local proof

- File: docs/evidence/2026-07-12-golden-path-closure/README.md
- File: docs/evidence/2026-07-12-golden-path-closure/manifest.json
- File: docs/evidence/2026-07-12-golden-path-closure/verification_summary.json
- File: docs/evidence/2026-07-12-golden-path-closure/source_hashes.json
- File: docs/evidence/2026-07-12-golden-path-closure/runtime_identity.json
- Title: Confirmed delivery policy, agent-owned merge, post-merge truth, and semantic state reconciliation
- Source/System: implementation proof and local executable gates
- Action: Added the schema-backed delivery policy, typed finish state machine,
  future-SHA-free post-merge verifier, self-reconciling state checks, generated
  team assets/two-subject CI, and complete mocked remote golden-path regression.
- Shows:
  - proof head `b46c97a7b643459185f21d7bd0bfd4a8d03017a0`
  - full scripts and schema-example suites pass
  - complete empty-folder through agent-owned merge/main-CI/cleanup regression passes
  - every generated profile passes its declared v2-lock gate
  - runtime is not applicable for the template root
- Proves:
  - local implementation and validation truth for BL-GOLDEN-PATH-CLOSURE-001
  - tracked proof does not require a future provider-created merge identity
  - the target default-branch state needs no follow-up metadata PR
- Type: implementation, test, adversarial, state_update
- as_of: 2026-07-12T10:44:33+02:00
- Notes: Remote PR/CI/merge/main verification and human product acceptance remain
  separately unproven until the authorized finish command completes.

## EV-2026-07-12-002: CTO engineering and architecture acceptance

- File: docs/ACCEPTANCE_FREEZES.md
- Title: StateDD v5 operational core accepted and frozen for stable maintenance
- Source/System: explicit human CTO acceptance after independent GitHub verification
- Action: Recorded engineering and architecture acceptance of final main baseline
  `5779baf293a9b5357f896d9725fd7edae2528445` and constrained future core work to
  reproduced defects, compatibility/security migrations, measured improvements,
  explicitly selected research, or the legal copyright-holder decision.
- Shows:
  - the human CTO accepts the operational architecture and agent-owned golden path
  - the core moves from construction to stable maintenance
  - human product acceptance remains a separate pending label
  - legal-owner and benchmark-superiority claims remain unproven
- Proves:
  - user-accepted engineering and architecture truth for the accepted main baseline
- Type: human_acceptance, state_update
- as_of: 2026-07-12T18:08:58+02:00
- Notes: This acceptance does not guess legal identity or claim product acceptance
  or benchmark superiority.

## EV-2026-07-14-001: Workspace lifecycle false-cleanup incident and clone audit

- File: docs/incidents/2026-07-14-workspace-lifecycle-false-cleanup.md
- File: docs/failure_scans/BL-WORKSPACE-LIFECYCLE-001.md
- File: docs/evidence/2026-07-14-workspace-lifecycle-closure/clone_audit.json
- Title: Finished agent isolation was reported released while directories remained
- Source/System: local filesystem, Git topology/reflogs/contexts, patch comparison,
  and external finish handoffs
- Action: Reproduced the metadata-only release defect, audited nine sibling clones
  and five linked worktrees, reversibly archived the visible clones, and opened a
  P0 quality-freeze repair.
- Shows:
  - two clone-of-clone provenance chains were created by agent sessions
  - all nine archived clone feature branches are integrated on main
  - three linked worktrees are integrated/superseded, bounded audit safeguards are
    selected, and dirty BL-BROWSER-002 WIP is preserved but unsafe to merge as-is
  - prior finish sidecars contradicted physical filesystem truth
- Proves:
  - the workspace lifecycle incident is a reproduced workflow/state-truth defect,
    not missing feature work hidden in the archived clones
- Type: known_bad_event, investigation, state_update
- as_of: 2026-07-14T17:23:11+02:00
- Notes: Focused regressions pass locally. Full gates, immutable proof, PR/CI,
  merge, direct-main CI, and final release proof remain pending.

## EV-2026-07-14-002: Workspace lifecycle repair passes authoritative local gate

- File: docs/evidence/2026-07-14-workspace-lifecycle-closure/README.md
- File: docs/evidence/2026-07-14-workspace-lifecycle-closure/manifest.json
- File: docs/evidence/2026-07-14-workspace-lifecycle-closure/verification_summary.json
- Title: Non-recursive managed workspace and physical-release repair validated locally
- Source/System: executable StateDD level-2 gate
- Action: Ran the authoritative gate with explicit slice, evidence-directory, and
  evidence-head binding after restoring those fail-closed CLI inputs.
- Shows:
  - 393 script tests and 5 schema-example tests pass
  - all generated profiles pass their declared conformance gate
  - strict evidence/redaction and runtime-not-applicable truth pass
  - Ruff, compile, state/schema, efficiency, and diff hygiene pass
- Proves:
  - local implementation and validation truth for BL-WORKSPACE-LIFECYCLE-001
- Type: test, adversarial, state_update
- as_of: 2026-07-14T17:50:00+02:00
- Notes: Exact-head remote CI, merge, direct-main CI, and physical release of the
  repair clone remain pending; this is not closure-grade.

## EV-2026-07-14-003: Workspace lifecycle repair closes remotely and self-releases

- File: docs/evidence/2026-07-14-workspace-lifecycle-closure/finish_slice_handoff.json
- File: docs/evidence/2026-07-14-workspace-lifecycle-closure/manifest.json
- Title: Exact-head remote closure and physical managed-clone release
- Source/System: GitHub Actions plus `scripts/statedd_finish_slice.py`
- Action: Verified the exact PR head and evidence binding, passed branch-head and
  merge-candidate CI, squash-merged PR #16, passed direct-main CI, verified the
  post-merge tree, deleted the remote branch, and released the managed clone.
- Shows:
  - PR head `400624ae6616403fcc768ceb5ba7a15bf471bb85` passed exact-head CI
  - merge/default head `d495589cfde23aae73aa83259f2381f78662cff1`
    passed direct-main CI
  - the remote feature branch is absent
  - the managed clone was quarantined and its original active path is absent
- Proves:
  - remote, CI, post-merge, branch-cleanup, and physical-release closure for
    BL-WORKSPACE-LIFECYCLE-001
- Type: remote_ci, post_merge, release_receipt, state_update
- as_of: 2026-07-14T18:09:24+02:00
- Notes: Human product acceptance remains separate; raw non-StateDD clones are
  detectable at managed boundaries but cannot be globally prohibited.

## EV-2026-08-25-001: Autonomous improvement workflow integrated

- File: docs/evidence/2026-08-25-autonomy-workflow-integration/README.md
- File: docs/evidence/2026-08-25-autonomy-workflow-integration/manifest.json
- File: docs/evidence/2026-08-25-autonomy-workflow-integration/quality_gate_output.txt
- File: docs/evidence/2026-08-25-autonomy-workflow-integration/git_safety_report.json
- File: docs/evidence/2026-08-25-autonomy-workflow-integration/run_notes.md
- Title: BL-AUTONOMY-001 improve skill, /projectstate-improve command, and autonomy ladder
- Source/System: test | state_update
- Action: Added `skills/improve/SKILL.md` and `commands/projectstate-improve.md`,
  inserted the L0-L4 Autonomy Ladder into `AGENTS.md` within its line budget,
  registered both subsystems, and repaired enumeration drift (git-safety skill,
  copilot mirror lists, prompts catalog, beginners-doc contradiction).
- Shows:
  - writable-grade Git safety preflight permitted mutation on the private slice branch
  - the authoritative level-2 conformance gate exits 0 with all changes in tree
  - AGENTS.md stays at its 110-line budget with the ladder present
- Proves:
  - local implementation and CI-parity validation of the autonomous
    improvement workflow integration
- Type: implementation | test | state_update
- as_of: 2026-08-25T23:00:00+02:00
- Notes: Remote closure (push, PR, exact-head CI, merge, direct-main CI) is not
  proven by this entry; per the Remote Truth Gate this is NOT CLOSURE-GRADE until
  remote finalization completes.

## EV-2026-08-25-002: Autonomous improvement workflow closes remotely

- File: docs/evidence/2026-08-25-autonomy-workflow-integration/finish_slice_handoff.json
- Title: BL-AUTONOMY-001 exact-head remote closure and managed-clone release
- Source/System: GitHub Actions plus `scripts/projectstate_finish_slice.py`
- Action: Verified the exact PR head and evidence binding, passed branch-head
  and merge-candidate CI in run 32899811460, squash-merged PR #19, passed
  direct-main CI in run 32900937110, verified post-merge tree equivalence,
  deleted the remote branch, and released the managed finish clone.
- Shows:
  - proof head `7db9a8caed24f3c5d18990cfe91031a9cfda7e51` bound to final PR
    head `92b4bf1625314f4a3305064485e9a2ceb82ace38` in the PR body
  - merge/default head `d1179f3abb9153deaf77adf8b65c854feea4f789` with
    SUCCESS direct-main CI
  - remote feature branch absent; quarantine receipt proves original clone
    path absent (status `HANDOFF_COMPLETE`)
- Proves:
  - remote, CI, post-merge, branch-cleanup, and physical-release closure for
    BL-AUTONOMY-001
- Type: remote_ci, post_merge, release_receipt, state_update
- as_of: 2026-08-25T23:35:00+02:00
- Notes: Human product acceptance remains separate. The external handoff
  receipt is authoritative for provider-created merge identity; tracked files
  never predict it.

## EV-2026-08-26-001: Improve-run dogfood reconciliation and rot repairs

- File: docs/evidence/2026-08-26-improve-run-001/README.md
- File: docs/evidence/2026-08-26-improve-run-001/manifest.json
- Title: BL-IMPROVE-RUN-001 first dogfooded /projectstate-improve run
- Source/System: test | state_update
- Action: Reconciled live truth after the cross-repo rollout (queue emptied,
  BL-WORKFLOW-CATALOG-001 closed with outcome), corrected docs/AGENTS.md catalog
  locations, appended append-only errata for the dangling v4 release-notes
  filename, removed dead instruction-lint code, and extended QUICK_COMMANDS
  with the adopt-first and improve-loop paths.
- Shows:
  - queue returned to stable empty state with rollout outcome in BACKLOG CLOSED
  - full CI-parity level-2 conformance gate exit 0 at the proof tree
- Proves:
  - local implementation and CI-parity validation of the reconciliation repairs
- Type: implementation | test | state_update
- as_of: 2026-08-26T01:00:00+02:00

## EV-2026-08-26-002: Integration-test Git-safety state-root isolation

- File: docs/evidence/2026-08-26-stateisolation/README.md
- File: docs/evidence/2026-08-26-stateisolation/manifest.json
- Title: BL-STATEISOLATION-001 per-test Git-safety state-root isolation
- Source/System: test | defect_repair
- Action: Pinned both integration harnesses to per-test Git-safety state roots
  with a hostile decoy latch guarding variable precedence; reproduced the
  ambient-latch contamination on main first, then closed it harness-only.
- Shows:
  - golden-path regression fails under an ambient latch before repair
  - golden path and 27/27 agent-worktree tests pass under the same hostile
    environment after repair, with the decoy untouched
  - full CI-parity level-2 conformance gate exit 0 at the proof tree
- Proves:
  - local implementation and CI-parity validation of the isolation repair
- Type: implementation | test | command_output
- as_of: 2026-08-26T12:00:00+02:00

## EV-2026-08-26-003: Remote closure receipt for BL-STATEISOLATION-001

- File: docs/evidence/2026-08-26-stateisolation-closure/finish_slice_handoff.json
- Title: BL-STATEISOLATION-001 merged, CI-verified, and physically closed
- Source/System: remote_ci | post_merge | release_receipt | state_update
- Action: Finished PR #76 through the authoritative exact-head finish path.
- Shows:
  - squash merge `70195fa8acfdf644890a86efb13ca6ba7026d372` is the verified
    default-branch head; direct-main CI run `32949925520` SUCCESS
  - PR tree equals merge tree (`source_tree_equal`); proof tree b64ed97 bound
  - remote branch absent; clean clone quarantined with original path absent
    (schema projectstate.finish_slice_handoff.v2, status HANDOFF_COMPLETE)
- Proves:
  - remote, CI, post-merge, branch-cleanup, and physical-release closure for
    BL-STATEISOLATION-001
- Type: remote_ci | post_merge | release_receipt | state_update
- as_of: 2026-08-26T11:00:00+02:00

## EV-2026-08-29-001: Safe profile migration and managed clone resume

- File: docs/evidence/2026-08-29-template-downstream-closure/README.md
- File: docs/evidence/2026-08-29-template-downstream-closure/manifest.json
- File: docs/evidence/2026-08-29-template-downstream-closure/runtime_identity.json
- File: docs/evidence/2026-08-29-template-downstream-closure/quality_gate_output.txt
- Title: BL-TEMPLATE-DOWNSTREAM-CLOSURE-001 local implementation and validation
- Source/System: test | schema | state_update
- Action: Added explicit remote-branch resume with optional exact-head binding,
  transactional forward profile migration, canonical profile agreement
  validation, measured footprint updates, and focused regressions.
- Shows:
  - full tests and generated-profile conformance pass
  - schema/state/metrics contracts agree at proof head
  - strict evidence and runtime-boundary checks pass
  - default `/tmp` quota failure was isolated from the verified alternate-TMPDIR
    run
- Proves:
  - local implementation and validation truth for the slice
- Type: implementation | test | state_update
- as_of: 2026-08-29T13:10:00+02:00
- Notes: Remote publication, exact-head CI, merge, and downstream migration are
  not proven by this entry; human product acceptance remains separate.
