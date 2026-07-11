---
scope: "scripts"
purpose: "Agent behavior for StateDD executable scripts"
---
# Scripts Agent Instructions

## Scope
This AGENTS.md applies to all work in `scripts/`. It defines how agents interact with StateDD executable tools.

## Authority

The filesystem, each command's `--help`, profile manifests, tests, and
`statedd_quality_gate.py` are the executable authority. Do not maintain a second
hand-written script inventory here or in downstream documentation.

## Agent Rules for Scripts

1. **Prefer skills/commands over ad-hoc script calls** — Use `/skill-name` or `/statedd-*` commands; they wrap scripts with context
2. **Run quality gates after any script change** — `python scripts/statedd_quality_gate.py --gate-level 2`
4. **Lint instructions after any AGENTS.md/skill/command change** — `python scripts/statedd_instruction_lint.py`
5. **Test scripts with `python -m pytest scripts/test_*.py`** before committing; Git safety changes must run `scripts/test_git_safety_check.py`
6. **Scripts are executable gates, not suggestions** — Non-zero exit = block closure

## Script Development Workflow
1. Identify need → add to catalog above
2. Create skill in `skills/` with SKILL.md wrapping the script
3. Create command in `commands/` for slash-invocation
4. Implement script in `scripts/` with proper exit codes
5. Add test in `scripts/test_<name>.py`
6. Run quality gate and instruction lint
7. Update this catalog

## Hygiene
- `scripts/__pycache__/` ignored in `.gitignore`
- Keep script headers: purpose, args, exit codes, example
- No secrets in scripts — use env vars
- Python 3.11+ target; no external deps beyond stdlib + pyyaml

## Human Override
Explicit human direction overrides script gates. Record in handoff.
