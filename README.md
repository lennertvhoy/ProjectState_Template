# Truth-First Project Operating System

This repository is a generalized workflow template for technical projects.

It is structured around:

- stable operating rules in `AGENTS.md`
- current truth in `PROJECT_STATE.yaml`
- a short human snapshot in `STATUS.md`
- architecture invariants in `PROJECT_DNA.yaml`
- a small active queue in `NEXT_ACTIONS.md`
- roadmap items in `BACKLOG.md`
- completed history in `WORKLOG.md`
- proof artifacts in `docs/EVIDENCE_LOG.md`
- a bootstrap quality rubric in `docs/BOOTSTRAP_QUALITY.md`
- project-specific adapter values in `PROJECT_ADAPTER.yaml`
- optional prompts in `prompts/`
- optional fixtures in `fixtures/`
- GitHub automation in `.github/`

The template supports two modes:

- `bootstrap` for discovery and baseline creation
- `operating` for steady-state delivery

Use this copy as the reusable version of the workflow. Attach project-specific code and adapters only when you start a new implementation.

## One-command initialization

Initialize a new repo copy with:

```bash
python scripts/init_template.py --name "Your Project Name"
```

This writes the core truth files, sets `repo_mode: bootstrap`, and prints the
next exact steps.

## Public-safe minimal mode

If you want the smallest public version:

```bash
python scripts/init_template.py --name "Your Project Name" --minimal
```

Minimal mode keeps the core workflow files and removes optional examples such
as `fixtures/` and bootstrap demo material.

## Public cleanup

For a copied repo that you want to publish:

1. Rename placeholder project values.
2. Optionally remove `fixtures/` and other example docs.
3. Set `repo_mode: bootstrap`.
4. Re-run the validation script.
