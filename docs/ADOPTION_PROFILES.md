# StateDD Adoption Profiles

Profiles let you initialize or adopt a repo with a StateDD footprint matched to
the project's needs. They do not change the core StateDD rules; they change which
default assets are included and how strongly the generated docs emphasize certain
practices.

## Available Profiles

### `minimal`

Use when you want the smallest useful StateDD footprint.

- Core state files, hygiene checks, audit, doctor, and schema validation remain.
- Optional fixtures, `docs/BOOTSTRAP_QUALITY.md`, and `docs/WORKFLOW_FOR_BEGINNERS.md`
  are removed.
- The bootstrap gate remains intact; unknowns must still be explicit.
- Does **not** relax evidence or runtime-proof requirements when a claim needs them.

### `solo`

Default profile for a single developer.

- Full template surface including evidence README template, runtime proof helper,
  schema validation, handoff helpers, and beginner docs.
- Standard handoff and evidence defaults.
- Good balance of discipline and low overhead.

### `team`

Use when multiple people will read handoffs, review evidence, or open pull requests.

- Same assets as `solo`.
- Generated `AGENTS.md` emphasizes slice contracts, claim ledgers, and CTO review.
- Encourages stricter evidence and audit hygiene by default.

### `regulated`

Use when acceptance criteria, audit trails, or runtime proof are non-negotiable.

- Same assets as `solo` and `team`.
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
