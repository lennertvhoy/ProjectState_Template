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

## EV-2026-06-28-002: StateDD v5 Efficiency Invariant and gate levels (BL-EFFICIENCY-001)

- File: /home/ff/Documents/Projects/StateDD_Template/docs/evidence/2026-06-28-efficiency-layer/README.md
- File: /home/ff/Documents/Projects/StateDD_Template/docs/evidence/2026-06-28-efficiency-layer/command_outputs/efficiency_check.txt
- File: /home/ff/Documents/Projects/StateDD_Template/docs/evidence/2026-06-28-efficiency-layer/command_outputs/test_efficiency_check.txt
- File: /home/ff/Documents/Projects/StateDD_Template/docs/evidence/2026-06-28-efficiency-layer/command_outputs/bloat_fixture_check.txt
- File: /home/ff/Documents/Projects/StateDD_Template/docs/evidence/2026-06-28-efficiency-layer/command_outputs/full_pytest.txt
- File: /home/ff/Documents/Projects/StateDD_Template/docs/evidence/2026-06-28-efficiency-layer/command_outputs/quality_gate.txt
- Title: BL-EFFICIENCY-001 hard Efficiency Invariant and tiered gate levels
- Source/System: test
- Action: Added Efficiency Invariant to AGENTS.md, created EFFICIENCY_BUDGET.yaml, implemented scripts/statedd_efficiency_check.py with tests, wired it into quality/closure/release gates, added gate-level metadata to all skills/commands, and fixed pre-existing v4/v5 fixture drift plus a CI tmpdir-reuse bug so the full gate passes.
- Shows:
  - `python scripts/statedd_efficiency_check.py --gate-level 2` passes on the template root
  - `python -m pytest scripts/test_efficiency_check.py -v` passes (10/10)
  - `python scripts/statedd_efficiency_check.py --gate-level 2 --root fixtures/efficiency_bloat_overcorrection` fails as expected on the bloat regression fixture
  - `python -m pytest scripts/ -q` passes (102 passed, 4 subtests passed)
  - `python scripts/statedd_quality_gate.py` passes all gates
  - GitHub Actions `Validate Template Docs` passes on PR #2 at HEAD 2e84aee
  - All skills and commands declare gate_level, evidence_max, cheapest_proof, and escalate_when
- Proves:
  - StateDD v5 now enforces the Efficiency Invariant: no bureaucracy without measurable value, smallest proof that crosses the truth boundary, and a bloat regression guard
  - The full local and CI quality gates are now clean for this slice
- Type: test
- as_of: 2026-06-28T18:17:00+00:00
- Notes: Branch pushed and GitHub Actions verified clean at HEAD 2e84aee. The pre-existing v4/v5 fixture drift and CI tmpdir-reuse bug have been fixed; the full quality gate is no longer blocked.

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
