# Subagent Review Output Template

Subagents inspect, they do not synthesize. The lead agent owns synthesis.

When you delegate to a subagent, require exactly this output format. No essays.
No speculative rewrites.

```markdown
Verdict: pass / fail / concern

Findings:
1. ...
2. ...

Required fixes:
1. ...
2. ...

Evidence checked:
- ...

Confidence: high / medium / low
```

## Usage Notes

- The lead agent must still read the original files and not blindly trust the subagent.
- A `concern` verdict means the subagent found something that needs human or CTO judgment.
- If there are no required fixes, write `None` under that heading.
- Keep findings to the five most important items.
- Subagents work only in their bounded isolated clone/worktree and return a commit
  plus this summary. They do not edit `PROJECT_STATE.yaml`, `STATUS.md`,
  `NEXT_ACTIONS.md`, or other global StateSpec truth, push the integration branch,
  open a competing PR, or claim whole-slice completion.
