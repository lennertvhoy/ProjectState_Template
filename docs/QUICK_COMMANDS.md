# ProjectState Quick Commands

Copy-paste commands for the most common ProjectState tasks.

For the beginner walkthrough, see `docs/GETTING_STARTED_5_MIN.md`.  
For profile details, see `docs/ADOPTION_PROFILES.md`.

## Start a new project

```bash
# Recommended default
python3 scripts/init_template.py new --name "My Project" --profile solo

# Smallest footprint
python3 scripts/init_template.py new --name "My Project" --profile minimal

# Into a specific directory
python3 scripts/init_template.py new --name "My Project" --profile solo --target ./my-project
```

## Adopt ProjectState in an existing repo

```bash
# Safe preview first
python3 scripts/init_template.py adopt --name "My Project" --dry-run

# Apply with the recommended profile
python3 scripts/init_template.py adopt --name "My Project" --profile solo

# Keep the existing README and add a link section
python3 scripts/init_template.py adopt --name "My Project" --profile solo --readme-link
```

## Upgrade an existing ProjectState repo

```bash
# Preview what the template would copy
python3 scripts/projectstate_upgrade.py /path/to/repo

# Apply only safe missing managed assets
python3 scripts/projectstate_upgrade.py /path/to/repo --apply
```

## Daily checks

```bash
# Fast health summary
python3 scripts/projectstate_doctor.py

# Documentation hygiene
python3 scripts/check_state_docs.py

# Schema-backed validation
python3 scripts/projectstate_validate_schema.py

# Version alignment
python3 scripts/projectstate_version_check.py
```

## Before claiming closure-grade

```bash
# Machine-checkable closure audit
python3 scripts/projectstate_audit.py

# Strict audit (fails on warnings)
python3 scripts/projectstate_audit.py --strict
```

## Finish a green slice

After the branch is pushed and its PR exists, confirmed `agent_after_green`
projects use one idempotent finish command:

```bash
python3 scripts/projectstate_finish_slice.py \
  --root . \
  --pr-number 123 \
  --expected-pr-head <40-character-sha> \
  --delivery-policy PROJECT_STATE.yaml \
  --evidence-folder docs/evidence/YYYY-MM-DD-slice \
  --merge-method squash \
  --handoff-output /absolute/path/to/final-handoff.json
```

The command refuses unconfirmed or `human_merge` policies. It retains recovery
state on failure and deletes the remote branch/releases isolation only after
direct default-branch CI and post-merge verification pass.

## Evidence and runtime proof

```bash
# Initialize an evidence folder
python3 scripts/projectstate_evidence_pack.py init docs/evidence/YYYY-MM-DD-slice --slice-id BL-123

# Hash artifacts and scan for obvious secrets
python3 scripts/projectstate_evidence_pack.py hash docs/evidence/YYYY-MM-DD-slice
python3 scripts/projectstate_evidence_pack.py scan docs/evidence/YYYY-MM-DD-slice

# Validate the evidence pack
python3 scripts/projectstate_evidence_pack.py check docs/evidence/YYYY-MM-DD-slice --strict

# Runtime identity for a user-facing service
python3 scripts/projectstate_runtime_proof.py --evidence-dir docs/evidence/YYYY-MM-DD-slice --url http://localhost:3000

# Re-probe that exact local runtime artifact
python3 scripts/projectstate_runtime_truth_check.py --artifact docs/evidence/YYYY-MM-DD-slice/runtime_identity.json --expected-endpoint http://localhost:3000

# Remote runtimes must expose a revision header equal to the Git HEAD
python3 scripts/projectstate_runtime_proof.py --evidence-dir docs/evidence/YYYY-MM-DD-slice --url https://service.example/health --revision-header X-Revision
python3 scripts/projectstate_runtime_truth_check.py --artifact docs/evidence/YYYY-MM-DD-slice/runtime_identity.json --expected-endpoint https://service.example/health --allow-remote

# Runtime identity for docs/scripts-only slices
python3 scripts/projectstate_runtime_proof.py --no-runtime-required --evidence-dir docs/evidence/YYYY-MM-DD-slice
```

## Browser verification

ProjectState requires browser-verification evidence for user-facing closure, not a specific browser automation provider.

```bash
# Initialize a provider-agnostic browser verification record
python3 scripts/projectstate_browser_verify.py init docs/evidence/YYYY-MM-DD-slice

# Validate browser verification evidence (strict mode requires explicit limits for manual providers)
python3 scripts/projectstate_browser_verify.py check docs/evidence/YYYY-MM-DD-slice --strict

# Record sha256 hashes for browser artifacts
python3 scripts/projectstate_browser_verify.py hash docs/evidence/YYYY-MM-DD-slice

# Summarize provider, checks, artifacts, and known limits
python3 scripts/projectstate_browser_verify.py summarize docs/evidence/YYYY-MM-DD-slice
```

Kimi WebBridge is a preferred provider when available, not a required dependency. Playwright, agent-native browser tools, existing E2E tests, manual screenshots, or custom tooling are accepted when evidence is durable and honestly scoped.

## Handoff helper

```bash
# Print a read-only handoff snapshot
python3 scripts/projectstate_handoff.py

# Include validation output in the snapshot
python3 scripts/projectstate_handoff.py --test-command "python3 scripts/check_state_docs.py"
```

## Bootstrap gate

```bash
# Before switching a repo from bootstrap to operating
python3 scripts/check_state_docs.py --bootstrap-gate
```
