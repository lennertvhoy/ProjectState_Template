# Release Notes — StateDD Template v4

**Status:** release-candidate ready  
**Version:** statedd-template-v4  
**Date:** 2026-06-23  

> This file is release-candidate ready. Do not publish a GitHub release from it
> until the human product owner explicitly says: "Publish the GitHub release now."

## One-line description

State Driven Development template for AI-assisted software projects with repo truth, runtime identity, evidence packs, schema validation, non-destructive adoption, and clean agent handoffs.

## Suggested GitHub topics

- ai-agents
- agentic-workflow
- ai-assisted-development
- software-development
- evidence
- runtime-identity
- schema-validation
- developer-tools
- prompt-engineering
- project-template

## What is StateDD Template?

A lightweight, executable workflow for AI-assisted software projects. It keeps
humans in control while giving coding agents a shared source of truth inside the
repo: live state, a short active queue, evidence-backed claims, and clean
handoffs between planning and implementation.

## Highlights in this release

- **Template-maintenance / downstream mode split** — the root repo maintains the
template; generated and adopted repos start in bootstrap mode with clear
separation of responsibilities.
- **Evidence pack manifests and redaction gate** — every closure-grade evidence
folder can carry a `manifest.json` with claims, artifact hashes, and conservative
redaction scanning.
- **Non-destructive downstream upgrade tooling** — `statedd_upgrade.py` brings an
existing StateDD repo forward without overwriting project truth.
- **Adoption profiles** — initialize or adopt with `minimal`, `solo`, `team`, or
`regulated` profiles matched to project needs. Default recommendation is `solo`.
- **Bootstrap wizard MVP** — interactive and `--answers` modes for the minimum
strategic questions needed to bootstrap honestly.
- **Schema-driven example project** — `schemas/examples/schema_prompt_loop/`
shows one schema validating data and generating prompt material so docs and
prompts cannot drift from the contract.
- **Executable workflow tooling** — `statedd_audit.py`, `statedd_doctor.py`,
`statedd_validate_schema.py`, `statedd_runtime_proof.py`, `statedd_handoff.py`,
and `statedd_version_check.py` make the workflow machine-checkable.

## Quick start

New project:

```bash
python3 scripts/init_template.py new --name "Your Project" --profile solo
python3 scripts/check_state_docs.py
```

Existing repo:

```bash
python3 scripts/init_template.py adopt --name "Your Project" --dry-run
python3 scripts/init_template.py adopt --name "Your Project" --profile solo
python3 scripts/check_state_docs.py
```

For all common commands, see `docs/QUICK_COMMANDS.md`.

## Known limits

- The bootstrap wizard is an MVP; it does not replace CTO-lane bootstrap judgment.
- The upgrade helper copies safe managed assets but does not semantic-merge
customized workflow files.
- The redaction scanner is pattern-based and cannot prove absence of secrets.
- Browser/runtime UI verification remains future work (BL-WB-001).

## License

Released under the custom StateDD license in `LICENSE`. Free use, modification,
distribution, and commercial use are permitted; teaching and training rights are
reserved. See `LICENSE_FAQ.md` for plain-language guidance.
