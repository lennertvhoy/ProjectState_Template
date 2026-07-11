# StateDD in Five Minutes

5 Minutes: choose a profile, initialize the workflow, start the coding agent,
and review the handoff.

This is the five-minute operator path. OpenCode users may also start with
`prompts/OPENCODE_STARTUP_PROMPT.md`.

StateDD is an agent-operated repository workflow. Humans choose intent, profile,
and permissions; coding agents read `AGENTS.md`, operate the executable controls,
maintain truth, and produce the handoff.

## 1. Choose a profile

Read [`ADOPTION_PROFILES.md`](ADOPTION_PROFILES.md). `minimal` is the smallest
workflow; `team` is the default for new projects; `solo` is the smaller
single-agent alternative; `team` adds parallel-agent/review controls;
`regulated` adds stricter evidence and acceptance guidance.

## 2. Install the workflow

For a new project:

```bash
python3 scripts/init_template.py new --name "My Project" --profile team
```

For an existing project, preview first:

```bash
python3 scripts/init_template.py adopt --name "My Project" --profile team --dry-run
```

## 3. Start the coding agent

Give it this instruction:

```text
Read AGENTS.md and follow its declared read order and controls.
```

The agent-facing constitution is the authority. It routes the agent to skills,
commands, executable scripts, and reference docs only when needed.

## 4. Validate honestly

Before mutation, the agent runs the centralized Git safety preflight. At slice
closure it runs:

```bash
python3 scripts/statedd_quality_gate.py --gate-level 2 --verbose
python3 scripts/statedd_handoff.py
```

The handoff must distinguish implemented, locally validated, remote, CI, runtime,
closure-grade, and human-accepted truth. User-facing work also needs runtime
identity and browser evidence. A local pass is not a remote or CI pass. Run
`python3 scripts/check_state_docs.py --bootstrap-gate` before switching from
bootstrap to operating.
