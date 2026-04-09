# WORKLOG

**Purpose:** Append-only history for completed work.

Use this file for dated session notes, verification summaries, and references to evidence artifacts.

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
