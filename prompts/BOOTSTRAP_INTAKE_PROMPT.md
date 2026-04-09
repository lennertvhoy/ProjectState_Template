# Bootstrap Intake Prompt

Use this when initializing a new or inherited repo.
This is typically the first question set the coding agent asks after reading the
repo and noticing it is still in `bootstrap` mode.

Rules:
- ask only what is needed to unblock truthful bootstrap
- do not invent architecture or maturity
- preserve unknowns explicitly when the user cannot prove something yet
- treat bootstrap as a broader discovery and planning phase, not a quick prelude to coding
- do not pretend placeholder backlog items are enough to leave bootstrap

Ask only the minimum strategic questions needed:

1. What is this project in one sentence?
2. Who is the primary user or operator?
3. What stage is the project in?
4. What is the next milestone that matters?
5. What must this project not become?
6. What systems or integrations are non-negotiable?
7. What deployment/runtime is targeted first?
8. What are the top constraints?
9. What is the biggest current blocker?
10. What should the agent optimize first?
