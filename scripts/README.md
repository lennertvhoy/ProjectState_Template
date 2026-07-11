# StateDD Executable Controls

Read `AGENTS.md` and follow its declared read order before using these tools.
This page is orientation only; executable help, profile manifests, tests, and
the quality gate are the authority. It intentionally does not maintain a second
manual script catalog.

## Common path

```bash
python3 scripts/statedd_git_safety_check.py --mode normal_branch
python3 scripts/statedd_quality_gate.py --gate-level 2 --verbose
python3 scripts/statedd_handoff.py
```

Use `python3 scripts/<tool>.py --help` for the active interface. Run
`python3 -m pytest scripts/ -q` for template-maintenance regressions. The root
development contract is in `pyproject.toml` and `requirements-dev.txt`; those
files are not copied into downstream profiles.

All nonzero gate results are meaningful. A failed safety operation latches
managed mutation read-only. No tool repairs Git permissions or force-cleans
affected state. Remote mutation is a separate explicit authorization boundary.
