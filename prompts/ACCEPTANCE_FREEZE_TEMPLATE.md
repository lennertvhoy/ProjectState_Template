# Acceptance Freeze Template

Use this after a user-facing or operator-facing milestone is accepted.
The goal is to freeze the accepted state so later work cannot quietly drift away
from what was approved.

Record the result in `docs/ACCEPTANCE_FREEZES.md`, `WORKLOG.md`, or another
durable repo artifact.

```text
Acceptance freeze

Milestone
- name: ...
- scope: ...

Source identity
- repo path: ...
- branch: ...
- head: ...

Runtime identity
- process/container: ...
- port/base URL: ...
- route(s) covered: ...
- rebuilt in this slice: yes | no
- duplicate runtimes checked: yes | no

Evidence
- screenshot or artifact path: ...
- docs/EVIDENCE_LOG.md entry: ...

regression guard
- later work must branch from head ...
- later acceptance checks must prove the runtime still maps to this repo/commit lineage
- any route-role change must be explicit in backlog scope and evidence

Notes
- ...
```
