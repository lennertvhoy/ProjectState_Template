---
name: "git-safety"
gate_level: 1
evidence_max: 1
cheapest_proof: "Schema-valid Git safety report permits the requested mode"
escalate_when: "Any metadata, fsck, synchronization, identity, or isolation check fails"
description: "Run the centralized fail-closed Git mutation preflight"
when_to_use:
  - "Before repository or StateDD mutation in an existing Git repo"
  - "Before provisioning an agent worktree or clone"
  - "After repairing a latched Git safety failure"
required_inputs:
  - "Requested repository path"
  - "Isolation mode: normal_branch, worktree, clone, or read_only"
  - "Source repo for clone mode"
step_by_step:
  - name: "Select the isolation mode"
    action: "Use normal_branch for one trusted local agent, clone for containers/independent agents, worktree only with explicit trusted-local same-identity opt-in, or read_only for diagnosis"
    verify: "Requested mode matches the runtime and collaboration boundary"
  - name: "Run one transaction"
    command: "python3 scripts/statedd_git_safety_check.py --mode <mode>"
    expected: "Human report exits 0; writable modes say mutation permitted: yes"
    failure: "Do not edit source/state; preserve the read-only latch and diagnose"
  - name: "Record JSON evidence"
    command: "python3 scripts/statedd_git_safety_check.py --mode <mode> --format json"
    expected: "Output validates against schemas/git_safety_report.schema.json"
    failure: "Report-validation failure is a blocking error"
  - name: "Restart only after repair"
    command: "python3 scripts/statedd_git_safety_check.py --mode <mode> --restart-session"
    expected: "All mandatory checks rerun and the external latch clears only on success"
    failure: "Remain read-only"
failure_cases:
  - name: "Permission or ownership anomaly"
    detection: "Metadata mismatch/unwritable or write probe fails"
    recovery: "Diagnosis only; no automatic permission repair"
    evidence: "Git safety JSON"
  - name: "Synchronization failure"
    detection: "Mandatory fetch fails"
    recovery: "Repair remote/network/credentials, then explicitly restart"
    evidence: "Synchronization and latch fields"
  - name: "Unsafe worktree boundary"
    detection: "Container, privileged runtime, unknown/mismatched identity, or absent opt-in"
    recovery: "Use an independent full clone"
    evidence: "Runtime, worktree, and isolation fields"
evidence_required:
  - "git_safety_report.json"
exit_criteria:
  - "Requested mode is permitted or read_only is honestly recorded"
  - "No failed mandatory Git operation is ignored"
  - "No permission repair or force cleanup was attempted"

