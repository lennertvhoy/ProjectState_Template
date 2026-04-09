# Final Handoff Template

Use this at the end of an implementation session when you need a canonical
handoff shape for the CTO lane.

```text
Final handoff for CTO lane

Current verified truth
- ...

What changed
- ...

Repo and runtime identity
- repo path: ...
- branch: ...
- head: ...
- process/container: ...
- port/base URL: ...
- rebuilt in this slice: yes | no

Direct verification
- command or artifact -> result

Evidence refs
- /absolute/path/to/artifact
- docs/EVIDENCE_LOG.md entry ID
- docs/ACCEPTANCE_FREEZES.md entry ID when a milestone was accepted

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
- whether the running artifact was rebuilt in this slice
- clean worktree status
- evidence references
- absolute file paths for evidence artifacts when available
- next recommended action
- paste-ready wording for the CTO chat
