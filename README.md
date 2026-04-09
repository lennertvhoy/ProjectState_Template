# Truth-First Project Operating System Template

This repository is a public template for technical projects that want explicit
live state, evidence-backed claims, a short active queue, and clean handoffs.

`README.md` is the complete user guide for using the template. The other files
are the operating system itself.

## What You Get

- `AGENTS.md`: operating contract and mode rules
- `STATUS.md`: short human snapshot of current truth
- `PROJECT_STATE.yaml`: structured machine-checkable current truth
- `PROJECT_DNA.yaml`: stable architecture and governance contract
- `PROJECT_ADAPTER.yaml`: project-specific vocabulary and runtime adapter
- `NEXT_ACTIONS.md`: active queue only
- `BACKLOG.md`: medium-term roadmap
- `WORKLOG.md`: append-only history
- `docs/EVIDENCE_LOG.md`: proof ledger for user-facing claims
- `scripts/init_template.py`: stamps a copied repo or creates a fresh initialized copy
- `scripts/check_state_docs.py`: validates the live-state document boundaries
- `prompts/`: optional prompt helpers for bootstrap, CTO review, and coding-agent delegation
- `fixtures/`: example bootstrap/operating snapshots and an adversarial inherited repo
- `.github/`: issue templates, PR template, and CI validation workflow

## Workflow Modes

- `bootstrap`: use this when the repo is new, inherited, or unclear. The goal is to establish truthful baseline state.
- `operating`: use this after bootstrap is complete. The project runs steady-state with short queues, explicit verification, and clean handoffs.

This template repository is itself maintained in `operating` mode.
Repos created from the template should start in `bootstrap`.

## Quick Start

1. Create a new repo from this template, or clone/copy it locally.
2. Initialize the copy with your project name.
3. Read the files in the required order.
4. Bootstrap the real project truth.
5. Run the validation script before handoff or publishing changes.

Initialize the current copy in place:

```bash
python3 scripts/init_template.py --name "Your Project Name"
```

Initialize a fresh directory directly from this checkout:

```bash
python3 scripts/init_template.py --name "Your Project Name" --target ../your-project
```

Create the smallest public-ready variant:

```bash
python3 scripts/init_template.py --name "Your Project Name" --minimal
```

`--minimal` removes `fixtures/` and `docs/BOOTSTRAP_QUALITY.md` after initialization.

## What The Init Script Does

- copies the template scaffold when `--target` points at a different directory
- stamps the managed state files with your project name
- sets the initialized repo to `repo_mode: bootstrap`
- keeps the README, scripts, prompts, and GitHub automation in place
- prints the next exact steps

If `--target` points at an existing non-empty directory outside the current checkout,
pass `--overwrite` to allow the script to write into it.

## Required Read Order

Start every session by reading:

1. `AGENTS.md`
2. `STATUS.md`
3. `PROJECT_STATE.yaml`
4. `PROJECT_DNA.yaml`
5. `NEXT_ACTIONS.md`

Read `BACKLOG.md` and `WORKLOG.md` when planning or reviewing history.

## Bootstrap Procedure

When a new project starts, do this in order:

1. Investigate the host system and runtime.
2. Investigate the repo structure and actual implementation reality.
3. Ask only the minimum strategic questions needed.
4. Update the state files with observed truth and explicit unknowns.
5. Create the first short active queue in `NEXT_ACTIONS.md`.
6. Record evidence for any user-facing claims in `docs/EVIDENCE_LOG.md`.
7. Flip `repo_mode` to `operating` when baseline truth is actually established.
8. Append the outcome to `WORKLOG.md`.

If something is not proven, label it honestly as `observed`, `unknown`, `reported`,
`assumed`, `blocked`, `stale`, or `invalid`.

## Operating Loop

Once bootstrap is complete:

1. Keep `STATUS.md` short and current.
2. Put structured live truth in `PROJECT_STATE.yaml`.
3. Put stable architecture assumptions in `PROJECT_DNA.yaml`.
4. Keep only open work in `NEXT_ACTIONS.md`.
5. Move completed history to `WORKLOG.md`.
6. Back every user-facing claim with direct evidence.
7. End implementation sessions with a handoff and hygiene check.

## When To Edit Which File

| File | Edit it when |
| --- | --- |
| `AGENTS.md` | the operating contract or repo mode changes |
| `STATUS.md` | the high-level truth snapshot changes |
| `PROJECT_STATE.yaml` | structured current truth changes |
| `PROJECT_DNA.yaml` | stable architecture or governance changes |
| `PROJECT_ADAPTER.yaml` | project vocabulary, runtime defaults, or integration names change |
| `NEXT_ACTIONS.md` | active open work changes |
| `BACKLOG.md` | medium-term priorities change |
| `WORKLOG.md` | a meaningful session completes |
| `docs/EVIDENCE_LOG.md` | you verified a user-facing claim |

## Validation

Run the hygiene check before handoff, PR review, or release:

```bash
python3 scripts/check_state_docs.py
```

You can also validate a different initialized copy or fixture:

```bash
python3 scripts/check_state_docs.py fixtures/bootstrap_dry_run/bootstrap
python3 scripts/check_state_docs.py fixtures/bootstrap_dry_run/operating
python3 scripts/check_state_docs.py fixtures/messy_inherited_repo/bootstrap
```

GitHub Actions runs the same validation on pushes and pull requests. The workflow
also dry-runs the initializer in both normal and `--minimal` modes.

## Repo Layout

- Root: live state, contract, roadmap, and history files
- `docs/`: durable evidence and rubric material
- `scripts/`: initialization and validation helpers
- `prompts/`: optional text prompts for bootstrap, CTO review, and coding-agent delegation
- `fixtures/`: sample outputs for dry runs and inherited-repo edge cases
- `.github/`: issue templates, PR template, and CI workflow

## Publishing A Downstream Project

Before you publish a repo created from this template:

1. Replace the template-level project name and adapter values.
2. Make sure the README reflects the real project once the workflow guide is no longer enough.
3. Remove optional examples with `--minimal` or manually delete `fixtures/` if they do not belong in the public repo.
4. Re-run `python3 scripts/check_state_docs.py`.
5. Make sure user-facing claims in the repo have evidence entries.

## Notes

- This template does not ship an application runtime.
- The design guidance for repo-authored docs lives in `DESIGN.md`.
- The project is released under the MIT license in [`LICENSE`](LICENSE).
