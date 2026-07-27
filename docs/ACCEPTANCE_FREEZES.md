# ACCEPTANCE_FREEZES.md

**Purpose:** Append-only ledger of accepted user-facing or operator-facing milestones.

Use this when a screen, route, workflow, or other visible milestone is accepted
and must be protected from quiet regression.

## Entry Format

```yaml
- ID: AF-YYYY-MM-DD-001
  Milestone: short milestone name
  Scope: what was accepted
  repo_path: /absolute/path/to/repo
  branch: main
  head: abc1234
  process_or_container: npm dev | docker container name | other
  port_or_base_url: http://localhost:3000
  routes:
    - /
    - /settings
  rebuilt_in_slice: true
  duplicate_runtimes_checked: true
  evidence_refs:
    - EV-YYYY-MM-DD-001
  regression_guard:
    - later work must branch from this accepted lineage
    - route-role changes require explicit backlog scope and new evidence
  Notes: optional
```

## Guidance

- Do not treat screenshots alone as an acceptance freeze.
- Tie the accepted state to repo truth, runtime truth, and evidence truth.
- If a later report conflicts with the freeze, prove runtime identity before drawing conclusions from git history.

## AF-2026-06-23-001: BL-011 template-maintenance mode split accepted

- Milestone: BL-011 root/downstream mode split
- Scope: Root template repository uses `repo_role: template_repository` and `projectstate_mode: template-maintenance`; generated/adopted downstream repositories use `repo_role: downstream_project` and start in `projectstate_mode: bootstrap`.
- Closure-grade: yes
- Accepted: yes
- repo_path: /home/ff/Documents/Projects/ProjectState_Template
- branch: main
- head: 00b5bf13ced5bcc4c19a0d8001fc69fdedad983a
- process_or_container: not applicable; docs/scripts-only template-governance slice
- port_or_base_url: not applicable
- routes: not applicable
- rebuilt_in_slice: false
- duplicate_runtimes_checked: not applicable
- evidence_refs:
  - EV-2026-06-23-002
- regression_guard:
  - Template root must remain `repo_role: template_repository` with `projectstate_mode: template-maintenance`.
  - Generated and adopted downstream repositories must not inherit template-maintenance mode.
  - Runtime proof work must build on this accepted mode split rather than reintroducing root/downstream ambiguity.
- Notes: Runtime identity proof artifact generation remains [BL-009].

## AF-2026-06-23-002: BL-012/013/014 adoption-ready template release accepted

- Milestone: BL-012/013/014 adoption-ready ProjectState template release
- Scope: Evidence pack manifests/redaction gate, non-destructive downstream upgrade tooling MVP, adoption profiles, and bootstrap wizard MVP are accepted as the current reusable template baseline.
- Closure-grade: yes
- Accepted: yes
- repo_path: /home/ff/Documents/Projects/ProjectState_Template
- branch: main
- head: 9f940ddd5c00f11896df6ab5b14bfe0dfe18bf8f
- process_or_container: not applicable; docs/scripts-only template-maintenance release
- port_or_base_url: not applicable
- routes: not applicable
- rebuilt_in_slice: false
- duplicate_runtimes_checked: not applicable
- runtime_identity_artifact: docs/evidence/2026-06-23-adoption-ready-evidence-release/runtime_identity.json
- evidence_pack_manifest: docs/evidence/2026-06-23-adoption-ready-evidence-release/manifest.json
- evidence_refs:
  - EV-2026-06-23-005
  - EV-2026-06-23-006
- human_override:
  used: yes
  rule_overridden: direct implementation/push on main without a PR branch
  requested_by: human product owner / CTO lane
  reason_accepted: self-contained template-maintenance release; worktree kept clean; strict audit and strict evidence-pack checks passed
  remaining_risk: direct-main commits bypass normal PR review; later changes should return to normal branch/PR discipline unless explicitly overridden
  still_closure_grade: yes
- accepted_capabilities:
  - schemas/evidence_manifest.schema.json defines the evidence manifest contract
  - scripts/projectstate_evidence_pack.py supports init/check/hash/scan evidence pack workflows
  - strict evidence-pack validation rejects empty complete manifests and insufficient manual-review records
  - scripts/projectstate_upgrade.py provides non-destructive downstream upgrade MVP behavior
  - scripts/init_template.py supports minimal, solo, team, and regulated adoption profiles
  - scripts/projectstate_bootstrap_wizard.py provides an MVP bootstrap wizard with interactive, --answers, and --dry-run modes
- regression_guard:
  - Closure-grade evidence packs must not regress to empty complete manifests.
  - Human overrides must remain explicit and scoped.
  - Redaction scanner must stay conservative and must not claim absence of secrets is proven.
  - Upgrade tooling must remain non-destructive by default.
  - Generated/adopted downstream repos must preserve bootstrap truth and project-specific state.
  - Minimal profile may omit optional deep-reference docs only where explicitly validated.
- known_limits:
  - Bootstrap wizard remains MVP and does not replace CTO-lane bootstrap judgment.
  - Upgrade helper does not semantic-merge customized workflow files.
  - Redaction scanning is pattern-based and cannot prove absence of secrets.
  - Browser/runtime UI verification remains deferred to BL-WB-001.

## AF-2026-06-23-005: BL-BROWSER-001 provider-agnostic browser verification accepted

- Milestone: BL-BROWSER-001 provider-agnostic browser verification contract
- Scope: Added `schemas/browser_verification.schema.json`, `docs/BROWSER_VERIFICATION.md`, `scripts/projectstate_browser_verify.py`, `scripts/test_browser_verification.py`, fixtures, and audit/doctor/CI integration so ProjectState accepts browser-verification evidence from any recognized provider.
- Closure-grade: yes
- Accepted: yes
- repo_path: /home/ff/Documents/Projects/ProjectState_Template
- branch: feature/provider-agnostic-browser-verification
- head: eb0cd886e900c2e35ddb8123b9fd599631335f89
- process_or_container: not applicable; docs/scripts-only template-maintenance slice
- port_or_base_url: not applicable
- routes: not applicable
- rebuilt_in_slice: false
- duplicate_runtimes_checked: not applicable
- runtime_identity_artifact: docs/evidence/2026-06-23-provider-agnostic-browser-verification/runtime_identity.json
- browser_verification_artifact: docs/evidence/2026-06-23-provider-agnostic-browser-verification/browser_verification.json
- evidence_pack_manifest: docs/evidence/2026-06-23-provider-agnostic-browser-verification/manifest.json
- evidence_refs:
  - EV-2026-06-23-009
- human_override:
  used: no
- accepted_capabilities:
  - schemas/browser_verification.schema.json defines projectstate.browser_verification.v1
  - scripts/projectstate_browser_verify.py supports init/check/hash/summarize without driving browsers
  - scripts/projectstate_audit.py requires browser_verification.json for user-facing/runtime closure and accepts any recognized provider in strict mode
  - scripts/projectstate_doctor.py reports browser verification status and provider-agnostic fallback guidance
  - scripts/projectstate_validate_schema.py validates browser_verification.json in evidence folders
  - prompts/EVIDENCE_README_TEMPLATE.md and prompts/FINAL_HANDOFF_TEMPLATE.md include browser verification fields
- regression_guard:
  - ProjectState must remain provider-agnostic: no single browser automation provider may become a hard dependency.
  - Kimi WebBridge may be documented as a preferred provider when available, but it must not be required.
  - Strict audit must continue to accept valid evidence from Playwright, agent-native browser tools, existing E2E tests, manual screenshots, and custom tooling.
  - docs/scripts-only slices must remain not applicable for browser verification.
- known_limits:
  - Concrete browser automation provider integration remains future work (BL-BROWSER-002).
  - The helper script validates and records evidence but does not drive browsers.

## AF-2026-06-23-004: BL-007 public usability and release-readiness polish accepted

- Milestone: BL-007 public usability and release-readiness polish
- Scope: Simplified README top half, added `docs/QUICK_COMMANDS.md`, improved `docs/ADOPTION_PROFILES.md` chooser with explicit `solo` default, polished `docs/GETTING_STARTED_5_MIN.md`, and finalized `docs/RELEASE_NOTES_projectstate-template-v4.md` as release-candidate ready.
- Closure-grade: yes
- Accepted: yes
- repo_path: /home/ff/Documents/Projects/ProjectState_Template
- branch: main
- head: 947a8964085b8377017d6681e20fa24d266dcab9
- process_or_container: not applicable; docs/scripts-only template-maintenance slice
- port_or_base_url: not applicable
- routes: not applicable
- rebuilt_in_slice: false
- duplicate_runtimes_checked: not applicable
- runtime_identity_artifact: docs/evidence/2026-06-23-release-readiness-polish/runtime_identity.json
- evidence_pack_manifest: docs/evidence/2026-06-23-release-readiness-polish/manifest.json
- evidence_refs:
  - EV-2026-06-23-008
- human_override:
  used: no
- accepted_capabilities:
  - README opens with a 60-second "Start here" path and a "Start Simple" section
  - `docs/QUICK_COMMANDS.md` provides a copy-paste command cheat sheet
  - `docs/ADOPTION_PROFILES.md` recommends `--profile solo` by default
  - `docs/GETTING_STARTED_5_MIN.md` can be followed without reading the full README first
  - `docs/RELEASE_NOTES_projectstate-template-v4.md` is release-candidate ready and requires explicit human permission to publish
- regression_guard:
  - README must keep a beginner-friendly top half.
  - Quick commands, adoption profiles, and the 5-minute guide must remain discoverable and accurate.
  - Release notes must keep the human-permission gate for GitHub release publishing.
- known_limits:
  - GitHub release publishing for projectstate-template-v4 is not done; requires explicit human permission.
  - Provider-agnostic browser verification remains future work (BL-BROWSER-001). Kimi WebBridge may be used when available, but ProjectState does not require a specific browser automation provider.

## AF-2026-06-23-003: BL-005 canonical schema/prompt example accepted

- Milestone: BL-005 canonical schema/export/import example project
- Scope: The `schemas/examples/schema_prompt_loop/` example demonstrates a schema-driven loop where one schema validates data and generates deterministic prompt material, with regression tests and CI coverage.
- Closure-grade: yes
- Accepted: yes
- repo_path: /home/ff/Documents/Projects/ProjectState_Template
- branch: main
- head: 0c17d4fe46e7a6cb73396b11e562b4cc008f6bad
- process_or_container: not applicable; docs/scripts-only template-maintenance release
- port_or_base_url: not applicable
- routes: not applicable
- rebuilt_in_slice: false
- duplicate_runtimes_checked: not applicable
- runtime_identity_artifact: docs/evidence/2026-06-23-canonical-schema-prompt-example/runtime_identity.json
- evidence_pack_manifest: docs/evidence/2026-06-23-canonical-schema-prompt-example/manifest.json
- evidence_refs:
  - EV-2026-06-23-007
- human_override:
  used: no
- accepted_capabilities:
  - schemas/examples/schema_prompt_loop/feature_slice.schema.json defines a small feature slice contract
  - schemas/examples/schema_prompt_loop/valid_slice.json passes schema validation
  - schemas/examples/schema_prompt_loop/invalid_slice.json fails schema validation with a useful error
  - schemas/examples/schema_prompt_loop/generate_prompt.py generates a deterministic prompt from the schema
  - schemas/examples/schema_prompt_loop/test_schema_prompt_loop.py guards against prompt fixture drift
  - The example is wired into `.github/workflows/validate.yml`
- regression_guard:
  - The schema/prompt example must keep passing validation and tests.
  - The generated prompt fixture must stay synchronized with the schema.
  - The example must remain stdlib-only and must not become a runtime dependency.
  - CI must continue to compile and run the example scripts.
- known_limits:
  - The example is intentionally small and educational.
  - The generated prompt uses only schema field names and descriptions.

## AF-2026-07-12-001: ProjectState v5 operational core accepted

- Milestone: ProjectState v5 operational template completion
- Scope: CTO engineering and architecture acceptance of the compact, repo-native
  ProjectState operational core, including structured bootstrap, bounded parallel-agent
  integration, confirmed agent-owned exact-head delivery, direct-main CI,
  post-merge verification, self-reconciling canonical state, and stable maintenance.
- Closure-grade: yes
- Accepted: yes
- Acceptance authority: human CTO
- Acceptance type: engineering_and_architecture
- Accepted on: 2026-07-12
- repo_path: /home/ff/Documents/Projects/ProjectState_Template
- branch: main
- accepted_head: 5779baf293a9b5357f896d9725fd7edae2528445
- process_or_container: not applicable; template repository has no application runtime
- port_or_base_url: not applicable
- rebuilt_in_slice: false
- duplicate_runtimes_checked: not applicable
- evidence_refs:
  - EV-2026-07-12-002
- accepted_capabilities:
  - structured bootstrap and profile generation
  - bounded parallel-agent integration with one integration owner
  - confirmed `agent_after_green` exact-head squash merge
  - branch-head, merge-candidate, and direct-main CI proof
  - post-merge source-tree equivalence and external handoff
  - verified remote-branch cleanup and isolation release
  - canonical state with no active P0/P1 implementation work
  - opt-in OKF interoperability
- regression_guard:
  - Do not open an unmeasured generic core-improvement slice.
  - Accept core changes only for a reproduced defect, compatibility/security
    migration, measured improvement against this baseline, explicitly selected
    optional research, or the verified legal copyright-holder decision.
  - Preserve routine agent ownership of branch, commit, push, PR, exact-head merge,
    direct-main verification, and post-merge cleanup under confirmed policy.
  - Preserve force-push, shared-history rewrite, CI-bypass, and human product-
    acceptance boundaries.
- known_limits:
  - Human product acceptance remains separately pending.
  - The verified legal copyright holder is not proven; `LICENSE` is unchanged.
  - Comparative benchmark superiority is not proven.
  - StateIR, StatePack, and OKF retrieval benchmarks remain optional research.
- human_override:
  used: no
