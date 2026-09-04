# ProjectState Quality Firewall

> **Optional hardened/legacy reference.** This is not part of the v6 core
> workflow and is not copied by the default `core` profile. Projects adopt
> only the controls justified by their actual risk and delivery boundary.

**Purpose:** Make ProjectState a failure-discovery workflow, not only a traceability workflow.

The quality firewall is a reusable layer that every downstream project adapts to
its own product. It protects the product by requiring broad, adversarial, and
runtime-aware proof before a slice can be treated as closure-grade.

## Core Rule

A slice is not closure-grade merely because its own acceptance checklist passed.
It must also pass the current project quality gates and any global invariants
that protect user-facing or operator-facing behavior.

A non-trivial fix or feature slice is not closure-grade if it only handles the
observed failing input without a durable invariant. Use
`ANTI_BRITTLENESS_GUARD.md` and `docs/quality_gates/ANTI_BRITTLENESS_GATE.md`
to record the anti-brittleness review.

## Evidence Hierarchy

Evidence should prove product truth, not only that commands ran.

Use these evidence types in `docs/EVIDENCE_LOG.md` and evidence README files:

- `implementation`: source changes, migrations, config updates, docs updates.
- `test`: unit, integration, typecheck, lint, build, schema, and static checks.
- `product_behavior`: proof that a real user/operator flow behaves correctly.
- `runtime_truth`: proof that the running artifact matches the repo and config being claimed.
- `adversarial`: negative, red-team, malformed, stale, bypass, or adjacent-failure checks.
- `known_bad_event`: regression proof for a previously observed bad event.
- `post_deploy`: proof that the deployed or daemonized system keeps working after release.
- `security_privacy`: secret scans, privacy checks, data-retention checks, auth checks.
- `state_update`: state/doc/handoff updates that accurately record the verified truth.

## Closure Gates

Before closure, answer these questions honestly:

1. Does the real user or operator flow work?
2. Are known bad flows impossible or blocked by a regression fixture?
3. Were likely adjacent failures searched for?
4. Does runtime identity prove the live artifact is the artifact being claimed?
5. Do global invariants pass independently of the slice checklist?
6. Is post-deploy or post-change watching required, and if so, did it pass?
7. Do the state files record residual risk instead of hiding it?
8. Does the fix generalize through a typed/schema/state-machine/validator/contract
   authority path instead of exact observed strings or fixture-only behavior?

## Execution Modes

Downstream repos should record `current_state.execution_mode` in
`PROJECT_STATE.yaml`.

- `operating`: normal delivery mode.
- `quality_freeze`: feature work is blocked until the failing quality gate is green.
- `incident_response`: an observed bad event is being captured, fixed, and proven.
- `release_candidate`: release hardening mode where closure gates are stricter.

Feature backlog items must not be selected during `quality_freeze` unless they
directly close the freeze condition.

## Required Project Adaptation

Each downstream project must define its own quality gates and global invariants.
Examples:

- A web app might require no console errors on accepted routes, current runtime
  identity, core journey browser proof, and known bad route regressions.
- A bot might require no raw provider/debug text in user output, live canary
  proof, provider preflight, and bad transcript regressions.
- A chess engine might require legal move invariants, engine correctness
  falsifiers, and benchmark regressions.
- A system configuration repo might require VM boot, rollback proof, service
  health, and install safety.

Do not paste a product-specific invariant into this template as universal truth.
Put project-specific invariants in the downstream repo, preferably in
`docs/quality_gates/README.md`, tests, scripts, or `PROJECT_ADAPTER.yaml`.

## Bad Event Ingestion

When a user reports a bad live event, use the incident workflow:

1. Classify severity and enter `incident_response` or `quality_freeze` for P0.
2. Save the event as a fixture or durable artifact.
3. Write an incident note under `docs/incidents/`.
4. Identify the missing invariant.
5. Add a failing test or quality check first where practical.
6. Fix the system, not only the symptom.
7. Prove the exact event now passes.
8. Prove adjacent cases pass.
9. Capture runtime/live proof when applicable.
10. Run post-deploy watch when applicable.
11. Complete the anti-brittleness review for non-trivial fixes/features.
12. Close only when global gates pass or a human override records the remaining risk.

## Handoff Truth

Agent handoffs are claims, not verified truth. A handoff may say a gate passed,
but ProjectState should only accept closure when the claim points to durable evidence
or an independent quality gate result.
