# ADR-0002: Confirm Delivery Policy Once and Keep Post-Merge Identities External

**Status:** accepted
**Date:** 2026-07-12
**Author:** human / integration coding agent

## Context

StateDD automated implementation, validation, push, PR preparation, and exact-head
remote closure but treated merge as a universal human boundary. That made the
human a routine release operator and encouraged follow-up PRs whose only purpose
was to copy provider-created merge/main identities into tracked state. A squash
merge commit cannot be known when the PR branch is committed, so requiring that
identity in tracked proof creates an unsatisfiable future-SHA dependency.

## Decision

Every downstream project confirms exactly one delivery-policy merge mode during
structured bootstrap:

- `agent_after_green` is the recommended canonical URL/team mode. The integration
  coding agent owns the exact verified PR-head merge, direct default-branch CI,
  post-merge equivalence, external handoff, and verified cleanup.
- `human_merge` remains available when regulation, organizational policy, or risk
  preference requires a person to perform the merge transition.

The confirmed mode is project truth and cannot be changed silently by an agent.
Force-push and shared-history rewrite remain outside routine authority. Final
product acceptance remains human regardless of delivery mode. CI-unavailable
merge requires a separate explicit override and is never inferred from local proof.

One typed, idempotent finish state machine owns the remote transition:

```text
LOCAL_VALIDATED → PUSHED → PR_OPEN → PR_READY
→ REMOTE_CLOSURE_VERIFIED → MERGED → MAIN_CI_VERIFIED → HANDOFF_COMPLETE
```

Tracked evidence binds the proof commit/tree, tests, claims, source hashes, final
PR head, and evidence folder. The provider supplies the resulting merge commit
and default-branch head. An external post-merge handoff records those identities,
the direct main-CI run, verification result, branch deletion, and isolation release.

The final PR carries the proposed stable default-branch state. It is not canonical
while it remains on the feature branch; it becomes canonical only if the finish
state machine successfully merges that exact head. If closure fails, the old main
state remains authoritative and recovery state is retained. This removes the need
for a post-merge metadata PR without asking tracked files to predict the future.

## Consequences

- Humans confirm policy once and are not routine Git operators under the
  recommended mode.
- Concurrent pushes, requested changes, unresolved current review threads, dirty
  merge state, or pending/failed CI block merge at a final remote re-query.
- Reruns observe provider truth and resume; an already merged PR is verified rather
  than merged again.
- Branch deletion and isolation release happen only after direct default-branch CI
  and content-preserving post-merge verification pass.
- Canonical live state stays stable and semantic; volatile provider identities live
  in GitHub, immutable evidence, history, or the external handoff.

## Alternatives Considered

- Universal human merge: rejected as the default because it breaks the intended
  coding-agent-owned golden path; retained as an explicit policy mode.
- Repository auto-merge as the only mechanism: rejected because it may be disabled
  and does not replace an expected-head constraint or post-merge verification.
- Tracked post-merge SHA repair: rejected because it creates a metadata-PR loop and
  cannot predict a provider-created squash identity.
- Local-test override for unavailable CI: rejected; only a separate explicit human
  override may cross that boundary, with the result labeled honestly.

## Related

- Backlog item: [BL-GOLDEN-PATH-CLOSURE-001]
- Failure scan: `docs/failure_scans/BL-GOLDEN-PATH-CLOSURE-001.md`
- Finish command: `scripts/statedd_finish_slice.py`
- Pre-merge finalizer: `scripts/statedd_remote_closure_finalizer.py`
- Post-merge verifier: `scripts/statedd_post_merge_verify.py`
