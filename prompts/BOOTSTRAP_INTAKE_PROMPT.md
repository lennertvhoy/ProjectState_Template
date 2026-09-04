# Bootstrap intake prompt

Ask only what is needed to establish the first real product journey:

1. Who is the primary user?
2. What observable outcome should they achieve?
3. What must this project not become?
4. Which durable constraints are non-negotiable?
5. What is the smallest end-to-end journey that would prove the first slice?
6. In which representative environment must it work?

Record the human-confirmed answers in `PROJECT.md` and `STATE.yaml`. Leave an
unknown explicit when it cannot be confirmed. Do not invent architecture,
deployment, integrations, backlog structure, release policy, or compliance
machinery before the first journey makes them necessary.

The default profile is `core`. Offer `hardened` only for a named security,
compliance, review, or delivery obligation. Never infer permission for remote
writes, merge, deployment, or product acceptance from profile choice.
