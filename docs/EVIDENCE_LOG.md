# EVIDENCE_LOG.md

**Purpose:** Structured ledger of proof artifacts for user-facing claims.

## Entry Format

```yaml
- ID: EV-YYYY-MM-DD-001
  File: path/to/artifact.png
  Title: short description
  Source/System: browser | api | test | log | screenshot
  Route/Page: optional route or URL
  Action: what was done
  Shows:
    - visible fact 1
    - visible fact 2
  Proves:
    - why the artifact matters
  Type: source-data | chatbot | gap | integration | docs-render-verification
  as_of: 2026-03-18T18:00:00+01:00
  Notes: optional context
```

## Guidance

- Link evidence to the specific claim it supports.
- Prefer durable artifact paths.
- Place saved artifacts under `docs/evidence/YYYY-MM-DD-<slug>/` when possible.
- Add timestamps for anything that may become stale.

## EV-2026-04-09-009: StateDD Adoption And Bootstrap-Gate Contract Updated

- File: README.md
- File: AGENTS.md
- File: scripts/init_template.py
- File: scripts/check_state_docs.py
- File: prompts/FINAL_HANDOFF_TEMPLATE.md
- Title: Naming cleanup, adopt flow, backlog IDs, and bootstrap gate added to the public template contract
- Source/System: test
- Action: Updated the live contract, prompt files, initializer, and validator so generated repos inherit the new naming model, explicit `new`/`adopt` flows, backlog-ID linkage, canonical handoff template, and bootstrap-gate checks
- Shows:
  - the README and template docs now use one clear public template name
  - the initializer now supports a first-class `adopt` path with `--dry-run`, optional README linking, and optional GitHub asset installation
  - the validator now checks backlog-ID linkage and exposes a dedicated `--bootstrap-gate`
  - the prompt files now own the canonical prompt text, reducing README drift
- Proves:
  - the remaining workflow contradictions identified in the review have been addressed in the template contract surface
  - downstream repos can now adopt the workflow without blindly copying the full template scaffold
- Type: docs-render-verification
- as_of: 2026-04-09T19:20:00+02:00

## EV-2026-04-09-010: Runtime Identity And Acceptance Freeze Guardrails Added

- File: README.md
- File: AGENTS.md
- File: scripts/init_template.py
- File: scripts/check_state_docs.py
- File: prompts/RUNTIME_IDENTITY_CHECKLIST.md
- File: prompts/ACCEPTANCE_FREEZE_TEMPLATE.md
- File: prompts/FINAL_HANDOFF_TEMPLATE.md
- File: docs/ACCEPTANCE_FREEZES.md
- Title: Runtime truth, acceptance truth, and wording discipline guardrails added to the template
- Source/System: test
- Action: Updated the contract, prompt files, initializer, and validator so downstream repos inherit runtime-identity proof requirements, acceptance freezes, and stricter negative-search wording discipline
- Shows:
  - user-facing acceptance now requires runtime identity proof instead of screenshots alone
  - accepted milestones can now be frozen to repo truth, runtime truth, and evidence truth
  - negative searches are explicitly constrained to `not found`, `not currently locatable`, or `not proven`
  - the adopt path now installs the same runtime-identity and acceptance-freeze assets as the full template path
- Proves:
  - the template now directly addresses the source/runtime/acceptance drift failure mode that previously remained only implicit
  - downstream repos receive durable guardrails for UI acceptance and runtime forensics instead of relying on ad hoc operator discipline
- Type: docs-render-verification
- as_of: 2026-04-09T20:12:00+02:00

## EV-2026-04-09-011: README Opening Copy Cleaned Up

- File: README.md
- Title: Public README opening rewritten for readability
- Source/System: test
- Action: Rewrote the first paragraphs so the template introduction reads naturally before introducing the slug/name distinction
- Shows:
  - the README now explains what the template is before explaining how it is named
  - the required naming relationship remains explicit without leading with internal vocabulary
- Proves:
  - the public-facing landing text is easier to read without weakening the naming contract
- Type: docs-render-verification
- as_of: 2026-04-09T20:20:00+02:00

## EV-2026-04-09-012: Public Naming Simplified

- File: README.md
- File: AGENTS.md
- File: scripts/init_template.py
- File: scripts/check_state_docs.py
- Title: Public template naming and wording simplified
- Source/System: test
- Action: Replaced the public name with `State Driven Development Template` consistently and removed the extra operating-model naming layer from the public docs and generated contract
- Shows:
  - the README and contract now describe one public template clearly
  - fixtures, validator rules, and generated outputs align on the simpler naming
- Proves:
  - downstream repos will inherit the simpler public wording instead of the previous layered naming explanation
- Type: docs-render-verification
- as_of: 2026-04-09T20:36:00+02:00

## EV-2026-04-09-004: Release Readiness Hardening Verified

- File: README.md
- File: AGENTS.md
- File: scripts/init_template.py
- File: scripts/check_state_docs.py
- File: .github/workflows/validate.yml
- File: .github/pull_request_template.md
- Title: Public release guidance, overwrite safety, and validation coverage reverified end to end
- Source/System: test
- Action: Revalidated the root docs and fixtures, exercised normal and minimal init targets, verified safe overwrite into a non-empty target, verified collision failure without `--force-overwrite`, verified forced overwrite succeeds intentionally, and observed the git-metadata warning path directly
- Shows:
  - the README is the canonical public guide and now explains safe initialization paths and CTO handoff expectations
  - the init script prevents silent replacement of conflicting files in existing non-empty targets unless `--force-overwrite` is explicitly used
  - initialized repos inherit the fuller operating contract and still pass the hygiene checks
  - the validator and CI cover template assets, stale-reference drift, and the higher-risk init flows
  - the init output warns when the target still contains `.git` metadata
- Proves:
  - the template is materially safer for public downstream use and accidental first-push or silent-overwrite hazards are reduced
  - the documented onboarding and release contract is backed by direct verification rather than only prose claims
- Type: docs-render-verification
- as_of: 2026-04-09T17:59:30+02:00

## EV-2026-04-09-005: Final Public Release Candidate Verified

- File: README.md
- File: STATUS.md
- File: PROJECT_STATE.yaml
- File: PROJECT_DNA.yaml
- File: PROJECT_ADAPTER.yaml
- File: scripts/init_template.py
- File: scripts/check_state_docs.py
- File: fixtures/bootstrap_dry_run/bootstrap/PROJECT_STATE.yaml
- File: fixtures/bootstrap_dry_run/operating/PROJECT_STATE.yaml
- File: fixtures/messy_inherited_repo/bootstrap/PROJECT_STATE.yaml
- Title: Final renamed release candidate revalidated end to end
- Source/System: test
- Action: Revalidated the root docs, fixtures, and full init matrix after aligning the public template name and internal version identifiers to `State-Driven Development Template`
- Shows:
  - the public-facing README and live state docs now use the same release name
  - generated repos and published fixtures no longer leak the old template slug
  - root, fixtures, normal init, safe overwrite, collision guard, forced overwrite, minimal mode, and git warning flows all still pass after the naming pass
- Proves:
  - the repository is internally consistent under the new public name
  - the renamed template remains ready for public release without regressing the hardening checks
- Type: docs-render-verification
- as_of: 2026-04-09T18:04:26+02:00

## EV-2026-04-09-006: CTO Handoff Model Corrected And Verified

- File: README.md
- File: AGENTS.md
- File: prompts/CTO_SESSION_PROMPT.md
- File: prompts/CODING_AGENT_PROMPT_GUIDE.md
- File: scripts/init_template.py
- File: scripts/check_state_docs.py
- Title: Human-relayed CTO handoff loop verified in repo and generated output
- Source/System: test
- Action: Corrected the workflow contract so the CTO lane is explicitly modeled as a separate chat that only sees pasted context, then revalidated the root repo and a freshly initialized copy
- Shows:
  - the workflow diagram now routes the coding-agent final handoff back through the human rather than directly to the CTO lane
  - the docs and prompts now state that the CTO lane does not have direct repo access unless context is pasted into the chat
  - the docs and prompts now require fresh coding-agent sessions for non-trivial loops and a final handoff for the next CTO pass
  - initialized copies inherit the corrected workflow contract
- Proves:
  - the public template no longer implies a direct CTO-to-repo or CTO-to-coding-agent link that most chatbot-based CTO lanes do not have
  - downstream users receive a clearer and more enforceable operating model for long-running AI-assisted work
- Type: docs-render-verification
- as_of: 2026-04-09T18:10:00+02:00

## EV-2026-04-09-007: Bootstrap-First Onboarding Flow Verified

- File: README.md
- File: AGENTS.md
- File: prompts/CODING_AGENT_PROMPT_GUIDE.md
- File: prompts/BOOTSTRAP_INTAKE_PROMPT.md
- File: scripts/init_template.py
- Title: Bootstrap onboarding now starts with coding-agent intake
- Source/System: test
- Action: Corrected the onboarding flow so the first bootstrap step is the coding agent reading the repo contract and asking the minimum strategic questions, then revalidated the root repo and a freshly initialized copy
- Shows:
  - quick start and first-session guidance now start with the coding agent rather than the CTO lane
  - the read-order section is clearly framed as an agent responsibility rather than a manual user task
  - generated template copies inherit the corrected bootstrap-first flow
- Proves:
  - the public onboarding docs now match the intended real-world workflow for new bootstrap repos
  - downstream users are less likely to start with the wrong actor or skip the initial bootstrap intake
- Type: docs-render-verification
- as_of: 2026-04-09T18:20:03+02:00

## EV-2026-04-09-008: Expanded Bootstrap Gate And Operating Model Verified

- File: README.md
- File: AGENTS.md
- File: prompts/CTO_SESSION_PROMPT.md
- File: prompts/CODING_AGENT_PROMPT_GUIDE.md
- File: prompts/BOOTSTRAP_INTAKE_PROMPT.md
- File: scripts/init_template.py
- File: scripts/check_state_docs.py
- Title: Bootstrap now requires filled state and a real backlog before operating mode
- Source/System: test
- Action: Expanded the workflow contract so bootstrap is a joint CTO + coding-agent planning phase and operating mode is backlog-slice driven, then revalidated the root repo and a fresh initialized copy
- Shows:
  - the README now includes a bootstrap completion gate and explains that `BACKLOG.md` must be real before switching modes
  - the docs and prompts now describe CTO participation in brainstorming, research, architecture framing, and backlog shaping during bootstrap
  - operating-mode prompts now target backlog slices and encourage subagents when supported and useful
  - handoff expectations now mention absolute evidence paths when available
- Proves:
  - the public template now more accurately models a fuller pre-implementation bootstrap phase
  - downstream repos inherit a clearer and more enforceable contract for moving from discovery into implementation
- Type: docs-render-verification
- as_of: 2026-04-09T18:20:03+02:00

## EV-2026-04-09-001: Public Release Hardening Verified

- File: README.md
- File: scripts/init_template.py
- File: .github/workflows/validate.yml
- Title: Public template release flow validated end to end
- Source/System: test
- Action: Revalidated the root docs and fixtures, then dry-ran the initializer into temporary normal and minimal targets
- Shows:
  - the README now contains the setup, bootstrap, validation, and publishing instructions
  - the initializer can create a usable target outside the current checkout
  - minimal mode removes optional example material without breaking validation
  - CI mirrors the same validation surface as the manual release checks
- Proves:
  - the template is ready for public release with the README as the primary usage guide
- Type: docs-render-verification
- as_of: 2026-04-09T17:24:48+02:00

## EV-2026-04-09-002: Onboarding Hardening Verified

- File: README.md
- File: scripts/check_state_docs.py
- File: scripts/init_template.py
- Title: Idiot-proof onboarding flow validated for root and initialized copies
- Source/System: test
- Action: Validated the new README onboarding sections, then dry-ran the init flow again for normal and minimal targets
- Shows:
  - the README contains first-session instructions and copy-paste prompts
  - the validator now checks for the required onboarding sections
  - initialized repos inherit the new CTO setup guidance
  - both normal and minimal init targets still pass the documentation checks
- Proves:
  - the template onboarding is materially harder to misuse or start incorrectly
- Type: docs-render-verification
- as_of: 2026-04-09T17:42:06+02:00

## EV-2026-04-09-003: Git Safety And Workflow Diagram Verified

- File: README.md
- File: scripts/check_state_docs.py
- File: scripts/init_template.py
- Title: Git ownership warning and workflow diagram validated
- Source/System: test
- Action: Revalidated the root README, then dry-ran normal and minimal init targets to confirm they inherit the git-safety warning and pass documentation checks
- Shows:
  - the README warns users to remove inherited `.git` metadata or create a fresh repo before first push
  - the README includes a mermaid workflow diagram covering bootstrap, operating, the CTO/coding-agent loop, and the file memory layer
  - the init script now prints the same git-ownership warning
  - downstream initialized copies still pass the documentation validator
- Proves:
  - the public template is significantly less likely to cause accidental pushes to the template repository
  - the workflow is now easier to understand visually for first-time users
- Type: docs-render-verification
- as_of: 2026-04-09T17:44:58+02:00

## EV-2026-03-18-001: Bootstrap Dry-Run Fixture Validated

- File: fixtures/bootstrap_dry_run/bootstrap/STATUS.md
- File: fixtures/bootstrap_dry_run/operating/STATUS.md
- Title: Dry-run bootstrap and operating snapshots validated
- Source/System: test
- Action: Validated both sample snapshots with the hygiene checker
- Shows:
  - bootstrap snapshot passes the template rules
  - operating snapshot passes the template rules
  - mode metadata is correct before and after transition
- Proves:
  - the template can initialize a repo and then transition it into operating mode
- Type: docs-render-verification
- as_of: 2026-03-18T18:45:00+01:00

## EV-2026-03-18-002: Messy Inherited Repo Bootstrap Validated

- File: fixtures/messy_inherited_repo/bootstrap/STATUS.md
- File: fixtures/messy_inherited_repo/bootstrap/PROJECT_STATE.yaml
- Title: Messy inherited-repo bootstrap snapshot validated
- Source/System: test
- Action: Validated the bootstrap fixture under contradictory documentation
- Shows:
  - source docs disagree about stack and deployment
  - missing state files were handled honestly
  - bootstrap output preserves reported/blocked/assumed/unknown labels
- Proves:
  - the bootstrap workflow stays honest when the repo is ambiguous
- Type: docs-render-verification
- as_of: 2026-03-18T19:10:00+01:00

## EV-2026-03-18-003: Template Init Script Validated

- File: scripts/init_template.py
- Title: One-command template initialization validated in a temp directory
- Source/System: test
- Action: Ran the init script against a temporary directory and validated the generated files
- Shows:
  - core truth files are written from the script
  - `repo_mode` starts in bootstrap
  - the generated files pass the hygiene checker
- Proves:
  - strangers can initialize the template in one command
- Type: docs-render-verification
- as_of: 2026-03-18T19:30:00+01:00
