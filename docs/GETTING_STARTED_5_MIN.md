# Getting Started In 5 Minutes

Use this when you want the shortest safe path from an empty or inherited repo
to a StateDD-guided coding-agent session.

For a beginner-friendly diagram and prompt map, see
`docs/WORKFLOW_FOR_BEGINNERS.md`.

## 1. Pick The Setup Path

For a new project:

```bash
python3 scripts/init_template.py new --name "Your Project"
```

For an existing repo, preview first:

```bash
python3 scripts/init_template.py adopt --name "Your Project" --dry-run
```

Then adopt when the preview is acceptable:

```bash
python3 scripts/init_template.py adopt --name "Your Project"
```

## 2. Start The Coding Agent

For OpenCode, paste:

```text
Read prompts/OPENCODE_STARTUP_PROMPT.md and follow it exactly.
```

For another terminal coding agent, paste:

```text
Read prompts/CODING_AGENT_STARTUP_PROMPT.md and follow it exactly.
```

## 3. Let Bootstrap Stay Honest

The first agent session should read:

1. `AGENTS.md`
2. `STATUS.md`
3. `PROJECT_STATE.yaml`
4. `PROJECT_DNA.yaml`
5. `NEXT_ACTIONS.md`

If the repo is still unclear, the agent should inspect first and ask only the
minimum strategic questions needed. It should not invent project truth.

## 4. Use The CTO Lane For Non-Trivial Work

For work that changes multiple files, architecture, runtime behavior, state
structure, integrations, or user-facing behavior, open a separate planning chat
and paste:

```text
Read prompts/CTO_SESSION_PROMPT.md and act as the CTO lane for this repo.
```

The CTO lane should produce one scoped coding-agent prompt, not a broad plan.

## 5. Work In Small Slices

Each implementation slice should:

- define one coherent scope
- verify directly with commands or runtime evidence
- update state files only when truth changes
- keep `NEXT_ACTIONS.md` active-only
- end with a final handoff

Use this helper near the end of a slice:

```bash
python3 scripts/statedd_handoff.py
```

If you want the helper to run validation and include the output:

```bash
python3 scripts/statedd_handoff.py --test-command "python3 scripts/check_state_docs.py"
```

## 6. Run The Gates

For normal hygiene:

```bash
python3 scripts/check_state_docs.py
python3 scripts/test_init_template.py
python3 scripts/statedd_doctor.py
```

Before claiming closure-grade:

```bash
python3 scripts/statedd_audit.py
```

Before leaving bootstrap:

```bash
python3 scripts/check_state_docs.py --bootstrap-gate
```

If the bootstrap gate fails, keep the repo in `bootstrap` and fix the reported
baseline gaps instead of claiming operating mode.

## What Not To Do

- Do not treat chat memory as repo truth.
- Do not accept screenshots without runtime identity proof.
- Do not turn a failed search into "never existed".
- Do not let `NEXT_ACTIONS.md` become a long backlog.
- Do not switch to `operating` until the baseline is proven.
