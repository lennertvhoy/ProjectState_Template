---
command: "statedd-remote-closure"
description: "Run the remote CI/CD closure finalizer"
---

# /statedd-remote-closure — Remote Closure Finalizer

**When to use:** After pushing a slice and before calling it closure-grade.

**Triggers:**
- Human types `/statedd-remote-closure`
- Close-slice skill reaches the remote closure step
- Release gate requires remote verification

**Procedure:**
1. Confirm worktree is clean (`git status --short`)
2. Confirm current branch is pushed to origin (`git ls-remote origin <branch>`)
3. Find the open PR for the current branch (or use `--pr-number`)
4. Verify PR head SHA equals local HEAD
5. Verify PR body references current HEAD or uses an explicit Proof head/Final PR head split
6. Verify GitHub Actions checks completed successfully for current HEAD
7. Verify `mergeStateStatus` is CLEAN, HAS_HOOKS, or MERGED
8. Verify in-repo evidence references current HEAD or uses an explicit proof_head/final_head split
9. Print and optionally write a JSON handoff artifact

**Required inputs:**
- Clean git worktree
- Current branch pushed to origin
- Open PR for the branch
- `GH_TOKEN` or `GITHUB_TOKEN` environment variable (or authenticated `gh` CLI)

**Failure cases:**
- Dirty worktree: commit or stash changes, re-run
- Branch not pushed: push, re-run
- No PR for branch: open a PR, re-run
- PR head drift: pull/push to align heads, re-run
- Stale PR body: edit PR body to reference current HEAD, re-run
- CI pending/failing: wait for CI or fix failures, re-push, re-run
- mergeStateStatus blocked: resolve branch protection or rebase, re-run
- Evidence references stale head: update evidence or add explicit proof_head/final_head split

**Exit criteria:** `statedd_remote_closure_finalizer.py` exits 0 with a `CI verified` or `merged` closure label.

**Command:**
```bash
python scripts/statedd_remote_closure_finalizer.py --verbose
```
