# StateDD Quick Commands

Copy-paste commands for the most common StateDD tasks.

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

## Adopt StateDD in an existing repo

```bash
# Safe preview first
python3 scripts/init_template.py adopt --name "My Project" --dry-run

# Apply with the recommended profile
python3 scripts/init_template.py adopt --name "My Project" --profile solo

# Keep the existing README and add a link section
python3 scripts/init_template.py adopt --name "My Project" --profile solo --readme-link
```

## Upgrade an existing StateDD repo

```bash
# Preview what the template would copy
python3 scripts/statedd_upgrade.py /path/to/repo

# Apply only safe missing managed assets
python3 scripts/statedd_upgrade.py /path/to/repo --apply
```

## Daily checks

```bash
# Fast health summary
python3 scripts/statedd_doctor.py

# Documentation hygiene
python3 scripts/check_state_docs.py

# Schema-backed validation
python3 scripts/statedd_validate_schema.py

# Version alignment
python3 scripts/statedd_version_check.py
```

## Before claiming closure-grade

```bash
# Machine-checkable closure audit
python3 scripts/statedd_audit.py

# Strict audit (fails on warnings)
python3 scripts/statedd_audit.py --strict
```

## Evidence and runtime proof

```bash
# Initialize an evidence folder
python3 scripts/statedd_evidence_pack.py init docs/evidence/YYYY-MM-DD-slice --slice-id BL-123

# Hash artifacts and scan for obvious secrets
python3 scripts/statedd_evidence_pack.py hash docs/evidence/YYYY-MM-DD-slice
python3 scripts/statedd_evidence_pack.py scan docs/evidence/YYYY-MM-DD-slice

# Validate the evidence pack
python3 scripts/statedd_evidence_pack.py check docs/evidence/YYYY-MM-DD-slice --strict

# Runtime identity for a user-facing service
python3 scripts/statedd_runtime_proof.py --evidence-dir docs/evidence/YYYY-MM-DD-slice --url http://localhost:3000

# Runtime identity for docs/scripts-only slices
python3 scripts/statedd_runtime_proof.py --no-runtime-required --evidence-dir docs/evidence/YYYY-MM-DD-slice
```

## Handoff helper

```bash
# Print a read-only handoff snapshot
python3 scripts/statedd_handoff.py

# Include validation output in the snapshot
python3 scripts/statedd_handoff.py --test-command "python3 scripts/check_state_docs.py"
```

## Bootstrap gate

```bash
# Before switching a repo from bootstrap to operating
python3 scripts/check_state_docs.py --bootstrap-gate
```
