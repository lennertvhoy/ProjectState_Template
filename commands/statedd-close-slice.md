---
command: "statedd-close-slice"
description: "Execute the close-slice skill: run quality gates, update state, freeze acceptance, verify remote truth"
---

# /statedd-close-slice — Close Implementation Slice

**When to use:** After implementation is complete, before declaring a slice closure-grade.

**Triggers:**
- Human types `/statedd-close-slice`
- CTO handoff requests slice closure
- Quality freeze initiated

**Procedure (delegates to `skills/close-slice/SKILL.md`):**
1. Run `skills/quality-gate/SKILL.md` — full quality gate pipeline
2. Run `scripts/statedd_remote_truth_check.py` — **Remote Truth Gate** (mandatory)
3. Run `scripts/statedd_closure_check.py` — final closure validation
4. If all gates pass:
   - Update `PROJECT_STATE.yaml` with slice completion
   - Update `BACKLOG.md` — mark slice done
   - Append to `WORKLOG.md` — slice summary
   - Update `docs/ACCEPTANCE_FREEZES.md` if user-facing
   - Run `scripts/statedd_handoff.py` for final handoff
5. If any gate fails:
   - Report specific failure
   - Do not close slice
   - Return to implementation

**Required evidence:**
- All quality gate outputs (exit 0)
- Remote truth check output (exit 0, closure label ≥ `pushed`)
- Closure check output (exit 0, closure-grade)
- Updated state files
- Acceptance freeze entry (if user-facing)
- Handoff text for CTO with explicit closure label

**Truth Boundary Verification (mandatory before closure):**
- Local commit truth → Remote branch truth: `git ls-remote origin <branch>` matches HEAD
- Local files → Tracked: `git ls-files <claimed_deliverables>` all present
- Remote branch truth → GitHub main truth: `git ls-remote origin HEAD` accessible
- GitHub main truth → CI truth: CI pipeline passes (future)
- CI truth → User-accepted truth: CTO sign-off on handoff

**Failure cases:**
- Quality gate fails: fix code/tests, re-run gate
- Remote truth check fails: push commits, track files, verify remote
- Closure check fails: address specific failure (runtime proof, evidence, etc.)
- State update fails: fix YAML/schemas
- Acceptance freeze missing: add entry for user-facing changes
- Handoff generation fails: check handoff script

**Exit criteria:** All gates pass, remote truth verified, state updated, handoff ready with explicit closure label (`pushed` / `GitHub-verified` / `CI-verified`).