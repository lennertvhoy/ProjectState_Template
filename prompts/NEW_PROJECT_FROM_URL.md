# New ProjectState project from URL

```text
Use the public ProjectState template at:

https://github.com/lennertvhoy/ProjectState_Template

to create a new project in the current folder with the default core profile.

Ask me for the project name, primary user, and one observable outcome if they are
not already explicit. Do not ask for architecture, deployment, or governance
machinery before the first vertical user journey makes those choices necessary.

Materialize with scripts/init_template.py. Do not retain the template repository's
Git history or template-maintenance state. Initialize a fresh main branch only
after verifying the destination is correct.

Then:
1. put the human-confirmed user, outcome, scope, non-goals, and durable constraints
   in PROJECT.md;
2. define one smallest real primary journey in STATE.yaml;
3. run that journey before broad secondary validation;
4. implement only the first vertical slice;
5. record bounded evidence in evidence/<slice-id>/summary.md;
6. run python3 scripts/projectstate_gate.py.

The first scaffold is expected to be not validated. Never turn it green by
changing acceptance or governance. Two failures at one delivery boundary require
simplifying an assumption and removing a moving part before adding machinery.

Use --profile hardened only if I explicitly select it for a named security,
compliance, review, or delivery obligation. Do not select a v5 compatibility
profile implicitly.

Configure or push to a remote only when that external action is in scope. Keep
remote delivery, CI, deployment, and human acceptance as separate claims.
```
