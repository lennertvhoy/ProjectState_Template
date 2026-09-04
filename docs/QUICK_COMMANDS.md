# ProjectState quick commands

## Create or adopt

```bash
# Default outcome-first core
python3 scripts/init_template.py new --name "My Project" --target ./my-project

# Preview and adopt without replacing the product README
python3 scripts/init_template.py adopt --name "My Project" --target ./existing --dry-run
python3 scripts/init_template.py adopt --name "My Project" --target ./existing

# Explicit hardened overlay
python3 scripts/init_template.py new --name "My Project" --profile hardened --target ./my-project
```

## Validate the outcome

Run the real primary journey named in `STATE.yaml`, record its result in the
slice evidence summary, then run:

```bash
python3 scripts/projectstate_gate.py
```

The scaffold initially returns `OUTCOME NOT VALIDATED`. Do not replace the real
journey with the gate command itself.

## Migrate a v5 project

Generate a temporary core and transfer only current project truth:

```bash
python3 scripts/init_template.py new --name "My Project" --profile core   --target /tmp/my-projectstate-core --no-init-git
```

See `docs/UPGRADING.md`. The existing `projectstate_upgrade.py` refreshes
locked v5 assets only; it does not perform the semantic core migration.

## Compatibility profiles

These are opt-in during migration:

```bash
python3 scripts/init_template.py new --name "My Project" --profile minimal
python3 scripts/init_template.py new --name "My Project" --profile solo
python3 scripts/init_template.py new --name "My Project" --profile team
python3 scripts/init_template.py new --name "My Project" --profile regulated
```

Their legacy quality, evidence, and remote-closure commands remain documented in
the generated compatibility profile. They are not part of the default core.
