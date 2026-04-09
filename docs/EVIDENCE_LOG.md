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
- Add timestamps for anything that may become stale.

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
