# Coding Agent Startup Prompt

Paste this into the coding agent when starting a new session and you do not yet
have a scoped prompt from the CTO lane.

```text
Read these files first in order:
1. AGENTS.md
2. STATUS.md
3. PROJECT_STATE.yaml
4. PROJECT_DNA.yaml
5. NEXT_ACTIONS.md

Then follow the repo contract exactly.

Your first job is to determine which of these two situations applies:

1. Fresh bootstrap or unclear repo state
2. Existing repo state with no current CTO prompt

If this is a fresh bootstrap or the repo is still unclear:
- do not start implementing yet
- inspect the repo
- ask only the minimum strategic questions needed to establish truthful bootstrap state
- update nothing until the project intent is clear enough to do so safely

If this is an existing repo state but no CTO prompt was provided:
- reconstruct the current verified state from the repo files
- identify what appears to be the highest-leverage next step
- do not begin non-trivial implementation yet
- first produce a CTO-ready handoff and a draft CTO prompt with the context needed to continue safely
- make that draft CTO prompt require `prompts/TOOL_MODEL_ROUTING_GUIDE.md` when tool/model choice matters, `prompts/FINAL_HANDOFF_TEMPLATE.md`, `prompts/RUNTIME_IDENTITY_CHECKLIST.md`, and the relevant validation commands

Treat work as non-trivial if it involves any of:
- multiple-file changes
- architecture or workflow changes
- user-facing behavior
- migrations, integrations, or state-structure changes
- anything likely to require more than one implementation prompt

Before non-trivial implementation, run this preflight from the repo root:

```bash
python3 scripts/statedd_git_safety_check.py --mode normal_branch
```

This one transaction proves the requested repo/common directory, effective
identity, metadata ownership and real writability, fsck, and mandatory fetch.
Any nonzero writable-mode result makes the session read-only until repaired and
an explicit `--restart-session` succeeds.

For containers or independent/parallel agents, use the default full-clone path:

```bash
python3 scripts/statedd_agent_worktree.py start --slice-id <BL-XXX>
```

This provisions an independent object database. Linked worktrees are available
only with `--isolation-mode worktree --worktree-opt-in
--trusted-local-machine`; never use them across containers or unknown UID/GID.
Use `python3 scripts/statedd_agent_worktree.py list` to inspect retained state.

If the preflight blocks, stop implementation and produce a Git safety recovery
handoff. If dirty files exist, run
`python3 scripts/statedd_worktree_guard.py --mode classify-dirty` and record the
classification table in the evidence folder before any non-trivial edits.

Always:
- anchor on verified current truth
- forbid overclaiming
- keep negative searches negative: use `not found`, `not currently locatable`, or `not proven`
- require runtime identity proof before accepting or investigating user-facing behavior
- treat remembered or user-supplied model capability, pricing, context-window, and availability claims as `reported` until verified from current primary sources when they affect routing
- include any CTO-selected tool/model/settings in the implementation prompt or final handoff
- use `prompts/TOOL_MODEL_ROUTING_GUIDE.md` when drafting a CTO prompt that should choose between tools, models, reasoning settings, context strategies, or budget modes
- use `prompts/SLICE_CONTRACT_TEMPLATE.md` before starting implementation
- use `prompts/EVIDENCE_README_TEMPLATE.md` for the claim ledger in every evidence folder
- answer the anti-brittleness questions in `ANTI_BRITTLENESS_GUARD.md` for every non-trivial fix or feature slice
- use `prompts/RUNTIME_IDENTITY_CHECKLIST.md` before UI acceptance or regression forensics
- use `prompts/ACCEPTANCE_FREEZE_TEMPLATE.md` after accepting a user-facing milestone
- use `prompts/FINAL_HANDOFF_TEMPLATE.md` for the final handoff shape
- run `python3 scripts/statedd_audit.py` before claiming closure-grade and `python3 scripts/statedd_doctor.py` for a quick health snapshot
- respect explicit human overrides per `AGENTS.md`, but record them honestly as `partial`, `override-approved`, or `not closure-grade`

If a CTO lane already exists and the user only forgot to paste the latest CTO prompt:
- do not guess the missing scope
- produce the best possible CTO-ready handoff first
- ask the user to continue from the CTO lane before non-trivial implementation

If the task is truly trivial and safely isolated, you may complete it directly.
Otherwise, stop after producing:
1. current verified truth
2. explicit unknowns or risks
3. recommended next step
4. a paste-ready CTO handoff
5. a draft next prompt for the coding agent
```
