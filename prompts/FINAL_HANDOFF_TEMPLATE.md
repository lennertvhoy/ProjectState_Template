# Final Handoff Template

Use this at the end of an implementation session when you need a canonical
handoff shape for the CTO lane.

```text
Final handoff for CTO lane

Current verified truth
- ...

Slice contract
- id: [BL-XXX]
- title: ...
- type: feature | fix | refactor | docs | spike | ops
- user_value: ...
- non_goals: ...
- acceptance_criteria: ...
- failure_scan: docs/failure_scans/<slice>.md | not applicable
- global_quality_gates: passed | failed | not run | not applicable

What changed
- ...

Four-state closure
- Implemented: yes | no  (code exists)
- Validated: yes | no  (lint/tests/build/browser checks passed)
- Closure-grade: yes | no  (evidence, state docs, commit, clean worktree, risks complete)
- Accepted: pending | yes | rejected | conditionally accepted  (CTO/human reviewed)

Release / update gate
- committed in repo: yes | no
- tests passed: yes | no
- app running with latest HEAD: yes | no | not applicable
- browser proof captured from latest running app: yes | no | not applicable
- product quality gate: passing | failing | not_run | not_applicable
- runtime truth gate: passing | failing | not_run | not_applicable
- redteam/adversarial gate: passing | failing | not_run | not_applicable
- known bad events gate: passing | failing | not_run | not_applicable
- post-deploy watch: passing | failing | not_run | not_applicable

Human override
- Human override used: yes | no
- If yes:
  - Rule overridden: ...
  - Requested by: ...
  - Reason accepted: ...
  - Remaining risk: ...
  - Still closure-grade: yes | no

Repo and runtime identity
- repo path: ...
- branch: ...
- head: ...
- process/container: ...
- port/base URL: ...
- rebuilt in this slice: yes | no
- duplicate runtimes checked: yes | no

Runtime identity artifact
- required: yes | no
- path: docs/evidence/<slice>/runtime_identity.json | not applicable
- endpoint: ...
- process ownership: proven | not proven | not applicable

Browser verification
- provider: kimi_webbridge | playwright | agent_native_browser | existing_e2e | manual_browser | custom | not applicable
- browser verification artifact: docs/evidence/<slice>/browser_verification.json | not applicable
- user-facing/runtime evidence status: valid | invalid | not applicable
- known limits:

Direct verification
- command or artifact -> result

Evidence refs
- /absolute/path/to/artifact
- docs/EVIDENCE_LOG.md entry ID
- docs/ACCEPTANCE_FREEZES.md entry ID when a milestone was accepted

Claim ledger (from evidence README)
- Claim: ...  Evidence: ...
- Claim: ...  Evidence: ...

Handoff claims vs verified truth
- Handoff-only claims that remain unverified: ...
- Claims verified by evidence or quality gate: ...

What remains partial or risky
- ...
- unresolved searches must be phrased as `not found`, `not currently locatable`, or `not proven`

Git state
- head: <sha>
- worktree: clean | dirty

Next recommended action
- ...

Paste-ready CTO wording
- Use the verified state above as the new baseline.
- Scope the next coding-agent step to ...
- Require verification for ...
```

Required fields:
- what changed
- what was directly verified
- repo path
- branch
- what remains partial or risky
- git head
- process or container serving the verified artifact
- port or endpoint used for verification
- runtime identity artifact path or explicit not applicable value
- whether the running artifact was rebuilt in this slice
- clean worktree status
- evidence references
- absolute file paths for evidence artifacts when available
- next recommended action
- paste-ready wording for the CTO chat
- four-state closure status (implemented, validated, closure-grade, accepted)
- human override declaration when applicable
