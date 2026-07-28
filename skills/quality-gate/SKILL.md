---
name: "quality-gate"
gate_level: 2
evidence_max: 8
cheapest_proof: "One authoritative quality-gate invocation exits 0"
escalate_when: "Release requires level 3 with CI proof"
description: "Execute the full quality gate pipeline for a slice"
when_to_use:
  - "After implementation, before closure"
  - "When CTO handoff requests quality freeze"
  - "Before release or deployment"
required_inputs:
  - "Slice ID"
  - "Branch with changes"
step_by_step:
  - name: "Run authoritative local gate"
    command: "python3 scripts/projectstate_quality_gate.py --gate-level 2"
    expected: "Exit 0 after every detected suite, compile, schema, state, instruction, efficiency, evidence, and diff check has run"
    failure: "Fix every aggregated failure and re-run the same command"
  - name: "Add risk-specific proof when applicable"
    action: "For user-facing/runtime work, run runtime identity plus browser verification; for releases or migrations, use gate level 3 and the release gate"
    expected: "Proof matches the actual change type"
    failure: "Record the slice as partial; never substitute screenshots or local tests for runtime or CI truth"
expected_outputs:
  - "All gate scripts exit 0"
  - "Test output"
  - "Static analysis output"
  - "State validation output"
failure_cases:
  # failure cases for quality-gate skill
  - name: "Any gate fails"
    detection: "Any quality gate script exits non-zero"
    recovery: "Address specific failure, re-run full pipeline"
    evidence: "Gate output logs"
  - name: "Tests fail"
    detection: "pytest exits non-zero"
    recovery: "Fix code, not tests (unless test bug)"
    evidence: "Test output"
  - name: "State invalid"
    detection: "check_state_docs.py or schema validation fails"
    recovery: "Fix YAML/schemas"
    evidence: "Validation output"
  - name: "Evidence missing"
    detection: "projectstate_evidence_type_check.py exits non-zero"
    recovery: "Collect required evidence before proceeding"
    evidence: "Evidence check output"
evidence_required:
  - "Authoritative quality-gate output"
  - "Risk-specific proof when required"
exit_criteria:
  - "The authoritative local quality gate passes (exit 0)"
  - "No outstanding failures"
  - "Ready for close-slice skill"
