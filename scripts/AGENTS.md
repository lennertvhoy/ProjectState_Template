---
scope: "scripts"
purpose: "Agent behavior for StateDD executable scripts"
---
# Scripts Agent Instructions

## Scope
This AGENTS.md applies to all work in `scripts/`. It defines how agents interact with StateDD executable tools.

## Script Catalog (Authoritative)

| Script | Purpose | Exit Codes |
|--------|---------|------------|
| `statedd_quality_gate.py` | Post-slice quality gate (tests, static analysis, state, evidence) | 0=pass, 1=fail, 2=error |
| `statedd_instruction_lint.py` | Lint AGENTS.md/skill/command files for config smells | 0=clean, 1=smells, 2=error |
| `statedd_bad_event_ingest.py` | Ingest bad events into incidents/failure-scans | 0=ok, 1=failed, 2=error |
| `statedd_probe_guidance.py` | Probe agent guidance with synthetic tasks | 0=pass, 1=gaps, 2=error |
| `statedd_closure_check.py` | Verify closure-grade criteria met | 0=closure-grade, 1=not, 2=error |
| `statedd_runtime_truth_check.py` | Verify runtime identity matches recorded truth | 0=match, 1=mismatch, 2=error |
| `statedd_evidence_type_check.py` | Verify evidence type matches change type | 0=match, 1=mismatch, 2=error |
| `statedd_validate_schema.py` | Validate YAML/JSON against schemas | 0=valid, 1=invalid, 2=error |
| `statedd_audit.py` | Machine-checkable closure audit | 0=pass, 1=fail, 2=error |
| `statedd_handoff.py` | Generate session handoff snapshot | 0=ok, 1=incomplete, 2=error |
| `statedd_runtime_proof.py` | Capture runtime identity proof | 0=captured, 1=failed, 2=error |
| `statedd_browser_verify.py` | Browser verification (Kimi/Playwright) | 0=verified, 1=failed, 2=error |
| `statedd_doctor.py` | Fast health summary | 0=healthy, 1=issues, 2=error |
| `statedd_version_check.py` | Version compatibility check | 0=ok, 1=mismatch, 2=error |
| `statedd_upgrade.py` | Upgrade downstream repos | 0=ok, 1=failed, 2=error |
| `statedd_bootstrap_wizard.py` | Interactive bootstrap | 0=ok, 1=failed, 2=error |
| `statedd_evidence_pack.py` | Package evidence bundle | 0=ok, 1=failed, 2=error |
| `statedd_remote_closure_finalizer.py` | Final remote CI/CD closure gate | 0=verified, 1=not closure-grade, 2=error |
| `check_state_docs.py` | Doc hygiene & bootstrap gate | 0=clean, 1=dirty, 2=error |
| `init_template.py` | Initialize downstream repo from template | 0=ok, 1=failed, 2=error |

## Agent Rules for Scripts

1. **Prefer skills/commands over ad-hoc script calls** — Use `/skill-name` or `/statedd-*` commands; they wrap scripts with context
2. **Never modify scripts without updating this catalog** — Keep catalog in sync
3. **Run quality gates after any script change** — `python scripts/statedd_quality_gate.py`
4. **Lint instructions after any AGENTS.md/skill/command change** — `python scripts/statedd_instruction_lint.py`
5. **Test scripts with `python -m pytest scripts/test_*.py`** before committing
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