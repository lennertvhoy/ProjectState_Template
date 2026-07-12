# New StateDD Project From URL

Use this as the canonical empty-folder startup prompt:

```text
Use the public StateDD template at:

https://github.com/lennertvhoy/StateDD_Template

to create a new project in the current folder.

Ask me first for:

1. the project name;
2. a concise description of its purpose.

Ask for the destination GitHub repository only when you cannot create or infer
one through the authenticated GitHub tooling available in this environment.

Use the StateDD `team` profile because this project may use parallel coding
subagents.

Materialization requirements:

- Clone the template into a temporary directory.
- Instantiate the selected downstream profile into the current absolute path.
- Do not retain the template repository's `.git` directory or Git history.
- Do not copy template-maintenance tests, evidence, incidents, worklogs, release
  history, or active template state into the project.
- Remove the temporary clone only after successful project materialization.
- Initialize a fresh Git repository using `main`.

Then enter StateDD bootstrap mode.

During bootstrap:

- Inspect the actual repository and environment before making architecture claims.
- Ask only architecture-critical questions.
- Establish project purpose, scope, architecture, constraints, and initial
  delivery milestones.
- Fill every required StateDD file truthfully.
- Use explicit `unknown` values with follow-up actions rather than inventing facts.
- Build a prioritized backlog for the first project milestone.
- Keep `NEXT_ACTIONS.md` short.
- Present the `team` profile's recommended `agent_after_green` delivery mode and
  the cautious `human_merge` alternative. Require me to confirm exactly one mode
  once; never treat silence or the generated proposal as authorization.
- Record the confirmed mode under `delivery_policy`, including squash merge,
  exact-PR-head, clean-merge-state, review/thread, branch-head CI,
  merge-candidate CI, remote-closure, direct-main CI, and post-merge verification
  requirements.
- Keep force-push, shared-history rewrite, and automatic merge without CI
  forbidden. A CI-unavailable merge needs a separate explicit human override.
- Do not implement product features before the bootstrap baseline is coherent.

Before handoff:

- Run the bootstrap, schema, and applicable profile validation.
- Create clean, intentional bootstrap commits.
- Configure the new project's own GitHub remote.
- Push the bootstrap baseline.
- Leave the worktree clean.

For later implementation slices, follow the confirmed delivery policy. Under
`agent_after_green`, the coding agent owns commit, push, PR preparation,
exact-head squash merge after every configured gate passes, direct-main CI,
post-merge verification, the external final handoff, and remote branch deletion
only after verified closure. Under `human_merge`, stop before merge. Final
product acceptance remains mine in either mode.

Finish with a CTO-ready handoff containing:

- repository URL;
- branch;
- exact pushed HEAD;
- StateDD profile;
- project purpose;
- architecture summary;
- important decisions;
- unresolved architecture questions;
- prioritized backlog;
- recommended first implementation slice;
- validation performed;
- evidence paths;
- CI status;
- known limits.

Do not ask me to run routine StateDD, Git, validation, or handoff commands that
you can run yourself.
```
