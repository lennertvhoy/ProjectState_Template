# Evidence README Template

Copy this into every evidence folder as `README.md`. Replace placeholders with
real values. The claim ledger is the core of executable StateDD.

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

- Claim: <concrete claim 2>
  Evidence: <command or artifact path>

## Verification Log

| Check | Command / Path | Result |
| --- | --- | --- |
| tests | `npm test` or `pytest` | pass / fail |
| lint | `npm run lint` | pass / fail |
| build | `npm run build` | pass / fail |
| audit | `python3 scripts/statedd_audit.py` | pass / fail |
| runtime identity proof | `prompts/RUNTIME_IDENTITY_CHECKLIST.md` | yes / no |
| schema ownership validation | `prompts/SCHEMA_OWNERSHIP_TEMPLATE.md` | yes / no / not applicable |

## Closure State

- Implemented: yes / no
- Validated: yes / no
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
