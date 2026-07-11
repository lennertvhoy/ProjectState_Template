# StateDD Template

StateDD is an agent-operated repository workflow. Humans provide project intent,
priorities, permissions, feedback, and final acceptance. Coding agents initialize
projects, maintain repository truth, execute slices, validate results, integrate
subagents, commit and push changes, and produce CTO-ready handoffs.

This repository maintains the reusable `statedd-template-v5` contract. It is not
an application runtime. Generated or adopted projects start in `bootstrap` and
move to `operating` only after their own truth is established.

## Operator path

For a new project, start with an empty folder, open a coding agent, and paste
[`prompts/NEW_PROJECT_FROM_URL.md`](prompts/NEW_PROJECT_FROM_URL.md). Answer the
project name and purpose. The agent uses the `team` profile, materializes a fresh
repository, bootstraps it, pushes the baseline, and returns a compact handoff.

Then send that handoff to the CTO agent. For each approved slice, paste the CTO
prompt back to the coding agent. The agent owns isolation, parallel work,
integration, gates, evidence, commits, pushes, and the pull request.

For an existing repository, the coding agent can use the initializer directly:

```bash
python3 scripts/init_template.py adopt --name "Your Project" --profile team --dry-run
```

The human normally only answers architecture-critical questions and accepts the
finished product. CI availability changes the reported status; it does not make
routine local execution unusable.

The agent-facing constitution is [`AGENTS.md`](AGENTS.md). Procedures live in
`skills/` and `commands/`; executable invariants live in `scripts/`; reference
material lives in `docs/`. These sources are loaded on demand according to
`AGENTS.md`.

## Profiles

Profiles are positive allowlists recorded in `STATEDD_ASSETS.json`. They keep
template-maintenance tests, fixtures, historical evidence, incidents, and
release history out of downstream projects unless explicitly selected. Template
development dependencies are intentionally root-only. The new-project default is
`team` because the canonical path supports parallel agents and remote review;
`minimal`, `solo`, and `regulated` remain explicit alternatives. See
[`docs/ADOPTION_PROFILES.md`](docs/ADOPTION_PROFILES.md).

## Truth and safety

Before repository or StateDD mutation, run the centralized safety transaction:

```bash
python3 scripts/statedd_git_safety_check.py --mode normal_branch
```

Use full clones for containers and independent agents. Linked worktrees require
explicit trusted-local, same-identity opt-in. A failed writable preflight latches
the session read-only until repair and an explicit restart. A context file never
authorizes a remote push; remote mutation requires its explicit path and operator
authorization.

For a slice, the authoritative local gate is:

```bash
python3 scripts/statedd_quality_gate.py --gate-level 2 --verbose
```

Local validation is not CI or human acceptance. User-facing closure additionally
requires runtime identity and browser evidence. Comparative performance or
superiority claims remain benchmark-gated. Implemented ≠ validated ≠
closure-grade ≠ accepted; negative searches remain `not found` or `not proven`,
and non-trivial work requires an anti-brittleness review.

## License posture

The repository uses the custom source-available StateDD Free Use License with
teaching rights reserved; teaching/training rights are reserved. It is not a conventional permissive open-source
license. [`LICENSE`](LICENSE) still contains an unresolved copyright-owner
placeholder; release readiness is therefore not proven. See
[`LICENSE_FAQ.md`](LICENSE_FAQ.md) for the plain-language policy, not legal advice.

## Useful entrypoints

- [`AGENTS.md`](AGENTS.md) — canonical coding-agent constitution and read order
- [`prompts/NEW_PROJECT_FROM_URL.md`](prompts/NEW_PROJECT_FROM_URL.md) — canonical empty-folder prompt
- [`docs/ADOPTION_PROFILES.md`](docs/ADOPTION_PROFILES.md) — profile selection
- [`prompts/CODING_AGENT_STARTUP_PROMPT.md`](prompts/CODING_AGENT_STARTUP_PROMPT.md) — generated startup control
- [`scripts/init_template.py`](scripts/init_template.py) — new/adopt workflow
- [`scripts/statedd_quality_gate.py`](scripts/statedd_quality_gate.py) — local slice gate
- [`scripts/statedd_handoff.py`](scripts/statedd_handoff.py) — read-only handoff snapshot
