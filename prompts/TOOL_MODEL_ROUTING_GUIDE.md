# Tool And Model Routing Guide

Use this guide from the CTO lane when the next slice would benefit from a
deliberate choice of chatbot, coding agent, model, reasoning setting, tool
surface, context strategy, or budget posture.

This guide is intentionally model-agnostic. Model catalogs, pricing, context
windows, and tool support change often. Do not bake stale benchmark claims into
the project state or coding-agent prompts.

## Routing Inputs

Ask only the minimum needed to choose a tool route:

- Which tools and models can the user actually access right now?
- Is the constraint quality, speed, free usage, privacy, rate limits, or cost?
- Does the task need repo access, browser access, shell access, GitHub access,
  external research, computer use, long context, image/document tooling, or no
  tools?
- Is the work planning, implementation, review, debugging, UI acceptance,
  migration, security-sensitive review, or documentation?
- How much verified context is already preserved in repo files versus chat?
- What must be proven before accepting the result?

## Freshness Rules

- Treat specific model capability, context-window, pricing, and availability
  claims as stale unless verified from primary docs or the provider UI/API in
  the current decision loop.
- If the user supplies model facts, label them as `reported` until verified.
- Prefer primary sources for current model facts. If current facts cannot be
  verified, say `not proven` and route by known task needs and risk tolerance.
- Do not claim one model is better than another without stating the basis:
  verified docs, direct project evidence, prior reported experience, or an
  assumption.

## Routing Output

When giving tool advice, provide a concise route:

```text
Recommended route
- planner/reviewer: <tool or chatbot>, <model>, <settings>
- coding agent: <tool>, <model>, <settings>
- optional support pass: <tool/model/settings or none>

Why this route
- quality/cost/speed/context tradeoff
- task risks this route controls
- what remains unverified

Config to use
- reasoning effort or thinking mode: <setting>
- context strategy: <what to paste, what to omit, what to keep in repo>
- tools to enable: <shell/browser/GitHub/web/subagents/etc.>
- tools to disable or avoid: <if relevant>
- verification gates: <commands, runtime proof, evidence artifacts>

Paste-ready prompt
- <prompt tailored to the selected tool/model/settings>
```

## Common Routing Patterns

- High-risk repo changes: use the strongest reliable coding/review model the
  user can access; require direct tests, runtime identity proof when relevant,
  and a final handoff.
- Budget-constrained implementation: allow a cheaper broad pass, then require a
  stronger review/fix/finish pass before accepting the work.
- Very long context: use a long-context model to summarize and compress into
  repo state, then send only the scoped slice to the coding agent.
- UI acceptance or regression forensics: prefer a tool stack with browser and
  screenshot/evidence support, but do not accept screenshots without runtime
  identity proof.
- Unknown or fast-moving model landscape: avoid vendor-specific assertions,
  compare available tools against the current slice, and mark unverified claims
  as `not proven`.

## Prompt Tailoring Rules

- A prompt for a weaker or cheaper model must be narrower, more explicit, and
  heavier on verification gates.
- A prompt for a strong reasoning model can include more architectural judgment,
  but must still forbid overclaiming and require direct verification.
- A prompt for a long-context model should ask it to extract durable facts into
  state files rather than keep truth trapped in chat.
- A prompt for a browser/computer-use tool must include runtime identity and
  evidence requirements before user-facing acceptance.
- A prompt for a no-tools chatbot must not ask it to verify repo/runtime truth;
  it should critique pasted evidence and write the next scoped coding prompt.
