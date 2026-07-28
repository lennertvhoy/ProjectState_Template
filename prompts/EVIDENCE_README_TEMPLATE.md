# Evidence README Template

Copy this into every evidence folder as `README.md`. Replace placeholders with
real values. The claim ledger is the core of executable ProjectState.

```markdown
# Evidence: <slice-title>

**Slice:** [BL-XXX] <title>  
**Date:** YYYY-MM-DD  
**Agent:** coding-agent  
**Branch:** main  
**HEAD:** abc1234

## Claims

- Claim: <concrete claim 1>
  Evidence: <command or artifact path>
  Evidence type: implementation | test | product_behavior | runtime_truth | adversarial | known_bad_event | post_deploy | security_privacy | state_update

- Claim: <concrete claim 2>
  Evidence: <command or artifact path>
  Evidence type: implementation | test | product_behavior | runtime_truth | adversarial | known_bad_event | post_deploy | security_privacy | state_update

## Failure Scan

- Required: yes / no
- Path: `docs/failure_scans/<slice>.md` / not applicable
- Adjacent failures checked:
- Known bad events covered:

## Worktree Dirty File Classification

| status | path | category | owner/notes |
| --- | --- | --- | --- |
| clean / ?? / M | `path` / not applicable | intended_slice_work / pre_existing_unrelated / generated_artifact / unknown_do_not_touch / safe_to_discard_after_proof | |

## Anti-Brittleness Review

| Question | Answer |
| --- | --- |
| What invariant prevents the failure class? | |
| Is the fix typed/schema/state-machine/validator/contract-based? | |
| Which behavior is centralized instead of scattered? | |
| Which observed examples are covered by general rules rather than exact strings? | |
| What adjacent cases were tested? | |
| What brittle pattern was explicitly avoided? | |
| Did the slice add keyword buckets, regex branches, exact prompt handling, fixture-only behavior, sleeps/timeouts, global mutable state, silent fallback, or provider-specific assumptions? | |
| If yes, why is that not the authority path? | |

## Verification Log

| Check | Command / Path | Result |
| --- | --- | --- |
| tests | `npm test` or `pytest` | pass / fail |
| lint | `npm run lint` | pass / fail |
| build | `npm run build` | pass / fail |
| schema validation | `python3 scripts/projectstate_validate_schema.py` | pass / fail |
| evidence manifest | `python3 scripts/projectstate_evidence_pack.py check docs/evidence/<slice>` | pass / fail |
| worktree guard | `python3 scripts/projectstate_worktree_guard.py --mode start-slice` / `--mode closure` | pass / fail |
| brittleness scan | `python3 scripts/projectstate_brittleness_check.py` | warnings reviewed / not applicable |
| audit | `python3 scripts/projectstate_audit.py` | pass / fail |
| runtime identity proof | `prompts/RUNTIME_IDENTITY_CHECKLIST.md` | yes / no |
| schema ownership validation | `prompts/SCHEMA_OWNERSHIP_TEMPLATE.md` | yes / no / not applicable |
| product quality gate | project-specific command/path | pass / fail / not applicable |
| runtime truth gate | project-specific command/path | pass / fail / not applicable |
| redteam/adversarial gate | project-specific command/path | pass / fail / not applicable |
| known bad events gate | project-specific command/path | pass / fail / not applicable |

## Evidence Pack Manifest

- Manifest: `manifest.json` / not applicable
- Redaction status: checked / checked_with_limits / manual_required / override_used / unchecked

## Runtime Identity

- Runtime required: yes / no
- Artifact: `runtime_identity.json` / not applicable
- Endpoint:
- Process ownership proven: yes / no / not applicable
- Known limits:

## Browser Verification

- Browser verification required: yes / no / not applicable
- Browser verification artifact: `browser_verification.json` / not applicable
- Provider used:
- Fallbacks considered:
- Known browser verification limits:

## Closure State

- Implemented: yes / no
- Validated: yes / no
- Global quality gates passed: yes / no / not applicable
- Closure-grade: yes / no
- Accepted: pending / yes / rejected / conditionally accepted

## Human Override

- Human override used: no
- If yes:
  - Rule overridden: ...
  - Requested by: ...
  - Reason accepted: ...
  - Remaining risk: ...
  - Still closure-grade: yes / no

## Risks / What Remains Partial

- ...
```
