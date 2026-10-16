---
name: Feature request
about: Propose a change to the template, its scripts, or the gate
title: ""
---

## The user and the outcome

This project is outcome-first. Describe the person who benefits and the result
they should be able to reach. Lead with the user and the outcome, not the
mechanism.

- User:
- Outcome after this change:

## The problem today

What is hard or impossible today, and for whom? Give a concrete example of the
primary journey that should work.

## Proposed change

The smallest change that would make that journey pass.

## Non-goals check

The template's non-goals are listed in
[PROJECT.md](https://github.com/lennertvhoy/ProjectState_Template/blob/main/PROJECT.md).
Confirm this request does not pull the template toward any of them:

- Acting as an application runtime dependency.
- Encoding any project's architecture in the workflow.
- Making local tests equivalent to user success, remote delivery, or owner acceptance.
- Requiring backlog, history, release, signing, or multi-agent machinery for every project.
- Schedulers, thread routers, autonomous loops, or host-specific team configuration in the template.

Does the request touch the managed contract (`core/AGENTS.managed.md`) or the
gate? If so, it can only change through a recorded release; note that here.

## Alternatives considered

Any simpler option that already exists or that you rejected, and why.
