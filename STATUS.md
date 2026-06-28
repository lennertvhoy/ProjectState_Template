# StateDD Template Status

**Updated At:** 2026-06-28 00:00 +02:00
**Execution Mode:** template-maintenance
**Project State:** template_maintenance_active
**Public URL:** https://github.com/lennertvhoy/StateDD_Template/releases/tag/v4

## Snapshot

- Repo identifies as `repo_role: template_repository` with `statedd_mode: template-maintenance` and spec version `statedd-template-v5`; generated/adopted downstream repos still start as `repo_role: downstream_project` with `statedd_mode: bootstrap`.
- `statedd-template-v5` is published as GitHub release `v5`; no further release steps are pending.
- BL-007 public usability polish, BL-BROWSER-001 provider-agnostic browser verification, and BL-QUALITY-001 quality firewall hardening are accepted as template capabilities.
- StateDD requires browser-verification evidence for user-facing closure, not a specific browser automation provider; Kimi WebBridge is preferred when available, but Playwright, agent-native browser tools, existing E2E tests, manual screenshots, or custom tooling are accepted when evidence is durable and honestly scoped.
- StateDD now treats handoffs as claims, separates repo truth from runtime truth, and requires downstream projects to define quality gates for product behavior, runtime truth, adversarial checks, known bad events, and post-deploy proof where applicable.
- Runtime proof, schema-backed validation, evidence pack manifests, downstream upgrade tooling, adoption profiles, the bootstrap wizard, provider-agnostic browser verification, and the canonical schema/prompt loop example remain template capabilities.
- BL-BROWSER-002 concrete provider integration remains open and is explicitly not a release blocker; last recorded clean release state was `main` at `2a9afd4`, and current worktree must be rechecked before closure.

## Product Truth

- This repository is a template, not an application product runtime.
- Product-facing template truth is the generated/adopted workflow contract and docs.

## Runtime Truth

- No application runtime exists for the template root.
- Runtime truth requirements apply to downstream projects and generated/adopted repos.

## Current Quality Gate

- Template quality gate: passing for BL-QUALITY-001 docs/schema/initializer/upgrade checks.
- Downstream quality firewall contract: implemented as generic reusable template guidance.

## Open P0/P1 Failures

- None known in the template root.

## What Is Not Proven

- Downstream repos have not yet upgraded to the quality firewall contract.

## Immediate Priorities

1. Integrate a concrete browser automation provider only when one is available and permitted, without making it a hard dependency.

## Active Blockers

- None.

## Notes

- Keep `STATUS.md` short.
- Use `PROJECT_STATE.yaml` for structured truth.
- Use `BACKLOG.md` backlog IDs inside `NEXT_ACTIONS.md` when active items are added.
- Prove runtime identity before accepting user-facing behavior.
