# Final Handoff Template

Use this at the end of an implementation session when you need a canonical
handoff shape for the CTO lane.

```text
Final handoff for CTO lane

Remote-first summary
- repository URL: ...
- branch: ...
- exact HEAD: ...
- PR URL: ... | not currently locatable
- delivery status: local-only | pushed | PR opened | merged | CI verified
- CI status: verified | unavailable | not verified
- evidence index: ...

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
- Git safety report: docs/evidence/<slice>/git_safety_report.json | not captured
- requested path: ...
- repo path: ...
- canonical repo root: ...
- Git directory: ...
- Git common directory: ...
- effective UID/GID: ...
- common-directory owner/group/mode: ...
- critical metadata ownership/writability: pass | fail | not proven
- write-probe result: pass | fail | not run
- git fsck result: pass | fail | not run
- mandatory synchronization result: pass | fail | not run
- selected isolation mode: normal_branch | worktree | clone | read_only
- mutation permitted: yes | no
- read-only latch / restart required: inactive | active / yes | no
- read-only enforcement scope: StateDD-managed only | OS filesystem-enforced
- branch: ...
- head: ...
- origin remote URL: ...
- upstream branch: ...
- local HEAD: ...
- upstream HEAD: ...
- local HEAD equals upstream: yes | no | not proven
- worktree topology captured: yes | no
- current worktree path: ...
- linked worktrees: ...
- dirty files classified: yes | no | not applicable
- GitHub-visible deliverables: yes | no | not proven
- local-only files claimed: yes | no
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
- worktree topology captured: yes | no
- upstream branch: ...
- upstream HEAD: ...
- local HEAD equals upstream: yes | no | not proven
- GitHub-visible deliverables: yes | no | not proven
- local-only files claimed: yes | no

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
- worktree topology captured
- current worktree path
- linked worktrees
- upstream branch
- local HEAD
- upstream HEAD
- local HEAD equals upstream
- dirty files classified
- GitHub-visible deliverables
- local-only files claimed
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
