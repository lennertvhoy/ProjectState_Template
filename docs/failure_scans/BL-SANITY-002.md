# Failure Scan: BL-SANITY-002 Template Logic Hole Repair

**Date:** 2026-07-07
**Backlog item:** [BL-SANITY-002]
**Author:** coding agent
**Severity:** P0
**Execution mode impact:** template-maintenance

## What Happened Or Could Happen

An ultra-critical sanity check of the ProjectState template repository found that several
closure-grade gates can pass while their underlying invariants are violated:

- `projectstate_audit.py` accepts an evidence README that records a stale HEAD.
- `projectstate_audit.py` falls back to the most recent commit's file list when the
  worktree is clean, so user-facing/schema/browser checks can evaluate the wrong files.
- `projectstate_handoff.py` reports `local-only files claimed: no` when no upstream is
  configured, even if nothing has ever been pushed.
- `projectstate_doctor.py` counts active NEXT_ACTIONS headings as "open blockers".
- `projectstate_runtime_proof.py` produces a `runtime_identity.json` artifact that
  `projectstate_runtime_truth_check.py` and `projectstate_closure_check.py` cannot consume.
- `projectstate_worktree_guard.py` permits a slice to start when dirty files are
  classified `unknown_do_not_touch`, and it labels any tracked branch as shared/default.
- `init_template.py` `new` mode can overwrite the template root's own truth files.
- `projectstate_upgrade.py` copies files without symlink/traversal guards and always
  reports `dry_run: true` in its JSON report.
- `projectstate_browser_verify.py` resolves artifact paths relative to the evidence
  directory without preventing `../../../etc/passwd` traversal.
- `projectstate_remote_closure_finalizer.py` runs `gh` from the process cwd (not the repo)
  and ignores an explicit `--github-token` when `gh` is installed.
- `projectstate_post_merge_verify.py` references an undeclared `$sha` GraphQL variable
  and checks merge ancestry against a remote SHA that may not be fetched locally.
- `projectstate_probe_guidance.py` writes files directly into the repo and leaves them
  there.

## How The User Or Operator Would Notice

- A downstream project receives a template that falsely claims closure-grade status.
- A coding agent starts a slice on dirty files that should never be touched.
- A generated repo is initialized by destroying the template root.
- A remote closure handoff queries or authenticates against the wrong GitHub repo.
- Runtime-identity checks fail for artifacts produced by the canonical helper.

## Likely Adjacent Failures

- Fixing one gate without updating its tests leaves the false pass/fail hidden.
- Tightening the audit may cause existing evidence folders to fail until they are
  regenerated or annotated with proof/final head markers.
- Adding symlink guards to `init_template.py` may break legitimate symlink-based
  workflows if the guard is too broad.

## Previous Tests That Might Miss This

- `test_post_merge_verify.py` only tests `--help` and missing `--pr-number`.
- `test_upgrade.py` dry-run safety test only checks static header strings.
- `test_init_template.py` does not attempt to initialize into the template root.
- `test_worktree_guard.py` does not test `--mode closure` success or the
  `unknown_do_not_touch` classification.
- Existing schema tests do not exercise empty `claims`/`artifacts` under a
  `"complete"` manifest or a `custom` browser provider missing `tool`/`command`.

## Global Invariant Needed

- Closure-grade means in-repo evidence, local HEAD, pushed branch, PR head, PR body,
  CI status, and merge state all agree; partial matches are not enough.
- Non-trivial slices start only from a classified, non-destructive worktree state.
- File-system helpers must not follow symlinks or traverse outside their target root.
- Producers and consumers of canonical artifacts must agree on the schema defined in
  `schemas/<artifact>.schema.json`.

## Adversarial Case

- Input/event: A malicious or misconfigured `browser_verification.json` references
  `path: "../../../etc/passwd"`; an agent runs
  `projectstate_browser_verify.py check <evidence> --strict`.
- Expected protected behavior: The verifier rejects the out-of-bounds path and exits
  non-zero without reading the file.
- Evidence required: Regression test and, if possible, an adversarial fixture under
  `fixtures/schema_validation/`.

## Runtime Or Live Proof Required

- Required: no
- Why: This is template-maintenance work on scripts and contracts; no application
  runtime exists for the template root.
- Artifact: not applicable

## Post-Deploy Watch Required

- Required: yes
- Duration or trigger: Until BL-SANITY-002 closes and the full gate suite passes on
  the final commit.
- Artifact: `docs/EVIDENCE_LOG.md` entry for BL-SANITY-002.

## Closure Blockers

- All ProjectState gates and regression tests must pass.
- `projectstate_audit.py --strict` must fail stale HEAD evidence and mismatching file sets.
- `projectstate_worktree_guard.py --mode start-slice` must reject `unknown_do_not_touch`
  classifications and must not label ordinary feature branches as shared/default.
- `projectstate_runtime_truth_check.py` and `projectstate_closure_check.py` must accept a
  `runtime_identity.json` produced by `projectstate_runtime_proof.py`.
- `init_template.py new --target <template-root>` must be refused.
- `projectstate_upgrade.py` must guard symlinks and report the actual `dry_run` value.
- `projectstate_browser_verify.py` must reject path traversal.
- `projectstate_remote_closure_finalizer.py` must run `gh` from `self.root` and honor
  `--github-token`.
- `projectstate_post_merge_verify.py` must declare `$sha` and fetch the remote default
  branch head before ancestry checks.

## Mitigations

| Failure mode | Detection | Prevention | Rollback | Evidence needed |
|---|---|---|---|---|
| Stale HEAD passes audit | audit --strict + regression test | require exact HEAD or proof/final markers | revert audit.py change | test_audit_head_mismatch_fails |
| Wrong changed-file set | changed_files_in_slice tests | use merge-base with default branch, not last commit | revert changed_files_in_slice | test_changed_files_uses_merge_base |
| local-only falsely 'no' | handoff tests | treat 'not proven' as unknown/local-only | revert handoff.py line | test_no_upstream_claims_local_only |
| Doctor counts active work as blockers | doctor output | read PROJECT_STATE closure_blockers/active_problems | revert doctor.py | test_doctor_blockers_match_state |
| Runtime identity schema mismatch | runtime_truth tests | align consumers with canonical schema | revert consumer changes | test_runtime_truth_accepts_canonical_schema |
| Worktree guard allows do_not_touch | worktree guard tests | reject any 'do_not_touch' classification | revert guard change | test_unknown_do_not_touch_blocks_start |
| init overwrites template root | init tests | refuse target == template_root | revert init.py guard | test_new_rejects_template_root |
| Upgrade symlink traversal | upgrade tests | reject symlink components in copy | revert upgrade.py | test_upgrade_rejects_symlink_source |
| Browser verify path traversal | browser tests | resolve and check path is inside evidence dir | revert browser.py | test_browser_verify_rejects_path_traversal |
| Remote closure cwd/token bugs | remote closure tests | run gh from repo root; pass token via env | revert finalizer changes | test_finalizer_uses_repo_root_and_token |
| Post-merge $sha/merge-base bugs | post-merge tests | declare variable; fetch remote head | revert verifier changes | test_post_merge_query_and_ancestry |
| Probe pollution | probe tests | run probes in temp dirs; clean up | revert probe guidance | test_probe_runs_in_temp_dir |
