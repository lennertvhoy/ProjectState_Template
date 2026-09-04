# Upgrading to the outcome-first core

Current template version: `projectstate-template-v6`

This is a semantic migration, not a file refresh. The v5 state surfaces may
contain useful project truth, so do not delete them before extracting it.

## Safe migration

1. Create a private migration branch from a clean, current checkout.
2. Read the existing project documents and identify:
   - the primary user and observable outcome;
   - durable scope, non-goals, and constraints;
   - the one slice actually in progress;
   - its acceptance criteria and smallest real journey;
   - open blockers, risks, and the exact next action.
3. Generate a fresh core instance in a temporary directory:

   ```bash
   python3 scripts/init_template.py new --name "Your Project" --profile core --target /tmp/your-projectstate-core --no-init-git
   ```

4. Transfer only the extracted truth into `PROJECT.md`, `STATE.yaml`, and the
   current evidence summary.
5. Run the real primary journey and `python3 scripts/projectstate_gate.py`.
6. Keep old files for review until the new core has been accepted. Remove or
   archive them in one explicit migration change; do not maintain both models as
   live truth.

## Mapping

| v5 material | v6 destination |
| --- | --- |
| product/user/scope across DNA, status, or state | `PROJECT.md` |
| active slice, blockers, risks, next action | `STATE.yaml` |
| current command results and limitations | `evidence/<slice-id>/summary.md` |
| closed worklog entries | Git history; retain separately only if legally needed |
| backlog | optional `BACKLOG.md` if the project genuinely needs one |
| release/remote/compliance controls | explicit `hardened` or project-specific policy |
| control-head bindings, counters, fixed line budgets | no migration; retire them |

Do not translate a green v5 repository gate into a passed primary journey. Rerun
the journey in a representative environment.

## Existing automated upgrader

`scripts/projectstate_upgrade.py` remains a v5 compatibility tool. It can safely
refresh assets inside a locked v5 profile, but it does not perform this semantic
migration and must not claim that it does. The v6 core intentionally has no asset
lock or self-updating governance.

## Compatibility profiles

`minimal`, `solo`, `team`, and `regulated` remain selectable for existing
consumers during the migration window. New projects default to `core`.
Compatibility-profile maintenance does not change the v6 project outcome or
acceptance criteria.

## Truth at handoff

Report local implementation, primary-journey validation, remote branch, CI,
deployment, and human acceptance separately. A local migration can be complete
without being pushed; it must say so.
