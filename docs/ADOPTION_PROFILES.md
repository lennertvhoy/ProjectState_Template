# StateDD Adoption Profiles

Profiles let you initialize or adopt a repo with a StateDD footprint matched to
the project's needs. `profiles/catalog.json` is the machine-readable authority
for dependencies, asset sets, capabilities, validation, and required gate level.
Capability IDs describe the interface a profile intends to expose; they are not
proof by themselves. Resolved validation IDs dispatch executable/presence
contracts in the generated quality gate and are the enforceable capability proof.
Profiles do not change core truth rules.

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

- `solo` assets plus isolated agent worktrees, remote closure, CTO/review prompts,
  upgrade guidance, and ADR templates.
- Generated `AGENTS.md` emphasizes slice contracts, claim ledgers, and CTO review.
- Encourages stricter evidence and audit hygiene by default.

### `regulated`

Use when acceptance criteria, audit trails, or runtime proof are non-negotiable.

- `team` assets plus post-merge verification.
- Generated `AGENTS.md` explicitly requires:
  - runtime identity proof for runtime/user-facing acceptance claims,
  - evidence-pack manifests with redaction status,
  - acceptance freeze records for accepted milestones,
  - explicit human override records when defaults are overridden.
- Do not claim closure-grade in this profile without satisfying those defaults.

### Optional `knowledge_okf` module

OKF knowledge is not part of any ordinary profile. Install it only when the
project needs a contained `knowledge/` bundle for durable domain concepts,
metrics, schema explanations, interfaces, or playbooks:

```bash
python3 scripts/init_template.py new --name "Your Project" --profile team --asset-set knowledge_okf
python3 scripts/init_template.py adopt --name "Your Project" --profile team --asset-set knowledge_okf
```

The module installs the pinned OKF v0.1 validator, StateDD provenance and
staleness contract, and a project-owned `knowledge/index.md` scaffold. It does
not duplicate StateDD operational truth or add knowledge files to `minimal`,
`solo`, or `team` unless explicitly selected.

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
files and lifecycle hashes in `STATEDD_ASSETS.json`. No profile receives template-maintenance tests,
fixtures, historical evidence, incident records, changelog, or release history.
CI runs each generated profile's own quality gate. `EFFICIENCY_BUDGET.yaml`
enforces startup files/bytes/estimated tokens and managed footprint files/bytes.
Reproducible profile and task-context measurements live only in
`docs/metrics/profile_metrics.json`; prose intentionally does not copy their
exact values.
