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
- Scope: Root template repository uses `repo_role: template_repository` and `statedd_mode: template-maintenance`; generated/adopted downstream repositories use `repo_role: downstream_project` and start in `statedd_mode: bootstrap`.
- Closure-grade: yes
- Accepted: yes
- repo_path: /home/ff/Documents/Projects/StateDD_Template
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
  - Template root must remain `repo_role: template_repository` with `statedd_mode: template-maintenance`.
  - Generated and adopted downstream repositories must not inherit template-maintenance mode.
  - Runtime proof work must build on this accepted mode split rather than reintroducing root/downstream ambiguity.
- Notes: Runtime identity proof artifact generation remains [BL-009].

## AF-2026-06-23-002: BL-012/013/014 adoption-ready template release accepted

- Milestone: BL-012/013/014 adoption-ready StateDD template release
- Scope: Evidence pack manifests/redaction gate, non-destructive downstream upgrade tooling MVP, adoption profiles, and bootstrap wizard MVP are accepted as the current reusable template baseline.
- Closure-grade: yes
- Accepted: yes
- repo_path: /home/ff/Documents/Projects/StateDD_Template
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
  - scripts/statedd_evidence_pack.py supports init/check/hash/scan evidence pack workflows
  - strict evidence-pack validation rejects empty complete manifests and insufficient manual-review records
  - scripts/statedd_upgrade.py provides non-destructive downstream upgrade MVP behavior
  - scripts/init_template.py supports minimal, solo, team, and regulated adoption profiles
  - scripts/statedd_bootstrap_wizard.py provides an MVP bootstrap wizard with interactive, --answers, and --dry-run modes
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

## AF-2026-06-23-003: BL-005 canonical schema/prompt example accepted

- Milestone: BL-005 canonical schema/export/import example project
- Scope: The `schemas/examples/schema_prompt_loop/` example demonstrates a schema-driven loop where one schema validates data and generates deterministic prompt material, with regression tests and CI coverage.
- Closure-grade: yes
- Accepted: yes
- repo_path: /home/ff/Documents/Projects/StateDD_Template
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
