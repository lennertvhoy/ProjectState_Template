# StateDD Template

StateDD is an agent-operated repository workflow. Humans provide project intent,
select profiles and permissions, and review evidence. Coding agents read
`AGENTS.md`, operate the StateDD scripts and skills, maintain repository truth,
and produce the handoff.

This repository maintains the reusable `statedd-template-v5` contract. It is not
an application runtime. Generated or adopted projects start in `bootstrap` and
move to `operating` only after their own truth is established.

## Operator path

1. Choose `minimal`, `solo`, `team`, or `regulated` in
   [`docs/ADOPTION_PROFILES.md`](docs/ADOPTION_PROFILES.md).
2. Initialize a new project or adopt an existing one:

   ```bash
   python3 scripts/init_template.py new --name "Your Project" --profile solo
   python3 scripts/init_template.py adopt --name "Your Project" --profile solo --dry-run
   ```

3. Give the coding agent one instruction:

   ```text
   Read AGENTS.md and follow its declared read order and controls.
   ```

4. Review the evidence and handoff produced by the agent.
5. Keep local, remote, GitHub, CI, runtime, and human-accepted truth distinct.

The agent-facing constitution is [`AGENTS.md`](AGENTS.md). Procedures live in
`skills/` and `commands/`; executable invariants live in `scripts/`; reference
material lives in `docs/`. These sources are loaded on demand according to
`AGENTS.md`.

## Profiles

Profiles are positive allowlists recorded in `STATEDD_ASSETS.json`. They keep
template-maintenance tests, fixtures, historical evidence, incidents, and
release history out of downstream projects unless explicitly selected. Template
development dependencies are intentionally root-only.

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
- [`docs/ADOPTION_PROFILES.md`](docs/ADOPTION_PROFILES.md) — profile selection
- [`prompts/CODING_AGENT_STARTUP_PROMPT.md`](prompts/CODING_AGENT_STARTUP_PROMPT.md) — generated startup control
- [`scripts/init_template.py`](scripts/init_template.py) — new/adopt workflow
- [`scripts/statedd_quality_gate.py`](scripts/statedd_quality_gate.py) — local slice gate
- [`scripts/statedd_handoff.py`](scripts/statedd_handoff.py) — read-only handoff snapshot
