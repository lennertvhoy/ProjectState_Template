# WORKLOG

**Purpose:** Append-only history for completed work.

Use this file for dated session notes, verification summaries, and references to evidence artifacts.

## 2026-04-09 - Bootstrap gate and backlog-slice operating model expanded

**Type:** docs_or_process_only
**Status:** COMPLETE
**Git Head:** 59aba64
**Worktree:** dirty (uncommitted workflow-contract expansion)

### What changed
- Expanded `README.md` so bootstrap is now explicitly a broader CTO + coding-agent discovery and planning phase that must fill out the state files and produce a real backlog before `operating` mode begins.
- Clarified that operating mode should usually execute one backlog slice or a very small group of tightly related backlog items from a fresh coding-agent session.
- Updated `AGENTS.md`, prompt helpers, validator rules, and generated init output so downstream repos inherit the same stronger bootstrap gate, subagent encouragement, and evidence-path handoff expectations.

### Verification
- `python3 -m py_compile scripts/check_state_docs.py scripts/init_template.py` -> PASS
- `python3 scripts/check_state_docs.py` -> PASS
- `python3 scripts/init_template.py --name "Demo Project" --target /tmp/state-dd-bootstrap-expanded-verify.NU1B7e/demo` -> PASS
- `python3 scripts/check_state_docs.py /tmp/state-dd-bootstrap-expanded-verify.NU1B7e/demo` -> PASS
- `rg -n 'Bootstrap Completion Gate|real \`BACKLOG.md\`, not a placeholder|backlog slice|subagents|absolute file paths' /tmp/state-dd-bootstrap-expanded-verify.NU1B7e/demo/README.md /tmp/state-dd-bootstrap-expanded-verify.NU1B7e/demo/AGENTS.md /tmp/state-dd-bootstrap-expanded-verify.NU1B7e/demo/prompts/CTO_SESSION_PROMPT.md /tmp/state-dd-bootstrap-expanded-verify.NU1B7e/demo/prompts/CODING_AGENT_PROMPT_GUIDE.md` -> PASS
- `git diff --check` -> PASS

### Evidence
- `docs/EVIDENCE_LOG.md` entry `EV-2026-04-09-008`

### Follow-up
1. Commit this workflow-contract expansion if you want the remote repo updated again.

## 2026-04-09 - Bootstrap-first onboarding flow corrected

**Type:** docs_or_process_only
**Status:** COMPLETE
**Git Head:** 59aba64
**Worktree:** dirty (uncommitted onboarding correction)

### What changed
- Corrected `README.md` so quick start and first-session guidance now begin with the coding agent reading the repo contract and asking the initial bootstrap questions.
- Clarified `AGENTS.md`, prompt guides, and generated init output so the first bootstrap intake happens before the CTO loop fully takes over.
- Renamed the read-order section so it is clearly the coding agent's required read order rather than a manual task for the human.

### Verification
- `python3 -m py_compile scripts/check_state_docs.py scripts/init_template.py` -> PASS
- `python3 scripts/check_state_docs.py` -> PASS
- `python3 scripts/init_template.py --name "Demo Project" --target /tmp/state-dd-bootstrapflow.kzSOKa/demo` -> PASS
- `python3 scripts/check_state_docs.py /tmp/state-dd-bootstrapflow.kzSOKa/demo` -> PASS
- `rg -n "Start the coding agent|detect bootstrap mode|minimum strategic questions|Agent Read Order|bootstrap handoff" /tmp/state-dd-bootstrapflow.kzSOKa/demo/README.md /tmp/state-dd-bootstrapflow.kzSOKa/demo/AGENTS.md /tmp/state-dd-bootstrapflow.kzSOKa/demo/prompts/CODING_AGENT_PROMPT_GUIDE.md /tmp/state-dd-bootstrapflow.kzSOKa/demo/prompts/BOOTSTRAP_INTAKE_PROMPT.md` -> PASS
- `git diff --check` -> PASS

### Evidence
- `docs/EVIDENCE_LOG.md` entry `EV-2026-04-09-007`

### Follow-up
1. Commit this onboarding-flow correction if you want the remote repo updated again.

## 2026-04-09 - CTO handoff loop corrected to human-relayed model

**Type:** docs_or_process_only
**Status:** COMPLETE
**Git Head:** 2015ca7
**Worktree:** dirty (uncommitted release candidate)

### What changed
- Corrected the workflow contract in `README.md`, `AGENTS.md`, prompt helpers, and generated template output so the CTO lane is modeled as a separate chat that only sees human-pasted context.
- Reworked the workflow diagram and operating-loop explanation to show the actual sequence: coding agent finishes, human pastes the final handoff into the CTO chat, CTO writes the next prompt, and the next coding-agent run starts as a fresh session.
- Tightened the validator so the README must preserve the user-relayed CTO context model and the fresh-session rule.

### Verification
- `python3 -m py_compile scripts/check_state_docs.py scripts/init_template.py` -> PASS
- `python3 scripts/check_state_docs.py` -> PASS
- `python3 scripts/init_template.py --name "Demo Project" --target /tmp/state-dd-cto-handoff.68219B/demo` -> PASS
- `python3 scripts/check_state_docs.py /tmp/state-dd-cto-handoff.68219B/demo` -> PASS
- `rg -n "direct repo access|fresh coding-agent session|final handoff|CTO lane" /tmp/state-dd-cto-handoff.68219B/demo/AGENTS.md /tmp/state-dd-cto-handoff.68219B/demo/README.md /tmp/state-dd-cto-handoff.68219B/demo/prompts/CTO_SESSION_PROMPT.md /tmp/state-dd-cto-handoff.68219B/demo/prompts/CODING_AGENT_PROMPT_GUIDE.md` -> PASS
- `git diff --check` -> PASS

### Evidence
- `docs/EVIDENCE_LOG.md` entry `EV-2026-04-09-006`

### Follow-up
1. Commit this workflow-contract correction so the public repo matches the intended CTO handoff model.

## 2026-04-09 - Final public release naming alignment and verification

**Type:** docs_or_process_only
**Status:** COMPLETE
**Git Head:** 2015ca7
**Worktree:** dirty (uncommitted release candidate)

### What changed
- Renamed the public template identity to `State-Driven Development Template` across the README, root state docs, helper scripts, and generated init output.
- Aligned internal template version identifiers and public fixtures with the new template name so generated repos and example snapshots no longer leak the old slug.
- Re-ran the full release checks after the naming pass to confirm the repo still satisfies the public release contract.

### Verification
- `python3 -m py_compile scripts/check_state_docs.py scripts/init_template.py` -> PASS
- `python3 scripts/check_state_docs.py` -> PASS
- `python3 scripts/check_state_docs.py fixtures/bootstrap_dry_run/bootstrap` -> PASS
- `python3 scripts/check_state_docs.py fixtures/bootstrap_dry_run/operating` -> PASS
- `python3 scripts/check_state_docs.py fixtures/messy_inherited_repo/bootstrap` -> PASS
- `python3 scripts/init_template.py --name "Demo Project" --target /tmp/state-dd-release-final.PsUNTu/demo` -> PASS
- `python3 scripts/check_state_docs.py /tmp/state-dd-release-final.PsUNTu/demo` -> PASS
- `python3 scripts/init_template.py --name "Demo Project" --target /tmp/state-dd-release-final.PsUNTu/nonempty-safe --overwrite` -> PASS
- `python3 scripts/check_state_docs.py /tmp/state-dd-release-final.PsUNTu/nonempty-safe` -> PASS
- `python3 scripts/init_template.py --name "Demo Project" --target /tmp/state-dd-release-final.PsUNTu/nonempty-conflict --overwrite` -> expected failure
- `python3 scripts/init_template.py --name "Demo Project" --target /tmp/state-dd-release-final.PsUNTu/nonempty-conflict --overwrite --force-overwrite` -> PASS
- `python3 scripts/check_state_docs.py /tmp/state-dd-release-final.PsUNTu/nonempty-conflict` -> PASS
- `python3 scripts/init_template.py --name "Demo Project" --minimal --target /tmp/state-dd-release-final.PsUNTu/minimal` -> PASS
- `python3 scripts/check_state_docs.py /tmp/state-dd-release-final.PsUNTu/minimal` -> PASS
- `python3 scripts/init_template.py --name "Demo Project" --target /tmp/state-dd-gitwarn-final.Ai8xYa/repo --overwrite` -> PASS with git warning observed
- `git diff --check` -> PASS

### Evidence
- `docs/EVIDENCE_LOG.md` entry `EV-2026-04-09-005`

### Follow-up
1. Commit this final release candidate state if you want the public remote updated.

## 2026-04-09 - Public release readiness audit and hardening pass

**Type:** docs_or_process_only
**Status:** COMPLETE
**Git Head:** 2015ca7
**Worktree:** dirty (uncommitted release-readiness pass)

### What changed
- Hardened `README.md` as the canonical public guide with safe initialization paths, tool-agnostic agent setup, and a clearer CTO handoff contract.
- Strengthened `scripts/init_template.py` so initialized repos inherit the fuller operating contract and existing non-empty targets are collision-protected unless `--force-overwrite` is used intentionally.
- Expanded `scripts/check_state_docs.py` and `.github/workflows/validate.yml` to enforce higher-signal release invariants and exercise normal, safe-overwrite, collision, force-overwrite, and minimal init flows.
- Tightened supporting prompt and PR-template assets so the public repo surface matches the operating contract.

### Verification
- `python3 -m py_compile scripts/check_state_docs.py scripts/init_template.py` -> PASS
- `python3 scripts/check_state_docs.py` -> PASS
- `python3 scripts/check_state_docs.py fixtures/bootstrap_dry_run/bootstrap` -> PASS
- `python3 scripts/check_state_docs.py fixtures/bootstrap_dry_run/operating` -> PASS
- `python3 scripts/check_state_docs.py fixtures/messy_inherited_repo/bootstrap` -> PASS
- `python3 scripts/init_template.py --name "Demo Project" --target /tmp/state-dd-release-audit.RkcyMh/demo` -> PASS
- `python3 scripts/check_state_docs.py /tmp/state-dd-release-audit.RkcyMh/demo` -> PASS
- `python3 scripts/init_template.py --name "Demo Project" --target /tmp/state-dd-release-audit.RkcyMh/nonempty-safe --overwrite` -> PASS
- `python3 scripts/check_state_docs.py /tmp/state-dd-release-audit.RkcyMh/nonempty-safe` -> PASS
- `python3 scripts/init_template.py --name "Demo Project" --target /tmp/state-dd-release-audit.RkcyMh/nonempty-conflict --overwrite` -> expected failure
- `python3 scripts/init_template.py --name "Demo Project" --target /tmp/state-dd-release-audit.RkcyMh/nonempty-conflict --overwrite --force-overwrite` -> PASS
- `python3 scripts/check_state_docs.py /tmp/state-dd-release-audit.RkcyMh/nonempty-conflict` -> PASS
- `python3 scripts/init_template.py --name "Demo Project" --minimal --target /tmp/state-dd-release-audit.RkcyMh/minimal` -> PASS
- `python3 scripts/check_state_docs.py /tmp/state-dd-release-audit.RkcyMh/minimal` -> PASS
- `python3 scripts/init_template.py --name "Demo Project" --target /tmp/state-dd-gitwarn.UIbs9d/repo --overwrite` -> PASS with git warning observed
- `git diff --check` -> PASS

### Evidence
- `docs/EVIDENCE_LOG.md` entry `EV-2026-04-09-004`

### Follow-up
1. Commit this release-readiness hardening pass if you want the remote repo updated.

## 2026-04-09 - Onboarding hardening for idiot-proof setup

**Type:** docs_or_process_only  
**Status:** COMPLETE  
**Git Head:** 986b314  
**Worktree:** dirty (uncommitted onboarding pass)

### What changed
- Expanded `README.md` with a first-session checklist, copy-paste startup prompts, a non-trivial-work definition, common failure modes, a single-agent fallback, and a concrete example flow.
- Tightened the operating contract so coding agents must ask for a CTO lane before non-trivial work if one does not already exist.
- Hardened the initializer and validator so downstream repos inherit the same onboarding expectations.

### Verification
- `python3 scripts/check_state_docs.py` -> PASS
- `python3 scripts/check_state_docs.py fixtures/bootstrap_dry_run/bootstrap` -> PASS
- `python3 scripts/check_state_docs.py fixtures/bootstrap_dry_run/operating` -> PASS
- `python3 scripts/check_state_docs.py fixtures/messy_inherited_repo/bootstrap` -> PASS
- `python3 scripts/init_template.py --name "Demo Project" --target /tmp/state-dd-template-onboarding.dYoK7S` -> PASS
- `python3 scripts/check_state_docs.py /tmp/state-dd-template-onboarding.dYoK7S` -> PASS
- `python3 scripts/init_template.py --name "Demo Project" --minimal --target /tmp/state-dd-template-onboarding-min.zb4SwI` -> PASS
- `python3 scripts/check_state_docs.py /tmp/state-dd-template-onboarding-min.zb4SwI` -> PASS

### Evidence
- `docs/EVIDENCE_LOG.md` entry `EV-2026-04-09-002`

### Follow-up
1. Commit and push the onboarding hardening pass if you want the remote repo updated.

## 2026-04-09 - Git safety and workflow diagram added

**Type:** docs_or_process_only  
**Status:** COMPLETE  
**Git Head:** 986b314  
**Worktree:** dirty (uncommitted onboarding pass)

### What changed
- Added a mermaid workflow diagram to `README.md` showing bootstrap, operating, the human-in-the-loop oversight, the CTO/coding-agent loop, and the role of the core files.
- Added an explicit git-safety section warning users to remove inherited `.git` metadata or create a fresh repo before first push.
- Extended the validator and initializer output so downstream repos inherit the same warning and onboarding expectations.

### Verification
- `python3 scripts/check_state_docs.py` -> PASS
- `python3 scripts/init_template.py --name "Demo Project" --target /tmp/state-dd-template-gitsafe.3BA5k0` -> PASS
- `python3 scripts/check_state_docs.py /tmp/state-dd-template-gitsafe.3BA5k0` -> PASS
- `python3 scripts/init_template.py --name "Demo Project" --minimal --target /tmp/state-dd-template-gitsafe-min.cLKxPS` -> PASS
- `python3 scripts/check_state_docs.py /tmp/state-dd-template-gitsafe-min.cLKxPS` -> PASS

### Evidence
- `docs/EVIDENCE_LOG.md` entry `EV-2026-04-09-003`

### Follow-up
1. Commit and push the git-safety and diagram pass if you want the remote repo updated.

## 2026-04-09 - Public release hardening and README consolidation

**Type:** docs_or_process_only  
**Status:** COMPLETE  
**Git Head:** 506535e  
**Worktree:** dirty (uncommitted release pass)

### What changed
- Rewrote `README.md` into the canonical end-user guide for setup, bootstrap, validation, and downstream publishing.
- Hardened `scripts/init_template.py` requirements by aligning the template contract and clarifying public initialization behavior.
- Tightened public repo assets: ignored local Codex artifacts, removed the broken issue-template contact link, and expanded CI validation coverage.
- Flipped the template repository itself into truthful `operating` mode and refreshed the root state files accordingly.

### Verification
- `python3 scripts/check_state_docs.py` -> PASS
- `python3 scripts/check_state_docs.py fixtures/bootstrap_dry_run/bootstrap` -> PASS
- `python3 scripts/check_state_docs.py fixtures/bootstrap_dry_run/operating` -> PASS
- `python3 scripts/check_state_docs.py fixtures/messy_inherited_repo/bootstrap` -> PASS
- `python3 scripts/init_template.py --name "Demo Project" --target /tmp/state-dd-template-demo.t3fPVj` -> PASS
- `python3 scripts/check_state_docs.py /tmp/state-dd-template-demo.t3fPVj` -> PASS
- `python3 scripts/init_template.py --name "Demo Project" --minimal --target /tmp/state-dd-template-minimal.9XN1rc` -> PASS
- `python3 scripts/check_state_docs.py /tmp/state-dd-template-minimal.9XN1rc` -> PASS

### Evidence
- `docs/EVIDENCE_LOG.md` entry `EV-2026-04-09-001`

### Follow-up
1. Commit the release pass so the handoff can return to a clean worktree state.

## 2026-03-18 - Generalized workflow template conversion

**Type:** docs_or_process_only  
**Status:** COMPLETE  
**Git Head:** 173218e  
**Worktree:** clean

### What changed
- Replaced the CDP-specific operating docs with a generalized truth-first workflow scaffold.
- Simplified the hygiene validator so it enforces the generic template boundaries.
- Removed the product implementation, infra, tests, and archived domain content from this copy.

### Verification
- `python scripts/check_state_docs.py` -> PASSED
- `git status --short` -> clean
- `rg --files` -> only template docs and validator remain

### Follow-up
1. Attach a real project adapter only when this template is used for a new repo.

## 2026-03-18 - Bootstrap and operating mode split

**Type:** docs_or_process_only  
**Status:** COMPLETE  
**Git Head:** 2922f57  
**Worktree:** dirty (pre-commit)

### What changed
- Added explicit `bootstrap` and `operating` modes to the workflow contract.
- Added machine-readable mode metadata to `AGENTS.md` and `PROJECT_STATE.yaml`.
- Updated the template docs to treat bootstrap as a first-class baseline phase.

### Verification
- `python scripts/check_state_docs.py` -> PASSED
- `git status --short` -> dirty before commit

### Follow-up
1. Populate project-specific adapter values when this template is reused for a real project.

## 2026-03-18 - Dry-run bootstrap fixture validated

**Type:** docs_or_process_only  
**Status:** COMPLETE  
**Git Head:** 2e3eaef  
**Worktree:** dirty (pre-commit)

### What changed
- Added a self-contained sample project fixture with bootstrap and operating snapshots.
- Validated both snapshots with the same hygiene checker used by the template root.
- Recorded the dry-run result in the root live-state docs and evidence ledger.

### Verification
- `python scripts/check_state_docs.py fixtures/bootstrap_dry_run/bootstrap` -> PASSED
- `python scripts/check_state_docs.py fixtures/bootstrap_dry_run/operating` -> PASSED

### Follow-up
1. Reuse the same pattern when bootstrapping a real inherited repo.

## 2026-03-18 - Messy inherited repo bootstrap validated

**Type:** docs_or_process_only  
**Status:** COMPLETE  
**Git Head:** 7a8119c  
**Worktree:** clean

### What changed
- Added an adversarial inherited-repo fixture with contradictory stack and deployment signals.
- Bootstrapped the fixture without inventing certainty.
- Verified the bootstrap snapshot with the docs checker.

### Verification
- `python scripts/check_state_docs.py fixtures/messy_inherited_repo/bootstrap` -> PASSED

### Follow-up
1. Use this fixture as the next guardrail when improving bootstrap question quality.

## 2026-03-18 - Public release hardening added

**Type:** docs_or_process_only  
**Status:** COMPLETE  
**Git Head:** 6775286  
**Worktree:** clean

### What changed
- Added a one-command initialization script with optional minimal mode.
- Added a project adapter file, bootstrap quality rubric, prompts, GitHub automation, and a license.
- Validated the init script in a temporary directory.

### Verification
- `python scripts/init_template.py --name "Demo Project" --target <tmp>` -> PASS
- `python scripts/check_state_docs.py <tmp>` -> PASS

### Follow-up
1. Publish the template with a release note for the new init and minimal modes.

## Template Entry

### YYYY-MM-DD - [Task Name]

**Type:** docs_or_process_only / verification_only / app_code / data_pipeline / infrastructure
**Status:** COMPLETE / PARTIAL / BLOCKED / PAUSED
**Git Head:** [sha]
**Worktree:** clean / dirty

#### What changed
- [change]

#### Verification
- [command] -> [result]

#### Evidence
- [artifact path]

#### Follow-up
1. [next action]
