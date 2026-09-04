# ProjectState Template

ProjectState is a small, repo-based workflow for keeping coding agents aligned
with a real product outcome.

Current template version: `projectstate-template-v6`

The default is deliberately narrow: one human-owned project definition, one
current slice, one primary user journey, and one bounded evidence summary. A
failed user journey always outranks passing secondary checks.

## Start

Create a new project:

```bash
python3 scripts/init_template.py new --name "Your Project" --target ../your-project
```

Adopt an existing repository without replacing its README:

```bash
python3 scripts/init_template.py adopt --name "Your Project" --target ../your-project --dry-run
python3 scripts/init_template.py adopt --name "Your Project" --target ../your-project
```

Both commands use the `core` profile unless you explicitly choose another one.

## The core

| Path | Sole responsibility |
| --- | --- |
| `PROJECT.md` | Human-owned user, outcome, scope, non-goals, and durable constraints |
| `STATE.yaml` | One current slice, its acceptance, journey, blockers, risks, and exact next action |
| `AGENTS.md` | Authority boundaries, workflow, stop-lines, and closure rules |
| `evidence/<slice-id>/summary.md` | Commands, environment, results, artifacts, and unresolved limitations |

The generated core also contains `scripts/projectstate_gate.py`, a small
dependency-free checker. It validates the four artifacts and makes the primary
journey the closure decision. `README.md` remains product documentation, not a
second state surface.

The first gate run is expected to fail. A scaffold cannot honestly know the
project's user, outcome, or real journey:

```bash
python3 scripts/projectstate_gate.py
```

Confirm `PROJECT.md`, replace the placeholders in `STATE.yaml`, run the real
journey yourself, record the result, and rerun the gate.

## What “green” means

- `implemented`: the change exists.
- `validated`: the named primary journey passed in the named environment.
- remote/CI/deployed: separately proven only when acceptance crosses that boundary.
- `accepted`: the human accepted the product result.

Unit tests, repository validators, hashes, clean Git status, or complete metadata
cannot turn a failed, blocked, or unrun primary journey green. Secondary checks
may add blockers; they never reverse the primary result.

The gate reads recorded state and evidence. It never executes a command merely
because repository text contains one.

## Human-owned governance

The human owns the project outcome, non-goals, acceptance criteria, governance,
risk exceptions, and product acceptance. Agents may update observed status,
evidence, blockers, risks, and the next action. They may propose a governance
change, but cannot approve or apply one simply to make their own work pass.

This deliberately removes companion control commits, mutable commit-head
bindings, line budgets, correction counters, and runtime dependence on workflow
files from the default model.

## Two-strike simplification

After two evidenced failures at the same delivery boundary, stop extending the
mechanism. Record:

- the assumption being reconsidered;
- one moving part removed or bypassed;
- the smallest real journey to rerun.

The outcome gate blocks further closure until that review exists. This is based
on two concrete failure records, not a general-purpose correction counter.

## Risk handling

The core fails closed for unresolved data-loss, destructive-operation,
privilege-escalation, secrets/private-data exposure, and permission-boundary
risk. Critical or high externally reachable vulnerabilities also block.

Other findings are assessed by severity, exposure, consequence, and affected
environment. A vulnerability confined to build tooling or a demonstrably
unreachable component is recorded with an owner and decision; it does not
automatically outweigh a working product journey. Temporary acceptance needs a
named human approver, rationale, and unexpired date.

## Profiles

### `core` — default

Use for ordinary product work. It installs the four canonical artifacts and the
outcome gate. Backlogs, worklogs, ADRs, release ledgers, multi-agent matrices,
and compliance records are optional project choices.

```bash
python3 scripts/init_template.py new --name "Your Project" --profile core
```

### `hardened` — explicit opt-in

Use only when actual exposure, regulation, or delivery obligations justify the
additional policy. It adds `HARDENED_POLICY.md`; hardened checks may add blockers
but cannot override the primary journey.

```bash
python3 scripts/init_template.py new --name "Your Project" --profile hardened
```

### v5 compatibility profiles

`minimal`, `solo`, `team`, and `regulated` remain explicitly selectable during
migration. They preserve the earlier multi-file and remote-closure workflows for
existing consumers. They are not recommended for new projects and are never
selected implicitly.

## Runtime independence

ProjectState coordinates work only. Product code must not import, parse, or
require `PROJECT.md`, `STATE.yaml`, `AGENTS.md`, `evidence/`, or its helper script
to start or run. Deleting the coordination layer must not break the application.

## Optional material

Add these only when the project needs them:

- `BACKLOG.md` for a real multi-slice roadmap;
- ADRs for durable architectural decisions;
- threat models for meaningful attack surfaces;
- remote CI/review proof when delivery is in scope;
- signing, audit retention, or compliance evidence when obligations require it;
- multi-agent ownership rules when agents actually run concurrently.

The initializer refuses automatic optional asset-set expansion for the v6
profiles; add justified project-specific tooling in a separately reviewed change.

Git history is the default work history. Do not duplicate it into a mandatory
workflow ledger.

## Maintainer notes

The design decision and migration boundary are recorded in
`docs/adr/0003-outcome-first-core.md`. The template repository retains the v5
implementation and historical files as compatibility material, but its current
authority is `AGENTS.md`, `PROJECT.md`, and `STATE.yaml`.

Run the focused core journey:

```bash
python3 scripts/test_outcome_core.py
```

Also run relevant legacy compatibility tests before publishing a migration. A
local pass is not remote delivery, CI verification, release, or human acceptance.
