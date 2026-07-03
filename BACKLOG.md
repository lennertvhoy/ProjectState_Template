# BACKLOG - Strategic Roadmap

**Product:** StateDD_Template
**Execution Mode:** template-maintenance
**Updated At:** 2026-07-03

## Purpose

This backlog tracks medium-term work using stable backlog IDs.
Reference these IDs from `NEXT_ACTIONS.md`.

## NOW

- [BL-WORKFLOW-002] Add worktree isolation and anti-brittleness guardrails so non-trivial coding-agent slices prove source-of-truth state before edits and avoid brittle example-only closure.

## NEXT

- [BL-BROWSER-002] Integrate a concrete browser automation provider using the provider-agnostic contract when a provider is available and permitted.

## CLOSED

- [BL-SANITY-001] StateDD repo coherence and efficiency repair: reconcile PR #2 efficiency layer, add backlog duplicate validation, repair truth files, fix closure evidence, add post-merge verifier, update CI.
- [BL-REMOTE-CLOSURE-001] Add a Remote CI/CD Closure Finalizer that blocks closure until local HEAD, pushed branch, PR head, PR body, evidence, GitHub Actions, and merge state all agree.
- [BL-QUALITY-001] Add the reusable StateDD quality firewall contract: failure scans, incident response, project quality gates, runtime-truth separation, and generated downstream template propagation.
- [BL-BROWSER-001] Add provider-agnostic browser verification for user-facing changes.
- [BL-007] Public usability and release-readiness polish: simplified README top half, added quick commands cheat sheet, improved adoption profile chooser, polished 5-minute guide, and finalized release notes as release-candidate ready.
- [BL-005] Add a real canonical schema/export/import example project that generates ChatGPT prompts from the same schema the app validates.
- [BL-012] Add evidence pack manifests and a redaction gate.
- [BL-013] Add non-destructive downstream upgrade tooling.
- [BL-014] Add adoption profiles and an interactive bootstrap wizard.

## WATCHLIST

- Queue bloat.
- Unverified claims.
- Confusion between template-maintenance truth and generated downstream truth.
- No feature backlog item may be selected while `execution_mode` is `quality_freeze`, unless it directly closes the freeze condition.
- Closure evidence must prove product/runtime truth where applicable, not only command execution or handoff claims.
