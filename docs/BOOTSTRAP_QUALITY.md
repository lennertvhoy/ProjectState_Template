# Bootstrap Quality Rubric

Use this rubric to judge whether a bootstrap run was actually good.

## Core Checks

- Did bootstrap separate observed facts from assumptions?
- Did it avoid fantasy architecture?
- Did it preserve unknowns explicitly?
- Did it keep the active queue short?
- Did it avoid copying roadmap prose into state files?
- Did it present `human_merge` and `agent_after_green`, record exactly one
  human-confirmed delivery mode, and avoid treating a proposal as authority?
- Did it leave a clear path to `operating` mode?

## Scoring

- `pass` - honest, concise, useful
- `warn` - structurally valid but weak or incomplete
- `fail` - invents truth, bloats state, or hides unknowns
