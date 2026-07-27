---
command: "projectstate-remote-closure"
gate_level: 2
evidence_max: 4
cheapest_proof: "Remote closure finalizer exits 0 for the exact pre-merge head"
escalate_when: "Release gate requires level 3 with CI proof"
description: "Verify the exact pre-merge PR candidate before policy-governed merge"
---

# /projectstate-remote-closure — Remote Closure Finalizer

**When to use:** After pushing a slice and before the merge transition. This proves
the exact PR candidate; full `agent_after_green` closure also requires merge,
direct default-branch CI, post-merge verification, and an external handoff.

**Procedure:**
1. Confirm the worktree is clean and the exact branch head is pushed.
2. Verify the PR body uniquely binds the proof head, final PR head, and evidence folder.
3. Verify PR and remote branch heads equal local HEAD.
4. Verify branch-head and merge-candidate CI completed successfully for that head.
5. Verify requested changes, unresolved current review threads, and dirty merge state are absent.
6. Validate the strict tracked evidence bundle.
7. Print and optionally write the pre-merge remote-finalizer receipt.

**Failure cases:**
- Dirty or unpushed branch: restore the clean exact-head boundary, then rerun.
- PR-head drift or stale body: stop; never merge the unexpected head.
- CI pending/failing: wait or fix on the same PR; local tests do not override it.
- Review or merge state blocked: resolve the blocker and re-query remote truth.
- Evidence mismatch: repair the tracked proof binding and obtain new exact-head CI.

**Exit criteria:** `projectstate_remote_closure_finalizer.py` exits 0 for the exact
pre-merge head. This alone does not prove the later merge or default-branch CI.

```bash
python3 scripts/projectstate_remote_closure_finalizer.py \
  --pr-number <pr-number> \
  --evidence-folder <docs/evidence/folder> \
  --verbose
```
