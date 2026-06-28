# Slice Contract Template

Use this before coding. Write it into the active evidence folder README header or
append it to `NEXT_ACTIONS.md` under the active item.

The slice contract prevents agents from wandering into adjacent work. It also
makes the human override rule explicit.

```yaml
slice:
  id: BL-XXX
  title: short active title
  type: feature | fix | refactor | docs | spike | ops
  owner: coding-agent
  user_value: one sentence describing real user or operator value
  non_goals:
    - Do not redesign X.
    - Do not add Y.
  acceptance_criteria:
    - Criterion 1 with verification method.
    - Criterion 2 with verification method.
    - Criterion 3 with evidence path.
  failure_scan:
    required: yes | no
    path: docs/failure_scans/<slice>.md | not applicable
    questions:
      - What could go wrong?
      - How would the user or operator notice?
      - What adjacent failures are likely?
      - What did previous tests miss?
      - Which invariant prevents the class?
      - Which adversarial case proves it?
      - What runtime or live proof is required?
  global_quality_gates:
    product_quality_gate: required | not_applicable
    runtime_truth_gate: required | not_applicable
    live_canary_gate: required | not_applicable
    redteam_gate: required | not_applicable
    known_bad_events_gate: required | not_applicable
  closure_rule: |
    This slice is not closure-grade merely because its own acceptance criteria
    pass. It must also pass applicable global quality gates and record residual
    risk honestly.
  escalation_required_for:
    - Changing canonical schema or product truth.
    - Adding silent repair behavior.
    - Replacing existing data model or architecture boundary.
    - Any irreversible change.
    - Bypassing a failing quality gate.
    - Leaving quality_freeze while P0 product behavior remains unproven.
  human_override:
    allowed: true
    protocol: |
      The human product owner may override workflow steps. The agent must not
      use "the workflow" to ignore explicit human direction. Override must be
      recorded in the evidence README and final handoff as
      `Human override used: yes`.
    acceptable_override_examples:
      - Skip browser proof for a docs-only or urgent internal change.
      - Use a temporary workaround when the user explicitly accepts the tradeoff.
      - Proceed without updating every state file if the change is exploratory.
      - Defer a full audit when the user asks for fast partial progress.
      - Exceed the normal evidence file limit if the user requests a larger diagnostic bundle.
    non_acceptable_overrides:
      - Deleting important data without backup.
      - Falsifying evidence, tests, screenshots, or handoff claims.
      - Claiming closure-grade status without proof.
      - Hiding failing tests.
      - Silently changing canonical schemas or product truth.
      - Making irreversible architecture changes without recording the decision.
```
