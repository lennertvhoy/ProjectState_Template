---
command: "statedd-close-slice"
gate_level: 2
evidence_max: 8
cheapest_proof: "Authoritative local gate plus policy-governed exact-head merge and post-merge verification"
escalate_when: "Release gate requires level 3 with CI proof"
description: "Close a slice through confirmed delivery policy, remote truth, and final handoff"
---

# /statedd-close-slice — Close Implementation Slice

**When to use:** After implementation is complete, before declaring a slice closure-grade.

**Triggers:**
- Human types `/statedd-close-slice`
- CTO handoff requests slice closure
- Quality freeze initiated

**Procedure (delegates to `skills/close-slice/SKILL.md`):**
1. Run `skills/quality-gate/SKILL.md` once through the authoritative quality-gate entrypoint.
2. If the local gate passes:
   - Update `PROJECT_STATE.yaml` to `validated_local_remote_pending` (or an
     equivalent closure-candidate state), never completion
   - Keep the slice active in `BACKLOG.md` until the remote transition completes
   - Append the local validation boundary to `WORKLOG.md` without calling it closed
   - Update `docs/ACCEPTANCE_FREEZES.md` only after actual human acceptance
   - Commit the implementation proof and stable tracked evidence; never predict a
     provider-created merge commit
   - Push and open/update one draft PR with proof head, final PR head, and evidence folder
   - Read the human-confirmed delivery policy; never change its merge mode silently
   - For confirmed `agent_after_green`, run `scripts/statedd_finish_slice.py` with
     the exact expected PR head, policy, evidence folder, squash method, and an
     external handoff path
   - Let that command own PR readiness, exact-head branch and merge-candidate CI,
     review/thread/merge-state checks, remote finalization, merge, direct main CI,
     post-merge verification, cleanup, and verified physical isolation release
   - For `human_merge`, stop after exact-head remote closure and report that the
     configured policy intentionally requires the human merge
   - Keep merge commit, default-branch head, main-CI run, and the closed-world
     release receipt in the external handoff. Do not open a metadata PR to put
     future identities in tracked files.
3. If any local or remote gate fails:
   - Report the exact state-machine transition and observed blocker
   - Retain the branch and isolation state for recovery
   - Resume idempotently after repair; never repeat an existing merge

**Required evidence:**
- All quality gate outputs (exit 0)
- Updated stable state files and strict tracked evidence
- Exact-head remote finalizer output
- External post-merge handoff for `agent_after_green`
- Acceptance freeze entry only when the human accepted a user-facing milestone

**Exit criteria:** Under `agent_after_green`, the local gate, exact-head remote
finalizer, exact expected-head merge, direct main CI, post-merge verifier, cleanup,
and external handoff all pass. Under `human_merge`, the handoff truthfully stops at
the configured manual boundary. Human product acceptance remains separate.

`HANDOFF_COMPLETE` is forbidden unless the release receipt proves the exact
original isolation path is absent. Clean managed clones move to quarantine outside
the project parent; clean opted-in worktrees are removed without force. Dirty or
contradictory state remains active for recovery.

If a clone is explicitly cancelled after a failed preflight, use
`statedd_agent_worktree.py abandon --reason <failed_preflight|superseded|operator_cancelled>`;
it quarantines only a clean managed clone and never claims post-merge validation.
