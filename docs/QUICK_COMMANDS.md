# StateSpec Quick Commands

This is a reference page, not a second constitution. Read `AGENTS.md` first and
follow its declared read order and task-scoped controls.

## Initialize or adopt

```bash
python3 scripts/init_template.py new --name "My Project" --profile team
python3 scripts/init_template.py adopt --name "My Project" --profile team --dry-run
python3 scripts/init_template.py adopt --name "My Project" --profile team
```

## Start and validate a slice

```bash
python3 scripts/statedd_git_safety_check.py --mode normal_branch
python3 scripts/statedd_quality_gate.py --gate-level 2 --verbose
python3 scripts/statedd_handoff.py
python3 scripts/check_state_docs.py
```

Use `--mode clone` for an independent agent and use linked `worktree` mode only
with explicit trusted-local, same-identity opt-in. A failed writable safety check
means read-only diagnosis until repair and `--restart-session`.

## Evidence and closure boundaries

```bash
python3 scripts/statedd_validate_schema.py
python3 scripts/statedd_audit.py --strict
python3 scripts/statedd_doctor.py
```

The quality gate is the authoritative local slice gate. Audit and remote closure
checks are separate claims. Local green does not prove remote branch truth, CI,
runtime identity, browser evidence, or human acceptance. Never call a slice
closure-grade without the corresponding independent proof.
