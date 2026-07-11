# StateDD Adoption Profiles

Profiles let you initialize or adopt a repo with a StateDD footprint matched to
the project's needs. They do not change the core StateDD rules; they change which
default assets are included and how strongly the generated docs emphasize certain
practices.

StateDD is agent-operated: humans choose intent, profiles, and permissions;
coding agents read `AGENTS.md`, use the executable controls, maintain truth, and
produce the handoff. Read `AGENTS.md` before using this reference page.

## Which profile should I choose?

**Default recommendation: `solo`.**

Use `minimal` if:

- you want the smallest useful StateDD footprint
- you want core state/schema/hygiene/efficiency/quality gates without optional
  runtime, audit, evidence-pack, team, or review helpers

Use `solo` if:

- you are one developer or one human + one coding agent
- you are unsure which profile to choose
- you want runtime/evidence/closure helpers without template-maintenance payload

Use `team` if:

- multiple humans or agents will review handoffs and evidence
- pull requests and shared review are part of your workflow

Use `regulated` if:

- acceptance, audit trail, runtime proof, and redaction records matter
- you need explicit acceptance freezes and override records by default

## Available Profiles

### `minimal`

Use when you want the smallest useful StateDD footprint.

- Core state files plus schema, hygiene, efficiency, and quality gates remain.
- Runtime, audit, evidence-pack, browser, team, and deep-reference helpers are
  omitted until the project needs them.
- The bootstrap gate remains intact; unknowns must still be explicit.
- Does **not** relax evidence or runtime-proof requirements when a claim needs them.

### `solo`

Default profile for a single developer.

- Curated downstream surface including runtime proof, evidence, browser, audit,
  closure, schema, and handoff helpers.
- Standard handoff and evidence defaults.
- Good balance of discipline and low overhead.

### `team`

Use when multiple people will read handoffs, review evidence, or open pull requests.

- `solo` assets plus full-clone-default agent isolation, explicit-opt-in linked
  worktrees, remote closure, CTO/review prompts, upgrade guidance, and ADR templates.
- Generated `AGENTS.md` emphasizes slice contracts, claim ledgers, and CTO review.
- Encourages stricter evidence and audit hygiene by default.
- Containers and independent agents use separate clones/object databases; linked
  worktrees are limited to a proven same-identity trusted local machine.

### `regulated`

Use when acceptance criteria, audit trails, or runtime proof are non-negotiable.

- `team` assets plus post-merge verification.
- Generated `AGENTS.md` explicitly requires:
  - runtime identity proof for runtime/user-facing acceptance claims,
  - evidence-pack manifests with redaction status,
  - acceptance freeze records for accepted milestones,
  - explicit human override records when defaults are overridden.
- Do not claim closure-grade in this profile without satisfying those defaults.

## Usage

```bash
python3 scripts/init_template.py new --name "Your Project" --profile minimal
python3 scripts/init_template.py new --name "Your Project" --profile solo
python3 scripts/init_template.py new --name "Your Project" --profile team
python3 scripts/init_template.py new --name "Your Project" --profile regulated

python3 scripts/init_template.py adopt --name "Your Project" --profile team
```

The `--minimal` flag is a legacy alias for `--profile minimal`.

Every profile is generated from an explicit allowlist and records its installed
files in `STATEDD_ASSETS.json`. No profile receives template-maintenance tests,
fixtures, historical evidence, incident records, changelog, or release history.
CI runs each generated profile's own quality gate. `EFFICIENCY_BUDGET.yaml`
enforces startup files/bytes/estimated tokens and managed footprint files/bytes.
Profile regressions use identical project names and equal-length target paths and
require `minimal` to remain the smallest mandatory startup payload. The
authoritative slice gate is `scripts/statedd_quality_gate.py --gate-level 2`;
template-only development dependencies and Ruff configuration are not copied to
downstream profiles.
