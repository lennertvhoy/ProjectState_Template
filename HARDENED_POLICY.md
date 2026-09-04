# ProjectState Hardened Overlay

This policy is installed only when a human selects `--profile hardened`. It adds
controls for projects whose exposure or obligations justify them. It does not
replace the primary journey and must not become an application dependency.

## Human ownership

Only the human risk owner may approve changes to this policy, the project
outcome, acceptance criteria, stop-lines, or a risk exception. An agent may
propose a change in the current evidence summary but cannot apply it merely to
make its own slice pass.

## Mandatory stop-lines

Fail closed for unresolved or unbounded risk involving:

- destructive or irreversible operations;
- data loss or corruption;
- privilege escalation or permission-boundary changes;
- secrets or private-data exposure;
- externally reachable critical or high-severity vulnerabilities.

Other findings require consequence, exposure, affected environment, owner, and
decision. Build-only or unreachable findings do not automatically block product
validation. Temporary acceptance requires a named human approver, rationale,
expiry, and a follow-up action.

## Delivery and compliance

Add remote-head proof, CI, review, signing, threat models, audit retention, or
regulated evidence only when the project or slice explicitly requires it. Keep
each proof tied to the boundary it crosses. Local product validation does not
claim remote delivery; remote delivery does not claim human product acceptance.

## Non-negotiable precedence

A failed primary journey blocks closure even when every hardened secondary gate
passes. Hardened controls may add blockers; they can never turn a failed product
journey green.
