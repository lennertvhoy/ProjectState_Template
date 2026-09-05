# Coding agent startup prompt

Paste this into a coding agent when no more specific task prompt exists.

```text
Read AGENTS.md, PROJECT.md, and STATE.yaml in that order. Then read only the
current slice's evidence/<slice-id>/summary.md and any nearest nested AGENTS.md
needed for the files you will touch.

Reconstruct the current outcome, slice, primary journey, blockers, risks, and
exact next action. Do not infer that passing tests means the product works.
Compare the handoff with the actual worktree and current evidence. Rerun a
journey when later changes invalidate its recorded result.

The human owns PROJECT.md, acceptance criteria, governance, risk exceptions, and
product acceptance. You may draft a proposed change, but do not apply one merely
to make your own work pass.

For implementation:
1. verify a clean or explicitly classified worktree and use a private branch for
   non-trivial work;
2. try the primary journey as early as practical;
3. implement the smallest change that can make it pass;
4. after two evidenced failures at the same boundary, reconsider the assumption,
   remove a moving part, and rerun the smallest journey before adding mechanism;
5. record the exact command, environment, result, artifacts, and limitations in
   the one evidence summary;
6. run relevant secondary checks;
7. update STATE.yaml coherently with the implementation;
8. run python3 scripts/projectstate_gate.py.

A failed, blocked, or unrun primary journey overrides green tests, linters,
hashes, repository validators, remote checks, and metadata.
When acceptance includes installation, run the distributed artifact in the
intended clean environment. Publication or rehearsal belongs in supporting
evidence; it does not change the primary journey's execution status.

Fail closed for destructive action, data loss/corruption, privilege escalation,
secrets/private-data exposure, and permission-boundary changes. Assess other
findings by consequence and exposure. Do not force-push, rewrite shared history,
deploy, publish, spend money, rotate credentials, or contact people without
explicit authority.

ProjectState is coordination only. Product code must start and run without
reading ProjectState files or tooling.

Finish with a concise handoff: outcome attempted, changes, primary-journey result,
secondary checks, blockers/risks, truth boundaries not proven, and exact next
action. Human acceptance remains pending unless the human explicitly provides it.
```
